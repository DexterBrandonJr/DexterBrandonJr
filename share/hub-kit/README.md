# Hub Kit

Give **`HUB-KIT.md`** to any AI (ChatGPT, Claude, Gemini, Copilot, a local
model) and say **"Run the Hub Kit."** It installs one private memory that
every AI you use reads first and writes back to last, and it teaches you
what you're building as it goes. It asks before anything is installed or
signed up for, never asks for a password, and checks its own work.

| File | What it is |
|---|---|
| `HUB-KIT.md` | The installer. One file, written for the AI; the tested code is inside it. |
| `hub-kit.html` | The same thing as a page for people: what it does, copy and save buttons, the full installer text. |
| `hub-kit.sql` | Level 3 (cloud): a PostgreSQL schema named `hub`. Supabase free tier is enough. |
| `hub_local.py` | Level 2 (local): one Python file, standard library only, one private SQLite file. |
| `hub_import.py` | The importer: a folder of notes, a ChatGPT or Claude export, or a CSV, into the local hub or into an SQL file for the cloud one. Reads only the path it is given, sends nothing. |
| `hub.config.example.json` | Settings for the importer and the level; copy to `hub.config.json`. Never holds a secret. |
| `src/protocol.md` | The installer's source text. |
| `src/build.py` | Builds `HUB-KIT.md` and `hub-kit.html` from the source and the two code files, and prints their fingerprints. |

## Three levels

- **Paper:** a `HUB.md` file any AI can read. No signup, no code.
- **Local:** `hub_local.py` on your computer, for AIs that can run commands.
- **Cloud:** `hub-kit.sql` in a Supabase project, reached through a connector
  by every AI on every device.

## Check it yourself

```sh
python3 hub_local.py selftest                          # SELFTEST OK · 24 checks passed
psql "$DATABASE_URL" -f hub-kit.sql                    # into an empty database or project
psql "$DATABASE_URL" -c "select hub.selftest();"      # SELFTEST OK · 24 checks passed
psql "$DATABASE_URL" -c "select * from hub.audit();"  # no rows
sha256sum hub-kit.sql hub_local.py hub_import.py       # must match the fingerprints in HUB-KIT.md
python3 hub_import.py --from folder --path ~/Notes --dry-run   # counts, writes nothing
```

Neither code file makes a network call, reads other files, or changes
anything outside its own schema or its own folder (`~/.hub`). Read them
before you run them; that is the check a tampered copy cannot fake.

## Rebuild after an edit

```sh
python3 src/build.py
```

Free to use, share and adapt.
