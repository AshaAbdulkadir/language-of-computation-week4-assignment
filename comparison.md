# Module 4 Database Comparison

**The two databases do not hold the same data.** They differ in one value for one book.

| Database | Books |
|---|---|
| Mine: `books.db` (Asha) | 10,014 |
| Partner's: `partner/books.db` (George) | 10,014 |

## Differences

### Books only in mine

None.

### Books only in my partner's

None.

### Books in both with a different value

| book_id | Title | Column (mine / partner's) | My value | Partner's value |
|---|---|---|---|---|
| 8174 | Washington's Crossing | `isbn_13_clean` / `isbn13_clean` | `9780195170344` | NULL |

Every other compared value of all 10,014 books is identical.

## How the comparison was made

**Same book.** Rows were matched on `book_id`, the primary book key in `rules.md` (R05).

**Columns compared.** All 23 supplier columns and the cleaned ISBNs, chosen before the comparison:

| Mine | Partner's | Compared as |
|---|---|---|
| `book_id` and the 22 other supplier columns | Same names | Each with its same-named column |
| `isbn_10_clean` | `isbn10_clean` | Cleaned ISBN-10 |
| `isbn_13_clean` | `isbn13_clean` | Cleaned ISBN-13 |

**Left out.** `goodreads_id_clean`, which only exists in mine (the validated Goodreads ID); the raw `goodreads_book_id` is compared instead. Neither database has a column that records when a row was loaded.

**Values** were compared exactly, so NULL and empty text count as different. Both databases were opened read-only, and `books.db` was not changed.

**Sources.**
* `partner/books.db` was downloaded from `https://github.com/Georgec4444/language-of-computation-week4-assignment/raw/assignment/books.db` (commit `98c1477`).
* SHA-256 of mine: `ba9b0a4d0c0bb9b05f7dbd64508639284cfc88071d60e1a326571a24c7e962e1`. SHA-256 of partner's: `e8434b286fad5ac92cd37cb9d3e0764303719a77db854734d2603add7584b1eb`.
* Both programs ingested byte-identical `books.csv` (`4d21d0e0…acb76a`) and `books-batch2.csv` (`bf884855…b53df5`), in the same three runs (R39): `books.csv`, `books.csv` again, then `books-batch2.csv`. Both produced the same counts on every run: 10,000 loaded; then 10,000 skipped; then 14 loaded, 4 updated, 13 skipped and 0 rejected.

## Why book 8174 differs

| | Value |
|---|---|
| Raw `isbn` | `195170342` |
| Raw `isbn13` | `195170342.0` |
| Cleaned ISBN-10, both databases | `0195170342` (leading zero restored, R12) |

R17 accepts a `.0` value in `isbn13` only when removing `.0` gives "exactly the same valid ISBN-10 already present in that row's `isbn` field (after permitted simple formatting)". Removing `.0` gives `195170342`, nine digits, which only equals the row's ISBN-10 `0195170342` once the leading zero is restored.

* **My program** counts leading-zero padding as permitted formatting, so the value is confirmed and the ISBN-13 `9780195170344` is derived.
* **My partner's program** only confirms values that are already ISBN-10-shaped, so it stores NULL with a warning. Its log records: "decimal-looking value is not an ISBN; not stripped; stored NULL".

Both readings are defensible under version 1.0 of R17. This is the only row in either file where they give different results.

## Differences that do not affect the data

* **Layout (allowed by R30):** different names for the cleaned ISBN columns, my extra `goodreads_id_clean` column, and unique indexes in mine.
* **Logs:** the same runs, counts, fingerprints and per-row reasons, in different JSON structures (R33, R34).
* **Tests:** independent suites (R40). Mine has 59 tests and my partner's 67; both pass against their own program.
* **Rules:** version 1.0 is the last version we both hold identically. Each of us wrote a version 1.1 with clarifications C1 to C9, and they differ on three points. C2 (padding in R17) causes the book 8174 difference. C3 (`9790` values) and C6 (the skip reason for a formatting-only repeat) don't change either database, because the data has no case where they apply.

## To make the databases match

Agree on one reading of R17 padding, write it identically into a shared version 1.1 of `rules.md`, and update the program that differs. Only book 8174 would change.
