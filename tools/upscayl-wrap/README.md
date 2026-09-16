# upscayl-wrap

A command-line wrapper around Upscayl's upscaling engine, with a record of
every job, rules that refuse the jobs that would hurt, and a prediction
written down before each run and scored after it.

Upscayl enlarges a photograph using a neural network — the same idea as Deep
Learning Super Sampling (DLSS), the technique where a game renders at a low
resolution and a network reconstructs a sharper frame. The difference is that
a game hands its network motion data from previous frames, and a photograph
has none, so the network works from the single image in front of it.

The desktop application is good at one image at a time. This is for the rest:
a hundred photos, a folder that fills up on its own, and knowing afterwards
what actually happened.

---

## What it adds over running the engine yourself

You can call `upscayl-bin` directly. Five things go wrong when you do.

**Its exit code is meaningless.** Not unreliable — meaningless. The engine
ends with an unconditional success return, and every early exit it has happens
during start-up, before it touches an image. Once processing begins, nothing
that goes wrong can change the status it exits with. Its per-image work
happens on threads whose results are thrown away.

That produces a failure worth describing on its own. When the graphics device
gives out part-way through, the half-finished buffer is handed to the encoder
anyway, and you get a complete, structurally valid image — usually solid
black. The right size, a correct header, opens in Preview. No amount of
inspecting that file reveals anything wrong with it, and the engine prints
"Upscayled Successfully!" underneath.

So this wrapper checks three things instead of one: that the file exists, that
it is a whole image of the predicted size, and that the engine's error stream
is clean. Only the third catches the black image. Upscayl's own application
does the same thing for the same reason — it ignores the exit code entirely
and searches the error output for the word "Error".

**It has two scale flags that are easy to confuse.** `-z` is the model's own
scale and `-s` is the final output scale, applied as a resample *after* the
model runs. On macOS the engine reads the model's scale out of its filename
and overwrites whatever `-z` was given, so `-z` does nothing. Worse, `-r` and
`-w` silently switch `-s` off. This wrapper never sends `-z`, `-r` or `-w`,
and sends `-s` only when it would change the result.

**Its batch mode loses track.** Two files whose names differ only by extension
can collapse onto one output, and it only notices when they happen to be
adjacent in sorted order. A failure part-way through gives no record of which
files were done.

**Nothing stops a runaway.** Point it at a folder that contains its own
output and it will upscale its results, then upscale those. A 4x upscale of a
48-megapixel photo is 768 megapixels, and nothing warns you first.

**Nothing remembers.** No history, so no way to answer whether a model got
slower, which photos justify the cost, or what failed last Tuesday.

---

## Install

On a Mac, from a terminal:

```bash
git clone https://github.com/DexterBrandonJr/DexterBrandonJr.git
cd DexterBrandonJr/tools/upscayl-wrap
./install.sh
```

The installer works from whichever starting point you are at:

| You have | It does |
| --- | --- |
| Upscayl already installed | Uses the engine inside it. Downloads nothing. |
| Homebrew | `brew install --cask upscayl`, about 370 megabytes. |
| Neither | Downloads just the engine and two models, about 70 megabytes. No application, no administrator password. |

It also clears the quarantine flag macOS puts on downloaded files, links the
command into `~/.local/bin`, creates the watch folders, and runs the checks.

Nothing here needs `sudo`, and there are no third-party Python packages. The
tool runs on the Python that comes with Apple's Command Line Tools.

`./install.sh --dry-run` prints what it would do and does none of it.

---

## Use

```bash
upscayl-wrap doctor                     # is everything present and working
upscayl-wrap models                     # what is available to upscale with
upscayl-wrap up photo.jpg -y            # one image
upscayl-wrap up *.jpg -o ~/big -y       # several, into a chosen folder
upscayl-wrap batch ~/Pictures/scans -r -y   # a folder and everything under it
upscayl-wrap report                     # what the record says
upscayl-wrap review                     # right, wrong, and what to change
```

Results are named `photo_4x.png`, so an upscale is never mistaken for its
original. Every command takes `--json` and prints a machine-readable object
instead of prose.

The `-y` approves the jobs. It is required until you raise the autonomy stage,
which is explained below.

Useful flags on `up` and `batch`:

| Flag | What it does |
| --- | --- |
| `-s, --scale` | Output scale. Default 4. |
| `-m, --model` | Which model. See `upscayl-wrap models`. |
| `-f, --format` | `png`, `jpg` or `webp`. Default `png`. |
| `--tile` | Tile size. Lower it if the engine runs out of memory on large images. 0 is automatic. |
| `--dry-run` | Check everything, run nothing. |
| `--force` | Replace an output that already exists. |

---

## The watch folder

Drop images into `~/Pictures/Upscayl Inbox` and have them appear upscaled in
`~/Pictures/Upscayl Out`.

```bash
upscayl-wrap stage --set 2      # let it act on its own, inside limits
upscayl-wrap install-agent      # sweep on a schedule
```

The sweep runs as a short-lived process every few minutes, and immediately
whenever the inbox changes. A process that starts, sweeps and exits cannot
leak memory or wedge, and comes back clean after a reboot.

```bash
upscayl-wrap uninstall-agent    # stop it
```

---

## How much it may do on its own

Three stages. It starts at the first one.

| Stage | Meaning |
| --- | --- |
| 1 | Approve everything. Every job needs `-y`. The scheduled sweep reports and does nothing. |
| 2 | Adjust within what was approved — these models, up to this scale, these folders. Anything outside still needs approval. |
| 3 | Act alone. |

Any part of the system can drop the stage back to 1 and stop the tool acting:
three failures in a row, a missing engine, a disk filling up. Only you can
raise it, and only by typing a command.

```bash
upscayl-wrap stage              # where it is now
upscayl-wrap stage --set 2      # raise it
upscayl-wrap halt --reason "..."  # stop it by hand
upscayl-wrap resume             # clear a halt; the stage returns to 1
```

Coming back from a halt always lands at stage 1, because resuming at the level
it halted from would skip the part where somebody checks the cause is fixed.

---

## What it refuses, and why

Every rule exists because the failure it prevents is silent.

| It refuses | Because |
| --- | --- |
| An input inside the output folder | Otherwise it upscales its own results, forever, until the disk fills. |
| Writing over the original | That is the only copy of the input. |
| An output path outside the output folder | A job should not be able to write anywhere on the disk. |
| A predicted output over 400 megapixels | A 4x upscale of a 48-megapixel photo is 768 megapixels. Nothing else warns you. |
| A job that would leave under 2 gigabytes free | A full disk mid-batch corrupts the file being written. |
| A truncated input | It produces a truncated output, and the engine does not always complain. |
| An incomplete model | Half a model gives an error message that is hard to trace back. |
| An image under 32 pixels on a side | A four-pixel-wide image resets the graphics device as reliably as an enormous one. |
| Transparency written out as a JPEG | The engine says it is converting the transparency away, then does not, and every transparent area arrives black. Use `png` or `webp`. |
| A PNG output over about 715 megapixels | The encoder sizes its buffer with 32-bit arithmetic and overflows past that, failing after the whole job has run. A bigger Mac does not help. |
| A models directory whose path lacks the word "models" | The engine checks for exactly that and refuses to start, with an error explaining nothing. |

The budgets are settings, not laws: `upscayl-wrap config --set
max_output_megapixels=800`.

Path comparisons are case-insensitive on macOS, because a Mac is normally
formatted that way and `~/Pictures/Out` and `~/pictures/out` are the same
folder. Comparing them as text would let a job escape its output folder by
changing one letter's case.

---

## Tile size, and why the default wastes your machine

The engine processes one tile of the image at a time, and its automatic choice
of tile size runs off a four-step ladder that stops at 200 pixels. Every step
above roughly two gigabytes of graphics memory takes the same top rung, so a
Mac with sixty-four gigabytes gets exactly the same tile as one with four.

So this wrapper picks a starting size from the machine's actual memory — 512
at thirty-two gigabytes and up — and walks it back down on its own if the
graphics processor complains, halving each time. Memory used scales roughly
with the square of the tile, so halving it roughly quarters the peak.

Two failures trigger that retry: `vkAllocateMemory failed`, which is running
out of graphics memory, and `vkQueueSubmit failed` or `vkWaitForFences
failed`, which is the graphics device being reset. Both are recorded, with
every attempt and its tile size, so `upscayl-wrap ledger` shows when a photo
needed two tries.

Set it by hand with `--tile 128` if you would rather not have it guess. Very
small tiles produce visible seams in flat areas, so the ladder stops at 32.

---

## The record

Every job appends one line to `~/.local/share/upscayl-wrap/ledger.jsonl`,
holding the input and its checksum, the exact command run, the prediction made
beforehand, the measured result, the score, and every gate check with its
verdict. Nothing in it is illustrative. If a row is there, it happened.

```bash
upscayl-wrap ledger --tail 20
upscayl-wrap report --last 100
cat ~/.local/share/upscayl-wrap/ledger.jsonl | jq 'select(.status=="failed")'
```

### The prediction, and why it is worth the trouble

Before each job the tool writes down the exact dimensions it expects, roughly
how many bytes, and roughly how long. Afterwards it compares.

The dimension prediction is the one that earns its keep. It is exact, so a
miss is never noise. An engine asked for 4x that quietly produces 2x leaves a
perfectly valid image file, and nothing about that file looks wrong — the
photo is just softer than it should be, and you find out months later. A
prediction written down beforehand turns that into a caught error.

Timing predictions start as a built-in guess and are replaced by this
machine's own measured history, so the tool tells you which one it is using
rather than presenting a guess and a measurement in the same voice.

### The comparison you would not otherwise make

Every tenth job also resamples the image the ordinary way, with no machine
learning, using the `sips` command built in to macOS. It records what that
cost. Over a few hundred jobs the record can answer the question that actually
matters: which photographs justify the model, and which may as well be
resampled.

### The review

```bash
upscayl-wrap review           # print it
upscayl-wrap review --write   # save it beside the ledger
```

Four headings: **right**, **wrong**, **could not have known** (a photo that
arrived corrupt is not the tool's mistake), and **will do differently**.

That last one is proposals only. The review never edits a setting. A tool that
tunes itself overnight is one whose behaviour nobody can predict in the
morning.

---

## When it goes wrong

Run `upscayl-wrap doctor` first. It checks every part and prints the fix for
whatever is broken, including the exact command to run.

| Symptom | Cause and fix |
| --- | --- |
| "engine was not found" | Upscayl is not installed, or is somewhere unusual. `upscayl-wrap doctor -v` lists every path searched. Set `UPSCAYL_BIN` to point at it directly. |
| The engine is found but nothing runs | macOS quarantine. Open Upscayl once from Finder, or `xattr -dr com.apple.quarantine /Applications/Upscayl.app`. |
| Crashes or runs out of memory on large photos | The tool already retries at half the tile size twice. To start lower, use `--tile 128`. |
| A result that is solid black | The graphics device failed mid-job. This is caught and reported as a failure rather than saved, so if you have a black file it came from somewhere else. |
| Everything refused at once | Probably halted. `upscayl-wrap stage` says so; `upscayl-wrap resume` clears it. |
| Failed jobs leave nothing to look at | They do. Partial outputs are kept in `~/.local/share/upscayl-wrap/quarantine` rather than deleted. |

A Vulkan-capable graphics processor is required. Vulkan is the graphics
programming interface the engine uses; on a Mac it runs through MoltenVK,
which translates it to Apple's Metal. Apple Silicon is supported natively.

---

## This part has to happen on the Mac

The upscaling itself is machine-bound and cannot move: it needs that
machine's graphics processor and the photo files on its disk. No amount of
design moves that to a phone.

Reading the results is not machine-bound, and does not have to happen there.
`upscayl-wrap report --compact` prints a single line built for a notification,
and every command takes `--json`.

---

## Layout

| File | What lives there |
| --- | --- |
| `upscaylwrap/gate.py` | The rules. Pure functions — no disk, no processes, no surprises. |
| `upscaylwrap/ledger.py` | The record. Append-only, one line per job. |
| `upscaylwrap/runner.py` | One job, start to finish, including proving it worked. |
| `upscaylwrap/scorer.py` | Predict before, score after. |
| `upscaylwrap/imageprobe.py` | Image headers, parsed with no third-party library. |
| `upscaylwrap/review.py` | The four-heading self-review. |
| `upscaylwrap/autonomy.py` | Stages and the halt. |
| `upscaylwrap/counterfactual.py` | The cheap alternative, measured. |
| `upscaylwrap/enginefaults.py` | The engine's known failure signatures, and the retry ladder. |
| `upscaylwrap/launchagent.py` | The scheduled sweep. |
| `upscaylwrap/cli.py` | The commands. |

## Tests

```bash
python3 tests/run_tests.py
```

No test framework to install. `tests/fake_upscayl.py` stands in for the real
engine and reproduces its genuine failure modes — success reported with no
output, a truncated file, quietly producing the wrong scale, and the valid
black image with a success banner — so the whole pipeline is testable on any
machine, with no graphics processor and no models.
