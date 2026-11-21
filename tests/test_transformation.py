"""Check aggregation, replayed parameters, boundaries and equivalent encodings."""

import copy
from fractions import Fraction
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.preprocessing.transformation import (
    FEATURES, construct_profiles, discretize_profiles, encode_transactions,
    fit_parameters, load_transformed, scale_profiles, validate_features,
)


ROOT = Path(__file__).resolve().parents[1]


class TransformationRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.features = load_transformed(ROOT, "profile_features.csv")
        cls.parameters = json.loads((ROOT / "results/tables/transformation/parameters.json").read_text())

    def test_parameters_reproduce_standard_scaler(self):
        transformed = scale_profiles(self.features, self.parameters)
        reference = StandardScaler().fit(self.features.sort_values("profile_id")[FEATURES])
        np.testing.assert_allclose(transformed[FEATURES], reference.transform(self.features[FEATURES]), atol=1e-12, rtol=0)
        np.testing.assert_allclose(transformed[FEATURES].mean(), 0, atol=1e-12, rtol=0)
        np.testing.assert_allclose(transformed[FEATURES].std(ddof=0), 1, atol=1e-12, rtol=0)

    def test_explicit_fit_subset_does_not_use_other_rows(self):
        ids = self.features.profile_id.iloc[::3].tolist()
        fitted = fit_parameters(self.features, ids)
        subset = self.features[self.features.profile_id.isin(ids)].sort_values("profile_id")
        self.assertEqual(set(fitted["fit_profile_ids"]), set(ids))
        np.testing.assert_allclose(fitted["scaler"]["mean"], subset[FEATURES].mean(), atol=1e-12, rtol=0)
        for feature in FEATURES[1:]:
            expected = np.quantile(subset[feature], [1 / 3, 2 / 3], method="linear")
            np.testing.assert_array_equal(expected, fitted["discretization"][feature]["cutpoints"])
        before = copy.deepcopy(fitted)
        scale_profiles(self.features, fitted)
        discretize_profiles(self.features, fitted)
        self.assertEqual(fitted, before)

    def test_exact_cut_boundaries_belong_to_lower_bin(self):
        for feature in FEATURES:
            spec = self.parameters["discretization"][feature]
            cuts = spec["cutpoints"]
            probe = self.features.iloc[:3].copy()
            probe[feature] = [cuts[0], cuts[1], np.nextafter(cuts[1], np.inf)]
            got = discretize_profiles(probe, self.parameters)[feature + "_bin"].tolist()
            self.assertEqual(got, spec["labels"])

    def test_invalid_features_and_reordered_scaler_are_rejected(self):
        invalid = self.features.copy()
        invalid.loc[0, "female_share"] = 1.01
        with self.assertRaises(ValueError):
            validate_features(invalid)
        invalid.loc[0, "female_share"] = np.nan
        with self.assertRaises(ValueError):
            validate_features(invalid)
        params = copy.deepcopy(self.parameters)
        params["feature_order"] = FEATURES[::-1]
        with self.assertRaises(ValueError):
            scale_profiles(self.features, params)

    def test_missing_or_duplicate_marginal_records_fail(self):
        folder = ROOT / "data/processed/selected"
        base = pd.read_csv(folder / "profile_base_counts.csv")
        age = pd.read_csv(folder / "profile_age_counts.csv")
        education = pd.read_csv(folder / "profile_education_counts.csv")
        with self.assertRaises(ValueError):
            construct_profiles(base, age.iloc[1:], education)
        with self.assertRaises(ValueError):
            construct_profiles(base, pd.concat([age, age.iloc[:1]]), education)
        age.loc[0, "age_18_30"] = np.nan
        with self.assertRaises(ValueError):
            construct_profiles(base, age, education)

    def test_zero_denominator_is_not_epsilon_imputed(self):
        folder = ROOT / "data/processed/selected"
        base = pd.read_csv(folder / "profile_base_counts.csv")
        base.loc[0, "total_prisoners"] = 0
        with self.assertRaises(ValueError):
            construct_profiles(base, pd.read_csv(folder / "profile_age_counts.csv"),
                               pd.read_csv(folder / "profile_education_counts.csv"))

    def test_equal_transactions_keep_separate_profile_observations(self):
        original = load_transformed(ROOT, "discretized_profiles.csv").iloc[:1]
        duplicate = original.copy()
        duplicate["profile_id"] = "boundary-test-second-observation"
        rows = pd.concat([original, duplicate], ignore_index=True)
        transactions, encoded, vocabulary = encode_transactions(rows, self.parameters)
        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0]["items"], transactions[1]["items"])
        self.assertTrue(encoded[vocabulary].sum(axis=1).eq(5).all())


class TransformedArtifactsTest(unittest.TestCase):
    def test_numerators_and_ratios_match_independent_source_sums(self):
        counts = load_transformed(ROOT, "profile_counts.csv").set_index(["state", "year"])
        features = load_transformed(ROOT, "profile_features.csv").set_index(["state", "year"])
        source = ROOT / "data/processed/selected"
        age = pd.read_csv(source / "profile_age_counts.csv")
        education = pd.read_csv(source / "profile_education_counts.csv")
        adult = {}
        for row in age.to_dict("records"):
            key = (row["state"], row["year"])
            adult[key] = adult.get(key, 0) + row["age_18_30"]
        illiterate = {}
        for row in education.to_dict("records"):
            if row["education"] == "Illiterate":
                key = (row["state"], row["year"])
                illiterate[key] = illiterate.get(key, 0) + sum(row[c] for c in ["convicts", "under_trial", "detenues", "others"])
        for key, row in counts.iterrows():
            self.assertEqual(row.age_18_30_count, adult[key])
            self.assertEqual(row.illiterate_count, illiterate[key])
            ratios = {"occupancy_ratio": (row.total_prisoners, row.total_capacity),
                      "undertrial_share": (row.undertrial_prisoners, row.total_prisoners),
                      "female_share": (row.female_prisoners, row.total_prisoners),
                      "age_18_30_share": (adult[key], row.total_prisoners),
                      "illiterate_share": (illiterate[key], row.total_prisoners)}
            for feature, (numerator, denominator) in ratios.items():
                self.assertAlmostEqual(features.at[key, feature], float(Fraction(int(numerator), int(denominator))), places=14)

    def test_python_and_spark_representations_match(self):
        vectors = load_transformed(ROOT, "clustering_features.csv")
        spark = load_transformed(ROOT, "spark_profiles.jsonl")
        self.assertEqual(vectors.profile_id.tolist(), [r["profile_id"] for r in spark])
        np.testing.assert_array_equal(vectors[FEATURES].to_numpy(), np.array([r["features"] for r in spark]))
        transactions = load_transformed(ROOT, "transactions.jsonl")
        onehot = load_transformed(ROOT, "transactions_onehot.csv")
        self.assertEqual(onehot.profile_id.tolist(), [r["profile_id"] for r in transactions])
        vocabulary = [c for c in onehot if c != "profile_id"]
        self.assertTrue(all(onehot[c].dtype == bool for c in vocabulary))
        for i, row in enumerate(transactions):
            self.assertEqual(row["items"], sorted(c for c in vocabulary if onehot.at[i, c]))
            self.assertEqual(len({item.split("=")[0] for item in row["items"]}), 5)
            self.assertEqual({item.split("=")[0] for item in row["items"]}, set(FEATURES))

    def test_all_outputs_preserve_the_selected_cohort(self):
        selected = pd.read_csv(ROOT / "data/processed/selected/profile_base_counts.csv")
        expected = set(selected.state + "|" + selected.year.astype(str))
        manifest = json.loads((ROOT / "results/tables/transformation/transformed_manifest.json").read_text())
        self.assertEqual(len(expected), 437)
        for item in manifest:
            data = load_transformed(ROOT, item["file"])
            ids = data.profile_id.tolist() if isinstance(data, pd.DataFrame) else [r["profile_id"] for r in data]
            self.assertEqual(len(ids), 437)
            self.assertEqual(set(ids), expected)
            self.assertEqual(len(set(ids)), len(ids))


if __name__ == "__main__":
    unittest.main()
