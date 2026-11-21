"""Check saved Spark execution, equivalent outputs and benchmark arithmetic."""
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from src.mining.spark_fp_growth import validate_equivalence

ROOT=Path(__file__).resolve().parents[1]


class SparkFPGrowthTest(unittest.TestCase):
    def test_comparator_rejects_incorrect_counts_and_metrics(self):
        a,b=frozenset(['a']),frozenset(['b'])
        correct=({a:3},{(a,b):(.5,.75,1.5)})
        validate_equivalence(correct,correct)
        for incorrect in [({a:2},correct[1]),(correct[0],{}),(correct[0],{(a,b):(.5,.75,2)})]:
            with self.assertRaises(AssertionError):validate_equivalence(incorrect,correct)

    def test_all_saved_itemsets_and_rules_match_frozen_python_results(self):
        output=ROOT/'results/tables/spark_fp_growth'
        table=pd.read_csv(output/'equivalence.csv')
        self.assertEqual(len(table),12)
        self.assertTrue(table.equivalent.all())
        for row in table.itertuples():
            label=f's{row.min_support:.2f}_c{row.min_confidence:.2f}'.replace('.','p')
            actual=pd.read_csv(output/f'itemsets_{label}.csv')
            py_label=f'{row.min_support:.2f}'.replace('.','p')
            expected=pd.read_csv(ROOT/f'results/tables/fp_growth/itemsets_s{py_label}.csv')
            aset={frozenset(json.loads(r.items)):r.support_count for r in actual.itertuples()}
            eset={frozenset(json.loads(r.items)):r.support_count for r in expected.itertuples()}
            self.assertEqual(aset,eset)
            arules=pd.read_csv(output/f'rules_{label}.csv')
            erules=pd.read_csv(ROOT/f'results/tables/fp_growth/rules_s{py_label}_c{row.min_confidence:.2f}.csv')
            erules=erules[erules.consequent_length.eq(1)]
            def mapping(frame):
                return {(frozenset(json.loads(r.antecedents)),frozenset(json.loads(r.consequents))):
                        (r.support,r.confidence,r.lift) for r in frame.itertuples()}
            am,em=mapping(arules),mapping(erules)
            self.assertEqual(am.keys(),em.keys())
            for key in am:np.testing.assert_allclose(am[key],em[key],atol=1e-12,rtol=0)

    def test_repeated_benchmark_scope_and_speedup_calculation(self):
        output=ROOT/'results/benchmarks/spark_fp_growth'
        runs=pd.read_csv(output/'timing_runs.csv')
        summary=pd.read_csv(output/'timing_summary.csv')
        self.assertEqual(len(runs[~runs.warmup]),12)
        self.assertEqual(len(runs[runs.warmup]),4)
        self.assertTrue(runs.seconds.gt(0).all())
        self.assertTrue((runs.sampled_peak_rss_mib>=runs.rss_baseline_mib).all())
        for row in summary.itertuples():
            group=runs[(~runs.warmup) & np.isclose(runs.min_support,row.min_support)]
            py=group[group.engine.eq('python')].seconds
            spark=group[group.engine.eq('spark')].seconds
            self.assertEqual(len(py),3)
            self.assertEqual(len(spark),3)
            self.assertAlmostEqual(row.speedup_python_over_spark,py.median()/spark.median())

    def test_notebook_executes_spark_and_generates_figures(self):
        nb=json.loads((ROOT/'notebooks/07_PySpark.ipynb').read_text())
        cells=[c for c in nb['cells'] if c['cell_type']=='code']
        self.assertTrue(all(c['execution_count'] is not None for c in cells))
        source='\n'.join(''.join(c['source']) for c in cells)
        self.assertIn('run_spark_fp_growth(ROOT',source)
        self.assertNotIn('Image(filename',source)
        self.assertEqual(sum('image/png' in o.get('data',{}) for c in cells for o in c.get('outputs',[])),2)
        self.assertFalse(any(o.get('output_type')=='error' for c in cells for o in c.get('outputs',[])))


if __name__=='__main__':unittest.main()
