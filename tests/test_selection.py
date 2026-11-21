"""Check observation units, denominator safety and selected-source lineage."""

import json
from pathlib import Path
import unittest

import pandas as pd

from src.preprocessing.cleaning import sha256
from src.preprocessing.selection import (CAPACITY, POPULATION, checked_join,
                                         load_descriptive_view, marginal_audit)


ROOT = Path(__file__).resolve().parents[1]


class SelectionRulesTest(unittest.TestCase):
    def test_join_refuses_row_multiplication(self):
        left = pd.DataFrame({"state": ["A", "A"], "year": [2001, 2001], "x": [1, 2]})
        right = pd.DataFrame({"state": ["A", "A"], "year": [2001, 2001], "y": [3, 4]})
        with self.assertRaises(pd.errors.MergeError):
            checked_join(left, right, ["state", "year"], "one_to_one")

    def test_join_rejects_missing_keys(self):
        left = pd.DataFrame({"state": [None], "year": [2001]})
        with self.assertRaises(ValueError):
            checked_join(left, left, ["state", "year"], "one_to_one")

    def test_marginal_does_not_hide_missing_values_in_sum(self):
        age = pd.read_csv(ROOT / "data/processed/cleaned/Age_group.csv").rename(columns={"state_name": "state"})
        ref = pd.read_csv(ROOT / "data/processed/selected/population_capacity_reference.csv")
        audit = marginal_audit(age, ref, "Age_group.csv")
        missing = audit[audit.state.eq("West Bengal") & audit.year.eq(2013)].iloc[0]
        self.assertEqual(missing.missing_measure_cells, 1)
        self.assertFalse(missing.compatible)
        swapped_status = audit[audit.state.eq("Tripura") & audit.year.eq(2004)].iloc[0]
        self.assertFalse(swapped_status.compatible)
        self.assertIn("male_detenues", swapped_status.mismatch_fields)

    def test_descriptive_loader_excludes_totals_and_bad_groups(self):
        view = load_descriptive_view(ROOT, "Education.csv")
        self.assertTrue(view.scope.eq("detail").all())
        self.assertTrue(view.population_compatible.all())
        self.assertTrue(view.category_grid_complete.all())
        self.assertTrue(view.analysis_eligible.all())
        training = load_descriptive_view(ROOT, "Vocational_training.csv")
        self.assertFalse(training.ambiguous_key.any())
        self.assertFalse(training.missing_numeric_cells.gt(0).any())


class SelectedArtifactsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = ROOT / "results/tables/selection"
        cls.selected = ROOT / "data/processed/selected"

    def test_reference_and_profile_cohort_are_unique_and_accounted_for(self):
        reference = pd.read_csv(self.selected / "population_capacity_reference.csv")
        profile = pd.read_csv(self.selected / "profile_base_counts.csv")
        exclusions = pd.read_csv(self.reports / "profile_exclusions.csv")
        self.assertEqual(len(reference), 447)
        self.assertEqual(len(profile), 437)
        self.assertEqual(len(exclusions), 10)
        for frame in [reference, profile, exclusions]:
            self.assertFalse(frame.duplicated(["state", "year"]).any())
        self.assertTrue(profile.total_prisoners.gt(0).all())
        self.assertTrue(profile.total_capacity.gt(0).all())
        self.assertEqual(len(exclusions[~exclusions.positive_denominators]), 4)
        keys = lambda d: set(zip(d.state, d.year))
        self.assertEqual(keys(reference), keys(profile) | keys(exclusions))
        self.assertFalse(keys(profile) & keys(exclusions))

    def test_native_profile_records_match_cleaned_sources(self):
        for name, original_name, field in [
            ("profile_age_counts.csv", "Age_group.csv", "age_18_30"),
            ("profile_education_counts.csv", "Education.csv", "convicts"),
        ]:
            original = pd.read_csv(ROOT / "data/processed/cleaned" / original_name).set_index("source_record")
            selected = pd.read_csv(self.selected / name)
            self.assertTrue((selected[field].to_numpy() == original.loc[selected.source_record, field].to_numpy()).all())
            self.assertFalse(selected.source_record.duplicated().any())
        for filename, count in [("profile_age_counts.csv", 16), ("profile_education_counts.csv", 12)]:
            selected = pd.read_csv(self.selected / filename)
            self.assertTrue(selected.groupby(["state", "year"]).size().eq(count).all())

    def test_profile_counts_trace_to_verified_totals(self):
        selected = pd.read_csv(self.selected / "profile_base_counts.csv")
        pop = pd.read_csv(ROOT / "data/processed/cleaned" / POPULATION).set_index("source_record")
        cap = pd.read_csv(ROOT / "data/processed/cleaned" / CAPACITY).set_index("source_record")
        self.assertTrue(pop.loc[selected.population_source_record, "Jail_Type"].eq("Total").all())
        self.assertTrue(cap.loc[selected.capacity_source_record, "TYPE OF JAIL"].eq("Total").all())
        for out, source, key, column in [
            ("total_prisoners", pop, "population_source_record", "Grand_Total"),
            ("female_prisoners", pop, "population_source_record", "Total_Female"),
            ("undertrial_prisoners", pop, "population_source_record", "Total_Under_trial"),
            ("total_capacity", cap, "capacity_source_record", "Total Capacity of Inmates"),
        ]:
            self.assertTrue((selected[out].to_numpy() == source.loc[selected[key], column].to_numpy()).all())

    def test_profile_has_no_encoded_or_derived_features(self):
        selected = pd.read_csv(self.selected / "profile_base_counts.csv")
        features = json.loads((self.reports / "feature_contract.json").read_text())
        self.assertEqual(len(features), 5)
        self.assertFalse(set(f["feature"] for f in features) & set(selected.columns))
        self.assertFalse({"cluster", "target", "is_state", "state_code", "religion", "caste"} & set(selected.columns))
        self.assertTrue(selected.select_dtypes("number").drop(columns="year").mod(1).eq(0).all().all())

    def test_cleaned_and_selected_manifests_match(self):
        for directory, manifest in [
            (ROOT / "data/processed/cleaned", ROOT / "results/tables/cleaning/cleaned_manifest.json"),
            (self.selected, self.reports / "selected_manifest.json"),
        ]:
            for item in json.loads(manifest.read_text()):
                self.assertEqual(sha256(directory / item["file"]), item["sha256"])


if __name__ == "__main__":
    unittest.main()
