from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


WORKFLOW_VERSION = "1.1.0"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(text: str, fallback: str = "paper") -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return value or fallback


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def project_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def state_path(project_dir: Path) -> Path:
    return project_dir / "state.json"


def read_state(project_dir: Path) -> dict[str, Any]:
    state = read_json(state_path(project_dir), default=None)
    if state is None:
        raise FileNotFoundError(f"Missing state.json in {project_dir}")
    return state


def write_state(project_dir: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now_iso()
    write_json(state_path(project_dir), state)


def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            ensure_dir(target)
        else:
            ensure_dir(target.parent)
            shutil.copy2(item, target)


def latest_matching(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime if p.exists() else 0)
    return matches[-1] if matches else None


def append_history(state: dict[str, Any], key: str, item: dict[str, Any]) -> None:
    state.setdefault(key, [])
    state[key].append({"at": now_iso(), **item})


def plain_text_from_tex(path: Path) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"%.*", "", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})?", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def count_bib_entries(path: Path) -> int:
    if not path.exists():
        return 0
    return len(re.findall(r"@\w+\s*\{", path.read_text(encoding="utf-8", errors="ignore")))


def load_latest_review(project_dir: Path) -> tuple[Path | None, dict[str, Any] | None]:
    path = latest_matching(project_dir / "reviews", "review_round_*.json")
    if path is None:
        return None, None
    return path, read_json(path, default={})
