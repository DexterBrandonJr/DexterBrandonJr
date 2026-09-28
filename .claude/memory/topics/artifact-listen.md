# Artifact Listen

## 2026-09-28 — Listen keeps playing in the background: a recording, not the browser's voice

**Decisions:**
- Background listening comes from a recording, not the browser's voice. Phones stop `speechSynthesis` the moment the page leaves the screen; an `<audio>` element plays through the phone's media player, so it survives the lock screen and other apps. Dex asked for exactly that ("find a workaround, don't push back").
- Record offline (Piper, voice `en_US-lessac-high`): the page's text never leaves the machine. Sending the text to a third-party speech endpoint was tried first and blocked as data exfiltration; the offline voice is the right design anyway.
- One reading queue: `narrate.py` reads what the page's own Listen script reads (`window.__listen`), so the recording and the voice cannot drift apart. A start time per block (`data-marks`) drives the highlight, the section picker and the lock-screen next/previous.
- A host without byte-range support still works: the bar fetches a local copy (`cache: 'no-store'`) and plays or seeks from that.

**Facts / preferences:**
- Route by Record: 136 blocks, 12 sections, 27.5 min, 9.9 MB MP3 (48 kbps mono), synthesized in about 5 minutes on 4 CPUs.
- Offline transcription check (faster-whisper `base.en`) on 10 sampled blocks: mean word match 0.93, and every sampled time slot held its intended block. The misses were the transcriber's ("straw moly" for "strong-only").
- Browser checks (Playwright on Chromium): 19/19 — play, section jumps on a ranged host and a plain one, speed, pause/resume, stop, the blocked-media fallback, voice mode with no recording.
- Bugs found and fixed on the way: `textContent` glued block children together ("2023-05FrugalGPT", 9 times in the brief); the section picker's first entry skipped the line above the first heading; Chromium makes a second request for the same URL wait behind the media stream's cache entry, which stalled the local copy until `no-store`.
- Not verified: background playback on a real phone (expected from how iOS Safari and Android Chrome treat `<audio>`); whether the Claude app's own viewer keeps audio going when the app is backgrounded; whether the artifact host serves byte ranges (both cases are handled).
- The "no network" claim about the browser's voice was dropped from the docs: some browsers' voices are network voices.
- Fact-check of the answers before this fix (they were wrong): "Google TTS is working" when 1 of 3 chunks was an HTML error page; paraphrased, partly invented text instead of the brief's; a claim that a page can call the phone's native voice with background audio (it cannot: `speechSynthesis` is that bridge); a refusal to read the brief that cited a "no tools" rule Dex never gave.

**Artifacts:**
- Brief, version 3 (page + `route-by-record.mp3`): https://claude.ai/artifact/UJGppVCHXFpzAoE2pMWZyf
- `share/artifact-listen/narrate.py` (recorder), `share/artifact-listen/listen.html` (bar with recording mode), `.claude/skills/innovation-brief/assets/brief-skeleton.html`, the innovation-brief `SKILL.md` step.

**Open threads:**
- Dex: tap Listen, switch apps, confirm it keeps playing. If the Claude app pauses it, open the page in Safari from the share menu, and record which one worked here.
- Earlier artifacts carry the voice-only bar or none; record them when asked (`narrate.py <page>.html`, publish the MP3 beside it).
