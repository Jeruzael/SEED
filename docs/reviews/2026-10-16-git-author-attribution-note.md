# Git Author Attribution Note — the `berg` Contributors-Graph Entry

- **Date:** 2026-10-16
- **Repository:** `Jeruzael/SEED`

## What was observed

GitHub's contributors list for this repository shows the
account `berg` (an unrelated GitHub user) with 88
contributions. The owner did not add this account as a
collaborator, and it has never had any repository access
beyond what any GitHub account has on a public repository.

## Cause

Commits authored by the owner's development agent ("berg",
running Muse) from its virtual machine used the git identity
`berg (Muse) <berg@users.noreply.github.com>`. GitHub resolves
the legacy noreply address form
`<username>@users.noreply.github.com` to the account holding
that username, so the agent's commits were attributed to that
account in the contributors graph.

## Scope

- 89 commits across all refs, dated 2026-10-11 to 2026-10-15,
  carry the agent identity as author and committer; GitHub's
  contributors graph attributes 88 of them to the `berg`
  account.
- Every such commit is identifiable by the author name
  "berg (Muse)". None was authored by the account holder,
  and no access was ever granted to or exercised by that
  account through this artifact. Repository collaborators are
  unchanged.

## Decision (owner, 2026-10-16)

Prospective fix only. The agent's git identity is now
`berg (Muse) <berg@agent.local>` — a non-GitHub domain that
cannot resolve to any GitHub account. The commit that adds
this note is the first commit under the new identity.

## Why history was not rewritten

Changing the email on the existing commits would change their
SHAs and invalidate the commit-level evidence cited across
the B10 and S1 review records. The misattribution is a
cosmetic graph label; this note is its permanent explanation
of record.
