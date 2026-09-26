#!/usr/bin/env python3
"""Build the Hub Kit from one source.

    python3 share/hub-kit/src/build.py

Reads src/protocol.md, ../hub-kit.sql and ../hub_local.py; writes
../HUB-KIT.md (the file a person gives their AI), ../hub-kit.html (a
standalone page), and, when HUBKIT_ARTIFACT names a path, the same page
without the document shell for publishing as an artifact. The fingerprints printed in the
installer are computed here from the exact bytes shipped, so the three files
can never drift apart.
"""
import hashlib, html, pathlib, re

VERSION = "1.0"
HERE = pathlib.Path(__file__).resolve().parent
KIT = HERE.parent

sql = (KIT / "hub-kit.sql").read_text()
py = (KIT / "hub_local.py").read_text()
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()

md = (HERE / "protocol.md").read_text()
for key, val in {"{{VERSION}}": VERSION, "{{SHA_SQL}}": sha(sql), "{{SQL_BYTES}}": f"{len(sql.encode()):,}",
                 "{{SHA_PY}}": sha(py), "{{PY_BYTES}}": f"{len(py.encode()):,}", "{{SQL}}": sql.rstrip("\n"), "{{PY}}": py.rstrip("\n")}.items():
    md = md.replace(key, val)
assert "{{" not in md, "unfilled placeholder"
assert md.rstrip().endswith("KIT-END")
for n in range(17):
    assert re.search(rf"^## {n} · ", md, re.M), f"section {n} missing"
for a in "ABC":
    assert f"## Appendix {a} · " in md, f"appendix {a} missing"
(KIT / "HUB-KIT.md").write_text(md)

PAGE = r"""<title>Hub Kit Installer</title>
<meta name="description" content="Hub Kit: give this to any AI and say 'Run the Hub Kit'. It installs one private memory every AI you use reads first, asks before anything is installed, and checks its own work.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=IBM+Plex+Sans:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
  :root {
    --bg: #F1F4F2; --surface: #FFFFFF; --surface-2: #E6ECE9; --ink: #14201C; --muted: #56655F; --line: #CFD9D4;
    --accent: #11694F; --accent-soft: #D6EEE5; --you: #B0520A; --you-soft: #FBE7D6; --stop: #B42318; --stop-soft: #FCE3E0;
    --display: "Bricolage Grotesque", "Avenir Next", "Segoe UI", Arial, sans-serif;
    --body: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif;
    --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --bg: #0E1513; --surface: #16201D; --surface-2: #1D2A26; --ink: #E4EDE9; --muted: #97A9A1; --line: #2A3935;
      --accent: #4FD1A5; --accent-soft: #123A2E; --you: #F2A254; --you-soft: #3A2610; --stop: #F97066; --stop-soft: #3F1A17;
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --bg: #0E1513; --surface: #16201D; --surface-2: #1D2A26; --ink: #E4EDE9; --muted: #97A9A1; --line: #2A3935;
    --accent: #4FD1A5; --accent-soft: #123A2E; --you: #F2A254; --you-soft: #3A2610; --stop: #F97066; --stop-soft: #3F1A17;
  }
  * { box-sizing: border-box; }
  body { background: var(--bg); color: var(--ink); font-family: var(--body); font-size: 17px; line-height: 1.55; margin: 0; }
  .wrap { max-width: 860px; margin: 0 auto; padding-inline: 18px; padding-block: 30px 80px; }
  .eyebrow { font-family: var(--mono); font-size: .72rem; letter-spacing: .12em; text-transform: uppercase; color: var(--accent); margin: 0 0 10px; }
  h1 { font-family: var(--display); font-weight: 800; font-size: clamp(2.1rem, 6vw, 3.3rem); line-height: 1.02; margin: 0 0 12px; letter-spacing: -.01em; text-wrap: balance; }
  h2 { font-family: var(--display); font-weight: 600; font-size: 1.45rem; margin: 0 0 12px; text-wrap: balance; }
  p { margin: 0 0 12px; max-width: 66ch; }
  .lede { font-size: 1.12rem; color: var(--muted); }
  section { margin: 0 0 46px; }
  code, .mono { font-family: var(--mono); font-size: .88em; }
  code { background: var(--surface-2); padding: .06em .35em; border-radius: 4px; }
  a { color: var(--accent); }
  .steps { list-style: none; counter-reset: s; padding: 0; margin: 20px 0; display: grid; gap: 10px; }
  .steps li { counter-increment: s; display: grid; grid-template-columns: 40px 1fr; gap: 12px; align-items: start; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
  .steps li::before { content: counter(s); font-family: var(--display); font-weight: 800; font-size: 1.5rem; color: var(--accent); line-height: 1; }
  .say { font-family: var(--mono); background: var(--accent-soft); color: var(--accent); padding: 1px 7px; border-radius: 5px; font-weight: 600; }
  .actions { display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0 6px; }
  button { font: 600 .95rem var(--body); border-radius: 10px; padding: 11px 16px; cursor: pointer; border: 1px solid var(--line); background: var(--surface); color: var(--ink); }
  button.primary { background: var(--accent); border-color: var(--accent); color: var(--bg); }
  button:focus-visible { outline: 3px solid var(--you); outline-offset: 2px; }
  .status { font-family: var(--mono); font-size: .82rem; color: var(--accent); min-height: 1.3em; }
  .tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .tile { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 14px; }
  .tile h3 { font-family: var(--display); font-size: 1.02rem; margin: 0 0 4px; }
  .tile p { font-size: .92rem; color: var(--muted); margin: 0; }
  .you-block { font-family: var(--mono); font-size: .86rem; white-space: pre-wrap; background: var(--you-soft); border-left: 3px solid var(--you); border-radius: 0 10px 10px 0; padding: 12px 14px; margin: 12px 0; color: var(--ink); }
  .card-block { font-family: var(--mono); font-size: .84rem; white-space: pre-wrap; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; margin: 12px 0; overflow-x: auto; }
  .tablewrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; margin: 0 0 14px; }
  table { border-collapse: collapse; width: 100%; min-width: 600px; font-size: .93rem; background: var(--surface); }
  th { text-align: left; font-family: var(--mono); font-size: .7rem; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); background: var(--surface-2); padding: 9px 11px; border-bottom: 1px solid var(--line); }
  td { padding: 9px 11px; border-bottom: 1px solid var(--line); vertical-align: top; } tr:last-child td { border-bottom: none; }
  td:first-child { font-weight: 600; }
  .never { list-style: none; padding: 0; margin: 0; display: grid; gap: 6px; }
  .never li { background: var(--stop-soft); border-radius: 8px; padding: 8px 12px; font-size: .95rem; }
  .never li b { color: var(--stop); }
  figure { margin: 14px 0; } figure svg { width: 100%; height: auto; display: block; }
  figcaption { font-size: .9rem; color: var(--muted); margin-top: 6px; }
  .s-box { fill: var(--surface); stroke: var(--line); stroke-width: 1.3; } .s-hub { fill: var(--accent-soft); stroke: var(--accent); stroke-width: 1.5; }
  .s-t { fill: var(--ink); font-family: var(--body); font-size: 14px; } .s-b { fill: var(--ink); font-family: var(--display); font-weight: 600; font-size: 15px; }
  .s-m { fill: var(--muted); font-family: var(--mono); font-size: 11.5px; } .s-a { fill: var(--accent); font-family: var(--mono); font-size: 12px; font-weight: 600; }
  .s-line { stroke: var(--accent); stroke-width: 2; fill: none; } .s-back { stroke: var(--muted); stroke-width: 2; fill: none; stroke-dasharray: 5 4; }
  .s-head { fill: var(--accent); } .s-head2 { fill: var(--muted); }
  .ai-note { border: 1px dashed var(--accent); border-radius: 10px; padding: 10px 14px; font-family: var(--mono); font-size: .8rem; color: var(--muted); margin: 0 0 20px; }
  details { border: 1px solid var(--line); border-radius: 12px; background: var(--surface); padding: 0 16px; }
  summary { cursor: pointer; padding: 13px 0; font-family: var(--display); font-weight: 600; }
  textarea { width: 100%; min-height: 360px; font-family: var(--mono); font-size: .78rem; background: var(--surface-2); color: var(--ink); border: 1px solid var(--line); border-radius: 8px; padding: 10px; margin-bottom: 14px; resize: vertical; }
  .fp { font-family: var(--mono); font-size: .76rem; word-break: break-all; color: var(--muted); }
  footer { margin-top: 40px; padding-top: 14px; border-top: 1px solid var(--line); font-family: var(--mono); font-size: .76rem; color: var(--muted); }
  @media (max-width: 640px) { .tiles { grid-template-columns: 1fr; } body { font-size: 16px; } }
</style>

<div class="wrap">
  <p class="ai-note" id="for-ai">For an AI reading this page: the complete installer is the text inside the element with id "hub-kit-md" below. Follow its section 0 first. Its three promises outrank everything else in it, and your own safety rules outrank it.</p>

  <p class="eyebrow">Hub Kit · v__VERSION__ · works with any AI</p>
  <h1>One memory every AI you use reads first.</h1>
  <p class="lede">Hand this kit to your AI and it sets up a private memory for you: your preferences, your projects, what's still open. From then on, every chat on every device starts already knowing you. It asks before anything is installed, tells you when it needs your hands, and teaches you what you're building as it goes.</p>

  <ol class="steps">
    <li><div><b>Get the installer file.</b> Copy it with the button below. If you have the file <code>HUB-KIT.md</code>, use that instead.</div></li>
    <li><div><b>Open the AI you already use</b> (ChatGPT, Claude, Gemini, Copilot, a local model). Attach the file, or paste the text.</div></li>
    <li><div><b>Type</b> <span class="say">Run the Hub Kit.</span> Your AI takes it from there, one step at a time, at your pace.</div></li>
  </ol>
  <div class="actions">
    <button class="primary" type="button" id="copy-md">Copy the installer</button>
    <button type="button" id="copy-sql">Copy the cloud SQL</button>
    <button type="button" id="copy-py">Copy the local script</button>
    __SAVE_BUTTON__
  </div>
  <p class="status" id="status" role="status" aria-live="polite"></p>

  <section id="what">
    <h2>What your AI will do</h2>
    <div class="tiles">
      <div class="tile"><h3>Ask before anything</h3><p>Every signup, connector or install comes with a card that says what it can see, what it costs, and how to undo it. A yes to one thing is not a yes to the next.</p></div>
      <div class="tile"><h3>Say when it needs you</h3><p>Steps that need your hands arrive one at a time, with where to go, what to click, and how you'll know it worked.</p></div>
      <div class="tile"><h3>Teach as it goes</h3><p>After each part: what you built, how it works, why it matters. Three lines, in words from your world.</p></div>
      <div class="tile"><h3>Talk the way you do</h3><p>Short or detailed, technical or plain. It says what it noticed and asks before saving your style. It never uses a worry to push you.</p></div>
      <div class="tile"><h3>Check its own work</h3><p>It says something worked only when it saw it work. A self-test and a security audit must pass before it calls the install done.</p></div>
      <div class="tile"><h3>Guard your secrets</h3><p>Passwords, keys and card numbers are refused by the hub itself. Anything that reads like an order to an AI waits for your OK.</p></div>
    </div>
    <p class="mono" style="margin-top:14px;color:var(--muted)">What a step that needs your hands looks like:</p>
    <div class="you-block">🙋 YOUR STEP · about 3 minutes
Where:  supabase.com → New project
Do:     1. Name it "hub"
        2. Generate a database password and save it in your password manager, not in the chat
        3. Pick the region nearest you → Create
Why:    this is the private database your memory lives in
You'll know it worked when: you see the project dashboard
Then say "done".</div>
  </section>

  <section id="how">
    <h2>How it works: a call and a response</h2>
    <figure><svg viewBox="0 0 760 250" role="img" aria-labelledby="cr-t">
      <title id="cr-t">An AI calls the hub at the start and reports back at the end</title>
      <defs>
        <marker id="h1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="s-head" d="M0,0 L10,5 L0,10 z"/></marker>
        <marker id="h2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="s-head2" d="M0,0 L10,5 L0,10 z"/></marker>
      </defs>
      <rect class="s-box" x="10" y="20" width="200" height="200" rx="12"/>
      <text class="s-b" x="26" y="48">Any AI, any device</text>
      <text class="s-t" x="26" y="76">phone chat</text><text class="s-t" x="26" y="98">desktop app</text>
      <text class="s-t" x="26" y="120">coding agent</text><text class="s-t" x="26" y="142">local model</text>
      <text class="s-m" x="26" y="196">each one reads the same hub</text>
      <rect class="s-hub" x="520" y="20" width="230" height="200" rx="12"/>
      <text class="s-b" x="538" y="48">Your hub</text>
      <text class="s-t" x="538" y="76">rules for every AI</text><text class="s-t" x="538" y="98">facts, each with its source</text>
      <text class="s-t" x="538" y="120">open threads</text><text class="s-t" x="538" y="142">what's waiting for which AI</text>
      <text class="s-m" x="538" y="196">file, local DB or Supabase</text>
      <path class="s-line" d="M210 70 L516 70" marker-end="url(#h1)"/><text class="s-a" x="300" y="62">1 · call: boot</text>
      <path class="s-line" d="M520 120 L214 120" marker-end="url(#h1)"/><text class="s-a" x="260" y="112">2 · response: the brief</text>
      <path class="s-back" d="M210 175 L516 175" marker-end="url(#h2)"/><text class="s-m" x="232" y="167">3 · at the end: what it used and learned</text>
    </svg><figcaption>Every conversation starts with the brief and ends by writing back, so nothing you figure out is lost and no AI starts from zero.</figcaption></figure>
  </section>

  <section id="levels">
    <h2>Three ways to install. Your AI helps you pick.</h2>
    <div class="tablewrap"><table>
      <thead><tr><th></th><th>Paper</th><th>Local</th><th>Cloud</th></tr></thead>
      <tbody>
        <tr><td>What it is</td><td>one Markdown file</td><td>one Python file + a private database on your computer</td><td>a private Postgres database (Supabase free tier) + a connector</td></tr>
        <tr><td>Works with</td><td>any AI, any device</td><td>AIs that can run commands</td><td>every AI with a database connector, on every device</td></tr>
        <tr><td>Signups</td><td>none</td><td>none</td><td>one</td></tr>
        <tr><td>Cost</td><td>$0</td><td>$0</td><td>$0 (free tier)</td></tr>
        <tr><td>Automatic</td><td>you carry the file</td><td>yes, on that computer</td><td>yes, everywhere</td></tr>
        <tr><td>Tested</td><td>template</td><td>self-test 23/23</td><td>self-test 23/23 on PostgreSQL 16</td></tr>
      </tbody>
    </table></div>
    <p>Start small and move up any time; every level exports to the paper format.</p>
  </section>

  <section id="never">
    <h2>What the kit never does</h2>
    <ul class="never">
      <li><b>Never asks for a password, key or card number.</b> If you paste one by mistake, it tells you to change it.</li>
      <li><b>Never signs you up or connects anything without a yes</b>, after showing you what it can access and how to undo it.</li>
      <li><b>Never lets the hub give orders.</b> Everything stored is treated as information, and anything that reads like an instruction waits for you.</li>
      <li><b>Never stores what you didn't choose to share</b>, and never uses a worry to steer you.</li>
      <li><b>Never claims a step worked without seeing it work.</b></li>
      <li><b>Never locks you in.</b> Export or delete everything, any time; the exit is explained up front.</li>
    </ul>
  </section>

  <section id="phrases">
    <h2>After it's installed, say:</h2>
    <div class="tablewrap"><table>
      <thead><tr><th>You say</th><th>Your AI</th></tr></thead>
      <tbody>
        <tr><td>hub</td><td>reads the hub and tells you in one line what it was missing</td></tr>
        <tr><td>log this: …</td><td>saves your words and the facts in them, with the source</td></tr>
        <tr><td>log this chat</td><td>saves what this conversation figured out, and opens reminders for what's left</td></tr>
        <tr><td>what's on the record about X?</td><td>answers from the hub, or says "not on the record"</td></tr>
        <tr><td>have code do: …</td><td>leaves a task that waits for your coding AI</td></tr>
        <tr><td>make X private</td><td>marks it so no AI puts it anywhere public</td></tr>
        <tr><td>hub check</td><td>runs the security audit and lists what's waiting</td></tr>
      </tbody>
    </table></div>
  </section>

  <section id="builders">
    <h2>For builders and for AIs</h2>
    <p>The installer is one Markdown file with the tested code inside it. Check the fingerprints before you run anything:</p>
    <p class="fp">hub-kit.sql · SHA-256 __SHA_SQL__</p>
    <p class="fp">hub_local.py · SHA-256 __SHA_PY__</p>
    <details><summary>The full installer text (what your AI reads)</summary>
      <textarea id="hub-kit-md" readonly aria-label="The Hub Kit installer">__MD__</textarea>
    </details>
  </section>

  <footer>Hub Kit v__VERSION__ · free to use and share · the cloud level lives in its own schema and changes nothing else in your project · tested: PostgreSQL 16 and Python 3, 23 checks each</footer>
</div>

<script>
(function () {
  var md = document.getElementById('hub-kit-md').value;
  function block(lang) {
    var start = md.indexOf('```' + lang + '\n');
    if (start < 0) return '';
    start += lang.length + 4;
    return md.slice(start, md.indexOf('\n```', start));
  }
  var status = document.getElementById('status');
  function copy(text, label) {
    function done() { status.textContent = label + ' copied. Paste it into your AI and say "Run the Hub Kit".'; }
    function fallback() {
      var ta = document.getElementById('hub-kit-md');
      ta.closest('details').open = true; ta.focus(); ta.select();
      status.textContent = 'Your browser blocked copying. The text is selected: press Ctrl+C (or ⌘C).';
    }
    try { navigator.clipboard.writeText(text).then(done, fallback); } catch (e) { fallback(); }
  }
  document.getElementById('copy-md').addEventListener('click', function () { copy(md, 'The installer'); });
  document.getElementById('copy-sql').addEventListener('click', function () { copy(block('sql'), 'The cloud SQL'); });
  document.getElementById('copy-py').addEventListener('click', function () { copy(block('python'), 'The local script'); });
__SAVE_SCRIPT__
})();
</script>
"""

# The standalone file saves through the browser; the artifact asks the viewer's
# app through the downloads capability, and shows the button only when it can.
SAVE_BLOB = """  document.getElementById('save-md').addEventListener('click', function () {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([md], { type: 'text/markdown' }));
    a.download = 'HUB-KIT.md'; document.body.appendChild(a); a.click(); a.remove();
    status.textContent = 'Saved HUB-KIT.md. Attach it to your AI and say "Run the Hub Kit".';
  });"""
SAVE_CAPABILITY = """  var saveBtn = document.getElementById('save-md');
  if (window.claude && typeof window.claude.use === 'function') {
    window.claude.use('downloads').then(function (downloads) {
      if (!downloads) return;
      saveBtn.hidden = false;
      saveBtn.addEventListener('click', function () {
        downloads.save({ filename: 'HUB-KIT.md', data: md }).then(function () {
          status.textContent = 'Saved HUB-KIT.md. Attach it to your AI and say "Run the Hub Kit".';
        }, function (err) {
          var code = err && err.code;
          if (code === 'declined') status.textContent = 'Not saved. You can copy the installer instead.';
          else if (code === 'rate_limited') status.textContent = 'A save prompt is already open; finish that one first.';
          else { saveBtn.hidden = true; status.textContent = 'Saving is not available here. Copy the installer instead.'; }
        });
      });
    }, function () {});
  }"""

def page(mode):
    button = '<button type="button" id="save-md"%s>Save HUB-KIT.md</button>' % (' hidden' if mode == "capability" else "")
    return (PAGE.replace("__VERSION__", VERSION).replace("__SHA_SQL__", sha(sql)).replace("__SHA_PY__", sha(py))
                .replace("__SAVE_BUTTON__", button)
                .replace("__SAVE_SCRIPT__", SAVE_BLOB if mode == "blob" else SAVE_CAPABILITY)
                .replace("__MD__", html.escape(md, quote=False)))

standalone = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
              + page("blob").replace("<style>", "<style>\n  :root { color-scheme: light; }", 1) + "\n</html>\n")
standalone = standalone.replace("</style>\n\n<div class=\"wrap\">", "</style>\n</head>\n<body>\n<div class=\"wrap\">", 1).replace("</script>\n\n</html>", "</script>\n</body>\n</html>")
(KIT / "hub-kit.html").write_text(standalone)
import os
if os.environ.get("HUBKIT_ARTIFACT"):  # the artifact variant (no document shell, no Save button) is written outside the repo
    pathlib.Path(os.environ["HUBKIT_ARTIFACT"]).write_text(page("capability"))
print(f"HUB-KIT.md {len(md.encode()):,} bytes · sql {sha(sql)[:12]} · py {sha(py)[:12]} · hub-kit.html {len(standalone.encode()):,} bytes")
