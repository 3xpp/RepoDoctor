import os
import stat
from enum import StrEnum
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from repo_doctor.checks.filesystem import is_protected_path
from repo_doctor.config import (
    CONFIG_FILENAME,
    ConfigError,
    resolve_configuration,
    select_checks,
    severity_deductions,
)
from repo_doctor.path_safety import has_symlink_component, normalize_local_path
from repo_doctor.reporting.json_report import render_json
from repo_doctor.reporting.markdown import render_markdown
from repo_doctor.reporting.terminal import render_terminal
from repo_doctor.scanner import (
    RepositoryScanError,
    resolve_repository_path,
    scan_repository,
)

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


def _is_protected_output(path: Path) -> bool:
    return is_protected_path(path)


def _same_existing_file(first: Path, second: Path) -> bool:
    if first == second:
        return True
    try:
        return os.path.samefile(first, second)
    except (FileNotFoundError, OSError):
        return False


def _validate_output_path(
    path: Path,
    *,
    reserved_root_policy: Path,
    active_policy: Path | None,
) -> None:
    if _is_protected_output(path):
        raise ValueError("refusing to write a report to a protected secret path")
    if path == reserved_root_policy:
        raise ValueError("refusing to overwrite the repository configuration path")
    if active_policy is not None and path == active_policy:
        raise ValueError("refusing to overwrite the active configuration file")
    if has_symlink_component(path):
        raise ValueError("refusing to write a report through a symbolic link")
    if active_policy is not None and _same_existing_file(path, active_policy):
        raise ValueError("refusing to overwrite the active configuration file")

    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if not stat.S_ISREG(mode):
        raise ValueError("refusing to replace a non-regular output target")


def _write_report(
    path: Path,
    content: str,
    *,
    reserved_root_policy: Path,
    active_policy: Path | None,
) -> None:
    _validate_output_path(
        path,
        reserved_root_policy=reserved_root_policy,
        active_policy=active_policy,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    _validate_output_path(
        path,
        reserved_root_policy=reserved_root_policy,
        active_policy=active_policy,
    )
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
    config: Annotated[
        list[Path] | None,
        typer.Option(
            "--config",
            help="Use this TOML policy instead of repository-root discovery.",
        ),
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

    try:
        resolved_repo = resolve_repository_path(path)
        loaded = resolve_configuration(
            resolved_repo,
            explicit_paths=tuple(config or ()),
        )
    except (ConfigError, RepositoryScanError) as error:
        _exit_error(str(error))

    reserved_root_policy = resolved_repo / CONFIG_FILENAME
    if output is not None:
        output = normalize_local_path(output)
        try:
            _validate_output_path(
                output,
                reserved_root_policy=reserved_root_policy,
                active_policy=loaded.source_path,
            )
        except (OSError, ValueError) as error:
            _exit_error(str(error))

    selected_checks = select_checks(loaded.settings)
    exclusions = {reserved_root_policy}
    if loaded.source_path is not None:
        exclusions.add(loaded.source_path)
    try:
        report = scan_repository(
            resolved_repo,
            checks=selected_checks,
            deductions=severity_deductions(loaded.settings),
            excluded_paths=exclusions,
        )
    except RepositoryScanError as error:
        _exit_error(str(error))

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
                _write_report(
                    output,
                    content,
                    reserved_root_policy=reserved_root_policy,
                    active_policy=loaded.source_path,
                )
            except (OSError, ValueError) as error:
                _exit_error(f"could not write report: {error}")

    if fail_under is not None and report.score < fail_under:
        typer.echo(
            f"Score {report.score} is below required threshold {fail_under}.",
            err=True,
        )
        raise typer.Exit(code=1)
