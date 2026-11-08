"""Tests for ingest.py, taken only from rules.md (version 1.1, 2026-11-08).

Each example test matches one row of the table in rules.md section 7. As the
table says, a row is a new book with a unique valid book_id, a nonblank title
and authors, no conflicting goodreads_book_id and no prior record, unless the
row states otherwise. Outcomes are read from the run's counts (R32, R33);
warnings, review flags and repairs from the run's log records (R34).
The last four tests cover repeat runs, the log, the counts and determinism.
"""

import os

import pytest

from conftest import (
    BATCH2_CSV, BOOK_ID_COLUMN, BOOKS_CSV, BOOKS_TABLE, CLEAN_ISBN10_COLUMN,
    CLEAN_ISBN13_COLUMN, LOG_COUNTS, LOG_STATUS, RECORD_REASON, RECORD_REVIEW,
    RECORD_WARNINGS, batch2_row, changes_for, data_row_count, is_empty, make_row,
    records_for, repairs_for, values_in,
)

OUTCOMES = ("loaded", "updated", "skipped", "rejected")


# ---------------------------------------------------------------------------
# Building rows
# ---------------------------------------------------------------------------

def new_book(number, isbn="", isbn13="", **changes):
    """A new book as the table assumes: unique valid book_id and
    goodreads_book_id, nonblank title and authors, no prior record.
    Any field, including book_id, can be overridden with changes."""
    fields = {"book_id": str(number), "goodreads_book_id": str(90000000 + number),
              "title": "Example Book {}".format(number),
              "original_title": "Example Book {}".format(number),
              "authors": "Example Author {}".format(number),
              "isbn": isbn, "isbn13": isbn13}
    fields.update(changes)
    return make_row("106", **fields)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def counts_are(entry, read, **outcomes):
    c = entry[LOG_COUNTS]
    assert c["read"] == read
    for name in OUTCOMES:
        assert c[name] == outcomes.get(name, 0), "{}: expected {}, got {}".format(
            name, outcomes.get(name, 0), c[name])


def isbns_are(env, book_id, isbn10, isbn13):
    """None means NULL: no cleaned value."""
    stored10, stored13 = env.stored_isbns(book_id)
    for label, expected, stored in (("ISBN-10", isbn10, stored10), ("ISBN-13", isbn13, stored13)):
        if expected is None:
            assert is_empty(stored), "book {}: {} should be NULL, got {!r}".format(book_id, label, stored)
        else:
            assert stored == expected, "book {}: {}".format(book_id, label)


def warned(entry, book_id):
    assert any(r.get(RECORD_WARNINGS) for r in records_for(entry, book_id)), \
        "book {}: expected a warning".format(book_id)


def not_warned(entry, book_id):
    assert not any(r.get(RECORD_WARNINGS) for r in records_for(entry, book_id)), \
        "book {}: expected no warning".format(book_id)


def flagged(entry, book_id):
    assert any(r.get(RECORD_REVIEW) is True for r in records_for(entry, book_id)), \
        "book {}: expected a review flag".format(book_id)


def repairs_logged(entry, book_id, *cleaned):
    logged = values_in(repairs_for(entry, book_id))
    for value in cleaned:
        assert value in logged, "book {}: repair to {} not logged".format(book_id, value)


def reason_contains(entry, book_id, text):
    reasons = " ".join(str(r.get(RECORD_REASON, "")) for r in records_for(entry, book_id)).lower()
    assert text in reasons, "book {}: reason should mention {!r}".format(book_id, text)


def stored_book_count(env):
    if not os.path.exists(env.db_path):
        return 0
    conn = env.connect()
    try:
        return conn.execute('SELECT COUNT(*) FROM "{}"'.format(BOOKS_TABLE)).fetchone()[0]
    finally:
        conn.close()


def load_one(env, book_id, isbn, isbn13):
    entry = env.run_rows(new_book(book_id, isbn, isbn13))
    counts_are(entry, read=1, loaded=1)
    return entry


# ---------------------------------------------------------------------------
# Examples table, rules.md section 7
# ---------------------------------------------------------------------------

def test_example_01_matching_valid_pair(env):
    """Example 1 (R10, R11): both valid; no repair."""
    e = load_one(env, 20001, "0439139600", "9780439139601")
    isbns_are(env, 20001, "0439139600", "9780439139601")
    assert repairs_for(e, 20001) == []


def test_example_02_padded_isbn10_and_rounded_isbn13(env):
    """Example 2 (R12, R16): pad ISBN-10, reconstruct ISBN-13 after half-even check; log both."""
    e = load_one(env, 20002, "439023483", "9.78043902348e+12")
    isbns_are(env, 20002, "0439023483", "9780439023481")
    repairs_logged(e, 20002, "0439023483", "9780439023481")


def test_example_03_eight_digit_isbn10_padded_isbn13_derived(env):
    """Example 3 (R12, R15): pad 8-digit ISBN-10, derive missing ISBN-13, log repairs."""
    e = load_one(env, 20003, "61120081", "")
    isbns_are(env, 20003, "0061120081", "9780061120084")
    repairs_logged(e, 20003, "0061120081", "9780061120084")


def test_example_04_hyphens_removed(env):
    """Example 4 (R12): remove hyphens; log formatting repair."""
    e = load_one(env, 20004, "0-450-19827-8", "9780450198274")
    isbns_are(env, 20004, "0450198278", "9780450198274")
    repairs_logged(e, 20004, "0450198278")


def test_example_05_spaces_removed(env):
    """Example 5 (R12): remove spaces; log formatting repair."""
    e = load_one(env, 20005, "162 001 4750", "9781620014752")
    isbns_are(env, 20005, "1620014750", "9781620014752")
    repairs_logged(e, 20005, "1620014750")


def test_example_06_lowercase_x_uppercased(env):
    """Example 6 (R12): uppercase final x; log repair."""
    e = load_one(env, 20006, "031200009x", "9780312000097")
    isbns_are(env, 20006, "031200009X", "9780312000097")
    repairs_logged(e, 20006, "031200009X")


def test_example_07_isbn13_in_isbn_column_moved(env):
    """Example 7 (R13): move ISBN-13 to its field, derive ISBN-10, log."""
    e = load_one(env, 20007, "9781982147600", "")
    isbns_are(env, 20007, "1982147601", "9781982147600")
    repairs_logged(e, 20007, "1982147601", "9781982147600")


def test_example_08_isbn10_derived_from_978_isbn13(env):
    """Example 8 (R14, R15): derive ISBN-10 from valid 978 ISBN-13; log."""
    e = load_one(env, 20008, "", "9780062398123")
    isbns_are(env, 20008, "0062398121", "9780062398123")
    repairs_logged(e, 20008, "0062398121")


def test_example_09_979_isbn13_has_no_isbn10(env):
    """Example 9 (R14): valid 979; no missing-ISBN-10 warning."""
    e = load_one(env, 20009, "", "9798351220413")
    isbns_are(env, 20009, None, "9798351220413")
    not_warned(e, 20009)


def test_example_10_rounded_isbn13_matches_derived(env):
    """Example 10 (R16): rounded value matches the derived ISBN-13; log reconstruction."""
    e = load_one(env, 20010, "1416524797", "9.78141652479e+12")
    isbns_are(env, 20010, "1416524797", "9781416524793")
    repairs_logged(e, 20010, "9781416524793")


def test_example_11_rounded_isbn13_without_isbn10(env):
    """Example 11 (R16): no companion ISBN-10; do not guess; warn."""
    e = load_one(env, 20011, "", "9.78067172365e+12")
    isbns_are(env, 20011, None, None)
    warned(e, 20011)


def test_example_12_ambiguous_rounded_isbn13(env):
    """Example 12 (R16): rounded ISBN-13 ambiguous; NULL and warn."""
    e = load_one(env, 20012, "", "9.7804251888e+12")
    isbns_are(env, 20012, None, None)
    warned(e, 20012)


def test_example_13_wrong_check_digit(env):
    """Example 13 (R18): wrong check digit; do not change it; warn."""
    e = load_one(env, 20013, "1854433017", "")
    isbns_are(env, 20013, None, None)
    warned(e, 20013)


def test_example_14_illegal_letter(env):
    """Example 14 (R18): illegal interior letter; warn."""
    e = load_one(env, 20014, "04390A3483", "")
    isbns_are(env, 20014, None, None)
    warned(e, 20014)


def test_example_15_extra_digit(env):
    """Example 15 (R18): extra digit; do not truncate; warn."""
    e = load_one(env, 20015, "15287463097", "")
    isbns_are(env, 20015, None, None)
    warned(e, 20015)


def test_example_16_product_code(env):
    """Example 16 (R18): 2940 product code is not an ISBN; warn."""
    e = load_one(env, 20016, "", "2940016231920")
    isbns_are(env, 20016, None, None)
    warned(e, 20016)


def test_example_17_product_code_with_valid_isbn10(env):
    """Example 17 (R18, R19): reject the product code, derive ISBN-13 from the
    valid ISBN-10; log the warning and the derivation."""
    e = load_one(env, 20017, "189221301X", "6.45573003012e+11")
    isbns_are(env, 20017, "189221301X", "9781892213013")
    warned(e, 20017)
    repairs_logged(e, 20017, "9781892213013")


def test_example_18_dot0_copy_of_isbn10(env):
    """Example 18 (R17): exact match to the validated ISBN-10; log confirmation and derivation."""
    e = load_one(env, 20018, "0439139600", "0439139600.0")
    isbns_are(env, 20018, "0439139600", "9780439139601")
    repairs_logged(e, 20018, "9780439139601")


def test_example_19_unconfirmed_dot0_value(env):
    """Example 19 (R17): unconfirmed decimal form; no stripping or guessing; warn."""
    e = load_one(env, 20019, "", "195170342.0")
    isbns_are(env, 20019, None, None)
    warned(e, 20019)


def test_example_20_both_isbns_blank(env):
    """Example 20 (R15, R20): identity valid; missing-ISBN warning."""
    e = load_one(env, 20020, "", "")
    isbns_are(env, 20020, None, None)
    warned(e, 20020)


def test_example_21_valid_but_mismatched_pair(env):
    """Example 21 (R21): both valid but not a pair; keep the book, flag."""
    e = load_one(env, 20021, "1555550126", "9781555550134")
    isbns_are(env, 20021, None, None)
    flagged(e, 20021)


def test_example_22_isbn_owned_by_another_book(env):
    """Example 22 (R22): after Angels & Demons owns the ISBN, Paper Moons is
    loaded without it; warn and flag. Angels & Demons keeps it."""
    env.run_rows(new_book(20122, "1416524797", ""))
    e = env.run_rows(new_book(20022, "1416524797", ""))
    counts_are(e, read=1, loaded=1)
    isbns_are(env, 20022, None, None)
    warned(e, 20022)
    flagged(e, 20022)
    isbns_are(env, 20122, "1416524797", "9781416524793")


def test_example_23_two_valid_mismatched_isbns(env):
    """Example 23 (R21): keep the book without either cleaned ISBN; flag."""
    e = load_one(env, 20023, "0446612707", "9780553813951")
    isbns_are(env, 20023, None, None)
    flagged(e, 20023)


def test_example_24_exact_duplicate_in_one_file(env):
    """Example 24 (R23): first loaded, second skipped as exact duplicate; two rows counted."""
    row = new_book(20024, "1528746309", "9781528746304")
    e = env.run_rows(row, list(row))
    counts_are(e, read=2, loaded=1, skipped=1)
    assert len(env.books(20024)) == 1
    isbns_are(env, 20024, "1528746309", "9781528746304")
    reason_contains(e, 20024, "exact duplicate in input")


def test_example_25_accepted_book_repeats_with_normalized_isbns(env):
    """Example 25 (R23): book 24 accepted from books.csv, then repeated with
    0439139600 / 9780439139601 and the same other values: skipped, unchanged."""
    env.run_rows(make_row("24"))
    before = env.stored_isbns(24)
    e = env.run_rows(batch2_row(24))
    counts_are(e, read=1, skipped=1)
    assert env.stored_isbns(24) == before
    assert len(env.books(24)) == 1


def test_example_26_blank_isbns_never_erase_accepted_ones(env):
    """Example 26 (R25, R29): book 25 has 0545010225; a later row with both
    ISBNs blank is skipped and the stored ISBNs are kept."""
    env.run_rows(make_row("25"))
    assert env.stored_isbns(25)[0] == "0545010225"
    before = env.stored_isbns(25)
    e = env.run_rows(batch2_row(25))
    counts_are(e, read=1, skipped=1)
    assert env.stored_isbns(25) == before


def test_example_27_approved_metadata_updated(env):
    """Example 27 (R27): book 132's ratings_count changes 449501 to 451425:
    updated, ISBNs kept, old and new values recorded."""
    env.run_rows(make_row("132"))
    before = env.stored_isbns(132)
    e = env.run_rows(batch2_row(132))
    counts_are(e, read=1, updated=1)
    assert env.stored_isbns(132) == before
    assert str(env.book(132)["ratings_count"]) == "451425"
    logged = values_in(changes_for(e, 132))
    assert {"449501", "451425"} <= logged, "old and new ratings_count not recorded"


@pytest.mark.parametrize("field,value", [("title", "A Different Title"), ("authors", "A Different Author")])
def test_example_28_same_book_id_with_different_identity(env, field, value):
    """Example 28 (R07): same book_id with a different title or authors is
    rejected; the existing record is unchanged."""
    env.run_rows(make_row("9"))
    before = env.book(9)
    e = env.run_rows(make_row("9", **{field: value}))
    counts_are(e, read=1, rejected=1)
    assert env.book(9) == before


def test_example_29_two_new_rows_share_a_goodreads_id(env):
    """Example 29 (R08): different book_ids, same valid goodreads_book_id:
    both rejected, neither chosen by row order."""
    e = env.run_rows(new_book(20029, goodreads_book_id="77777777"),
                     new_book(20129, goodreads_book_id="77777777"))
    counts_are(e, read=2, rejected=2)
    assert env.book(20029) is None and env.book(20129) is None


def test_example_30_no_goodreads_id_and_no_isbn(env):
    """Example 30 (R06, R20): primary identity is enough; loaded with a warning."""
    e = env.run_rows(new_book(20030, goodreads_book_id=""))
    counts_are(e, read=1, loaded=1)
    isbns_are(env, 20030, None, None)
    warned(e, 20030)


def test_example_31_two_new_books_claim_the_same_isbn(env):
    """Example 31 (R22): both loaded without the disputed ISBN; both flagged."""
    e = env.run_rows(new_book(20031, "0300000022", ""), new_book(20131, "0300000022", ""))
    counts_are(e, read=2, loaded=2)
    for book_id in (20031, 20131):
        isbns_are(env, book_id, None, None)
        flagged(e, book_id)


def test_example_32_different_validated_isbn_on_existing_book(env):
    """Example 32 (R26): rejected; the stored ISBN and metadata are not changed
    by the conflicting row."""
    env.run_rows(new_book(20032, "1416524797", ""))
    before = env.book(20032)
    e = env.run_rows(new_book(20032, "0300000014", "", ratings_count="999999"))
    counts_are(e, read=1, rejected=1)
    assert env.book(20032) == before


@pytest.mark.parametrize("changes", [
    {"book_id": ""},
    {"book_id": "abc"},
    {"book_id": "12.5"},
    {"title": ""},
    {"authors": "   "},
], ids=["blank-book_id", "nonnumeric-book_id", "fractional-book_id", "blank-title", "blank-authors"])
def test_example_33_required_identity_missing(env, changes):
    """Example 33 (R05): blank or invalid book_id, or blank title or authors:
    rejected, no book inserted."""
    e = env.run_rows(new_book(20033, **changes))
    counts_are(e, read=1, rejected=1)
    assert stored_book_count(env) == 0


def test_example_34_missing_isbn_filled_later(env):
    """Example 34 (R25): an existing book without a cleaned ISBN later supplies
    a valid nonconflicting one: updated, old and new values logged."""
    env.run_rows(new_book(20034, "", ""))
    isbns_are(env, 20034, None, None)
    e = env.run_rows(new_book(20034, "0300000006", ""))
    counts_are(e, read=1, updated=1)
    isbns_are(env, 20034, "0300000006", "9780300000009")
    assert "0300000006" in values_in(changes_for(e, 20034)), "new ISBN not logged as a change"


def test_example_35_invalid_isbn10_and_unsupported_rounded_isbn13(env):
    """Example 35 (R16, R18): do not change 0 to X; both NULL; warn."""
    e = load_one(env, 20035, "812971060", "9.78081297106e+12")
    isbns_are(env, 20035, None, None)
    warned(e, 20035)


# ---------------------------------------------------------------------------
# Repeat runs, log, counts and determinism
# ---------------------------------------------------------------------------

def test_rerun_creates_no_duplicates(env):
    """R23, R30, R39: running books.csv twice inserts no duplicate book or
    cleaned ISBN, and the second run loads and updates nothing."""
    count_sql = 'SELECT COUNT(*), COUNT(DISTINCT "{0}") FROM "{1}"'.format(BOOK_ID_COLUMN, BOOKS_TABLE)
    env.run(BOOKS_CSV)
    conn = env.connect()
    try:
        after_first = conn.execute(count_sql).fetchone()[0]
    finally:
        conn.close()
    second = env.run(BOOKS_CSV)
    assert second[LOG_COUNTS]["loaded"] == 0 and second[LOG_COUNTS]["updated"] == 0
    conn = env.connect()
    try:
        total, distinct = conn.execute(count_sql).fetchone()
        assert total == after_first, "the second run added books"
        assert total == distinct, "a book_id is stored more than once"
        for col in (CLEAN_ISBN10_COLUMN, CLEAN_ISBN13_COLUMN):
            dup = conn.execute(
                'SELECT "{0}" FROM "{1}" WHERE "{0}" IS NOT NULL AND "{0}" != \'\' '
                'GROUP BY "{0}" HAVING COUNT(*) > 1'.format(col, BOOKS_TABLE)).fetchall()
            assert dup == [], "a cleaned ISBN is stored on more than one book in " + col
    finally:
        conn.close()


def test_every_run_appends_to_the_log(env):
    """R33, R37: every run, including a failed one, appends one entry and
    leaves earlier entries exactly as they were."""
    earlier = []
    for path in (BATCH2_CSV, BATCH2_CSV, os.path.join(env.folder, "missing.csv")):
        env.run(path)
        log = env.log()
        assert len(log) == len(earlier) + 1
        assert log[:len(earlier)] == earlier
        earlier = log
    assert earlier[-1][LOG_STATUS] == "failed"


@pytest.mark.parametrize("files", [
    [BOOKS_CSV],
    [BOOKS_CSV, BOOKS_CSV],
    [BOOKS_CSV, BOOKS_CSV, BATCH2_CSV],
], ids=["run1-books", "run2-books-again", "run3-batch2"])
def test_outcome_counts_add_up_to_rows_read(env, files):
    """R32, R39: loaded + updated + skipped + rejected = rows_read, for each
    run of the three-run sequence."""
    for path in files:
        e = env.run(path)
    c = e[LOG_COUNTS]
    assert c["read"] == data_row_count(files[-1])
    assert c["loaded"] + c["updated"] + c["skipped"] + c["rejected"] == c["read"]


def test_same_file_on_empty_database_gives_same_database(env, fixed_clock):
    """R39: the same input on a fresh start gives the same database. Both runs
    see the same clock, so only the input and rules can make them differ."""
    env.run(BOOKS_CSV)
    first = env.dump()
    os.remove(env.db_path)
    env.run(BOOKS_CSV)
    assert env.dump() == first


# ---------------------------------------------------------------------------
# Clarification examples, rules.md section 8 (version 1.1)
# ---------------------------------------------------------------------------

def test_example_36_rounded_product_code_not_used(env):
    """Example 36 (C1): a rounded product code gives no ISBN-13; warn."""
    e = load_one(env, 20036, "189221301X", "6.4557300301e+11")
    isbns_are(env, 20036, "189221301X", None)
    warned(e, 20036)


def test_example_37_rounded_9790_value_not_used(env):
    """Example 37 (C1, C3): pad the ISBN-10; a rounded 9790 value gives no ISBN-13; warn."""
    e = load_one(env, 20037, "6280560", "9.79000767239e+12")
    isbns_are(env, 20037, "0006280560", None)
    warned(e, 20037)


def test_example_38_unconfirmed_decimal_not_derived(env):
    """Example 38 (C2): an unconfirmed decimal value; no derivation; warn."""
    e = load_one(env, 20038, "0439139600", "0439139601.0")
    isbns_are(env, 20038, "0439139600", None)
    warned(e, 20038)


def test_example_39_unconfirmed_decimal_product_code_not_derived(env):
    """Example 39 (C2): an unconfirmed decimal product code; no derivation; warn."""
    e = load_one(env, 20039, "553609416", "76783609419.0")
    isbns_are(env, 20039, "0553609416", None)
    warned(e, 20039)


def test_example_40_decimal_confirmed_after_padding(env):
    """Example 40 (C2): R17 confirms the decimal value after padding; derive and log."""
    e = load_one(env, 20040, "195170342", "195170342.0")
    isbns_are(env, 20040, "0195170342", "9780195170344")
    repairs_logged(e, 20040, "9780195170344")


def test_example_41_invalid_979_value_flagged(env):
    """Example 41 (C3): an invalid 979 value contradicts the ISBN-10; warn and flag."""
    e = load_one(env, 20041, "0439139600", "9798351220410")
    isbns_are(env, 20041, "0439139600", None)
    warned(e, 20041)
    flagged(e, 20041)


def test_example_42_9790_value_treated_as_product_code(env):
    """Example 42 (C3): a 9790 ISMN is a product code; derive; warn and log."""
    e = load_one(env, 20042, "0439139600", "9790439139601")
    isbns_are(env, 20042, "0439139600", "9780439139601")
    warned(e, 20042)
    repairs_logged(e, 20042, "9780439139601")


def test_example_43_conflicting_pair_for_book_without_isbns(env):
    """Example 43 (C4): no ISBN accepted; skipped; flagged."""
    env.run_rows(new_book(20043, "", ""))
    e = env.run_rows(new_book(20043, "1555550126", "9781555550134"))
    counts_are(e, read=1, skipped=1)
    isbns_are(env, 20043, None, None)
    flagged(e, 20043)


def test_example_44_blank_raw_isbn_stored_as_empty_text(env):
    """Example 44 (C5): the blank raw isbn is stored as empty text; cleaned ISBN-10 is NULL."""
    load_one(env, 20044, "", "9798351220413")
    isbns_are(env, 20044, None, "9798351220413")
    book = env.book(20044)
    assert book["isbn"] == "", "raw isbn should be empty text, got {!r}".format(book["isbn"])
    assert book["isbn13"] == "9798351220413"


def test_example_45_formatting_only_duplicate_in_one_file(env):
    """Example 45 (C6): first row loaded; second skipped as a normalized duplicate."""
    e = env.run_rows(new_book(20045, "0-439-13960-0", ""), new_book(20045, "0439139600", ""))
    counts_are(e, read=2, loaded=1, skipped=1)
    isbns_are(env, 20045, "0439139600", "9780439139601")
    reason_contains(e, 20045, "normalized duplicate in input")


def test_example_46_exact_copy_of_rejected_row_skipped(env):
    """Example 46 (C7): the first copy is rejected (R26), the second skipped as an exact duplicate."""
    env.run_rows(new_book(20046, "0439139600", ""))
    before = env.book(20046)
    row = new_book(20046, "1620014750", "")
    e = env.run_rows(row, list(row))
    counts_are(e, read=2, rejected=1, skipped=1)
    reason_contains(e, 20046, "exact duplicate in input")
    assert env.book(20046) == before


def test_example_47_fill_that_contradicts_other_stored_isbn_rejected(env):
    """Example 47 (C8): the fill contradicts the stored ISBN-13; rejected; nothing changes."""
    env.run_rows(new_book(20047, "1854433017", "9780062398123"))
    isbns_are(env, 20047, None, "9780062398123")
    before = env.book(20047)
    e = env.run_rows(new_book(20047, "0439139600", "195170342.0"))
    counts_are(e, read=1, rejected=1)
    assert env.book(20047) == before


def test_example_48_valid_isbn10_moved_from_isbn13_column(env):
    """Example 48 (C9): move the valid ISBN-10, derive the ISBN-13, warn about the invalid isbn."""
    e = load_one(env, 20048, "1854433017", "0439139600")
    isbns_are(env, 20048, "0439139600", "9780439139601")
    warned(e, 20048)
    repairs_logged(e, 20048, "0439139600", "9780439139601")
