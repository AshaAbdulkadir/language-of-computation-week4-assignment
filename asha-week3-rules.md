# Book Ingestion Rules

Guiding principle: I want to prioritize data accuracy and avoid making assumptions when information is missing.

## 1. ISBN Validation and Data Quality

**Validity**

* A valid ISBN-10 has 10 characters: nine digits followed by a digit or a capital `X`, and it passes the ISBN-10 checksum.
* A valid ISBN-13 has 13 digits, starts with 978 or 979, and passes the ISBN-13 checksum.
* The raw `isbn` and `isbn13` values are always kept exactly as received. Repairs apply only to the cleaned ISBN fields.

**Repairs**

I agree with the remaining recommendations, provided every repair is validated and documented. Do not assume a reconstructed ISBN belongs to the correct book based on its checksum alone.

The approved repairs are:

* Add the missing leading zeros to an ISBN-10 that has 7 to 9 characters, only when the padded value passes the checksum.
* Remove hyphens and spaces from an ISBN.
* Change a lowercase `x` check character to `X`.
* Move a valid ISBN-13 found in the `isbn` column to the ISBN-13 field.
* Use an ISBN-10 that was stored in `isbn13` with a `.0` ending, only when it is the same as the row's `isbn`.
* Convert a valid ISBN-10 into its ISBN-13 when the stored ISBN-13 was rounded, only when the rounded value agrees with the result.
* Fill in a missing ISBN-10 or ISBN-13 by converting the valid other form. A 979 ISBN-13 has no ISBN-10, so it is left blank without a warning.

**Values that are not repaired**

For the 16 incorrect check digits, keep the ISBN blank and load with a warning only when another reliable identifier is available. Do not guess the corrected digit.

For the 45 rounded ISBN-13 values, do not reconstruct the ISBN from the checksum alone. Leave it blank and load with a warning when a valid alternative identifier exists.

For books 916, 2374, and 5026, do not change 0 to X based only on the checksum. Leave the invalid ISBN blank and load with a warning when the Goodreads ID is valid.

The same applies when an ISBN can't be recovered without guessing. These values stay blank:

* A wrong check digit that nothing else in the row confirms.
* A rounded ISBN-13 that could be either of two valid ISBNs, or matches none.
* An ISBN-13 cut short.
* An ISBN with an extra digit.
* An ISBN with a letter inside the number.

Codes that are not ISBNs (Barnes & Noble IDs starting with 2940, UPC product codes, values starting with 622 or 123) are never used as ISBNs.

In every case in this subsection, the row loads with a warning only if it meets the identifier rule in section 2. Otherwise it is rejected.

## 2. Book Identity and Duplicate Detection

Use goodreads_book_id as the primary identifier and a validated ISBN-13 as a secondary identifier. If they point to different records, do not automatically merge them.

For records without usable ISBNs, allow a valid, unique goodreads_book_id as an alternative identifier. Otherwise, reject the row.

Reject conflicting identities and flag them for review rather than risk overwriting the wrong book. Conflicting identities include:

* A goodreads_book_id and an ISBN-13 that point to different books.
* An `isbn` and an `isbn13` in the same row that belong to different books.
* One ISBN on two different books.
* Two rows with the same goodreads_book_id and different values in the same batch.

Reject all 13 conflicting records in books.csv and flag them for review. Do not guess which ISBN is correct.

Also:

* A match on title, author and year can be suggested for review, but is never merged automatically.
* A shared `work_id` means another edition of the same work, not the same book.
* Rows that are exact duplicates within a batch are loaded once, and the extra copies are skipped.

## 3. Existing Books and Updates

* An incoming row is compared with the existing book using cleaned values. A difference only in the raw format, such as `439139600` compared with `0439139600`, is not a change.
* A blank value never overwrites an existing value.
* An invalid value is replaced by a valid one. The previous value is kept and the change is reported.
* A valid ISBN that changes to a different valid ISBN is a conflicting identity. It is rejected and flagged for review.
* Other fields, such as rating counts, are updated and the change is reported.

## 4. Ingestion Report Requirements

Make sure the report includes the required loaded, updated, skipped, and rejected counts, along with warnings and reasons for records needing attention.

**Outcomes**

Each source row should have one primary outcome: loaded, updated, skipped, or rejected.

* **Loaded:** a new book was added. A record inserted with a warning should count as loaded, with the warning tracked separately.
* **Updated:** an existing book changed. A warning on an updated row is also tracked separately.
* **Skipped:** Count unchanged records as skipped, including records where incoming blank values do not change existing data. Record the reason. Extra copies of an exact duplicate row are also skipped.
* **Rejected:** the row was not loaded and is flagged for review, with the reason.

Loaded, updated, skipped and rejected must add up to the number of rows read.

**Report contents**

* **Header:** file name, SHA-256, run date (yyyy-MM-dd), and the number of rows read, loaded, updated, skipped and rejected, plus the number of warnings.
* **Counts by issue:** how many rows had each issue, and what was done.
* **Repairs:** for every repaired value, the row, the raw value, the repaired value and the rule applied.
* **Records needing attention:** for every warning, skip and rejection, the book_id, title, issue, raw value, outcome and the reason.

## 5. ISBN Test Examples

Examples 1 to 14 assume books.csv is loaded first. Examples 15 to 19 assume books-batch2.csv is loaded after it. Example 20 is a made-up case, and example 21 covers the decision on books 916, 2374 and 5026.

| # | Source row | Raw `isbn` / `isbn13` | Outcome | Expected result | Rule |
|---|---|---|---|---|---|
| 1 | books.csv 9, Angels & Demons | `1416524797` / `9.78141652479e+12` | Loaded | ISBN-10 valid as stored. ISBN-13 `9781416524793` converted and agrees with the rounded value. Repair logged | 1, conversion |
| 2 | books.csv 1, The Hunger Games | `439023483` / `9.78043902348e+12` | Loaded | Padded to `0439023483`, which passes the checksum. ISBN-13 `9780439023481` converted and agrees. Two repairs logged | 1, padding and conversion |
| 3 | books-batch2.csv 10002, Salt and Ember | `0-450-19827-8` / `9780450198274` | Loaded | Hyphens removed to give `0450198278`, which agrees with the ISBN-13. Repair logged | 1, formatting |
| 4 | books-batch2.csv 10004, Winter Orchard | `031200009x` / `9780312000097` | Loaded | Changed to `031200009X`, which agrees with the ISBN-13. Repair logged | 1, formatting |
| 5 | books-batch2.csv 10014, An Atlas of Small Kindnesses | `9781982147600` / empty | Loaded | ISBN-13 moved to its field. ISBN-10 `1982147601` converted from it. Repairs logged | 1, moving and filling in |
| 6 | books-batch2.csv 10006, Notes from the Night Ferry | empty / `9798351220413` | Loaded, no warning | A 979 ISBN-13 has no ISBN-10 | 1 |
| 7 | books.csv 1543, The Racketeer | `385535144` / `9.78038553514e+12` | Loaded with a warning | Wrong check digit. Both ISBNs left blank. Identified by goodreads_book_id 13573236 | 1, the 16 incorrect check digits |
| 8 | books.csv 260, How to Win Friends and Influence People | empty / `9.78067172365e+12` | Loaded with a warning | Only `9780671723651` fits, but it is not reconstructed. ISBN left blank. Identified by goodreads_book_id 4865 | 1, the 45 rounded ISBN-13 values |
| 9 | books.csv 799, Watchers | empty / `9.7804251888e+12` | Loaded with a warning | Could be `9780425188798` or `9780425188804`. ISBN left blank. Identified by goodreads_book_id 32423 | 1, cannot recover without guessing |
| 10 | books.csv 2894, Sailor Moon #1 | `189221301X` / `6.45573003012e+11` | Loaded with a warning | ISBN-10 valid as stored. The `isbn13` is a product code and is not used. ISBN-13 `9781892213013` converted from the ISBN-10. Repair logged | 1, codes that are not ISBNs, filling in |
| 11 | books.csv 106, Bossypants | empty / empty | Loaded with a warning | No ISBN. Identified by its valid, unique goodreads_book_id 9418327 | 2, records without usable ISBNs |
| 12 | books.csv 622, Nights in Rodanthe | `446612707` / `9.78055381395e+12` | Rejected | `isbn` and `isbn13` belong to different books. Flagged for review | 2, the 13 conflicting records |
| 13 | books-batch2.csv 10013, Paper Moons | `1416524797` / empty | Rejected | goodreads_book_id 90010013 is new, but the ISBN belongs to book 9, Angels & Demons. Flagged for review | 2, conflicting identities |
| 14 | books-batch2.csv 10011, Tides of Marrow Bay | `1555550126` / `9781555550134` | Rejected | Both pass their checksums but belong to different books. Flagged for review | 2, conflicting identities |
| 15 | books-batch2.csv 10001, two identical lines | `1528746309` / `9781528746304` | First line loaded, second skipped | Exact duplicate. Reason recorded for the skipped line | 2, exact duplicates |
| 16 | books-batch2.csv 24, Harry Potter and the Goblet of Fire | `0439139600` / `9780439139601` | Skipped | books.csv row 24 was already repaired to these same values (`439139600` padded, ISBN-13 converted), and no other field changed. Reason recorded | 3, cleaned values compared |
| 17 | books-batch2.csv 25, Harry Potter and the Deathly Hallows | empty / empty | Skipped | The existing `0545010225` is kept, because a blank never overwrites. No other field changed. Reason recorded | 3 and 4, skipped |
| 18 | books-batch2.csv 132, The Five People You Meet in Heaven | `1401308589` / `9.78140130858e+12` | Updated | ratings_count changed from 449,501 to 451,425. Change reported | 3, other fields |
| 19 | books-batch2.csv 10009, Borrowed Light | `15287463097` / empty | Loaded with a warning | Extra digit. ISBN left blank. Identified by goodreads_book_id 90010009 | 1, cannot recover without guessing |
| 20 | Made-up row | empty / empty, with a goodreads_book_id that is blank or already used by another book | Rejected | No usable ISBN and no valid, unique goodreads_book_id. Reason recorded | 2, records without usable ISBNs |
| 21 | books.csv 916, Reading Lolita in Tehran | `812971060` / `9.78081297106e+12` | Loaded with a warning | `0` is not changed to `X`. Both ISBNs left blank. Identified by goodreads_book_id 7603 | 1, books 916, 2374, and 5026 |

## 6. Implementation Decisions

These decisions apply the rules above to the ingestion script, `ingest.py`.

**Database**

1. Store all 23 original source columns without duplicating the raw ISBN fields, plus separate cleaned ISBN-10 and ISBN-13 fields. The source columns are stored as text exactly as received.
2. Rejected rows are stored in a review table in `books.db`, as well as in the log.
3. Previous values are kept in a change history table recording the book, field, old value, new value and run.
4. Preserve the original raw ISBN values. Record later incoming values and changes in the history table.

**Applying the rules to any file**

5. The rules are applied by pattern, not by book number. Any wrong check digit, and any rounded ISBN-13 that no valid ISBN-10 confirms, is left blank with a warning. Any row whose valid ISBN-10 and 978 or 979 ISBN-13 don't match is rejected.
6. A conflict between `isbn` and `isbn13` only counts when the ISBN-10 is valid after the approved repairs. An invalid ISBN-10 is a wrong check digit case: left blank with a warning, not rejected.
7. Any value in a format these rules do not cover is not repaired. It is left blank, and the row loads with a warning if it meets the identifier rule.
8. Warnings are added for any value left blank because it couldn't be used, any code that isn't an ISBN, and a row with both ISBN columns empty. Repairs and the 979 case get no warning, but are listed under repairs.

**Identity**

9. A valid `goodreads_book_id` has digits only and is greater than zero.
10. Reject both conflicting incoming rows, but do not delete or overwrite an existing accepted database record. This applies to two rows in one file with the same `goodreads_book_id` and different values, and to two new rows with the same ISBN.
11. Matches on title, author and year are not suggested by the script.
12. `book_id` is stored only. It is not used to identify a book.

**Updates and repeat runs**

13. When an existing book has a blank ISBN and a new row brings a valid ISBN that belongs to no other book, the blank is filled in and the row counts as updated.
14. Fields other than the ISBNs are compared exactly as text.
15. Skipped rows should remain classified as skipped. Record relevant warnings without counting them as newly loaded. Rows that were rejected before are rejected again with the same reason.

**Log and report**

16. The log includes everything in section 4, and `report.html` shows all of it.
17. Rows not loaded are the skipped and rejected rows. Exact duplicates within a file are skipped with their own reason, separate from "already exists".
18. The run time is recorded as yyyy-MM-dd HH:mm:ss in local time, with the time zone shown.
19. For missing or unreadable input files, record a failed run without changing the database. The same applies to a file with missing columns or a file that isn't UTF-8.
20. `books.db` and `ingestion-log.json` are kept in the same folder as `ingest.py`, wherever it is run from. The command is `python3 ingest.py <file.csv>`.

**Further decisions**

21. A row with a usable ISBN but a blank or invalid `goodreads_book_id` is rejected. Every stored book must have a valid `goodreads_book_id`.
22. An invalid ISBN-10 does not count as missing. When the row also has a valid ISBN-13, the ISBN-13 is kept and the ISBN-10 is left blank with a warning.
23. A file whose header has columns beyond the 23 expected ones is a failed run. The database is not changed.
24. A data row with more or fewer fields than the header is rejected with the reason "row has N fields, expected 23". The rest of the file is processed normally.
