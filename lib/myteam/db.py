"""`myteam db` — searchable, updatable team databases (experts, contacts, vendors ...).

One SQLite file, ~/myteam/data/team.db, stdlib only. A *table* holds records
whose fields are free-form (whatever columns the agent found). Each record has
a stable identity built from key fields (OpenAlex/ORCID/email/homepage, else
name + organization), so adding the same person again UPDATES them instead of
creating a duplicate. Every change is logged with who made it; every fact can
carry its source URL; `last verified` dates drive re-checking. Full-text search
over all fields. CSV/JSON are for import and export only.

Rules baked in (same as the rest of MyTeam): agents add/update/mark; only the
boss removes records.
"""
import csv
import io
import json
import re
import sqlite3
import sys
import time

from . import config

DB = config.STATE / "data" / "team.db"
STATUSES = ("active", "moved", "retired", "duplicate", "removed")
SOURCE_FIELDS = ("source", "sources", "source_url", "source_urls", "url_source", "ref", "refs")
ORG_FIELDS = ("affiliation", "organization", "organisation", "institution", "company", "org",
              "employer", "university")
DEFAULT_KEYS = ["openalex_id", "orcid", "email", "homepage", "website", "linkedin", "url"]

USAGE = """\
myteam db — the team's searchable, updatable tables (stored in ~/myteam/data/team.db)

  myteam db                                    list tables
  myteam db new <table> ["what it holds"] [--keys orcid,email]
  myteam db add <table> --from rows.csv|rows.json [--source URL]
  myteam db add <table> name="Jane Doe" affiliation=MIT expertise="RL; robotics" source=https://...
  myteam db search <table> "words" [--where field=value] [-n 20] [--fields a,b] [--json|--csv] [--all]
  myteam db show <table> <id|name>             one record, its sources and change history
  myteam db set <table> <id> field=value ...   edit fields (field= clears it; status=moved|retired|duplicate|active)
  myteam db verify <table> <id> [--source URL] mark as re-checked today
  myteam db stale <table> [--days 180]         records not verified recently
  myteam db history <table> [id] [-n 30]       who changed what
  myteam db export <table> [file.csv|-]        default: ~/myteam/deliverables/data/<table>.csv
  myteam db remove <table> <id> ["why"]        boss only (agents: set status=duplicate or file a request)
  myteam db sql "SELECT ..."                   read-only SQL for anything else

Adding a record that already exists (same key) updates it; empty values never erase data.
"""


# ───────────────────────── storage ─────────────────────────

def connect(path=None):
    path = path or DB
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=20000")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS tables (
        name TEXT PRIMARY KEY, description TEXT DEFAULT '', keys TEXT DEFAULT '[]',
        columns TEXT DEFAULT '[]', created TEXT, updated TEXT);
    CREATE TABLE IF NOT EXISTS records (
        tbl TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'active', sources TEXT NOT NULL DEFAULT '[]',
        created TEXT, updated TEXT, verified TEXT, PRIMARY KEY (tbl, id));
    CREATE TABLE IF NOT EXISTS aliases (
        tbl TEXT NOT NULL, alias TEXT NOT NULL, id TEXT NOT NULL, PRIMARY KEY (tbl, alias));
    CREATE TABLE IF NOT EXISTS changes (
        ts TEXT, tbl TEXT, id TEXT, by TEXT, action TEXT, detail TEXT);
    CREATE INDEX IF NOT EXISTS changes_rec ON changes (tbl, id);
    CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(
        body, tokenize='unicode61 remove_diacritics 2');
    """)
    return con


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _by():
    import os
    who = os.environ.get("MYTEAM_SESSION") or os.environ.get("MYTEAM_MEMBER") or "owner"
    from . import sessions
    return who[len(sessions.PREFIX):] if who.startswith(sessions.PREFIX) else who


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def table_slug(name):
    t = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")
    if not t:
        raise SystemExit("bad table name '{}'".format(name))
    return t


def field_name(k):
    return re.sub(r"[^a-z0-9]+", "_", str(k).strip().lower()).strip("_")


def _norm_value(field, v):
    v = str(v).strip().lower()
    v = re.sub(r"^https?://", "", v)
    v = re.sub(r"^www\.", "", v).rstrip("/")
    if field == "orcid":
        m = re.search(r"\d{4}-\d{4}-\d{4}-\d{3}[\dx]", v)
        v = m.group(0) if m else v
    elif field == "openalex_id":
        m = re.search(r"a\d{6,}", v)
        v = m.group(0) if m else v
    return v


def _get_table(con, name, create=True, description="", keys=None):
    t = table_slug(name)
    row = con.execute("SELECT * FROM tables WHERE name=?", (t,)).fetchone()
    if row is None:
        if not create:
            raise SystemExit("no table '{}' — `myteam db` lists them".format(t))
        con.execute("INSERT INTO tables (name, description, keys, columns, created, updated) "
                    "VALUES (?,?,?,?,?,?)",
                    (t, description, json.dumps(keys or DEFAULT_KEYS), "[]", _now(), _now()))
        row = con.execute("SELECT * FROM tables WHERE name=?", (t,)).fetchone()
    return row


def _keys(trow):
    return json.loads(trow["keys"] or "[]") or DEFAULT_KEYS


def _columns(trow):
    return json.loads(trow["columns"] or "[]")


# ───────────────────────── identity ─────────────────────────

def _aliases(keys, data):
    """All identity strings for a record, strongest first."""
    out = []
    for k in keys:
        if data.get(k):
            out.append("{}:{}".format(k, _norm_value(k, data[k])))
    name = data.get("name") or data.get("full_name")
    if name:
        org = next((data[f] for f in ORG_FIELDS if data.get(f)), "")
        out.append("name:" + _slug(name) + ("@" + _slug(org) if org else ""))
    return out


def _new_id(aliases, data):
    if aliases:
        a = aliases[0]
        kind, val = a.split(":", 1)
        return val if kind in ("id", "name") else "{}:{}".format(kind, val)
    blob = json.dumps(data, sort_keys=True, ensure_ascii=False)
    import hashlib
    return "rec-" + hashlib.sha1(blob.encode()).hexdigest()[:10]


def _find(con, tbl, aliases):
    hits = []
    for a in aliases:
        r = con.execute("SELECT id FROM aliases WHERE tbl=? AND alias=?", (tbl, a)).fetchone()
        if r and r["id"] not in hits:
            hits.append(r["id"])
    return hits


def _resolve(con, tbl, token):
    """id, alias, or a name → record id."""
    r = con.execute("SELECT id FROM records WHERE tbl=? AND id=?", (tbl, token)).fetchone()
    if r:
        return r["id"]
    low = token.strip().lower()
    for a in (low, "name:" + _slug(token)):
        r = con.execute("SELECT id FROM aliases WHERE tbl=? AND alias=?", (tbl, a)).fetchone()
        if r:
            return r["id"]
    rows = con.execute("SELECT id FROM aliases WHERE tbl=? AND (alias LIKE ? OR alias LIKE ?)",
                       (tbl, "%:" + _norm_value("", token),
                        "name:" + _slug(token) + "%")).fetchall()
    ids = sorted({x["id"] for x in rows})
    if len(ids) == 1:
        return ids[0]
    if len(ids) > 1:
        raise SystemExit("'{}' matches several records: {}".format(token, ", ".join(ids[:8])))
    raise SystemExit("no record '{}' in {} (try `myteam db search {} \"{}\"`)".format(
        token, tbl, tbl, token))


# ───────────────────────── writing ─────────────────────────

def _split_sources(v):
    return [s for s in re.split(r"[\s;|,]+", str(v or "")) if s]


def _clean_row(raw):
    data, srcs, status = {}, [], None
    for k, v in raw.items():
        if k is None:
            continue
        f = field_name(k)
        if not f:
            continue
        if isinstance(v, (list, tuple)):
            v = "; ".join(str(x) for x in v if x not in (None, ""))
        elif isinstance(v, dict):
            v = json.dumps(v, ensure_ascii=False)
        v = "" if v is None else str(v).strip()
        if f == "id":
            data["\0id"] = v
        elif f in SOURCE_FIELDS:
            srcs += _split_sources(v)
        elif f == "status":
            status = v.lower() or None
        else:
            data[f] = v
    return data, srcs, status


def _reindex(con, tbl, rid):
    r = con.execute("SELECT rowid, data FROM records WHERE tbl=? AND id=?", (tbl, rid)).fetchone()
    con.execute("DELETE FROM search WHERE rowid=?", (r["rowid"],))
    body = " ".join([rid] + [v for v in json.loads(r["data"]).values() if v])
    con.execute("INSERT INTO search (rowid, body) VALUES (?,?)", (r["rowid"], body))


def _log(con, tbl, rid, action, detail, by):
    con.execute("INSERT INTO changes VALUES (?,?,?,?,?,?)",
                (_now(), tbl, rid, by, action,
                 json.dumps(detail, ensure_ascii=False) if not isinstance(detail, str) else detail))


def _set_aliases(con, tbl, rid, aliases):
    for a in aliases:
        con.execute("INSERT OR IGNORE INTO aliases VALUES (?,?,?)", (tbl, a, rid))


def _check_status(status, by):
    if status and status not in STATUSES:
        raise SystemExit("status must be one of: " + ", ".join(STATUSES))
    if status == "removed" and by != "owner":
        raise SystemExit("only the boss removes records — set status=duplicate, or "
                         "`myteam request other \"remove ... from db\"`")


def upsert(con, table, raw, source=None, by=None, verify=True):
    """Insert or update one record. Returns (action, id, note)."""
    by = by or _by()
    trow = _get_table(con, table)
    tbl = trow["name"]
    data, srcs, status = _clean_row(raw)
    _check_status(status, by)
    if source:
        srcs += [s for s in _split_sources(source) if s not in srcs]
    explicit = _slug(data.pop("\0id", ""))
    data = {k: v for k, v in data.items() if v != ""}
    if not data:
        return "skipped", None, "empty row"
    aliases = _aliases(_keys(trow), data)
    if explicit:   # the caller named the record: match on that id only
        hits = [explicit] if con.execute("SELECT 1 FROM records WHERE tbl=? AND id=?",
                                         (tbl, explicit)).fetchone() else []
    else:
        hits = _find(con, tbl, aliases)
    note = ""
    if len(hits) > 1:
        note = "possible duplicate of {}".format(", ".join(hits[1:]))
    now = _now()
    if not hits:
        rid = explicit or _new_id(aliases, data)
        n, base = 2, rid
        while con.execute("SELECT 1 FROM records WHERE tbl=? AND id=?", (tbl, rid)).fetchone():
            rid, n = "{}-{}".format(base, n), n + 1
        con.execute("INSERT INTO records (tbl,id,data,status,sources,created,updated,verified) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (tbl, rid, json.dumps(data, ensure_ascii=False), status or "active",
                     json.dumps(srcs), now, now, now if verify else None))
        _set_aliases(con, tbl, rid, aliases)
        _reindex(con, tbl, rid)
        _log(con, tbl, rid, "add", {"fields": sorted(data), "sources": srcs}, by)
        action = "new"
    else:
        rid = hits[0]
        r = con.execute("SELECT * FROM records WHERE tbl=? AND id=?", (tbl, rid)).fetchone()
        old = json.loads(r["data"])
        oldsrc = json.loads(r["sources"])
        diff, conflicts = {}, []
        for k in _keys(trow):   # a different ID value is suspicious: keep the old one, flag it
            if old.get(k) and data.get(k) and _norm_value(k, old[k]) != _norm_value(k, data[k]):
                conflicts.append("{} {} vs {}".format(k, old[k], data.pop(k)))
        if conflicts:
            note = "; ".join(filter(None, [note, "kept existing " + ", ".join(conflicts)
                                           + " — same person? check, or add as its own record "
                                           "with id=..."]))
        if old.get("name") and data.get("name") and _slug(old["name"]) != _slug(data["name"]):
            other = [x.strip() for x in old.get("other_names", "").split(";") if x.strip()]
            if data["name"] not in other:   # keep the first name; remember variants
                data["other_names"] = "; ".join(other + [data["name"]])
            del data["name"]
        for k, v in data.items():
            if old.get(k, "") != v:
                diff[k] = [old.get(k, ""), v]
                old[k] = v
        newsrc = oldsrc + [s for s in srcs if s not in oldsrc]
        st = status or r["status"]
        if st != r["status"]:
            diff["status"] = [r["status"], st]
        if diff or newsrc != oldsrc:
            con.execute("UPDATE records SET data=?, sources=?, status=?, updated=?, "
                        "verified=COALESCE(?, verified) WHERE tbl=? AND id=?",
                        (json.dumps(old, ensure_ascii=False), json.dumps(newsrc), st, now,
                         now if verify else None, tbl, rid))
            _set_aliases(con, tbl, rid, _aliases(_keys(trow), old))
            _reindex(con, tbl, rid)
            if newsrc != oldsrc:
                diff["+sources"] = [s for s in newsrc if s not in oldsrc]
            _log(con, tbl, rid, "update", diff, by)
            action = "updated"
        else:
            if verify:
                con.execute("UPDATE records SET verified=? WHERE tbl=? AND id=?", (now, tbl, rid))
            action = "unchanged"
    cols = _columns(trow)
    added = [k for k in data if k not in cols]
    if added or action != "unchanged":
        con.execute("UPDATE tables SET columns=?, updated=? WHERE name=?",
                    (json.dumps(cols + added), now, tbl))
    return action, rid, note


def read_rows(path):
    """Rows from .csv/.tsv/.json/.jsonl (or '-' = stdin, format sniffed)."""
    if path == "-":
        text, ext = sys.stdin.read(), ""
    else:
        from pathlib import Path
        p = Path(path).expanduser()
        if not p.exists():
            raise SystemExit("no file " + path)
        text, ext = p.read_text(encoding="utf-8-sig"), p.suffix.lower()
    s = text.lstrip()
    if ext in (".json", ".jsonl") or s[:1] in "[{":
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                obj = obj.get("rows") or obj.get("records") or obj.get("data") or [obj]
            return [r for r in obj if isinstance(r, dict)]
        except ValueError:
            return [json.loads(l) for l in s.splitlines() if l.strip()]
    delim = "\t" if ext == ".tsv" else None
    if delim is None:
        try:
            delim = csv.Sniffer().sniff(s[:4096], delimiters=",\t;").delimiter
        except csv.Error:
            delim = ","
    return list(csv.DictReader(io.StringIO(s), delimiter=delim))


def _kv(args):
    out = {}
    for a in args:
        if "=" not in a:
            raise SystemExit("expected field=value, got '{}'".format(a))
        k, v = a.split("=", 1)
        out[k] = v
    return out


# ───────────────────────── reading ─────────────────────────

def _fts_query(q, mode):
    toks = re.findall(r"\w+", q, re.U)
    if not toks:
        return None
    return (" OR " if mode == "or" else " ").join('"{}"*'.format(t) for t in toks)


def search(con, table, q="", where=None, limit=20, include_all=False):
    tbl = _get_table(con, table, create=False)["name"]
    rows = []
    if q.strip():
        for mode in ("and", "or"):
            fq = _fts_query(q, mode)
            if not fq:
                break
            try:
                rows = con.execute(
                    "SELECT r.*, bm25(search) AS score FROM search JOIN records r "
                    "ON r.rowid = search.rowid WHERE search MATCH ? AND r.tbl=? "
                    "ORDER BY score LIMIT ?", (fq, tbl, max(limit * 5, 200))).fetchall()
            except sqlite3.OperationalError:
                rows = []
            if rows:
                break
        if not rows:   # CJK, partial words, punctuation — plain substring fallback
            terms = [t.lower() for t in q.split()]
            for r in con.execute("SELECT r.*, 0 AS score FROM records r WHERE tbl=?", (tbl,)):
                hay = (r["id"] + " " + r["data"]).lower()
                if all(t in hay for t in terms):
                    rows.append(r)
    else:
        rows = con.execute("SELECT r.*, 0 AS score FROM records r WHERE tbl=? "
                           "ORDER BY updated DESC", (tbl,)).fetchall()
    out = []
    for r in rows:
        if not include_all and r["status"] == "removed":
            continue
        d = json.loads(r["data"])
        ok = True
        for f, v in (where or {}).items():
            f = field_name(f)
            have = r["status"] if f == "status" else d.get(f, "")
            if v.lower() not in str(have).lower():
                ok = False
                break
        if ok:
            out.append(_record(r))
        if len(out) >= limit:
            break
    return out


def _record(r):
    return {"id": r["id"], "status": r["status"], **json.loads(r["data"]),
            "sources": json.loads(r["sources"]), "updated": r["updated"],
            "verified": r["verified"]}


def _display_cols(cols, recs, want=None):
    if want:
        return [field_name(c) for c in want.split(",") if c.strip()]
    pref = [c for c in ("name", "title", "affiliation", "organization", "company",
                        "expertise", "role", "email", "country") if c in cols]
    rest = [c for c in cols if c not in pref]
    return (pref + rest)[:5]


def _short(v, w):
    v = str(v if v is not None else "").replace("\n", " ")
    return v if len(v) <= w else v[:w - 1] + "…"


def print_table(recs, cols):
    if not recs:
        print("no matches")
        return
    widths = {"id": min(28, max(len(r["id"]) for r in recs))}
    for c in cols:
        widths[c] = min(34, max([len(c)] + [len(str(r.get(c, ""))) for r in recs]))
    head = ["id"] + cols
    print("  ".join(h.ljust(widths[h]) for h in head))
    print("  ".join("─" * widths[h] for h in head))
    for r in recs:
        flag = "" if r["status"] == "active" else " [{}]".format(r["status"])
        print("  ".join(_short(r.get(h, "") if h != "id" else r["id"] + flag,
                               widths[h]).ljust(widths[h]) for h in head))
    print("({} record{})".format(len(recs), "" if len(recs) == 1 else "s"))


def write_csv(recs, cols, fh):
    head = ["id", "status"] + cols + ["sources", "updated", "verified"]
    w = csv.DictWriter(fh, fieldnames=head, extrasaction="ignore")
    w.writeheader()
    for r in recs:
        row = dict(r)
        row["sources"] = "; ".join(r.get("sources") or [])
        w.writerow(row)


# ───────────────────────── CLI ─────────────────────────

def _opts(args, valued=(), flags=()):
    pos, opt, i = [], {}, 0
    while i < len(args):
        a = args[i]
        name = a.lstrip("-")
        if a.startswith("-") and name in valued and i + 1 < len(args):
            opt.setdefault(name, []).append(args[i + 1])
            i += 2
            continue
        if a.startswith("-") and name in flags:
            opt[name] = True
            i += 1
            continue
        pos.append(a)
        i += 1
    return pos, opt


def main(args):
    if not args or args[0] in ("list", "ls", "tables"):
        if args and args[0] in ("-h", "--help", "help"):
            print(USAGE)
            return 0
        return cmd_list()
    cmd, rest = args[0], args[1:]
    if cmd in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    con = connect()
    try:
        with con:
            return _dispatch(con, cmd, rest)
    finally:
        con.close()


def cmd_list():
    if not DB.exists():
        print("no tables yet — the first `myteam db add <table> ...` creates one\n")
        print(USAGE)
        return 0
    con = connect()
    rows = con.execute(
        "SELECT t.name, t.description, t.updated, "
        "(SELECT COUNT(*) FROM records r WHERE r.tbl=t.name AND r.status!='removed') AS n "
        "FROM tables t ORDER BY t.name").fetchall()
    if not rows:
        print("no tables yet — `myteam db add <table> ...` creates one")
    for r in rows:
        print("  {:<20} {:>6} records   updated {}   {}".format(
            r["name"], r["n"], (r["updated"] or "")[:10], r["description"] or ""))
    print("\n{}   (`myteam db help` for commands)".format(DB))
    return 0


def _need(rest, n, usage):
    if len(rest) < n:
        raise SystemExit("usage: myteam db " + usage)


def _dispatch(con, cmd, rest):
    if cmd == "new":
        pos, o = _opts(rest, valued=("keys",))
        _need(pos, 1, 'new <table> ["what it holds"] [--keys orcid,email]')
        t = table_slug(pos[0])
        if con.execute("SELECT 1 FROM tables WHERE name=?", (t,)).fetchone():
            print("= table {} already exists".format(t))
            return 0
        keys = [field_name(k) for k in o["keys"][0].split(",")] if o.get("keys") else None
        _get_table(con, t, description=" ".join(pos[1:]), keys=keys)
        print("✓ table {} — identity keys: {} (else name + organization)".format(
            t, ", ".join(keys or DEFAULT_KEYS)))
        return 0

    if cmd == "add":
        pos, o = _opts(rest, valued=("from", "source"))
        _need(pos, 1, "add <table> --from rows.csv | field=value ...")
        source = (o.get("source") or [None])[0]
        rows = []
        for f in o.get("from", []):
            rows += read_rows(f)
        if pos[1:]:
            rows.append(_kv(pos[1:]))
        if not rows:
            raise SystemExit("nothing to add — give --from file.csv or field=value pairs")
        counts, notes = {"new": 0, "updated": 0, "unchanged": 0, "skipped": 0}, []
        for raw in rows:
            action, rid, note = upsert(con, pos[0], raw, source=source)
            counts[action] += 1
            if note:
                notes.append("{}: {}".format(rid or "?", note))
            if len(rows) == 1 and rid:
                print("{} {}".format({"new": "✓ added", "updated": "✓ updated",
                                      "unchanged": "= unchanged"}[action], rid))
        if len(rows) > 1:
            print("{}: {new} new, {updated} updated, {unchanged} unchanged{sk}".format(
                table_slug(pos[0]), sk=", {} skipped (empty)".format(counts["skipped"])
                if counts["skipped"] else "", **counts))
        for n in notes[:20]:
            print("  ! " + n)
        if notes:
            print("  (check those and `myteam db set <table> <id> status=duplicate` if so)")
        return 0

    if cmd in ("search", "find", "s"):
        pos, o = _opts(rest, valued=("where", "n", "fields", "limit"),
                       flags=("json", "csv", "all"))
        _need(pos, 1, 'search <table> "words" [--where field=value] [-n 20]')
        where = _kv(o.get("where", []))
        limit = int((o.get("n") or o.get("limit") or ["20"])[0])
        recs = search(con, pos[0], " ".join(pos[1:]), where, limit, bool(o.get("all")))
        trow = _get_table(con, pos[0], create=False)
        cols = _display_cols(_columns(trow), recs, (o.get("fields") or [None])[0])
        if o.get("json"):
            print(json.dumps(recs, ensure_ascii=False, indent=1))
        elif o.get("csv"):
            write_csv(recs, _columns(trow), sys.stdout)
        else:
            print_table(recs, cols)
        return 0

    if cmd in ("show", "get"):
        _need(rest, 2, "show <table> <id|name>")
        tbl = _get_table(con, rest[0], create=False)["name"]
        rid = _resolve(con, tbl, " ".join(rest[1:]))
        r = con.execute("SELECT * FROM records WHERE tbl=? AND id=?", (tbl, rid)).fetchone()
        rec = _record(r)
        print("{} / {}   [{}]".format(tbl, rid, rec["status"]))
        for k, v in json.loads(r["data"]).items():
            print("  {:<16} {}".format(k, v))
        print("  {:<16} {}".format("sources", "\n                   ".join(rec["sources"]) or "—"))
        print("  {:<16} added {} · updated {} · verified {}".format(
            "dates", (r["created"] or "")[:10], (r["updated"] or "")[:10],
            (r["verified"] or "never")[:10]))
        hist = con.execute("SELECT * FROM changes WHERE tbl=? AND id=? ORDER BY ts DESC LIMIT 8",
                           (tbl, rid)).fetchall()
        if hist:
            print("  history:")
            for h in hist:
                print("    {} {:<10} {:<8} {}".format(h["ts"][:16], h["by"], h["action"],
                                                    _short(h["detail"], 90)))
        return 0

    if cmd in ("set", "update", "edit"):
        _need(rest, 3, "set <table> <id> field=value ...")
        tbl = _get_table(con, rest[0], create=False)["name"]
        rid = _resolve(con, tbl, rest[1])
        kv = _kv(rest[2:])
        by = _by()
        r = con.execute("SELECT * FROM records WHERE tbl=? AND id=?", (tbl, rid)).fetchone()
        data, srcs = json.loads(r["data"]), json.loads(r["sources"])
        diff, status = {}, r["status"]
        for k, v in kv.items():
            f = field_name(k)
            if f == "status":
                _check_status(v.lower(), by)
                if v.lower() != status:
                    diff["status"] = [status, v.lower()]
                    status = v.lower()
            elif f in SOURCE_FIELDS:
                add = [s for s in _split_sources(v) if s not in srcs]
                if add:
                    srcs += add
                    diff["+sources"] = add
            elif v == "":
                if f in data:
                    diff[f] = [data.pop(f), ""]
            elif data.get(f) != v:
                diff[f] = [data.get(f, ""), v]
                data[f] = v
        if not diff:
            print("= no change")
            return 0
        con.execute("UPDATE records SET data=?, sources=?, status=?, updated=? "
                    "WHERE tbl=? AND id=?",
                    (json.dumps(data, ensure_ascii=False), json.dumps(srcs), status, _now(),
                     tbl, rid))
        trow = _get_table(con, tbl)
        cols = _columns(trow)
        _set_aliases(con, tbl, rid, _aliases(_keys(trow), data))
        con.execute("UPDATE tables SET columns=?, updated=? WHERE name=?",
                    (json.dumps(cols + [k for k in data if k not in cols]), _now(), tbl))
        _reindex(con, tbl, rid)
        _log(con, tbl, rid, "set", diff, by)
        print("✓ {} updated: {}".format(rid, ", ".join(diff)))
        return 0

    if cmd == "verify":
        pos, o = _opts(rest, valued=("source",))
        _need(pos, 2, "verify <table> <id> [--source URL]")
        tbl = _get_table(con, pos[0], create=False)["name"]
        rid = _resolve(con, tbl, " ".join(pos[1:]))
        r = con.execute("SELECT sources FROM records WHERE tbl=? AND id=?", (tbl, rid)).fetchone()
        srcs = json.loads(r["sources"])
        add = [s for s in _split_sources((o.get("source") or [""])[0]) if s not in srcs]
        con.execute("UPDATE records SET verified=?, sources=? WHERE tbl=? AND id=?",
                    (_now(), json.dumps(srcs + add), tbl, rid))
        _log(con, tbl, rid, "verify", {"+sources": add} if add else "", _by())
        print("✓ {} verified today".format(rid))
        return 0

    if cmd == "stale":
        pos, o = _opts(rest, valued=("days", "n"))
        _need(pos, 1, "stale <table> [--days 180]")
        tbl = _get_table(con, pos[0], create=False)["name"]
        days = int((o.get("days") or ["180"])[0])
        cutoff = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - days * 86400))
        rows = con.execute("SELECT * FROM records WHERE tbl=? AND status NOT IN "
                           "('removed','duplicate') AND (verified IS NULL OR verified < ?) "
                           "ORDER BY verified LIMIT ?",
                           (tbl, cutoff, int((o.get("n") or ["50"])[0]))).fetchall()
        recs = [_record(r) for r in rows]
        print_table(recs, _display_cols(_columns(_get_table(con, tbl)), recs)[:3] + ["verified"])
        if recs:
            print("re-check each, then `myteam db set ...` / `myteam db verify {} <id> --source URL`"
                  .format(tbl))
        return 0

    if cmd in ("history", "log"):
        pos, o = _opts(rest, valued=("n",))
        _need(pos, 1, "history <table> [id] [-n 30]")
        tbl = _get_table(con, pos[0], create=False)["name"]
        n = int((o.get("n") or ["30"])[0])
        if len(pos) > 1:
            rid = _resolve(con, tbl, " ".join(pos[1:]))
            rows = con.execute("SELECT * FROM changes WHERE tbl=? AND id=? ORDER BY ts DESC "
                               "LIMIT ?", (tbl, rid, n)).fetchall()
        else:
            rows = con.execute("SELECT * FROM changes WHERE tbl=? ORDER BY ts DESC LIMIT ?",
                               (tbl, n)).fetchall()
        for h in reversed(rows):
            print("{} {:<10} {:<7} {:<26} {}".format(h["ts"][:16], h["by"], h["action"],
                                                     _short(h["id"], 26), _short(h["detail"], 80)))
        if not rows:
            print("no changes logged")
        return 0

    if cmd == "export":
        pos, o = _opts(rest, flags=("all",))
        _need(pos, 1, "export <table> [file.csv|-]")
        trow = _get_table(con, pos[0], create=False)
        tbl = trow["name"]
        rows = con.execute("SELECT * FROM records WHERE tbl=? ORDER BY id", (tbl,)).fetchall()
        recs = [_record(r) for r in rows if o.get("all") or r["status"] != "removed"]
        if len(pos) > 1 and pos[1] == "-":
            write_csv(recs, _columns(trow), sys.stdout)
            return 0
        from pathlib import Path
        dest = Path(pos[1]).expanduser() if len(pos) > 1 else \
            config.STATE / "deliverables" / "data" / "{}.csv".format(tbl)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", newline="", encoding="utf-8-sig") as fh:   # BOM: Excel opens UTF-8
            write_csv(recs, _columns(trow), fh)
        print("✓ {} records → {}".format(len(recs), dest))
        return 0

    if cmd in ("remove", "rm", "delete"):
        _need(rest, 2, 'remove <table> <id> ["why"]')
        if _by() != "owner":
            raise SystemExit("only the boss removes records — set status=duplicate|retired, or "
                             "`myteam request other \"remove <id> from <table>: why\"`")
        tbl = _get_table(con, rest[0], create=False)["name"]
        rid = _resolve(con, tbl, rest[1])
        con.execute("UPDATE records SET status='removed', updated=? WHERE tbl=? AND id=?",
                    (_now(), tbl, rid))
        _log(con, tbl, rid, "remove", " ".join(rest[2:]), "owner")
        print("✓ {} removed (hidden from search; `set {} {} status=active` restores it)".format(
            rid, tbl, rid))
        return 0

    if cmd == "sql":
        _need(rest, 1, 'sql "SELECT ..."')
        q = " ".join(rest)
        if not re.match(r"^\s*(select|with|pragma\s+table_info)\b", q, re.I):
            raise SystemExit("read-only: SELECT / WITH queries only")
        ro = sqlite3.connect("file:{}?mode=ro".format(DB), uri=True)
        try:
            cur = ro.execute(q)
            head = [d[0] for d in cur.description or []]
            w = csv.writer(sys.stdout)
            w.writerow(head)
            for row in cur.fetchmany(1000):
                w.writerow(row)
        except sqlite3.Error as e:
            raise SystemExit("sql error: {}".format(e))
        finally:
            ro.close()
        return 0

    print(USAGE)
    return 1
