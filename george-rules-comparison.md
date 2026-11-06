# Module 4 — Comparison of Week 3 Book Ingestion Rules

**Course:** MSAI-5523, Language of Computation  
**Partners:** George (`Georgec4444`) and Asha (`AshaAbdulkadir`)  
**Prepared:** November 5, 2026  
**Status:** **Neutral working draft — no shared rules have been approved**

## Purpose and sources

This document compares the two students' existing Week 3 `rules.md` files **decision by decision**. It does not judge which rules are better, choose between them, or modify either student's Week 3 rules. The partners must review and edit this comparison together before agreeing on a single Week 4 `rules.md`.

- [George's Week 3 rules (assignment branch)](https://github.com/Georgec4444/language-of-computation-week3-assignment/blob/assignment/rules.md) — 15 numbered rules, additional clarifications and final decisions, and 26 test examples.
- [Asha's Week 3 rules (assignment branch)](https://github.com/AshaAbdulkadir/language-of-computation-week3-assignment/blob/assignment/rules.md) — six sections, 21 ISBN test examples, and implementation decisions.

**Status key:** **Agree** = same stated policy on this point; **Disagree** = different policies or outcomes; **One-sided** = only one document explicitly specifies the decision; **Clarify** = broadly similar but the precise conditions or results may differ. An outcome described as **conditional** depends on other input fields or the database state not specified in that example.

## Part A — Decision-by-decision comparison

### A1. ISBN validation, repair, and missing values

| # | Decision | George's Week 3 rule | Asha's Week 3 rule | Status |
|---|---|---|---|---|
| 1 | ISBN-10 validation | Nine digits plus digit or `X`; modulus-11 checksum. | Same structure and checksum. | **Agree** |
| 2 | ISBN-13 validation | Thirteen digits, 978 or 979 prefix; explicitly excludes 9790/ISMN. | Thirteen digits, 978 or 979 prefix; no explicit 9790 exception. | **Clarify** |
| 3 | Raw source preservation | Original CSVs unchanged; original problematic values preserved in logs; all 23 supplier fields preserved in database. | Original CSVs unchanged; raw `isbn`/`isbn13` stored exactly as received, with separate cleaned fields. | **Agree** on preservation; storage differs |
| 4 | Restore leading zeroes | Pad a digit-only ISBN-10 shorter than 10 characters if checksum passes. | Pad a 7–9-character ISBN-10 if checksum passes. | **Clarify**: 1–6-digit inputs |
| 5 | Remove spaces/hyphens | Remove simple formatting, then validate and log. | Same. | **Agree** |
| 6 | Lowercase final `x` | Convert to `X`, validate, log. | Same. | **Agree** |
| 7 | Valid ISBN in wrong column | Move to correct column if no conflict; derive counterpart when permitted. | Explicitly move ISBN-13 found in `isbn`; other wrong-column cases not equally explicit. | **Clarify** |
| 8 | ISBN-10 stored in ISBN-13 column with `.0` | Damaged decimal forms are invalid; do not repair by guessing or stripping `.0`. | Permit a specific `.0` repair when it matches the row's ISBN-10. | **Disagree** for that specific case |
| 9 | Scientific-notation ISBN-13 with supporting ISBN-10 | Reconstruct only from valid ISBN-10 if rounded scientific value matches at its stated precision; final clarification specifies decimal half-even rounding. | Reconstruct only if valid ISBN-10 conversion agrees with rounded ISBN-13. | **Clarify** exact rounding and significant-digit rules |
| 10 | Rounded ISBN-13 without reliable ISBN-10 | Leave damaged value blank; warn; do not guess. | Same. | **Agree** |
| 11 | Incorrect check digit | Never change digit merely to make checksum pass; leave invalid field blank and warn. | Same; explicitly mentions books 916, 2374, 5026. | **Agree** |
| 12 | ISBN-10 ↔ ISBN-13 conversion when destination is truly empty | Derive 978 counterpart from validated source; log. | Same. | **Agree** |
| 13 | Derive ISBN-13 after original ISBN-13 is invalid or a product code | Explicitly **do not** bypass rejection of a damaged/non-ISBN value by deriving from ISBN-10; only derive when original field was genuinely empty. | Example *Sailor Moon #1* discards a product code and derives ISBN-13 from valid ISBN-10. | **Disagree** |
| 14 | ISBN-13 starting 979 | Accept valid 979 ISBN-13; no ISBN-10 conversion; no missing-ISBN warning. | Same. | **Agree** |
| 15 | Invalid characters, extra digits, truncation | Do not invent or delete arbitrary digits; invalid ISBN blank, warning. | Same. | **Agree** |
| 16 | Non-ISBN barcodes/product codes | Never accept as ISBN; preserve problem for review. | Same, with specific examples (2940, UPC, 622, 123). | **Agree** |
| 17 | Book with no usable ISBN | Keep if valid supplier `book_id`, nonempty title and author. | Keep if valid unique `goodreads_book_id`; reject otherwise. | **Disagree** on required identity |
| 18 | Warning for bad/missing ISBN | Warn when invalid/missing; repairs logged separately. | Warn when invalid/missing; repairs and 979 exception not warnings. | **Agree** in general |

### A2. Book identity, conflicts, and duplicates

| # | Decision | George's Week 3 rule | Asha's Week 3 rule | Status |
|---|---|---|---|---|
| 19 | Primary book identity | Supplier `book_id` is primary key; compare title and author as cross-check. | `goodreads_book_id` is primary; validated ISBN-13 secondary; `book_id` is stored but not used for identity. | **Disagree** |
| 20 | Required fields | Positive whole-number `book_id`, nonblank `title`, nonblank `authors`; otherwise reject. | Valid positive digit-only `goodreads_book_id` required even if ISBN is usable; explicit title/author rejection rule not stated. | **Disagree / One-sided** |
| 21 | Two valid ISBNs in one row identify different books | Keep identifiable **new** book, store both ISBNs NULL, flag for review; existing record is preserved. | Reject incoming row and flag for review. | **Disagree** |
| 22 | ISBN already assigned to another book | Keep incoming identifiable book, set its conflicting ISBN NULL, flag for review. | Reject incoming conflicting record, flag for review. | **Disagree** |
| 23 | Goodreads ID and ISBN-13 point to different records | No separate Goodreads-ID identity rule; use supplier `book_id` and ISBN-conflict handling. | Reject as conflicting identities. | **Disagree** |
| 24 | Two rows share an identifier but have different values | Same `book_id` with conflicting title/author: reject incoming row and preserve stored book; other supplier-field differences are review-only. | Two new rows with same Goodreads ID but different values: reject both; existing accepted book is preserved. | **Disagree / Clarify** |
| 25 | Exact duplicate rows within one delivery | Insert once, skip repeat, log. | Same. | **Agree** |
| 26 | Same work versus same edition | Different `book_id`s remain separate; flag possible duplicates. | Shared `work_id` denotes another edition, not the same book. | **Clarify** overlapping intent, different explicit rules |
| 27 | Title/author/year match across identifiers | Flag potential duplicate, do not auto-merge; trim title/author for exact, case-sensitive comparisons. | May suggest a match in general rule, but implementation says script does **not** suggest matches; no auto-merge. | **Clarify** |
| 28 | Reused ID with changed title/author | Reject changed row for same `book_id`; preserve original. | Goodreads ID governs identity; other fields compared exactly and may be updated. | **Disagree** |

### A3. Repeated ingestion, updates, and database structure

| # | Decision | George's Week 3 rule | Asha's Week 3 rule | Status |
|---|---|---|---|---|
| 29 | Rerun identical data | Do not duplicate or create unnecessary updates. | Same; unchanged rows skipped. | **Agree** |
| 30 | Compare repaired ISBNs | Compare normalized/validated values, not raw formatting. | Same. | **Agree** |
| 31 | Blank later value | Never overwrite a valid stored value with blank. | Same. | **Agree** |
| 32 | Safe improvement to missing/invalid ISBN | Update validated ISBN when same book and no conflict; log. | Same principle, with Goodreads identity. | **Agree**, conditional on identity policy |
| 33 | New valid ISBN conflicts with different valid stored ISBN | Preserve existing value, flag; classify according to other update rules. | Reject incoming row and flag. | **Disagree** |
| 34 | Updates to ratings and other non-ISBN fields | Preserve original values; report differences for review but do not automatically update. | Update other changed fields (e.g., ratings count), report change. | **Disagree** |
| 35 | Title/author whitespace | Trim for comparison; case-sensitive; preserve original stored text. | Compare non-ISBN fields exactly as text. | **Disagree** for whitespace-only changes |
| 36 | Database schema | One `books` table containing 23 supplier fields, `book_id` primary key; warnings and repairs in JSON log. | `books` table with raw and cleaned ISBNs, plus review and change-history tables; Goodreads identity. | **Disagree** on schema and keys |
| 37 | Preserve all source columns | Store all 23 supplier columns, as text except validated integer key; blanks become NULL. | Store all 23 source columns as text, plus cleaned ISBN fields. | **Clarify** key type and blank representation |

### A4. Logs, reports, and operational rules

| # | Decision | George's Week 3 rule | Asha's Week 3 rule | Status |
|---|---|---|---|---|
| 38 | One outcome per row | Loaded, updated, skipped, rejected; totals equal rows read; warning is separate. | Same. | **Agree** |
| 39 | Append ingestion history | Append each run to `ingestion-log.json`, preserving prior runs. | Requires run log and report; exact append behavior should be confirmed against the script and agreed rules. | **Clarify** |
| 40 | Repair and review details | Log original values, repairs, row numbers, book IDs, reasons, old/new values. | Same general detail; additionally issue counts and explicit review fields. | **Agree / Clarify** on required fields |
| 41 | SHA-256 input-file fingerprint | Not explicitly required. | Explicitly required in report header. | **One-sided: Asha** |
| 42 | HTML report | Self-contained, opens locally, selects JSON log, newest run first. | HTML report must display required report data; implementation says all section-4 details. | **Clarify** UI requirements |
| 43 | Timestamp format and timezone | Timestamp required; precise format not specified. | `yyyy-MM-dd HH:mm:ss`, local time with timezone; report header includes date. | **One-sided: Asha** |
| 44 | Missing/unreadable file | General principle: report rejected/unprocessed input; no detailed file-level failure protocol. | Record failed run; do not change DB; applies to missing file, bad UTF-8, missing/extra header columns. | **One-sided: Asha** |
| 45 | Malformed data row | Reject rows missing essential fields. | Reject rows whose field count differs from 23; continue remaining rows. | **Clarify** |
| 46 | File and output locations | CLI accepts CSV filename; database `books.db`; log `ingestion-log.json`. | CLI accepts CSV filename; database/log placed beside `ingest.py` regardless of working directory. | **Clarify** |
| 47 | External lookups or AI during ingestion | Explicitly prohibited. | Emphasizes no guesses and approved deterministic repairs; no equally explicit general ban. | **One-sided: George** |
| 48 | Original input files | Never edit `books.csv` or `books-batch2.csv`. | Same. | **Agree** |

## Part B — George's 26 examples, evaluated against Asha's rules

**Reading this table:** “Asha's rule would...” is a comparison of *written policies*, not a claim that either student's Python code has been run. Where identity fields or prior database contents are unknown, the comparison is conditional.

| George example | George's expected result | Applying Asha's written rules | Assessment |
|---|---|---|---|
| G1. `0439139600` valid ISBN-10 | Accept unchanged. | Accept valid ISBN-10. | **Agree** |
| G2. `9780439139601` valid ISBN-13 | Accept unchanged. | Accept valid ISBN-13. | **Agree** |
| G3. `439023483` | Pad to `0439023483`; log. | Same 9-digit padding; also in Asha's Hunger Games example. | **Agree** |
| G4. `61120081` | Pad to `0061120081`; log. | 8-digit ISBN-10 is within Asha's permitted 7–9 digits. | **Agree** |
| G5. `0-450-19827-8` | Remove hyphens; accept. | Same. | **Agree** |
| G6. `162 001 4750` | Remove spaces; accept. | Same. | **Agree** |
| G7. `031200009x` | Uppercase `X`; accept. | Same. | **Agree** |
| G8. `0439023483` + rounded ISBN-13 | Derive `9780439023481` if precision check passes. | Derive if rounded scientific value agrees; precise rounding policy not identical in wording. | **Clarify** |
| G9. Rounded ISBN-13 without valid ISBN-10 | ISBN-13 NULL; warn. | Same. | **Agree** |
| G10. *Small Hours*: wrong check digit | Invalid ISBN NULL; keep identifiable book; warn. | Invalid ISBN NULL; keep **only if** Goodreads ID valid and no identity conflict. | **Conditional** |
| G11. *The Glass Aviary*: illegal `A` | Invalid ISBN NULL; keep identifiable book; warn. | Same ISBN treatment; different identity requirements. | **Conditional** |
| G12. *Borrowed Light*: 11-digit ISBN-10 | ISBN NULL; warn; keep book. | Same invalid-ISBN treatment, subject to Goodreads ID. | **Conditional** |
| G13. `2940016231920` product code | ISBN NULL; warn. | Same. | **Agree**, if identity valid |
| G14. `195170342.0` damaged decimal | ISBN NULL; warn. | Asha permits a **different**, narrow `.0` case only if ISBN-10 stored in `isbn13` matches `isbn`; this example lacks that confirmation. | **Clarify** |
| G15. `9798351220413` | Valid ISBN-13, no ISBN-10 and no missing warning. | Same. | **Agree** |
| G16. `9780062398123` with ISBN-10 blank | Derive `0062398121`; log. | Same. | **Agree** |
| G17. Both ISBNs blank, identifiable book | Load by supplier ID/title/author; warn. | Load only with valid unique Goodreads ID. | **Different if identifiers differ** |
| G18. `9781982147600` in `isbn` field | Move; derive `1982147601`; log. | Same; Asha's Atlas example. | **Agree** |
| G19. *Tides of Marrow Bay*: valid but mismatched pair | Load book, both ISBNs NULL; review. | Reject row. | **Disagree** |
| G20. *Paper Moons*: ISBN assigned to *Angels & Demons* | Load book, incoming ISBN NULL; review. | Reject row. | **Disagree** |
| G21. Exact repeat for book 10001 | First load, second skip. | Same if identity valid. | **Agree** |
| G22. Hypothetical existing book gains safe ISBN | Update and log. | Same if Goodreads identity agrees. | **Agree / conditional** |
| G23. Existing book returns with blank ISBNs | Preserve stored ISBNs; skip if unchanged. | Same. | **Agree** |
| G24. Invalid/missing `book_id`, title or author | Reject entire row. | Asha requires Goodreads ID, not `book_id`; title/author rejection not stated as the same hard requirement. | **Disagree / Clarify** |
| G25. Non-ISBN supplier field changes | Preserve stored value; report difference, no automatic update. | Update changed non-ISBN field and report. | **Disagree** |
| G26. Trailing space in existing title | Trim for identity comparison; no new book or field update. | Goodreads identity determines match; non-ISBN text is compared exactly, potentially producing an update. | **Disagree** on update handling |

## Part C — Asha's 21 examples, evaluated against George's rules

| Asha example | Asha's expected result | Applying George's written rules | Assessment |
|---|---|---|---|
| A1. *Angels & Demons*, rounded ISBN-13 | Load; derive `9781416524793` from valid ISBN-10. | Same if original scientific value passes George's exact rounding test. | **Clarify** rounding |
| A2. *The Hunger Games*, short ISBN-10 + rounded ISBN-13 | Load; pad ISBN-10 and derive ISBN-13. | Same, subject to exact rounding check. | **Agree / Clarify** |
| A3. *Salt and Ember*, hyphenated ISBN-10 | Load; remove hyphens. | Same. | **Agree** |
| A4. *Winter Orchard*, lowercase `x` | Load; uppercase `X`. | Same. | **Agree** |
| A5. *An Atlas of Small Kindnesses*, ISBN-13 in `isbn` | Load; move to correct field and derive ISBN-10. | Same. | **Agree** |
| A6. *Notes from the Night Ferry*, 979 ISBN-13 | Load; no missing-ISBN-10 warning. | Same. | **Agree** |
| A7. *The Racketeer*, wrong check digit and unusable rounded ISBN-13 | Load with warning; both ISBNs blank using Goodreads ID. | Both ISBNs NULL and warn; load if valid supplier ID/title/author. | **Same ISBN result; identity conditional** |
| A8. *How to Win Friends and Influence People*, rounded ISBN-13 only | Load with warning; ISBN blank. | Same ISBN result; load if supplier identity valid. | **Same ISBN result; identity conditional** |
| A9. *Watchers*, ambiguous rounded ISBN-13 | Load with warning; ISBN blank. | Same ISBN result; load if supplier identity valid. | **Same ISBN result; identity conditional** |
| A10. *Sailor Moon #1*, valid ISBN-10 plus non-ISBN product code | Load with warning; derive ISBN-13 `9781892213013`. | Keep valid ISBN-10 but leave **damaged original ISBN-13 field NULL**; no derivation to bypass rejected field. | **Disagree** |
| A11. *Bossypants*, both ISBNs blank | Load with warning using Goodreads ID. | Load with warning if supplier `book_id`, title and author valid. | **Same outcome if both identities valid** |
| A12. *Nights in Rodanthe*, conflicting ISBNs | Reject. | Keep identifiable new book, both conflicting ISBNs NULL; review. | **Disagree** |
| A13. *Paper Moons*, ISBN used by another book | Reject. | Keep identifiable new book, conflicting ISBN NULL; review. | **Disagree** |
| A14. *Tides of Marrow Bay*, mismatched ISBN pair | Reject. | Keep identifiable new book, both ISBNs NULL; review. | **Disagree** |
| A15. Two identical *Lantern Keeper's Daughter* rows | First load, second skip. | Same. | **Agree** |
| A16. *Harry Potter and the Goblet of Fire*, previously repaired ISBNs | Skip unchanged repeat. | Same after normalized comparison, if no other material differences. | **Agree** |
| A17. *Harry Potter and the Deathly Hallows*, later blank ISBNs | Skip, preserve valid stored ISBN. | Same. | **Agree** |
| A18. *The Five People You Meet in Heaven*, ratings count changed | Update ratings count and report. | Do **not** update non-ISBN field; report difference, skip if no safe ISBN improvement. | **Disagree** |
| A19. *Borrowed Light*, extra ISBN digit | Load with warning; ISBN blank using Goodreads ID. | Same ISBN result; load if supplier identity valid. | **Same ISBN result; identity conditional** |
| A20. Made-up row: no ISBN, missing/reused Goodreads ID | Reject. | May load if supplier `book_id`, title and author are valid and unique; otherwise reject. | **Disagree / conditional** |
| A21. *Reading Lolita in Tehran*, invalid `0` check digit | Leave invalid ISBN blank; warn; do not change `0` to `X`. | Same no-guess rule; load if supplier identity valid. | **Agree / conditional** |

## Part D — Discussion and decisions for George and Asha

**No decisions have been made in this draft.** Record your joint choices here while discussing them. Update both copies of the final rules with the same language.

| Topic to settle | Question for both partners | Joint decision (to complete together) |
|---|---|---|
| Book identity | Is the primary identity `book_id`, `goodreads_book_id`, or a specified combination? What fields are mandatory? | **Pending** |
| Conflicting ISBN-10/ISBN-13 | Keep identifiable book with blank ISBNs, or reject row? What about existing records? | **Pending** |
| ISBN reused by another book | Keep new book without that ISBN, or reject it? | **Pending** |
| Goodreads/ISBN identity conflict | How do we resolve an ISBN pointing to a different Goodreads identity? | **Pending** |
| Scientific-notation precision | Which deterministic rounding and comparison method applies? | **Pending** |
| `.0` values | Is any exact, independently confirmed `.0` correction permitted? | **Pending** |
| Damaged ISBN-13 with valid ISBN-10 | Can we derive the ISBN-13 after rejecting the supplied product code or damaged value? | **Pending** |
| Missing ISBNs | Which identity fields must be present to keep an ISBN-less book? | **Pending** |
| Non-ISBN field changes | Update ratings/title/other supplier fields, or report without changing them? | **Pending** |
| Duplicate handling | What happens for duplicate supplier IDs, duplicate Goodreads IDs, matching ISBNs, and identical repeated rows? | **Pending** |
| Database schema | Which identity key, source columns, cleaned columns, review/history tables, and blank-value representations are required? | **Pending** |
| Logging and failures | Confirm append-only logs, SHA-256, timestamp format, HTML requirements, malformed input, and failed-run behavior. | **Pending** |

## Part E — How to turn this draft into the required shared rules

1. **Review this comparison together.** Check that each row fairly represents the two original Week 3 rules. Correct anything either partner believes is misstated.
2. **Fill in the joint decisions** in Part D. Where the source rules are silent, write a new explicit decision together.
3. **Create one complete, internally consistent set of agreed rules.** This is not a vote for one student's whole file; it is a new shared specification.
4. **End the agreed rules with a table of at least 12 ISBN input examples and their exact expected outcomes**, including conflict cases, invalid/missing values, repairs, repeated records, and updates. The examples must reflect the agreed rules, not conflicting Week 3 expectations.
5. **Give both partners an identical copy named `rules.md`** for the Week 4 assignment. The final assignment requires one `rules.md` in each student's workspace, not competing rule files.
6. **After Part 1, work independently** on pytest tests and `ingest.py` as the professor instructed. Do not share prompts, test code, or ingestion code.

### Scope note

This is a **document comparison**, not a run of the two ingestion programs or a database comparison. Any row-level prediction marked *conditional* requires checking actual input identity fields and the database's prior state. No final shared rules have been selected, and this draft should **not** be renamed to the agreed `rules.md` until both partners have made those decisions.
