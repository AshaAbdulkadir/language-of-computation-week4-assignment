# Shared Book Ingestion Rules (Draft)

> **NOT YET APPROVED.** Proposed shared rules for Asha and George. Not the final `rules.md`. Nothing here is binding until both partners approve it.

**Course:** MSAI-5523, Language of Computation, Module 4
**Partners:** Asha (`AshaAbdulkadir`) and George (`Georgec4444`)
**Prepared:** 2026-11-05
**Rationale, decision sources and review notes:** `shared-rules-notes.md` (optional reading)

## Principles

1. Identity problems reject a row. ISBN problems never do: a book with a valid identity is kept, its unusable ISBNs are left blank, and the row gets a warning.
2. No guessing. Only the repairs in section 4 are allowed, each a fixed calculation from the same row.
3. Row order does not change what is stored, which rows are rejected, or the counts. Checks across rows use the database as it was at the start of the run and the whole file at once.
4. Every row has exactly one outcome: loaded, updated, skipped or rejected. Warnings are tracked separately.

## 1. Input and run

1. The command is `python3 ingest.py <file.csv>`. `books.db` and `ingestion-log.json` are kept in the same folder as `ingest.py`, wherever it is run from.
2. Source CSV files are never modified.
3. No AI model, network lookup or outside source is used at run time.
4. The run fails, the database is unchanged, and a failed run entry is logged when the file is missing or unreadable, is not valid UTF-8, or its header is missing, repeats, or adds to the 23 expected columns.
5. All database changes in a run are made in one transaction. If the run stops partway, nothing from it is kept and the run is logged as failed.
6. A data row with more or fewer fields than the header is rejected with the reason "row has N fields, expected 23". The rest of the file continues.
7. A cell that is empty or holds only spaces is treated as empty and stored as NULL.
8. Rows are numbered by the CSV line on which the record starts. The header is line 1.

## 2. Book identity

1. A valid `book_id` or `goodreads_book_id` contains digits only and is greater than zero.
2. Every row needs a valid `book_id`, a valid `goodreads_book_id`, and a nonempty `title` and `authors` after trimming spaces at both ends. Otherwise it is rejected.
3. `book_id` is the primary key. `goodreads_book_id` is unique across stored books.
4. A new `book_id` whose `goodreads_book_id` belongs to a different stored book is rejected.
5. An existing `book_id` that arrives with a different `goodreads_book_id`, `title` or `authors` is rejected. The stored book is not changed.
6. Title and authors are compared after trimming spaces at both ends, and are otherwise exact and case sensitive. The `title` column is used, not `original_title`.
7. Within one file:
   * Rows sharing a `book_id` that are identical in all 23 fields: the earliest line is processed and the others are skipped with "exact duplicate of line N".
   * Rows sharing a `book_id` that are not all identical: every one of them is rejected, including identical copies.
   * Different `book_id`s sharing a `goodreads_book_id`: all of those rows are rejected.
   * A stored book is not changed by these rejections.
8. Books with different `book_id`s but the same trimmed title and authors are all kept, never merged. Every row in the file that matches a stored book or another row in this way gets a "possible duplicate" warning.
9. `work_id` is stored but plays no part in identity.

## 3. ISBN validity

1. A valid ISBN-10 has nine digits followed by a digit or capital `X`, and passes the ISBN-10 checksum.
2. A valid ISBN-13 has 13 digits, starts with 978 or 979 but not 9790 (an ISMN), and passes the ISBN-13 checksum.
3. ISBNs are handled as text, never as numbers.
4. A passing checksum shows a value is well formed, not that it belongs to the book in the row.

## 4. Approved repairs

Each repair is logged with line, raw value, result and rule. A repair alone causes no warning.

1. **Formatting.** Remove hyphens and spaces. Change a final lowercase `x` to `X`.
2. **Leading zeros.** An ISBN-10 of 7 to 9 digits is padded with zeros on the left, only if the result passes the checksum.
3. **Wrong column.** A valid ISBN-13 in `isbn`, or a valid ISBN-10 in `isbn13`, moves to its correct field when that field is empty or holds the identical value. If that field holds a different valid ISBN, rule 6.1 applies. If it holds anything else, the misplaced value is not used and gets a warning.
4. **`.0` values in `isbn13`.** Remove the `.0` and pad as in 4.2.
   * If the result equals the row's repaired ISBN-10, it is a copy that confirms it, and the row is treated as having no ISBN-13 value.
   * If the result is a valid ISBN-10 that does not equal the row's repaired ISBN-10, or the row has no valid ISBN-10, it is a conflicting ISBN-10 under rule 6.1.
   * Otherwise the value is judged by its digits under 4.7 or section 5.
5. **Filling in.** An empty field is filled by converting the valid other form: ISBN-10 to its 978 ISBN-13, or a 978 ISBN-13 to its ISBN-10. A 979 ISBN-13 has no ISBN-10; that field stays blank without a warning.
6. **Rounded ISBN-13s.** A scientific notation value (such as `9.78141652479e+12`) is never stored as an ISBN. If its digits start with 978 or 979 (not 9790) and the row has a valid ISBN-10:
   * convert the ISBN-10 to an ISBN-13
   * round it to the number of significant digits written in the source value (`9.7804391396e+12` has 11), using round half to even and exact decimal arithmetic
   * if the result equals the source value, use the converted ISBN-13. Otherwise rule 6.1 applies

   With no valid ISBN-10, the ISBN-13 is left blank with a warning.
7. **Non-ISBN codes in `isbn13`.** A value whose digits (after removing `.0` or expanding scientific notation) do not start with 978 or 979, or start with 9790, is not an ISBN. Examples are Barnes & Noble IDs (2940), UPC codes and ISMNs. It is not stored, the row gets a warning, and the ISBN-13 is filled from a valid ISBN-10 under 4.5.

## 5. Values not repaired

These are left blank with a warning. Nothing is calculated from them, and the field is not filled from the other ISBN.

* A wrong check digit, including a final `0` that would pass as `X`
* An ISBN-13 cut short, including a `.0` value that starts with 978 or 979 but has too few digits
* An extra digit
* A letter or other character inside the number
* A rounded ISBN-13 with no valid ISBN-10 in the row
* Any value in a form these rules do not cover

If the ISBN-10 is invalid and the ISBN-13 is valid, the ISBN-13 is kept and the ISBN-10 stays blank with a warning.

## 6. ISBN conflicts

A conflict blanks both ISBN fields of the affected row, adds a warning, and flags the row for review. It never rejects a row with a valid identity.

1. **Within a row.** A valid ISBN-10 and a valid ISBN-13 that do not correspond; a rounded ISBN-13 that disagrees with the valid ISBN-10 under 4.6; or a conflicting `.0` ISBN-10 under 4.4.
2. **With a stored book.** An incoming ISBN-10 or ISBN-13 that belonged to a different book at the start of the run. The stored book keeps its ISBNs.
3. **Within one file.** The same ISBN carried by rows for two or more different books, when no book held it at the start of the run. Every one of those rows is blanked, including a row for an existing book that would otherwise fill a blank ISBN.
4. **With the same book.** An existing book with a valid stored ISBN and an incoming different valid ISBN: the stored value is kept.
5. Ownership is checked against repaired and converted values, both ISBN-10 and ISBN-13.

## 7. Existing books, updates and reruns

An incoming row is compared with the stored book that has the same `book_id`, after rule 2.5 confirms the identity.

1. ISBNs are compared using repaired values. A difference only in raw format (`439139600` against `0439139600`) is not a change.
2. A blank incoming value never overwrites a stored value.
3. A blank stored ISBN is filled by a valid incoming ISBN that section 6 does not blank.
4. Other source columns are compared exactly as text and a nonblank differing value is applied, except the identity fields in rule 2.5 and the raw `isbn` and `isbn13` columns (rule 8.2).
5. Every applied change is recorded in the change history.
6. A row with at least one applied change is **updated**. Otherwise it is **skipped** with "no change". Either can carry warnings.
7. **Reruns.** Every row is processed again under the same rules. Running the same file again with no other run in between: loaded and updated rows are skipped with "no change", exact duplicates are skipped again, and rejected rows are rejected again with the same reason. Warnings are recorded again. If other files ran in between, a row is judged against the database as it is now.

## 8. Database

1. **`books`**, one row per book:
   * `book_id`: integer, primary key
   * `goodreads_book_id`: integer, unique
   * the other 21 source columns, including raw `isbn` and `isbn13`, as text exactly as received (empty or spaces only cells as NULL)
   * `clean_isbn10` and `clean_isbn13`: the repaired ISBNs, unique when not NULL
2. **Raw ISBN values.** A loaded book keeps the raw `isbn` and `isbn13` of its loading row, even when the repaired value is NULL. They change only when a later row fills a blank ISBN under 7.3; then each raw column with a nonblank incoming cell takes that cell. A later raw value that is not applied is recorded in the log under "raw ISBN differences" and does not change the database.
3. **`book_changes`**, one row per changed column: `book_id`, column, old value, new value, run timestamp.
4. Rejected rows are not stored in the database. They are recorded in the log.

## 9. Outcomes

* **Loaded:** a new book was stored, with or without warnings.
* **Updated:** an existing book had at least one change applied.
* **Skipped:** an existing book had nothing to change, or the row was an exact duplicate within the file.
* **Rejected:** the row was not stored, with the reason recorded.

Loaded, updated, skipped and rejected add up to the number of data rows read.

## 10. Log and report

1. Each run appends one entry to `ingestion-log.json`, creating the file if needed and keeping earlier entries.
2. Each entry contains:
   * **Header:** file name, SHA-256, run timestamp as `yyyy-MM-dd HH:mm:ss` local time with UTC offset (for example `2026-11-05 19:30:00 -06:00`), status (completed or failed), and counts of rows read, loaded, updated, skipped, rejected and warnings
   * **Counts by issue**, with what was done
   * **Repairs:** line, `book_id`, raw value, result, rule
   * **Changes:** line, `book_id`, column, old value, new value
   * **Raw ISBN differences:** line, `book_id`, column, stored raw value, incoming raw value, reason not applied
   * **Records needing attention:** for every warning, skip and rejection, the line, `book_id`, title, issue, raw value, outcome, reason, and whether a person should review it
   * **Failure reason**, for a failed run
3. `report.html` is one self contained file that opens without a server, has a button to choose `ingestion-log.json`, and shows every run newest first with all of the above.

## 11. Processing order

A row rejected or skipped at one stage takes no part in later stages.

| Stage | Step | Rules |
|---|---|---|
| 1 | File checks. Failure ends the run | 1.4 |
| 2 | Row field count | 1.6 |
| 3 | Identity fields present and valid | 2.1, 2.2 |
| 4 | Within the file: group by `book_id`, then by `goodreads_book_id` | 2.7 |
| 5 | Against books stored at the start of the run | 2.4, 2.5 |
| 6 | ISBN repair, each row on its own. `isbn13` is classified in this order: empty; valid ISBN-13; valid ISBN-10 in the wrong column; `.0` value (4.4); other `.0` or scientific notation value by its digits (4.6, 4.7, 5) | 3, 4, 5 |
| 7 | Conflicts within the row | 6.1 |
| 8 | Conflicts with stored books, then across rows of the file | 6.2, 6.3, 6.5 |
| 9 | Possible duplicate warnings | 2.8 |
| 10 | Changes to existing books | 6.4, 7, 8.2 |
| 11 | Outcome, in this order: rejected; exact duplicate skipped; loaded (new `book_id`); updated; skipped "no change" | 9 |
| 12 | Write everything in one transaction, then append the log entry | 1.5, 10 |

## 12. ISBN examples

Runs, in order: **Run 1** loads books.csv into an empty database. **Run 2** loads books.csv again. **Run 3** loads books-batch2.csv. **H** marks a made-up row with its database state stated. The made-up ISBNs `0300000006`, `0300000014` and `0300000022` pass their checksums and appear in neither file. Line numbers are CSV lines, header on line 1.

| # | Run and state | Row | Raw `isbn` / `isbn13` | Outcome | `clean_isbn10` / `clean_isbn13` | Reason |
|---|---|---|---|---|---|---|
| 1 | Run 1 | books.csv line 10, book 9, Angels & Demons | `1416524797` / `9.78141652479e+12` | Loaded | `1416524797` / `9781416524793` | Converted ISBN-13 rounds to the source value (4.6) |
| 2 | Run 1 | line 2, book 1, The Hunger Games | `439023483` / `9.78043902348e+12` | Loaded | `0439023483` / `9780439023481` | Padded, then rebuilt (4.2, 4.6) |
| 3 | Run 1 | line 5999, book 5998, Wanted | `098870742X` / `9.7809887074e+12` | Loaded | `098870742X` / `9780988707429` | Source shows 11 significant digits. `9780988707429` rounded to 11 digits is `97809887074`, which matches (4.6) |
| 4 | Run 1 | line 623, book 622, Nights in Rodanthe | `446612707` / `9.78055381395e+12` | Loaded with a warning, flagged | NULL / NULL | `9780446612708` rounds to `9.78044661271e+12`, not the source value (6.1) |
| 5 | Run 1 | line 1107, book 1106, The Great Divorce | `6280560` / `9.79000767239e+12` | Loaded with a warning | `0006280560` / `9780006280569` | Padded from 7 digits. 9790 is an ISMN, so the ISBN-13 is filled from the ISBN-10 (4.2, 4.7) |
| 6 | Run 1 | line 2895, book 2894, Sailor Moon #1 | `189221301X` / `6.45573003012e+11` | Loaded with a warning | `189221301X` / `9781892213013` | Product code is not an ISBN. ISBN-13 filled from the ISBN-10 (4.7) |
| 7 | Run 1 | line 8175, book 8174, Washington's Crossing | `195170342` / `195170342.0` | Loaded | `0195170342` / `9780195170344` | `.0` value equals the ISBN-10. ISBN-13 filled in (4.4, 4.5) |
| 8 | H, empty database | new book 10030, otherwise valid | `0300000006` / `300000014.0` | Loaded with a warning, flagged | NULL / NULL | `.0` value pads to `0300000014`, a valid ISBN-10 different from `0300000006` (4.4, 6.1) |
| 9 | Run 1 | line 1544, book 1543, The Racketeer | `385535144` / `9.78038553514e+12` | Loaded with a warning | NULL / NULL | `0385535144` fails the checksum. No valid ISBN-10 to check the rounded value (5) |
| 10 | Run 1 | line 917, book 916, Reading Lolita in Tehran | `812971060` / `9.78081297106e+12` | Loaded with a warning | NULL / NULL | `0812971060` fails the checksum. The `0` is not changed to `X` (5) |
| 11 | Run 1 | line 107, book 106, Bossypants | empty / empty | Loaded with a warning | NULL / NULL | No ISBN. Identity is valid (2.2, 5) |
| 12 | Run 2 | all 10,000 rows of books.csv | as in run 1 | All skipped, "no change" | unchanged | Run 1 rejected no row. Warnings such as book 622's are recorded again (7.7) |
| 13 | Run 3 | books-batch2.csv line 4, book 24, Goblet of Fire | `0439139600` / `9780439139601` | Skipped | `0439139600` / `9780439139601` | Repaired values equal the stored ones. Raw values logged as raw ISBN differences (7.1, 8.2) |
| 14 | Run 3 | line 26, book 25, Deathly Hallows | empty / empty | Skipped | `0545010225` / `9780545010221` | Blanks do not overwrite (7.2) |
| 15 | Run 3 | line 5, book 132, The Five People You Meet in Heaven | `1401308589` / `9.78140130858e+12` | Updated | `1401308589` / `9781401308582` | `ratings_count` 449501 to 451425, `work_ratings_count` 474699 to 476623, `ratings_5` 165040 to 166964. Three history rows (7.4) |
| 16 | Run 3 | line 16, book 10011, Tides of Marrow Bay | `1555550126` / `9781555550134` | Loaded with a warning, flagged | NULL / NULL | Both valid, but `1555550126` converts to `9781555550127` (6.1) |
| 17 | Run 3 | line 24, book 10013, Paper Moons | `1416524797` / empty | Loaded with a warning, flagged | NULL / NULL | Book 9 held this ISBN at the start of the run and keeps it (6.2) |
| 18 | Run 3 | lines 14 and 15, book 10001, The Lantern Keeper's Daughter | `1528746309` / `9781528746304` on both | Line 14 loaded, line 15 skipped | `1528746309` / `9781528746304` | Line 15: "exact duplicate of line 14" (2.7) |
| 19 | Run 3 | line 30, book 10002, Salt and Ember | `0-450-19827-8` / `9780450198274` | Loaded | `0450198278` / `9780450198274` | Hyphens removed. Pair corresponds (4.1) |
| 20 | Run 3 | line 18, book 10014, An Atlas of Small Kindnesses | `9781982147600` / empty | Loaded | `1982147601` / `9781982147600` | ISBN-13 moved, ISBN-10 filled in (4.3, 4.5) |
| 21 | Run 3 | line 10, book 10006, Notes from the Night Ferry | empty / `9798351220413` | Loaded, no warning | NULL / `9798351220413` | A 979 ISBN-13 has no ISBN-10 (4.5) |
| 22 | Run 3 | line 20, book 10009, Borrowed Light | `15287463097` / empty | Loaded with a warning | NULL / NULL | Extra digit. No digit is removed (5) |
| 23 | H, after run 3. Book 106 has NULL ISBNs | book 106, otherwise unchanged | `0300000006` / empty | Updated | `0300000006` / `9780300000009` | Blank ISBN filled. History rows for `clean_isbn10`, `clean_isbn13` and raw `isbn` (7.3, 8.2) |
| 24 | H, after run 1 | book 9, otherwise unchanged | `0300000014` / empty | Skipped with a warning, flagged | `1416524797` / `9781416524793` | A different valid ISBN does not replace the stored one (6.4) |
| 25 | H, after run 1 | book 9 with title `Angels and Demons` | `1416524797` / empty | Rejected | unchanged | Title differs from the stored book (2.5) |
| 26 | H, after run 1. Book 106 has NULL ISBNs. One file holds book 106 and new book 10025 | both rows | `0300000022` / empty on both | Book 106 skipped with a warning. Book 10025 loaded with a warning. Both flagged | NULL / NULL on both | Two different books carry an ISBN no book held at the start of the run (6.3) |
| 27 | H, after run 1. One file holds new book 10024 on lines 2 and 3 (identical) and line 4 (different `ratings_count`) | all three rows | `0300000022` / empty | All three rejected | none | Rows sharing a `book_id` are not all identical (2.7) |
| 28 | H, any state | a row with 22 fields | any | Rejected | none | "row has 22 fields, expected 23" (1.6) |
