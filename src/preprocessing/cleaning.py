"""Clean the downloaded tables and save reproducible data-quality evidence."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .schema import (CANONICAL_STATES, FREE_TEXT, MISSING_TOKENS, STATE_COLUMNS,
                     UNION_TERRITORIES, category_value, column_roles, row_scope, token)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_raw(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        records = [(i, row) for i, row in enumerate(reader, start=2)]
    blank = sum(not row or all(not v.strip() for v in row) for _, row in records)
    records = [(i, row) for i, row in records if row and any(v.strip() for v in row)]
    original_width = len(header)
    repaired = False
    if path.name == "Religion.csv" and original_width == 8:
        # Validate the missing header using every record, not pandas' inferred index.
        expected = ["state_name", "is_state", "year", "gender", "convicts",
                    "under_trial", "detenues", "others"]
        if header != expected or not all(
            len(row) == 9 and row[3] in {"Male", "Female"}
            and row[4] in {"Christian", "Hindu", "Muslim", "Others", "Sikh"}
            and all(v.isdigit() for v in row[5:]) for _, row in records
        ):
            raise ValueError("Religion schema does not match the validated repair.")
        header.insert(4, "religion")
        repaired = True
    if any(len(row) != len(header) for _, row in records):
        raise ValueError(f"Unexpected record width in {path.name}")
    frame = pd.DataFrame([row for _, row in records], columns=header, dtype="string")
    frame.index = pd.Index([i for i, _ in records], name="source_record")
    return frame, blank, original_width, repaired


def missing_mask(series):
    return series.astype("string").str.strip().str.casefold().isin(MISSING_TOKENS) | series.isna()


def equations(columns):
    """Return only totals that can be checked using fields in the same record."""
    names = {token(c): c for c in columns}
    result = []

    def add(total, components):
        if total in names and all(c in names for c in components):
            result.append((names[total], [names[c] for c in components]))

    for name in names:
        if name.startswith("male_"):
            suffix = name[5:]
            add("total_" + suffix, [name, "female_" + suffix])
    add("total", ["male", "female"])
    add("grand_total", ["total_male", "total_female"])
    for sex in ["male", "female", "total"]:
        add("total_" + sex, [f"{sex}_{status}" for status in
                             ["convicts", "under_trial", "detenues", "others"]])
        add("total_" + sex, [f"{sex}_{age}" for age in
                             ["16_18_years", "18_30_years", "30_50_years", "above_50_years"]])
    add("total_capacity_of_inmates", ["total_capacity_of_male_inmates", "total_capacity_of_female_inmates"])
    add("total_inmate_population", ["male_inmate_population", "female_inmate_population"])
    add("total_no_of_women_prisoners_with_children", [
        "no_of_convict_women_prisoners_with_children", "no_of_under_trial_women_prisoners_with_children",
        "no_of_detenues_women_prisoners_with_children", "no_of_other_women_prisoners_with_children"])
    add("total_no_of_children_of_women_prisoners", [
        "no_of_children_of_convict_women_prisoners", "no_of_children_of_under_trial_women_prisoners",
        "no_of_children_of_detenues_women_prisoners", "no_of_children_of_other_women_prisoners"])
    # The fiscal snapshot labels include column numbers; match their full prefixes.
    budget_parts = [k for k in names if k.startswith(("total_annual_budget_plan_", "total_annual_budget_non_plan_"))]
    budget_total = next((k for k in names if k.startswith("total_annual_budget_total_")), None)
    expenditure_parts = [k for k in names if k.startswith(("actual_expenditure_plan_", "actual_expenditure_non_plan_",
                         "actual_expenditure_expenditure_on_account_"))]
    expenditure_total = next((k for k in names if k.startswith("actual_expenditure_total_")), None)
    if budget_total and len(budget_parts) == 2:
        add(budget_total, budget_parts)
    if expenditure_total and len(expenditure_parts) == 3:
        add(expenditure_total, expenditure_parts)
    return result


def infer_missing(frame, formulas, events, filename):
    # Fill a count only when at least two independent equations agree exactly.
    candidates = {}
    for total, parts in formulas:
        fields = [total] + parts
        incomplete = frame[fields].isna().sum(axis=1).eq(1)
        for idx in frame.index[incomplete]:
            unknown = next(c for c in fields if pd.isna(frame.at[idx, c]))
            value = (sum(frame.at[idx, c] for c in parts) if unknown == total else
                     frame.at[idx, total] - sum(frame.at[idx, c] for c in parts if c != unknown))
            candidates.setdefault((idx, unknown), []).append((float(value), total))
    for (idx, column), values in candidates.items():
        numbers = [v for v, _ in values]
        if len(values) >= 2 and len(set(numbers)) == 1 and numbers[0] >= 0 and numbers[0].is_integer():
            frame.at[idx, column] = int(numbers[0])
            events.append({"file": filename, "source_record": idx, "column": column,
                           "action": "recover_from_agreeing_totals", "old_value": "",
                           "new_value": int(numbers[0]), "reason": "; ".join(t for _, t in values)})


def check_totals(frame, formulas, filename, stage):
    findings = []
    tolerance = 0.15 if Path(filename).name.startswith("Total_Budget_and_Actual_") else 1e-8
    for total, parts in formulas:
        complete = frame[[total] + parts].notna().all(axis=1)
        calculated = frame[parts].sum(axis=1, min_count=len(parts))
        for idx in frame.index[complete & ~np.isclose(
            frame[total].to_numpy(dtype=float, na_value=np.nan),
            calculated.to_numpy(dtype=float, na_value=np.nan), rtol=0, atol=tolerance, equal_nan=False
        )]:
            findings.append({"file": filename, "stage": stage, "source_record": idx,
                             "check": "within_record", "total_field": total,
                             "reported": frame.at[idx, total], "calculated": calculated.loc[idx],
                             "difference": frame.at[idx, total] - calculated.loc[idx]})
    return findings


def group_total_checks(frame, roles, filename):
    """Check selected mutually exclusive category partitions, never arbitrary groups."""
    specs = []
    basename = Path(filename).name
    if "Jail_Type" in frame or "TYPE OF JAIL" in frame:
        c = "Jail_Type" if "Jail_Type" in frame else "TYPE OF JAIL"
        specs.append((c, "Total", ["Central Jail", "District Jail", "Sub Jail", "Women Jail",
                                    "Borstal School", "Open Jail", "Special Jail", "Others"]))
    if "PERIOD OF DETENTION" in frame:
        specs.append(("PERIOD OF DETENTION", "Total", ["Upto 3 months", "3-6 months", "6-12 months",
                     "1-2 Years", "2-3 Years", "3-5 Years", "Above 5 Years"]))
    if basename == "Inmates_death.csv":
        parts = [v for v in frame["details"].unique() if v.startswith("Un-natural Deaths - ")]
        specs.append(("details", "Un-natural Deaths", parts))
    if basename == "Inmates_released.csv":
        for prefix, total in [("Convicts Released - ", "Total Convicts Released"),
                              ("Under trials Released - ", "Total Under trials Released"),
                              ("Detenus Released - ", "Total Detenus Released")]:
            specs.append(("details", total, [v for v in frame["details"].unique() if v.startswith(prefix)]))
    if basename in {"Budget.CSV", "Expenditure.CSV", "Expenditure_on_inmates.CSV", "Training_of_Jail_Officers.CSV"}:
        values = frame["Indicator_Name"].unique().tolist()
        totals = [v for v in values if v.lower().startswith("total")]
        if len(totals) == 1:
            specs.append(("Indicator_Name", totals[0], [v for v in values if v not in totals]))
    if basename.startswith("SLL_"):
        labels = frame["CRIME HEAD"].unique().tolist()
        components = [v for v in labels if not v.startswith(("TOTAL", "(C) CIVIL"))]
        for total_label in ["TOTAL", "TOTAL (B)"]:
            if total_label in labels:
                specs.append(("CRIME HEAD", total_label, components))
    findings, checks, incomplete = [], 0, 0
    for dimension, total_label, parts in specs:
        keys = [k for k in roles["keys"] if k != dimension]
        for _, group in frame.groupby(keys, dropna=False, sort=True):
            totals = group[group[dimension].eq(total_label)]
            # Different SLL years use TOTAL and TOTAL (B) for the same subtotal.
            if basename.startswith("SLL_") and len(totals) == 0:
                continue
            if len(totals) != 1:
                incomplete += 1
                continue
            details = group[group[dimension].isin(parts)]
            if set(details[dimension]) != set(parts) or len(details) != len(parts):
                incomplete += 1
                continue
            total = totals.iloc[0]
            for c in roles["measures"]:
                if pd.isna(total[c]) or details[c].isna().any():
                    incomplete += 1
                    continue
                checks += 1
                expected = details[c].sum()
                if not np.isclose(float(total[c]), float(expected), rtol=0, atol=1e-8):
                    findings.append({"file": filename, "stage": "after", "source_record": totals.index[0],
                                     "check": "category_partition", "total_field": c,
                                     "reported": total[c], "calculated": expected,
                                     "difference": total[c] - expected})
    return findings, checks, incomplete


def quality_profile(frame, roles, filename, stage):
    rows = []
    for c in frame:
        series = frame[c]
        missing = missing_mask(series)
        numeric = c in roles["numeric"]
        values = pd.to_numeric(series.mask(missing), errors="coerce") if numeric else None
        rows.append({"file": filename, "stage": stage, "column": c, "rows": len(frame),
                     "dtype": str(series.dtype), "missing": int(missing.sum()),
                     "invalid_numeric": int((values.isna() & ~missing).sum()) if numeric else 0,
                     "negative": int(values.lt(0).sum()) if numeric else 0,
                     "noninteger": int((values.dropna() % 1 != 0).sum()) if numeric else 0,
                     "requires_integer": numeric and c not in roles["continuous"]})
    return rows


def outlier_checks(frame, roles, filename):
    # Compare values within the same non-geographic categories across state-years.
    dimensions = [c for c in roles["keys"] if c not in STATE_COLUMNS
                  and c.lower() not in {"year", "timeperiod"}]
    if filename == "Prison_details_2015.csv":
        return [], []
    groups = frame.groupby(dimensions, dropna=False, sort=True) if dimensions else [((), frame)]
    bounds, flags = [], []
    for key, group in groups:
        context = json.dumps(dict(zip(dimensions, key if isinstance(key, tuple) else (key,))), ensure_ascii=False)
        for c in roles["measures"]:
            series = group[c].dropna().astype(float)
            if len(series) < 8:
                continue
            q1, q3 = series.quantile([0.25, 0.75])
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            flagged = series[(series < lower) | (series > upper)] if iqr > 0 else series.iloc[:0]
            bounds.append({"file": filename, "column": c, "context": context, "n": len(series),
                           "q1": q1, "q3": q3, "iqr": iqr, "lower": lower, "upper": upper,
                           "flagged": len(flagged), "status": "checked" if iqr > 0 else "zero_iqr_not_flagged"})
            for idx, value in flagged.items():
                flags.append({"file": filename, "source_record": idx, "column": c,
                              "value": value, "context": context, "lower": lower, "upper": upper})
    return bounds, flags


def run_cleaning(root):
    root = Path(root).resolve()
    raw = root / "data/raw"
    output = root / "data/processed/cleaned"
    quarantine_dir = root / "data/processed/quarantine"
    reports = root / "results/tables/cleaning"
    manifest = json.loads((root / "results/tables/dataset_inventory.json").read_text())
    raw_paths = sorted(p for p in raw.rglob("*") if p.suffix.lower() == ".csv")
    expected = {r["file"]: r["sha256"] for r in manifest}
    actual = {p.relative_to(raw).as_posix(): sha256(p) for p in raw_paths}
    if actual != expected:
        raise ValueError("Raw files differ from the Phase 0 manifest. Review the source before cleaning.")
    for directory in [output, quarantine_dir, reports]:
        directory.mkdir(parents=True, exist_ok=True)
    profiles, summaries, events, categories, totals = [], [], [], [], []
    outlier_bounds, outliers, row_flags, dictionaries, lineage, blank_records = [], [], [], [], [], []
    schema_repairs = []
    for path in raw_paths:
        filename = path.relative_to(raw).as_posix()
        frame, blank, original_width, repaired = read_raw(path)
        cols = list(frame.columns)
        roles = column_roles(path.name, cols)
        profiles.extend(quality_profile(frame, roles, filename, "before"))
        rows_before = len(frame)
        if repaired:
            schema_repairs.append({"file": filename, "declared_fields": original_width,
                                   "corrected_fields": len(cols), "action": "Insert religion after gender"})
        if blank:
            blank_records.append({"file": filename, "blank_records_removed": blank})
        for c in cols:
            old = frame[c].copy()
            frame[c] = old.str.strip().mask(missing_mask(old))
            if c in roles["text"] and c not in FREE_TEXT:
                frame[c] = frame[c].map(lambda v: category_value(c, v) if pd.notna(v) else pd.NA).astype("string")
            changes = old.ne(frame[c]).fillna(old.notna() & frame[c].isna())
            if changes.any():
                changed = pd.DataFrame({"old_value": old[changes], "new_value": frame.loc[changes, c]})
                for (a, b), n in changed.groupby(["old_value", "new_value"], dropna=False).size().items():
                    categories.append({"file": filename, "column": c, "old_value": a,
                                       "new_value": b, "count": int(n)})
        invalid_rows = set()
        for c in roles["numeric"]:
            original = frame[c].copy()
            values = pd.to_numeric(original, errors="coerce")
            invalid = original.notna() & values.isna()
            invalid |= values.lt(0) | (~np.isfinite(values.to_numpy(dtype=float, na_value=np.nan)) & values.notna())
            if c not in roles["continuous"]:
                invalid |= values.notna() & values.mod(1).ne(0)
            if c.lower() in {"year", "timeperiod"}:
                invalid |= values.notna() & ~values.between(2001, 2010 if c == "TimePeriod" else 2013)
            if c == "is_state":
                invalid |= values.notna() & ~values.isin([0, 1])
            for idx in frame.index[invalid]:
                invalid_rows.add(idx)
                events.append({"file": filename, "source_record": idx, "column": c,
                               "action": "invalid_to_missing", "old_value": original.loc[idx],
                               "new_value": "", "reason": "Non-numeric, non-finite, negative or invalid domain"})
            frame[c] = values.mask(invalid).astype("Float64" if c in roles["continuous"] else "Int64")
        for c in [x for x in roles["text"] if x in STATE_COLUMNS]:
            unknown = set(frame[c].dropna()) - set(CANONICAL_STATES)
            if unknown:
                raise ValueError(f"Unmapped geography in {filename}: {unknown}")
        if "is_state" in frame:
            state = next(c for c in roles["text"] if c in STATE_COLUMNS)
            expected_flag = ~frame[state].isin(UNION_TERRITORIES)
            for idx in frame.index[frame["is_state"].notna() & frame["is_state"].ne(expected_flag.astype(int))]:
                events.append({"file": filename, "source_record": idx, "column": "is_state",
                               "action": "state_flag_conflict_retained", "old_value": frame.at[idx, "is_state"],
                               "new_value": frame.at[idx, "is_state"], "reason": "Historical jurisdiction flag requires review"})
        formulas = equations(cols)
        before_totals = check_totals(frame, formulas, filename, "before")
        totals.extend(before_totals)
        infer_missing(frame, formulas, events, filename)

        # Training and goods files lack the identifier needed to prove duplicate events.
        ambiguous_grain = path.name in {"Vocational_training.csv", "Value_of_goods_produced_by_inmates.csv"}
        duplicate_mask = frame.duplicated(cols, keep="first")
        duplicate_candidates = int(duplicate_mask.sum())
        removed = []
        if not ambiguous_grain:
            for idx in frame.index[duplicate_mask]:
                matching = frame.loc[:idx].drop(index=idx)
                match = matching.eq(frame.loc[idx]).fillna(matching.isna() & frame.loc[idx].isna()).all(axis=1)
                lineage.append({"file": filename, "source_record": idx, "disposition": "duplicate_removed",
                                "retained_record": matching.index[match][0]})
            removed = frame.index[duplicate_mask].tolist()
            frame = frame.loc[~duplicate_mask].copy()
        conflict = frame.duplicated(roles["keys"], keep=False)
        missing_key = frame[roles["keys"]].isna().any(axis=1)
        quarantine_mask = missing_key | (conflict & (not ambiguous_grain))
        quarantine = frame.loc[quarantine_mask].copy()
        for idx in quarantine.index:
            lineage.append({"file": filename, "source_record": idx, "disposition": "quarantined_key_conflict"
                            if conflict.loc[idx] else "quarantined_missing_key", "retained_record": ""})
        if len(quarantine):
            target = quarantine_dir / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            quarantine.reset_index().to_csv(target, index=False)
        frame = frame.loc[~quarantine_mask].copy()
        after_totals = check_totals(frame, formulas, filename, "after")
        partition_issues, partition_checks, incomplete_checks = group_total_checks(frame, roles, filename)
        totals.extend(after_totals + partition_issues)
        bounds, flags = outlier_checks(frame, roles, filename)
        outlier_bounds.extend(bounds)
        outliers.extend(flags)
        mismatch_counts = pd.Series([v["source_record"] for v in after_totals + partition_issues]).value_counts()
        outlier_counts = pd.Series([v["source_record"] for v in flags]).value_counts()
        metadata = pd.DataFrame(index=frame.index)
        metadata["file"] = filename
        metadata["scope"] = frame.apply(lambda row: row_scope(row, path.name), axis=1)
        metadata["missing_numeric_cells"] = frame[roles["measures"]].isna().sum(axis=1)
        metadata["total_mismatch_checks"] = mismatch_counts.reindex(frame.index, fill_value=0).astype(int)
        metadata["outlier_cells"] = outlier_counts.reindex(frame.index, fill_value=0).astype(int)
        metadata["ambiguous_key"] = conflict.reindex(frame.index, fill_value=False)
        metadata["invalid_value_masked"] = frame.index.isin(invalid_rows)
        row_flags.extend(metadata.reset_index().to_dict("records"))
        profiles.extend(quality_profile(frame, roles, filename, "after"))
        target = output / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        frame.reset_index().to_csv(target, index=False)
        dictionaries.append({"file": filename, "columns": cols, "roles": roles,
                             "dtypes": {c: str(frame[c].dtype) for c in cols},
                             "grain": "under-specified" if ambiguous_grain else "validated_unique_keys",
                             "nonadditive_fields": ["Number of jails"] if path.name == "Prison_details_2015.csv" else [],
                             "aggregation_warning": "Never sum across files or mix total/subtotal/detail rows. Consult row_flags.csv."})
        summaries.append({"file": filename, "rows_before": rows_before, "rows_after": len(frame),
                          "blank_records_removed": blank, "schema_repaired": repaired,
                          "duplicate_candidates": duplicate_candidates, "duplicates_removed": len(removed),
                          "duplicates_retained_ambiguous_grain": duplicate_candidates if ambiguous_grain else 0,
                          "quarantined_rows": len(quarantine), "key_conflict_rows_retained": int(conflict.loc[frame.index].sum()),
                          "missing_cells_before": sum(p["missing"] for p in profiles if p["file"] == filename and p["stage"] == "before"),
                          "missing_cells_after": int(frame.isna().sum().sum()),
                          "within_record_mismatches_before": len(before_totals),
                          "within_record_mismatches_after": len(after_totals),
                          "within_record_checks_after": sum(int(frame[[t] + parts].notna().all(axis=1).sum())
                                                            for t, parts in formulas),
                          "partition_mismatches": len(partition_issues), "partition_checks": partition_checks,
                          "partition_checks_incomplete": incomplete_checks, "outlier_cells_flagged": len(flags)})
    tables = {"quality_columns": profiles, "quality_summary": summaries, "cell_actions": events,
              "category_changes": categories, "total_checks_failed": totals, "outlier_bounds": outlier_bounds,
              "outliers": outliers, "row_flags": row_flags, "excluded_records": lineage,
              "schema_repairs": schema_repairs, "blank_records": blank_records}
    for name, records in tables.items():
        pd.DataFrame(records).to_csv(reports / f"{name}.csv", index=False)
    (reports / "cleaned_schema.json").write_text(json.dumps(dictionaries, indent=2) + "\n")
    clean_manifest = [{"file": p.relative_to(output).as_posix(), "sha256": sha256(p)}
                      for p in sorted(output.rglob("*")) if p.is_file()]
    (reports / "cleaned_manifest.json").write_text(json.dumps(clean_manifest, indent=2) + "\n")
    unchanged = all(sha256(raw / name) == digest for name, digest in expected.items())
    if not unchanged:
        raise AssertionError("Raw files changed during cleaning.")
    result = {"files": len(summaries), "rows_before": sum(v["rows_before"] for v in summaries),
              "rows_after": sum(v["rows_after"] for v in summaries),
              "duplicates_removed": sum(v["duplicates_removed"] for v in summaries),
              "quarantined_rows": sum(v["quarantined_rows"] for v in summaries),
              "missing_cells_before": sum(v["missing_cells_before"] for v in summaries),
              "missing_cells_after": sum(v["missing_cells_after"] for v in summaries),
              "counts_recovered": sum(v["action"] == "recover_from_agreeing_totals" for v in events),
              "outlier_cells_flagged": len(outliers), "raw_hashes_unchanged": unchanged}
    (reports / "run_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def load_cleaned(root, filename, scope):
    """Load a declared aggregation scope with saved types and row-quality metadata."""
    if scope not in {"detail", "reported_total", "reported_subtotal", "separate_population", "directory"}:
        raise ValueError("Choose one explicit row scope; mixing totals and details would double count.")
    root = Path(root)
    specs = json.loads((root / "results/tables/cleaning/cleaned_schema.json").read_text())
    spec = next(s for s in specs if s["file"] == filename)
    frame = pd.read_csv(root / "data/processed/cleaned" / filename, dtype=spec["dtypes"])
    flags = pd.read_csv(root / "results/tables/cleaning/row_flags.csv")
    selected = flags[flags["file"].eq(filename) & flags["scope"].eq(scope)]
    return frame.merge(selected.drop(columns="file"), on="source_record", validate="one_to_one")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    print(json.dumps(run_cleaning(args.root), indent=2))


if __name__ == "__main__":
    main()
