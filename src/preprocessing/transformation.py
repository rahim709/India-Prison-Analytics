"""Build validated profile features and equivalent Python/Spark mining inputs."""

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.preprocessing import StandardScaler

from .cleaning import sha256
from .selection import MARGINALS, STATUS


FEATURES = ["occupancy_ratio", "undertrial_share", "female_share", "age_18_30_share", "illiterate_share"]
KEYS = ["state", "year"]
META = ["profile_id", "state", "year"]


def require_keys(frame, dimensions, name):
    if frame[dimensions].isna().any().any() or frame.duplicated(dimensions).any():
        raise ValueError(f"Missing or duplicate observation keys in {name}.")


def check_counts(frame, columns, name):
    values = frame[columns].to_numpy(dtype=float, na_value=np.nan)
    if not np.isfinite(values).all() or (values < 0).any() or (values % 1 != 0).any():
        raise ValueError(f"Counts must be finite, nonmissing, nonnegative integers: {name}.")


def check_grid(frame, filename, base_keys):
    dimensions = MARGINALS[filename]
    require_keys(frame, KEYS + list(dimensions), filename)
    require_keys(frame, ["source_record"], filename)
    expected = set(itertools.product(*dimensions.values()))
    actual_keys = set()
    for key, group in frame.groupby(KEYS, sort=True):
        actual_keys.add(key)
        actual = set(group[list(dimensions)].itertuples(index=False, name=None))
        if actual != expected or len(group) != len(expected):
            raise ValueError(f"Incomplete demographic grid in {filename}: {key}.")
    if actual_keys != base_keys:
        raise ValueError(f"Cohort keys differ in {filename}.")


def validate_features(frame):
    require_keys(frame, ["profile_id"], "profile features")
    values = frame[FEATURES].to_numpy(dtype=float, na_value=np.nan)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Profile features must be finite and nonnegative.")
    if (values[:, 1:] > 1).any():
        raise ValueError("Demographic shares cannot exceed one.")


def construct_profiles(base, age, education):
    require_keys(base, KEYS, "base counts")
    fields = ["total_prisoners", "total_capacity", "female_prisoners", "undertrial_prisoners"]
    check_counts(base, fields, "base counts")
    if not (base.total_prisoners.gt(0) & base.total_capacity.gt(0)).all():
        raise ValueError("Prisoner and capacity denominators must be positive.")
    base_keys = set(base[KEYS].itertuples(index=False, name=None))
    check_grid(age, "Age_group.csv", base_keys)
    check_grid(education, "Education.csv", base_keys)
    check_counts(age, ["age_18_30"], "age counts")
    check_counts(education, list(STATUS), "education counts")

    # Aggregate each marginal table independently before any state-year join.
    adult = age.groupby(KEYS, sort=True).age_18_30.sum(min_count=16).rename("age_18_30_count").reset_index()
    totals = education[list(STATUS)].sum(axis=1, min_count=4)
    all_education = education.assign(education_count=totals).groupby(KEYS).education_count.sum(min_count=12)
    illiterate = education.loc[education.education.eq("Illiterate")].copy()
    illiterate["illiterate_count"] = illiterate[list(STATUS)].sum(axis=1, min_count=4)
    illiterate = illiterate.groupby(KEYS).illiterate_count.sum(min_count=2).reset_index()
    counts = base.merge(adult, on=KEYS, how="left", validate="one_to_one")
    counts = counts.merge(illiterate, on=KEYS, how="left", validate="one_to_one")
    counts = counts.sort_values(KEYS).reset_index(drop=True)
    expected = all_education.reindex(pd.MultiIndex.from_frame(counts[KEYS])).to_numpy()
    if not np.array_equal(expected, counts.total_prisoners.to_numpy()):
        raise ValueError("Education counts do not use the same population denominator.")
    check_counts(counts, fields + ["age_18_30_count", "illiterate_count"], "aggregated counts")
    for numerator in ["female_prisoners", "undertrial_prisoners", "age_18_30_count", "illiterate_count"]:
        if counts[numerator].gt(counts.total_prisoners).any():
            raise ValueError(f"Numerator exceeds the prison population: {numerator}.")
    counts.insert(0, "profile_id", counts.state.astype(str) + "|" + counts.year.astype(str))
    require_keys(counts, ["profile_id"], "profile identity")
    features = counts[META].copy()
    features["occupancy_ratio"] = counts.total_prisoners.astype(float) / counts.total_capacity.astype(float)
    for name, numerator in [("undertrial_share", "undertrial_prisoners"), ("female_share", "female_prisoners"),
                            ("age_18_30_share", "age_18_30_count"), ("illiterate_share", "illiterate_count")]:
        features[name] = counts[numerator].astype(float) / counts.total_prisoners.astype(float)
    validate_features(features)
    lineage = counts[META + ["population_source_record", "capacity_source_record"]].copy()
    for name, source in [("age_source_records", age), ("education_source_records", education)]:
        ids = source.groupby(KEYS).source_record.apply(lambda s: json.dumps(sorted(int(v) for v in s)))
        lineage[name] = ids.reindex(pd.MultiIndex.from_frame(lineage[KEYS])).to_numpy()
    count_columns = META + fields + ["age_18_30_count", "illiterate_count"]
    return counts[count_columns], features, lineage


def fit_parameters(features, fit_profile_ids=None):
    validate_features(features)
    if fit_profile_ids is None:
        fit = features.copy()
        scope = "full selected cohort for descriptive unsupervised analysis; no held-out evaluation"
    else:
        requested = list(fit_profile_ids)
        if len(set(requested)) != len(requested) or not set(requested).issubset(set(features.profile_id)):
            raise ValueError("Fit IDs must be unique members of the supplied profiles.")
        fit = features[features.profile_id.isin(requested)].copy()
        scope = "explicit fit subset; other rows are transformed without refitting"
    if len(fit) < 3:
        raise ValueError("At least three fit profiles are required for tertile cut points.")
    fit = fit.sort_values("profile_id")
    scaler = StandardScaler(with_mean=True, with_std=True).fit(fit[FEATURES])
    bins = {"occupancy_ratio": {"method": "fixed occupancy bands", "cutpoints": [1.0, 1.5],
                                "labels": ["within_capacity", "over_100_to_150pct", "over_150pct"]}}
    for feature in FEATURES[1:]:
        cuts = np.quantile(fit[feature].to_numpy(dtype=float), [1 / 3, 2 / 3], method="linear")
        if cuts[0] >= cuts[1]:
            raise ValueError(f"Tied tertile cut points for {feature}; choose and document another rule explicitly.")
        bins[feature] = {"method": "cohort tertiles", "quantiles": [1 / 3, 2 / 3],
                         "quantile_method": "linear", "cutpoints": cuts.tolist(),
                         "labels": ["lower_tertile", "middle_tertile", "upper_tertile"]}
    parameters = {"feature_order": list(FEATURES), "fit_scope": scope, "fit_rows": len(fit),
                  "fit_profile_ids": fit.profile_id.tolist(), "sklearn_version": sklearn.__version__,
                  "scaler": {"method": "StandardScaler", "with_mean": True, "with_std": True,
                             "ddof": 0, "mean": scaler.mean_.tolist(), "variance": scaler.var_.tolist(),
                             "scale": scaler.scale_.tolist(), "constant_scale_rule": "scale=1 for zero variance"},
                  "discretization": bins,
                  "boundary_rule": "x <= first cut: first label; first < x <= second: second label; x > second: third label",
                  "outlier_policy": "retained; no clipping, winsorization or log transformation"}
    return parameters


def scale_profiles(features, parameters):
    validate_features(features)
    if parameters["feature_order"] != FEATURES:
        raise ValueError("Scaler feature order differs from the profile contract.")
    mean = np.asarray(parameters["scaler"]["mean"], dtype=float)
    scale = np.asarray(parameters["scaler"]["scale"], dtype=float)
    if mean.shape != (len(FEATURES),) or scale.shape != mean.shape or not np.isfinite(mean).all() or not (np.isfinite(scale) & (scale > 0)).all():
        raise ValueError("Invalid saved scaler parameters.")
    values = (features[FEATURES].to_numpy(dtype=float) - mean) / scale
    if not np.isfinite(values).all():
        raise ValueError("Standardization produced nonfinite values.")
    result = features[["profile_id"]].copy()
    result[FEATURES] = values
    return result


def discretize_profiles(features, parameters):
    validate_features(features)
    discrete = features[META].copy()
    for feature in FEATURES:
        spec = parameters["discretization"][feature]
        cuts = np.asarray(spec["cutpoints"], dtype=float)
        if len(cuts) != 2 or not np.isfinite(cuts).all() or cuts[0] >= cuts[1] or len(spec["labels"]) != 3:
            raise ValueError(f"Invalid saved bin specification: {feature}.")
        # Equality belongs to the lower interval; tied values are never split by rank.
        positions = np.searchsorted(cuts, features[feature].to_numpy(dtype=float), side="left")
        discrete[feature + "_bin"] = [spec["labels"][i] for i in positions]
    return discrete


def encode_transactions(discrete, parameters):
    require_keys(discrete, ["profile_id"], "transactions")
    vocabulary = sorted(f"{feature}={label}" for feature in FEATURES
                        for label in parameters["discretization"][feature]["labels"])
    transactions = []
    for row in discrete.to_dict("records"):
        items = sorted(f"{feature}={row[feature + '_bin']}" for feature in FEATURES)
        if len(items) != len(set(items)) or not set(items).issubset(vocabulary):
            raise ValueError("Duplicate or unknown transaction items.")
        transactions.append({"profile_id": row["profile_id"], "state": str(row["state"]),
                             "year": int(row["year"]), "items": items})
    encoded = pd.DataFrame([[item in t["items"] for item in vocabulary] for t in transactions],
                           columns=vocabulary, dtype=bool)
    encoded.insert(0, "profile_id", discrete.profile_id.to_numpy())
    if not encoded[vocabulary].sum(axis=1).eq(len(FEATURES)).all():
        raise AssertionError("Each profile must contribute exactly one item per feature.")
    return transactions, encoded, vocabulary


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n")


def spark_struct(fields):
    return {"type": "struct", "fields": [{"name": name, "type": dtype, "nullable": False, "metadata": {}}
                                          for name, dtype in fields]}


def run_transformation(root):
    root = Path(root).resolve()
    selected = root / "data/processed/selected"
    output = root / "data/processed/transformed"
    reports = root / "results/tables/transformation"
    inputs = []
    for folder, manifest in [("data/raw", "results/tables/dataset_inventory.json"),
                             ("data/processed/cleaned", "results/tables/cleaning/cleaned_manifest.json"),
                             ("data/processed/selected", "results/tables/selection/selected_manifest.json")]:
        for item in json.loads((root / manifest).read_text()):
            path = root / folder / item["file"]
            if sha256(path) != item["sha256"]:
                raise ValueError(f"Upstream file differs from its recorded manifest: {path.relative_to(root)}.")
            inputs.append({"file": path.relative_to(root).as_posix(), "sha256": item["sha256"]})
    selected_manifest = json.loads((root / "results/tables/selection/selected_manifest.json").read_text())
    specs = {s["file"]: s for s in selected_manifest}
    contract = json.loads((root / "results/tables/selection/feature_contract.json").read_text())
    if [item["feature"] for item in contract] != FEATURES:
        raise ValueError("Selected feature contract differs from transformation implementation.")
    load = lambda name: pd.read_csv(selected / name, dtype=specs[name]["dtypes"])
    counts, features, lineage = construct_profiles(load("profile_base_counts.csv"),
                                                 load("profile_age_counts.csv"), load("profile_education_counts.csv"))
    parameters = fit_parameters(features)
    parameters["feature_definitions"] = contract
    scaled = scale_profiles(features, parameters)
    # Confirm replayed JSON parameters use the same convention as StandardScaler.
    reference_scaler = StandardScaler().fit(features.sort_values("profile_id")[FEATURES])
    if not np.allclose(scaled[FEATURES], reference_scaler.transform(features[FEATURES]), atol=1e-12, rtol=0):
        raise AssertionError("Saved scaler parameters do not reproduce scikit-learn output.")
    discrete = discretize_profiles(features, parameters)
    transactions, encoded, vocabulary = encode_transactions(discrete, parameters)
    for directory in [output, reports]:
        directory.mkdir(parents=True, exist_ok=True)
    frames = {"profile_counts.csv": counts, "profile_features.csv": features,
              "clustering_features.csv": scaled, "discretized_profiles.csv": discrete,
              "transactions_onehot.csv": encoded}
    for filename, frame in frames.items():
        frame.to_csv(output / filename, index=False, float_format="%.17g")
    write_jsonl(output / "transactions.jsonl", transactions)
    spark_rows = [{"profile_id": row["profile_id"], "features": [float(row[f]) for f in FEATURES]}
                  for row in scaled.to_dict("records")]
    write_jsonl(output / "spark_profiles.jsonl", spark_rows)
    reloaded_transactions = [json.loads(line) for line in (output / "transactions.jsonl").read_text().splitlines()]
    reloaded_vectors = [json.loads(line) for line in (output / "spark_profiles.jsonl").read_text().splitlines()]
    if reloaded_transactions != transactions or reloaded_vectors != spark_rows:
        raise AssertionError("JSON export changed the transaction or feature representation.")
    lineage.to_csv(reports / "profile_lineage.csv", index=False)
    (reports / "parameters.json").write_text(json.dumps(parameters, indent=2, allow_nan=False) + "\n")
    (reports / "input_provenance.json").write_text(json.dumps(inputs, indent=2) + "\n")
    scaler = parameters["scaler"]
    pd.DataFrame({"feature": FEATURES, "mean": scaler["mean"], "variance_ddof0": scaler["variance"],
                  "scale": scaler["scale"], "fit_rows": parameters["fit_rows"]}).to_csv(reports / "scaling_parameters.csv", index=False, float_format="%.17g")
    bin_rows = [{"feature": f, "method": s["method"], "first_cut": s["cutpoints"][0], "second_cut": s["cutpoints"][1],
                 "labels": ";".join(s["labels"]), "comparison": "lower intervals include the right boundary"}
                for f, s in parameters["discretization"].items()]
    pd.DataFrame(bin_rows).to_csv(reports / "discretization_parameters.csv", index=False, float_format="%.17g")
    array = lambda dtype: {"type": "array", "elementType": dtype, "containsNull": False}
    spark_contract = {"feature_order": FEATURES, "preprocessing": "Read saved standardized vectors; do not refit a Spark scaler.",
                      "clustering": {"file": "spark_profiles.jsonl", "schema": spark_struct([("profile_id", "string"), ("features", array("double"))]), "vector_length": len(FEATURES)},
                      "association": {"file": "transactions.jsonl", "schema": spark_struct([("profile_id", "string"), ("state", "string"), ("year", "long"), ("items", array("string"))]), "items_column": "items"},
                      "runtime_status": "Spark input prepared and JSON round-trip verified; no PySpark execution yet."}
    (reports / "spark_input_contract.json").write_text(json.dumps(spark_contract, indent=2) + "\n")
    schemas = [{"file": name, "rows": len(frame), "format": "csv", "dtypes": {c: str(frame[c].dtype) for c in frame},
                "sha256": sha256(output / name)} for name, frame in frames.items()]
    schemas += [{"file": name, "rows": len(features), "format": "jsonl", "sha256": sha256(output / name)}
                for name in ["transactions.jsonl", "spark_profiles.jsonl"]]
    (reports / "transformed_manifest.json").write_text(json.dumps(schemas, indent=2) + "\n")
    if any(sha256(root / item["file"]) != item["sha256"] for item in inputs):
        raise AssertionError("Transformation modified an upstream file.")
    summary = {"profiles": len(features), "numeric_features": len(FEATURES), "transactions": len(transactions),
               "items_per_transaction": len(FEATURES), "declared_items": len(vocabulary),
               "observed_items": sum(bool(encoded[c].any()) for c in vocabulary),
               "onehot_shape": [len(encoded), len(vocabulary)], "onehot_true_cells": int(encoded[vocabulary].sum().sum()),
               "fit_rows": parameters["fit_rows"], "upstream_files_verified": len(inputs),
               "raw_cleaned_selected_unchanged": True, "pyspark_executed": False, "mining_or_clustering_executed": False}
    (reports / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def load_transformed(root, filename):
    root = Path(root)
    manifest = json.loads((root / "results/tables/transformation/transformed_manifest.json").read_text())
    spec = next(s for s in manifest if s["file"] == filename)
    path = root / "data/processed/transformed" / filename
    if sha256(path) != spec["sha256"]:
        raise ValueError("Transformed output differs from its manifest.")
    if spec["format"] == "jsonl":
        return [json.loads(line) for line in path.read_text().splitlines()]
    return pd.read_csv(path, dtype=spec["dtypes"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    print(json.dumps(run_transformation(parser.parse_args().root), indent=2))


if __name__ == "__main__":
    main()
