"""Check FP-Growth against lecture examples and independent transaction counts."""
import itertools
import json
from pathlib import Path
import unittest

import pandas as pd

from src.mining.fp_growth import (CONFIDENCES, SUPPORTS, exact_counts, load_transactions,
                                 minimum_count, mine_itemsets, mine_rules, validate_outputs)

ROOT = Path(__file__).resolve().parents[1]


class FPGrowthTest(unittest.TestCase):
    def test_lecture_trace_and_support_boundary(self):
        # The nine transactions from Lecture 7 are a small algorithm fixture.
        baskets = [['I1','I2','I5'], ['I2','I4'], ['I2','I3'], ['I1','I2','I4'],
                   ['I1','I3'], ['I2','I3'], ['I1','I3'], ['I1','I2','I3','I5'], ['I1','I2','I3']]
        matrix = pd.DataFrame([{i: i in b for i in ['I1','I2','I3','I4','I5']} for b in baskets], dtype=bool)
        rows = [{'items': b} for b in baskets]
        counts = exact_counts(rows)
        self.assertEqual([counts[frozenset([i])] for i in matrix], [6,7,6,2,2])
        self.assertEqual(counts[frozenset(['I1','I2','I5'])], 2)
        itemsets = mine_itemsets(matrix, 2/9)
        rules = mine_rules(itemsets, 9, 0.7)
        validate_outputs(itemsets, rules, counts, 9, 2/9, .7)
        match = rules[(rules.antecedents == frozenset(['I1','I5'])) & (rules.consequents == frozenset(['I2']))]
        self.assertEqual(len(match), 1)
        self.assertAlmostEqual(match.iloc[0].confidence, 1)
        self.assertAlmostEqual(match.iloc[0].lift, 9/7)

    def test_real_inputs_preserve_duplicate_patterns(self):
        rows, matrix = load_transactions(ROOT)
        self.assertEqual(matrix.shape, (437,15))
        self.assertEqual(len({tuple(sorted(r['items'])) for r in rows}), 159)
        self.assertTrue(matrix.sum(axis=1).eq(5).all())

    def test_all_declared_parameters_are_exact(self):
        rows, matrix = load_transactions(ROOT)
        # Enumerate the whole feature-compatible search space, including zero supports.
        families = [[c for c in matrix if c.startswith(f + '=')] for f in
                    ['occupancy_ratio','undertrial_share','female_share','age_18_30_share','illiterate_share']]
        direct = {}
        for combo in itertools.product(*[[None] + f for f in families]):
            items = frozenset(i for i in combo if i is not None)
            if items:
                direct[items] = int(matrix[list(items)].all(axis=1).sum())
        self.assertEqual(len(direct),1023)
        for support in SUPPORTS:
            itemsets = mine_itemsets(matrix,support)
            for confidence in CONFIDENCES:
                validate_outputs(itemsets,mine_rules(itemsets,len(rows),confidence),direct,
                                 len(rows),support,confidence)

    def test_validation_detects_wrong_metrics_and_omissions(self):
        rows,matrix=load_transactions(ROOT)
        counts=exact_counts(rows)
        itemsets=mine_itemsets(matrix,.05)
        rules=mine_rules(itemsets,len(rows),.7)
        corrupted=rules.copy()
        corrupted.loc[corrupted.index[0],'lift'] += .1
        with self.assertRaises(AssertionError):
            validate_outputs(itemsets,corrupted,counts,len(rows),.05,.7)
        with self.assertRaises(AssertionError):
            validate_outputs(itemsets,rules.iloc[:-1],counts,len(rows),.05,.7)
        with self.assertRaises(AssertionError):
            validate_outputs(itemsets.iloc[:-1],rules,counts,len(rows),.05,.7)

    def test_empty_result_and_threshold_validation(self):
        rows,matrix=load_transactions(ROOT)
        itemsets=mine_itemsets(matrix,1.0)
        self.assertTrue(itemsets.empty)
        rules=mine_rules(itemsets,len(rows),.7)
        self.assertTrue(rules.empty)
        validate_outputs(itemsets,rules,exact_counts(rows),len(rows),1.0,.7)
        self.assertEqual([minimum_count(s,437) for s in SUPPORTS],[22,44,66,88])
        for support in [0,-.1,1.01]:
            with self.assertRaises(ValueError):minimum_count(support,437)

    def test_saved_results_match_direct_rule_counts(self):
        rows,matrix=load_transactions(ROOT)
        saved=pd.read_csv(ROOT/'results/tables/fp_growth/exploratory_rules.csv')
        self.assertEqual(len(saved),4)
        self.assertTrue(pd.read_csv(ROOT/'results/tables/fp_growth/association_rules.csv').empty)
        for r in saved.to_dict('records'):
            a,b=json.loads(r['antecedents']),json.loads(r['consequents'])
            mask=matrix[a+b].all(axis=1)
            self.assertEqual(int(mask.sum()),r['support_count'])
            self.assertAlmostEqual(mask.sum()/matrix[a].all(axis=1).sum(),r['confidence'])
            matched=[row for row,present in zip(rows,mask) if present]
            self.assertEqual(len({t['state'] for t in matched}),r['covered_states'])
            self.assertEqual(len({t['year'] for t in matched}),r['covered_years'])


if __name__=='__main__':unittest.main()
