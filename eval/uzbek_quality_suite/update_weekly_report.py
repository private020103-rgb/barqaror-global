#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="eval/uzbek_quality_suite/results/latest_results.json")
    parser.add_argument("--report", default="eval/weekly_report.md")
    args = parser.parse_args()

    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"## Uzbek Quality Suite — {timestamp}",
        "",
        "| Subset | Metric | Score | Threshold | Status |",
        "|---|---|---:|---:|---|",
    ]

    for subset, row in results.items():
        status = "PASS ✅" if row["passed"] else "FAIL ❌"
        lines.append(
            f"| {subset} | {row['metric']} | {row['score']:.4f} | {row['minimum_threshold']:.2f} | {status} |"
        )

    lines.append("\n")
    new_block = "\n".join(lines)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        old = report_path.read_text(encoding="utf-8").strip()
        updated = old + "\n\n" + new_block
    else:
        updated = "# Weekly Quality Report\n\n" + new_block

    report_path.write_text(updated + "\n", encoding="utf-8")
    print(f"Updated {report_path}")


if __name__ == "__main__":
    main()
