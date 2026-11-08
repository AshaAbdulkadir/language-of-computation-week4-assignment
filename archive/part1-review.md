# Part 1 Review: Comparing the Two Rule Comparisons

**Course:** MSAI-5523, Language of Computation, Module 4
**Partners:** Asha (`AshaAbdulkadir`) and George (`Georgec4444`)
**Prepared:** 2026-11-05
**Status:** working draft for joint review. No rules have been decided.

## Sources

| File in this folder | What it is | Check |
|---|---|---|
| `rules-comparison.md` | Asha's comparison, copied from `week3-assignment/rules-comparison.md` | Byte for byte identical to the original. The original is unchanged |
| `george-rules-comparison.md` | George's comparison, copied from `language-of-computation/rules-comparison.md` | Byte for byte identical to the file provided |

Both comparisons were checked against the two original Week 3 files on the `assignment` branch:

* `github.com/AshaAbdulkadir/language-of-computation-week3-assignment/blob/assignment/rules.md`
* `github.com/Georgec4444/language-of-computation-week3-assignment/blob/assignment/rules.md`

Where a finding depends on the data, it was checked against `week3-assignment/books.csv` and `books-batch2.csv`. No ingestion code was run.

## 1. Discrepancies between the two comparisons

Each item says where the two comparisons differ, what each original Week 3 rule says, and what the data shows. Errors in either comparison are listed the same way, including errors in Asha's.

| # | Topic | Asha's comparison | George's comparison | What the originals and the data show |
|---|---|---|---|---|
| D1 | Nights in Rodanthe (book 622) under George's rules | ISBN-10 kept, ISBN-13 NULL with a warning, loaded (George's Rule 4) | Both ISBNs NULL, flagged for review (George's Rule 11) | George's Rule 11 applies when both ISBNs are "individually valid". The stored ISBN-13 `9.78055381395e+12` is not a valid ISBN-13 as stored, so Rule 11 does not fit the text. George's Rule 4 covers it: "If ... the values conflict, store NULL for the damaged ISBN-13 and warn". See section 3 |
| D2 | George's example 14, `195170342.0` | Asha's `.0` repair applies, so the result differs from George's | Asha's `.0` repair needs the value to match `isbn`, and "this example lacks that confirmation" | The only row with this value is books.csv book 8174, Washington's Crossing, whose `isbn` is `195170342`. The values match, so Asha's `.0` repair condition is met |
| D3 | What happens to ISBN-13 after Asha's `.0` repair | States that the fill-in rule converts `0195170342` to `9780195170344` | Not addressed | Asha's rules do not say whether `isbn13` counts as "missing" once its `.0` value has been used as the ISBN-10. Asha's comparison stated one reading as fact. It is an open question (checklist I9) |
| D4 | Rounding method for scientific notation ISBN-13s | Examples 1, 2 and George's example 8 marked "Same" | Marked "Clarify" | For those three examples both readings give the same result. Across books.csv the method matters: of 9,251 rows with a valid ISBN-10 and a rounded 978 or 979 ISBN-13, round half to even leaves 12 disagreeing, while round half up leaves 408 disagreeing. Neither comparison reported this consequence (checklist I8) |
| D5 | Original CSV files never edited | Not listed as a decision | Marked "Agree" (A1 row 3 and A4 row 48), saying Asha's rules require it | Only George's rules state it. Asha's rules say the raw `isbn` and `isbn13` values are kept as received, but say nothing about the source files |
| D6 | Rerunning a file: rows rejected before | Marked "Agree" | Lists rerun behavior as Agree, without the rejection detail | Only Asha's rules (decision 15) say a row rejected before is rejected again with the same reason. George's rules say every row is processed with the same rules on every run, but do not state this outcome. Asha's comparison overstated the agreement |
| D7 | Rows marked "conditional" in George's comparison | Rows checked against the data | G10, G11, G12, G17, A7, A8, A9, A11, A19, A21 left conditional on identity fields | In every one of these rows, `book_id`, `goodreads_book_id`, title and author are all present and valid, and no identifier is duplicated in books.csv. The ISBN outcome is the same under both rules. The difference only appears for rows like Asha's example 20 or George's example 24 |
| D8 | Title, author, year match | Asha: may be suggested, never merged, script does not suggest. George: potential duplicate warning | Row title says "Title/author/year" for both | George's rules use title and author only. Year appears only in Asha's rules |
| D9 | `work_id` | Marked "Only Asha" | Marked "Clarify" | Only Asha's rules mention `work_id`. The difference is in labeling, not substance |
| D10 | Count of conflicting rows | Not checked | Not checked | Asha's rules say "all 13 conflicting records". The data has 12 rows where a valid ISBN-10 (after approved repairs) meets a rounded 978 or 979 ISBN-13 that does not match it beyond rounding. Two more rows (4322, 8552) disagree but have an invalid ISBN-10, which Asha's decision 6 treats as a wrong check digit case, not a conflict. Which row makes the thirteenth was not traced |

## 2. Decisions missed by one or both comparisons

| # | Decision in the original rules | Whose rule | Covered by Asha's comparison | Covered by George's comparison |
|---|---|---|---|---|
| M1 | Use `title`, not `original_title`, for identity checks (George, final answer 3) | George only | No | No |
| M2 | Which category a rounded ISBN-13 that disagrees with a valid ISBN-10 falls into (Nights in Rodanthe and 11 other rows) | Both, differently | Partly (one row) | No. Not in Part D |
| M3 | ISBN-13 with a 9790 (ISMN) prefix. Book 1106 in books.csv has `9.79000767239e+12` | George excludes it, Asha is silent | Yes | Yes, but Part D omits it and does not mention book 1106 |
| M4 | Database and log kept beside `ingest.py` wherever it is run from (Asha, decision 20) | Asha only | No | Yes (A4 row 46) |
| M5 | Exact duplicates within a file get their own reason, separate from "already exists" (Asha, decision 17) | Asha only | No | No |
| M6 | Two new rows in one file sharing an ISBN | Both, differently | Yes | Folded into A2 row 22. Not in Part D |
| M7 | Outcome category when an existing book's valid ISBN meets a different valid ISBN | Asha names one (rejected). George's rules name none | Yes | Yes, but Part D omits it |
| M8 | Lower limit for adding leading zeros | Asha 7 to 9 characters, George no limit | Yes | Yes, but Part D omits it. No row in either file has fewer than 7 digits |
| M9 | Moving a valid ISBN-10 found in `isbn13` (the reverse direction) | George only | Yes | Yes, but Part D omits it |
| M10 | Cells holding only spaces become NULL (George, final decision 2). There are 5 such cells across the two files | George only | Yes | No |
| M11 | Invalid ISBN-10 with a valid ISBN-13: keep the ISBN-13, ISBN-10 blank with a warning (Asha decision 22, George Rule 5 and final decision 4) | Both, same result | Yes | Only the ISBN-13 side (A1 row 13) |
| M12 | Outcome category for a row George's rules keep but flag (Tides of Marrow Bay, Paper Moons) | George's rules say "keep the book" without naming loaded with a warning | No | No |

## 3. Asha's Decision 5 and Example 12 (Nights in Rodanthe)

### The row

books.csv book 622, Nights in Rodanthe, `goodreads_book_id` 15926.

| Field | Raw value | What it is |
|---|---|---|
| `isbn` | `446612707` | Padded to `0446612707`, which passes the ISBN-10 checksum. A valid ISBN-10 after an approved repair. No other row in books.csv uses it |
| `isbn13` | `9.78055381395e+12` | Scientific notation with 12 significant digits. The 13th digit (the check digit) is gone, so it is not a valid ISBN-13 as stored |

The ISBN-13 that the ISBN-10 converts to is `9780446612708`. Rounded to 12 significant digits, that would be `9.78044661271e+12`, not `9.78055381395e+12`. The two values differ from the fifth digit on, far beyond what rounding can explain.

Exactly one valid ISBN-13 rounds to `9.78055381395e+12`: `9780553813951` (ISBN-10 `0553813951`). No other row in books.csv carries that ISBN, so the rounded value does not point to another record in this data. It points to a different ISBN.

### What Asha's Week 3 rules say

| Text | What it says about this row |
|---|---|
| Section 1, validity | A valid ISBN-13 has 13 digits and passes the checksum. The stored value fails this |
| Decision 5, first sentence | "Any rounded ISBN-13 that no valid ISBN-10 confirms is left blank with a warning." This row matches: the valid ISBN-10 does not confirm the rounded value. Result: loaded with a warning, ISBN-10 kept, ISBN-13 blank |
| Decision 5, second sentence | "Any row whose valid ISBN-10 and 978 or 979 ISBN-13 don't match is rejected." This can be read to include a rounded value that starts with 978, or to mean only a full, valid ISBN-13 |
| Decision 6 | A conflict only counts when the ISBN-10 is valid after repairs. This row's ISBN-10 is valid, so this does not exclude it |
| Section 2, conflicting identities | "An `isbn` and an `isbn13` in the same row that belong to different books." It does not say both values must be valid |
| Example 12 | Rejected as one of "the 13 conflicting records" |

### Invalid ISBN, or two valid identities in conflict?

The facts point in both directions. The classification is the decision to make.

* **It is not a conflict between two valid ISBNs as stored.** The ISBN-13 fails the validity rule in both students' rules. George's Rule 11 and Asha's Tides of Marrow Bay example (two values that both pass their checksums) describe a different situation.
* **It is also more than an ordinary damaged value.** For most rounded ISBN-13s, the surviving 12 digits agree with the ISBN-10 and only the check digit is lost. Here the surviving digits disagree, and they fit exactly one other valid ISBN. If the surviving digits are treated as evidence of identity, the row carries two different book identifiers.

So the question for the partners is whether the 12 surviving digits of a rounded ISBN-13 count as an identifier (which makes this an identity conflict) or only as a damaged value (which makes this an invalid ISBN). The two sentences of Asha's decision 5 and Example 12 do not settle it, because each reading is supported by some of the text.

### Results under each reading

| Reading | Book 622 result | Rule text it follows |
|---|---|---|
| Invalid ISBN | Loaded with a warning. ISBN-10 `0446612707` kept, ISBN-13 blank | Asha decision 5 (first sentence). George Rule 4 |
| Identity conflict, row rejected | Rejected and flagged for review | Asha Example 12, section 2, decision 5 (second sentence) |
| Identity conflict, book kept | Loaded, both ISBNs blank, flagged for review | The pattern of George's Rule 11, if extended to damaged values. George's comparison describes this result, but George's Rule 11 as written needs both values to be valid |

### Rows affected by the same choice

All 12 rows in books.csv where a valid ISBN-10 meets a rounded 978 or 979 ISBN-13 that does not match it (round half to even):

622, 1027, 1106, 4351, 4501, 5183, 7142, 7838, 7856, 8618, 8869, 9038.

Book 1106 (The Great Divorce, `9.79000767239e+12`) has a 9790 prefix. Under George's rules that prefix is not an ISBN at all, so book 1106 would be handled as a non-ISBN code rather than under this choice (checklist I6).

## 4. Decision checklist

Each row states a question the two Week 3 rules answer differently, or that only one answers. The "Depends on the choice" column describes what changes, using the data where it was checked. The decision column is left for George and Asha.

### Identity

| # | Question | Asha's Week 3 rule | George's Week 3 rule | Depends on the choice | Decision |
|---|---|---|---|---|---|
| ID1 | What is the primary identifier? | `goodreads_book_id`, with a validated ISBN-13 as secondary | `book_id`, with title and author as a cross check | Which column must be unique in the database. Both columns are unique in books.csv, so the choice changes results only for new rows that reuse one identifier but not the other | |
| ID2 | Which fields must be present and valid for a row to be accepted? | A valid `goodreads_book_id` (digits only, greater than zero, unique) | A valid `book_id` (positive whole number), a nonempty title and a nonempty author | Asha example 20 and George example 24 change outcome. No row in either file has a blank title or author | |
| ID3 | What happens when an existing book returns with a different title or author? | Applied as an ordinary field change. Counted as updated | Rejected. The existing record is kept and the conflict reported | Outcome of any such row: updated or rejected | |
| ID4 | How are title and author compared? | Exactly as text | Trimmed at both ends, then exact and case sensitive. `title`, not `original_title` | George example 26. At least 10 books.csv rows already have leading or trailing spaces in title or author, so a later file that trims them would produce updates under one rule and skips under the other | |
| ID5 | Are different IDs with the same title and author flagged? | May be suggested, but the script does not suggest | Potential duplicate warning | Number of warnings in each report | |
| ID6 | Does a shared `work_id` mean anything? | Another edition, not the same book | Not stated | Whether `work_id` is ever used | |
| ID7 | What outcome does a row get when George's rules keep it but flag it (conflicting pair, ISBN owned by another book)? | Not applicable (Asha rejects these) | "Keep the book" without naming the outcome | Whether these rows count as loaded with a warning, or as something else | |

### ISBN conflicts

| # | Question | Asha's Week 3 rule | George's Week 3 rule | Depends on the choice | Decision |
|---|---|---|---|---|---|
| C1 | A valid ISBN-10 with a rounded ISBN-13 whose surviving digits do not match (section 3) | Decision 5 and Example 12 give different results | Rule 4: ISBN-13 NULL with a warning, ISBN-10 kept | 12 rows in books.csv: loaded with a warning, or rejected, or loaded with both ISBNs blank | |
| C2 | Both ISBNs pass their checksums but do not match each other (Tides of Marrow Bay) | Rejected, flagged | Loaded, both ISBNs NULL, flagged | Batch 2 book 10011: rejected or loaded | |
| C3 | The incoming ISBN already belongs to another book (Paper Moons) | Rejected, flagged | Loaded, that ISBN NULL, flagged | Batch 2 book 10013: rejected or loaded | |
| C4 | Two new rows in the same file share an ISBN | Both rejected | The later row keeps its book with that ISBN NULL | Whether the first row is affected by the second | |
| C5 | An existing book's valid ISBN meets a different valid incoming ISBN | Rejected, flagged | Existing value kept, flagged, no outcome named | Which outcome count the row lands in | |
| C6 | Does the `goodreads_book_id` pointing to a different record than the ISBN-13 count as a conflict? | Yes, rejected | No such rule | Depends on ID1 | |

### ISBN repairs and invalid values

| # | Question | Asha's Week 3 rule | George's Week 3 rule | Depends on the choice | Decision |
|---|---|---|---|---|---|
| I1 | Is a 9790 (ISMN) prefix a valid ISBN-13? | Not excluded | Excluded | Book 1106 | |
| I2 | Lower length limit for adding leading zeros | 7 characters | None | No row in either file is affected | |
| I3 | Can a valid ISBN-10 found in `isbn13` move to the ISBN-10 field? | Only the ISBN-13 to ISBN-10 column direction is stated | Either direction, if the destination is empty or does not conflict | Future files only | |
| I4 | Are cells holding only spaces treated as empty? | Not stated | Yes, stored as NULL | 5 cells across the two files | |
| I5 | Where are raw ISBN values kept? | In the database, beside separate cleaned ISBN fields | In the log. The database stores the cleaned value or NULL | Database columns | |
| I6 | What happens to a rounded ISBN-13 after deciding I1? | Depends on C1 for book 1106 | Non-ISBN code, NULL with a warning | Book 1106 | |
| I7 | Can an ISBN-13 be derived from a valid ISBN-10 after the `isbn13` value was rejected as a product code? | Yes (Sailor Moon example) | No. Derivation only when the field was truly empty | 6 rows in books.csv: 958, 2894, 3689, 5268, 6142, 6437 get an ISBN-13 or stay NULL | |
| I8 | Which rounding method decides whether a converted ISBN-13 agrees with a rounded value? | "Agrees with the rounded value", method not stated | Round half to even, at the significant digits shown, exact decimal arithmetic | Round half to even: 12 rows disagree. Round half up: 408 rows disagree. The difference is 396 rows that either get a rebuilt ISBN-13 or a blank with a warning | |
| I9 | An ISBN-10 stored in `isbn13` with `.0`: used or not? If used, is the ISBN-13 then filled by conversion? | Used when it equals the row's `isbn`. Whether the ISBN-13 is then filled is not stated | Invalid, NULL with a warning | Book 8174 (Washington's Crossing) is the only row that meets Asha's condition. The other four `.0` rows (958, 1443, 6142, 6437) do not match their `isbn` | |

### When a book arrives again

| # | Question | Asha's Week 3 rule | George's Week 3 rule | Depends on the choice | Decision |
|---|---|---|---|---|---|
| R1 | Are changes to fields other than ISBNs applied? | Yes, counted as updated | No, reported for review | Batch 2 books 13, 14, 132 and 134 (ratings fields changed): updated or skipped | |
| R2 | Where are previous values kept? | A change history table in `books.db` | Old and new ISBN values in the log | Database schema | |
| R3 | Where are rejected rows kept? | A review table in `books.db` and the log | The log only | Database schema | |
| R4 | Is a row rejected before rejected again on a rerun, with the same reason? | Yes | Not stated | Second run of the same file | |
| R5 | Does an exact duplicate within a file get its own skip reason? | Yes, separate from "already exists" | Not stated | Report wording | |

### Report and run behavior

| # | Question | Asha's Week 3 rule | George's Week 3 rule | Depends on the choice | Decision |
|---|---|---|---|---|---|
| P1 | Is the input file's SHA-256 recorded? | Yes | Not stated | Report header | |
| P2 | Timestamp format | Run date yyyy-MM-dd. Run time yyyy-MM-dd HH:mm:ss, local, with time zone | A timestamp, format not stated | Report header | |
| P3 | Are counts by issue required? | Yes | Not stated | Report contents | |
| P4 | Is a total warning count required in the header? | Yes | Not stated | Report header | |
| P5 | How are rows numbered? | "Row", numbering not stated | CSV line number, starting at 2 for the first data row | Every row reference in the log | |
| P6 | Does each run append to `ingestion-log.json` and keep earlier runs? | Not stated | Yes | Log structure | |
| P7 | What must `report.html` do? | Show everything in the log | Self contained, opens without a server, file picker for the log, newest run first | Report page | |
| P8 | What happens with a missing, unreadable or non UTF-8 file, or a header with missing or extra columns? | Failed run recorded. Database unchanged | Not stated | Error handling | |
| P9 | What happens with a row that has more or fewer fields than the header? | Rejected with "row has N fields, expected 23". The rest of the file continues | Not stated | Malformed rows | |
| P10 | Where are `books.db` and `ingestion-log.json` written? | Beside `ingest.py`, wherever it is run from | Named, location not stated | Running from another folder | |
| P11 | Must the source CSV files stay unchanged? | Not stated | Yes | Both partners' rules may already assume this | |
| P12 | Are AI models and network lookups banned at run time? | Not stated | Yes | Both partners' code may already follow this | |

## 5. Already in agreement

These need no decision, but the shared `rules.md` should still state them: ISBN-10 and ISBN-13 checksum validity, ISBNs treated as text, removing hyphens and spaces, uppercase `X`, no guessing of check digits, no `0` to `X` changes, blank for truncated values, extra digits and letters, non-ISBN codes never used as ISBNs, filling a truly empty field by conversion, the 979 rule, exact duplicates loaded once, cleaned values compared on repeat arrival, a blank never overwriting a value, an invalid stored ISBN replaced by a valid one, the four outcomes adding up to rows read, and warnings tracked separately from outcomes.
