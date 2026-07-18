# Decisions

## 2026-07-18 — Keep Phase 0 local and deterministic

Phase 0 scans only user-selected local directories. It performs no authentication,
network request, telemetry, AI call, or automatic repository modification.

## 2026-07-18 — Use independent checks

Every rule implements the shared `Check` protocol and returns one Pydantic `Finding`.
The scanner owns ordering and orchestration; reporters consume only the completed
`Report`. This keeps checks isolated and fixture-testable.

## 2026-07-18 — Deduct points by severity

Scores start at 100 and failed high, medium, low, and informational findings deduct
20, 10, 5, and 0 points. The simple formula is predictable for users and automation.

## 2026-07-18 — Treat Docker as low-severity universal polish

Missing Docker support always deducts five points. It improves reproducibility but
does not outweigh foundational documentation, licensing, tests, or CI.

## 2026-07-18 — Make the environment example conditional

`.env.example` fails only when deterministic environment-usage signals are present.
The scanner checks example-file metadata but never opens `.env` or `.env.*` content.

## 2026-07-18 — Stabilize reports with Pydantic

Findings and reports use fixed field order, string severity values, ordered findings,
timezone-aware UTC timestamps, and version `0.1.0`. All renderers share this model.

## 2026-07-18 — Reject protected paths before access

Traversal skips symlinks, generated directories, dependency trees, known credential
filenames, environment files, and private-key suffixes. Environment detection also
skips oversized text. Explicit report output rejects protected path components,
symlink components, and existing non-regular targets before creating directories or
writing content.

## 2026-07-18 — Prefer strict, bounded text detection

Environment-usage candidates are limited by suffix, location, and a 1 MiB size cap.
They are decoded as strict UTF-8; undecodable files are skipped rather than decoded
heuristically. This favors predictable findings and avoids interpreting binary data.

## 2026-07-18 — Render untrusted values literally and on one logical line

Human reporters collapse embedded line breaks and control characters. The terminal
renderer passes dynamic values as literal Rich `Text`, while Markdown escapes inline
syntax and table delimiters. This prevents scanned names from injecting report markup.

## 2026-07-18 — Isolate fixture repositories from project test discovery

Fixture repositories remain under `tests/fixtures`, but pytest excludes that tree
from recursive discovery. Their intentionally incomplete or sample test files are
scanner inputs, not tests for GitHub Repo Doctor itself.

## 2026-07-18 — Accept Phase 0 filesystem snapshot limits

Checks verify regular files and avoid symlinks, but Phase 0 does not lock a repository
against concurrent mutation. Hard links look like ordinary regular files and are not
rejected. Stronger race-resistant traversal is deferred until its portability and
complexity are justified.

## 2026-07-18 — Use uv_build

The user approved `uv_build` as the build-only backend paired with uv. Application
runtime dependencies remain limited to Typer, Rich, and Pydantic.
