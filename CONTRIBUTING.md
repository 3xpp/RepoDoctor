# Contributing to GitHub Repo Doctor

Thank you for helping improve GitHub Repo Doctor. Participation is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Security reports

Do not open a public issue for a suspected vulnerability. Use
[GitHub private vulnerability reporting](https://github.com/3xpp/RepoDoctor/security/advisories/new)
and follow the [security policy](SECURITY.md). Never include live credentials or
private repository data.

## Before starting

- Search existing issues before opening a new one.
- Use the bug or feature issue form so reports contain actionable context.
- Discuss substantial behavior, scoring, schema, or dependency changes before
  implementation.
- Ask before adding a runtime dependency.

## Development setup

Requirements:

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/3xpp/RepoDoctor.git
cd RepoDoctor
uv sync
```

Create a focused branch and keep changes small.

## Testing

Run the most focused relevant test while developing:

```bash
uv run pytest tests/unit/test_scoring.py -v
```

Before requesting review, run the complete project contract:

```bash
make test
make test-e2e
make lint
uv run ruff format --check .
make typecheck
make build
```

Fixture repositories under `tests/fixtures` are scanner inputs rather than test
modules. Use synthetic placeholders only. Never copy `.env` contents, credentials,
tokens, private keys, or private repository data into a fixture.

## Engineering contract

- Keep scanning deterministic, local-only, and read-only.
- Define rules through the shared check protocol.
- Derive stable configurable IDs from the ordered check registry.
- Preserve JSON field order and configuration semantics deliberately.
- Prefer `pathlib` and the standard library.
- Add default-compatibility, invalid-input, and secret-safety coverage for policy
  changes.
- Update `docs/SCORING.md` when checks, severities, or deductions change.
- Keep README commands and examples aligned with real CLI output.

## Commits and pull requests

Use conventional commit messages such as `feat:`, `fix:`, `test:`, `docs:`, and
`ci:`. Pull requests should explain the problem, the chosen solution, compatibility
impact, and exact validation performed.

Contributions are accepted under the project's [MIT License](LICENSE).
