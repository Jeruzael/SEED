# Security Policy

SEED is an experimental research project. Its development and evaluation tools are not represented as production-hardened software. No particular version currently has a guaranteed security-support period.

## Reporting a vulnerability

Please **do not** disclose suspected vulnerabilities, reproduction data containing private information, credentials, or exploit details in public GitHub issues, discussions, or pull requests.

If the repository's **Security → Report a vulnerability** option is available, use GitHub's private vulnerability reporting. If that option is unavailable, contact the repository owner through an existing private communication channel first. Do not publish sensitive details while arranging a secure reporting route.

A useful private report contains:
- A concise description and the affected code or component.
- Minimal, redacted reproduction steps and relevant environment details.
- The security impact and practical preconditions.
- Suggested mitigation, if known.

Do not send active keys, passwords, personal data, or private datasets, and do not attempt to access third-party systems or SEED installations without authorization.

## Scope and response

Reports affecting runtime storage boundaries, unsafe file access, evaluation isolation, authentication, CI workflows, dependencies, and leaked credentials are welcome. Maintainers will assess reports as capacity permits; this project does not promise a service-level response time.

A confirmed exposed credential must be revoked or rotated by its owner. Deleting it from the latest commit or adding it to `.gitignore` is not sufficient if it appeared in Git history. Public clones cannot be reliably recalled, even if history is later rewritten.

## Safe contributions

Propose changes via reviewed pull requests rather than directly modifying `master`. Keep GitHub Actions permissions minimal, avoid persisting checkout credentials, and never commit local runtime directories, evaluator state, environment files, or secrets.

SEED B10 engineering verification must not be misrepresented as empirical scientific acceptance. Empirical evaluation and execution-unlock changes require separate explicit owner authorization.
