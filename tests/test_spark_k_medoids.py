"""Validate distributed PAM kernels and executed comparison outputs."""
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.metrics import adjusted_rand_score

from src.mining.k_medoids import load_profiles, swap_costs
from src.mining.spark_k_medoids import partition_assignments, partition_swap_costs

ROOT=Path(__file__).resolve().parents[1]


class SparkKMedoidsTest(unittest.TestCase):
    def test_partition_aggregation_matches_all_direct_swap_costs(self):
        x=np.random.default_rng(10).normal(size=(11,5))
        d=cdist(x,x,metric='cityblock');medoids=np.array([1,6,9])
        parts=[list(enumerate(d))[:4],list(enumerate(d))[4:]]
        outputs=[next(partition_swap_costs(iter(part),medoids,len(x))) for part in parts]
        objective=sum(v[0] for v in outputs)
        costs=sum((v[1] for v in outputs),np.zeros((3,8)))
        _,expected=swap_costs(d,medoids)
        np.testing.assert_allclose(costs,expected,atol=1e-12,rtol=0)
        self.assertAlmostEqual(objective,d[:,medoids].min(axis=1).sum())

    def test_assignment_ties_let_each_medoid_represent_itself(self):
        d=np.zeros((4,4))
        result=list(partition_assignments(iter(enumerate(d)),[0,2]))
        self.assertEqual(result[0],(0,0,0))
        self.assertEqual(result[2],(2,1,0))

    def test_saved_results_match_phase7_real_representatives_and_distances(self):
        raw,scaled,x=load_profiles(ROOT)
        assignments=pd.read_csv(ROOT/'results/tables/spark_k_medoids/cluster_assignments.csv')
        previous=pd.read_csv(ROOT/'results/tables/k_medoids/cluster_assignments.csv').set_index('profile_id')
        self.assertEqual(assignments.profile_id.tolist(),raw.profile_id.tolist())
        self.assertEqual(adjusted_rand_score(assignments.cluster,previous.loc[assignments.profile_id].cluster),1)
        self.assertEqual(assignments.medoid_profile_id.tolist(),previous.loc[assignments.profile_id].medoid_profile_id.tolist())
        np.testing.assert_allclose(assignments.distance_to_medoid,previous.loc[assignments.profile_id].distance_to_medoid,atol=1e-12,rtol=0)
        equality=pd.read_csv(ROOT/'results/tables/spark_k_medoids/equivalence.csv')
        self.assertEqual(len(equality),2)
        self.assertTrue(equality.equivalent.all())
        self.assertTrue(equality.max_candidate_swap_cost_difference.lt(1e-9).all())

    def test_benchmark_has_three_repetitions_and_correct_ratio(self):
        base=ROOT/'results/benchmarks/spark_k_medoids'
        runs=pd.read_csv(base/'timing_runs.csv');summary=pd.read_csv(base/'timing_summary.csv').iloc[0]
        self.assertEqual(len(runs[runs.warmup]),2)
        self.assertEqual(len(runs[~runs.warmup]),6)
        measured=runs[~runs.warmup]
        py=measured[measured.engine.eq('python')].seconds
        sp=measured[measured.engine.eq('spark')].seconds
        self.assertAlmostEqual(summary.speedup_python_over_spark,py.median()/sp.median())
        self.assertTrue(runs.seconds.gt(0).all())
        self.assertTrue((runs.sampled_peak_rss_mib>=runs.rss_baseline_mib).all())

    def test_notebook_executes_and_generates_its_own_plots(self):
        nb=json.loads((ROOT/'notebooks/08_PySpark_KMedoids.ipynb').read_text())
        cells=[c for c in nb['cells'] if c['cell_type']=='code']
        self.assertTrue(all(c['execution_count'] is not None for c in cells))
        self.assertEqual(sum('image/png' in o.get('data',{}) for c in cells for o in c.get('outputs',[])),2)
        self.assertFalse(any(o.get('output_type')=='error' for c in cells for o in c.get('outputs',[])))


if __name__=='__main__':unittest.main()
