"""Verify MAFIA pruning, maximality and recounted rule metrics independently."""
import itertools
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from src.mining.fp_growth import load_transactions
from src.mining.mafia import (bitmap_support, mafia, maximal_union_rules,
                             validate_maximal, vertical_bitmaps)

ROOT=Path(__file__).resolve().parents[1]


def exhaustive_maximal(baskets,support):
    vocabulary=sorted(set().union(*(set(b) for b in baskets)))
    frequent={}
    cutoff=int(np.ceil(len(baskets)*support))
    for size in range(1,len(vocabulary)+1):
        for items in itertools.combinations(vocabulary,size):
            items=frozenset(items)
            count=sum(items <= set(b) for b in baskets)
            if count>=cutoff:frequent[items]=count
    return {items:count for items,count in frequent.items() if not any(items<other for other in frequent)}


class MafiaTest(unittest.TestCase):
    def test_lecture_maximal_example_without_enumerating_exponential_subsets(self):
        first=[f'a{i:03d}' for i in range(1,101)]
        second=first[:50]
        maximal,stats=mafia([first,second],.5)
        self.assertEqual(maximal,{frozenset(first):1})
        self.assertGreater(stats['pep_items'],0)
        self.assertLess(stats['nodes'],10)

    def test_leftmost_fhut_skips_siblings_and_preserves_output(self):
        baskets=[['a','b','c','d']]*3
        full,stats=mafia(baskets,1,pep=False)
        control,slow=mafia(baskets,1,pep=False,fhut=False,hutmfi=False,dynamic_order=False)
        self.assertEqual(full,control)
        self.assertEqual(full,{frozenset('abcd'):3})
        self.assertGreater(stats['fhut_sibling_branches_skipped'],0)
        self.assertLess(stats['nodes'],slow['nodes'])

    def test_every_pruning_combination_against_exhaustive_random_fixtures(self):
        rng=np.random.default_rng(819)
        hut_skipped=0
        for _ in range(40):
            membership=rng.random((int(rng.integers(2,11)),6))<rng.uniform(.25,.85)
            baskets=[[str(j) for j,present in enumerate(row) if present] for row in membership]
            support=float(rng.choice([.2,.5,1.0]))
            expected=exhaustive_maximal(baskets,support)
            for flags in itertools.product([False,True],repeat=4):
                maximal,stats=mafia(baskets,support,**dict(zip(['pep','fhut','hutmfi','dynamic_order'],flags)))
                self.assertEqual(maximal,expected)
                hut_skipped+=stats['hutmfi_tail_items_skipped']
        self.assertGreater(hut_skipped,0)

    def test_bitmap_counts_retain_duplicates_and_empty_baskets(self):
        baskets=[['a','b'],['a','b'],['a'],[]]
        vertical=vertical_bitmaps(baskets)
        self.assertEqual(bitmap_support(['a','b'],vertical,4),2)
        self.assertEqual(bitmap_support(['a'],vertical,4),3)
        self.assertEqual(mafia(baskets,.5)[0],{frozenset(['a','b']):2})
        self.assertEqual(mafia([[],[]],.5)[0],{})
        for invalid in [[],[['a','a']],[[1]]]:
            with self.assertRaises(ValueError):mafia(invalid,.5)
        for support in [0,-.1,1.1]:
            with self.assertRaises(ValueError):mafia(baskets,support)

    def test_maximal_unions_do_not_supply_all_rule_supports(self):
        baskets=[['a','b','c'],['a','b','c'],['a','b'],['a']]
        maximal,_=mafia(baskets,.5)
        self.assertEqual(maximal,{frozenset('abc'):2})
        rules,cache=maximal_union_rules(maximal,baskets,.6)
        self.assertEqual(cache[frozenset('a')],4)
        self.assertEqual(cache[frozenset('ab')],3)
        match=rules[(rules.antecedents==frozenset('ab')) & (rules.consequents==frozenset('c'))].iloc[0]
        self.assertAlmostEqual(match.confidence,2/3)
        self.assertAlmostEqual(match.lift,4/3)
        self.assertFalse(any(a|b==frozenset('ab') for a,b in zip(rules.antecedents,rules.consequents)))
        with self.assertRaises(ValueError):maximal_union_rules({frozenset('abc'):3},baskets,.6)

    def test_real_mfis_have_no_frequent_extensions_and_match_saved_fp(self):
        rows,matrix=load_transactions(ROOT)
        baskets=[row['items'] for row in rows]
        for support in [.05,.1,.15,.2]:
            maximal,_=mafia(baskets,support)
            validate_maximal(maximal,baskets,support)
            label=f'{support:.2f}'.replace('.','p')
            saved=pd.read_csv(ROOT/f'results/tables/mafia/maximal_s{label}.csv')
            self.assertEqual({frozenset(json.loads(r.items)):r.support_count for r in saved.itertuples()},maximal)
            fp=pd.read_csv(ROOT/f'results/tables/fp_growth/itemsets_s{label}.csv')
            all_sets={frozenset(json.loads(r.items)):r.support_count for r in fp.itertuples()}
            expected={items:count for items,count in all_sets.items() if not any(items<other for other in all_sets)}
            self.assertEqual(maximal,expected)
        with self.assertRaises(AssertionError):validate_maximal({},baskets,.1)

    def test_saved_rules_recount_metrics_and_expose_missing_nonmaximal_union(self):
        rows,matrix=load_transactions(ROOT)
        output=ROOT/'results/tables/mafia'
        rules=pd.read_csv(output/'exploratory_maximal_union_rules.csv')
        self.assertEqual(len(rules),4)
        self.assertTrue(pd.read_csv(output/'maximal_union_rules.csv').empty)
        for row in rules.itertuples():
            a,b=json.loads(row.antecedents),json.loads(row.consequents)
            joint=int(matrix[a+b].all(axis=1).sum())
            ca,cb=int(matrix[a].all(axis=1).sum()),int(matrix[b].all(axis=1).sum())
            self.assertEqual(joint,row.support_count)
            self.assertAlmostEqual(row.support,joint/len(rows))
            self.assertAlmostEqual(row.confidence,joint/ca)
            self.assertAlmostEqual(row.lift,(joint/ca)/(cb/len(rows)))
        comparison=pd.read_csv(output/'parameter_comparison.csv')
        self.assertEqual(len(comparison),12)
        omitted=pd.read_csv(output/'omitted_fp_rules.csv')
        self.assertEqual(len(omitted),1)
        self.assertAlmostEqual(omitted.iloc[0].min_support,.05)
        self.assertAlmostEqual(omitted.iloc[0].min_confidence,.6)
        self.assertEqual(omitted.iloc[0].support_count,62)


if __name__=='__main__':unittest.main()
