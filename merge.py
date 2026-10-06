"""Three-way merging of prompt text into local files."""

from pathlib import Path
import re

from merge3 import Merge3

from client import PlatformError


def merge_text(base: str, left: str, right: str, labels: tuple[str, str, str]) -> tuple[str, bool]:
    merger = Merge3(base.splitlines(keepends=True), left.splitlines(keepends=True), right.splitlines(keepends=True))
    chunks = []
    conflict = False
    for group in merger.merge_groups():
        if group[0] != "conflict":
            chunks.append("".join(group[1]))
            continue
        conflict = True
        if chunks and not chunks[-1].endswith(("\n", "\r")):
            chunks.append("\n")
        _, original, a, b = group
        sections = [("<<<<<<< " + labels[1], a)]
        if labels[0]:
            sections.append(("||||||| " + labels[0], original))
        sections.append(("=======", b))
        for marker, content in sections:
            chunks.append(marker + "\n")
            text = "".join(content)
            chunks.append(text)
            if text and not text.endswith(("\n", "\r")):
                chunks.append("\n")
        chunks.append(">>>>>>> " + labels[2] + "\n")
    return "".join(chunks), conflict


def prompt_filename(name: str) -> str:
    # Keep all output directly under merge/, including owner/name references.
    safe = re.sub(r"[^\w.-]+", "_", name, flags=re.UNICODE).strip(".")
    if not safe:
        raise PlatformError("Prompt name cannot be used as a filename.")
    return safe + ".txt"


def write_merges(base: dict[str, str], left: dict[str, str], right: dict[str, str],
                 names: dict[str, str], labels: tuple[str, str, str],
                 output: Path = Path("merge")) -> bool:
    planned = []
    used = set()
    for key in sorted(base.keys() | left.keys() | right.keys()):
        if key not in left and key not in right:
            continue
        a, b, original = left.get(key, ""), right.get(key, ""), base.get(key, "")
        # A deletion on one side and an unchanged other side stays deleted.
        if key in base and ((key not in left and b == original) or (key not in right and a == original)):
            continue
        filename = prompt_filename(names[key])
        if filename.casefold() in used:
            raise PlatformError(f"Multiple prompts map to {filename}; cannot write an unambiguous merge.")
        used.add(filename.casefold())
        path = output / filename
        if path.exists() or path.is_symlink():
            raise PlatformError(f"Output already exists: {path}. Move it aside before merging again.")
        text, conflict = merge_text(original, a, b, labels)
        planned.append((path, text, conflict))
    if not planned:
        print("No merged prompt files to write.")
        return False
    if output.is_symlink():
        raise PlatformError("The merge output directory must not be a symlink.")
    try:
        output.mkdir(parents=True, exist_ok=True)
        for path, text, conflict in planned:
            with path.open("x", encoding="utf-8", newline="") as handle:
                handle.write(text)
            print(f"{path}: {'CONFLICT — edit the marked sections' if conflict else 'merged'}")
    except OSError as exc:
        raise PlatformError(f"Could not write merge output ({type(exc).__name__}).") from exc
    return any(conflict for _, _, conflict in planned)


def workflow_prompt_names(*workflows: dict) -> dict[str, str]:
    names = {}
    for workflow in workflows:
        for node in workflow.get("nodes", []):
            identifier = (node.get("args") or {}).get("prompt_id")
            names[node["id"]] = identifier.split(":", 1)[0] if isinstance(identifier, str) and identifier else node["id"]
    return names
