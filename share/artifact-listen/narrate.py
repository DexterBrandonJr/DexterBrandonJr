#!/usr/bin/env python3
"""Record a page's Listen text as an MP3 that keeps playing with the screen off."""
import argparse
import glob
import html
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

PROBE = ('<script>(function(){var d=window.__listen||(window.__listenQueue?{blocks:window.__listenQueue,sections:[]}:null);'
         'var p=document.createElement("pre");p.id="__listen_dump";p.textContent=JSON.stringify(d);'
         'document.body.appendChild(p);})();</script>')

MONTHS = 'January February March April May June July August September October November December'.split()


def month(m):
    n = int(m)
    return MONTHS[n - 1] if 1 <= n <= 12 else m


def money(m):
    whole, cents = int(m[1]), int(m[2])
    if not whole:
        return f'{cents} cents'
    return f'{whole} dollar{"s" if whole != 1 else ""}' + (f' {cents}' if cents else '')


RULES = [
    (r'\b(\d{4})-(\d\d) · (\d\d)(?!\d)',lambda m: f'{month(m[2])} and {month(m[3])} {m[1]}'),
    (r'\b(\d{4})-(\d\d)-(\d\d)(?!\d)', lambda m: f'{month(m[2])} {int(m[3])}, {m[1]}'),
    (r'\b(\d{4})-(\d\d)(?![-\d])', lambda m: f'{month(m[2])} {m[1]}'),
    (r'\b((?:%s)(?: \d{1,2},)? \d{4}) ?(?=[A-Z])' % '|'.join(MONTHS), r'\1. '),
    (r'\$(\d+)\.(\d\d)\b', money),
    (r'\b00(\d\d)\b', r'\1'),
    (r'(\d)\s*–\s*(\d)', r'\1 to \2'),
    (r'\bn/a\b', 'not applicable'),
    (r'\bE\[(\w+)\]', r'expected \1'),
    (r'(\w)\.md\b', r'\1 dot M D'),
    (r'\barXiv\b', 'archive'),
    (r'\b0(\d):(\d\d)\b', r'\1:\2'),
    (r'\b([a-z]):(\d+)', r'\1 \2'),
    (r'\bv(\d+)\b', r'version \1'),
    (r':\s*—\s*(?=[.;]|$)', ': none'),
    (r'\s*—\s*', ', '),
    (r'\s*–\s*', ' '),
    (r'\s*·\s*', ', '),
    (r'\s*−\s*', ' minus '),
    (r'(\d)\s*×', r'\1 times'),
    (r'\s*×\s*', ' times '),
    (r'\s*[≈~]\s*', ' about '),
    (r'\s*→\s*', ' to '),
    (r'\s+=\s+|=', ' equals '),
    (r'\s+\+\s+', ' plus '),
    (r'(\d)\s*%', r'\1 percent'),
    (r'\s*&\s*', ' and '),
    (r'\b([a-z]+)\s*/\s*([a-z]+)\b', r'\1 or \2'),
    (r'\s+/\s+', ' or '),
    (r'/', ' slash '),
    (r'_', ' '),
    (r'[\[\]{}|<>*#`\\^]', ' '),
    (r'\s{2,}', ' '),
    (r'\s+([,.;:!?])', r'\1'),
    (r'([,.;:])[,.;:]+', r'\1'),
]


def speakable(text, heading=False):
    if heading:
        text = re.sub(r'^(\d+)\s*·\s*', r'Section \1. ', text)
    for pattern, repl in RULES:
        text = re.sub(pattern, repl, text)
    return text.strip()


def find_chrome():
    found = [os.environ.get('CHROME')]
    found += sorted(glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome'))
    found += ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
              '/Applications/Chromium.app/Contents/MacOS/Chromium']
    found += [shutil.which(n) for n in ('chromium', 'chromium-browser', 'google-chrome', 'chrome')]
    for c in found:
        if c and os.path.exists(c):
            return c
    sys.exit('narrate: no Chrome or Chromium found; set CHROME to its path')


def reading(page):
    src = page.read_text(encoding='utf-8')
    at = src.rfind('</body>')
    probed = src[:at] + PROBE + src[at:] if at >= 0 else src + PROBE
    with tempfile.TemporaryDirectory() as d:
        f = Path(d, 'probe.html')
        f.write_text(probed, encoding='utf-8')
        args = [find_chrome(), '--headless=new', '--disable-gpu', '--virtual-time-budget=5000', '--dump-dom', f.as_uri()]
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            args.insert(1, '--no-sandbox')
        dom = subprocess.run(args, capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<pre id="__listen_dump">(.*?)</pre>', dom, re.S)
    data = json.loads(html.unescape(m.group(1))) if m else None
    if not data or not data.get('blocks'):
        sys.exit('narrate: no Listen bar on the page, or it found nothing to read')
    return data


def id3(title):
    def frame(fid, text):
        body = b'\x01' + text.encode('utf-16')
        return fid.encode() + struct.pack('>I', len(body)) + b'\x00\x00' + body
    frames = frame('TIT2', title) + frame('TPE1', 'Listen')
    n = len(frames)
    return b'ID3\x03\x00\x00' + bytes([(n >> 21) & 127, (n >> 14) & 127, (n >> 7) & 127, n & 127]) + frames


def record(texts, starts, voice_name, voice_dir, kbps, title):
    try:
        import lameenc
        from piper import PiperVoice
    except ImportError:
        sys.exit('narrate: needs piper-tts and lameenc (pip install piper-tts lameenc)')
    model = voice_dir / f'{voice_name}.onnx'
    if not model.exists():
        voice_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, '-m', 'piper.download_voices', '--download-dir', str(voice_dir), voice_name], check=True)
    voice = PiperVoice.load(str(model))
    rate = voice.config.sample_rate
    pcm, marks, spans = bytearray(), [], []
    for i, text in enumerate(texts):
        if i:
            pcm += bytes(2 * int(rate * (1.0 if i in starts else 0.45)))
        marks.append(round(len(pcm) / 2 / rate, 2))
        for chunk in voice.synthesize(text):
            pcm += chunk.audio_int16_bytes
        spans.append(len(pcm) / 2 / rate - marks[-1])
    enc = lameenc.Encoder()
    enc.set_bit_rate(kbps)
    enc.set_in_sample_rate(rate)
    enc.set_channels(1)
    enc.set_quality(2)
    mp3 = id3(title) + enc.encode(bytes(pcm)) + enc.flush()
    return mp3, marks, spans, len(pcm) / 2 / rate


def attach(page, src, marks, duration):
    s = page.read_text(encoding='utf-8')
    tag = (f'<audio id="ls-audio" preload="none" src="{html.escape(src)}" '
           f'data-duration="{round(duration)}" data-marks="{json.dumps(marks, separators=(",", ":"))}"></audio>')
    s, k = re.subn(r'<audio id="ls-audio"[^>]*>(?:\s*</audio>)?', lambda m: tag, s, count=1)
    if not k:
        s, k = re.subn(r'<button type="button" id="ls-play"', lambda m: tag + '\n' + m.group(0), s, count=1)
    if not k:
        sys.exit('narrate: no Listen bar on the page to attach the recording to')
    page.write_text(s, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description='Record a page that carries the Listen bar as an MP3 with an offline voice, '
                                             'and attach it to the bar so it plays in the background on a phone.',
                                 epilog='Setup once: pip install piper-tts lameenc. The voice downloads on first run. '
                                        'Publish the MP3 beside the page under the same name.')
    ap.add_argument('page', type=Path)
    ap.add_argument('--out', type=Path, help='MP3 path (default: next to the page, same name)')
    ap.add_argument('--voice', default='en_US-lessac-high')
    ap.add_argument('--voice-dir', type=Path, default=Path.home() / '.cache' / 'piper-voices')
    ap.add_argument('--kbps', type=int, default=48)
    ap.add_argument('--text', action='store_true', help='print what would be spoken and stop')
    ap.add_argument('--no-attach', action='store_true', help='write the MP3 but leave the page alone')
    a = ap.parse_args()

    data = reading(a.page)
    starts = {s['at'] for s in data.get('sections', [])}
    texts = [speakable(t, i in starts) for i, t in enumerate(data['blocks'])]
    if a.text:
        print('\n'.join(texts))
        return
    m = re.search(r'<title>(.*?)</title>', a.page.read_text(encoding='utf-8'), re.S)
    title = html.unescape(m.group(1)).strip() if m else a.page.stem
    out = a.out or a.page.with_suffix('.mp3')
    mp3, marks, spans, duration = record(texts, starts, a.voice, a.voice_dir, a.kbps, title)
    out.write_bytes(mp3)
    if not a.no_attach:
        attach(a.page, out.name, marks, duration)
    words = [len(t.split()) for t in texts]
    odd = [i for i, (w, s) in enumerate(zip(words, spans)) if s <= 0 or not 1.0 <= w / s <= 4.5]
    print(f'{out}: {len(mp3) / 1e6:.1f} MB, {duration / 60:.1f} min, {len(texts)} blocks, {len(starts)} sections')
    for i in odd:
        print(f'  check block {i}: {words[i]} words in {spans[i]:.1f} s: {texts[i][:80]}')


if __name__ == '__main__':
    main()
