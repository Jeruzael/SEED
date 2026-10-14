# S1 — Historical Credential-Exposure Audit (Read-Only)

- **Repository:** `Jeruzael/SEED` (public)
- **Tracking issue:** #39
- **Audit date:** 2026-10-15 (Asia/Manila)
- **Master at audit time:** `f2602c3c61f96ac38098c38fecf3863df6c9be2d`
  ("Merge PR #35: Public repository security policy and PR safeguards")
- **Auditor:** independent audit agent (read-only; no repository
  modification, no history rewrite, no credential rotation)
- **Status of this report:** PREPARED, UNCOMMITTED. Publication
  requires owner approval after independent review of this report.

## 1. Method

- A fresh **mirror clone** of the repository was created in an
  isolated audit workspace, separate from any installed SEED
  organism and from the working development clone:
  `git clone --mirror git@github.com:Jeruzael/SEED.git`.
- Scanner: **Gitleaks 8.30.1** (official release binary,
  `gitleaks_8.30.1_linux_x64.tar.gz`, full SHA-256
  `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`,
  verified against the official release checksums file during
  the deep independent review), default rule configuration
  (no custom rules, no allowlist), run with `--redact=100`
  so no finding could print a secret value into any log or
  report.
- Three passes were executed:
  1. `gitleaks git` over the mirror with `--log-opts="--all"`
     (full history across all mirrored refs).
  2. `gitleaks dir` over **every blob** extracted from the
     mirror's object store (complete blob census, independent
     of commit-diff mechanics).
  3. A targeted pass over the one file whose content Git treats
     as binary (see §3), with NUL bytes stripped, across all
     19 historical versions.
- Supplementary names-only sweeps (file names reported, never
  matching lines): private-key headers
  (`BEGIN … PRIVATE KEY`), token prefixes (`ghp_`, `gho_`,
  `github_pat_`, `sk-`, `AKIA…`, `xox[baprs]-`), and
  credential-assignment patterns
  (`password|secret|api_key|auth_token` with a quoted value).
- A path census listed every file path that ever existed in
  history and screened it for credential-adjacent names
  (`.env`, `*.pem`, `*.key`, `*.p12`, `credential*`, `secret*`,
  `id_rsa`, `id_ed25519`).

## 2. Coverage

| Item | Count |
| --- | --- |
| Advertised remote refs | 75 (1 HEAD symref, 37 heads, 37 pull) |
| Mirrored refs | 74 (37 heads + 37 `refs/pull/*/head`) |
| Tags | 0 (none advertised) |
| Commits across all refs | 293 (all reachable from `master`) |
| Objects in mirror | 2,674 (293 commits, 1,276 trees, 1,105 blobs) |
| Unreachable objects in mirror | 0 (`git fsck --unreachable`) |
| Blobs examined | 1,105 / 1,105 (33,929,343 bytes total; see coverage note) |
| Commits with text diffs scanned (pass 1) | 252 / 293 |

Pass-1 coverage delta, fully accounted for: 39 of the 293
commits are merges, for which `git log` produces no default
patch; 2 further commits (`718b070`, `b7bb5bb`) touch only
`docs/evaluation/artifact-replay-gates.md`, whose content
contains a NUL byte and is therefore treated as binary by Git
and skipped by diff-based scanning. Those two commits' content
is inside the blob census (pass 2) and was additionally scanned
in text form in pass 3.

**Coverage note (corrected 2026-10-15 after the deep
independent review, finding MINOR-1):** an earlier draft of
this report overstated pass-2 coverage as "1,105 / 1,105 blobs
content-scanned". Byte reconciliation shows Gitleaks read
33,537,388 of the 33,929,343 total blob bytes: it binary-skips
exactly one blob, the roadmap PDF
`docs/roadmaps/SEED_B10_to_0.3_Development_Roadmap_v1.0.pdf`
(391,955 bytes, single historical version), in both pass 1 and
pass 2. That blob was instead examined by text extraction
(`pdftotext`, 45,823 bytes of extracted text) scanned with
Gitleaks and with the supplementary sweeps — no findings — and
its raw bytes were also covered by the names-only text sweeps
(0 matches). With that compensating check, every blob in the
mirror has been examined in a meaningful form at least once.

## 3. Results

- Pass 1 (history, all refs): **no leaks found** (exit 0 under
  `--exit-code 0`; Gitleaks reported 0 findings).
- Pass 2 (blob census): **no leaks found** in the 1,104 blobs
  Gitleaks reads as content; the remaining blob (the roadmap
  PDF) was examined by text extraction per the §2 coverage
  note — **no leaks found**.
- Pass 3 (NUL-stripped ledger file, 19 versions, 185.87 KB):
  **no leaks found**.
- Private-key header sweep: **0 files**.
- Token-prefix sweep: **0 files**.
- Credential-assignment sweep: **0 files**.
- Path census: **no credential-adjacent file path has ever
  existed in the history** (no `.env`, key, or credential files
  under any name matched).
- Execution failures: none. (One local environment note: the
  scanner binary tarball required `--no-same-owner` to extract
  in the audit VM; this did not affect scanning.)

### Classification

- **CONFIRMED EXPOSURE:** none.
- **FALSE POSITIVE:** none (there were no findings to classify).
- **UNRESOLVED / REQUIRES PRIVATE INVESTIGATION:** none.

No credential values appear anywhere in this report or in the
audit logs; all scanner output was produced under full
redaction.

## 4. Limitations

A clean result means *no known unresolved exposure within the
verified scope below* — it is not proof that all historical
information is safe.

1. **Server-side unreachable objects.** A clone receives only
   objects reachable from advertised refs. Dangling or
   unreachable objects retained on GitHub's servers (e.g. from
   force-pushed or deleted branches) are not transferred by
   the fetch protocol and could not be scanned. The mirror
   itself contains 0 unreachable objects.
2. **Unadvertised refs.** GitHub advertises branch heads and
   `refs/pull/*/head`; server-side refs not advertised for
   fetch (such as `refs/pull/*/merge`) were not separately
   scanned. Their head-side content is within the mirrored
   pull refs.
3. **Binary content.** Image and other binary blobs were
   included in the blob census; the targeted text sweeps read
   them as text and found nothing, but data embedded in
   binaries in non-textual form (e.g. steganography) is beyond
   pattern scanning. Concretely, the one PDF blob in history
   is binary-skipped by Gitleaks and was examined through its
   extracted text layer (§2 coverage note); content present
   in a PDF only as rendered/vector data without a text layer
   would not be visible to that check either.
4. **Encoded or fragmented secrets.** Secrets that are
   base64-encoded, encrypted, split across strings, or in
   novel formats can evade rule-based scanners, including
   Gitleaks' default rules (no custom configuration was used).
5. **Outside Git.** Issue/PR attachments, release assets,
   GitHub Actions logs and secrets, gists, and any fork's
   independent history are outside this audit's scope.
6. **Point-in-time.** The audit covers history up to the
   master SHA above and the refs advertised at audit time.
7. **Filename-keyed rules in pass 2.** The blob census
   extracted blobs under their hash names, so any scanner
   rule keyed on a file's path or name could not fire in that
   pass. This is mitigated by pass 1, which scans history
   with real paths, and by the deep independent review's
   compensating scan of seven full trees exported with real
   filenames (1,797 files, zero findings).

## 5. Remediation status and recommendation

- Private remediation required: **none** (no confirmed or
  unresolved exposure was found, so no revocation or rotation
  is indicated by this audit).
- **Recommendation: PASS — no known unresolved credential
  exposure within the verified scope.**
- This audit does not authorize I31 or G7, does not unlock
  empirical dispatch, and is not scientific acceptance. It
  removes one documented pre-I31 concern (unknown historical
  exposure) within the limits of §4.

## 6. Next steps (owner-gated)

1. Independent security review of this redacted report.
2. Owner decision on publishing this report (a documentation
   PR, per project process) and on closing Issue #39.
3. No history rewrite is recommended: with zero findings,
   rewriting public history would carry cost and risk with no
   identified benefit.
