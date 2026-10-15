# S1 — Targeted Verification: PDF Extraction Evidence & Corrected Audit Report

## Reviewer designation and independence declaration

Fresh independent reviewer agent for this targeted verification
only. I did **not** perform the original S1 audit, did **not**
write the deep independent review (`deep-review.md`), and did
**not** apply the corrections to the audit report. Every value
below was recomputed by me from primary artifacts: the mirror
(`~/workspace/audit-s1/seed-mirror.git`), the auditor's retained
artifacts (`pdfcheck/`, `blobs/`, scan logs and JSON), and the
scanner (`~/workspace/tools/gitleaks`, 8.30.1). Read-only
throughout: I edited neither report and changed nothing in the
audit workspace (my scratch work is in `/tmp/tv-scratch/`). No
credential value was seen, printed, or copied at any point; all
sweeps were run in counts-only form.

- **Repository / baseline:** `Jeruzael/SEED`,
  master `f2602c3c61f96ac38098c38fecf3863df6c9be2d` (per the
  audit and deep review records).
- **Documents verified:** the corrected audit report
  (`report-work/docs/reviews/2026-10-15-seed-historical-credential-audit.md`)
  and, for Target 3, the deep review (`deep-review.md`).

## Target 1 — PDF text-extraction evidence (all recomputed)

| Claim | Recomputed value | Result |
| --- | --- | --- |
| Only blob ever at `docs/roadmaps/SEED_B10_to_0.3_Development_Roadmap_v1.0.pdf` | `git rev-list --all --objects` shows exactly one blob for that path: `39cdacd1d461813f035325b81f9ee86a57e9c851` | ✓ exact |
| Blob size 391,955 bytes | `git cat-file -s` = **391,955** | ✓ exact |
| `pdfcheck/` holds that blob's PDF + extracted text | `39cdacd1….pdf` (391,955 B) and `39cdacd1….pdf.txt` (45,823 B) present; the PDF is **byte-identical** (`cmp`) to the blob extracted fresh from the mirror | ✓ |
| Extracted text = 45,823 bytes | My own `pdftotext` (Poppler 24.02.0) extraction of the mirror blob: **45,823 bytes**, and `cmp`-**byte-identical** to the auditor's `.txt` | ✓ exact — no version-variance/materiality question arises |
| Gitleaks over the extraction: zero findings | My run, `gitleaks dir` with `--redact=100` over my own extraction: "scanned ~45823 bytes … no leaks found"; JSON report literally `[]` | ✓ zero findings |
| Supplementary sweeps over extracted text: all zero | Private-key headers **0**; token prefixes (`ghp_`/`gho_`/`github_pat_`/`sk-`/`AKIA`/`xox…`) **0**; credential-assignment pattern **0** (all counts over my extraction) | ✓ all zero |
| Byte reconciliation: total − pass-2 scanned = PDF size | Census recomputed via `cat-file --batch-all-objects`: **1,105 blobs, 33,929,343 bytes total**. Pass-2 scanned volume **33,537,388** bytes — confirmed in the auditor's original log and independently reproduced by my own re-run of `gitleaks dir` over `blobs/` ("scanned ~33537388 bytes … no leaks found"). 33,929,343 − 33,537,388 = **391,955**, exactly the PDF blob | ✓ exact |

Target 1 conclusion: the compensating PDF check is genuine and
complete — the single Gitleaks-skipped blob's text layer was
extracted reproducibly (byte-identical output) and is clean
under Gitleaks' full default rule set and all three
supplementary patterns.

## Target 2 — Corrected audit report accuracy

Read in full. Confirmations, with section references:

- **(i) 1,105 blobs inventoried** — §2 table: 2,674 objects
  (293 commits, 1,276 trees, **1,105 blobs**); "Blobs examined
  1,105 / 1,105 (33,929,343 bytes total; see coverage note)".
  ✓
- **(ii) 1,104 blobs scanned by Gitleaks as raw content** —
  §3, Pass 2: "no leaks found **in the 1,104 blobs Gitleaks
  reads as content**"; §2 coverage note gives the underlying
  byte figures (33,537,388 of 33,929,343 read; exactly one
  blob binary-skipped). ✓ The submitted-vs-read distinction
  is now drawn precisely.
- **(iii) One binary PDF examined via extracted text plus
  supplementary checks** — §2 coverage note: `pdftotext`,
  45,823 bytes of extracted text, "scanned with Gitleaks and
  with the supplementary sweeps — no findings — and its raw
  bytes were also covered by the names-only text sweeps
  (0 matches)". Matches Target 1's recomputation exactly. ✓
- **(iv) Remaining binary/encoded limitations still stated** —
  §4 item 3 (binary content; the PDF named concretely,
  including "content present in a PDF only as rendered/vector
  data without a text layer would not be visible to that check
  either"), §4 item 4 (base64-encoded, encrypted, split, or
  novel-format secrets can evade rule-based scanners), §4
  item 7 (filename-keyed rules in pass 2, with the pass-1 and
  compensating-tree-scan mitigations, matching the deep
  review's INFORMATIONAL-2 disposition). ✓
- **Transparent correction record** — §2 carries a note headed
  "Coverage note (corrected 2026-10-15 after the deep
  independent review, finding MINOR-1)" that quotes the
  earlier draft's overstatement ("1,105 / 1,105 blobs
  content-scanned") verbatim before correcting it. The
  correction is disclosed in place, not silently rewritten. ✓
- **Full scanner SHA-256 (§1)** — the report prints
  `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`;
  my own `sha256sum` of `~/workspace/tools/gitleaks.tar.gz`
  returns exactly this value (which the deep review §11
  already matched to the official release checksums). ✓
- **§3 claims** — no sentence in §3 claims all 1,105 blobs
  were Gitleaks-scanned; Pass 1's line is transparent about
  the `--exit-code 0` flag. ✓
- **Recommendation scoping (§5)** — "PASS — no known
  unresolved credential exposure **within the verified
  scope**", and "This audit does not authorize I31 or G7,
  does not unlock empirical dispatch, and is not scientific
  acceptance." ✓ No overreach.
- **Deep review record** — `deep-review.md` stands unaltered
  as the historical record of the pre-correction review:
  **S1 INDEPENDENT HISTORICAL SECURITY REVIEW: PASS WITH
  FINDINGS, BLOCKER 0 / MAJOR 0 / MINOR 1 / INFORMATIONAL 2 /
  UNRESOLVED 0**, recommendation HOLD pending exactly the
  corrections (MINOR-1 wording; INFORMATIONAL-1 full checksum;
  INFORMATIONAL-2 limitation sentence) that the corrected
  report now contains, per its §15 condition. This targeted
  verification is the separate record of the correction and
  the PDF evidence, as required; the deep review's verdict is
  neither edited nor superseded in place. ✓

## Target 3 — Publication safety of both documents

Pattern scans (counts of matches **with payloads**) over both
files:

| Pattern class | Corrected audit report | Deep review |
| --- | --- | --- |
| Token payloads (`ghp_`/`gho_`/`github_pat_`/`sk-`/`AKIA…`/`xox…` + payload) | 0 | 0 |
| Private-key blocks (`BEGIN … PRIVATE KEY`) | 0 | 0 |
| Auth headers (`Authorization: Bearer/Basic/Token …`) | 0 | 0 |
| AWS secret-key assignment pattern | 0 | 0 |
| Email-regex matches | 1 — identified: `git@github.com`, GitHub's public SSH endpoint inside the documented `git clone --mirror` command; not personal data | 0 |

Both documents otherwise contain only: the public repository
name (`Jeruzael/SEED`), the public issue number (#39), public
commit/blob SHAs of a public repository, the official Gitleaks
release checksum and extracted-binary checksum (public release
data), and scanner result summaries that are empty result sets
produced under `--redact=100`. Descriptive pattern strings
(e.g. bare `ghp_` in methodology text) appear without payloads,
as expected. **Both documents are safe for publication in a
public repository.** ✓

## Findings

- **BLOCKER:** none.
- **MAJOR:** none.
- **MINOR:** none.
- **INFORMATIONAL-1 (non-defect observation):** §1's method
  list still describes pass 2 as "`gitleaks dir` over **every
  blob** extracted from the mirror's object store". Read alone
  this could be misread as a coverage claim; in context it
  describes submission (all 1,105 blobs *were* presented to
  the scanner), and §§2–3 now state precisely that Gitleaks
  read 1,104 of them as content and binary-skipped one. The
  wording is accurate as written; no correction is required.
  Recorded only so a future reader is not confused by the
  difference between §1's method summary and §2's coverage
  accounting.
- **UNRESOLVED:** none.

## Final lines

**TARGETED VERIFICATION: PASS**

**PUBLICATION RECOMMENDATION: READY** — the PDF
text-extraction evidence is independently reproduced and
clean; the corrected audit report's coverage accounting
(1,105 inventoried / 1,104 Gitleaks-read / 1 PDF examined via
extracted text) is accurate in every particular I recomputed;
the deep review's PASS WITH FINDINGS (0/0/1/2/0) and its
MINOR-1 remain the preserved historical record; and both
documents are safe for public publication. This recommendation
covers publication readiness only — it does not merge any PR,
close issue #39, or authorize I31/G7.
