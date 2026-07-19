import re
from pathlib import Path

from repo_doctor.models import Finding, Severity

README_PRIORITY = ("readme.md", "readme.rst", "readme")
RECOGNIZED_SECTIONS = {
    "installation": ("installation",),
    "usage": ("usage",),
    "quickstart": ("quickstart", "quick start"),
    "setup": ("setup",),
    "testing": ("testing",),
    "development": ("development",),
    "contributing": ("contributing",),
    "license": ("license", "licence"),
}
ATX_HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.+?)\s*#*\s*$")
MARKDOWN_UNDERLINE_RE = re.compile(r"^\s*([=\-])\1{2,}\s*$")
RST_UNDERLINE_RE = re.compile(r"^\s*([=\-~^\"'`:+*#<>_])\1{2,}\s*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def find_readme(repo_path: Path) -> Path | None:
    entries = sorted(
        (entry for entry in repo_path.iterdir() if not entry.is_symlink() and entry.is_file()),
        key=lambda entry: entry.name,
    )
    for candidate_name in README_PRIORITY:
        matches = [entry for entry in entries if entry.name.casefold() == candidate_name]
        if matches:
            return matches[0]
    return None


def _is_indented_code(line: str) -> bool:
    indentation = line[: len(line) - len(line.lstrip(" \t"))]
    return "\t" in indentation or len(indentation) >= 4


def _markdown_fenced_lines(lines: list[str]) -> set[int]:
    fenced_lines: set[int] = set()
    opening_marker: str | None = None
    for index, line in enumerate(lines):
        fence_match = FENCE_RE.match(line)
        if opening_marker is None:
            if fence_match:
                opening_marker = fence_match.group(1)
                fenced_lines.add(index)
            continue

        fenced_lines.add(index)
        if fence_match:
            marker = fence_match.group(1)
            if (
                marker[0] == opening_marker[0]
                and len(marker) >= len(opening_marker)
                and not line[fence_match.end() :].strip()
            ):
                opening_marker = None
    return fenced_lines


def _extract_headings(text: str, *, is_rst: bool = False) -> list[str]:
    headings: list[str] = []
    lines = text.splitlines()
    fenced_lines = set() if is_rst else _markdown_fenced_lines(lines)
    underline_re = RST_UNDERLINE_RE if is_rst else MARKDOWN_UNDERLINE_RE
    for index, line in enumerate(lines):
        if index in fenced_lines or _is_indented_code(line):
            continue
        atx_match = ATX_HEADING_RE.fullmatch(line)
        if atx_match:
            headings.append(atx_match.group(1))
        if index + 1 < len(lines):
            next_line = lines[index + 1]
            if (
                line.strip()
                and index + 1 not in fenced_lines
                and not _is_indented_code(next_line)
                and underline_re.fullmatch(next_line)
            ):
                headings.append(line.strip())
    return headings


def _recognized_section_count(headings: list[str]) -> int:
    recognized: set[str] = set()
    for heading in headings:
        normalized = re.sub(r"[^a-z0-9]+", " ", heading.casefold()).strip()
        for section, aliases in RECOGNIZED_SECTIONS.items():
            if any(
                re.search(
                    rf"(?:^|\s){re.escape(alias)}(?:$|\s)",
                    normalized,
                )
                for alias in aliases
            ):
                recognized.add(section)
    return len(recognized)


class ReadmeExistsCheck:
    @property
    def id(self) -> str:
        return "readme-exists"

    def run(
        self,
        repo_path: Path,
        *,
        excluded_paths: frozenset[Path] = frozenset(),
    ) -> Finding:
        passed = find_readme(repo_path) is not None
        return Finding(
            id=self.id,
            title="README exists",
            description=(
                "A supported root README file is present."
                if passed
                else "No supported root README file was found."
            ),
            severity=Severity.HIGH,
            category="Documentation",
            recommendation=(
                "Keep the README aligned with the project."
                if passed
                else "Add README.md with the project's purpose and setup guidance."
            ),
            passed=passed,
        )


class ReadmeSectionsCheck:
    @property
    def id(self) -> str:
        return "readme-sections"

    def run(
        self,
        repo_path: Path,
        *,
        excluded_paths: frozenset[Path] = frozenset(),
    ) -> Finding:
        readme = find_readme(repo_path)
        section_count = 0
        if readme is not None:
            try:
                text = readme.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                text = ""
            headings = _extract_headings(
                text,
                is_rst=readme.suffix.casefold() == ".rst",
            )
            section_count = _recognized_section_count(headings)
        passed = section_count >= 2
        return Finding(
            id=self.id,
            title="README has useful sections",
            description=(
                f"The README contains {section_count} recognized sections."
                if readme is not None
                else "README usefulness cannot pass without a README."
            ),
            severity=Severity.MEDIUM,
            category="Documentation",
            recommendation=(
                "Keep installation and usage guidance current."
                if passed
                else "Add at least two sections such as Installation, Usage, or Testing."
            ),
            passed=passed,
        )
