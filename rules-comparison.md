# Rules Comparison: Week 3 Book Ingestion

Compared files (branch `assignment`, read 2026-11-05):

* **Asha:** `github.com/AshaAbdulkadir/language-of-computation-week3-assignment/blob/assignment/rules.md`
* **Georgec4444:** `github.com/Georgec4444/language-of-computation-week3-assignment/blob/assignment/rules.md`

Each decision is marked **Agree**, **Disagree**, **Only Asha**, or **Only Georgec4444**. When the two rules overlap only partly, the decision is marked Disagree and the note says which part matches. This document compares what the rules say. It does not judge which set is better.

## 1. ISBN problems

| Decision | Asha | Georgec4444 | Status |
|---|---|---|---|
| What makes an ISBN-10 valid | Nine digits plus a digit or capital `X`, passes the checksum | Nine digits plus a digit or `X`, passes the modulus 11 check | Agree |
| What makes an ISBN-13 valid | 13 digits, starts with 978 or 979, passes the checksum | Same, but a 9790 (ISMN) prefix is excluded | Disagree (only Georgec4444 excludes 9790) |
| ISBNs treated as text | Source columns stored as text exactly as received | ISBNs read as strings so leading zeros survive | Agree |
| Raw values kept | Raw `isbn` and `isbn13` kept in the database. Repairs go only to separate cleaned fields | Original problem values kept in the run log. The database stores NULL or the repaired value | Disagree (both keep the raw value, but in different places) |
| Missing leading zeros | Pad an ISBN-10 of 7 to 9 characters, only when the result passes the checksum | Pad any digit only ISBN-10 shorter than 10 digits, only when the result passes | Disagree (Asha sets a lower limit of 7 characters, Georgec4444 sets none) |
| Hyphens and spaces | Removed | Removed | Agree |
| Lowercase `x` | Changed to `X` | Changed to `X` | Agree |
| Cells holding only spaces | Not mentioned | Treated as empty and stored as NULL | Only Georgec4444 |
| ISBN in the wrong column | A valid ISBN-13 in `isbn` moves to the ISBN-13 field | Moves in either direction, only when the destination is empty or does not conflict. A different valid value already there is a conflict | Disagree (Asha covers one direction only and states no destination condition) |
| ISBN-10 stored in `isbn13` with `.0` | Used when it equals the row's `isbn` | "Damaged .0 decimal values" are invalid: NULL with a warning | Disagree |
| Rounded (scientific notation) ISBN-13 with a valid ISBN-10 | Convert the ISBN-10. Use it only when the rounded value agrees | Same, with the rounding method fixed: round half to even, at the number of significant digits shown, using exact decimal arithmetic | Agree on the rule. Only Georgec4444 defines the rounding method |
| Rounded ISBN-13 with no valid ISBN-10 | Not rebuilt. Blank with a warning | Not rebuilt. NULL with a warning | Agree |
| Rounded ISBN-13 that disagrees with a valid ISBN-10 | Decision 5 says blank with a warning. Example 12 treats this as one of the 13 conflicting records and rejects the row | ISBN-13 NULL with a warning. ISBN-10 kept. Not rebuilt later from the ISBN-10 | Disagree (see example 12 below) |
| Wrong check digit | Not corrected. Blank, loaded with a warning if the identifier rule is met | Not corrected. NULL, book kept, warning | Agree |
| Changing a final `0` to `X` (books 916, 2374, 5026) | Not done. Blank with a warning | Covered by "do not change the final character just to make it pass" | Agree |
| ISBN-13 cut short, extra digit, letter inside | Blank. Loaded with a warning if the identifier rule is met | NULL, book kept, warning. No digits removed | Agree |
| Non-ISBN codes (2940, UPC, 622, 123) | Never used as ISBNs | Non-ISBN product codes and barcodes are invalid ISBNs: NULL with a warning | Agree |
| Fill in a missing ISBN-10 or ISBN-13 by conversion | Yes. A 979 ISBN-13 gets no ISBN-10 and no warning | Yes. Same 979 handling | Agree |
| Fill in a field whose value was rejected as invalid | An invalid ISBN-10 is not "missing", so with a valid ISBN-13 the ISBN-10 is left blank with a warning. Example 10 converts a missing ISBN-13 from the ISBN-10 when the `isbn13` value was a product code | Derivation only when the original field was truly empty. A field rejected under Rule 4 or Rule 12 stays NULL | Disagree (the two match for an invalid ISBN-10 but differ when the rejected `isbn13` value was a product code) |
| Specific problem counts (16 wrong check digits, 45 rounded values) | Named | Not named | Only Asha |
| Rules applied by pattern, not by book number | Stated (decision 5) | Implied by "same rules every time" | Agree |
| Any format not covered | Not repaired, left blank, row loads with a warning if the identifier rule is met | Covered by Rule 12 (unrecoverable ISBNs are NULL with a warning) | Agree |
| No AI or internet lookups at run time | Not mentioned | Stated | Only Georgec4444 |

## 2. What makes two rows the same book

| Decision | Asha | Georgec4444 | Status |
|---|---|---|---|
| Primary identifier | `goodreads_book_id`, with a validated ISBN-13 as a secondary identifier | Supplier `book_id`, with title and author as a cross check | Disagree |
| Role of `book_id` | Stored only, never used for identity | Primary key of the books table | Disagree |
| Role of `goodreads_book_id` | Required for every stored book: digits only, greater than zero, unique | Not mentioned | Only Asha |
| Required fields for a row to be accepted | A valid `goodreads_book_id`. Title and author not required | A valid `book_id` (positive whole number), a nonempty title, and a nonempty author | Disagree |
| Row with no usable ISBN | Loaded with a warning if the `goodreads_book_id` is valid and unique, otherwise rejected | Loaded with a warning if the book identity is usable | Disagree (they rely on different identifiers) |
| A row's `isbn` and `isbn13` are both valid but belong to different books | Row rejected and flagged for review | New book kept, both ISBNs stored as NULL, flagged for review | Disagree |
| Incoming ISBN already belongs to a different book | Row rejected and flagged | Incoming book kept, the conflicting ISBN stored as NULL, existing assignment kept, flagged | Disagree |
| Two new rows in one file with the same ISBN | Both rows rejected. The existing record is not touched | Checked against books processed earlier in the same file. The later row's ISBN is stored as NULL and the book is kept | Disagree |
| Same identifier, different values, in the same file | Two rows with the same `goodreads_book_id` and different values: both rejected | Second row with the same `book_id` is treated as an existing book. A different title or author means it is rejected. Other differences are reported but not applied | Disagree |
| Same identifier, different title or author, across runs | Title and author are ordinary fields, so the change is applied and reported | Row rejected. The existing record is kept and the conflict reported | Disagree |
| Different IDs with the same title and author | Title, author and year may be suggested for review but are never merged. The script makes no suggestions (decision 11) | Kept as separate records with a potential duplicate warning. Never merged automatically | Disagree (both refuse to merge, but only Georgec4444 issues a warning) |
| Shared `work_id` | Another edition, not the same book | Not mentioned | Only Asha |
| Exact duplicate rows | Within a file, loaded once. Extra copies skipped | Exact re-sends skipped | Agree |
| Leading and trailing spaces in title and author | Fields other than ISBNs compared exactly as text | Trimmed before comparing, then compared exactly and case sensitive | Disagree |

## 3. When a book arrives again

| Decision | Asha | Georgec4444 | Status |
|---|---|---|---|
| ISBNs compared after cleaning, not raw | Yes | Yes | Agree |
| Rerunning the same file | Skipped rows stay skipped. Rows rejected before are rejected again with the same reason | Creates no new books and no unnecessary updates | Agree |
| Blank incoming value | Never overwrites | Never erases a good stored value | Agree |
| Invalid stored ISBN, valid incoming ISBN | Replaced, previous value kept, change reported | Replaced, update logged | Agree |
| Blank stored ISBN, valid incoming ISBN that belongs to no other book | Filled in, counted as updated | Filled in, counted as updated | Agree |
| Valid stored ISBN, different valid incoming ISBN | Rejected and flagged | Existing value kept, conflict flagged. No outcome category is named | Disagree (both keep the existing value, but only Asha names the outcome) |
| Changes to fields other than ISBNs (for example `ratings_count`) | Updated and reported | Not applied. Reported for review | Disagree |
| Nothing improves | Skipped, with a reason | Skipped | Agree |
| Where previous values are kept | Change history table in `books.db` (book, field, old value, new value, run) | Old and new ISBN values in `ingestion-log.json`. No extra database columns | Disagree |
| Where rejected rows are kept | Review table in `books.db` and the log | The log only | Disagree |

## 4. What the report must say

| Decision | Asha | Georgec4444 | Status |
|---|---|---|---|
| Four outcomes, one per row | Loaded, updated, skipped, rejected | Same | Agree |
| Counts add up to rows read | Yes | Yes | Agree |
| Loaded or updated with a warning | Keeps its outcome. The warning is tracked separately | Same | Agree |
| Reason for every row not loaded | Yes, plus a reason for every warning | Yes, plus what a person should review | Agree |
| Repairs | Row, raw value, repaired value, rule applied | Old and new ISBN values | Agree (Asha also requires the rule name) |
| File identification | File name and SHA-256 | Source file name | Disagree (only Asha requires SHA-256) |
| Run time | Run date as yyyy-MM-dd. Run time as yyyy-MM-dd HH:mm:ss in local time with the time zone | A timestamp, format not stated | Only Asha (for the format) |
| Counts by issue | Required | Not mentioned | Only Asha |
| Total warnings in the header | Required | Not mentioned | Only Asha |
| Row reference | `book_id` and row | CSV line number starting at 2, and `book_id` | Disagree (only Georgec4444 fixes the numbering) |
| Log history | Not stated | Each run appended to `ingestion-log.json`. Earlier runs kept | Only Georgec4444 |
| `report.html` | Shows everything in the log | Self contained, opens without a server, file picker for the log, runs shown newest first | Only Georgec4444 (for these details) |
| Failed runs (missing, unreadable, non UTF-8 file, missing or extra header columns) | Recorded as a failed run. The database is unchanged | Not mentioned | Only Asha |
| Row with the wrong number of fields | Rejected with "row has N fields, expected 23" | Not mentioned | Only Asha |

## 5. Asha's examples under Georgec4444's rules

| # | Row | Asha's result | Under Georgec4444's rules | Different? |
|---|---|---|---|---|
| 1 | Angels & Demons | Loaded, ISBN-13 converted | Same | No |
| 2 | The Hunger Games | Loaded, padded and converted | Same | No |
| 3 | Salt and Ember | Loaded, hyphens removed | Same | No |
| 4 | Winter Orchard | Loaded, `x` to `X` | Same | No |
| 5 | An Atlas of Small Kindnesses | Loaded, moved and filled in | Same | No |
| 6 | Notes from the Night Ferry | Loaded, no warning | Same | No |
| 7 | The Racketeer | Loaded with a warning, both ISBNs blank | Same | No |
| 8 | How to Win Friends and Influence People | Loaded with a warning, ISBN blank | Same | No |
| 9 | Watchers | Loaded with a warning, ISBN blank | Same | No |
| 10 | Sailor Moon #1 | Loaded with a warning. ISBN-13 `9781892213013` converted from the ISBN-10 | Loaded with a warning, but ISBN-13 stays NULL. The `isbn13` value was rejected under Rule 12, and a rejected field is not rebuilt from the other ISBN | **Yes** (stored ISBN-13 differs) |
| 11 | Bossypants | Loaded with a warning by `goodreads_book_id` | Loaded with a warning by `book_id` 106 | No |
| 12 | Nights in Rodanthe | Rejected as a conflicting record | The ISBN-10 `0446612707` is valid. Its ISBN-13 `9780446612708` does not match the rounded `9.78055381395e+12`, so under Rule 4 the ISBN-13 is NULL with a warning. The ISBN-10 is kept. Loaded with a warning | **Yes** |
| 13 | Paper Moons | Rejected, ISBN belongs to Angels & Demons | Loaded. ISBN stored as NULL, Angels & Demons keeps it, flagged for review | **Yes** |
| 14 | Tides of Marrow Bay | Rejected, pair disagrees | Loaded with both ISBNs NULL, flagged for review | **Yes** |
| 15 | book 10001, two identical lines | First loaded, second skipped | Same | No |
| 16 | Goblet of Fire (batch 2) | Skipped, cleaned values equal | Same (only the raw ISBN format differs from books.csv) | No |
| 17 | Deathly Hallows (batch 2) | Skipped, blank does not overwrite | Same | No |
| 18 | The Five People You Meet in Heaven | Updated, `ratings_count` 449,501 to 451,425 | Not applied. The difference is reported for review and no ISBN improves, so the row is skipped | **Yes** |
| 19 | Borrowed Light | Loaded with a warning, ISBN blank | Same | No |
| 20 | Made up: no ISBNs, `goodreads_book_id` blank or already used | Rejected | `goodreads_book_id` is not checked. If `book_id`, title and author are valid, it is loaded with a warning | **Yes** |
| 21 | Reading Lolita in Tehran | Loaded with a warning, no `0` to `X` | Same | No |

## 6. Georgec4444's examples under Asha's rules

Georgec4444's examples describe ISBN handling. Where they name a row, the row was checked in books.csv or books-batch2.csv.

| # | Situation | Georgec4444's result | Under Asha's rules | Different? |
|---|---|---|---|---|
| 1 | ISBN-10 `0439139600` | Valid, unchanged | Same | No |
| 2 | ISBN-13 `9780439139601` | Valid, unchanged | Same | No |
| 3 | ISBN-10 `439023483` | Padded, logged | Same | No |
| 4 | ISBN-10 `61120081` (8 characters) | Padded to `0061120081`, logged | Same (inside the 7 to 9 character range) | No |
| 5 | ISBN-10 `0-450-19827-8` | Hyphens removed | Same | No |
| 6 | ISBN-10 `162 001 4750` | Spaces removed | Same | No |
| 7 | ISBN-10 `031200009x` | Changed to `X` | Same | No |
| 8 | `0439023483` with `9.78043902348e+12` | ISBN-13 rebuilt and logged | Same | No |
| 9 | `9.78043902348e+12` with no valid ISBN-10 | NULL with a warning | Same | No |
| 10 | Small Hours, `1854433017` | NULL, book kept, warning | Same (`goodreads_book_id` 90010007 is valid and unique) | No |
| 11 | The Glass Aviary, `04390A3483` | NULL, book kept, warning | Same (`goodreads_book_id` 90010008) | No |
| 12 | Borrowed Light, `15287463097` | NULL with a warning | Same | No |
| 13 | `2940016231920` (Wait for You, books.csv book 1165, `isbn` empty) | NULL with a warning | Same (no ISBN-10 to convert from; `goodreads_book_id` 17314430) | No |
| 14 | `195170342.0` (Washington's Crossing, books.csv book 8174, `isbn` `195170342`) | ISBN-13 NULL with a warning. ISBN-10 padded to `0195170342` and kept. ISBN-13 not rebuilt | The `.0` value equals the row's `isbn`, so Asha's repair accepts it. With no ISBN-13 left, the fill in rule converts `0195170342` to `9780195170344`. Repairs logged, no warning | **Yes** |
| 15 | `9798351220413`, ISBN-10 blank | Accepted, no warning | Same | No |
| 16 | `9780062398123`, ISBN-10 blank | ISBN-10 `0062398121` derived | Same | No |
| 17 | Untitled Manuscript, both blank | Loaded with a warning | Same (`goodreads_book_id` 90010010 is valid and unique) | No |
| 18 | `9781982147600` in `isbn` | Moved, ISBN-10 derived | Same | No |
| 19 | Tides of Marrow Bay | New book kept with both ISBNs NULL, flagged | Rejected and flagged | **Yes** |
| 20 | Paper Moons | Incoming book kept, ISBN NULL, flagged | Rejected and flagged | **Yes** |
| 21 | book 10001 repeated | First inserted, repeat skipped | Same | No |
| 22 | Hypothetical: book 24 returns with a valid ISBN replacing a missing or invalid one | Updated, logged | Same (updated, previous value kept in history) | No |
| 23 | Book 25 returns with both ISBNs blank | Skipped, existing values kept | Same | No |
| 24 | Missing or invalid `book_id`, or blank title or author | Row rejected | Not a reason to reject. The row is rejected only if its `goodreads_book_id` is blank, invalid, or already used. Otherwise it loads | **Yes** (unless the `goodreads_book_id` is also bad) |
| 25 | Existing book, a non ISBN column differs | Field kept unchanged, difference reported | Field updated, change reported, row counted as updated | **Yes** |
| 26 | Existing book, title `The Hunger Games ` with a trailing space | Trimmed, recognized, no field change | Recognized by `goodreads_book_id`, but the title is compared exactly as text, so the trailing space counts as a change and the row is updated | **Yes** |

## Summary of differing examples

* **Asha's examples that differ under Georgec4444's rules:** 10 (stored ISBN-13 only), 12, 13, 14, 18, 20.
* **Georgec4444's examples that differ under Asha's rules:** 14, 19, 20, 24, 25, 26.
