# S1 — Deep Independent Historical Security Review

## 1. Reviewer designation and independence declaration

Fresh, deep independent reviewer agent. I am **not** the original
S1 auditor and **not** the author of the earlier report review
(`report-review.md`). I did not assume any prior conclusion: every
material number below was recomputed by me from the mirror, the
scanner, or the live remote, and two scans (history git pass and
the NUL-file pass) plus one compensating scan were re-executed by
me independently. Read-only throughout: I modified neither the
original report, the mirror, any repository, nor any history,
and I committed and published nothing. No credential value was
seen, printed, or copied at any point (all sweeps were run in
names/counts-only form).

## 2. Exact reviewed repository SHA

`f2602c3c61f96ac38098c38fecf3863df6c9be2d` (master,
"Merge PR #35: Public repository security policy and PR
safeguards"). Verified live during this review:
`git ls-remote origin master` still returns exactly this SHA —
**the baseline has not moved** since the audit.

## 3. Original audit report identity

`docs/reviews/2026-10-15-seed-historical-credential-audit.md`
(prepared, uncommitted copy at
`~/workspace/audit-s1/report-work/docs/reviews/2026-10-15-seed-historical-credential-audit.md`),
audit date 2026-10-15, tracking issue #39, auditor's
recommendation "PASS — no known unresolved credential exposure
within the verified scope."

## 4. Commands executed and verification methodology

- `git ls-remote origin` (full advertisement) and per-class
  counts; `git for-each-ref` in the mirror; SHA-for-SHA diff of
  all mirror `refs/heads/*` and `refs/pull/*/head` against the
  live advertisement.
- `git rev-list --all --count`, `--no-merges --count`,
  `rev-list master --count`; `git cat-file --batch-all-objects`
  census and exact blob-byte summation; `git fsck --unreachable`.
- Read of both original structured outputs
  (`gitleaks-full.json`, `gitleaks-blobs.json`) at byte level.
- Independent re-execution of `gitleaks git` on the mirror with
  `--redact=100` and **default exit-code behaviour** (no
  `--exit-code 0`), JSON report to my own scratch.
- Byte-level reconciliation of pass 2 (total blob bytes vs
  scanner-reported scanned bytes), plus single-blob control
  scans of the only two NUL-containing blobs.
- Blob-inventory diff: `ls blobs/` vs the mirror's blob hash
  list.
- Compensating real-filename scan: `git archive` exports of 7
  trees, one `gitleaks dir` over the set, `--redact=100`.
- NUL-file forensics: per-version blob enumeration, NUL count
  on the version introduced at `718b070`, byte totals of
  `nulcheck/`, and my own `gitleaks dir` rescan of `nulcheck/`.
- Provenance: full `sha256sum` of the retained tarball;
  download of the official `gitleaks_8.30.1_checksums.txt` from
  the Gitleaks v8.30.1 GitHub release; comparison; `sha256sum`
  of the extracted binary; `gitleaks version`; searches for
  `.gitleaks.toml` / `.gitleaksignore` in the master tree, the
  full history path list, and the audit workspace.
- Independent re-runs of all supplementary sweeps
  (names/counts only) and the credential-adjacent path census.
- Full read of the original report for safety and limitations.

## 5. Verified ref, commit, object, and blob counts

Every figure in the original report's coverage table reproduced
**exactly**:

| Item | Report claim | My recomputation |
| --- | --- | --- |
| Advertised refs | 75 (1 HEAD, 37 heads, 37 pull) | 75 (1 / 37 / 37) ✓ |
| Tags | 0 | 0 ✓ |
| Mirrored refs | 74 | 74 ✓ |
| Commits (`rev-list --all`) | 293 | 293 ✓ |
| Merge commits | 39 (implied) | 293 − 254 non-merges = 39 ✓ |
| Commits reachable from master | 293 (all) | `rev-list master` = 293 ✓ |
| Objects | 2,674 | 293 commits + 1,276 trees + 1,105 blobs = 2,674 ✓ |
| Unreachable objects in mirror | 0 | `fsck --unreachable` = 0 ✓ |
| Blob files extracted | 1,105 | 1,105, hash list identical to Git's ✓ |
| Mirror pull/head refs vs live | (implied current) | SHA-identical for all 37 + 37 ✓ |
| Total blob content | 33.54 MB (see Finding MINOR-1) | **33,929,343 bytes total**; 33,537,388 bytes is the Gitleaks-scanned subset ✓/⚠ |

## 6. Verified Gitleaks version and configuration

- Binary reports **8.30.1** (`gitleaks version`).
- Effective configuration: **default embedded rules**. The
  original commands carried no `--config` flag, and no
  `.gitleaks.toml` or `.gitleaksignore` exists in the master
  tree, anywhere in the full history path census, or in the
  audit workspace. No allowlist or exclusion was in play.
- Redaction: `--redact=100` on the original runs and on all of
  mine.

## 7. Results of all three passes

- **Pass 1 (git history, `--log-opts="--all"`):** original
  structured output is literally `[]` (3 bytes). My independent
  re-run reproduced it exactly: 252 commits scanned, 4,269,217
  bytes, "no leaks found", JSON `[]`. **Zero findings —
  confirmed.**
- **Pass 2 (blob census):** original structured output is
  literally `[]`. Gitleaks scanned 33,537,388 bytes. Zero
  findings — **confirmed for every blob Gitleaks actually
  read**; see §9/Finding MINOR-1 for the single binary blob it
  skipped.
- **Pass 3 (NUL-stripped ledger file):** my own rescan of
  `nulcheck/` reproduced 185,865 bytes scanned, "no leaks
  found", JSON `[]`. **Zero findings — confirmed.**

## 8. Scanner exit-code assessment

The original pass 1 was run with `--exit-code 0`, so its exit
code, taken alone, would prove nothing — the original report
disclosed this transparently ("exit 0 under `--exit-code 0`;
Gitleaks reported 0 findings"). The zero-finding conclusion
does **not** rest on that exit code: (a) the structured JSON
output is an empty array, (b) the run log records "no leaks
found", and (c) my re-run **without** `--exit-code 0` returned
the true default exit code **0**, which Gitleaks returns only
when no findings exist (it exits 1 otherwise), with byte-identical
scan volume. The exit-code concern is fully resolved.

## 9. Binary / NUL-file coverage verification

- The 252-vs-293 delta is exactly as the report explains:
  39 merges produce no default patch; commits `718b070` and
  `b7bb5bb` each touch **only**
  `docs/evaluation/artifact-replay-gates.md` (verified by
  `diff-tree`), whose blob Git treats as binary.
- The ledger file has exactly **19 distinct historical blob
  versions** (recomputed). The version introduced at `718b070`
  is blob `96f34bf6d585…` (2,851 bytes) and contains exactly
  **1 NUL byte** (offset 2528); `b7bb5bb` replaces it with the
  2,852-byte fixed version. `nulcheck/` holds 19 files
  totalling **185,865 bytes = 185.87 KB**, as claimed.
- Pass 3 did not replace the original-byte scan: pass 2 covered
  the **original unmodified** ledger blob — a single-blob
  control scan shows Gitleaks reads all 2,851 bytes of it
  (its NUL does not trigger Gitleaks' binary skip). Pass 3's
  NUL-stripped copies were an additional pass, not a substitute.
- **The one true coverage gap (Finding MINOR-1):** exactly two
  blobs in the census contain NUL bytes — the ledger blob above
  and blob `39cdacd1d461…`, the roadmap PDF
  (`docs/roadmaps/SEED_B10_to_0.3_Development_Roadmap_v1.0.pdf`,
  391,955 bytes). Byte reconciliation is exact:
  33,929,343 (total) − 33,537,388 (Gitleaks pass-2 scanned) =
  **391,955 = the PDF blob, byte for byte**. A single-blob
  control run confirms Gitleaks scans **0 bytes** of the PDF
  (binary skip); it was likewise unscanned in pass 1 (binary
  diff). The PDF's raw bytes were covered by the names-only
  text sweeps (0 matches), but text inside a PDF is typically
  Flate-compressed, so raw-byte pattern sweeps are weaker there
  than on plain text — a nuance the report's binary limitation
  covers only generically.

## 10. Credential and filename-sweep results (independently re-run)

All zero, matching the original report:

- Private-key headers (`BEGIN … PRIVATE KEY`): **0 files**.
- Token prefixes (`ghp_`, `gho_`, `github_pat_`, `sk-`,
  `AKIA…`, `xox[baprs]-`): **0 files**.
- Credential-assignment patterns (password/secret/api_key/
  auth_token with a quoted value): **0 files**.
- Path census across all history: **no** `.env`, `*.pem`,
  `*.key`, `*.p12`, `credential*`, `secret*`, `id_rsa`, or
  `id_ed25519` path has ever existed (**0 matches**).

Formats these patterns do **not** cover (stated for honesty):
tokens without known prefixes, credentials in prose or config
syntax outside the assignment pattern, values shorter than the
pattern thresholds, split/encoded strings, and text compressed
inside binary containers (see §9). Gitleaks' broader default
rule set (150+ rules incl. generic entropy-based detection)
mitigates much of this for the plain-text content it read.

## 11. Scanner provenance assessment

- Full SHA-256 of the retained tarball, computed by me:
  `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`.
- The official `gitleaks_8.30.1_checksums.txt` from the
  Gitleaks v8.30.1 GitHub release lists exactly this hash for
  `gitleaks_8.30.1_linux_x64.tar.gz` — **full match**. The
  scanner binary is authentically the official release.
- Extracted binary SHA-256 (for the record):
  `88f91962aa2f93ac6ab281d553b9e125f5197bbbce38f9f2437f7299c32e5509`.
- The original report printed only the 16-hex prefix
  (`551f6fc83ea457d6`). The prefix is correct, but a prefix
  alone does not let a reader verify integrity — see Finding
  INFORMATIONAL-1. Provenance itself is **fully verified**.

## 12. Findings by severity

### BLOCKER — none.

### MAJOR — none.

### MINOR-1 — Pass-2 coverage wording overstates Gitleaks coverage of one binary blob

- **Evidence:** §5/§9 above. Total blob content is 33,929,343
  bytes; Gitleaks pass 2 scanned 33,537,388; the delta is
  exactly the 391,955-byte roadmap PDF blob, which a control
  run shows Gitleaks scanning as 0 bytes.
- **Affected claim:** report §2 — "Blobs content-scanned
  1,105 / 1,105 (33.54 MB)" and "Every blob in the mirror was
  therefore content-scanned at least once."
- **Impact:** LOW. One roadmap PDF; its raw bytes returned 0
  matches on every sweep; no indication of credential content;
  the audit's zero-exposure conclusion is not materially
  weakened. But the sentences as written tell a reader Gitleaks
  examined content it in fact skipped, and the fallback
  (raw-byte sweeps) is weaker on compressed PDF streams than
  the report conveys.
- **Recommended disposition:** correct the two sentences before
  publication — e.g. "Blobs submitted to the scanner:
  1,105 / 1,105; Gitleaks content-scanned 1,104 (33,537,388
  bytes). The remaining blob — a 391,955-byte binary PDF —
  was skipped by the scanner as binary in both passes and was
  covered by the raw-text sweeps only; text compressed inside
  binary containers is a stated limitation (§4.3)."
- **Blocks publication:** YES, until corrected (narrowly — see
  §15). Does not block the audit's PASS conclusion.

### INFORMATIONAL-1 — Scanner checksum printed as prefix only

- **Evidence:** §11. The full hash is now verified against the
  official release checksums; the report carries only
  `551f6fc83ea457d6`.
- **Impact:** MINIMAL — provenance is in fact sound; only the
  report's verifiability by third parties is reduced.
- **Disposition:** print the full SHA-256 in the report.
- **Blocks publication:** NO (bundle with MINOR-1's correction).

### INFORMATIONAL-2 — Pass-2 filename-keyed-rule caveat not mentioned in the report

- **Evidence:** pass-2 blobs were extracted under hash names,
  so any Gitleaks rule keyed on file path/name could not fire
  in that pass; the original report does not note this.
- **Impact:** NEGLIGIBLE in fact — pass 1 scans with real paths
  across all history, and my compensating check exported 7
  full trees with real filenames (master `f2602c3`, root
  `6dd5429`, `2940fae`, `1dd7c58`, `082391f`, and the parents
  of both NUL commits; 1,797 files, 18.68 MB) and scanned them
  with real paths: **zero findings**.
- **Disposition:** add one sentence to the report's limitations
  noting the hash-name extraction and the pass-1 mitigation.
- **Blocks publication:** NO.

### UNRESOLVED — none.

**Counts: BLOCKER 0 / MAJOR 0 / MINOR 1 / INFORMATIONAL 2 /
UNRESOLVED 0.**

## 13. Limitations and unresolved questions

The original report's six limitations are honest and complete
as far as they go: server-side unreachable objects (a clone
provably cannot fetch them; the mirror's own `fsck` count is
0), unadvertised refs (`refs/pull/*/merge` content is composed
of the mirrored head-side objects), binary-embedded data,
encoded/encrypted/fragmented/novel formats, out-of-Git surfaces
(attachments, Actions logs, forks), and point-in-time scope.
The report nowhere implies those areas were scanned, and it
correctly frames its result as "no known unresolved exposure
within the verified scope," not proof of absolute safety. Two
additions are recommended (the PDF-specific binary nuance in
MINOR-1 and the filename caveat in INFORMATIONAL-2); neither
opens an unresolved question. There are **no unresolved
questions** from this review: the one quantity that initially
looked discrepant (33.54 MB vs 33.93 MB total) is fully
explained by the verified PDF skip.

## 14. Final verdict

**S1 INDEPENDENT HISTORICAL SECURITY REVIEW: PASS WITH FINDINGS**

The original audit's central claims are, on my independent
recomputation, accurate: complete advertised-ref coverage,
293 commits, 1,105 blobs, a genuine official scanner, zero
findings in all three passes (independently reproduced for
passes 1 and 3 and byte-reconciled for pass 2), zero sweep
matches, and honest limitations. The PASS recommendation of the
original audit is supported. The findings concern the precision
of two coverage sentences and documentation completeness — not
the audit's conclusion.

## 15. Recommendation

**HOLD** — narrowly and only until the MINOR-1 wording
correction (and, in the same edit, the INFORMATIONAL-1 full
checksum and INFORMATIONAL-2 limitation sentence) is applied
to the report by its author. Publishing a report that states
"1,105 / 1,105 content-scanned" while the verified record shows
one binary blob was skipped would repeat, in miniature, the
kind of overstatement this audit chain exists to catch. Once
those corrections land, the report is PUBLICATION READY with
no further review required from me, and the S1 audit verdict
stands as **PASS — no known unresolved credential exposure
within the verified scope**.

---

*Review safety note (task §H): I read the original report in
full. It contains no credential values, no authentication
headers, no personal account data beyond the public repository
name and issue number, and no unredacted scanner output (all
scanner artifacts are empty result sets produced under
`--redact=100`). Subject to the corrections above, it is
suitable for publication in a public repository.*
