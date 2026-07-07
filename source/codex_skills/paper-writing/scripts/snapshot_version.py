from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from workflow_common import ensure_dir, read_state, write_json, write_state


DEFAULT_PATTERNS = [
    "topic.yaml",
    "state.json",
    "iteration_brief.md",
    "main.tex",
    "gate_report.json",
    "refs/*.bib",
    "refs/*.json",
    "refs/*.jsonl",
    "sections/*.tex",
    "tables/*.tex",
    "figures/*.pdf",
    "figures/*.png",
    "experiments/*.md",
    "experiments/*.json",
    "reviews/*.json",
    "build/*.pdf",
    "build/compile_report.json",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Snapshot a paper project version.")
    parser.add_argument("project_dir")
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    state = read_state(project_dir)
    version = int(state.get("current_version", 0)) + 1
    version_name = f"v{version:03d}"
    snapshot_dir = ensure_dir(project_dir / "snapshots" / version_name)

    copied = []
    for pattern in DEFAULT_PATTERNS:
        for src in project_dir.glob(pattern):
            if src.is_file():
                rel = src.relative_to(project_dir)
                dst = snapshot_dir / rel
                ensure_dir(dst.parent)
                shutil.copy2(src, dst)
                copied.append(str(rel))

    manifest = {
        "version": version,
        "label": args.label,
        "copied_files": copied,
        "iteration": state.get("iteration"),
        "phase": state.get("phase"),
    }
    write_json(snapshot_dir / "manifest.json", manifest)
    state["current_version"] = version
    state["latest_snapshot"] = str(snapshot_dir)
    write_state(project_dir, state)
    print(f"Snapshot {version_name}: {snapshot_dir}")


if __name__ == "__main__":
    main()

