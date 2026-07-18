import os
import stat
from enum import StrEnum
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from repo_doctor.checks.filesystem import is_protected_path
from repo_doctor.reporting.json_report import render_json
from repo_doctor.reporting.markdown import render_markdown
from repo_doctor.reporting.terminal import render_terminal
from repo_doctor.scanner import RepositoryScanError, scan_repository

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Evaluate the practical readiness of a local repository.",
)


class OutputFormat(StrEnum):
    TERMINAL = "terminal"
    JSON = "json"
    MARKDOWN = "markdown"


@app.callback()
def main() -> None:
    """Scan local repositories without changing their contents."""


def _exit_error(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=2)


def _normalize_output_path(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _is_protected_output(path: Path) -> bool:
    return is_protected_path(path)


def _has_symlink_component(path: Path) -> bool:
    candidate = Path(path.anchor)
    for part in path.parts[1:]:
        candidate /= part
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            return True
    return False


def _validate_output_path(path: Path) -> None:
    if _is_protected_output(path):
        raise ValueError("refusing to write a report to a protected secret path")
    if _has_symlink_component(path):
        raise ValueError("refusing to write a report through a symbolic link")

    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if not stat.S_ISREG(mode):
        raise ValueError("refusing to replace a non-regular output target")


def _write_report(path: Path, content: str) -> None:
    _validate_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _validate_output_path(path)
    path.write_text(content, encoding="utf-8")


@app.command()
def scan(
    path: Annotated[
        Path,
        typer.Argument(help="Local repository directory to scan."),
    ] = Path("."),
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            case_sensitive=False,
            help="Report format: terminal, json, or markdown.",
        ),
    ] = OutputFormat.TERMINAL,
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Write JSON or Markdown to this file."),
    ] = None,
    fail_under: Annotated[
        int | None,
        typer.Option(
            "--fail-under", min=0, max=100, help="Exit 1 when the score is below this threshold."
        ),
    ] = None,
) -> None:
    if output is not None and output_format is OutputFormat.TERMINAL:
        _exit_error("--output requires JSON or Markdown format")
    if output is not None:
        output = _normalize_output_path(output)
        try:
            _validate_output_path(output)
        except (OSError, ValueError) as exc:
            _exit_error(str(exc))

    try:
        report = scan_repository(path)
    except RepositoryScanError as exc:
        _exit_error(str(exc))

    if output_format is OutputFormat.TERMINAL:
        render_terminal(report)
    else:
        content = (
            render_json(report) if output_format is OutputFormat.JSON else render_markdown(report)
        )
        if output is None:
            typer.echo(content, nl=False)
        else:
            try:
                _write_report(output, content)
            except (OSError, ValueError) as exc:
                _exit_error(f"could not write report: {exc}")

    if fail_under is not None and report.score < fail_under:
        typer.echo(
            f"Score {report.score} is below required threshold {fail_under}.",
            err=True,
        )
        raise typer.Exit(code=1)
