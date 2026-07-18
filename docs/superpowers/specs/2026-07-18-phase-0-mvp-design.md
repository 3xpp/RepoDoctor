# GitHub Repo Doctor Phase 0 MVP Design

**Status:** Approved for specification
**Date:** 2026-07-18

## Context

GitHub Repo Doctor helps developers evaluate whether a local repository makes a professional, maintainable first impression. Phase 0 is a deterministic, local-only Python CLI. Its analysis never changes the scanned repository or sends contents anywhere; only an explicitly requested `--output` report may be written.

The target users are students, junior developers, indie hackers, open-source maintainers, and small teams. The initial product favors clear explanations and predictable behavior over exhaustive analysis.

## Goals

- Scan a local repository using seven focused readiness checks.
- Return a score from 0 to 100 and a finding for every check.
- Explain failed checks with severity, category, and a concrete recommendation.
- Render the same report as a Rich terminal view, stable JSON, or Markdown.
- Support a CI-friendly score threshold without failing low-scoring scans by default.
- Package the CLI for Python 3.12 or newer and manage it with `uv`.
- Prove behavior with unit tests and good/bad repository fixtures.

## Non-goals

Phase 0 does not include remote repositories, GitHub authentication or APIs, automatic fixes, vulnerability scanning, dependency-graph analysis, AI services, a web application, a database, or telemetry. Repository inspection is read-only. The CLI may create or replace only the report file explicitly requested with `--output`, including when that path is inside the scanned repository, but it refuses every protected environment, credential, or private-key filename defined by the secret-safety rules.

## Initialization Status

The previously empty directory was initialized as a Git repository on the `main` branch before design work continued. Root contributor guidance is committed in `AGENTS.md`; it records the `uv` workflow, deterministic-check rules, dependency policy, secret protections, stable JSON requirement, documentation responsibilities, and conventional-commit policy.

## Chosen Product Approach

The score uses universal severity deductions. A missing Docker setup is a low-severity finding for every repository because container support is valuable polish but is not essential. The environment-example check is the sole applicability-aware rule: it only fails when environment-variable usage is detected and `.env.example` is absent.

This approach is preferred over fully applicability-aware scoring because two users looking at the same repository should receive the same easily explained result. It is preferred over category point budgets because direct severity deductions are simpler to document and extend in an MVP.

## Architecture

The package is divided into focused domains:

- `cli.py` owns Typer argument parsing, output selection, file writing, and exit codes.
- `scanner.py` validates a repository path, runs an ordered check registry, and builds a report.
- `checks/base.py` defines the check protocol. Each check receives a repository `Path` and returns one `Finding`.
- Individual modules under `checks/` implement README, license, tests, CI, Docker, and environment-example rules.
- `models.py` defines Pydantic enums and models for findings and reports.
- `scoring.py` is a pure calculation from findings to a clamped score and deterministic summary.
- Modules under `reporting/` render terminal, JSON, and Markdown representations without rescanning.

The data flow is:

```text
CLI path and options
        |
        v
local scanner -> ordered checks -> Finding list
        |                              |
        +---------- scoring <----------+
                       |
                       v
                    Report
                       |
        +--------------+--------------+
        v              v              v
     terminal         JSON         Markdown
```

Checks do not call one another and reporters do not know how findings were produced. This keeps each rule independently testable and allows future checks without changing report rendering.

## Report Contract

`Severity` is a string enum with `info`, `low`, `medium`, and `high` values.

Each `Finding` contains, in stable field order:

1. `id`
2. `title`
3. `description`
4. `severity`
5. `category`
6. `recommendation`
7. `passed`

Each `Report` contains, in stable field order:

1. `repo_path`
2. `score`
3. `max_score`
4. `summary`
5. `findings`
6. `generated_at`
7. `version`

`generated_at` is a timezone-aware UTC timestamp. `version` starts at `0.1.0`. JSON uses Pydantic JSON-mode serialization, two-space indentation, enum values rather than enum names, ISO 8601 timestamps, and a final newline. Findings remain in registry order so automation receives deterministic ordering. Stability means a consistent schema and ordering; timestamp values naturally differ between scans.

Every check has an intrinsic category and severity. Those values remain the same whether the check passes or fails, so passed findings are stable automation records rather than a separate result type. The environment check therefore remains `medium` and `Configuration` when no environment usage is detected.

## Initial Checks

| Finding ID | Category | Pass condition | Severity | Deduction on failure |
| --- | --- | --- | --- | ---: |
| `readme-exists` | Documentation | A root-level `README.md`, `README.rst`, or `README` exists, case-insensitively. | high | 20 |
| `readme-sections` | Documentation | A discovered README has at least two recognized section headings. | medium | 10 |
| `license-exists` | Licensing | A recognized root-level license file exists, case-insensitively. | high | 20 |
| `tests-exist` | Testing | A `tests/` directory or a recognized test filename exists. | medium | 10 |
| `ci-exists` | Automation | `.github/workflows/` contains at least one regular `.yml` or `.yaml` file. | medium | 10 |
| `docker-exists` | Operations | A root-level `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`, `compose.yml`, or `compose.yaml` exists. | low | 5 |
| `env-example` | Configuration | No environment usage is detected, or root-level `.env.example` exists. | medium | 10 |

README candidates use the fixed priority `README.md`, `README.rst`, then `README`, with case-insensitive comparison. If a case-sensitive filesystem contains multiple spellings of the same candidate, lexicographic filename order breaks the tie. The sections check reads only that selected file.

README headings are matched case-insensitively for `installation`, `usage`, `quickstart`, `setup`, `testing`, `development`, `contributing`, and `license`. Markdown ATX and setext headings are recognized; reStructuredText section titles are recognized when underlined. Matching headings instead of arbitrary prose reduces false positives. If no README exists, both README findings fail because presence and usefulness represent separate readiness concerns.

Recognized license filenames are `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `LICENCE`, `LICENCE.md`, `LICENCE.txt`, `COPYING`, `COPYING.md`, `COPYING.txt`, and `UNLICENSE`, compared case-insensitively.

Recognized test files include Python `test_*.py` and `*_test.py`, plus JavaScript or TypeScript `*.test.js`, `*.test.jsx`, `*.test.ts`, `*.test.tsx`, `*.spec.js`, `*.spec.jsx`, `*.spec.ts`, and `*.spec.tsx`. Search skips generated, dependency, version-control, and virtual-environment directories.

## Filesystem and Secret Safety

Filesystem inspection is read-only. Explicit report-file writing belongs only to the CLI output layer. Checks use `pathlib`, reject symlinked files, walk with symlink following disabled, and never resolve a discovered path outside the selected repository.

Recursive content discovery prunes exactly these directory names: `.git`, `.hg`, `.svn`, `.venv`, `venv`, `env`, `node_modules`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.tox`, `.nox`, `dist`, `build`, `coverage`, and `htmlcov`.

The environment detector considers regular files with these lowercase suffixes: `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`, `.toml`, `.yaml`, `.yml`, `.json`, `.ini`, `.cfg`, `.conf`, and `.sh`. It additionally considers the selected root README and the four supported root Compose filenames. Files larger than 1 MiB are rejected before content is opened.

Protection is applied before metadata size checks or content reads. The detector rejects basename `.env`, every basename starting with `.env.`, `.envrc`, `.npmrc`, `.pypirc`, `credentials`, `credentials.json`, `secrets.json`, `secrets.yaml`, `secrets.yml`, `secrets.toml`, `service-account.json`, `id_rsa`, and `id_ed25519`. It also rejects suffixes `.pem`, `.key`, `.p12`, `.pfx`, and `.keystore`. Existence of `.env.example` is checked through directory-entry metadata only and its contents are never opened.

Environment usage is detected through fixed, case-sensitive source tokens `os.environ`, `os.getenv(`, `process.env`, `import.meta.env`, `load_dotenv(`, `dotenv.config(`, `from dotenv`, and `import dotenv`. Compose and configuration text additionally recognizes `env_file:` and interpolation matching `\$\{[A-Z_][A-Z0-9_]*\}`. README text recognizes `.env` or `.env.example` when bounded by whitespace, backticks, quotes, or line boundaries. Matching text and variable names are never included in a report.

A scanner-level safety unit test replaces the environment candidate iterator with a protected path named `.env`, installs a read spy that fails immediately, and invokes `scan_repository`. Passing proves the full scanner orchestration filters the path before any open/read operation. Fixture files and committed tests contain placeholders only and never contain real credentials.

## Scoring and Summary

The score begins at 100. Only failed findings deduct points:

- high: 20 points
- medium: 10 points
- low: 5 points
- info: 0 points

The score is clamped at zero. Passed checks remain in JSON and Markdown; the terminal view summarizes passes and focuses its finding groups on failures.

Summary text is based only on the final score:

- 90–100: excellent readiness
- 75–89: good foundation with minor improvements
- 50–74: meaningful readiness gaps
- 0–49: substantial work recommended before sharing

With these weights, the complete good fixture scores 100. The nearly empty bad fixture scores 25 because the conditional environment check passes when no environment usage exists.

## CLI Contract

The package exposes the `repo-doctor` command with a `scan` subcommand:

```text
repo-doctor scan PATH [--format terminal|json|markdown] [--output FILE] [--fail-under 0..100]
```

- `PATH` defaults to `.` and must resolve to a readable directory.
- `--format` defaults to `terminal`.
- Terminal output shows the repository, score, summary, passed-check count, failures grouped high-to-low, and recommendations.
- JSON and Markdown print to standard output unless `--output` is supplied.
- `--output` writes UTF-8 text and creates missing parent directories. It is supported for JSON and Markdown, not terminal rendering. A protected basename or suffix is rejected before directories are created or files are opened.
- A normal scan exits 0 regardless of score.
- If `--fail-under` is provided and the score is lower, rendering or file writing completes and the process exits 1.
- Invalid paths, invalid thresholds, unsupported option combinations, and output failures produce concise messages and exit 2.

Machine-readable output is never mixed with Rich decoration or status messages on standard output.

## Error Handling

Expected CLI errors are converted to short, actionable messages without tracebacks. A check must not silently hide unexpected programming errors. Files that disappear during a scan, cannot be decoded as text, or become unreadable are skipped by content-based detection; structural existence checks still operate on available metadata. The scanner performs no recovery that writes into the scanned repository.

## Packaging and Tooling

The project targets Python 3.12 and uses a `src/` package layout. Runtime dependencies are Typer, Rich, and Pydantic. Development dependencies are pytest, Ruff, and mypy. The packaging plan proposes `uv_build`, the build-only backend maintained for `uv`; it is not imported by the application and introduces no runtime dependency. Because it is outside the brief's explicit dependency list, implementation requires the user's approval of this specification before adding it. No other third-party packages are included.

The Makefile exposes `install`, `dev`, `test`, `test-e2e`, `lint`, `typecheck`, `format`, and `build` commands with the behavior specified in the project brief.

Root project hygiene includes the standard MIT `LICENSE` text, a Python-focused `.gitignore` that excludes real environment files while explicitly retaining `.env.example`, and a placeholder-only `.env.example`. The example explains that Phase 0 requires no environment variables and lists only empty reserved values for `GITHUB_TOKEN`, `OPENAI_API_KEY`, and `OLLAMA_BASE_URL`; no value is copied from the process environment or another file.

## Testing Strategy

Unit tests cover README detection and heading thresholds, license candidates, each score deduction and score clamping, JSON serialization shape and ordering, output writing, threshold exit behavior, and the protected environment-file boundary.

End-to-end tests scan two committed fixtures:

- `good_repo` includes a useful README, license, tests, GitHub Actions workflow, Dockerfile, environment usage, and `.env.example`; it must score at least 90.
- `bad_repo` contains only a harmless placeholder source file; it must score below 50.

CLI tests use Typer's `CliRunner`. JSON tests parse standard output rather than relying only on string snapshots. Time-dependent tests inject or construct a fixed timestamp. Validation runs unit tests, end-to-end tests, Ruff, mypy, package build, direct good/bad scans, JSON parsing, and both passing and failing threshold scenarios.

## Documentation

The root README explains the product, repository-hygiene motivation, installation, three required quickstart commands, terminal and JSON examples, development commands, limitations, and roadmap. `docs/SCORING.md` documents every category, severity, deduction, why each check matters, and the capabilities deliberately not scored in Phase 0. `docs/DECISIONS.md` records durable architectural choices, and `docs/FAILURES.md` records encountered implementation or environment failures and their resolutions.

## Delivery Milestones

1. Bootstrap packaging, metadata, license, ignore rules, and source/test structure.
2. Add report models, scoring, scanner orchestration, and seven checks.
3. Add terminal, JSON, and Markdown rendering plus CLI behavior.
4. Add fixture-based unit and end-to-end coverage.
5. Add user documentation and scoring/decision/failure records.
6. Run every acceptance check, inspect the final tree and commit history, and leave a clean worktree.

Each completed milestone receives a conventional commit. No remote is configured or pushed by this work.
