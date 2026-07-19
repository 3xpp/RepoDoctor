# GitHub Repo Doctor Contributor Instructions

## Project Scope

GitHub Repo Doctor is a local-only Python CLI that evaluates repository readiness. Keep the local scanner deterministic: do not add remote scanning, GitHub API access, authentication, AI services, web applications, databases, or automatic rewriting of scanned repositories.

## Tooling

- Use Python 3.12 or newer.
- Use `uv` as the package and environment manager.
- Use Typer for the CLI, Rich for terminal reports, and Pydantic for report models.
- Use pytest, Ruff, and mypy for validation.
- Ask before adding any new runtime dependency.

## Engineering Rules

- Organize code by domain: CLI, scanner, checks, models, scoring, reporting, and tests.
- Keep scanner rules deterministic, isolated, and testable.
- Define checks through the shared check protocol and return stable Pydantic findings.
- Use fixture-based tests for repository checks and end-to-end behavior.
- Keep JSON field names and semantics stable; treat schema changes as deliberate compatibility changes.
- Keep `.repo-doctor.toml` schema changes versioned, strict, and backward-conscious.
- Derive configurable check IDs from the ordered check registry; never duplicate the
  registry in configuration code.
- Add default-compatibility, invalid-config, and secret-safety tests for every policy
  behavior change.
- Keep active policy contents out of environment-usage detection and report output.
- Update `docs/SCORING.md` whenever checks, severities, or deductions change.
- Prefer `pathlib` and the standard library for filesystem work.
- Keep source files focused and avoid unrelated refactors.

## Secret Safety

- Never read, print, edit, stage, or commit `.env` or real secret files.
- `.env.example` may contain placeholders only; never copy values from a real environment file.
- Never expose `GITHUB_TOKEN`, `OPENAI_API_KEY`, `OLLAMA_BASE_URL`, or other credentials.
- Scanner tests must prove protected environment files are not opened.

## Required Validation

Before committing implementation changes, run the checks relevant to the milestone. Before final handoff, run:

```text
make test
make test-e2e
make lint
make typecheck
make build
```

Verify both good and bad fixtures with the CLI, JSON output validity, and `--fail-under` behavior.

## Git Workflow

- Work in small, reviewable milestones.
- Use conventional commit messages.
- Preserve unrelated user changes.
- Do not push unless explicitly asked.
- Finish with a clean worktree unless an intentional exception is documented.
