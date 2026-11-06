#!/usr/bin/env python3
"""Load a books CSV file into books.db, following rules.md (Module 4, version 1.0).

Usage:
    python3 ingest.py <file.csv>

Uses only the Python standard library. No AI and no network access (R04).
books.db and ingestion-log.json are kept next to this script (R36).
Every decision in a run is made from the file and the database as it was at the
start of the run, then all changes are written together, so the same file and
the same starting database always give the same result (R39).
"""

import csv
import datetime
import decimal
import hashlib
import io
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Read at run time, so tests can point them at test.db and a test log (R40).
DB_PATH = os.path.join(HERE, "books.db")
LOG_PATH = os.path.join(HERE, "ingestion-log.json")

COLUMNS = [
    "book_id", "goodreads_book_id", "best_book_id", "work_id", "books_count",
    "isbn", "isbn13", "authors", "original_publication_year", "original_title",
    "title", "language_code", "average_rating", "ratings_count",
    "work_ratings_count", "work_text_reviews_count", "ratings_1", "ratings_2",
    "ratings_3", "ratings_4", "ratings_5", "image_url", "small_image_url",
]
# R27: the only fields an existing book may have updated.
APPROVED_FIELDS = [
    "books_count", "average_rating", "ratings_count", "work_ratings_count",
    "work_text_reviews_count", "ratings_1", "ratings_2", "ratings_3", "ratings_4",
    "ratings_5", "image_url", "small_image_url",
]
# R28: never changed automatically; differences are recorded for review.
PROTECTED_FIELDS = ["best_book_id", "work_id", "original_title",
                    "original_publication_year", "language_code"]
EXTRA_COLUMNS = ["goodreads_id_clean", "isbn_10_clean", "isbn_13_clean"]

REASON_DUPLICATE = "exact duplicate in input"
REASON_EXISTS = "already exists, no change"


class LogError(Exception):
    pass


# ---------------------------------------------------------------------------
# ISBN arithmetic (R10, R11, R14)
# ---------------------------------------------------------------------------

def check_char_10(core9):
    d = (11 - sum((10 - i) * int(c) for i, c in enumerate(core9)) % 11) % 11
    return "X" if d == 10 else str(d)


def check_char_13(core12):
    return str((10 - sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(core12)) % 10) % 10)


def isbn10_valid(s):
    return bool(re.fullmatch(r"[0-9]{9}[0-9X]", s)) and check_char_10(s[:9]) == s[9]


def isbn13_valid(s):
    return (bool(re.fullmatch(r"97[89][0-9]{10}", s)) and not s.startswith("9790")
            and check_char_13(s[:12]) == s[12])


def to13(isbn10):
    core = "978" + isbn10[:9]
    return core + check_char_13(core)


def to10(isbn13):
    """A 979 ISBN-13 has no ISBN-10 (R14)."""
    if not isbn13.startswith("978"):
        return None
    return isbn13[3:12] + check_char_10(isbn13[3:12])


def isbn_forms(i10, i13):
    """Every form of a row's ISBNs, for ownership checks (R22)."""
    forms = {x for x in (i10, i13) if x}
    if i10:
        forms.add(to13(i10))
    if i13 and to10(i13):
        forms.add(to10(i13))
    return forms


def isbn_key(i10, i13):
    return i13 or (to13(i10) if i10 else None)


# ---------------------------------------------------------------------------
# Classifying the two raw ISBN cells (R12, R13, R16, R17, R18)
# ---------------------------------------------------------------------------

SCI = re.compile(r"([0-9])(?:\.([0-9]+))?[eE]\+?([0-9]+)")


def formatted(raw):
    """R12 simple formatting: remove spaces and hyphens, uppercase a final x."""
    s = re.sub(r"[\s\-]", "", raw)
    steps = ["removed spaces and hyphens"] if s and s != raw else []
    if s.endswith("x"):
        s = s[:-1] + "X"
        steps.append("uppercased final x")
    return s, steps


def classify_isbn(raw):
    s, steps = formatted(raw)
    if s == "":
        return {"kind": "empty"}
    if re.fullmatch(r"[0-9]{13}", s):
        if isbn13_valid(s):
            return {"kind": "isbn13", "value": s, "steps": steps}
        return {"kind": "invalid", "issue": "isbn: 13-digit value is not a valid ISBN-13"}
    if re.fullmatch(r"[0-9]{9}[0-9X]", s):
        if isbn10_valid(s):
            return {"kind": "isbn10", "value": s, "steps": steps}
        return {"kind": "invalid", "issue": "isbn: wrong check digit"}
    if re.fullmatch(r"[0-9]{7,9}", s):
        padded = s.zfill(10)
        if isbn10_valid(padded):
            return {"kind": "isbn10", "value": padded, "steps": steps + ["restored leading zeros"]}
        return {"kind": "invalid", "issue": "isbn: wrong check digit (leading zeros also missing)"}
    if re.fullmatch(r"[0-9]+", s):
        return {"kind": "invalid", "issue": "isbn: wrong number of digits"}
    return {"kind": "invalid", "issue": "isbn: contains characters that are not allowed"}


def classify_isbn13(raw):
    s, steps = formatted(raw)
    if s == "":
        return {"kind": "empty"}
    if re.fullmatch(r"[0-9]{13}", s):
        if isbn13_valid(s):
            return {"kind": "valid13", "value": s, "steps": steps}
        if s.startswith("9790"):
            return {"kind": "not_isbn", "issue": "isbn13: 9790 ISMN, not an ISBN"}
        if s.startswith("978"):
            return {"kind": "bad978", "value": s, "issue": "isbn13: 978 value with a wrong check digit"}
        if s.startswith("979"):
            return {"kind": "invalid", "issue": "isbn13: wrong check digit"}
        return {"kind": "not_isbn", "issue": "isbn13: product code, not an ISBN"}
    if re.fullmatch(r"[0-9]{9}[0-9X]", s) and isbn10_valid(s):
        return {"kind": "isbn10", "value": s, "steps": steps}
    m = SCI.fullmatch(s)
    if m:
        value = decimal.Decimal(s)
        if value != value.to_integral_value():
            return {"kind": "invalid", "issue": "isbn13: scientific notation value is not a whole number"}
        digits = str(int(value))
        if len(digits) == 13 and digits[:3] in ("978", "979") and not digits.startswith("9790"):
            return {"kind": "rounded", "value": value, "sig": len(m.group(1) + (m.group(2) or ""))}
        return {"kind": "not_isbn", "issue": "isbn13: scientific notation code that is not an ISBN-13"}
    m = re.fullmatch(r"([0-9]+)\.0", s)
    if m:
        return {"kind": "dot0", "digits": m.group(1)}
    if re.fullmatch(r"[0-9]+", s):
        if s[:3] in ("978", "979"):
            return {"kind": "invalid", "issue": "isbn13: wrong number of digits"}
        return {"kind": "not_isbn", "issue": "isbn13: product code, not an ISBN"}
    return {"kind": "invalid", "issue": "isbn13: contains characters that are not allowed"}


def rounds_to(full13, rounded):
    """R16: round the derived ISBN-13 half to even to the significant digits written
    in the source value, with exact decimal arithmetic, and compare exactly."""
    drop = 13 - rounded["sig"]
    exact = decimal.Decimal(full13)
    if drop > 0:
        exact = exact.scaleb(-drop).quantize(decimal.Decimal(1), rounding=decimal.ROUND_HALF_EVEN).scaleb(drop)
    return exact == rounded["value"]


def evaluate_isbns(raw_isbn, raw_isbn13):
    """Apply sections 3 and R21 to one row's ISBN cells on their own."""
    a, b = classify_isbn(raw_isbn), classify_isbn13(raw_isbn13)
    out = {"isbn10": None, "isbn13": None, "warnings": [], "repairs": [],
           "review": False, "pair_conflict": False}

    def warn(issue, field, raw, review=False):
        out["warnings"].append({"issue": issue, "field": field, "raw_value": raw,
                                "action": "not used as a cleaned ISBN"})
        out["review"] = out["review"] or review

    def repair(field, raw, cleaned, rule):
        out["repairs"].append({"field": field, "raw_value": raw, "repaired_value": cleaned, "rule": rule})

    def conflict(issue):
        out["isbn10"] = out["isbn13"] = None
        out["repairs"] = []
        out["pair_conflict"] = True
        warn(issue, "isbn, isbn13", "{} / {}".format(raw_isbn, raw_isbn13), review=True)
        return out

    if a["kind"] == "invalid":
        warn(a["issue"], "isbn", raw_isbn)

    # R13: a valid ISBN-13 in the isbn column.
    if a["kind"] == "isbn13":
        moved = a["value"]
        if b["kind"] == "valid13" and b["value"] != moved:
            return conflict("isbn holds a valid ISBN-13 that differs from isbn13 (R13, R21)")
        if b["kind"] not in ("empty", "valid13"):
            warn(b.get("issue", "isbn13: value not used, isbn already holds a valid ISBN-13"), "isbn13", raw_isbn13)
        out["isbn13"] = moved
        repair("isbn_13_clean", raw_isbn, moved, "moved valid ISBN-13 from the isbn column (R13)")
        ten = to10(moved)
        if ten:
            out["isbn10"] = ten
            repair("isbn_10_clean", raw_isbn, ten, "derived ISBN-10 from ISBN-13 (R13, R14)")
        return out

    # R13: a valid ISBN-10 in the isbn13 column.
    if b["kind"] == "isbn10":
        moved = b["value"]
        if a["kind"] == "invalid":
            warn("isbn13 holds a valid ISBN-10 but isbn holds an invalid value", "isbn13", raw_isbn13, review=True)
            return out
        if a["kind"] == "isbn10" and a["value"] != moved:
            return conflict("isbn and isbn13 hold two different valid ISBN-10s (R13, R21)")
        out["isbn10"] = moved
        if a["kind"] == "empty":
            repair("isbn_10_clean", raw_isbn13, moved, "moved valid ISBN-10 from the isbn13 column (R13)")
        elif a["steps"]:
            repair("isbn_10_clean", raw_isbn, moved, "; ".join(a["steps"]) + " (R12)")
        out["isbn13"] = to13(moved)
        repair("isbn_13_clean", raw_isbn13, out["isbn13"], "derived ISBN-13 from ISBN-10 (R13, R14)")
        return out

    if a["kind"] == "isbn10":
        i10 = a["value"]
        t13 = to13(i10)
        out["isbn10"] = i10
        if a["steps"]:
            repair("isbn_10_clean", raw_isbn, i10, "; ".join(a["steps"]) + " (R12)")
        kind = b["kind"]
        if kind == "empty":
            out["isbn13"] = t13
            repair("isbn_13_clean", raw_isbn13, t13, "derived missing ISBN-13 from ISBN-10 (R15)")
        elif kind == "valid13":
            if b["value"] != t13:
                return conflict("isbn and isbn13 are both valid but are not the same ISBN (R21)")
            out["isbn13"] = t13
            if b["steps"]:
                repair("isbn_13_clean", raw_isbn13, t13, "; ".join(b["steps"]) + " (R12)")
        elif kind == "rounded":
            if rounds_to(t13, b):
                out["isbn13"] = t13
                repair("isbn_13_clean", raw_isbn13, t13,
                       "rebuilt from ISBN-10; matches the scientific notation value, half even (R16)")
            else:
                warn("isbn13: rounded value does not match the ISBN-13 derived from the ISBN-10 (R16)",
                     "isbn13", raw_isbn13, review=True)
        elif kind == "bad978":
            if b["value"][:12] == t13[:12]:
                warn(b["issue"], "isbn13", raw_isbn13)
                out["isbn13"] = t13
                repair("isbn_13_clean", raw_isbn13, t13, "derived ISBN-13 from ISBN-10; first 12 digits agree (R19)")
            else:
                warn("isbn13: 978 value with a wrong check digit contradicts the ISBN-10 (R19)",
                     "isbn13", raw_isbn13, review=True)
        elif kind == "dot0" and (b["digits"].zfill(10) if 7 <= len(b["digits"]) <= 9 else b["digits"]) == i10:
            out["isbn13"] = t13
            repair("isbn_13_clean", raw_isbn13, t13,
                   "isbn13 held this row's ISBN-10 followed by .0; confirmed, ISBN-13 derived (R17)")
        else:  # product code, ISMN, unconfirmed .0 value or another unusable value
            issue = b.get("issue", "isbn13: decimal value not confirmed by this row's ISBN-10 (R17)")
            warn(issue, "isbn13", raw_isbn13)
            out["isbn13"] = t13
            repair("isbn_13_clean", raw_isbn13, t13, "derived ISBN-13 from the valid ISBN-10 (R19)")
        return out

    # No valid ISBN-10 in the row.
    kind = b["kind"]
    if kind == "valid13":
        out["isbn13"] = b["value"]
        if b["steps"]:
            repair("isbn_13_clean", raw_isbn13, b["value"], "; ".join(b["steps"]) + " (R12)")
        ten = to10(b["value"])
        if ten and a["kind"] == "empty":  # R19.4: never replace an invalid ISBN-10
            out["isbn10"] = ten
            repair("isbn_10_clean", raw_isbn, ten, "derived missing ISBN-10 from ISBN-13 (R15)")
    elif kind == "rounded":
        warn("isbn13: rounded scientific notation with no valid ISBN-10 to confirm it (R16)", "isbn13", raw_isbn13)
    elif kind == "dot0":
        warn("isbn13: decimal value not confirmed by an ISBN-10 (R17)", "isbn13", raw_isbn13)
    elif kind == "empty":
        if a["kind"] == "empty":
            warn("no ISBN in either column (R15)", "isbn, isbn13", "")
    else:
        warn(b["issue"], "isbn13", raw_isbn13, review=(kind == "bad978"))
    return out


# ---------------------------------------------------------------------------
# Identity (R05, R06)
# ---------------------------------------------------------------------------

def positive_int(value):
    s = (value or "").strip()
    if re.fullmatch(r"[0-9]+", s) and int(s) > 0:
        return int(s)
    return None


def blank(value):
    return value is None or value.strip() == ""


def stored_value(field, value):
    """R03: raw ISBN text is kept exactly; other blank or whitespace-only cells become NULL."""
    if field in ("isbn", "isbn13"):
        return value
    return None if blank(value) else value


# ---------------------------------------------------------------------------
# Input file and log (R02, R33, R37)
# ---------------------------------------------------------------------------

def read_input(path):
    """Return (rows, sha256, error). rows is a list of (line_number, fields)."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return None, None, "File not found"
    except IsADirectoryError:
        return None, None, "Path is a folder, not a file"
    except OSError as e:
        return None, None, "File could not be read: " + (e.strerror or str(e))
    sha = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        return None, sha, "File is not UTF-8 (invalid byte at position {})".format(e.start)
    reader = csv.reader(io.StringIO(text, newline=""))
    rows = []
    try:
        header = next(reader, None)
        if header is None:
            return None, sha, "File is empty"
        while True:
            line = reader.line_num + 1
            fields = next(reader, None)
            if fields is None:
                break
            if fields:  # a completely empty line is not a data row
                rows.append((line, fields))
    except csv.Error as e:
        return None, sha, "File could not be read as CSV: {}".format(e)
    missing = [c for c in COLUMNS if c not in header]
    extra = [c for c in header if c not in COLUMNS]
    repeated = sorted({c for c in header if header.count(c) > 1})
    problems = []
    if missing:
        problems.append("missing columns: " + ", ".join(missing))
    if extra:
        problems.append("unexpected columns: " + ", ".join(extra))
    if repeated:
        problems.append("columns appear more than once: " + ", ".join(repeated))
    if problems:
        return None, sha, "Header does not match the 23 required columns (" + "; ".join(problems) + ")"
    index = {c: header.index(c) for c in COLUMNS}
    return [(line, fields, index) for line, fields in rows], sha, None


def read_log():
    if not os.path.exists(LOG_PATH):
        return []
    try:
        with open(LOG_PATH, encoding="utf-8") as f:
            runs = json.load(f)
    except (OSError, ValueError) as e:
        raise LogError("{} could not be read ({}). It was not changed.".format(LOG_PATH, e))
    if not isinstance(runs, list):
        raise LogError("{} is not a list of runs. It was not changed.".format(LOG_PATH))
    return runs


def append_log(runs, entry):
    """R33: append one run and rewrite atomically, so earlier runs are never lost."""
    runs.append(entry)
    tmp = LOG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(runs, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, LOG_PATH)


# ---------------------------------------------------------------------------
# Database (R30)
# ---------------------------------------------------------------------------

def schema_columns():
    return COLUMNS + EXTRA_COLUMNS


def create_schema(conn):
    cols = ['"book_id" INTEGER PRIMARY KEY'] + ['"{}" TEXT'.format(c) for c in COLUMNS[1:]]
    cols += ['"goodreads_id_clean" INTEGER', '"isbn_10_clean" TEXT', '"isbn_13_clean" TEXT']
    conn.execute("CREATE TABLE IF NOT EXISTS books (\n  {}\n)".format(",\n  ".join(cols)))
    existing = [r[1] for r in conn.execute("PRAGMA table_info(books)")]
    if existing != schema_columns():
        raise RuntimeError("books.db has a different structure (made by an older ingest.py). "
                           "Move it aside and run again")
    for col in EXTRA_COLUMNS:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS books_{0} ON books({0}) WHERE {0} IS NOT NULL".format(col))


def fetch_book(conn, book_id):
    cur = conn.execute("SELECT * FROM books WHERE book_id = ?", (book_id,))
    row = cur.fetchone()
    return dict(zip([d[0] for d in cur.description], row)) if row else None


def isbn_owner(conn, forms):
    if not forms:
        return None
    marks = ", ".join("?" * len(forms))
    values = sorted(forms)
    row = conn.execute("SELECT book_id FROM books WHERE isbn_10_clean IN ({0}) OR isbn_13_clean IN ({0}) "
                       "ORDER BY book_id".format(marks), values + values).fetchone()
    return row[0] if row else None


def goodreads_owner(conn, gid):
    row = conn.execute("SELECT book_id FROM books WHERE goodreads_id_clean = ?", (gid,)).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def new_result(line, fields):
    return {"line": line, "fields": fields, "rec": None, "book_id": "", "bid": None, "gid": None,
            "title": "", "outcome": None, "reason": None, "review": False, "duplicate": False,
            "ev": None, "warnings": [], "repairs": [], "changes": [], "insert": None, "update": None}


def reject(r, reason):
    r["outcome"] = "rejected"
    r["reason"] = reason
    r["review"] = True


def warn(r, issue, field="", raw="", review=False, action="recorded, nothing changed"):
    r["warnings"].append({"issue": issue, "field": field, "raw_value": raw, "action": action})
    r["review"] = r["review"] or review


def normalized(r):
    """A row's meaning after permitted normalization (R24): a difference that
    disappears here is formatting, not a material conflict."""
    rec, ev = r["rec"], r["ev"]
    other = tuple(None if blank(rec[c]) else rec[c] for c in COLUMNS
                  if c not in ("book_id", "goodreads_book_id", "isbn", "isbn13", "title", "authors"))
    return (r["bid"], rec["title"].strip(), rec["authors"].strip(), r["gid"], ev["isbn10"], ev["isbn13"], other)


def ingest(conn, rows):
    """Decide every row from the file and the database as it was at the start
    of the run, then return the results. Nothing is written here."""
    results = []

    # Row shape (R38) and required identity (R05, R06).
    for line, fields, index in rows:
        r = new_result(line, fields)
        results.append(r)
        if len(fields) != len(COLUMNS):
            reject(r, "row has {} fields, expected 23".format(len(fields)))
            continue
        rec = {c: fields[index[c]] for c in COLUMNS}
        r.update({"rec": rec, "book_id": rec["book_id"], "title": rec["title"]})
        problems = []
        r["bid"] = positive_int(rec["book_id"])
        if r["bid"] is None:
            problems.append("book_id is blank or not a positive whole number")
        if blank(rec["title"]):
            problems.append("title is blank")
        if blank(rec["authors"]):
            problems.append("authors is blank")
        if problems:
            reject(r, "required identity missing: " + "; ".join(problems) + " (R05)")
            continue
        r["gid"] = positive_int(rec["goodreads_book_id"])
        if r["gid"] is None:
            warn(r, "goodreads_book_id is missing or invalid; not used for identity (R06)",
                 "goodreads_book_id", rec["goodreads_book_id"])

    # Exact duplicates in the file (R23).
    first = {}
    for r in results:
        if r["outcome"] is None:
            key = tuple(r["fields"])
            if key in first:
                r.update({"outcome": "skipped", "duplicate": True,
                          "reason": "{} (same as line {})".format(REASON_DUPLICATE, first[key])})
            else:
                first[key] = r["line"]

    pending = [r for r in results if r["outcome"] is None]
    for r in pending:
        r["ev"] = evaluate_isbns(r["rec"]["isbn"], r["rec"]["isbn13"])
        r["warnings"].extend(r["ev"]["warnings"])
        r["review"] = r["review"] or r["ev"]["review"]

    # Competing rows in the file (R08, R24): never choose one by row order.
    by_bid = {}
    for r in pending:
        by_bid.setdefault(r["bid"], []).append(r)
    for bid, group in by_bid.items():
        if len(group) < 2:
            continue
        if len({normalized(r) for r in group}) > 1:
            lines = ", ".join(str(r["line"]) for r in group)
            for r in group:
                reject(r, "competing rows for book_id {} in this file, lines {} (R24)".format(bid, lines))
        else:
            for r in group[1:]:
                r.update({"outcome": "skipped", "duplicate": True,
                          "reason": "{} after normalization (same as line {})".format(REASON_DUPLICATE, group[0]["line"])})
    by_gid = {}
    for r in results:
        if r["outcome"] is None and r["gid"] is not None:
            by_gid.setdefault(r["gid"], []).append(r)
    for gid, group in by_gid.items():
        if len({r["bid"] for r in group}) > 1:
            lines = ", ".join(str(r["line"]) for r in group)
            for r in group:
                reject(r, "goodreads_book_id {} is claimed by different book_ids, lines {} (R08)".format(gid, lines))

    # Identity against stored books (R07, R08).
    for r in results:
        if r["outcome"] is not None:
            continue
        stored = fetch_book(conn, r["bid"])
        r["stored"] = stored
        owner = goodreads_owner(conn, r["gid"]) if r["gid"] is not None else None
        if owner is not None and owner != r["bid"]:
            reject(r, "goodreads_book_id {} already identifies book_id {} (R08)".format(r["gid"], owner))
        elif stored is not None:
            if r["rec"]["title"].strip() != (stored["title"] or "").strip() or \
                    r["rec"]["authors"].strip() != (stored["authors"] or "").strip():
                reject(r, "book_id {} returned with a different title or authors (R07)".format(r["bid"]))
            elif r["gid"] is not None and stored["goodreads_id_clean"] is not None and \
                    r["gid"] != stored["goodreads_id_clean"]:
                reject(r, "book_id {} returned with a different goodreads_book_id (R07)".format(r["bid"]))

    # ISBN ownership (R22): first against stored books, then between rows of this file.
    live = [r for r in results if r["outcome"] is None]
    for r in live:
        ev = r["ev"]
        owner = isbn_owner(conn, isbn_forms(ev["isbn10"], ev["isbn13"]))
        if owner is not None and owner != r["bid"]:
            ev["isbn10"] = ev["isbn13"] = None
            ev["repairs"] = []
            warn(r, "ISBN already belongs to book_id {}; not assigned (R22)".format(owner),
                 "isbn, isbn13", "{} / {}".format(r["rec"]["isbn"], r["rec"]["isbn13"]), review=True)
    claims = {}
    for r in live:
        key = isbn_key(r["ev"]["isbn10"], r["ev"]["isbn13"])
        if key:
            claims.setdefault(key, []).append(r)
    for key, group in claims.items():
        if len({r["bid"] for r in group}) > 1 and isbn_owner(conn, isbn_forms(None, key)) is None:
            lines = ", ".join(str(r["line"]) for r in group)
            for r in group:
                r["ev"]["isbn10"] = r["ev"]["isbn13"] = None
                r["ev"]["repairs"] = []
                warn(r, "ISBN {} is claimed by different books in this file, lines {}; not assigned (R22)".format(
                    key, lines), "isbn, isbn13", "{} / {}".format(r["rec"]["isbn"], r["rec"]["isbn13"]), review=True)

    # New books and changes to existing books (R25 to R29).
    for r in live:
        ev, rec, stored = r["ev"], r["rec"], r["stored"]
        if stored is None:
            values = {c: stored_value(c, rec[c]) for c in COLUMNS}
            values["book_id"] = r["bid"]
            values.update({"goodreads_id_clean": r["gid"], "isbn_10_clean": ev["isbn10"],
                           "isbn_13_clean": ev["isbn13"]})
            r.update({"outcome": "loaded", "insert": values, "repairs": ev["repairs"]})
            continue

        if ev["pair_conflict"] and (stored["isbn_10_clean"] or stored["isbn_13_clean"]):
            reject(r, "conflicting ISBN pair for a book that already has accepted ISBNs (R21)")
            continue
        changes, filled = [], []
        for col, new in (("isbn_10_clean", ev["isbn10"]), ("isbn_13_clean", ev["isbn13"])):
            old = stored[col]
            if new is None or new == old:
                continue
            if old is None:
                changes.append((col, old, new))
                filled.append(col)
            else:
                reject(r, "different validated ISBN for book_id {}: stored {}, incoming {} (R26)".format(
                    r["bid"], old, new))
                break
        if r["outcome"] == "rejected":
            continue
        for f in APPROVED_FIELDS:
            if not blank(rec[f]) and rec[f] != stored[f]:
                changes.append((f, stored[f], rec[f]))
        for f in PROTECTED_FIELDS:
            if not blank(rec[f]) and rec[f] != stored[f]:
                warn(r, "{} differs from the stored value and was not changed (R28)".format(f), f, rec[f], review=True)
        if r["gid"] is not None and stored["goodreads_id_clean"] is None:
            warn(r, "goodreads_book_id differs from the stored value and was not changed (R28)",
                 "goodreads_book_id", rec["goodreads_book_id"], review=True)
        if changes:
            r.update({"outcome": "updated", "update": changes,
                      "repairs": [p for p in ev["repairs"] if p["field"] in filled],
                      "changes": [{"field": f, "old_value": o, "new_value": n} for f, o, n in changes]})
        else:
            r.update({"outcome": "skipped", "reason": REASON_EXISTS})
    return results


def write_changes(conn, results):
    names = schema_columns()
    insert_sql = "INSERT INTO books ({}) VALUES ({})".format(
        ", ".join('"{}"'.format(c) for c in names), ", ".join("?" * len(names)))
    for r in results:
        if r["insert"]:
            conn.execute(insert_sql, [r["insert"][c] for c in names])
        elif r["update"]:
            conn.execute("UPDATE books SET {} WHERE book_id = ?".format(
                ", ".join('"{}" = ?'.format(f) for f, _, _ in r["update"])),
                [n for _, _, n in r["update"]] + [r["bid"]])


def summarize(results):
    counts = {"read": len(results), "loaded": 0, "updated": 0, "skipped": 0, "rejected": 0,
              "skipped_duplicate_in_file": 0, "skipped_already_exist": 0, "warnings": 0, "review": 0}
    issues = {}
    repairs, changes, attention = [], [], []

    def tally(issue, action):
        issues[(issue, action)] = issues.get((issue, action), 0) + 1

    for r in results:
        counts[r["outcome"]] += 1
        if r["outcome"] == "skipped":
            counts["skipped_duplicate_in_file" if r["duplicate"] else "skipped_already_exist"] += 1
        counts["warnings"] += len(r["warnings"])
        counts["review"] += 1 if r["review"] else 0
        # "row" repeats the CSV line number (R34) under the name report.html reads.
        base = {"line": r["line"], "row": r["line"], "book_id": r["book_id"],
                "goodreads_book_id": r["rec"]["goodreads_book_id"] if r["rec"] else None,
                "title": r["title"]}
        for w in r["warnings"]:
            tally(w["issue"], r["outcome"])
        for p in r["repairs"]:
            tally(p["rule"], "repaired")
            repairs.append(dict(base, **p))
        for c in r["changes"]:
            changes.append(dict(base, **c))
        if r["outcome"] in ("rejected", "skipped"):
            tally(r["reason"], r["outcome"])
        if r["outcome"] != "loaded" or r["warnings"] or r["review"]:
            ev = r["ev"] or {}
            record = dict(base, outcome=r["outcome"], reason=r["reason"], review=r["review"],
                          warnings=r["warnings"],
                          raw_isbn=r["rec"]["isbn"] if r["rec"] else None,
                          raw_isbn13=r["rec"]["isbn13"] if r["rec"] else None,
                          isbn10_clean=ev.get("isbn10"), isbn13_clean=ev.get("isbn13"))
            if r["outcome"] == "rejected":
                record["raw_row"] = r["fields"]
            attention.append(record)
    by_issue = [{"issue": i, "action": a, "rows": n}
                for (i, a), n in sorted(issues.items(), key=lambda x: (-x[1], str(x[0][0]), x[0][1]))]
    return counts, by_issue, repairs, changes, attention


def main(argv):
    if len(argv) != 2:
        print("Usage: python3 ingest.py <file.csv>", file=sys.stderr)
        return 2
    path = argv[1]
    now = datetime.datetime.now().astimezone()
    run_time = now.strftime("%Y-%m-%d %H:%M:%S %z ") + (now.tzname() or "")
    try:
        runs = read_log()
    except LogError as e:
        print("Stopped: " + str(e), file=sys.stderr)
        return 1

    entry = {"run_date": now.strftime("%Y-%m-%d"), "run_time": run_time.strip(), "status": None,
             "file": os.path.basename(path), "file_path": os.path.abspath(path), "sha256": None}
    rows, sha, error = read_input(path)
    entry["sha256"] = sha or "unavailable"
    if error:
        entry.update({"status": "failed", "failure_reason": error})
        append_log(runs, entry)
        print("Run failed: {}. The database was not changed.".format(error), file=sys.stderr)
        return 1

    db_existed = os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    try:
        conn.execute("BEGIN")
        create_schema(conn)
        results = ingest(conn, rows)
        write_changes(conn, results)
        counts, by_issue, repairs, changes, attention = summarize(results)
        total = counts["loaded"] + counts["updated"] + counts["skipped"] + counts["rejected"]
        if total != counts["read"]:
            raise RuntimeError("outcomes add up to {}, but {} rows were read".format(total, counts["read"]))
        conn.execute("COMMIT")
    except Exception as e:  # R37: any failure leaves the database unchanged
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        conn.close()
        if not db_existed and os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        entry.update({"status": "failed", "failure_reason": "Error during ingestion: {}".format(e)})
        append_log(runs, entry)
        print("Run failed: {}. The database was not changed.".format(e), file=sys.stderr)
        return 1
    conn.close()

    entry.update({"status": "completed", "counts": counts, "counts_by_issue": by_issue,
                  "repairs": repairs, "changes": changes, "attention": attention})
    append_log(runs, entry)
    print("{}  {}".format(entry["run_time"], entry["file"]))
    print("  read {read}, loaded {loaded}, updated {updated}, skipped {skipped} "
          "(already exist {skipped_already_exist}, exact duplicates {skipped_duplicate_in_file}), "
          "rejected {rejected}, warnings {warnings}, for review {review}".format(**counts))
    print("  details: " + LOG_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
