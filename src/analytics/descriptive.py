"""Describe the selected prison tables with explicit grains and denominators."""

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.preprocessing.cleaning import sha256
from src.preprocessing.schema import token
from src.preprocessing.selection import (CAPACITY, POPULATION, MARGINALS,
                                         STATUS, descriptive_columns, load_descriptive_view)
from src.preprocessing.transformation import FEATURES, load_transformed


KEYS = ["state", "year"]


def safe_ratio(numerator, denominator):
    """A zero or missing denominator stays undefined, never an invented zero."""
    numerator = pd.Series(numerator, copy=False).astype(float)
    denominator = pd.Series(denominator, copy=False).astype(float)
    return numerator.div(denominator.where(denominator.gt(0)))


def numeric_statistics(series):
    values = pd.to_numeric(series, errors="raise").dropna().astype(float)
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite values cannot enter statistical summaries.")
    n = len(values)
    result = {"n": n, "missing": int(series.isna().sum()), "zeros": int(values.eq(0).sum()),
              "nonzero": int(values.ne(0).sum()), "distinct_values": int(values.nunique())}
    if n == 0:
        result.update({c: np.nan for c in ["mean", "median", "minimum", "maximum", "range",
                      "sample_variance", "sample_std", "q1", "q3", "iqr", "skewness", "excess_kurtosis"]})
        result.update(mode_values="[]", mode_frequency=0, mode_count=0, mode_status="no_observations", shape_status="empty")
        return result
    q1, q3 = values.quantile([0.25, 0.75], interpolation="linear")
    constant = values.nunique() == 1
    frequencies = values.value_counts()
    highest = int(frequencies.iloc[0])
    modes = sorted(float(v) for v in frequencies[frequencies.eq(highest)].index)
    # Do not print hundreds of uninformative 'modes' for all-unique ratios.
    unique = highest == 1 and n > 1
    result.update(mean=float(values.mean()), median=float(values.median()), minimum=float(values.min()),
                  maximum=float(values.max()), range=float(values.max() - values.min()),
                  sample_variance=float(values.var(ddof=1)) if n > 1 else np.nan,
                  sample_std=float(values.std(ddof=1)) if n > 1 else np.nan,
                  q1=float(q1), q3=float(q3), iqr=float(q3 - q1),
                  skewness=float(values.skew()) if n >= 3 and not constant else np.nan,
                  excess_kurtosis=float(values.kurt()) if n >= 4 and not constant else np.nan,
                  mode_values=json.dumps([] if unique else modes), mode_frequency=highest, mode_count=len(modes),
                  mode_status="all_values_unique" if unique else "single_mode" if len(modes) == 1 else "multiple_modes",
                  shape_status="constant_undefined" if constant else "sample_size_limits" if n < 4 else "defined")
    return result


def summary_rows(frame, measures, context):
    return [dict(context, measure=c, **numeric_statistics(frame[c])) for c in measures]


def reference_panel(reference):
    frame = reference.copy()
    for status in ["convicts", "under_trial", "detenues", "others"]:
        frame[status] = frame["male_" + status] + frame["female_" + status]
    frame["male_prisoners"] = frame.total_prisoners - frame.female_prisoners
    if not frame[["convicts", "under_trial", "detenues", "others"]].sum(axis=1).eq(frame.total_prisoners).all():
        raise ValueError("Reference legal-status counts do not partition the population.")
    frame["occupancy_ratio"] = safe_ratio(frame.total_prisoners, frame.total_capacity)
    frame["undertrial_share"] = safe_ratio(frame.undertrial_prisoners, frame.total_prisoners)
    frame["female_share"] = safe_ratio(frame.female_prisoners, frame.total_prisoners)
    return frame


def yearly_population(frame, cohort_name):
    rows = []
    for year, group in frame.groupby("year", sort=True):
        prisoners, capacity = int(group.total_prisoners.sum()), int(group.total_capacity.sum())
        rows.append({"cohort": cohort_name, "year": int(year), "states": int(group.state.nunique()),
                     "prisoners": prisoners, "capacity": capacity,
                     "convicts": int(group.convicts.sum()), "undertrials": int(group.under_trial.sum()),
                     "detenues": int(group.detenues.sum()), "others": int(group.others.sum()),
                     "female_prisoners": int(group.female_prisoners.sum()),
                     "occupancy_ratio_pooled": prisoners / capacity if capacity > 0 else np.nan,
                     "occupancy_ratio_mean_state": float(group.occupancy_ratio.mean()),
                     "undertrial_share_pooled": float(group.under_trial.sum() / prisoners) if prisoners else np.nan,
                     "female_share_pooled": float(group.female_prisoners.sum() / prisoners) if prisoners else np.nan,
                     "states_above_capacity": int(group.total_prisoners.gt(group.total_capacity).sum()),
                     "zero_prisoner_states": int(group.total_prisoners.eq(0).sum())})
    result = pd.DataFrame(rows)
    result["prisoners_change"] = result.prisoners.diff()
    result["prisoners_change_fraction"] = result.prisoners.pct_change(fill_method=None)
    return result


def demographic_tables(views, reference):
    pieces, gender_pieces, status_pieces = [], [], []
    ref = reference[KEYS + ["total_prisoners", "male_prisoners", "female_prisoners"]]
    for filename, dimension in [("Age_group.csv", "age_group"), ("Age_group.csv", "nationality"),
                                ("Education.csv", "education"), ("Caste.csv", "caste"),
                                ("Religion.csv", "religion"), ("Domicile.csv", "domicile")]:
        view = views[filename]
        if dimension == "age_group":
            measures = ["age_16_18", "age_18_30", "age_30_50", "age_50_above"]
            work = view.melt(id_vars=KEYS + ["gender", "type"], value_vars=measures,
                             var_name="category", value_name="prisoners")
        else:
            value = view[["age_16_18", "age_18_30", "age_30_50", "age_50_above"]].sum(axis=1, min_count=4) if dimension == "nationality" else view[["convicts", "under_trial", "detenues", "others"]].sum(axis=1, min_count=4)
            label = "category" if dimension == "nationality" else dimension
            dimensions = KEYS + ["gender", label] + (["type"] if dimension == "nationality" else [])
            work = view[dimensions].rename(columns={label: "category"}).copy()
            work["prisoners"] = value
        if filename == "Age_group.csv":
            status_work = work.rename(columns={"type": "legal_status"}).copy()
            status_work["legal_status"] = status_work.legal_status.map({v: k for k, v in STATUS.items()})
        else:
            status_work = view.melt(id_vars=KEYS + [dimension], value_vars=list(STATUS),
                                    var_name="legal_status", value_name="prisoners").rename(columns={dimension: "category"})
        status_year = status_work.groupby(["year", "legal_status", "category"], sort=True).prisoners.sum().reset_index()
        matching = reference.merge(view[KEYS].drop_duplicates(), on=KEYS, validate="one_to_one")
        status_denominators = matching.groupby("year")[list(STATUS)].sum().reset_index().melt(
            id_vars="year", var_name="legal_status", value_name="status_population")
        status_year = status_year.merge(status_denominators, on=["year", "legal_status"], validate="many_to_one")
        status_year["share_within_status"] = safe_ratio(status_year.prisoners, status_year.status_population)
        status_year["covered_states"] = status_year.year.map(view.groupby("year").state.nunique())
        status_year["source"], status_year["dimension"] = filename, dimension
        status_pieces.append(status_year)
        by_gender = work.groupby(KEYS + ["gender", "category"], sort=True).prisoners.sum(min_count=1).reset_index()
        by_gender = by_gender.merge(ref, on=KEYS, how="left", validate="many_to_one")
        by_gender["gender_population"] = np.where(by_gender.gender.eq("Male"), by_gender.male_prisoners, by_gender.female_prisoners)
        by_gender["share_within_gender"] = safe_ratio(by_gender.prisoners, by_gender.gender_population)
        by_gender["source"], by_gender["dimension"] = filename, dimension
        gender_pieces.append(by_gender[["source", "dimension"] + KEYS + ["gender", "category", "prisoners", "gender_population", "share_within_gender"]])
        totals = by_gender.groupby(KEYS + ["category"], sort=True).prisoners.sum().reset_index()
        totals = totals.merge(ref[KEYS + ["total_prisoners"]], on=KEYS, validate="many_to_one")
        totals["source"], totals["dimension"] = filename, dimension
        totals["share_of_state_population"] = safe_ratio(totals.prisoners, totals.total_prisoners)
        pieces.append(totals[["source", "dimension"] + KEYS + ["category", "prisoners", "total_prisoners", "share_of_state_population"]])
    for dimension, fields in [("gender", ["male_prisoners", "female_prisoners"]),
                              ("legal_status", ["convicts", "under_trial", "detenues", "others"])]:
        group = reference.melt(id_vars=KEYS + ["total_prisoners"], value_vars=fields,
                               var_name="category", value_name="prisoners")
        group["source"], group["dimension"] = POPULATION, dimension
        group["share_of_state_population"] = safe_ratio(group.prisoners, group.total_prisoners)
        pieces.append(group[["source", "dimension"] + KEYS + ["category", "prisoners", "total_prisoners", "share_of_state_population"]])
    state_year = pd.concat(pieces, ignore_index=True)
    gender_state_year = pd.concat(gender_pieces, ignore_index=True)
    # Reconcile each separate marginal distribution, never sum across dimensions.
    for _, group in state_year.groupby(["source", "dimension", "state", "year"], sort=True):
        if int(group.prisoners.sum()) != int(group.total_prisoners.iloc[0]):
            raise ValueError("A demographic distribution does not match its covered population.")
    year_rows = []
    reference_totals = reference.groupby("year").total_prisoners.sum()
    for (source, dimension, year), group in state_year.groupby(["source", "dimension", "year"], sort=True):
        denominator = int(group.drop_duplicates(KEYS).total_prisoners.sum())
        categories = group.groupby("category").prisoners.sum()
        for category, count in categories.items():
            year_rows.append({"source": source, "dimension": dimension, "year": int(year), "category": category,
                              "prisoners": int(count), "covered_prisoners": denominator,
                              "covered_states": int(group.state.nunique()),
                              "share_of_covered_population": count / denominator if denominator else np.nan,
                              "population_coverage_fraction": denominator / reference_totals.loc[year]})
    year = pd.DataFrame(year_rows)
    demographic_status_year = pd.concat(status_pieces, ignore_index=True)
    gender_counts = gender_state_year.groupby(["source", "dimension", "year", "gender", "category"]).prisoners.sum().reset_index()
    gender_denominators = gender_state_year.drop_duplicates(["source", "dimension", "state", "year", "gender"]).groupby(
        ["source", "dimension", "year", "gender"]).agg(gender_population=("gender_population", "sum"), covered_states=("state", "nunique")).reset_index()
    gender_year = gender_counts.merge(gender_denominators, on=["source", "dimension", "year", "gender"], validate="many_to_one")
    gender_year["share_within_gender"] = safe_ratio(gender_year.prisoners, gender_year.gender_population)
    return state_year, gender_state_year, year, demographic_status_year, gender_year


def correlation_rows(frame, measures, scope, year=None):
    rows = []
    for method in ["pearson", "spearman"]:
        matrix = frame[measures].corr(method=method)
        for left, right in itertools.product(measures, repeat=2):
            rows.append({"scope": scope, "year": year, "method": method, "left": left, "right": right,
                         "paired_n": int(frame[[left, right]].notna().all(axis=1).sum()),
                         "correlation": matrix.at[left, right]})
    return rows


def recidivism_tables(view):
    frame = view[KEYS + ["source_record", "convicts_admitted", "habitual_offenders"]].copy()
    frame["count_pair_valid"] = frame.habitual_offenders.le(frame.convicts_admitted)
    frame["habitual_share_of_admissions"] = safe_ratio(frame.habitual_offenders, frame.convicts_admitted).where(frame.count_pair_valid)
    annual = []
    for year, group in frame.groupby("year", sort=True):
        valid = group[group.count_pair_valid]
        denominator = int(valid.convicts_admitted.sum())
        numerator = int(valid.habitual_offenders.sum())
        annual.append({"year": int(year), "reported_states": int(group.state.nunique()),
                       "reported_admissions": int(group.convicts_admitted.sum()),
                       "reported_habitual_offenders": int(group.habitual_offenders.sum()),
                       "valid_pair_states": int(valid.state.nunique()), "invalid_pair_states": int((~group.count_pair_valid).sum()),
                       "positive_denominator_states": int(valid.convicts_admitted.gt(0).sum()),
                       "ratio_cohort_admissions": denominator, "ratio_cohort_habitual": numerator,
                       "habitual_share_of_admissions_pooled": numerator / denominator if denominator > 0 else np.nan})
    return frame, pd.DataFrame(annual)


def run_descriptive(root):
    root = Path(root).resolve()
    output = root / "results/tables/descriptive"
    output.mkdir(parents=True, exist_ok=True)
    inputs = []
    manifests = [("data/raw", "results/tables/dataset_inventory.json"),
                 ("data/processed/cleaned", "results/tables/cleaning/cleaned_manifest.json"),
                 ("data/processed/selected", "results/tables/selection/selected_manifest.json"),
                 ("data/processed/transformed", "results/tables/transformation/transformed_manifest.json")]
    for folder, manifest in manifests:
        for item in json.loads((root / manifest).read_text()):
            path = root / folder / item["file"]
            if sha256(path) != item["sha256"]:
                raise ValueError(f"An upstream file changed: {path.relative_to(root)}")
            inputs.append({"file": path.relative_to(root).as_posix(), "sha256": item["sha256"]})
    plans = json.loads((root / "results/tables/selection/descriptive_views.json").read_text())
    specs = {s["file"]: s for s in json.loads((root / "results/tables/cleaning/cleaned_schema.json").read_text())}
    views = {p["file"]: load_descriptive_view(root, p["file"]) for p in plans}
    reference = reference_panel(pd.read_csv(root / "data/processed/selected/population_capacity_reference.csv"))
    profiles = load_transformed(root, "profile_features.csv")
    reference_keys = set(reference[KEYS].itertuples(index=False, name=None))
    for filename, frame in views.items():
        if set(frame[KEYS].itertuples(index=False, name=None)) - reference_keys:
            raise ValueError(f"Source coverage cannot be matched to the population reference: {filename}")
    global_rows, stratum_rows, annual_rows, frequency_rows, coverage_rows, definitions = [], [], [], [], [], []
    for filename, frame in views.items():
        spec = specs[filename]
        selected = set(descriptive_columns(spec))
        measures = [c for c in spec["roles"]["measures"] if c in selected]
        keys = next(p["native_keys"] for p in plans if p["file"] == filename)
        dimensions = [k for k in keys if k not in KEYS]
        global_rows.extend(summary_rows(frame, measures, {"source": filename, "scope": "eligible_native_records"}))
        for year, group in frame.groupby("year", sort=True):
            annual_rows.extend(summary_rows(group, measures, {"source": filename, "year": int(year),
                                                              "states": int(group.state.nunique()), "scope": "eligible_native_records"}))
        grouped = frame.groupby(dimensions, dropna=False, sort=True) if dimensions else [((), frame)]
        for key, group in grouped:
            context = json.dumps(dict(zip(dimensions, key if isinstance(key, tuple) else (key,))), ensure_ascii=False)
            stratum_rows.extend(summary_rows(group, measures, {"source": filename, "stratum": context}))
        for column in keys:
            frequencies = frame[column].value_counts(dropna=False, sort=False)
            for value, count in sorted(frequencies.items(), key=lambda pair: str(pair[0])):
                frequency_rows.append({"source": filename, "field": column, "category": str(value),
                                       "native_records": int(count), "denominator_records": len(frame),
                                       "record_fraction": count / len(frame) if len(frame) else np.nan})
        for year, group in frame.groupby("year", sort=True):
            matching = reference.merge(group[KEYS].drop_duplicates(), on=KEYS, validate="one_to_one")
            total = reference.loc[reference.year.eq(year), "total_prisoners"].sum()
            coverage_rows.append({"source": filename, "year": int(year), "native_records": len(group),
                                  "covered_states": int(group.state.nunique()), "reference_states": int(reference.loc[reference.year.eq(year), "state"].nunique()),
                                  "matched_reference_prisoners": int(matching.total_prisoners.sum()),
                                  "population_coverage_fraction": float(matching.total_prisoners.sum() / total)})
        for c in measures:
            unit = ("rupees, nominal source values" if "In Rs." in c else
                    "source wage units; currency/time basis unverified" if filename == "Wages.csv" else
                    "reported field count; preserve source definition")
            definitions.append({"source": filename, "measure": c, "unit": unit,
                                "observation_keys": ";".join(keys),
                                "sum_across_years": "not a unique-person or single-year total",
                                "population_note": "Separate source indicator; overlaps with other sources/measures are possible."})
    reference_measures = ["total_prisoners", "total_capacity", "convicts", "under_trial", "detenues", "others",
                          "female_prisoners", "male_prisoners", "occupancy_ratio", "undertrial_share", "female_share"]
    global_rows.extend(summary_rows(reference, reference_measures, {"source": "verified_population_reference", "scope": "state_year"}))
    global_rows.extend(summary_rows(profiles, FEATURES, {"source": "five_feature_profiles", "scope": "selected_state_year"}))
    state_summary = []
    for state, group in reference.groupby("state", sort=True):
        state_summary.extend(summary_rows(group, reference_measures, {"state": state, "years": len(group),
                                                                    "first_year": int(group.year.min()), "last_year": int(group.year.max())}))
    years = sorted(reference.year.unique())
    stable = reference.groupby("state").year.agg(lambda s: set(s) == set(years))
    balanced = reference[reference.state.isin(stable[stable].index)].copy()
    annual_available = yearly_population(reference, "all_available_states")
    annual_balanced = yearly_population(balanced, "same_states_all_13_years")
    latest = reference[reference.year.eq(max(years))].copy()
    latest["prisoner_count_rank"] = latest.total_prisoners.rank(method="min", ascending=False).astype(int)
    latest["occupancy_ratio_rank"] = latest.occupancy_ratio.rank(method="min", ascending=False).astype(int)
    demographic_state, demographic_gender, demographic_year, demographic_status_year, demographic_gender_year = demographic_tables(views, reference)
    common_keys = set(reference[KEYS].itertuples(index=False, name=None))
    for filename in MARGINALS:
        common_keys &= set(views[filename][KEYS].itertuples(index=False, name=None))
    common = pd.DataFrame(sorted(common_keys), columns=KEYS)
    correlations = correlation_rows(profiles, FEATURES, "selected_profiles_pooled")
    for year, group in profiles.groupby("year", sort=True):
        correlations.extend(correlation_rows(group, FEATURES, "selected_profiles_within_year", int(year)))
    centered = profiles[FEATURES] - profiles.groupby("state")[FEATURES].transform("mean")
    correlations.extend(correlation_rows(centered, FEATURES, "selected_profiles_within_state_centered"))
    correlations.extend(correlation_rows(reference, ["total_prisoners", "total_capacity", "female_prisoners", "undertrial_prisoners",
                                                     "occupancy_ratio", "undertrial_share", "female_share"], "reference_state_year_pooled"))
    recidivism, recidivism_year = recidivism_tables(views["Recidivism.csv"])

    # Crime counts stay separate by statute/status source and complete crime grid.
    crime_rows = []
    for filename, frame in views.items():
        if "crime" not in Path(filename).name.lower():
            continue
        measures = [c for c in specs[filename]["roles"]["measures"] if token(c).startswith(("male_", "female_"))]
        frame = frame.assign(reported_count=frame[measures].sum(axis=1, min_count=len(measures)))
        for year, group in frame.groupby("year", sort=True):
            denominator = int(group.reported_count.sum())
            for head, count in group.groupby("CRIME HEAD").reported_count.sum().items():
                crime_rows.append({"source": filename, "year": int(year), "crime_head": head, "reported_count": int(count),
                                   "covered_states": int(group.state.nunique()), "within_source_total": denominator,
                                   "share_within_source_counts": count / denominator if denominator else np.nan})
    # Other indicators are never summed across differently defined measures/categories.
    indicator_rows = []
    for filename, frame in views.items():
        spec = specs[filename]
        measures = [c for c in spec["roles"]["measures"] if c in set(descriptive_columns(spec))]
        keys = next(p["native_keys"] for p in plans if p["file"] == filename)
        dims = [k for k in keys if k not in KEYS]
        if filename in MARGINALS or filename in {POPULATION, CAPACITY} or "crime" in Path(filename).name.lower():
            continue
        for key, group in frame.groupby(["year"] + dims, sort=True, dropna=False):
            key = key if isinstance(key, tuple) else (key,)
            context = json.dumps(dict(zip(dims, key[1:])), ensure_ascii=False)
            for measure in measures:
                additive = filename != "Wages.csv"
                indicator_rows.append({"source": filename, "year": int(key[0]), "stratum": context, "measure": measure,
                                       "covered_states": int(group.state.nunique()), "native_records": len(group),
                                       "sum_reported_values": float(group[measure].sum()) if additive else np.nan,
                                       "mean_state_value": float(group[measure].mean()), "median_state_value": float(group[measure].median()),
                                       "interpretation": "Sum of reported values in this one indicator/stratum; not unique people across indicators or years." if additive else "Wages are summarized across states without adding rates; source units unverified."})
    tables = {"numeric_summary.csv": pd.DataFrame(global_rows), "stratified_numeric_summary.csv": pd.DataFrame(stratum_rows),
              "annual_numeric_summary.csv": pd.DataFrame(annual_rows), "categorical_record_frequencies.csv": pd.DataFrame(frequency_rows),
              "source_year_coverage.csv": pd.DataFrame(coverage_rows), "measure_dictionary.csv": pd.DataFrame(definitions),
              "state_year_totals.csv": reference, "state_numeric_summary.csv": pd.DataFrame(state_summary),
              "year_summary_available.csv": annual_available, "year_summary_balanced.csv": annual_balanced,
              "latest_state_snapshot.csv": latest.sort_values("prisoner_count_rank"),
              "demographic_state_year.csv": demographic_state, "demographic_gender_state_year.csv": demographic_gender,
              "demographic_year.csv": demographic_year, "common_demographic_cohort_keys.csv": common,
              "demographic_status_year.csv": demographic_status_year, "demographic_gender_year.csv": demographic_gender_year,
              "correlations.csv": pd.DataFrame(correlations), "recidivism_state_year.csv": recidivism,
              "recidivism_year.csv": recidivism_year, "crime_year.csv": pd.DataFrame(crime_rows),
              "indicator_year.csv": pd.DataFrame(indicator_rows)}
    for name, frame in tables.items():
        frame.to_csv(output / name, index=False, float_format="%.17g")
    metadata = {"sample_variance_ddof": 1, "quartiles": "linear interpolation", "skewness": "unbiased Fisher-Pearson sample skewness; n>=3 and nonconstant",
                "kurtosis": "unbiased Fisher excess kurtosis (normal reference=0); n>=4 and nonconstant",
                "mode_rule": "all tied modes recorded; all-unique series explicitly marked and not listed as informative modes",
                "correlation": "Pearson and Spearman; pairwise complete observations; no significance or causality claim",
                "national_ratios": "ratio of matching population sums, not an unweighted mean of state ratios",
                "units": "counts are source-specific annual reported observations; do not sum stocks across years as distinct prisoners",
                "recidivism": "habitual/admissions share is undefined for zero admissions or numerator>denominator; not longitudinal reoffending probability",
                "plots_or_mining_run": False}
    (output / "methods.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output / "input_provenance.json").write_text(json.dumps(inputs, indent=2) + "\n")
    manifest = [{"file": name, "rows": len(frame), "sha256": sha256(output / name)} for name, frame in tables.items()]
    (output / "table_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if any(sha256(root / item["file"]) != item["sha256"] for item in inputs):
        raise AssertionError("Descriptive analytics changed an upstream data file.")
    summary = {"descriptive_sources": len(views), "reference_state_years": len(reference), "balanced_states": int(balanced.state.nunique()),
               "balanced_state_years": len(balanced), "profile_state_years": len(profiles), "common_demographic_state_years": len(common),
               "numeric_summary_rows": len(global_rows), "stratified_summary_rows": len(stratum_rows), "tables_generated": len(tables),
               "recidivism_invalid_count_pairs": int((~recidivism.count_pair_valid).sum()), "upstream_files_verified": len(inputs),
               "upstream_unchanged": True, "visualization_or_mining_started": False}
    (output / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    print(json.dumps(run_descriptive(parser.parse_args().root), indent=2))


if __name__ == "__main__":
    main()
