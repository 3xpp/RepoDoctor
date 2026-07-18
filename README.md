# GitHub Repo Doctor

GitHub Repo Doctor is a local-only Python CLI that gives GitHub-style repositories
a practical readiness score and specific fixes. Phase 0 checks README quality,
licensing, tests, GitHub Actions, Docker setup, and environment-file hygiene.

It never uploads repository data, calls a remote API, or rewrites scanned files.
Only an explicitly requested, non-secret JSON or Markdown report path is written.

## Why repository hygiene matters

A working codebase can still be difficult to trust or adopt. Clear setup and usage
instructions, an explicit license, tests, CI, reproducible tooling, and safe
configuration examples help contributors understand a project before investing time.
Repo Doctor turns those first-impression signals into a deterministic report.

## Installation

Requirements: Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

For development from a clone:

```bash
uv sync
```

Install the local CLI as a uv tool:

```bash
uv tool install .
```

## Quickstart

```bash
repo-doctor scan .
repo-doctor scan . --format json
repo-doctor scan . --fail-under 80
```

The path defaults to the current directory. A low score still exits successfully
unless `--fail-under` is supplied.

## Example terminal report

An intentionally incomplete repository produces this output. Captured logical lines
remain stable regardless of the Rich console width:

```text
Repository readiness
25/100
Substantial work is recommended before sharing this repository.
Repository: /absolute/path/to/tests/fixtures/bad_repo
1/7 checks passed

HIGH findings
- README exists: Add README.md with the project's purpose and setup guidance.
- License exists: Add an OSI-approved license file such as LICENSE.

MEDIUM findings
- README has useful sections: Add at least two sections such as Installation, Usage, or Testing.
- Tests exist: Add a tests directory or conventionally named test files.
- GitHub Actions workflow exists: Add a workflow under .github/workflows to run project checks.

LOW findings
- Docker setup exists: Consider adding a Dockerfile or Compose file for reproducible setup.
```

Terminal and Markdown renderers treat report data as literal text and collapse
embedded control characters and line breaks to keep each logical value on one line.

## JSON output

```bash
repo-doctor scan . --format json
repo-doctor scan . --format json --output report.json
```

The stable JSON schema has this shape:

```json
{
  "repo_path": "/absolute/path/to/repository",
  "score": 25,
  "max_score": 100,
  "summary": "Substantial work is recommended before sharing this repository.",
  "findings": [
    {
      "id": "readme-exists",
      "title": "README exists",
      "description": "No supported root README file was found.",
      "severity": "high",
      "category": "Documentation",
      "recommendation": "Add README.md with the project's purpose and setup guidance.",
      "passed": false
    }
  ],
  "generated_at": "2026-07-18T12:00:00Z",
  "version": "0.1.0"
}
```

Passed findings remain in JSON so automation receives all seven check results.

## Markdown output

```bash
repo-doctor scan . --format markdown
repo-doctor scan . --format markdown --output report.md
```

Output files are allowed only for JSON and Markdown. Repo Doctor rejects protected
secret path components, symbolic-link components, and existing non-regular targets
before it creates directories or writes a report.

## CI threshold

```bash
repo-doctor scan . --fail-under 80
```

The report is rendered first. The command exits 1 only when its score is below the
requested threshold. Invalid input or an inaccessible path exits 2. These semantics
make the threshold useful in CI without making low scores fail by default.

## Development

| Command | Purpose |
| --- | --- |
| `make install` | Resolve the uv environment. |
| `make dev` | Scan this repository. |
| `make test` | Run unit tests. |
| `make test-e2e` | Run fixture-based end-to-end tests. |
| `make lint` | Run Ruff checks. |
| `make typecheck` | Run mypy against `src`. |
| `make format` | Format and apply safe Ruff fixes. |
| `make build` | Build the source and wheel distributions. |

Pytest excludes `tests/fixtures` from normal discovery so fixture files remain scan
inputs rather than becoming part of the project's own test collection.

## Scoring

Scores start at 100. Failed high, medium, and low findings deduct 20, 10, and
5 points respectively; informational findings deduct nothing. Scores never fall
below zero. See [docs/SCORING.md](docs/SCORING.md) for the complete contract.

## Limitations

Phase 0 does not scan remote repositories, authenticate with GitHub, inspect
dependency graphs, find vulnerabilities, judge source-code quality, verify license
contents, detect every possible environment-access idiom, or propose automatic fixes.
It does not check screenshots, contribution guides, codes of conduct, or security
policies yet.

Filesystem checks are deterministic best-effort snapshots, not a defense against a
repository being changed concurrently. Hard-linked files are indistinguishable from
ordinary regular files, and environment-usage candidates that are oversized or not
strict UTF-8 are skipped rather than decoded heuristically.

## Roadmap

- Add more deterministic open-source hygiene checks.
- Support explicit configuration of check applicability and weights.
- Add remote GitHub scanning only after the local contract is mature.
- Explore opt-in fix guidance without modifying repositories automatically.

## License

GitHub Repo Doctor is available under the [MIT License](LICENSE).
