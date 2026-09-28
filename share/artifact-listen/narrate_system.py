#!/usr/bin/env python3
"""Record every view of a multi-page system and write the listening shell that plays them as one."""
import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from narrate import DEFAULT_VOICE, reading, record, speakable  # noqa: E402

SHELL = Path(__file__).with_name('system-shell.html')
EAR = re.compile(r'<script type="text/x-listen">(.*?)</script>', re.S)


def view_text(page):
    """A view's words for the ear: its own narration script when it has one, else what the Listen bar reads."""
    ear = EAR.search(page.read_text(encoding='utf-8'))
    if ear:
        paras = [re.sub(r'\s+', ' ', p).strip() for p in re.split(r'\n\s*\n', html.unescape(ear.group(1)))]
        return [speakable(p) for p in paras if p], set()
    data = reading(page, inject=True)
    starts = {s['at'] for s in data.get('sections', [])}
    return [speakable(t, i in starts) for i, t in enumerate(data['blocks'])], starts


def main():
    ap = argparse.ArgumentParser(description='Record each view listed in DIR/listen.json and write DIR/index.html, '
                                             'a player that keeps one recording going while the views change.',
                                 epilog='listen.json: {"title": "...", "views": [{"id": "overview", "file": "overview.html", '
                                        '"title": "Overview", "tier": 1}, ...]}. Views listed in listening order. '
                                        'A view can carry <script type="text/x-listen"> with words written for the ear.')
    ap.add_argument('dir', type=Path)
    ap.add_argument('--voice', default=DEFAULT_VOICE)
    ap.add_argument('--voice-dir', type=Path, default=Path.home() / '.cache' / 'piper-voices')
    ap.add_argument('--kbps', type=int, default=48)
    ap.add_argument('--no-autoplay', action='store_true')
    ap.add_argument('--force', action='store_true', help='re-record every view, changed or not')
    a = ap.parse_args()

    root = a.dir
    manifest = json.loads((root / 'listen.json').read_text(encoding='utf-8'))
    out = root / 'listen'
    out.mkdir(exist_ok=True)
    old = {}
    if (out / 'playlist.json').exists():
        old = {it['id']: it for it in json.loads((out / 'playlist.json').read_text(encoding='utf-8'))['items']}

    ids = [v['id'] for v in manifest['views']]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[A-Za-z0-9_-]+', i) for i in ids):
        sys.exit('narrate_system: view ids must be unique and use only letters, digits, - and _')

    items, made, kept = [], 0, 0
    for v in manifest['views']:
        texts, starts = view_text(root / v['file'])
        digest = hashlib.sha256(json.dumps([a.voice, a.kbps, texts]).encode()).hexdigest()[:16]
        mp3 = out / f"{v['id']}.mp3"
        prev = old.get(v['id'])
        if not a.force and prev and prev.get('hash') == digest and mp3.exists():
            items.append({**prev, 'title': v['title'], 'tier': int(v.get('tier', 1)), 'file': v['file']})
            kept += 1
            continue
        audio, marks, _, duration = record(texts, starts, a.voice, a.voice_dir, a.kbps, v['title'])
        mp3.write_bytes(audio)
        items.append({'id': v['id'], 'title': v['title'], 'tier': int(v.get('tier', 1)), 'file': v['file'],
                      'src': f"listen/{v['id']}.mp3", 'duration': round(duration, 2), 'hash': digest, 'marks': marks})
        made += 1
        print(f"  recorded {v['id']}: {duration / 60:.1f} min, {len(audio) / 1e6:.1f} MB")

    for gone in set(old) - set(ids):
        (out / f'{gone}.mp3').unlink(missing_ok=True)
    playlist = {'title': manifest['title'], 'voice': a.voice, 'items': items}
    (out / 'playlist.json').write_text(json.dumps(playlist, indent=1), encoding='utf-8')
    shell = SHELL.read_text(encoding='utf-8')
    shell = shell.replace('/*TITLE*/', html.escape(manifest['title']))
    shell = shell.replace('/*PLAYLIST*/null', json.dumps(playlist).replace('</', '<\\/'))
    shell = shell.replace('/*AUTOPLAY*/true', 'false' if a.no_autoplay else 'true')
    (root / 'index.html').write_text(shell, encoding='utf-8')
    total = sum(it['duration'] for it in items)
    print(f'{root / "index.html"}: {len(items)} views, {total / 60:.1f} min; recorded {made}, unchanged {kept}')


if __name__ == '__main__':
    main()
