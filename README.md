# GitHub Repo Doctor

GitHub Repo Doctor is a local-only CLI that scores practical repository readiness.
It checks documentation, licensing, tests, CI, Docker support, and environment-file
hygiene without uploading or rewriting repository contents.

## Installation

```bash
uv sync
```

## Quickstart

```bash
uv run repo-doctor scan .
```

## Development

```bash
make test
make lint
make typecheck
```

## Scoring

The score starts at 100 and applies documented deductions for failed readiness checks.
