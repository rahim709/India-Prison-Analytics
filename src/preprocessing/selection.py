"""Select task inputs and validate their observation units without transforming features."""

import argparse
import itertools
import json
from pathlib import Path

import pandas as pd

from .cleaning import sha256
from .schema import STATE_COLUMNS, token


POPULATION = "Jail wise population of prison inmates.csv"
CAPACITY = "Other Prison data/Population_and_capacity_of_jails.csv"
MARGINALS = {
    "Age_group.csv": {"category": ["Indians", "Foreigners"],
                      "type": ["Convicts", "Under Trials", "Detenus", "Others"],
                      "gender": ["Male", "Female"]},
    "Education.csv": {"gender": ["Male", "Female"], "education": [
        "Below Class X", "Class X and above but below graduate", "Graduate",
        "Holding technical degree/diploma etc", "Illiterate", "Post-Graduate"]},
    "Caste.csv": {"gender": ["Male", "Female"], "caste": ["SC", "ST", "OBC", "Others"]},
    "Religion.csv": {"gender": ["Male", "Female"], "religion": ["Christian", "Hindu", "Muslim", "Others", "Sikh"]},
    "Domicile.csv": {"gender": ["Male", "Female"], "domicile": [
        "Belongs to other Country", "Belongs to other State", "Belongs to State"]},
}
STATUS = {"convicts": "Convicts", "under_trial": "Under Trials", "detenues": "Detenus", "others": "Others"}
BASE_FIELDS = ["state", "year", "population_source_record", "capacity_source_record",
               "total_prisoners", "total_capacity", "female_prisoners", "undertrial_prisoners"]
DEFERRED = {
    "Prison_details_2015.csv": "Separate 2015 jail directory; contacts and jail identifiers are irrelevant to historical state-year profiles.",
    "Total_Budget_and_Actual_Expenditure_during_ the_year_2015_2016.csv": "Separate 2015–2016 fiscal cross-section cannot join to 2001–2013 on state alone.",
    "Budget.CSV": "Administrative budget indicators cover only 2001–2010; outside the selected population/demographic scope, with units requiring verification.",
    "Expenditure.CSV": "Administrative spending indicators cover only 2001–2010; outside the selected population/demographic scope, with units requiring verification.",
    "Expenditure_on_inmates.CSV": "Administrative spending indicators cover only 2001–2010; outside the selected population/demographic scope, with units requiring verification.",
    "Details_of_electronic_equipments_used_in_prison.CSV": "Equipment inventory is outside the selected prisoner-profile scope and has shorter temporal coverage.",
    "Number_of_vehicles_available.CSV": "Vehicle inventory is outside the selected prisoner-profile scope and has shorter temporal coverage.",
    "Movements_outside_jail_premises.CSV": "Movement indicators are flows rather than prisoner-profile attributes; shorter temporal coverage.",
    "Strength_of_officials.CSV": "Overlapping staff hierarchies require a separate resource study; not prisoner demographic observations.",
    "Training_of_Jail_Officers.CSV": "Officer training is a separate administrative population; not prisoner vocational training.",
}
FEATURE_CONTRACT = [
    {"feature": "occupancy_ratio", "sources": [POPULATION, CAPACITY],
     "future_formula": "total_prisoners / total_capacity", "reason": "Capacity pressure, independent of absolute state size."},
    {"feature": "undertrial_share", "sources": [POPULATION],
     "future_formula": "undertrial_prisoners / total_prisoners", "reason": "Legal-status composition without complementary status shares."},
    {"feature": "female_share", "sources": [POPULATION],
     "future_formula": "female_prisoners / total_prisoners", "reason": "Aggregate gender composition; not an individual risk score."},
    {"feature": "age_18_30_share", "sources": ["Age_group.csv", POPULATION],
     "future_formula": "sum age_18_30 over nationality, status and gender / total_prisoners", "reason": "One age-composition measure; omit other complementary age shares."},
    {"feature": "illiterate_share", "sources": ["Education.csv", POPULATION],
     "future_formula": "sum four status counts for education=Illiterate over gender / total_prisoners", "reason": "One education-composition measure with a verified common denominator."},
]


def canonical_keys(frame):
    state = next(c for c in frame if c in STATE_COLUMNS)
    year = next(c for c in frame if c.lower() in {"year", "timeperiod"})
    return frame.rename(columns={state: "state", year: "year"})


def checked_join(left, right, keys, cardinality, how="inner"):
    if left[keys].isna().any().any() or right[keys].isna().any().any():
        raise ValueError("Join keys cannot contain missing values.")
    return left.merge(right, on=keys, how=how, validate=cardinality, indicator=True,
                      suffixes=("_population", "_capacity"))


def marginal_audit(frame, reference, filename):
    """Compare complete marginal distributions to the same eight population cells."""
    dimensions = MARGINALS[filename]
    expected = set(itertools.product(*dimensions.values()))
    measures = (["age_16_18", "age_18_30", "age_30_50", "age_50_above"]
                if filename == "Age_group.csv" else list(STATUS))
    groups = {key: group for key, group in frame.groupby(["state", "year"], sort=True)}
    findings = []
    for ref in reference.to_dict("records"):
        key = (ref["state"], ref["year"])
        group = groups.get(key, frame.iloc[:0])
        tuples = list(group[list(dimensions)].itertuples(index=False, name=None))
        grid_complete = len(tuples) == len(expected) and set(tuples) == expected
        missing = int(group[measures].isna().sum().sum())
        mismatches = []
        for gender in ["Male", "Female"]:
            for status, label in STATUS.items():
                column = gender.lower() + "_" + status
                if filename == "Age_group.csv":
                    values = group.loc[group.gender.eq(gender) & group.type.eq(label), measures]
                else:
                    values = group.loc[group.gender.eq(gender), [status]]
                # A partially missing margin must never be interpreted as zero.
                if len(values) == 0 or values.isna().any().any():
                    continue
                if int(values.sum().sum()) != int(ref[column]):
                    mismatches.append(column)
        findings.append({"file": filename, "state": key[0], "year": key[1],
                         "present": bool(len(group)), "rows": len(group), "expected_rows": len(expected),
                         "grid_complete": grid_complete, "missing_measure_cells": missing,
                         "mismatch_fields": ";".join(mismatches),
                         "compatible": grid_complete and missing == 0 and not mismatches})
    reference_keys = set(zip(reference.state, reference.year))
    if set(groups) - reference_keys:
        raise ValueError(f"Unmatched marginal keys require review: {filename}")
    return pd.DataFrame(findings)


def descriptive_columns(spec):
    """Choose one additive column representation, while keeping native dimensions."""
    filename = Path(spec["file"]).name
    roles = spec["roles"]
    measures = roles["measures"]
    if filename in {Path(POPULATION).name, "Inmates_suffering_from_mental_ilness.csv"}:
        measures = [c for c in measures if token(c).startswith(("male_", "female_"))]
    elif "crime" in filename.lower():
        measures = [c for c in measures if token(c).startswith(("male_", "female_"))]
    elif filename in {"Inmates_death.csv", "Inmates_escapee.csv", "Inmates_released.csv",
                      "Details_of_inmates_parole_during_the_year.csv", "Period_of_detention_of_undertrials.csv"}:
        measures = [c for c in measures if c.lower() in {"male", "female"}]
    elif filename == "Population_and_capacity_of_jails.csv":
        measures = ["Number of Central Jails", "Total Capacity of Inmates", "Total Inmate population"]
    elif filename == "Number_of_women_prisoners_with_children.csv":
        measures = [c for c in measures if not c.startswith("Total")]
    return list(dict.fromkeys(["source_record"] + roles["keys"] + measures))


def profile_attribute_role(filename, column):
    primary = filename in [POPULATION, CAPACITY, "Age_group.csv", "Education.csv"]
    if not primary:
        return "excluded"
    if column in STATE_COLUMNS or column.lower() == "year":
        return "join_key_only"
    if column == "source_record":
        return "provenance_only"
    allowed = {
        POPULATION: {"Grand_Total": "future_denominator_and_occupancy_numerator",
                     "Total_Female": "future_numerator", "Total_Under_trial": "future_numerator"},
        CAPACITY: {"Total Capacity of Inmates": "future_denominator"},
        "Age_group.csv": {"category": "group_dimension_only", "type": "group_dimension_only",
                          "gender": "group_dimension_only", "age_18_30": "future_numerator"},
        "Education.csv": {"gender": "group_dimension_only", "education": "category_predicate_only",
                          **{c: "future_numerator" for c in STATUS}},
    }
    return allowed[filename].get(column, "validation_only_or_excluded")


def make_descriptive_view(frame, spec, flags, compatibility=None):
    """Return selected source fields with explicit per-group eligibility metadata."""
    frame = canonical_keys(frame)
    columns = descriptive_columns(spec)
    renamed = canonical_keys(pd.DataFrame(columns=columns)).columns.tolist()
    metadata = flags.loc[flags.file.eq(spec["file"])].drop(columns="file")
    merged = frame[renamed].merge(metadata, on="source_record", validate="one_to_one")
    eligible = (merged.scope.eq("detail") & merged.missing_numeric_cells.eq(0)
                & merged.total_mismatch_checks.eq(0) & ~merged.ambiguous_key & ~merged.invalid_value_masked)
    merged["record_eligible"] = eligible
    # Retained rows are not necessarily complete state-year distributions.
    # Totals/subtotals are deliberately excluded, not treated as missing detail records.
    detail_quality = eligible.where(merged.scope.eq("detail"), True)
    merged["group_quality_eligible"] = detail_quality.groupby([merged.state, merged.year]).transform("all")
    variable_categories = Path(spec["file"]).name in {"Vocational_training.csv", "Value_of_goods_produced_by_inmates.csv"}
    if not variable_categories:
        dims = (MARGINALS[spec["file"]] if spec["file"] in MARGINALS else
                {c: sorted(merged.loc[merged.scope.eq("detail"), c].dropna().unique())
                 for c in renamed if c in spec["roles"]["keys"] and c not in {"state", "year"}})
        # Original geographic key names have already become state/year.
        dims = {c: values for c, values in dims.items() if c in merged and c not in STATE_COLUMNS
                and c.lower() not in {"year", "timeperiod"}}
        expected = set(itertools.product(*dims.values()))
        complete = {}
        for key, group in merged.groupby(["state", "year"], sort=True):
            detail = group.loc[group.scope.eq("detail")]
            tuples = (list(detail[list(dims)].itertuples(index=False, name=None)) if dims
                      else [()] * len(detail))
            complete[key] = len(tuples) == len(expected) and set(tuples) == expected
        merged["category_grid_complete"] = [complete[(s, y)] for s, y in zip(merged.state, merged.year)]
    else:
        merged["category_grid_complete"] = True
    if spec["file"] in MARGINALS:
        if compatibility is not None:
            match = compatibility[compatibility.file.eq(spec["file"])][["state", "year", "compatible"]]
            merged = merged.merge(match.rename(columns={"compatible": "population_compatible"}),
                                  on=["state", "year"], how="left", validate="many_to_one")
            if merged.population_compatible.isna().any():
                raise ValueError("Marginal compatibility metadata is incomplete.")
    merged["analysis_eligible"] = (merged.record_eligible & merged.group_quality_eligible
                                   & merged.category_grid_complete)
    if "population_compatible" in merged:
        merged["analysis_eligible"] &= merged.population_compatible
    return merged


def load_descriptive_view(root, filename, eligible_only=True):
    root = Path(root)
    plans = json.loads((root / "results/tables/selection/descriptive_views.json").read_text())
    if not any(p["file"] == filename for p in plans):
        raise ValueError("This source is deferred by the selection plan.")
    specs = json.loads((root / "results/tables/cleaning/cleaned_schema.json").read_text())
    spec = next(s for s in specs if s["file"] == filename)
    frame = pd.read_csv(root / "data/processed/cleaned" / filename, dtype=spec["dtypes"])
    flags = pd.read_csv(root / "results/tables/cleaning/row_flags.csv")
    compatibility = pd.read_csv(root / "results/tables/selection/marginal_compatibility.csv")
    view = make_descriptive_view(frame, spec, flags, compatibility)
    return view.loc[view.analysis_eligible].copy() if eligible_only else view


def run_selection(root):
    root = Path(root).resolve()
    cleaned = root / "data/processed/cleaned"
    cleaning_reports = root / "results/tables/cleaning"
    reports = root / "results/tables/selection"
    selected_dir = root / "data/processed/selected"
    input_manifest = json.loads((cleaning_reports / "cleaned_manifest.json").read_text())
    input_hashes = {r["file"]: r["sha256"] for r in input_manifest}
    if any(sha256(cleaned / name) != digest for name, digest in input_hashes.items()):
        raise ValueError("Cleaned input differs from the Phase 1 manifest.")
    specs = json.loads((cleaning_reports / "cleaned_schema.json").read_text())
    frames = {s["file"]: pd.read_csv(cleaned / s["file"], dtype=s["dtypes"]) for s in specs}
    flags = pd.read_csv(cleaning_reports / "row_flags.csv")
    population, capacity = canonical_keys(frames[POPULATION]), canonical_keys(frames[CAPACITY])
    native_pop = population.rename(columns={"Jail_Type": "jail_type"})
    native_cap = capacity.rename(columns={"TYPE OF JAIL": "jail_type"})
    native = checked_join(native_pop, native_cap, ["state", "year", "jail_type"], "one_to_one", "outer")
    if not native._merge.eq("both").all():
        raise ValueError("Population and capacity native-key coverage differs.")
    native_disagreements = []
    for left, right in [("Grand_Total", "Total Inmate population"),
                        ("Total_Male", "Male Inmate population"), ("Total_Female", "Female Inmate population")]:
        for row in native.loc[~native[left].eq(native[right])].to_dict("records"):
            native_disagreements.append({"state": row["state"], "year": row["year"], "jail_type": row["jail_type"],
                                         "population_field": left, "capacity_field": right,
                                         "population_value": row[left], "capacity_value": row[right]})
    pop = population[population.Jail_Type.eq("Total")].copy()
    cap = capacity[capacity["TYPE OF JAIL"].eq("Total")].copy()
    joined = checked_join(pop, cap, ["state", "year"], "one_to_one", "outer")
    if not joined._merge.eq("both").all():
        raise ValueError("Reported state-year totals have unmatched keys.")
    for left, right in [("Grand_Total", "Total Inmate population"),
                        ("Total_Male", "Male Inmate population"), ("Total_Female", "Female Inmate population")]:
        if not joined[left].eq(joined[right]).all():
            raise ValueError("Reported state-year population totals disagree.")
    reference = pd.DataFrame({"state": joined.state, "year": joined.year,
                              "population_source_record": joined.source_record_population,
                              "capacity_source_record": joined.source_record_capacity,
                              "total_prisoners": joined.Grand_Total,
                              "total_capacity": joined["Total Capacity of Inmates"],
                              "female_prisoners": joined.Total_Female,
                              "undertrial_prisoners": joined.Total_Under_trial})
    for gender in ["male", "female"]:
        for status in STATUS:
            column = next(c for c in pop if token(c) == gender + "_" + status)
            reference[gender + "_" + status] = joined[column]
    reference = reference.sort_values(["state", "year"]).reset_index(drop=True)
    audits = pd.concat([marginal_audit(canonical_keys(frames[f]), reference, f) for f in MARGINALS], ignore_index=True)
    core = audits[audits.file.isin(["Age_group.csv", "Education.csv"])]
    eligibility = core.groupby(["state", "year"], sort=True).compatible.all().rename("marginal_compatible").reset_index()
    cohort = reference.merge(eligibility, on=["state", "year"], validate="one_to_one")
    cohort["positive_denominators"] = cohort.total_prisoners.gt(0) & cohort.total_capacity.gt(0)
    cohort["profile_eligible"] = cohort.marginal_compatible & cohort.positive_denominators
    profile = cohort.loc[cohort.profile_eligible, BASE_FIELDS].copy()
    keys = profile[["state", "year"]]
    age = canonical_keys(frames["Age_group.csv"]).merge(keys, on=["state", "year"], validate="many_to_one")
    age = age[["state", "year", "source_record", "category", "type", "gender", "age_18_30"]]
    education = canonical_keys(frames["Education.csv"]).merge(keys, on=["state", "year"], validate="many_to_one")
    education = education[["state", "year", "source_record", "gender", "education"] + list(STATUS)]
    for directory in [reports, selected_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    outputs = {"population_capacity_reference.csv": reference, "profile_base_counts.csv": profile,
               "profile_age_counts.csv": age, "profile_education_counts.csv": education}
    for filename, frame in outputs.items():
        frame.to_csv(selected_dir / filename, index=False)
    audits.to_csv(reports / "marginal_compatibility.csv", index=False)
    pd.DataFrame(native_disagreements).to_csv(reports / "native_population_disagreements.csv", index=False)
    cohort[["state", "year", "marginal_compatible", "positive_denominators", "profile_eligible"]].to_csv(reports / "cohort_eligibility.csv", index=False)
    exclusions = cohort.loc[~cohort.profile_eligible, ["state", "year", "marginal_compatible", "positive_denominators"]].copy()
    exclusions["reason"] = exclusions.apply(lambda r: "Age/education completeness or population compatibility" if not r.marginal_compatible
                                             else "Zero prisoner denominator; demographic proportions undefined", axis=1)
    exclusions.to_csv(reports / "profile_exclusions.csv", index=False)
    expected_grid = pd.MultiIndex.from_product([sorted(reference.state.unique()), range(2001, 2014)], names=["state", "year"])
    present = pd.MultiIndex.from_frame(reference[["state", "year"]])
    expected_grid.difference(present).to_frame(index=False).to_csv(reports / "absent_reference_keys.csv", index=False)
    file_decisions, attributes, views, coverage = [], [], [], []
    for spec in specs:
        filename, basename = spec["file"], Path(spec["file"]).name
        descriptive = basename not in DEFERRED
        primary = filename in [POPULATION, CAPACITY, "Age_group.csv", "Education.csv"]
        columns = descriptive_columns(spec) if descriptive else []
        reason = DEFERRED.get(basename, "Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations.")
        if primary:
            reason = "Primary profile source; explicit common-cohort and denominator checks required. " + reason
        file_decisions.append({"file": filename, "primary_profile": primary,
                               "descriptive_candidate": descriptive, "reason": reason})
        for c in spec["columns"] + ["source_record"]:
            selected = c in columns
            role = ("provenance_only" if c == "source_record" else "join_or_group_key" if c in spec["roles"]["keys"]
                    else "selected_measure" if selected else "excluded")
            explanation = ("Metadata only; never an input to distance or association mining." if role in {"provenance_only", "join_or_group_key"}
                           else "Atomic count or source-specific measure; preserve its population and unit." if selected
                           else reason if not descriptive else "Redundant total/component, numeric identifier or unused metadata; avoid double counting.")
            attributes.append({"file": filename, "column": c, "descriptive_selected": selected,
                               "role": role, "profile_role": profile_attribute_role(filename, c),
                               "reason": explanation})
        if descriptive:
            view = make_descriptive_view(frames[filename], spec, flags, audits)
            native_keys = ["state" if k in STATE_COLUMNS else "year" if k.lower() in {"year", "timeperiod"} else k for k in spec["roles"]["keys"]]
            views.append({"file": filename, "columns": columns,
                          "native_keys": native_keys, "scope": "detail",
                          "row_rule": "analysis_eligible: detail scope, complete group quality/category grid, and population-compatible marginals",
                          "warning": "Selection metadata does not make indicators additive. Preserve groups, units and overlapping-population limits."})
            coverage.append({"file": filename, "rows": len(view), "native_key_duplicate_rows": int(view.duplicated(native_keys, keep=False).sum()),
                             "state_years": len(view[["state", "year"]].drop_duplicates()),
                             "record_eligible_rows": int(view.record_eligible.sum()),
                             "group_quality_eligible_detail_rows": int((view.record_eligible & view.group_quality_eligible).sum()),
                             "analysis_eligible_rows": int(view.analysis_eligible.sum())})
    pd.DataFrame(file_decisions).to_csv(reports / "file_decisions.csv", index=False)
    pd.DataFrame(attributes).to_csv(reports / "attribute_decisions.csv", index=False)
    pd.DataFrame(coverage).to_csv(reports / "source_view_coverage.csv", index=False)
    (reports / "descriptive_views.json").write_text(json.dumps(views, indent=2) + "\n")
    (reports / "feature_contract.json").write_text(json.dumps(FEATURE_CONTRACT, indent=2) + "\n")
    contracts = [
        {"left": POPULATION, "right": CAPACITY, "keys": ["state", "year", "jail_type"], "cardinality": "one_to_one", "checked_rows": len(native), "status": "keys_valid_but_measures_disagree", "population_cells_compared": len(native) * 3, "disagreeing_cells": len(native_disagreements), "use": "Do not integrate conflicting jail-type measures; use verified state-year totals for profiles."},
        {"left": "population totals", "right": "capacity totals", "keys": ["state", "year"], "cardinality": "one_to_one", "checked_rows": len(reference), "status": "verified"},
        {"left": "age/education native records", "right": "profile cohort keys", "keys": ["state", "year"], "cardinality": "many_to_one", "status": "verified_filter_only"},
        {"left": "Age_group.csv", "right": "Education.csv", "keys": ["state", "year"], "cardinality": "many_to_many", "status": "forbidden", "reason": "Separate marginal distributions cannot establish joint age/education records. Aggregate independently at Phase 3 before one-to-one integration."},
        {"left": "2001–2013 tables", "right": "2015/2015–2016 tables", "keys": ["state"], "status": "forbidden", "reason": "Dates and geographic boundaries are not aligned."},
    ]
    (reports / "join_contracts.json").write_text(json.dumps(contracts, indent=2) + "\n")
    manifest = [{"file": name, "rows": len(frame), "dtypes": {c: str(frame[c].dtype) for c in frame},
                 "sha256": sha256(selected_dir / name)} for name, frame in outputs.items()]
    (reports / "selected_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if any(sha256(cleaned / name) != digest for name, digest in input_hashes.items()):
        raise AssertionError("Selection changed cleaned source files.")
    summary = {"files_reviewed": len(specs), "descriptive_candidate_files": len(views),
               "deferred_files": len(specs) - len(views), "primary_source_files": 4,
               "reference_state_years": len(reference), "profile_state_years": len(profile),
               "profile_excluded_state_years": len(reference) - len(profile),
               "profile_age_rows": len(age), "profile_education_rows": len(education),
               "planned_features": len(FEATURE_CONTRACT), "features_computed": False,
               "cleaned_hashes_unchanged": True}
    (reports / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    print(json.dumps(run_selection(parser.parse_args().root), indent=2))


if __name__ == "__main__":
    main()
