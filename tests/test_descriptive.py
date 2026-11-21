"""Validate statistical conventions, aggregation scopes and covered populations."""

import json
from pathlib import Path
import statistics
import unittest

import numpy as np
import pandas as pd
from scipy import stats

from src.analytics.descriptive import numeric_statistics, recidivism_tables, safe_ratio, yearly_population
from src.preprocessing.cleaning import sha256
from src.preprocessing.transformation import FEATURES, load_transformed


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/tables/descriptive"


class DescriptiveRulesTest(unittest.TestCase):
    def test_statistics_match_independent_reference_formulas(self):
        values = [1, 2, 2, 4, 6]
        result = numeric_statistics(pd.Series(values))
        self.assertEqual(result["n"], 5)
        self.assertEqual(result["mean"], statistics.mean(values))
        self.assertEqual(result["median"], statistics.median(values))
        self.assertEqual(result["sample_variance"], statistics.variance(values))
        self.assertEqual(result["sample_std"], statistics.stdev(values))
        self.assertEqual((result["q1"], result["q3"], result["iqr"]), (2, 4, 2))
        self.assertEqual(json.loads(result["mode_values"]), [2])
        self.assertAlmostEqual(result["skewness"], stats.skew(values, bias=False), places=12)
        self.assertAlmostEqual(result["excess_kurtosis"], stats.kurtosis(values, bias=False, fisher=True), places=12)

    def test_modes_and_undefined_constant_shapes_are_explicit(self):
        multiple = numeric_statistics(pd.Series([1, 1, 2, 2, 3]))
        self.assertEqual(json.loads(multiple["mode_values"]), [1, 2])
        unique = numeric_statistics(pd.Series([1, 2, 3, 4]))
        self.assertEqual(unique["mode_status"], "all_values_unique")
        constant = numeric_statistics(pd.Series([0, 0, 0, 0]))
        self.assertEqual(constant["zeros"], 4)
        self.assertEqual(constant["sample_variance"], 0)
        self.assertTrue(np.isnan(constant["skewness"]))
        self.assertTrue(np.isnan(constant["excess_kurtosis"]))

    def test_missing_small_samples_and_zero_denominators_stay_undefined(self):
        singleton = numeric_statistics(pd.Series([5.0, np.nan]))
        self.assertEqual(singleton["missing"], 1)
        self.assertTrue(np.isnan(singleton["sample_variance"]))
        empty = numeric_statistics(pd.Series([np.nan]))
        self.assertEqual(empty["n"], 0)
        self.assertTrue(np.isnan(empty["mean"]))
        result = safe_ratio(pd.Series([0, 1, 1]), pd.Series([0, 0, 2]))
        self.assertTrue(result.iloc[:2].isna().all())
        self.assertEqual(result.iloc[2], 0.5)

    def test_pooled_ratios_are_not_unweighted_state_means(self):
        frame = pd.DataFrame({"state": ["A", "B"], "year": [2001, 2001], "total_prisoners": [1, 90],
                              "total_capacity": [1, 100], "convicts": [1, 90], "under_trial": [0, 0],
                              "detenues": [0, 0], "others": [0, 0], "female_prisoners": [0, 0],
                              "occupancy_ratio": [1.0, 0.9]})
        result = yearly_population(frame, "test").iloc[0]
        self.assertAlmostEqual(result.occupancy_ratio_pooled, 91 / 101)
        self.assertAlmostEqual(result.occupancy_ratio_mean_state, 0.95)
        self.assertNotEqual(result.occupancy_ratio_pooled, result.occupancy_ratio_mean_state)

    def test_invalid_admission_pairs_do_not_become_percentages(self):
        frame = pd.DataFrame({"state": ["A", "B"], "year": [2001, 2001], "source_record": [2, 3],
                              "convicts_admitted": [0, 100], "habitual_offenders": [19, 10]})
        detail, annual = recidivism_tables(frame)
        self.assertFalse(detail.loc[0, "count_pair_valid"])
        self.assertTrue(pd.isna(detail.loc[0, "habitual_share_of_admissions"]))
        self.assertEqual(annual.iloc[0].reported_habitual_offenders, 29)
        self.assertEqual(annual.iloc[0].ratio_cohort_habitual, 10)
        self.assertAlmostEqual(annual.iloc[0].habitual_share_of_admissions_pooled, 0.1)


class DescriptiveArtifactsTest(unittest.TestCase):
    def test_annual_totals_reconcile_without_subtotal_duplication(self):
        years = pd.read_csv(OUTPUT / "year_summary_available.csv")
        reference = pd.read_csv(ROOT / "data/processed/selected/population_capacity_reference.csv")
        expected = reference.groupby("year")["total_prisoners"].sum()
        self.assertEqual(years.prisoners.tolist(), expected.tolist())
        self.assertTrue(years[["convicts", "undertrials", "detenues", "others"]].sum(axis=1).eq(years.prisoners).all())
        np.testing.assert_allclose(years.occupancy_ratio_pooled, years.prisoners / years.capacity, rtol=1e-14)

    def test_balanced_panel_uses_the_same_states_in_every_year(self):
        reference = pd.read_csv(OUTPUT / "state_year_totals.csv")
        complete = reference.groupby("state").year.nunique().eq(13)
        stable = reference[reference.state.isin(complete[complete].index)]
        summary = pd.read_csv(OUTPUT / "year_summary_balanced.csv")
        self.assertEqual(stable.state.nunique(), 34)
        self.assertEqual(len(stable), 442)
        self.assertTrue(summary.states.eq(34).all())
        self.assertEqual(summary.prisoners.tolist(), stable.groupby("year").total_prisoners.sum().tolist())

    def test_demographic_partitions_and_denominators_match_their_coverage(self):
        detail = pd.read_csv(OUTPUT / "demographic_state_year.csv")
        annual = pd.read_csv(OUTPUT / "demographic_year.csv")
        for _, group in detail.groupby(["source", "dimension", "state", "year"]):
            self.assertEqual(group.prisoners.sum(), group.total_prisoners.iloc[0])
        for _, group in annual.groupby(["source", "dimension", "year"]):
            self.assertEqual(group.prisoners.sum(), group.covered_prisoners.iloc[0])
            self.assertAlmostEqual(group.share_of_covered_population.sum(), 1.0)
        age2013 = annual[annual.source.eq("Age_group.csv") & annual.dimension.eq("age_group") & annual.year.eq(2013)]
        self.assertEqual(age2013.covered_states.unique().tolist(), [34])
        self.assertLess(age2013.population_coverage_fraction.iloc[0], 1)
        for name, dimensions, denominator, share in [
            ("demographic_status_year.csv", ["source", "dimension", "year", "legal_status"], "status_population", "share_within_status"),
            ("demographic_gender_year.csv", ["source", "dimension", "year", "gender"], "gender_population", "share_within_gender"),
        ]:
            conditional = pd.read_csv(OUTPUT / name)
            for _, group in conditional.groupby(dimensions):
                self.assertEqual(group.prisoners.sum(), group[denominator].iloc[0])
                if group[denominator].iloc[0] > 0:
                    self.assertAlmostEqual(group[share].sum(), 1.0)

    def test_record_frequencies_are_native_records_not_prisoner_shares(self):
        frequencies = pd.read_csv(OUTPUT / "categorical_record_frequencies.csv")
        for _, group in frequencies.groupby(["source", "field"]):
            self.assertEqual(group.native_records.sum(), group.denominator_records.iloc[0])
            self.assertAlmostEqual(group.record_fraction.sum(), 1.0)

    def test_correlations_match_direct_profile_calculations(self):
        profiles = load_transformed(ROOT, "profile_features.csv")
        correlations = pd.read_csv(OUTPUT / "correlations.csv")
        pooled = correlations[correlations.scope.eq("selected_profiles_pooled")]
        for method in ["pearson", "spearman"]:
            matrix = pooled[pooled.method.eq(method)].pivot(index="left", columns="right", values="correlation").reindex(index=FEATURES, columns=FEATURES)
            np.testing.assert_allclose(matrix, profiles[FEATURES].corr(method=method), atol=1e-14, rtol=0)
        self.assertTrue(pooled.paired_n.eq(437).all())

    def test_crime_sources_keep_separate_composition_denominators(self):
        crime = pd.read_csv(OUTPUT / "crime_year.csv")
        for _, group in crime.groupby(["source", "year"]):
            self.assertEqual(group.reported_count.sum(), group.within_source_total.iloc[0])
            self.assertAlmostEqual(group.share_within_source_counts.sum(), 1.0)

    def test_manifests_and_upstream_data_are_unchanged(self):
        for item in json.loads((OUTPUT / "input_provenance.json").read_text()):
            self.assertEqual(sha256(ROOT / item["file"]), item["sha256"])
        for item in json.loads((OUTPUT / "table_manifest.json").read_text()):
            self.assertEqual(sha256(OUTPUT / item["file"]), item["sha256"])


if __name__ == "__main__":
    unittest.main()
