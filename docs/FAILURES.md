# Failures

This log records concrete implementation or environment failures and their resolution.

## 2026-07-18 — Workspace sandbox loopback setup

- **Symptom:** Safe filesystem, Git, uv, and test commands intermittently failed
  before execution with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`.
- **Impact:** No project file or repository data was damaged.
- **Resolution:** Retried the exact safe commands with approved sandbox escalation;
  application behavior and dependency choices were unchanged.
- **Status:** Resolved for the affected commands; the environment fault can recur.

## 2026-07-18 — Escalation review deadline

- **Symptom:** Two large documentation-only patch commands were rejected because
  automatic permission review did not finish before its deadline.
- **Impact:** The commands never executed and no project file was damaged.
- **Resolution:** Split the same reviewed changes into smaller `apply_patch` calls.
- **Status:** Resolved; each smaller patch completed successfully.

## 2026-07-18 — Existing-file patch helper failure

- **Symptom:** In-place `apply_patch` updates of existing files failed in the
  workspace filesystem helper, including approved retries, before applying a diff.
- **Impact:** The existing files remained unchanged; no project content was lost.
- **Resolution:** Moved only the affected non-secret files to unique `/tmp` backup
  paths after verifying matching byte sizes, then recreated the reviewed files with
  `apply_patch` Add File operations. Backups were kept through validation.
- **Status:** Resolved with a recoverable workflow; temporary backups were removed
  after acceptance passed.

## 2026-07-18 — uv build emitted a PEP 639 classifier warning

- **Symptom:** `uv build` warned that the legacy
  `License :: OSI Approved :: MIT License` classifier is deprecated when modern
  license metadata is present.
- **Impact:** Distribution artifacts still built, but acceptance output was noisy.
- **Resolution:** Removed only the deprecated classifier. The PEP 639-compatible
  `license = "MIT"` metadata and tracked `LICENSE` file remain authoritative.
- **Status:** Resolved; the final build is warning-clean.

## 2026-07-18 — README comparison command was shell-expanded

- **Symptom:** The first in-memory README comparison embedded Markdown fence
  backticks in a double-quoted shell argument, so the shell attempted command
  substitution and the diagnostic exited 1 before comparing output. A later
  inline JSON parser check had the same shell-quoting class of typo.
- **Impact:** No project or report file was written or changed.
- **Resolution:** Replaced the literal fence with shell-safe character construction,
  passed the JSON path as a positional argument, and reran both diagnostics; the
  README example matched line-for-line modulo the path and JSON parsed successfully.
- **Status:** Resolved; the corrected comparison and parser check exited 0.

## 2026-07-18 — Captured terminal output wrapped at console width

- **Symptom:** Rich inserted width-dependent newlines into logical repository and
  recommendation lines when output was captured through a narrow non-TTY console.
- **Impact:** Human-readable content was correct, but captured output could differ
  from the stable README example and become harder to process line by line.
- **Resolution:** Enabled `soft_wrap=True` on every non-blank terminal report line
  and added a narrow-console regression for repository and recommendation lines.
- **Status:** Resolved; direct captured bad-fixture output matches the README example
  modulo the absolute repository path.

## 2026-07-18 — Distribution archives did not declare the license file

- **Symptom:** Project metadata named the MIT license but did not explicitly declare
  `LICENSE` for inclusion in built source and wheel archives.
- **Impact:** Archive consumers could not rely on the project configuration alone to
  guarantee that the full license text was shipped with both distribution formats.
- **Resolution:** Added `license-files = ["LICENSE"]` to project metadata, rebuilt,
  and verified the license file in both the sdist and wheel manifests.
- **Status:** Resolved; both release archives contain the tracked license text.
