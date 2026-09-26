#!/usr/bin/env python3
"""Hub Kit importer: bring what you already have into your hub.

    python3 hub_import.py --from folder  --path ~/Notes        --level local
    python3 hub_import.py --from chatgpt --path conversations.json --level cloud --out import.sql
    python3 hub_import.py --from claude  --path conversations.json --level local --dry-run
    python3 hub_import.py --from csv     --path notes.csv      --level local

What it reads (only what you point it at; it never walks outside that path):
  folder   every .md and .txt file in the folder (one capture per file)
  chatgpt  the conversations.json from a ChatGPT data export
  claude   the conversations.json from a Claude data export
  csv      a file with a "text" column and optional "title", "when", "author"

Where it writes:
  --level local   into the Level 2 hub (hub_local.py, ~/.hub/hub.db or --db)
  --level cloud   an import.sql file of  select hub.capture(...)  calls you run
                  with psql; nothing is sent anywhere by this script

Every item lands as a raw capture: the words as they were, with a title,
a reference and the original date. The hub's own guard refuses anything
that looks like a secret; the count of refusals is reported, never the
values. Long conversations are split into parts under --chunk characters.
Facts are not invented from the text: an AI reads the captures afterwards
and writes facts with quotes, the way section 9 of the kit describes.

Standard library only. Python 3.8+. Nothing leaves your machine.
"""
import argparse, csv, datetime as dt, json, os, sys, pathlib

DEFAULT_CONFIG = {"level": "local", "author": "me", "surface": "import", "chunk_chars": 6000, "db": None}


def load_config(path):
    cfg = dict(DEFAULT_CONFIG)
    if path:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        cfg.update({k: v for k, v in data.get("import", {}).items() if k in cfg})
        if "level" in data and data["level"] in ("local", "cloud"):
            cfg["level"] = data["level"]
        if data.get("db"):
            cfg["db"] = data["db"]
    return cfg


def iso(ts):
    if ts is None:
        return dt.datetime.now(dt.timezone.utc).isoformat()
    if isinstance(ts, (int, float)):
        return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat()
    return str(ts)


def chunks(text, size):
    text = text.strip()
    if len(text) <= size:
        return [text]
    out, buf = [], ""
    for para in text.split("\n"):
        if len(buf) + len(para) + 1 > size and buf:
            out.append(buf.strip()); buf = ""
        buf += para + "\n"
    if buf.strip():
        out.append(buf.strip())
    return out


# --- readers: each yields dicts {title, text, when, ref} -------------------
def read_folder(path):
    root = pathlib.Path(path).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"not a folder: {root}")
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() not in (".md", ".txt") or not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        when = dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat()
        yield {"title": p.stem, "text": text, "when": when, "ref": f"file:{p.relative_to(root)}"}


def read_chatgpt(path):
    data = json.load(open(path, encoding="utf-8"))
    for conv in data:
        title = conv.get("title") or "untitled"
        msgs = []
        for node in (conv.get("mapping") or {}).values():
            m = node.get("message") if isinstance(node, dict) else None
            if not m:
                continue
            role = (m.get("author") or {}).get("role", "")
            parts = ((m.get("content") or {}).get("parts") or [])
            text = "\n".join(p for p in parts if isinstance(p, str)).strip()
            if text and role in ("user", "assistant"):
                msgs.append((m.get("create_time") or 0, role, text))
        msgs.sort(key=lambda x: x[0])
        if not msgs:
            continue
        body = "\n\n".join(f"{'Me' if r == 'user' else 'AI'}: {t}" for _, r, t in msgs)
        yield {"title": title, "text": body, "when": iso(conv.get("create_time")), "ref": f"chatgpt:{conv.get('id') or conv.get('conversation_id') or title}"}


def read_claude(path):
    data = json.load(open(path, encoding="utf-8"))
    for conv in data:
        title = conv.get("name") or "untitled"
        msgs = []
        for m in conv.get("chat_messages") or []:
            text = (m.get("text") or "").strip()
            if not text:
                text = "\n".join(c.get("text", "") for c in (m.get("content") or []) if isinstance(c, dict)).strip()
            if text:
                msgs.append((m.get("created_at") or "", m.get("sender", ""), text))
        msgs.sort(key=lambda x: x[0])
        if not msgs:
            continue
        body = "\n\n".join(f"{'Me' if s == 'human' else 'AI'}: {t}" for _, s, t in msgs)
        yield {"title": title, "text": body, "when": iso(conv.get("created_at")), "ref": f"claude:{conv.get('uuid') or title}"}


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), 1):
            text = (row.get("text") or "").strip()
            if not text:
                continue
            yield {"title": row.get("title") or f"row {i}", "text": text, "when": iso(row.get("when") or None), "ref": f"csv:{i}"}


READERS = {"folder": read_folder, "chatgpt": read_chatgpt, "claude": read_claude, "csv": read_csv}


# --- writers ---------------------------------------------------------------
def sql_literal(s):
    tag = "$hk$"
    while tag in s:
        tag = tag[:-1] + "x$"
    return f"{tag}{s}{tag}"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hub_import.py", description="Bring notes and chat exports into your hub.")
    ap.add_argument("--from", dest="kind", required=True, choices=sorted(READERS))
    ap.add_argument("--path", required=True)
    ap.add_argument("--level", choices=["local", "cloud"])
    ap.add_argument("--config", help="hub.config.json (see hub.config.example.json)")
    ap.add_argument("--out", default="import.sql", help="cloud: the SQL file to write")
    ap.add_argument("--db", help="local: the hub database (default from config, else hub_local.py's default)")
    ap.add_argument("--chunk", type=int, help="split items longer than this many characters")
    ap.add_argument("--author", help="who wrote these words (default me)")
    ap.add_argument("--dry-run", action="store_true", help="count and show titles; write nothing")
    a = ap.parse_args(argv)

    cfg = load_config(a.config)
    level = a.level or cfg["level"]
    chunk = a.chunk or int(cfg["chunk_chars"])
    author = a.author or cfg["author"]
    surface = cfg["surface"]

    items = []
    for it in READERS[a.kind](a.path):
        parts = chunks(it["text"], chunk)
        for k, part in enumerate(parts, 1):
            title = it["title"] if len(parts) == 1 else f"{it['title']} (part {k}/{len(parts)})"
            items.append({"title": title, "text": part, "when": it["when"], "ref": it["ref"] if len(parts) == 1 else f"{it['ref']}#{k}"})
    if not items:
        print("nothing to import"); return 1
    if a.dry_run:
        print(f"{len(items)} capture(s) would be written ({level}):")
        for it in items[:40]:
            print(f"  - {it['title']} · {len(it['text']):,} chars · {it['when'][:10]}")
        if len(items) > 40:
            print(f"  … and {len(items) - 40} more")
        return 0

    if level == "cloud":
        lines = ["-- hub_import.py · run with: psql \"$DATABASE_URL\" -f " + a.out,
                 "-- each line is one capture; the hub refuses any that carries a secret (the statement fails, the rest continue with ON_ERROR_STOP off)",
                 "\\set ON_ERROR_STOP off", "set client_min_messages = warning;"]
        for it in items:
            lines.append("select hub.capture(%s, %s, %s, %s::timestamptz, %s, %s);" % (
                sql_literal(it["text"]), sql_literal(surface), sql_literal(author), sql_literal(it["when"]), sql_literal(it["ref"]), sql_literal(it["title"])))
        pathlib.Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {a.out}: {len(items)} capture(s). Read it, then run it with psql. Nothing was sent.")
        return 0

    # local: import the Level 2 hub from the same folder
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    try:
        import hub_local
    except ImportError:
        raise SystemExit("hub_local.py must sit next to hub_import.py for --level local")
    db = a.db or cfg["db"] or os.environ.get("HUB_DB") or hub_local.DEFAULT_DB
    h = hub_local.Hub(db)
    if not h.db.execute("select 1 from sqlite_master where name='facts'").fetchone():
        raise SystemExit("no hub here yet: run  python3 hub_local.py init  first")
    done = dup = refused = 0
    for it in items:
        try:
            _, outcome = h.capture(it["text"], surface, author, it["title"], it["ref"], it["when"], "export")
            if outcome == "captured":
                done += 1
            else:
                dup += 1
        except hub_local.Refused:
            refused += 1
    h.db.commit()
    print(f"imported {done} capture(s) · {dup} already there · {refused} refused by the guard (they looked like they carried a secret; nothing was stored)")
    print("next: in a chat, say \"hub\" then \"what's on the record about <a topic>?\" — an AI writes facts from these captures with quotes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
