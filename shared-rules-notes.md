# Shared Rules: Rationale and Review Notes

> Optional companion to `shared-rules-draft.md`. **NOT YET APPROVED.** This document explains the draft; it adds no rules. If the two disagree, the draft governs.

**Prepared:** 2026-11-05
**History:** `part1-review.md` (39 open questions) led to `proposed-rules.md`, which was reviewed as `proposed-rules-reviewed.md`, which was condensed into `shared-rules-draft.md`.

## 1. Why the main decisions were made

**Book identity.** `book_id` is the key because it is the supplier's key and the one the supplier reuses when a book is sent again. `goodreads_book_id` must also be valid and unique, as an independent check against a reused or mistyped `book_id`. Both are unique in books.csv, so requiring both rejects nothing in the current data. A changed title or author under an existing key means the key no longer identifies one book, so that row is rejected.

**Conflicting ISBNs.** When two ISBN values in a row disagree, the files do not say which is right. Both are blanked and flagged, and the book is kept because its identity is fine. A rounded ISBN-13 whose surviving digits disagree with a valid ISBN-10 is treated the same way, because those digits show it describes a different ISBN. An ISBN already held by another book stays with that book.

**Rounding.** The comparison uses round half to even, which is how the source values were produced: across the 9,251 books.csv rows with a valid ISBN-10 and a rounded 978 or 979 value, round half to even leaves 12 disagreements and round half up leaves 408.

**Updates.** Rating counts and similar fields change legitimately between deliveries, so they are updated with full history. Identity fields never change automatically, a valid stored ISBN is never replaced, and a blank never overwrites.

**Row order.** Every check across rows uses the database at the start of the run and the whole file at once, so reordering a file changes nothing that is stored or counted.

## 2. Decisions proposed in this draft

These are proposed, not approved.

| Item | Proposed decision | Effect on the data |
|---|---|---|
| **A9** | A `.0` value in `isbn13` that is a valid ISBN-10 different from the row's ISBN-10 is a conflicting ISBN-10. Both ISBN fields are blanked and the row is flagged for review (rules 4.4, 6.1). The draft applies the same treatment when the row has no valid ISBN-10 of its own; that part is an interpretation and should be confirmed | No row in either file. Example 8 is made up |
| **A10** | Rounded values are compared at the number of significant digits written in the source value (rule 4.6). `9.7804391396e+12` is compared at 11 digits | 972 books.csv values show 11 digits because the file dropped a trailing zero. Book 5998 (Wanted) agrees at the 11 digits written and gets ISBN-13 `9780988707429` (example 3). Comparing at a full 12 digits instead would make it a conflict, with 13 conflicting rows rather than 12 |

**Note on A10.** "Significant digits actually present in the source" was read as the digits written in the cell. If the partners meant the 12 digits of precision the conversion kept (counting the dropped trailing zero), rule 4.6 should say "12 significant digits", example 3 becomes a conflict, and Asha's Week 3 count of 13 conflicting records is reproduced.

Items A1 to A8 and A11 from `proposed-rules-reviewed.md` are carried into the draft unchanged: rules 2.7 (A1, A11 through stage order), 6.3 (A2), the start of run database (A3), 2.8 (A4), 8.2 and the raw ISBN differences log (A5), the `clean_isbn10` and `clean_isbn13` names (A6), 1.7 (A7), and 4.3 (A8).

## 3. Where each decision came from

**Asha** follows Asha's Week 3 rules, **George** follows George's, **Both** combines them, and **New** was stated by neither.

| Question | Draft rule | Source |
|---|---|---|
| Primary identifier and unique Goodreads ID | 2.3, 2.4 | Both |
| Required fields | 2.2 | Both |
| Changed title or author rejected | 2.5 | George |
| Trimmed, case sensitive comparison of `title` | 2.6 | George |
| Possible duplicate warning | 2.8 | George |
| `work_id` not used | 2.9 | New |
| Kept but flagged rows count as loaded | 9 | New |
| Rounded ISBN-13 disagreeing with ISBN-10 is a conflict | 6.1 | New |
| Valid ISBN pair that disagrees: both blank, book kept | 6.1 | George |
| ISBN owned by another book: blank, book kept | 6.2 | George |
| Shared ISBN within a file | 6.3 | New |
| Different valid ISBN on an existing book: stored kept | 6.4 | George |
| 9790 is not an ISBN | 3.2 | George |
| Pad 7 to 9 digits | 4.2 | Asha |
| Wrong column moves in both directions | 4.3 | George |
| Spaces only cells are empty | 1.7 | George |
| Raw source columns plus repaired columns | 8.1, 8.2 | Asha |
| Fill ISBN-13 after a non-ISBN code, not after a damaged ISBN | 4.7, 5 | Both |
| Round half to even at the digits written | 4.6 | George |
| `.0` copy confirms the ISBN-10 | 4.4 | Asha |
| `.0` ISBN-10 that differs is a conflict (A9) | 4.4, 6.1 | New |
| Non-identity fields updated with history | 7.4, 8.3 | Asha |
| Rejected rows in the log only | 8.4 | George |
| Rerun behavior | 7.7 | Asha |
| Exact duplicates get their own reason | 2.7 | Asha |
| Mixed rows sharing a `book_id` all rejected | 2.7 | New |
| SHA-256, timestamp format, counts by issue, warning total | 10.2 | Asha |
| Line numbers from the CSV, header line 1 | 1.8 | George |
| Append each run | 10.1 | George |
| Self contained report | 10.3 | Both |
| Failed runs, one transaction | 1.4, 1.5 | Asha |
| Wrong field count rejected | 1.6 | Asha |
| Files beside `ingest.py` | 1.1 | Asha |
| Source files never modified | 1.2 | George |
| No AI or network lookups | 1.3 | George |

## 4. How the examples were checked

A verification script kept outside the project read books.csv and books-batch2.csv from this folder.

* **Computed:** every checksum, padding, conversion and round half to even comparison in the examples, including book 5998 at 11 digits, the three made-up ISBNs (valid and absent from both files), and example 8's `.0` value.
* **Confirmed in the files:** every line number, `book_id`, raw value and title used, and the exact columns that differ for books 24, 25 and 132 between the two files.
* **Run 1 rejects nothing:** every books.csv row has 23 fields, valid and unique IDs, a nonblank title and authors, and no exact duplicate. No repaired or converted ISBN is held by two books. This supports example 12.
* **Not verifiable yet:** outcome labels and warnings were derived by applying the rules by hand. They can only be confirmed once an implementation exists. Examples marked H are made up.
