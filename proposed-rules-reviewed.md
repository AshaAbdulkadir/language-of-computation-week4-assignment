# Proposed Shared Book Ingestion Rules (Reviewed)

> **NOT YET APPROVED.** This is a proposal for Asha and George to review together. It is not the final `rules.md`. Nothing here is binding until both partners approve it.

**Course:** MSAI-5523, Language of Computation, Module 4
**Partners:** Asha (`AshaAbdulkadir`) and George (`Georgec4444`)
**Prepared:** 2026-11-05
**Revision of:** `proposed-rules.md`, reviewed for internal consistency. The policy choices are unchanged. Section 14 lists every change, every item that needs approval, and how each example was checked.
**Based on:** `asha-week3-rules.md`, George's Week 3 `rules.md` (`Georgec4444/language-of-computation-week3-assignment`, branch `assignment`), `rules-comparison.md`, `george-rules-comparison.md`, and `part1-review.md`

Every recommendation is judged against four criteria: the same input and database state always give the same result (deterministic), no value is stored unless the files prove it (accurate), anyone can rerun and audit a run (reproducible), and the design stays as simple as the data allows (practical).

Items marked **[A1]** to **[A11]** are clarifications or decisions added in this review. Each one needs approval and is explained in section 14.2.

## Guiding principles

1. **Identity problems reject a row. ISBN problems never do.** A row is rejected only when we cannot tell which book it is. A book with a valid identity is kept even when its ISBNs are unusable: the ISBN is left blank and the row gets a warning.
2. **No guessing.** Only the repairs listed in section 4 are allowed. Every repair is a fixed calculation from values in the same row.
3. **Row order does not change the result.** Reordering the rows of a file never changes what is stored, which rows are rejected, or the outcome counts. Every check that involves more than one row uses the database as it was at the start of the run and the whole file at once (section 11). The only place order appears is in labeling exact duplicates: the earliest line is processed and the later identical lines are reported as skipped duplicates of it. Because those lines are identical, which line number carries which label changes neither the stored data nor the counts.
4. **Every row has exactly one outcome**: loaded, updated, skipped or rejected. Warnings are tracked separately.

## Why the main decisions were made

**Book identity (section 2).** `book_id` is the database key, because it is the supplier's key and it is what the supplier reuses when a book is sent again (every repeated book in books-batch2.csv keeps its `book_id`). `goodreads_book_id` must also be valid and unique, because it is an independent check that catches a reused or mistyped `book_id`. Both columns are unique across books.csv, so requiring both rejects nothing in the current data. Title and author must be present and must not change for an existing book, because a changed title under the same key means the key no longer identifies one book.

**Conflicting ISBNs (section 6).** When the two ISBN values in a row disagree, nothing in the files says which one is right. Both are left blank and the row is flagged for review, but the book is kept, because its identity is fine. This applies the same way whether the second value is a full ISBN-13 (Tides of Marrow Bay) or a rounded one whose surviving digits disagree (Nights in Rodanthe and 11 other rows). The rounded case is treated as a conflict because the surviving digits are enough to show the two values describe different ISBNs. Keeping only the ISBN-10 would mean trusting one side without evidence. When an incoming ISBN already belongs to another book, the existing book keeps it and the incoming book is stored without it.

**Scientific notation rounding (section 4.6).** Rebuilt ISBN-13s are compared using round half to even at the number of significant digits shown, with exact decimal arithmetic. This is the method the source data matches: across 9,251 rows in books.csv with a valid ISBN-10 and a rounded 978 or 979 value, round half to even leaves 12 disagreements, while round half up leaves 408. Using round half up would wrongly blank 396 good ISBN-13s. This review found that comparing at the digits shown is slightly looser than the data's real precision, which affects one row (book 5998). See **[A10]**.

**Updates (section 7).** Fields that describe the book's activity, such as rating counts, change legitimately between deliveries, so they are updated and every old value is kept in a change history table. Identity fields (`book_id`, `goodreads_book_id`, title, authors) never change automatically: a row that tries to change them is rejected. A valid stored ISBN is never replaced by a different one. A blank never overwrites anything.

## 1. Input and run

1. The command is `python3 ingest.py <file.csv>`. `books.db` and `ingestion-log.json` are kept in the same folder as `ingest.py`, wherever the command is run from.
2. The source CSV files are never modified.
3. No AI model, network lookup or outside source is used at run time. Every decision comes from the file, the database and these rules.
4. The run fails, the database is left unchanged, and a failed run entry is written to the log when:
   * the file is missing or cannot be read
   * the file is not valid UTF-8
   * the header is missing any of the 23 expected columns, repeats a column, or has extra columns
5. All database changes in a run are made in one transaction. If the run stops partway for any reason, nothing from that run is kept, and the run is logged as failed.
6. A data row with more or fewer fields than the header is rejected with the reason "row has N fields, expected 23". The rest of the file is processed normally.
7. A cell that is empty or holds only spaces is treated as empty by every rule, and is stored as NULL. **[A7]**
8. Rows are numbered by the CSV line on which the record starts. The header is line 1.

## 2. Book identity

1. A valid `book_id` and a valid `goodreads_book_id` each contain digits only and are greater than zero.
2. Every row must have a valid `book_id`, a valid `goodreads_book_id`, a nonempty `title` and a nonempty `authors` value, after trimming spaces at both ends. A row missing any of these is rejected.
3. `book_id` is the primary key. `goodreads_book_id` must be unique across all stored books.
4. A new `book_id` whose `goodreads_book_id` already belongs to a different stored book is rejected.
5. An existing `book_id` that arrives with a different `goodreads_book_id`, `title` or `authors` is rejected, and the stored book is not changed.
6. Title and authors are compared after trimming spaces at both ends, and are otherwise exact and case sensitive. The `title` column is used, not `original_title`. A difference only in leading or trailing spaces is not a change.
7. Within one file:
   * If every row sharing a `book_id` is identical in all 23 fields, the earliest line is processed and the others are skipped as exact duplicates (rule 7.8).
   * If rows sharing a `book_id` are not all identical, every row with that `book_id` is rejected, including any identical copies among them, because the file does not say which version is right. **[A1]**
   * If two or more different `book_id`s share a `goodreads_book_id`, all of those rows are rejected.
   * A book already stored in the database is not changed by any of these rejections.
8. Two or more books with different `book_id`s but the same trimmed title and authors are all kept and never merged. Every row in the file whose title and authors match a stored book or another row in the file gets a "possible duplicate" warning. (No such pair exists in books.csv.) **[A4]**
9. `work_id` is stored but has no role in identity.

## 3. ISBN validity

1. A valid ISBN-10 has nine digits followed by a digit or a capital `X`, and passes the ISBN-10 checksum.
2. A valid ISBN-13 has 13 digits, starts with 978 or 979 but not 9790, and passes the ISBN-13 checksum. A 9790 prefix is an ISMN (a music number), not an ISBN.
3. ISBNs are handled as text, never as numbers.
4. A passing checksum shows a value is well formed. It does not prove the ISBN belongs to the book in the row.

## 4. Approved repairs

Each repair is logged with the line, the raw value, the result and the rule. A repair alone does not cause a warning. Section 11 gives the order in which a row's two ISBN values are classified.

1. **Formatting.** Remove hyphens and spaces. Change a final lowercase `x` to `X`.
2. **Leading zeros.** An ISBN-10 of 7 to 9 digits gets zeros added on the left, only if the result passes the checksum.
3. **Wrong column.** A valid ISBN-13 in `isbn`, or a valid ISBN-10 in `isbn13`, is moved to its correct field when that field is empty or holds the identical value. If the correct field holds a different valid ISBN of the same kind, rule 6.1 applies **[A8]**. If it holds anything else, the misplaced value is not used and gets a warning.
4. **`.0` copies.** A value in `isbn13` ending in `.0` whose digits, after padding, equal the row's repaired ISBN-10 is a copy of that ISBN-10. It confirms the ISBN-10, and the row is treated as having no ISBN-13 value. A `.0` value that is a valid ISBN-10 but does not equal the row's ISBN-10 is an open question **[A9]**. Any other `.0` value is handled by its digits, under 4.7 or section 5.
5. **Filling in.** When a field holds no value, it is filled by converting the valid other form: ISBN-10 to its 978 ISBN-13, or a 978 ISBN-13 to its ISBN-10. A 979 ISBN-13 has no ISBN-10; that field stays blank with no warning.
6. **Rounded ISBN-13s.** A value in scientific notation (for example `9.78141652479e+12`) is never stored as an ISBN. If its digits start with 978 or 979 (not 9790) and the row has a valid ISBN-10, convert the ISBN-10 to an ISBN-13 and round it to the number of significant digits shown in the source value, using round half to even and exact decimal arithmetic **[A10]**. If the two agree, the converted ISBN-13 is used. If they disagree, rule 6.1 applies. If there is no valid ISBN-10, the ISBN-13 is left blank with a warning.
7. **Non-ISBN codes in `isbn13`.** A value whose digits (after removing `.0` or expanding scientific notation) do not start with 978 or 979, or start with 9790, is not an ISBN. Examples are Barnes & Noble IDs (2940), UPC codes and ISMNs. It is not stored as an ISBN, the row gets a warning, and the ISBN-13 is filled from a valid ISBN-10 under 4.5, because a code from another numbering system says nothing against the ISBN-10.

## 5. Values that are not repaired

These are left blank with a warning, and the row continues under section 2. Nothing is calculated from them, and the field is not filled from the other ISBN, because a damaged ISBN may be evidence against it.

* A wrong check digit, including a final `0` that would pass as `X`
* An ISBN-13 cut short, including a `.0` value that starts with 978 or 979 but has too few digits
* An extra digit
* A letter or other character inside the number
* A rounded ISBN-13 with no valid ISBN-10 in the row, including one that could match more than one ISBN
* Any value in a form these rules do not cover

When an ISBN-10 is invalid and the ISBN-13 is valid, the ISBN-13 is kept and the ISBN-10 stays blank with a warning.

## 6. ISBN conflicts

Conflicts never reject a row with a valid identity. Each conflict blanks both ISBN fields of the affected row, adds a warning, and flags the row for review.

1. **Within a row.** If a valid ISBN-10 and a valid ISBN-13 do not correspond, or a rounded 978 or 979 ISBN-13 does not agree with the valid ISBN-10 under 4.6, both ISBN fields are left blank.
2. **With a stored book.** If an incoming ISBN-10 or ISBN-13 belonged to a different book at the start of the run, both ISBN fields of the incoming row are left blank. The stored book keeps its ISBNs. **[A3]**
3. **Within one file.** If rows for two or more different books in the same file carry the same ISBN, and no book held that ISBN at the start of the run, both ISBN fields are left blank on every one of those rows. This includes a row for an existing book that would otherwise fill a blank ISBN. **[A2]**
4. **With the same book's stored ISBN.** If an existing book has a valid stored ISBN and the incoming row brings a different valid ISBN, the stored value is kept.
5. Ownership is checked against the repaired and converted ISBNs, both ISBN-10 and ISBN-13.

## 7. Existing books and updates

A row is compared with the stored book that has the same `book_id`, after rule 2.5 has confirmed the identity matches.

1. ISBNs are compared using repaired values. A difference only in raw format (`439139600` against `0439139600`) is not a change.
2. A blank incoming value never overwrites a stored value.
3. A stored repaired ISBN that is blank (missing or previously discarded) is filled by a valid incoming ISBN that is not blanked by section 6.
4. The other source columns are compared exactly as text, except the identity fields in rule 2.5 and the raw `isbn` and `isbn13` columns, which follow rule 8.2. A nonblank incoming value that differs is applied. **[A5]**
5. Every applied change is written to the change history with the old and new value (rule 8.3).
6. If at least one change is applied, the row is **updated**. Otherwise it is **skipped**, with the reason "no change". A skipped or updated row can still carry warnings.
7. **Rerunning a file.** Every row is processed again under the same rules. If the same file is run again with no other run in between:
   * a row that was loaded or updated is now **skipped** with the reason "no change", because its values are already stored. Any warnings its ISBN values cause are recorded again
   * an exact duplicate is skipped again
   * a rejected row is rejected again with the same reason, because every rejection reason depends only on the file and on stored books that the earlier run did not change

   If other files have been run in between, a previously rejected row is judged against the database as it is now and can get a different outcome.
8. A row identical in all 23 fields to an earlier row in the same file is **skipped** with the reason "exact duplicate of line N", where N is the earliest identical line. This reason is separate from "no change".

## 8. Database

1. **`books`**: one row per book.
   * `book_id`: integer, primary key
   * `goodreads_book_id`: integer, unique
   * the other 21 source columns, including the raw `isbn` and `isbn13`, stored as text exactly as received, except that an empty or spaces only cell is stored as NULL
   * `clean_isbn10` and `clean_isbn13`: the repaired ISBNs, unique when not NULL **[A6]**
2. **Raw ISBN values.**
   * When a book is loaded, its raw `isbn` and `isbn13` are the cells of the loading row, even when the repaired value is NULL.
   * The raw columns change only when a later row fills a repaired ISBN under rule 7.3. Then each raw column whose incoming cell is nonblank is replaced by that cell. A blank incoming cell leaves the stored raw value as it is.
   * A later raw value that differs from the stored one and is not applied (a format only difference, a blank, an invalid value, or a conflict) is recorded in the log under "raw ISBN differences" (rule 10.2). It does not change the database. **[A5]**
3. **`book_changes`**: one row per changed column, with `book_id`, column name, old value, new value, and the run timestamp. A filled ISBN produces a row for each repaired column that changed and each raw column that changed.
4. Rejected rows are not stored in the database. They are recorded in the log, and the source file keeps the original.

## 9. Outcomes

| Outcome | Meaning |
|---|---|
| **Loaded** | A new book was stored. A book stored with warnings is still loaded |
| **Updated** | An existing book had at least one change applied |
| **Skipped** | An existing book had nothing to change, or the row was an exact duplicate within the file |
| **Rejected** | The row was not stored. The reason is recorded |

Loaded, updated, skipped and rejected must add up to the number of data rows read.

## 10. Log and report

1. Each run appends one entry to `ingestion-log.json`. Earlier entries are kept. The file is created if it does not exist.
2. Each entry contains:
   * **Header:** file name, SHA-256 of the file, run timestamp as `yyyy-MM-dd HH:mm:ss` local time with UTC offset (for example `2026-11-05 19:30:00 -06:00`), run status (completed or failed), and the counts of rows read, loaded, updated, skipped, rejected and warnings
   * **Counts by issue:** how many rows had each issue, and what was done
   * **Repairs:** line, `book_id`, raw value, result and rule
   * **Changes:** line, `book_id`, column, old value and new value
   * **Raw ISBN differences:** line, `book_id`, column, stored raw value, incoming raw value, and why it was not applied **[A5]**
   * **Records needing attention:** for every warning, skip and rejection, the line, `book_id`, title, issue, raw value, outcome and reason, plus a flag when a person should review it
   * **Failure reason**, for a failed run
3. `report.html` is a single self contained file that opens without a server. It has a button to choose `ingestion-log.json`, and shows every run newest first, with all of the contents above.

## 11. Processing order

Each run follows these stages in order. A row that is rejected or skipped as a duplicate at one stage takes no part in later stages. Every check that compares rows with stored books uses the database as it was at the start of the run, so no row sees the effect of another row in the same run. **[A3]**

| Stage | What happens | Rules | Possible result |
|---|---|---|---|
| 1. File checks | File exists, is readable and UTF-8, and the header has exactly the 23 columns | 1.4 | Failed run. Nothing else happens |
| 2. Row shape | Each row has 23 fields | 1.6 | Rejected |
| 3. Identity fields | `book_id`, `goodreads_book_id`, title and authors are present and valid | 2.1, 2.2 | Rejected |
| 4. Within the file | Group the remaining rows by `book_id`, then by `goodreads_book_id` | 2.7, 7.8 | Skipped as an exact duplicate, or rejected |
| 5. Against stored books | New `book_id` with a stored `goodreads_book_id`, or existing `book_id` with a changed identity | 2.4, 2.5 | Rejected |
| 6. ISBN repair | Each row on its own. Classify `isbn13` in this order: empty; valid ISBN-13 after formatting; valid ISBN-10 in the wrong column; `.0` copy of the row's ISBN-10; any other `.0` or scientific notation value by its digits (978 or 979 and not 9790: a damaged or rounded ISBN-13, otherwise a non-ISBN code). Classify `isbn` after formatting and padding: valid ISBN-10, valid ISBN-13 in the wrong column, or invalid. Then apply the wrong column moves, the rounding check and filling in | 3, 4, 5 | Repaired ISBNs, repairs and warnings. No row is rejected here |
| 7. Within a row | Compare the row's ISBN-10 and ISBN-13 | 6.1 | Both ISBNs blanked, warning |
| 8. Across rows | First against books stored at the start of the run, then among rows for different books in the file | 6.2, 6.3, 6.5 | Both ISBNs blanked, warning |
| 9. Possible duplicates | Title and authors against stored books and other rows in the file | 2.8 | Warning |
| 10. Changes | For an existing `book_id`: fill blank ISBNs, keep a different stored ISBN, apply changed source columns | 6.4, 7, 8.2 | Changes, raw ISBN differences, warnings |
| 11. Outcome | Assigned in this order: rejected (stages 2 to 5); skipped as an exact duplicate (stage 4); loaded (a new `book_id`); updated (at least one change at stage 10); otherwise skipped with "no change" | 9 | One outcome per row |
| 12. Write | All inserts, updates and change history rows in one transaction. Then append the log entry | 1.5, 8, 10 | Completed run, or failed run with nothing kept |

## 12. Decisions on the 39 checklist questions

The source column says which Week 3 rule the recommendation follows: **Asha**, **George**, **Both** (the two combined), or **New** (neither stated it).

| # | Recommendation | Rule | Source |
|---|---|---|---|
| ID1 | `book_id` is the primary key. `goodreads_book_id` must also be valid and unique | 2.3, 2.4 | Both |
| ID2 | Require `book_id`, `goodreads_book_id`, title and authors | 2.2 | Both |
| ID3 | Changed title or author on an existing book: rejected | 2.5 | George |
| ID4 | Trim both ends, then exact and case sensitive. Use `title` | 2.6 | George |
| ID5 | Possible duplicate warning, never merged | 2.8 | George |
| ID6 | `work_id` stored, not used for identity | 2.9 | New |
| ID7 | A kept but flagged row counts as loaded with a warning | 9 | New |
| C1 | Rounded ISBN-13 disagreeing with a valid ISBN-10: both blank, warning, review | 6.1 | New |
| C2 | Two valid ISBNs that disagree: both blank, book kept, review | 6.1 | George |
| C3 | ISBN owned by another book: incoming ISBNs blank, book kept, review | 6.2 | George |
| C4 | Rows for different books in one file share an ISBN: blank on all of them | 6.3 | New |
| C5 | Different valid ISBN for an existing book: stored value kept, warning, review | 6.4 | George |
| C6 | No separate Goodreads and ISBN rule. Covered by 2.4 and 6.2 | 2.4, 6.2 | Both |
| I1 | 9790 is not an ISBN | 3.2 | George |
| I2 | Pad 7 to 9 digits only | 4.2 | Asha |
| I3 | Move in either direction when the destination is empty or identical | 4.3 | George |
| I4 | Cells holding only spaces are empty | 1.7 | George |
| I5 | Raw source columns in the database, plus repaired ISBN columns | 8.1, 8.2 | Asha |
| I6 | Book 1106 is a non-ISBN code, handled by 4.7 | 4.7 | George |
| I7 | Fill ISBN-13 from ISBN-10 after a non-ISBN code, but not after a damaged ISBN | 4.7, 5 | Both |
| I8 | Round half to even at the digits shown, exact decimal arithmetic | 4.6 | George |
| I9 | A `.0` copy of the row's ISBN-10 confirms it, and the ISBN-13 is then filled in | 4.4 | Asha |
| R1 | Non-identity fields are updated, with history | 7.4 | Asha |
| R2 | Change history table in `books.db` | 8.3 | Asha |
| R3 | Rejected rows in the log only | 8.4 | George |
| R4 | On an unchanged rerun, loaded and updated rows are skipped and rejected rows are rejected again with the same reason | 7.7 | Asha |
| R5 | Exact duplicate gets its own reason | 7.8 | Asha |
| P1 | SHA-256 recorded | 10.2 | Asha |
| P2 | `yyyy-MM-dd HH:mm:ss` local time with UTC offset | 10.2 | Asha |
| P3 | Counts by issue required | 10.2 | Asha |
| P4 | Warning total in the header | 10.2 | Asha |
| P5 | CSV line where the record starts, header is line 1 | 1.8 | George |
| P6 | Append each run, keep earlier runs | 10.1 | George |
| P7 | Self contained report with file picker, newest first, all contents | 10.3 | Both |
| P8 | Failed run logged, database unchanged, one transaction per run | 1.4, 1.5 | Asha |
| P9 | Wrong field count: row rejected, file continues | 1.6 | Asha |
| P10 | Database and log beside `ingest.py` | 1.1 | Asha |
| P11 | Source files never modified | 1.2 | George |
| P12 | No AI or network lookups at run time | 1.3 | George |

**One more decision not in the checklist.** `part1-review.md` did not list what happens when the same `book_id` appears twice in one file with different values (Asha rejected both rows; George treated the second as a repeat of the first). The proposal is rule 2.7: all such rows are rejected. This keeps row order from affecting results (principle 3).

## 13. ISBN examples

The examples assume this sequence. Line numbers are CSV lines, with the header on line 1.

* **Run 1:** books.csv into an empty database
* **Run 2:** books.csv again
* **Run 3:** books-batch2.csv
* **H:** a made-up row, with the database state stated. The made-up ISBNs `0300000006`, `0300000014` and `0300000022` pass their checksums and appear in neither file.

The **Check** column says how each example was verified (section 14.3): **C** means the ISBN arithmetic was computed, **D** means the row values were confirmed in the CSV file, and **R** means the outcome follows from the rules but could not be checked by running anything, because no implementation exists yet.

| # | Run and state before | Row | Raw `isbn` / `isbn13` | Outcome | Stored `clean_isbn10` / `clean_isbn13` | What happens | Rule | Check |
|---|---|---|---|---|---|---|---|---|
| 1 | Run 1, empty | books.csv line 10, book 9, Angels & Demons | `1416524797` / `9.78141652479e+12` | Loaded | `1416524797` / `9781416524793` | Converted ISBN-13 rounds to the shown value. Repair logged | 4.6 | C, D |
| 2 | Run 1 | line 2, book 1, The Hunger Games | `439023483` / `9.78043902348e+12` | Loaded | `0439023483` / `9780439023481` | Padded, then ISBN-13 rebuilt. Two repairs | 4.2, 4.6 | C, D |
| 3 | Run 1 | line 1107, book 1106, The Great Divorce | `6280560` / `9.79000767239e+12` | Loaded with a warning | `0006280560` / `9780006280569` | Padded from 7 digits. The 9790 value is an ISMN, not an ISBN, so the ISBN-13 is filled from the ISBN-10 | 4.2, 4.7 | C, D |
| 4 | Run 1 | line 623, book 622, Nights in Rodanthe | `446612707` / `9.78055381395e+12` | Loaded with a warning | NULL / NULL | `0446612707` converts to `9780446612708`, which rounds to `9.78044661271e+12`, not the shown value. Both blank, flagged for review | 6.1 | C, D |
| 5 | Run 1 | line 1544, book 1543, The Racketeer | `385535144` / `9.78038553514e+12` | Loaded with a warning | NULL / NULL | `0385535144` fails the checksum. No valid ISBN-10, so the rounded value cannot be checked | 5 | C, D |
| 6 | Run 1 | line 917, book 916, Reading Lolita in Tehran | `812971060` / `9.78081297106e+12` | Loaded with a warning | NULL / NULL | `0812971060` fails the checksum. `081297106X` would pass, but the final `0` is not changed to `X` | 5 | C, D |
| 7 | Run 1 | line 800, book 799, Watchers | empty / `9.7804251888e+12` | Loaded with a warning | NULL / NULL | No ISBN-10 to check against. The value shows 11 digits: ten valid ISBN-13s round to it at 11 digits, and two (`9780425188798`, `9780425188804`) at 12 digits | 4.6, 5 | C, D |
| 8 | Run 1 | line 2895, book 2894, Sailor Moon #1 | `189221301X` / `6.45573003012e+11` | Loaded with a warning | `189221301X` / `9781892213013` | Product code (starts 645) is not an ISBN. ISBN-13 filled from the ISBN-10 | 4.7 | C, D |
| 9 | Run 1 | line 959, book 958, The Complete Anne of Green Gables Boxed Set | `553609416` / `76783609419.0` | Loaded with a warning | `0553609416` / `9780553609417` | UPC code (starts 767) is not an ISBN. ISBN-13 filled from the ISBN-10 | 4.7 | C, D |
| 10 | Run 1 | line 8175, book 8174, Washington's Crossing | `195170342` / `195170342.0` | Loaded | `0195170342` / `9780195170344` | `.0` value pads to the row's ISBN-10. ISBN-13 filled in. Repairs logged | 4.4, 4.5 | C, D |
| 11 | Run 1 | line 1444, book 1443, The Secret of the Nagas | `9380658797` / `97893806587.0` | Loaded with a warning | NULL / NULL | ISBN-10 fails the checksum. The `.0` value starts with 978 but has 11 digits, so it is a damaged ISBN-13 | 5 | C, D |
| 12 | Run 1 | line 107, book 106, Bossypants | empty / empty | Loaded with a warning | NULL / NULL | No ISBN. Identity is valid | 2.2, 5 | D |
| 13 | Run 2, after run 1 | all 10,000 rows of books.csv | as in run 1 | All 10,000 skipped ("no change") | unchanged | Run 1 rejects no row (section 14.3), so run 2 has nothing to reject. Rows like book 622 are skipped and their warnings recorded again. No raw ISBN differences | 7.7 | D, R |
| 14 | Run 3, after runs 1 and 2 | books-batch2.csv line 4, book 24, Goblet of Fire | `0439139600` / `9780439139601` | Skipped | `0439139600` / `9780439139601` | Repaired values equal the stored ones. Raw columns stay `439139600` / `9.7804391396e+12`. Both incoming raw values are logged as raw ISBN differences (format only) | 7.1, 8.2 | C, D |
| 15 | Run 3 | line 26, book 25, Deathly Hallows | empty / empty | Skipped | `0545010225` / `9780545010221` | Blanks do not overwrite. Logged as raw ISBN differences (blank) | 7.2, 8.2 | C, D |
| 16 | Run 3 | line 5, book 132, The Five People You Meet in Heaven | `1401308589` / `9.78140130858e+12` | Updated | `1401308589` / `9781401308582` | `ratings_count` 449501 to 451425, `work_ratings_count` 474699 to 476623, `ratings_5` 165040 to 166964. Three history rows | 7.4, 8.3 | C, D |
| 17 | Run 3 | line 16, book 10011, Tides of Marrow Bay | `1555550126` / `9781555550134` | Loaded with a warning | NULL / NULL | Both pass their checksums, but `1555550126` converts to `9781555550127`. Flagged for review | 6.1 | C, D |
| 18 | Run 3 | line 24, book 10013, Paper Moons | `1416524797` / empty | Loaded with a warning | NULL / NULL | Book 9 held this ISBN at the start of the run and keeps it. Book 9's own row in this file (line 21) is identical to books.csv and is skipped. Flagged for review | 6.2 | D |
| 19 | Run 3 | lines 14 and 15, book 10001, The Lantern Keeper's Daughter | `1528746309` / `9781528746304` (both lines) | Line 14 loaded. Line 15 skipped | `1528746309` / `9781528746304` | Line 15 reason: "exact duplicate of line 14" | 2.7, 7.8 | C, D |
| 20 | Run 3 | line 30, book 10002, Salt and Ember | `0-450-19827-8` / `9780450198274` | Loaded | `0450198278` / `9780450198274` | Hyphens removed. The pair corresponds | 4.1 | C, D |
| 21 | Run 3 | line 27, book 10004, Winter Orchard | `031200009x` / `9780312000097` | Loaded | `031200009X` / `9780312000097` | Lowercase `x` changed. The pair corresponds | 4.1 | C, D |
| 22 | Run 3 | line 18, book 10014, An Atlas of Small Kindnesses | `9781982147600` / empty | Loaded | `1982147601` / `9781982147600` | ISBN-13 moved, ISBN-10 filled in | 4.3, 4.5 | C, D |
| 23 | Run 3 | line 10, book 10006, Notes from the Night Ferry | empty / `9798351220413` | Loaded, no warning | NULL / `9798351220413` | A 979 ISBN-13 has no ISBN-10 | 4.5 | C, D |
| 24 | Run 3 | line 6, book 10012, The Long Walk Home | `441773028` / `9.78044177302e+12` | Loaded | `0441773028` / `9780441773022` | Padded, ISBN-13 rebuilt and agrees | 4.2, 4.6 | C, D |
| 25 | Run 3 | line 3, book 10008, The Glass Aviary | `04390A3483` / empty | Loaded with a warning | NULL / NULL | Letter inside the number | 5 | D |
| 26 | Run 3 | line 20, book 10009, Borrowed Light | `15287463097` / empty | Loaded with a warning | NULL / NULL | Extra digit. No digit is removed | 5 | D |
| 27 | H, after run 3. Book 106 still has NULL ISBNs | book 106, Bossypants, otherwise unchanged | `0300000006` / empty | Updated | `0300000006` / `9780300000009` | Blank stored ISBN filled. Three history rows: `clean_isbn10`, `clean_isbn13`, and raw `isbn`. Raw `isbn13` stays NULL because the incoming cell is blank | 7.3, 8.2, 8.3 | C, R |
| 28 | H, after run 1 | book 9, Angels & Demons, otherwise unchanged | `0300000014` / empty | Skipped with a warning | `1416524797` / `9781416524793` | `0300000014` converts to `9780300000016`. A different valid ISBN does not replace the stored one. Logged as a raw ISBN difference. Flagged for review | 6.4, 8.2 | C, R |
| 29 | H, after run 1 | book 9 with title `Angels and Demons` | `1416524797` / empty | Rejected | unchanged | Stored title is `Angels & Demons  (Robert Langdon, #1)` | 2.5 | D, R |
| 30 | H, after run 1 | new book 10020 with `goodreads_book_id` 960 | `0300000022` / empty | Rejected | none | 960 belongs to book 9 | 2.4 | D, R |
| 31 | H, any state | new book 10021 with a blank title | `0300000022` / empty | Rejected | none | Title is required | 2.2 | R |
| 32 | H, after run 1. One file holds new books 10022 and 10023 | both rows | `0300000022` / empty on both | Both loaded with a warning | NULL / NULL on both | Same ISBN on rows for two different books, held by no book at the start of the run | 6.3 | C, R |
| 33 | H, after run 1 | book 1 with title `The Hunger Games (The Hunger Games, #1) ` (trailing space), otherwise unchanged | `439023483` / `9.78043902348e+12` | Skipped | `0439023483` / `9780439023481` | Trailing space is not a change | 2.6 | D, R |
| 34 | H, any state | a row with 22 fields | any | Rejected | none | "row has 22 fields, expected 23". Other rows continue | 1.6 | R |
| 35 | H, any state | `python3 ingest.py missing.csv` | none | Failed run. No row outcomes | unchanged | Failed run entry written to the log | 1.4 | R |
| 36 | H, after run 1. One file holds new book 10024 on lines 2 and 3 (identical) and line 4 (different `ratings_count`) | all three rows | `0300000022` / empty | All three rejected | none | Rows sharing a `book_id` are not all identical. Depends on **[A1]** | 2.7 | R |
| 37 | H, after run 1. Book 106 has NULL ISBNs. One file holds book 106 and new book 10025 | both rows, `isbn` `0300000006` on each | `0300000006` / empty on both | Book 106 skipped with a warning. Book 10025 loaded with a warning | NULL / NULL on both | No book held the ISBN at the start of the run, and two different books carry it. The result is the same in either row order. Depends on **[A2]** | 6.3 | C, R |

## 14. Review notes

### 14.1 Changes made in this review

| # | Issue | Change |
|---|---|---|
| 1 | Row order independence against exact duplicates | Principle 3 now says what order does and does not affect. Rule 2.7 states how a group of rows sharing a `book_id` is handled when some are identical and some are not. Cross-row checks now use the database at the start of the run (stage 8, rule 6.2), so no row sees another row's effect. Rule 6.3 now covers any two books in the file, not only new ones |
| 2 | Raw ISBN preservation | Rule 8.2 defines when the raw `isbn` and `isbn13` columns are set and changed, and where later values that are not applied go. Rule 7.4 no longer treats raw ISBN columns as ordinary fields. The repaired columns are renamed `clean_isbn10` and `clean_isbn13`, because the earlier name `isbn13` collided with the raw source column |
| 3 | Rerun statement | Rule 7.7 and example 13 now say loaded and updated rows become skipped, and rejected rows are rejected again with the same reason |
| 4 | Deterministic order | Section 11 sets out twelve stages, the classification order for ISBN values, and the order in which outcomes are assigned |
| 5 | Contradictions found | Rule 4.3 no longer conflicts with rule 6.1 when both columns hold different valid ISBNs **[A8]**. Rules 4.4 and 4.7 overlapped for one kind of `.0` value; that case is now an open question **[A9]**. Rule 1.7 and rule 8.1 now agree on how a spaces only cell is stored **[A7]** |
| 6 | Examples | Example 7's note was wrong: at the 11 digits shown, ten valid ISBN-13s fit, not two. Examples 13 to 16, 18 and 27 now describe raw values and history rows. Examples 36 and 37 were added to show rules 2.7 and 6.3. A Check column was added |

### 14.2 Items that need approval

None of these changes a policy choice in `proposed-rules.md`. **New** items add behavior the earlier draft did not cover. **Clarification** items state one reading of a rule that was ambiguous or self contradicting.

| Item | Type | What it says | Why it is needed | Alternative |
|---|---|---|---|---|
| **A1** | New | When rows sharing a `book_id` are not all identical, every row in the group is rejected, including identical copies | Rule 2.7 and rule 7.8 did not say what happens to a group that has both | Process the identical copies once and reject only the differing rows. This makes the result depend on which version is treated as the original |
| **A2** | Clarification | Rule 6.3 applies to any two books in the file, including an existing book filling a blank ISBN, not only two new books | Without it, an existing book and a new book sharing an ISBN in one file get different results depending on row order | None that keeps row order irrelevant |
| **A3** | Clarification | Identity checks (2.4, 2.5) and ownership checks (6.2) use the database as it was at the start of the run | Needed for principle 3. Conflicts within the file are handled by 2.7 and 6.3 instead | Check against the database as rows are written, which makes the result depend on row order |
| **A4** | Clarification | The possible duplicate warning goes on every matching row in the file, not only "the incoming one" | Two new rows in the same file are both incoming | Warn only the later line, which depends on row order |
| **A5** | New | Raw ISBN values: rules 8.2 and 7.4 as written, plus a "raw ISBN differences" section in the log | The earlier draft did not say how later raw values are recorded. Without the log section, a format only difference on an updated row would be lost | Record raw differences in `book_changes` instead of the log. This mixes values that were applied with values that were not |
| **A6** | Clarification | Repaired columns are named `clean_isbn10` and `clean_isbn13` | The earlier name `isbn13` collided with the raw source column of the same name | Any other names that do not collide |
| **A7** | Clarification | A spaces only cell is stored as NULL, as George's Week 3 rule says and checklist item I4 follows | The earlier rule 8.1 said cells are stored exactly as received, with only empty cells as NULL | Store spaces only cells as received but treat them as empty |
| **A8** | Clarification | A misplaced valid ISBN that meets a different valid ISBN in the correct column is a conflict under 6.1, as George's Week 3 rule 10 says | The earlier rule 4.3 discarded the misplaced value and kept the other, which contradicted 6.1 | None that keeps 6.1 consistent |
| **A9** | **Open, needs a decision** | A `.0` value in `isbn13` that is a valid ISBN-10 but does not equal the row's ISBN-10 (or the row has none) | Rule 4.4 sent it to section 5, while rule 4.7 classified it as a non-ISBN code. The two give different results. No row in either file has this | (a) Section 5: blank with a warning, not filled. (b) A conflict under 6.1. (c) A wrong column ISBN-10 under 4.3 |
| **A10** | **Open, needs a decision** | Rule 4.6 compares at "the number of significant digits shown", following George's Week 3 wording | A rounded value always carries 12 significant digits. When the 12th digit is 0, the file drops it, so 972 rows show 11 digits. Comparing at 11 digits is looser. In books.csv this changes one row: book 5998, Wanted (`098870742X` / `9.7809887074e+12`). Its ISBN-10 converts to `9780988707429`, which rounds to `978098870743` at 12 digits but the file holds `978098870740`. At the digits shown it agrees and the ISBN-13 is rebuilt; at 12 digits it is a conflict under 6.1 and both ISBNs are blank. Comparing at 12 digits gives 13 conflicting rows, which matches the "13 conflicting records" count in Asha's Week 3 notes | (a) Keep the digits shown. (b) Always compare at 12 significant digits. The reviewer's recommendation is (b), because it uses the precision the data actually has |
| **A11** | Clarification | Stage 4 groups only rows that passed stages 2 and 3, so a row already rejected for a missing title does not cause a valid row with the same `book_id` to be rejected | The earlier draft did not give an order | Group all rows before validating them |

### 14.3 How the examples were checked

A verification script (kept outside the project, in the session scratchpad) read books.csv and books-batch2.csv from this folder and checked 56 facts. All 56 passed. Book 5998 (item A10) was checked with a separate calculation.

* **ISBN arithmetic (C):** every checksum, padding, ISBN-10 to ISBN-13 and ISBN-13 to ISBN-10 conversion, and every round half to even comparison in examples 1 to 11, 14 to 17, 19 to 24, 27, 28, 32 and 37, plus the three made-up ISBNs and their absence from both files.
* **Row values (D):** every line number, `book_id`, raw ISBN value and title used in the examples. For books 24, 25 and 132, the exact list of columns that differ between books.csv and books-batch2.csv. Book 9's batch 2 row is identical to its books.csv row, and so are books 106's.
* **Run 1 rejects nothing:** every books.csv row has 23 fields, valid `book_id` and `goodreads_book_id`, a nonblank title and authors, and both IDs are unique. There are no exact duplicate rows, no ISBN shared by two books, and no title and author pair shared by two books. This supports examples 13 and 16 and the statement that requiring both IDs rejects nothing.
* **Not verifiable yet (R):** every outcome label (loaded, updated, skipped, rejected) and every warning is derived by applying these rules by hand. None of them can be confirmed by running anything until an implementation exists. Examples 29 to 37 are made up, so only their ISBN arithmetic and the stored values they rely on could be checked. Example 13's claim that all 10,000 rows are skipped depends on that hand derivation.

### 14.4 Before this becomes `rules.md`

1. George and Asha review the recommendations in section 12, the extra decision on rule 2.7, and items A1 to A11. A9 and A10 need a choice.
2. Any change is made in this file first, then the examples in section 13 are checked against it again.
3. Once both partners approve, the file is saved as `rules.md` with the **NOT YET APPROVED** label removed, and both partners keep an identical copy.
