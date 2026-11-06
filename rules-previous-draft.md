# Book Ingestion Rules

> **APPROVED** on 2026-11-06 by Asha and George. Shared rules built from George's recommendations in "possible combined rules". Both partners use this identical file.

**Course:** MSAI-5523, Language of Computation, Module 4
**Partners:** Asha (`AshaAbdulkadir`) and George (`Georgec4444`)
**Prepared:** 2026-11-06

## Principles

1. Keep the book when its ISBN is bad. Reject the record when its identity cannot be trusted.
2. Never guess. Only the repairs in section 3 are allowed, and each is a fixed calculation from values in the same row. No AI model, network lookup or outside source is used during ingestion.
3. When a decision is ambiguous, flag the record for human review instead of guessing.
4. The same input and the same database state always give the same result, whoever runs the program. Row order within a file does not change what is stored, which rows are rejected, or the counts.
5. Every row read gets exactly one outcome: loaded, updated, skipped or rejected. Warnings are recorded separately.

## 1. Book identity and required fields

1. `book_id` is the primary identifier. Each `book_id` is stored at most once.
2. `goodreads_book_id` is an additional identity check. It must be unique across stored books.
3. A valid `book_id` or `goodreads_book_id` contains digits only and is greater than zero.
4. Every row must have a valid `book_id`, a valid `goodreads_book_id`, a nonempty `title` and a nonempty `authors` value, after trimming spaces at both ends. A row that fails is **rejected**.
5. Title and authors are compared after trimming spaces at both ends, and otherwise exactly and case sensitively. The `title` column is used, not `original_title`.
6. A new `book_id` whose `goodreads_book_id` already belongs to a different stored book is **rejected** and flagged for review.
7. An existing `book_id` that arrives with a different `goodreads_book_id`, title or authors is **rejected** and flagged for review. The stored book is not changed.
8. `work_id` is stored but plays no part in identity.

## 2. ISBN validation

1. A valid ISBN-10 has nine digits followed by a digit or capital `X`, and passes the ISBN-10 checksum.
2. A valid ISBN-13 has 13 digits, starts with 978 or 979 but not 9790 (an ISMN, used for music), and passes the ISBN-13 checksum.
3. ISBNs are handled as text, never as numbers, so leading zeros are kept.
4. A cell that is empty or holds only spaces is treated as empty.
5. A passing checksum shows a value is well formed, not that it belongs to the book in the row.

## 3. Permitted ISBN repairs and conversions

Every repair is recorded with the line, `book_id`, original value, repaired value and rule. A repair alone does not cause a warning.

1. **Formatting.** Remove hyphens and spaces. Change a final lowercase `x` to `X`.
2. **Leading zeros.** An ISBN-10 of 7 to 9 digits is padded with zeros on the left, only if the result passes the checksum.
3. **Wrong column.** A valid ISBN-13 in `isbn`, or a valid ISBN-10 in `isbn13`, moves to its correct field when that field is empty or holds the identical value. If the correct field holds a different valid ISBN, rule 4.1 applies. If it holds anything else, the misplaced value is not used and gets a warning.
4. **Conversion to fill an empty field.** An empty ISBN-13 is filled from a valid ISBN-10 (978 prefix). An empty ISBN-10 is filled from a valid 978 ISBN-13. A 979 ISBN-13 has no ISBN-10; that field stays empty without a warning.
5. **Scientific notation ISBN-13.** A value such as `9.78141652479e+12` is never stored as an ISBN. If its digits start with 978 or 979 (not 9790) and the row has a valid ISBN-10:
   * convert the ISBN-10 to its ISBN-13
   * round that to the number of significant digits written in the source value (`9.7804391396e+12` has 11), using round half to even and exact decimal arithmetic
   * if the result equals the source value, the converted ISBN-13 is used. If not, rule 4.2 applies

   With no valid ISBN-10, the ISBN-13 is left empty with a warning.
6. **Invalid ISBN-13 with a valid ISBN-10.** When the `isbn13` value is not a usable ISBN-13 and is not covered by 3.5 or rule 4.2, it is discarded with a warning, and the ISBN-13 is derived from the valid ISBN-10 as in 3.4. This covers non-ISBN codes such as Barnes & Noble IDs (2940), UPC codes and ISMNs (9790), as well as other damaged values.
7. **`.0` values in `isbn13`.** Remove the `.0` and pad as in 3.2. If the result equals the row's repaired ISBN-10, it confirms that ISBN-10 and the row is treated as having no ISBN-13 value (3.4 then fills it). Otherwise the `.0` value is discarded with a warning and handled under 3.6.

## 4. Conflicting identifiers and duplicate books

A conflicting ISBN never rejects a row whose identity is valid. The book is kept, the conflicting ISBN fields are left empty, a warning is added, and the row is flagged for review.

1. **Pair within a row.** A valid ISBN-10 and a valid ISBN-13 that do not correspond: both ISBN fields are left empty.
2. **Rounded value that disagrees.** A scientific notation ISBN-13 that fails the check in 3.5 against a valid ISBN-10: both ISBN fields are left empty.
3. **ISBN belongs to another book.** An incoming ISBN-10 or ISBN-13 that belonged to a different book at the start of the run is not assigned. Both ISBN fields of the incoming row are left empty, because the ISBN-10 and ISBN-13 of a row describe the same edition. The stored book keeps its ISBNs.
4. **Same ISBN on two books in one file.** If rows for two or more different books in the same file carry the same ISBN, and no book held it at the start of the run, both ISBN fields are left empty on every one of those rows.
5. **Different valid ISBN for the same book.** An existing book with a valid stored ISBN keeps it when an incoming row brings a different valid ISBN.
6. **Identity conflicts** are covered by rules 1.6 and 1.7 and reject the row.
7. **Exact duplicates in one file.** Rows sharing a `book_id` that are identical in all 23 fields: the earliest line is processed, and the others are **skipped** with "exact duplicate of line N".
8. **Different versions in one file.** Rows sharing a `book_id` that are not all identical are all **rejected** and flagged for review, including identical copies among them. Rows with different `book_id`s that share a `goodreads_book_id` are all rejected. A stored book is not changed.
9. **Possible duplicates.** Books with different `book_id`s and the same trimmed title and authors are all kept and never merged. Every such row gets a "possible duplicate" warning.

## 5. Missing or invalid information

These values are discarded with a warning. Nothing is guessed from them, though an ISBN-13 may still be derived from a valid ISBN-10 in the same row under 3.6. The row continues under section 1.

* An ISBN-10 with a wrong check digit, including a final `0` that would pass as `X`
* An ISBN with an extra digit, a missing digit, or a letter or other character inside the number
* A scientific notation ISBN-13 with no valid ISBN-10 in the row
* Both ISBN columns empty
* Any ISBN value in a form these rules do not cover

When the ISBN-10 is invalid and the ISBN-13 is valid, the ISBN-13 is kept and the ISBN-10 stays empty with a warning. When the ISBN-10 is invalid, nothing is derived from it.

## 6. Updates and repeated ingestion

An incoming row is compared with the stored book that has the same `book_id`, after rule 1.7 confirms its identity.

1. ISBNs are compared using repaired values. A difference only in raw format (`439139600` against `0439139600`) is not a change.
2. A blank or invalid incoming value never overwrites a stored value. A validated ISBN is never overwritten.
3. A stored ISBN that is empty is filled by a valid incoming ISBN that section 4 does not leave empty.
4. Other supplier fields are updated when the incoming value is nonblank and differs, compared exactly as text. Identity fields (`book_id`, `goodreads_book_id`, title, authors) and the raw `isbn` and `isbn13` columns are not updated this way.
5. Every applied change records the book, field, old value, new value and run timestamp.
6. A row with at least one applied change is **updated**. Otherwise it is **skipped** with "no change". Either can carry warnings.
7. **Reruns.** Every row is processed again under the same rules. Running the same file again with no other run in between creates no new books and no updates: rows loaded or updated before are skipped with "no change", exact duplicates are skipped again, and rejected rows are rejected again with the same reason. Warnings are recorded again.

## 7. Database and source data preservation

These rules set what must be preserved and how records behave. Table and column names are each partner's choice.

1. Source CSV files are never modified.
2. All 23 supplier fields of every stored book are preserved exactly as received, except that an empty or spaces only cell is stored as missing.
3. The repaired ISBN-10 and ISBN-13 are stored separately from the raw `isbn` and `isbn13` values. Repaired ISBNs are unique across stored books.
4. A loaded book keeps the raw `isbn` and `isbn13` of its loading row, even when a repaired value is empty. The raw values change only when a later row fills an empty repaired ISBN under 6.3; then each raw column whose incoming cell is nonblank takes that cell. A later raw value that is not applied is recorded in the log as a raw ISBN difference.
5. The old and new value of every applied change (6.5) are kept in the database.
6. Rejected rows are not stored as books. They are recorded in the log with their original values.
7. `books.db` and `ingestion-log.json` are kept in the same folder as `ingest.py` by default. Tests use a separate database and log, and never read or change the real ingestion results.

## 8. Logging, warnings and reporting

1. Each run appends one entry to `ingestion-log.json`, creating it if needed and keeping all earlier entries.
2. Each entry contains:
   * **Header:** input file name, SHA-256 of the file, run timestamp as `yyyy-MM-dd HH:mm:ss` local time with UTC offset (for example `2026-11-06 19:30:00 -06:00`), status (completed or failed), and counts of rows read, loaded, updated, skipped, rejected and warnings
   * **Counts by issue**, with what was done
   * **Repairs:** line, `book_id`, original value, repaired value, rule
   * **Changes:** line, `book_id`, field, old value, new value
   * **Raw ISBN differences:** line, `book_id`, column, stored raw value, incoming raw value, why it was not applied
   * **Records needing attention:** for every warning, skip and rejection, the line, `book_id`, title, issue, original value, outcome, reason, and whether a person should review it
   * **Failure reason**, for a failed run
3. Loaded, updated, skipped and rejected add up to the number of data rows read.
4. Rows are identified by the CSV line on which the record starts. The header is line 1, so the first data row is line 2.
5. `report.html` is a single self contained file that opens without a server, lets the user choose `ingestion-log.json`, and shows every run newest first with its counts, repairs, warnings, changes and records needing attention.

## 9. File errors and failure handling

1. The run fails, the database is unchanged, and a failed run entry is logged when the file is missing or unreadable, is not valid UTF-8, or its header is missing any of the 23 expected columns, repeats a column, or adds columns.
2. All database changes in a run are made together. If a run stops partway, nothing from it is kept and the run is logged as failed.
3. A data row with more or fewer fields than the header is **rejected** with "row has N fields, expected 23". The rest of the file continues.

## 10. Processing order

A row rejected or skipped at one stage takes no part in later stages. Checks against stored books use the database as it was at the start of the run.

| Stage | Step | Rules |
|---|---|---|
| 1 | File checks. Failure ends the run | 9.1 |
| 2 | Row field count | 9.3 |
| 3 | Identity fields present and valid | 1.3, 1.4 |
| 4 | Within the file: exact duplicates and different versions | 4.7, 4.8 |
| 5 | Identity against stored books | 1.6, 1.7 |
| 6 | ISBN validation and repair, each row on its own | 2, 3, 5 |
| 7 | ISBN conflicts within the row | 4.1, 4.2 |
| 8 | ISBN conflicts with stored books, then across rows of the file | 4.3, 4.4 |
| 9 | Possible duplicate warnings | 4.9 |
| 10 | Changes to existing books | 4.5, 6 |
| 11 | Outcome: rejected; exact duplicate skipped; loaded (new `book_id`); updated; skipped "no change" | 6.6 |
| 12 | Save all changes together, then append the log entry | 8, 9.2 |

## 11. ISBN test examples

**Run 1** loads books.csv into an empty database, **Run 2** loads books.csv again, and **Run 3** then loads books-batch2.csv. **H** is a made-up row with its database state stated. The made-up ISBNs `0300000006` and `0300000014` pass their checksums and appear in neither file. Line numbers are CSV lines.

| # | Run and state | Row | Raw `isbn` / `isbn13` | Outcome | Stored ISBN-10 / ISBN-13 | Reason |
|---|---|---|---|---|---|---|
| 1 | Run 1 | books.csv line 10, book 9, Angels & Demons | `1416524797` / `9.78141652479e+12` | Loaded | `1416524797` / `9781416524793` | Converted ISBN-13 rounds to the source value (3.5) |
| 2 | Run 1 | line 2, book 1, The Hunger Games | `439023483` / `9.78043902348e+12` | Loaded | `0439023483` / `9780439023481` | Padded, then converted and checked (3.2, 3.5) |
| 3 | Run 1 | line 5999, book 5998, Wanted | `098870742X` / `9.7809887074e+12` | Loaded | `098870742X` / `9780988707429` | Source shows 11 significant digits. `9780988707429` rounded to 11 digits matches (3.5) |
| 4 | Run 1 | line 623, book 622, Nights in Rodanthe | `446612707` / `9.78055381395e+12` | Loaded with a warning, flagged | empty / empty | `9780446612708` rounds to `9.78044661271e+12`, not the source value (4.2) |
| 5 | Run 1 | line 1107, book 1106, The Great Divorce | `6280560` / `9.79000767239e+12` | Loaded with a warning | `0006280560` / `9780006280569` | Padded from 7 digits. 9790 is an ISMN, so it is discarded and the ISBN-13 derived (3.2, 3.6) |
| 6 | Run 1 | line 2895, book 2894, Sailor Moon #1 | `189221301X` / `6.45573003012e+11` | Loaded with a warning | `189221301X` / `9781892213013` | Product code discarded, ISBN-13 derived (3.6) |
| 7 | Run 1 | line 8175, book 8174, Washington's Crossing | `195170342` / `195170342.0` | Loaded | `0195170342` / `9780195170344` | `.0` value equals the ISBN-10, then ISBN-13 filled (3.7, 3.4) |
| 8 | H, empty database | new book 10030, otherwise valid | `0300000006` / `300000014.0` | Loaded with a warning | `0300000006` / `9780300000009` | `.0` value pads to a different ISBN-10, so it is discarded and the ISBN-13 derived (3.7, 3.6) |
| 9 | Run 1 | line 1544, book 1543, The Racketeer | `385535144` / `9.78038553514e+12` | Loaded with a warning | empty / empty | `0385535144` fails the checksum, so nothing can be checked or derived (5) |
| 10 | Run 1 | line 107, book 106, Bossypants | empty / empty | Loaded with a warning | empty / empty | No ISBN. Identity is valid (5) |
| 11 | Run 3 | books-batch2.csv line 16, book 10011, Tides of Marrow Bay | `1555550126` / `9781555550134` | Loaded with a warning, flagged | empty / empty | Both valid, but `1555550126` converts to `9781555550127` (4.1) |
| 12 | Run 3 | line 24, book 10013, Paper Moons | `1416524797` / empty | Loaded with a warning, flagged | empty / empty | Book 9 already holds this ISBN and keeps it (4.3) |
| 13 | Run 3 | lines 14 and 15, book 10001, The Lantern Keeper's Daughter | `1528746309` / `9781528746304` on both | Line 14 loaded, line 15 skipped | `1528746309` / `9781528746304` | Line 15: "exact duplicate of line 14" (4.7) |
| 14 | Run 3 | line 30, book 10002, Salt and Ember | `0-450-19827-8` / `9780450198274` | Loaded | `0450198278` / `9780450198274` | Hyphens removed. Pair corresponds (3.1) |
| 15 | Run 3 | line 18, book 10014, An Atlas of Small Kindnesses | `9781982147600` / empty | Loaded | `1982147601` / `9781982147600` | ISBN-13 moved, ISBN-10 filled (3.3, 3.4) |
| 16 | Run 3 | line 10, book 10006, Notes from the Night Ferry | empty / `9798351220413` | Loaded, no warning | empty / `9798351220413` | A 979 ISBN-13 has no ISBN-10 (3.4) |
| 17 | Run 3 | line 20, book 10009, Borrowed Light | `15287463097` / empty | Loaded with a warning | empty / empty | Extra digit. No digit is removed (5) |
| 18 | Run 2 | all 10,000 rows of books.csv | as in run 1 | All skipped, "no change" | unchanged | Run 1 rejected no row. Warnings recorded again (6.7) |
| 19 | Run 3 | line 4, book 24, Goblet of Fire | `0439139600` / `9780439139601` | Skipped | `0439139600` / `9780439139601` | Same repaired values as stored. Raw values logged as raw ISBN differences (6.1, 7.4) |
| 20 | Run 3 | line 26, book 25, Deathly Hallows | empty / empty | Skipped | `0545010225` / `9780545010221` | Blanks never overwrite (6.2) |
| 21 | Run 3 | line 5, book 132, The Five People You Meet in Heaven | `1401308589` / `9.78140130858e+12` | Updated | `1401308589` / `9781401308582` | `ratings_count` 449501 to 451425, `work_ratings_count` 474699 to 476623, `ratings_5` 165040 to 166964, with old and new values kept (6.4, 6.5) |
| 22 | H, after run 3. Book 106 has empty ISBNs | book 106, otherwise unchanged | `0300000006` / empty | Updated | `0300000006` / `9780300000009` | Empty ISBN filled (6.3) |
| 23 | H, after run 1 | book 9, otherwise unchanged | `0300000014` / empty | Skipped with a warning, flagged | `1416524797` / `9781416524793` | A different valid ISBN does not replace the stored one (4.5) |
| 24 | H, after run 1 | book 9 with title `Angels and Demons` | `1416524797` / empty | Rejected, flagged | unchanged | Title differs from the stored book (1.7) |
| 25 | H, after run 1 | new book 10020 with `goodreads_book_id` 960 | empty / empty | Rejected, flagged | none | 960 belongs to book 9 (1.6) |
| 26 | H, any state | a row with 22 fields | any | Rejected | none | "row has 22 fields, expected 23" (9.3) |
| 27 | H, any state | `python3 ingest.py missing.csv` | none | Failed run, no row outcomes | unchanged | Failed run entry logged (9.1) |
