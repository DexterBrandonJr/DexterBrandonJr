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

## 2026-09-28 — Recorded pages start by themselves and resume where you stopped

**Decisions:**
- Dex: "once done, start audio playback automatically so I can be in another app when it plays." A recorded page marked `data-autoplay` (now `narrate.py`'s default; `--no-autoplay` turns it off) starts playing the moment it opens.
- Where the browser refuses sound a page starts on its own, the first tap anywhere on the page starts it (a capture listener for click, touchend and keydown, ignoring taps on the bar itself, disarmed once playback starts).
- Each viewer's place is kept in `localStorage` (`listen-at:<file>`, every 5 s and on pause), so an automatic start picks up where Dex stopped instead of at the top of 27 minutes. Stop, the end of the recording, or picking a section forgets it.

**Facts / preferences:**
- iPhones never let a page start sound without a tap, and a web page cannot start audio on a phone that doesn't have it open. So "no tap at all" is not buildable from a page; one tap anywhere is the floor on iPhone. The push-notification tool carries text only, so it cannot start audio either.
- Browser checks (Playwright on Chromium): 31/31. New ones: plays on open with no tap; the saved position matches where it paused; reopening picks up there; Stop forgets it; with autoplay refused the bar says "Tap anywhere to start listening", a tap on the text starts it, a saved place reads "picks up at 5:00" and the tap resumes at 5:00; the Listen button still works.
- Not verified: whether the Claude app's own viewer allows sound without a tap (if it does, the brief plays with zero taps there).

**Artifacts:**
- Brief, version 4, starts on open: https://claude.ai/artifact/UJGppVCHXFpzAoE2pMWZyf

**Open threads:**
- Zero taps on iPhone would need a phone-side trigger, e.g. a Shortcuts automation that fires on a message from Claude and plays the file. It needs a one-time setup on the phone and a file reachable without a login; not built.

## 2026-09-28 — Multi-view systems: one player, one recording per view, failure and growth scans

**Decisions:**
- A system of many pages or tiers gets one player page (`system-shell.html`, written by `narrate_system.py`) that owns the audio; views load inside it, so moving between views never stops the recording. Lock-screen next/previous move between views; a tier limit sets how deep a listen goes; "follow" makes the page track the view being read.
- One recording per view, fingerprinted by its words and voice; a rerun re-records only views whose words changed. A view can carry `<script type="text/x-listen">` with words written for the ear, used instead of the screen text (charts, filters, cards).
- Default voice is now `en_US-lessac-medium`: 5.4x faster than `-high` (21.6x vs 4.0x real time on 4 CPUs) with the same clarity (offline transcription 0.916 vs 0.917 word match). Splitting across processes is slower; the engine already uses every core.
- Briefs publish first and record in the background, then republish at the same link. Browser-generated voices were ruled out (iPhones suspend that kind of audio in the background); online voice services too (the text would leave the machine).

**Facts / preferences:**
- System checks (Playwright, Chromium, host without byte ranges): 12/12 — plays on open, next view and the page follows, navigating inside a view keeps audio, a view's end rolls into the next, tier limit, reopening resumes, follow off, tap inside a view starts it when autoplay is refused.
- Recorder on the demo: 4 views in 9 s; unchanged rerun records 0; editing one view records 1. Every run still opens a headless browser per view to read it (about a second each).
- Artifact limits that bound a system: 255 files per publish, 16 MB per file, 256 MB per version: about 11 hours of audio at 48 kbps.
- Failure predictions on the hub's ledger (subject innovation-brief-skill): 170 views load inside the player on Dex's phone, p 0.70; 171 audio survives an app switch in iPhone Safari, p 0.85; 172 the same in the Claude iOS app's viewer, p 0.40; 173 a recording goes stale at least once by 2026-10-28, p 0.60; 174 the cleanup rules misread a symbol Dex notices by 2026-10-28, p 0.45.

**Artifacts:**
- Demo system: https://claude.ai/artifact/2KFAaXtJK57HwUQUPFuA1C
- `share/artifact-listen/narrate_system.py`, `share/artifact-listen/system-shell.html`

**Open threads:**
- Settle bets 170–172 from Dex's phone test of the demo and the brief.
- Growth, in order: staleness guard (view carries its fingerprint, player warns when audio is older); live "what changed" clips from the scheduled loop; block-level highlight inside views; a short spoken summary per tier; the hub digest as a daily audio briefing; a quality voice (Kokoro) where a GPU exists.
