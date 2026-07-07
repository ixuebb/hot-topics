from __future__ import annotations

import argparse
import re
from pathlib import Path

from workflow_common import read_jsonl, write_json


ENTRY_RE = re.compile(r"@(?P<type>\w+)\s*\{\s*(?P<key>[^,]+),(?P<body>.*?)\n\}", re.DOTALL)
FIELD_RE = re.compile(r"(?P<name>\w+)\s*=\s*\{(?P<value>.*?)\}\s*,?", re.DOTALL)


def parse_bib(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    entries = []
    for match in ENTRY_RE.finditer(text):
        fields = {m.group("name").lower(): " ".join(m.group("value").split()) for m in FIELD_RE.finditer(match.group("body"))}
        entries.append({"type": match.group("type"), "key": match.group("key").strip(), "fields": fields})
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify basic BibTeX integrity against the citation plan.")
    parser.add_argument("project_dir")
    parser.add_argument("--min-verification-rate", type=float, default=0.80)
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    entries = parse_bib(project_dir / "refs" / "references.bib")
    plan = read_jsonl(project_dir / "refs" / "citation_plan.jsonl")
    plan_keys = {row.get("bib_key") for row in plan if row.get("bib_key")}
    entry_keys = [entry["key"] for entry in entries]
    duplicate_keys = sorted({key for key in entry_keys if entry_keys.count(key) > 1})

    missing_required = []
    for entry in entries:
        fields = entry["fields"]
        missing = [name for name in ["title", "author", "year"] if not fields.get(name)]
        if missing:
            missing_required.append({"key": entry["key"], "missing": missing})

    missing_from_bib = sorted(plan_keys - set(entry_keys))
    unplanned_entries = sorted(set(entry_keys) - plan_keys)
    verified = len(entries) - len(missing_required) - len(duplicate_keys)
    verification_rate = verified / max(1, len(entries))
    report = {
        "entry_count": len(entries),
        "planned_count": len(plan_keys),
        "verification_rate": round(verification_rate, 3),
        "passed": verification_rate >= args.min_verification_rate and not duplicate_keys and not missing_from_bib,
        "duplicate_keys": duplicate_keys,
        "missing_required_fields": missing_required,
        "missing_from_bib": missing_from_bib,
        "unplanned_entries": unplanned_entries,
    }
    write_json(project_dir / "refs" / "verification_report.json", report)
    print(f"Verification rate: {report['verification_rate']}")
    print(f"Passed: {report['passed']}")
    if duplicate_keys:
        print(f"Duplicate keys: {duplicate_keys}")
    if missing_from_bib:
        print(f"Missing planned keys from BibTeX: {len(missing_from_bib)}")


if __name__ == "__main__":
    main()

