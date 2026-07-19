# Scoring

GitHub Repo Doctor starts every repository at 100 points. Only failed enabled
findings deduct points, and the final score is clamped at zero.

## Severity deductions

| Severity | Deduction | Meaning |
| --- | ---: | --- |
| High | 20 | A foundational trust or adoption signal is missing. |
| Medium | 10 | A meaningful maintainability signal is missing. |
| Low | 5 | Useful professional polish is missing. |
| Info | 0 | Context that does not lower readiness. |

These are the built-in defaults. A version-1 `.repo-doctor.toml` may override all
four global deductions with integers from 0 through 100. `info` must remain zero,
and values must satisfy `high >= medium >= low >= info`. Scores still begin at 100
and clamp at zero.

Each check may be disabled independently under `[checks.<finding-id>]`. Disabled
checks are outside the effective policy: they do not run, appear in findings, or
deduct points. At least one check must remain enabled. Check order always follows
the built-in registry rather than TOML table order.

Passed enabled findings remain in JSON and Markdown but deduct nothing.

## Checks and categories

| Check | Category | Severity | Failure deduction |
| --- | --- | --- | ---: |
| README exists | Documentation | High | 20 |
| README has at least two useful sections | Documentation | Medium | 10 |
| License exists | Licensing | High | 20 |
| Tests exist | Testing | Medium | 10 |
| GitHub Actions workflow exists | Automation | Medium | 10 |
| Docker or Compose setup exists | Operations | Low | 5 |
| `.env.example` exists when environment usage is detected | Configuration | Medium | 10 |

The environment check passes when no environment usage is detected. Missing Docker
support always deducts five points under the default policy: containers are useful
reproducibility polish, but less fundamental than documentation, licensing, tests,
or CI.

## Detection contract

- A root `README.md`, `README.rst`, or `README` satisfies the existence check.
  README usefulness requires at least two recognized headings: Installation, Usage,
  Quickstart, Setup, Testing, Development, Contributing, or License.
- A root `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `LICENCE`, `LICENCE.md`,
  `LICENCE.txt`, `COPYING`, `COPYING.md`, `COPYING.txt`, or `UNLICENSE` satisfies
  the license check. Names are case-insensitive; contents are not interpreted.
- A `tests` directory or a conventionally named test file satisfies the tests check.
- At least one regular `.yml` or `.yaml` file under `.github/workflows` satisfies CI.
- A root `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`, `compose.yml`, or
  `compose.yaml` satisfies Docker setup.
- Environment usage is detected from a bounded set of tokens in supported source and
  configuration files, a root Compose file, or the selected README. Candidate files
  must be regular, at most 1 MiB, and strict UTF-8; undecodable candidates are skipped.
  The reserved root policy and effective policy source are never opened by environment
  detection. Protected environment files are also never opened, and a root regular
  `.env.example` is checked by metadata only.

Symlinked candidates and non-regular file candidates do not satisfy these checks.

## Why each check matters

- **README exists:** visitors need a clear project entry point.
- **Useful README sections:** installation and usage guidance reduce adoption friction.
- **License exists:** users need explicit legal permission to use and contribute.
- **Tests exist:** automated examples increase confidence in changes.
- **GitHub Actions exists:** CI makes project checks repeatable for contributors.
- **Docker exists:** container metadata can make setup more reproducible.
- **Environment example:** placeholder names document configuration without exposing
  real values.

## Score bands

| Score | Summary |
| ---: | --- |
| 90–100 | Excellent readiness with strong open-source hygiene. |
| 75–89 | Good foundation with a few worthwhile improvements. |
| 50–74 | Meaningful readiness gaps should be addressed. |
| 0–49 | Substantial work is recommended before sharing. |

## Not checked yet

Repo Doctor does not inspect remote repositories, vulnerability databases, dependency
graphs, source-code quality, license contents, screenshots, contribution guides,
codes of conduct, security policies, GitHub settings, or AI-generated suggestions.
It does not modify scanned repositories.

Scanning is a best-effort local snapshot. Concurrent filesystem mutation is outside
the scanner consistency model, and hard links cannot be distinguished from ordinary
regular files through the metadata checks used here.
