"""Shared setup for the ingest.py tests (rules.md R40).

Every test runs ingest.py against a database named test.db and its own log, both
in a fresh temporary folder that is deleted when the test ends, pass or fail.
The real books.db and ingestion-log.json are never used, and a guard fails any
test that changes them.
"""

import csv
import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import types

import pytest

sys.dont_write_bytecode = True  # importing ingest.py must not leave a __pycache__ folder

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS_CSV = os.path.join(PROJECT, "books.csv")
BATCH2_CSV = os.path.join(PROJECT, "books-batch2.csv")
REAL_FILES = [os.path.join(PROJECT, "books.db"), os.path.join(PROJECT, "ingestion-log.json")]

sys.path.insert(0, PROJECT)
import ingest  # noqa: E402

# ---------------------------------------------------------------------------
# How the tests read ingest.py's results.
# rules.md R30 lets each partner choose table and column names, and the log
# field names are not fixed either. These names match the current ingest.py.
# If ingest.py changes them, change them here only.
# ---------------------------------------------------------------------------
BOOKS_TABLE = "books"
BOOK_ID_COLUMN = "book_id"
CLEAN_ISBN10_COLUMN = "isbn_10_clean"
CLEAN_ISBN13_COLUMN = "isbn_13_clean"
LOG_COUNTS = "counts"          # rows read and the four outcome counts (R32, R33)
LOG_RECORDS = "attention"      # per-row records with outcome, warnings, reason (R34)
LOG_REPAIRS = "repairs"        # repairs with raw and cleaned values (R12, R34)
LOG_CHANGES = "changes"        # field changes with old and new values (R25, R27, R34)
LOG_STATUS = "status"          # completed or failed (R33, R37)
RECORD_OUTCOME = "outcome"
RECORD_WARNINGS = "warnings"
RECORD_REASON = "reason"
RECORD_REVIEW = "review"       # true when a human should review the row (R34)
TEST_DB_NAME = "test.db"


def file_state(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.fixture(autouse=True)
def real_files_untouched():
    """R40: fail any test that creates, changes or deletes the real books.db
    or ingestion-log.json in the project folder."""
    before = {p: file_state(p) for p in REAL_FILES}
    yield
    after = {p: file_state(p) for p in REAL_FILES}
    assert after == before, "a test touched the real books.db or ingestion-log.json"


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1:]


HEADER, BOOKS_ROWS = read_csv(BOOKS_CSV)
BOOKS_BY_ID = {r[0]: r for r in BOOKS_ROWS}
_, BATCH2_ROWS = read_csv(BATCH2_CSV)


def make_row(base_book_id, **changes):
    """A copy of a books.csv row with some fields changed, as a list of 23 values."""
    row = dict(zip(HEADER, BOOKS_BY_ID[base_book_id]))
    for field, value in changes.items():
        assert field in row, field
        row[field] = value
    return [row[c] for c in HEADER]


def batch2_row(book_id):
    """The books-batch2.csv row for a book_id (the first one, if repeated)."""
    return next(list(r) for r in BATCH2_ROWS if r[0] == str(book_id))


def data_row_count(path):
    return len(read_csv(path)[1])


class Env:
    """A temporary folder holding test.db, the test log and any CSV a test writes."""

    def __init__(self, folder):
        self.folder = folder
        self.db_path = os.path.join(folder, TEST_DB_NAME)
        self.log_path = os.path.join(folder, "test-ingestion-log.json")
        self._files = 0

    # running ------------------------------------------------------------
    def run(self, csv_path):
        """Run ingest.py on csv_path and return the log entry this run added."""
        assert os.path.basename(ingest.DB_PATH) == TEST_DB_NAME
        assert os.path.dirname(ingest.DB_PATH) == self.folder
        before = len(self.log())
        ingest.main(["ingest.py", csv_path])
        entries = self.log()
        assert len(entries) == before + 1, "the run did not add exactly one log entry"
        return entries[-1]

    def write_csv(self, rows, header=None):
        self._files += 1
        path = os.path.join(self.folder, "input-{}.csv".format(self._files))
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(header or HEADER)
            w.writerows(rows)
        return path

    def run_rows(self, *rows):
        return self.run(self.write_csv(list(rows)))

    # reading ------------------------------------------------------------
    def log(self):
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path, encoding="utf-8") as f:
            return json.load(f)

    def connect(self):
        assert os.path.exists(self.db_path), "test.db was not created"
        return sqlite3.connect(self.db_path)

    def books(self, book_id):
        """Every stored row for this book_id, as dictionaries."""
        if not os.path.exists(self.db_path):
            return []
        conn = self.connect()
        try:
            cur = conn.execute(
                'SELECT * FROM "{}" WHERE "{}" = ?'.format(BOOKS_TABLE, BOOK_ID_COLUMN), (str(book_id),))
            names = [d[0] for d in cur.description]
            return [dict(zip(names, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def book(self, book_id):
        found = self.books(book_id)
        assert len(found) <= 1, "book_id {} is stored {} times".format(book_id, len(found))
        return found[0] if found else None

    def stored_isbns(self, book_id):
        b = self.book(book_id)
        assert b is not None, "book {} is not stored".format(book_id)
        return b[CLEAN_ISBN10_COLUMN], b[CLEAN_ISBN13_COLUMN]

    def dump(self, tables=None):
        """Every row of every table (or of the named tables), for exact comparison."""
        conn = self.connect()
        try:
            names = tables or [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            return {t: sorted(conn.execute('SELECT * FROM "{}"'.format(t)).fetchall(), key=repr) for t in names}
        finally:
            conn.close()


@pytest.fixture
def env(monkeypatch):
    """A fresh temporary folder with ingest.py pointed at test.db and a test log.
    The folder and everything in it are deleted when the test ends (R40)."""
    folder = tempfile.mkdtemp(prefix="ingest-test-")
    monkeypatch.setattr(ingest, "DB_PATH", os.path.join(folder, TEST_DB_NAME))
    monkeypatch.setattr(ingest, "LOG_PATH", os.path.join(folder, "test-ingestion-log.json"))
    try:
        yield Env(folder)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        assert not os.path.exists(folder), "test files were not removed"


class _FixedDatetime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        fixed = datetime.datetime(2026, 11, 6, 12, 0, 0, tzinfo=datetime.timezone.utc)
        return fixed if tz else fixed.replace(tzinfo=None)


@pytest.fixture
def fixed_clock(monkeypatch):
    """Give ingest.py the same time on every run, so only the input can make runs differ."""
    monkeypatch.setattr(ingest, "datetime", types.SimpleNamespace(datetime=_FixedDatetime))


# ---------------------------------------------------------------------------
# Reading one book's details from a log entry
# ---------------------------------------------------------------------------

def _for(entry, key, book_id):
    return [r for r in entry.get(key, []) if str(r.get("book_id")) == str(book_id)]


def records_for(entry, book_id):
    return _for(entry, LOG_RECORDS, book_id)


def repairs_for(entry, book_id):
    return _for(entry, LOG_REPAIRS, book_id)


def changes_for(entry, book_id):
    return _for(entry, LOG_CHANGES, book_id)


def values_in(items):
    """Every value held in a list of log items, as strings."""
    return {str(v) for item in items for v in item.values() if v is not None}


def is_empty(value):
    return value in (None, "")
