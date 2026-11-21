"""Inspect raw CSV structure without cleaning or calculating analytical results."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


def inspect_csv(path, raw_dir):
    # Read records directly so malformed headers cannot silently shift columns.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        records = list(reader)
    data = [row for row in records if row]
    widths = Counter(map(len, data))
    schema_matches = set(widths) == {len(header)}
    dimensions = {}
    if schema_matches:
        for i, name in enumerate(header):
            key = name.strip().lower()
            if (key in {"year", "timeperiod", "area_name"}
                    or ("state" in key and key != "is_state")):
                dimensions[name] = sorted({row[i] for row in data})
    return {
        "file": path.relative_to(raw_dir).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(data),
        "blank_records": len(records) - len(data),
        "header_columns": len(header),
        "record_widths": dict(sorted(widths.items())),
        "schema_matches": schema_matches,
        "columns": header,
        "coverage": dimensions,
        "coverage_note": "Read using declared header." if schema_matches else
            "Coverage not inferred: header width differs from record width.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.root.resolve()
    raw_dir = root / "data/raw"
    files = sorted(p for p in raw_dir.rglob("*") if p.suffix.lower() == ".csv")
    if not files:
        raise SystemExit("No raw CSV files found. Download rajanand/prison-in-india first.")
    inventory = [inspect_csv(path, raw_dir) for path in files]
    output_dir = root / "results/tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "dataset_inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    columns = ["file", "bytes", "rows", "blank_records", "header_columns",
               "record_widths", "schema_matches", "sha256"]
    with (output_dir / "dataset_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(inventory)
    print(f"Audited {len(files)} CSV files; {sum(x['rows'] for x in inventory):,} nonblank records.")
    print(f"Total size: {sum(x['bytes'] for x in inventory):,} bytes.")
    print("Schema mismatches:", [x["file"] for x in inventory if not x["schema_matches"]])


if __name__ == "__main__":
    main()
