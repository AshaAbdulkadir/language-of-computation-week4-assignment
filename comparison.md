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

## Why our data differs

Our data is not the same, but only by one value: the cleaned ISBN-13 of book 8174 (*Washington's Crossing*). Everything else in both databases matches. George has not published his own `comparison.md` yet, so this section is based on his database, his ingestion log, his `rules.md` draft and his test suite. I will update it once we have talked it through together.

**Which rule it comes from.** The difference comes from R17, the narrow `.0` exception, and how it works together with R12. The row has `isbn=195170342` and `isbn13=195170342.0`. R17 only confirms the `.0` value when it matches the row's ISBN-10 "after permitted simple formatting". R12 says restoring leading zeros is an approved repair, but it lists it separately from removing spaces and hyphens. I read "permitted simple formatting" as including the padding, so `195170342` becomes `0195170342`, matches, and I derive `9780195170344`. George reads R17 as only confirming values that are already ISBN-10-shaped, so his program stores NULL.

**Did the rule let it through?** Yes. R17 does not say whether padding counts, and both readings fit the wording of version 1.0. When we each wrote our clarifications for version 1.1, I wrote that padding counts (C2) and George's C2 does not mention padding, so the gap is still open.

**Did the tests let it through?** Yes. None of our 35 shared examples has a `.0` value that needs padding: example 18 uses a full ten-digit `0439139600.0`, and example 19 has a blank `isbn`. My own suite added example 40, which checks my reading, and George's clarification tests check unconfirmed decimal values but not this case. So each suite passes with its own reading, and no shared test could catch the difference.

**Did the code let it through?** No, the code is not the cause. Each program does what its own reading of the rule says. Neither has a bug here.

**How we close it.** We agree on one reading of R17, write it the same way into one shared version 1.1 together with C3 and C6, add an example for it, and update the program that differs. After that our databases should be identical.
