# GitHub Repo Doctor Phase 1 Configuration Design

**Status:** Approved for specification
**Date:** 2026-07-19

## Context

Phase 0 provides a deterministic local scanner with seven fixed checks and fixed
severity deductions. Those defaults are useful for a broad audience, but not
every repository has the same readiness requirements. For example, a library may
not need Docker while a service team may want a stricter CI threshold.

Phase 1 introduces a small, versioned TOML configuration contract. A repository
can commit its policy beside its code, while an explicit CLI option can select a
different policy for local or CI use. Configuration changes which existing checks
run and how much failed severities deduct; it does not add remote access,
automatic fixes, new checks, or a web service.

## Goals

- Automatically discover `.repo-doctor.toml` at the root of the scanned repository.
- Support `--config PATH` as an explicit replacement for automatic discovery.
- Let users enable or disable each existing check independently.
- Let users configure global point deductions for `high`, `medium`, `low`, and
  `info` severities.
- Preserve Phase 0 checks, scores, findings, and output contracts when no
  configuration file exists, except for the deliberate `0.2.0` version value.
- Commit a ready-to-use root `.repo-doctor.toml` whose values match the defaults.
- Reject malformed, ambiguous, unknown, or unsafe configuration with concise CLI
  errors and exit code 2.
- Preserve existing JSON field names, types, and ordering while explicitly
  versioning the Phase 1 finding-list semantics.
- Cover discovery, precedence, validation, scoring, CLI behavior, and secret
  safety with unit and end-to-end tests.

## Non-goals

This phase does not add checks, per-check point weights, category budgets, custom
finding text, path include/exclude patterns, configuration inheritance, multiple
merged files, environment-variable overrides, remote configuration, config-file
generation commands, GitHub integration, AI suggestions, or automatic changes to
the scanned repository.

## Chosen Approach

The chosen approach is a versioned repository-root TOML file with an explicit CLI
override. Python's standard-library `tomllib` parses the file and Pydantic validates
the resulting structure. No new runtime dependency is required.

This is preferred over explicit-only configuration because a committed repository
policy should work with the simplest command, `repo-doctor scan .`. It is preferred
over CLI flags for every check and severity because a versioned file is repeatable,
reviewable, and practical in CI. It is preferred over merging multiple files because
one effective source has simple, predictable precedence.

## Configuration Contract

The canonical configuration is:

```toml
version = 1

[scoring]
high = 20
medium = 10
low = 5
info = 0

[checks.readme-exists]
enabled = true

[checks.readme-sections]
enabled = true

[checks.license-exists]
enabled = true

[checks.tests-exist]
enabled = true

[checks.ci-exists]
enabled = true

[checks.docker-exists]
enabled = true

[checks.env-example]
enabled = true
```

`version` is required and must be the integer `1`. The `scoring` and `checks`
tables are optional; omitted entries inherit built-in defaults. This allows a
minimal file such as:

```toml
version = 1

[checks.docker-exists]
enabled = false
```

Only the seven existing finding IDs are accepted below `checks`. Each check table
accepts only `enabled`, which must be a TOML Boolean. Unknown top-level keys,
unknown scoring keys, unknown check IDs, and unknown keys within a check table are
errors. Strict validation prevents misspellings from silently changing policy.

Scoring values must be TOML integers from 0 through 100; Boolean values are not
accepted as integers. `info` must remain `0`, and deductions must satisfy
`high >= medium >= low >= info`. These constraints preserve the meaning of the
severity names. A configured deduction may be zero, and the final score remains
clamped at zero.

Checks remain independent. Disabling `readme-exists`, for example, does not
implicitly disable `readme-sections`. Users who want neither README rule must
disable both explicitly. At least one of the seven checks must remain enabled;
configuration that disables all checks is rejected instead of producing a
misleading vacuous `100/100` report.

## Discovery and Precedence

Configuration resolution uses exactly one source:

1. If one `--config PATH` is present, that file is used and root auto-discovery is
   skipped completely.
2. Otherwise, `<resolved-repository-root>/.repo-doctor.toml` is used when it exists.
3. Otherwise, the immutable built-in defaults are used.

There is no field-by-field merge between an explicit file and the auto-discovered
file. Within the selected file, omitted optional values inherit built-in defaults.
An explicit path expands `~` and is otherwise interpreted relative to the process
working directory. A missing explicit file is an error; an absent automatic file is
normal. Repeating `--config` is ambiguous and exits 2 rather than silently choosing
the first or last value.

An explicit file prevents even metadata or content inspection of the automatic
candidate. This makes precedence observable and guarantees that an unsafe or invalid
root file cannot interfere with a deliberately selected policy.

## Architecture and Data Flow

A new `config.py` domain module owns:

- strict Pydantic models for the versioned file shape;
- immutable built-in settings;
- safe path validation and bounded TOML loading;
- discovery and explicit-path precedence;
- an internal loaded-configuration value containing settings and the optional source
  path;
- conversion from validated settings to enabled checks and severity deductions.

The CLI adds a `--config PATH` option, requests the effective configuration, and
converts configuration failures into concise exit-code-2 errors. Repository path
validation occurs before automatic discovery so the policy is always selected from
the actual resolved scan root. The scanner remains responsible for report
construction. Its scoring input is extended from the fixed module constant to an
injected severity-deduction mapping, with the current mapping as the default. Its
ordered check input remains injectable.

The check protocol gains a stable read-only `id` attribute. Each implementation uses
that same value in its returned finding, avoiding a second configuration-only ID
registry. IDs must be unique. The existing check registry remains the single ordered
source of available checks. Selection filters it by `check.id` without reordering it,
so enabled findings preserve Phase 0's deterministic order. Reporters require no
configuration knowledge.

The selected configuration source is excluded from the environment-usage content
candidate set. A policy comment mentioning `.env` must not make the scanned project
appear to use environment variables, and the policy loader remains the only component
that reads that file.

```text
CLI repository path and optional --config
                    |
                    v
       resolve one effective configuration
          |             |           |
          v             v           v
  filter checks    deductions   source exclusion
          |             |           |
          +-------------+-----------+
                        v
                 local scanner
                        |
                        v
              compatible Report shape
                        |
           +------------+------------+
           v            v            v
        terminal       JSON       Markdown
```

Programmatic callers that do not provide configured checks or deductions continue
to receive the current defaults.

## Scoring and Report Semantics

The score still starts at 100 and subtracts the configured global deduction for
each failed enabled finding. It never falls below zero. `max_score` remains 100,
and the score-summary bands remain unchanged.

A disabled check does not run, does not appear in `findings`, and deducts no points.
This treats disabled checks as outside the repository's policy rather than as
automatic passes. Terminal pass counts and Markdown/JSON finding lists therefore
reflect only enabled checks.

The `Finding` and `Report` fields, field order, types, and serialization rules do not
change. The meaning of `findings` deliberately evolves from “all seven built-in
checks” to “all enabled checks in registry order.” The package and `Report.version`
advance from `0.1.0` to `0.2.0` to signal this Phase 1 semantic change.

Configuration metadata is not embedded in the report in this phase. The emitted
`score` is authoritative, but JSON alone cannot reproduce a custom-weight score;
consumers that require an audit trail must preserve the policy file with the report.
Embedding an effective policy is deferred because it would change the stable report
schema. This tradeoff is documented explicitly rather than claiming that Phase 1
JSON is self-contained.

## Filesystem and Secret Safety

Configuration loading must never become a way to read a protected file. Before any
open or content read, both automatic and explicit candidates are checked using the
project's protected-path policy. Config candidates with a symbolic-link component,
non-regular file type, or protected basename/suffix are rejected. Broken final or
parent symlinks are errors rather than absent files. An automatic
`.repo-doctor.toml` that exists but is unsafe is an error instead of silently falling
back to defaults.

Loading opens the candidate as a file descriptor, using no-follow behavior where the
platform supports it, and verifies the opened descriptor is a regular file. A quick
metadata size rejection is followed by a bounded read of at most 1 MiB plus one byte.
Exactly 1 MiB is accepted; observing the extra byte is rejected. This preserves the
limit even if a file grows between metadata inspection and reading. The bounded bytes
must decode as UTF-8 before `tomllib` parses them.

Pydantic models hide input values in their error rendering. CLI error translation
uses sanitized error details with input and documentation URLs excluded; it never
prints `str(ValidationError)` or raw TOML. Parse and validation errors identify the
path and actionable field or location without echoing configuration values. A test
uses a unique sentinel invalid value and proves it appears in neither standard output
nor standard error.

The scanner remains local-only and read-only. The committed configuration contains
policy values only and no environment values. The existing `.env` and credential
protections remain unchanged. Tests install a read spy and prove that an explicit
protected config path is rejected before it is opened.

An explicitly requested report output still may replace ordinary regular files, but
it may not target the effective configuration source or the reserved
`<repository-root>/.repo-doctor.toml` path, even when that root file does not yet
exist. Such a collision exits 2 before the report path is created or written,
preventing a scan from destroying its governing policy or creating a JSON/Markdown
file that breaks automatic discovery on the next scan.

## Error Handling and CLI Contract

The extended command is:

```text
repo-doctor scan PATH [--config FILE] [--format terminal|json|markdown]
                      [--output FILE] [--fail-under 0..100]
```

Expected configuration failures include duplicate options, a missing explicit file,
inaccessible path, unsafe path, oversized file, invalid UTF-8, invalid TOML,
unsupported version, unknown keys or check IDs, invalid value types or ranges,
non-monotonic severity deductions, and disabling every check. They produce a concise
`Error: ...` message on standard error and exit 2 without a traceback or partial
report.

Configuration does not change output routing. Machine-readable JSON on standard
output remains free of status text. `--fail-under` is evaluated against the configured
score after the report has been rendered or written, preserving the existing exit-1
contract for a valid scan below its threshold.

## Testing Strategy

Unit tests will cover:

- default settings and partial-file default inheritance;
- the complete canonical file;
- all seven exact check IDs, ID uniqueness, agreement between `check.id` and returned
  finding IDs, and stable registry filtering order;
- custom severity deductions and score clamping;
- disabling one or multiple checks and rejecting all checks disabled;
- unsupported versions, unknown keys, unknown IDs, invalid types and ranges,
  nonzero `info`, non-monotonic weights, and sanitized error text;
- missing, non-regular, final-symlinked, parent-symlinked, oversized, malformed, and
  invalid-UTF-8 files, including exact 1 MiB and 1 MiB-plus-one boundaries;
- rejection of protected config paths before any read;
- exclusion of the effective policy file from environment-usage detection;
- rejection of report-output collisions with the effective policy and with an absent
  repository-root policy path;
- CLI auto-discovery, explicit override precedence, duplicate-option rejection, error
  exit codes, JSON purity, and configured `--fail-under` behavior;
- proof that a valid explicit file prevents any access to an invalid automatic file.

End-to-end tests will scan fixture repositories with no configuration to prove Phase 0
scores are unchanged, then scan a temporary configured fixture to prove automatic
discovery changes enabled findings and scoring. The committed project configuration
will also be exercised by the development scan.

Validation before implementation commits and final handoff includes:

```text
make test
make test-e2e
make lint
make typecheck
make build
uv run repo-doctor scan .
uv run repo-doctor scan tests/fixtures/good_repo --format json
uv run repo-doctor scan tests/fixtures/bad_repo --fail-under 80
```

The expected failing-threshold command must exit 1; all other validation commands
must succeed. JSON output is parsed in a test rather than accepted by visual
inspection alone.

## Documentation and Repository Policy

The root README will gain configuration discovery, schema, examples, precedence,
and error behavior. `docs/SCORING.md` will explain configurable severity deductions
and disabled-check semantics. `docs/DECISIONS.md` will record the versioned TOML,
single-source precedence, compatibility tradeoff, and stable-report choice.
`docs/FAILURES.md` will record only failures actually encountered during
implementation or validation.

The committed root `.repo-doctor.toml` will contain the canonical default values,
keeping this repository's current score and findings unchanged while serving as a
working example. `AGENTS.md` will be updated to require configuration compatibility
tests and documentation updates when the schema changes.

## Delivery Milestones

1. Add stable check identities, strict configuration models, safe TOML loading, and
   focused unit tests.
2. Integrate configured check selection, source exclusion, and severity deductions
   into scanner scoring.
3. Add CLI discovery and `--config` override behavior with CLI and safety tests.
4. Add fixture-based end-to-end coverage and the root `.repo-doctor.toml`.
5. Update package version, user, scoring, decision, failure, and contributor
   documentation.
6. Run the full acceptance suite, inspect the final tree and commits, and leave a
   clean worktree.

Each completed milestone uses a conventional commit. No remote is pushed.
