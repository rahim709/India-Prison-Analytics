"""Verify PAM swaps, real medoids, objective values and selection rules."""
import itertools
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.metrics import silhouette_score

from src.mining.k_medoids import (assign, build_medoids, load_profiles, pam,
                                  reference_swap_costs, swap_costs)

ROOT = Path(__file__).resolve().parents[1]


class KMedoidsTest(unittest.TestCase):
    def test_hand_checkable_solution_matches_exhaustive_optimum(self):
        x=np.array([0,1,2,10,11,12],dtype=float)[:,None]
        d=cdist(x,x,metric='cityblock')
        exact=min((d[:,list(m)].min(axis=1).sum(),m) for m in itertools.combinations(range(6),2))
        for initial in [None,[0,1],[0,5]]:
            fit=pam(d,2,initial)
            self.assertAlmostEqual(fit['cost'],4)
            self.assertAlmostEqual(fit['cost'],exact[0])
            np.testing.assert_array_equal(fit['medoids'],[1,4])
            self.assertTrue(np.all(np.diff([h['cost'] for h in fit['history']]) < 0))

    def test_all_swap_costs_match_independent_reassignment(self):
        x=np.random.default_rng(71).normal(size=(12,3))
        for metric in ['cityblock','euclidean']:
            d=cdist(x,x,metric=metric)
            for k in [1,2,5,12]:
                medoids=build_medoids(d,k)
                candidates,fast=swap_costs(d,medoids)
                expected_candidates,slow=reference_swap_costs(d,medoids)
                np.testing.assert_array_equal(candidates,expected_candidates)
                np.testing.assert_allclose(fast,slow,atol=1e-12,rtol=0)

    def test_duplicate_ties_preserve_real_representatives(self):
        d=np.zeros((5,5))
        fit=pam(d,3,[0,1,2])
        self.assertEqual(fit['cost'],0)
        np.testing.assert_array_equal(fit['labels'][fit['medoids']],range(3))
        self.assertEqual(len(set(fit['labels'])),3)
        repeated=pam(d,3,[0,1,2])
        np.testing.assert_array_equal(fit['labels'],repeated['labels'])

    def test_invalid_inputs_and_unfinished_convergence_are_rejected(self):
        for d in [np.ones((2,3)),np.array([[0,1],[2,0]]),np.array([[0,np.nan],[np.nan,0]]),-np.eye(2)]:
            with self.assertRaises(ValueError):pam(d,1)
        d=cdist(np.array([0,1,2,10,11,12])[:,None],np.array([0,1,2,10,11,12])[:,None])
        for k,initial in [(0,None),(7,None),(2,[1,1]),(2,[0,6]),(2,[.1,2.0])]:
            with self.assertRaises(ValueError):pam(d,k,initial)
        with self.assertRaises(RuntimeError):pam(d,2,[0,1],max_iter=0)

    def test_real_assignments_and_medoids_match_saved_features(self):
        raw,scaled,x=load_profiles(ROOT)
        output=ROOT/'results/tables/k_medoids'
        assignments=pd.read_csv(output/'cluster_assignments.csv')
        medoids=pd.read_csv(output/'medoids.csv').sort_values('cluster')
        self.assertEqual(assignments.profile_id.tolist(),raw.profile_id.tolist())
        positions=[int(raw.index[raw.profile_id.eq(i)][0]) for i in medoids.profile_id]
        d=cdist(x,x,metric='cityblock')
        expected=d[:,positions].min(axis=1)
        np.testing.assert_allclose(assignments.distance_to_medoid,expected,atol=1e-12)
        assigned=d[np.arange(len(d)),np.array(positions)[assignments.cluster]]
        np.testing.assert_allclose(assigned,expected,atol=1e-12)
        for row in medoids.itertuples():
            profile=raw.loc[raw.profile_id.eq(row.profile_id)].iloc[0]
            for feature in ['occupancy_ratio','undertrial_share','female_share','age_18_30_share','illiterate_share']:
                self.assertAlmostEqual(getattr(row,feature),profile[feature])
        summary=json.loads((output/'run_summary.json').read_text())
        self.assertAlmostEqual(expected.sum(),summary['objective'])
        self.assertAlmostEqual(silhouette_score(d,assignments.cluster,metric='precomputed'),summary['silhouette'])
        _,costs=reference_swap_costs(d,np.sort(positions))
        self.assertGreaterEqual(costs.min(),expected.sum()-1e-10)

    def test_saved_selection_and_sensitivity_are_complete(self):
        output=ROOT/'results/tables/k_medoids'
        comparison=pd.read_csv(output/'candidate_k_comparison.csv')
        starts=pd.read_csv(output/'initialization_runs.csv')
        summary=json.loads((output/'run_summary.json').read_text())
        self.assertEqual(len(comparison),14)
        self.assertEqual(len(starts),70)
        candidates=comparison[comparison.metric.eq('cityblock') & comparison.eligible]
        expected=candidates.sort_values(['silhouette','k'],ascending=[False,True]).iloc[0]
        self.assertEqual(summary['selected_k'],expected.k)
        self.assertGreaterEqual(expected.min_cluster_size,22)
        trace=pd.read_csv(output/'objective_trace.csv')
        self.assertTrue(np.all(np.diff(trace.cost)<0))
        self.assertAlmostEqual(trace.cost.iloc[-1],summary['objective'])
        stability=pd.read_csv(output/'state_block_stability.csv')
        self.assertEqual(len(stability),10)
        self.assertTrue(stability.retained_states.eq(28).all())
        self.assertTrue(stability.ari_on_retained_profiles.between(-1,1).all())


if __name__=='__main__':unittest.main()
