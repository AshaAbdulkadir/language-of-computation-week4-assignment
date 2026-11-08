# Proposed Shared Book Ingestion Rules

> **NOT YET APPROVED.** This is a proposal for Asha and George to review together. It is not the final `rules.md`. Nothing here is binding until both partners approve it.

**Course:** MSAI-5523, Language of Computation, Module 4
**Partners:** Asha (`AshaAbdulkadir`) and George (`Georgec4444`)
**Prepared:** 2026-11-05
**Based on:** `asha-week3-rules.md`, George's Week 3 `rules.md` (`Georgec4444/language-of-computation-week3-assignment`, branch `assignment`), `rules-comparison.md`, `george-rules-comparison.md`, and `part1-review.md`

Every recommendation is judged against four criteria: the same input and database state always give the same result (deterministic), no value is stored unless the files prove it (accurate), anyone can rerun and audit a run (reproducible), and the design stays as simple as the data allows (practical). Section 11 maps each of the 39 checklist questions in `part1-review.md` to the rule that answers it.

## Guiding principles

1. **Identity problems reject a row. ISBN problems never do.** A row is rejected only when we cannot tell which book it is. A book with a valid identity is kept even when its ISBNs are unusable: the ISBN is left blank and the row gets a warning.
2. **No guessing.** Only the repairs listed in section 4 are allowed. Every repair is a fixed calculation from values in the same row.
3. **Row order does not matter.** Reordering the rows of a file never changes any row's outcome.
4. **Every row has exactly one outcome**: loaded, updated, skipped or rejected. Warnings are tracked separately.

## Why the main decisions were made

**Book identity (section 2).** `book_id` is the database key, because it is the supplier's key and it is what the supplier reuses when a book is sent again (every repeated book in books-batch2.csv keeps its `book_id`). `goodreads_book_id` must also be valid and unique, because it is an independent check that catches a reused or mistyped `book_id`. Both columns are unique across books.csv, so requiring both rejects nothing in the current data. Title and author must be present and must not change for an existing book, because a changed title under the same key means the key no longer identifies one book.

**Conflicting ISBNs (section 6).** When the two ISBN values in a row disagree, nothing in the files says which one is right. Both are left blank and the row is flagged for review, but the book is kept, because its identity is fine. This applies the same way whether the second value is a full ISBN-13 (Tides of Marrow Bay) or a rounded one whose surviving digits disagree (Nights in Rodanthe and 11 other rows). The rounded case is treated as a conflict because 12 surviving digits are enough to show the two values describe different ISBNs. Keeping only the ISBN-10 would mean trusting one side without evidence. When an incoming ISBN already belongs to another book, the existing book keeps it and the incoming book is stored without it.

**Scientific notation rounding (section 4.6).** Rebuilt ISBN-13s are compared using round half to even at the number of significant digits shown, with exact decimal arithmetic. This is the method the source data matches: across 9,251 rows in books.csv with a valid ISBN-10 and a rounded 978 or 979 value, round half to even leaves 12 disagreements (all genuine conflicts), while round half up leaves 408. Using round half up would wrongly blank 396 good ISBN-13s.

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
7. A cell holding only spaces is treated as empty.
8. Rows are numbered by the CSV line on which the record starts. The header is line 1.

## 2. Book identity

1. A valid `book_id` and a valid `goodreads_book_id` each contain digits only and are greater than zero.
2. Every row must have a valid `book_id`, a valid `goodreads_book_id`, a nonempty `title` and a nonempty `authors` value, after trimming spaces at both ends. A row missing any of these is rejected.
3. `book_id` is the primary key. `goodreads_book_id` must be unique across all stored books.
4. A new `book_id` whose `goodreads_book_id` already belongs to a different stored book is rejected.
5. An existing `book_id` that arrives with a different `goodreads_book_id`, `title` or `authors` is rejected, and the stored book is not changed.
6. Title and authors are compared after trimming spaces at both ends, and are otherwise exact and case sensitive. The `title` column is used, not `original_title`. A difference only in leading or trailing spaces is not a change.
7. Within one file, if two rows that are not exact duplicates share a `book_id`, or two different `book_id`s share a `goodreads_book_id`, all of those rows are rejected, because the file does not say which version is right. A book already stored in the database is not changed.
8. Two books with different `book_id`s but the same trimmed title and authors are both kept, and the incoming one gets a "possible duplicate" warning. They are never merged. (No such pair exists in books.csv.)
9. `work_id` is stored but has no role in identity.

## 3. ISBN validity

1. A valid ISBN-10 has nine digits followed by a digit or a capital `X`, and passes the ISBN-10 checksum.
2. A valid ISBN-13 has 13 digits, starts with 978 or 979 but not 9790, and passes the ISBN-13 checksum. A 9790 prefix is an ISMN (a music number), not an ISBN.
3. ISBNs are handled as text, never as numbers.
4. A passing checksum shows a value is well formed. It does not prove the ISBN belongs to the book in the row.

## 4. Approved repairs

Each repair is logged with the line, the raw value, the result and the rule. A repair alone does not cause a warning.

1. **Formatting.** Remove hyphens and spaces. Change a final lowercase `x` to `X`.
2. **Leading zeros.** An ISBN-10 of 7 to 9 digits gets zeros added on the left, only if the result passes the checksum.
3. **Wrong column.** A valid ISBN-13 in `isbn`, or a valid ISBN-10 in `isbn13`, is moved to its correct field when that field is empty or holds the identical value. Otherwise the misplaced value is not used and gets a warning.
4. **`.0` copies.** A value in `isbn13` ending in `.0` whose digits, after padding, equal the row's repaired ISBN-10 is a copy of that ISBN-10. It confirms the ISBN-10, and the row is treated as having no ISBN-13 value. Any other `.0` value is handled under section 5.
5. **Filling in.** When a field holds no value, it is filled by converting the valid other form: ISBN-10 to its 978 ISBN-13, or a 978 ISBN-13 to its ISBN-10. A 979 ISBN-13 has no ISBN-10; that field stays blank with no warning.
6. **Rounded ISBN-13s.** A value in scientific notation (for example `9.78141652479e+12`) is never stored as an ISBN. If its digits start with 978 or 979 (not 9790) and the row has a valid ISBN-10, convert the ISBN-10 to an ISBN-13 and round it to the number of significant digits shown in the source value, using round half to even and exact decimal arithmetic. If the two agree, the converted ISBN-13 is used. If they disagree, section 6.1 applies. If there is no valid ISBN-10, the ISBN-13 is left blank with a warning.
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

Conflicts never reject a row with a valid identity. Each conflict blanks the affected ISBNs, adds a warning, and flags the row for review.

1. **Within a row.** If a valid ISBN-10 and a valid ISBN-13 do not correspond, or a rounded 978 or 979 ISBN-13 does not agree with the valid ISBN-10 under 4.6, both ISBN fields are left blank.
2. **With a stored book.** If an incoming ISBN-10 or ISBN-13 already belongs to a different stored book, both ISBN fields of the incoming row are left blank. The stored book keeps its ISBNs.
3. **Within one file.** If two new rows in the same file carry the same ISBN, that ISBN is left blank on both rows.
4. **With the same book's stored ISBN.** If an existing book has a valid stored ISBN and the incoming row brings a different valid ISBN, the stored value is kept.
5. Ownership is checked against the repaired and converted ISBNs, both ISBN-10 and ISBN-13.

## 7. Existing books and updates

A row is compared with the stored book that has the same `book_id`, after section 2.5 has confirmed the identity matches.

1. ISBNs are compared using repaired values. A difference only in raw format (`439139600` against `0439139600`) is not a change.
2. A blank incoming value never overwrites a stored value.
3. A stored ISBN that is blank (missing or previously discarded) is filled by a valid incoming ISBN that belongs to no other book.
4. Other fields, except the identity fields in section 2.5, are compared exactly as text. A nonblank incoming value that differs is applied.
5. Every applied change is written to the change history with the old and new value.
6. If at least one change is applied, the row is **updated**. Otherwise it is **skipped**, with the reason "no change". A skipped or updated row can still carry warnings.
7. Rerunning a file processes every row again under the same rules. With no other changes in between, every row gets the same result as before: a rejected row is rejected again with the same reason, and no row is loaded or updated.
8. A row identical in all 23 fields to an earlier row in the same file is **skipped** with the reason "exact duplicate of line N". This reason is separate from "no change".

## 8. Database

1. **`books`**: one row per book.
   * `book_id`: integer, primary key
   * `goodreads_book_id`: integer, unique
   * the other 21 source columns, stored as text exactly as received, with an empty cell stored as NULL
   * `isbn10` and `isbn13`: the repaired ISBNs, unique when not NULL
2. The raw `isbn` and `isbn13` source columns change only when the repaired ISBN changes.
3. **`book_changes`**: one row per applied change, with `book_id`, field, old value, new value, and the run timestamp.
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
   * **Changes:** line, `book_id`, field, old value and new value
   * **Records needing attention:** for every warning, skip and rejection, the line, `book_id`, title, issue, raw value, outcome and reason, plus a flag when a person should review it
   * **Failure reason**, for a failed run
3. `report.html` is a single self contained file that opens without a server. It has a button to choose `ingestion-log.json`, and shows every run newest first, with all of the contents above.

## 11. Decisions on the 39 checklist questions

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
| C4 | Two new rows in one file share an ISBN: blank on both | 6.3 | New |
| C5 | Different valid ISBN for an existing book: stored value kept, warning, review | 6.4 | George |
| C6 | No separate Goodreads and ISBN rule. Covered by 2.4 and 6.2 | 2.4, 6.2 | Both |
| I1 | 9790 is not an ISBN | 3.2 | George |
| I2 | Pad 7 to 9 digits only | 4.2 | Asha |
| I3 | Move in either direction when the destination is empty or identical | 4.3 | George |
| I4 | Cells holding only spaces are empty | 1.7 | George |
| I5 | Raw source columns in the database, plus repaired ISBN columns | 8.1 | Asha |
| I6 | Book 1106 is a non-ISBN code, handled by 4.7 | 4.7 | George |
| I7 | Fill ISBN-13 from ISBN-10 after a non-ISBN code, but not after a damaged ISBN | 4.7, 5 | Both |
| I8 | Round half to even at the digits shown, exact decimal arithmetic | 4.6 | George |
| I9 | A `.0` copy of the row's ISBN-10 confirms it, and the ISBN-13 is then filled in | 4.4 | Asha |
| R1 | Non-identity fields are updated, with history | 7.4 | Asha |
| R2 | Change history table in `books.db` | 8.3 | Asha |
| R3 | Rejected rows in the log only | 8.4 | George |
| R4 | Rerun gives the same results, including rejections | 7.7 | Asha |
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

## 12. ISBN examples

The examples assume this sequence. Line numbers are CSV lines, with the header on line 1.

* **Run 1:** books.csv into an empty database
* **Run 2:** books.csv again
* **Run 3:** books-batch2.csv
* **H:** a made-up row, with the database state stated. The made-up ISBNs `0300000006`, `0300000014` and `0300000022` pass their checksums and appear in neither file.

| # | Run and state before | Row | Raw `isbn` / `isbn13` | Outcome | Stored ISBN-10 / ISBN-13 | What happens | Rule |
|---|---|---|---|---|---|---|---|
| 1 | Run 1, empty | books.csv line 10, book 9, Angels & Demons | `1416524797` / `9.78141652479e+12` | Loaded | `1416524797` / `9781416524793` | Converted ISBN-13 rounds to the shown value. Repair logged | 4.6 |
| 2 | Run 1 | line 2, book 1, The Hunger Games | `439023483` / `9.78043902348e+12` | Loaded | `0439023483` / `9780439023481` | Padded, then ISBN-13 rebuilt. Two repairs | 4.2, 4.6 |
| 3 | Run 1 | line 1107, book 1106, The Great Divorce | `6280560` / `9.79000767239e+12` | Loaded with a warning | `0006280560` / `9780006280569` | Padded from 7 digits. The 9790 value is an ISMN, not an ISBN, so the ISBN-13 is filled from the ISBN-10 | 4.2, 4.7 |
| 4 | Run 1 | line 623, book 622, Nights in Rodanthe | `446612707` / `9.78055381395e+12` | Loaded with a warning | NULL / NULL | `0446612707` converts to `9780446612708`, which does not round to the shown value. Both blank, flagged for review | 6.1 |
| 5 | Run 1 | line 1544, book 1543, The Racketeer | `385535144` / `9.78038553514e+12` | Loaded with a warning | NULL / NULL | `0385535144` fails the checksum. No valid ISBN-10, so the rounded value cannot be checked | 5 |
| 6 | Run 1 | line 917, book 916, Reading Lolita in Tehran | `812971060` / `9.78081297106e+12` | Loaded with a warning | NULL / NULL | Final `0` is not changed to `X` | 5 |
| 7 | Run 1 | line 800, book 799, Watchers | empty / `9.7804251888e+12` | Loaded with a warning | NULL / NULL | No ISBN-10 to check against. Two ISBNs fit the rounded value | 4.6, 5 |
| 8 | Run 1 | line 2895, book 2894, Sailor Moon #1 | `189221301X` / `6.45573003012e+11` | Loaded with a warning | `189221301X` / `9781892213013` | Product code is not an ISBN. ISBN-13 filled from the ISBN-10 | 4.7 |
| 9 | Run 1 | line 959, book 958, The Complete Anne of Green Gables Boxed Set | `553609416` / `76783609419.0` | Loaded with a warning | `0553609416` / `9780553609417` | UPC code is not an ISBN. ISBN-13 filled from the ISBN-10 | 4.7 |
| 10 | Run 1 | line 8175, book 8174, Washington's Crossing | `195170342` / `195170342.0` | Loaded | `0195170342` / `9780195170344` | `.0` value is a copy of the ISBN-10. ISBN-13 filled in. Repairs logged | 4.4, 4.5 |
| 11 | Run 1 | line 1444, book 1443, The Secret of the Nagas | `9380658797` / `97893806587.0` | Loaded with a warning | NULL / NULL | ISBN-10 fails the checksum. The `.0` value starts with 978 but has 11 digits, so it is a damaged ISBN-13 | 5 |
| 12 | Run 1 | line 107, book 106, Bossypants | empty / empty | Loaded with a warning | NULL / NULL | No ISBN. Identity is valid | 2.2, 5 |
| 13 | Run 2, after run 1 | all 10,000 rows of books.csv | as in run 1 | Each row repeats its run 1 result as skipped (or rejected) | unchanged | Nothing loaded or updated. Book 622 is skipped and keeps its warning | 7.7 |
| 14 | Run 3, after runs 1 and 2 | books-batch2.csv line 4, book 24, Goblet of Fire | `0439139600` / `9780439139601` | Skipped | `0439139600` / `9780439139601` | Repaired values equal the stored ones. Only the raw format differs | 7.1 |
| 15 | Run 3 | line 26, book 25, Deathly Hallows | empty / empty | Skipped | `0545010225` / `9780545010221` | Blanks do not overwrite | 7.2 |
| 16 | Run 3 | line 5, book 132, The Five People You Meet in Heaven | `1401308589` / `9.78140130858e+12` | Updated | `1401308589` / `9781401308582` | `ratings_count` 449501 to 451425, plus `work_ratings_count` and `ratings_5`. Three history rows | 7.4, 7.5 |
| 17 | Run 3 | line 16, book 10011, Tides of Marrow Bay | `1555550126` / `9781555550134` | Loaded with a warning | NULL / NULL | Both pass their checksums but do not correspond. Flagged for review | 6.1 |
| 18 | Run 3 | line 24, book 10013, Paper Moons | `1416524797` / empty | Loaded with a warning | NULL / NULL | The ISBN belongs to book 9, which keeps it. Flagged for review | 6.2 |
| 19 | Run 3 | lines 14 and 15, book 10001, The Lantern Keeper's Daughter | `1528746309` / `9781528746304` (both lines) | Line 14 loaded. Line 15 skipped | `1528746309` / `9781528746304` | Line 15 reason: "exact duplicate of line 14" | 7.8 |
| 20 | Run 3 | line 30, book 10002, Salt and Ember | `0-450-19827-8` / `9780450198274` | Loaded | `0450198278` / `9780450198274` | Hyphens removed | 4.1 |
| 21 | Run 3 | line 27, book 10004, Winter Orchard | `031200009x` / `9780312000097` | Loaded | `031200009X` / `9780312000097` | Lowercase `x` changed | 4.1 |
| 22 | Run 3 | line 18, book 10014, An Atlas of Small Kindnesses | `9781982147600` / empty | Loaded | `1982147601` / `9781982147600` | ISBN-13 moved, ISBN-10 filled in | 4.3, 4.5 |
| 23 | Run 3 | line 10, book 10006, Notes from the Night Ferry | empty / `9798351220413` | Loaded, no warning | NULL / `9798351220413` | A 979 ISBN-13 has no ISBN-10 | 4.5 |
| 24 | Run 3 | line 6, book 10012, The Long Walk Home | `441773028` / `9.78044177302e+12` | Loaded | `0441773028` / `9780441773022` | Padded, ISBN-13 rebuilt and agrees | 4.2, 4.6 |
| 25 | Run 3 | line 3, book 10008, The Glass Aviary | `04390A3483` / empty | Loaded with a warning | NULL / NULL | Letter inside the number | 5 |
| 26 | Run 3 | line 20, book 10009, Borrowed Light | `15287463097` / empty | Loaded with a warning | NULL / NULL | Extra digit. No digit is removed | 5 |
| 27 | H, after run 3. Book 106 has NULL ISBNs | book 106, Bossypants, otherwise unchanged | `0300000006` / empty | Updated | `0300000006` / `9780300000009` | Blank stored ISBN filled. History rows added | 7.3 |
| 28 | H, after run 1 | book 9, Angels & Demons, otherwise unchanged | `0300000014` / empty | Skipped with a warning | `1416524797` / `9781416524793` | A different valid ISBN does not replace the stored one. Flagged for review | 6.4 |
| 29 | H, after run 1 | book 9 with title `Angels and Demons` | `1416524797` / empty | Rejected | unchanged | Title differs from the stored book | 2.5 |
| 30 | H, after run 1 | new book 10020 with `goodreads_book_id` 960 | `0300000022` / empty | Rejected | none | 960 belongs to book 9 | 2.4 |
| 31 | H, any state | new book 10021 with a blank title | `0300000022` / empty | Rejected | none | Title is required | 2.2 |
| 32 | H, after run 1. One file holds new books 10022 and 10023 | both rows | `0300000022` / empty on both | Both loaded with a warning | NULL / NULL on both | Same ISBN on two new rows in one file | 6.3 |
| 33 | H, after run 1 | book 1 with title `The Hunger Games (The Hunger Games, #1) ` (trailing space) | `439023483` / `9.78043902348e+12` | Skipped | `0439023483` / `9780439023481` | Trailing space is not a change | 2.6 |
| 34 | H, any state | a row with 22 fields | any | Rejected | none | "row has 22 fields, expected 23". Other rows continue | 1.6 |
| 35 | H, any state | `python3 ingest.py missing.csv` | none | Failed run. No row outcomes | unchanged | Failed run entry written to the log | 1.4 |

## Before this becomes `rules.md`

1. George and Asha review every recommendation in section 11, and the extra decision on rule 2.7.
2. Any change is made in this file first, then the examples in section 12 are checked against it again.
3. Once both partners approve, the file is saved as `rules.md` with the **NOT YET APPROVED** label removed, and both partners keep an identical copy.
