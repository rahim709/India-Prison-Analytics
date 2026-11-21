"""Mine maximal frequent itemsets with bitmap MAFIA and verified rule supports."""

import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd

from src.mining.fp_growth import (BASE_CONFIDENCE, BASE_SUPPORT, CONFIDENCES, EXPLORATORY_CONFIDENCE,
                                 EXPLORATORY_SUPPORT, METRICS, SUPPORTS, exact_counts,
                                 load_transactions, minimum_count, serialize_rules)
from src.preprocessing.cleaning import sha256

PAPER = 'https://www.cs.cornell.edu/johannes/papers/2001/icde2001-mafia.pdf'


def vertical_bitmaps(transactions):
    if not transactions:
        raise ValueError('At least one transaction is required.')
    bitmaps = {}
    for tid, basket in enumerate(transactions):
        if any(not isinstance(item, str) or not item for item in basket):
            raise ValueError('Item names must be nonempty strings.')
        if len(basket) != len(set(basket)):
            raise ValueError('Items must be unique within each transaction.')
        for item in basket:
            bitmaps[item] = bitmaps.get(item, 0) | (1 << tid)
    return dict(sorted(bitmaps.items()))


def bitmap_support(items, bitmaps, n):
    bitmap = (1 << n) - 1
    for item in items:
        bitmap &= bitmaps[item]
    return bitmap.bit_count()


def mafia(transactions, min_support, *, pep=True, fhut=True, hutmfi=True, dynamic_order=True):
    """Run MAFIA head/tail DFS; return nonempty MFIs, integer counts and counters."""
    n = len(transactions)
    cutoff = minimum_count(min_support, n)
    vertical = vertical_bitmaps(transactions)
    found = {}
    stats = Counter({name: 0 for name in ['nodes', 'bitmap_intersections', 'infrequent_extensions',
                                         'pep_items', 'fhut_prunes', 'hutmfi_prunes',
                                         'dynamic_reorder_nodes', 'candidate_insertions',
                                         'dominated_candidates_removed', 'max_recursion_depth',
                                         'fhut_sibling_branches_skipped', 'hutmfi_tail_items_skipped']})

    def insert(items, count):
        if not items or any(items <= known for known in found):
            return
        dominated = [known for known in found if known < items]
        for known in dominated:
            del found[known]
        stats['dominated_candidates_removed'] += len(dominated)
        found[items] = count
        stats['candidate_insertions'] += 1

    def search(head, bitmap, tail, depth):
        # The return value says whether this node's original head-union-tail is frequent.
        stats['nodes'] += 1
        stats['max_recursion_depth'] = max(stats['max_recursion_depth'], depth)
        hut = head | frozenset(tail)
        if hutmfi and any(hut <= known for known in found):
            stats['hutmfi_prunes'] += 1
            stats['hutmfi_tail_items_skipped'] += len(tail)
            return True
        count = bitmap.bit_count()
        extensions = []
        all_children_frequent = True
        for item in tail:
            child = bitmap & vertical[item]
            stats['bitmap_intersections'] += 1
            support = child.bit_count()
            if support < cutoff:
                stats['infrequent_extensions'] += 1
                # The original HUT stays infrequent even after this item is trimmed.
                all_children_frequent = False
            elif pep and child == bitmap:
                # Equal transaction sets let us move this item from tail to head.
                head = head | {item}
                stats['pep_items'] += 1
            else:
                extensions.append((item, child, support))
        if dynamic_order and extensions:
            extensions.sort(key=lambda candidate: (candidate[2], candidate[0]))
            stats['dynamic_reorder_nodes'] += 1
        if not extensions:
            insert(head, count)
            return all_children_frequent
        first_child_hut_frequent = False
        for position, (item, child, _) in enumerate(extensions):
            remaining = tuple(candidate[0] for candidate in extensions[position+1:])
            child_hut_frequent = search(head | {item}, child, remaining, depth+1)
            if position == 0:
                first_child_hut_frequent = child_hut_frequent
                if fhut and child_hut_frequent:
                    # The first child's HUT covers every remaining sibling branch.
                    stats['fhut_prunes'] += 1
                    stats['fhut_sibling_branches_skipped'] += len(extensions)-1
                    return all_children_frequent
        return all_children_frequent and first_child_hut_frequent

    search(frozenset(), (1 << n)-1, tuple(vertical), 0)
    result = dict(sorted(found.items(), key=lambda pair: (len(pair[0]), tuple(sorted(pair[0])))))
    return result, dict(stats)


def validate_maximal(maximal, transactions, min_support):
    n = len(transactions)
    cutoff = minimum_count(min_support, n)
    rows = [{'items': basket} for basket in transactions]
    counts = exact_counts(rows)
    frequent = {items: count for items, count in counts.items() if count >= cutoff}
    expected = {items: count for items, count in frequent.items()
                if not any(items < other for other in frequent)}
    if maximal != expected:
        raise AssertionError('MAFIA output is not the complete exact maximal-itemset collection.')
    vocabulary = sorted(set().union(*(set(t) for t in transactions)))
    extension_records = []
    baskets = [set(t) for t in transactions]
    for items, count in maximal.items():
        if sum(items <= basket for basket in baskets) != count or count < cutoff:
            raise AssertionError('An MFI has an incorrect or insufficient support count.')
        for item in vocabulary:
            if item not in items:
                extension = items | {item}
                actual = sum(extension <= basket for basket in baskets)
                if actual >= cutoff:
                    raise AssertionError('An MFI has a frequent one-item extension.')
                extension_records.append(dict(items=json.dumps(sorted(items)), added_item=item,
                                              extension_count=actual, min_count=cutoff,
                                              extension_frequent=False))
    return counts, extension_records


def maximal_union_rules(maximal, transactions, confidence):
    if not 0 <= confidence <= 1:
        raise ValueError('Confidence must be in [0, 1].')
    vertical = vertical_bitmaps(transactions)
    n = len(transactions)
    support_cache = {}

    def recount(items):
        if items not in support_cache:
            support_cache[items] = bitmap_support(items, vertical, n)
        return support_cache[items]

    records = []
    for union, declared in maximal.items():
        union_count = recount(union)
        if declared != union_count:
            raise ValueError('A maximal union has an incorrect support count.')
        for size in range(1, len(union)):
            for combination in itertools.combinations(sorted(union), size):
                a = frozenset(combination)
                b = union - a
                count_a, count_b = recount(a), recount(b)
                conf = union_count / count_a
                if conf >= confidence:
                    sa, sb, joint = count_a/n, count_b/n, union_count/n
                    records.append(dict(antecedents=a, consequents=b,
                                        **{'antecedent support': sa, 'consequent support': sb,
                                           'support': joint, 'confidence': conf, 'lift': conf/sb,
                                           'leverage': joint-sa*sb}))
    return pd.DataFrame(records, columns=['antecedents', 'consequents'] + METRICS), support_cache


def serialize_maximal(maximal, n):
    records = [dict(items=json.dumps(sorted(items)), length=len(items), support_count=count,
                    support=count/n) for items, count in maximal.items()]
    return pd.DataFrame(records, columns=['items','length','support_count','support']).sort_values(
        ['length','support_count','items'], ascending=[True,False,True]).reset_index(drop=True)


def compare_rules_with_fp(maximal, rules, fp_path):
    fp = pd.read_csv(fp_path)
    def key(a, b):
        return frozenset(json.loads(a)), frozenset(json.loads(b))
    expected = {key(r.antecedents, r.consequents): r for r in fp.itertuples()
                if frozenset(json.loads(r.antecedents) + json.loads(r.consequents)) in maximal}
    observed = {key(r.antecedents, r.consequents): r for r in rules.itertuples()}
    if expected.keys() != observed.keys() or len(observed) != len(rules):
        raise AssertionError('Maximal-union rules differ from the equivalent FP-Growth rule subset.')
    for pair, row in observed.items():
        reference = expected[pair]
        for metric in ['support', 'confidence', 'lift', 'leverage', 'antecedent_support', 'consequent_support']:
            if not np.isclose(getattr(row, metric), getattr(reference, metric), atol=1e-12, rtol=0):
                raise AssertionError('Rule metrics differ from saved FP-Growth outputs.')
    return len(fp), len(expected)


def run_mafia(root):
    root = Path(root)
    output = root / 'results/tables/mafia'
    output.mkdir(parents=True, exist_ok=True)
    rows, matrix = load_transactions(root)
    transactions = [r['items'] for r in rows]
    provenance = [{'file':'data/processed/transformed/'+spec['file'], 'sha256':spec['sha256']}
                  for spec in json.loads((root/'results/tables/transformation/transformed_manifest.json').read_text())]
    fp_root = root / 'results/tables/fp_growth'
    baseline_maximal, baseline_rules, exploratory_rules = None, None, None
    comparison, validations, histogram, ablations, omitted = [], [], [], [], []
    for support in SUPPORTS:
        label = f'{support:.2f}'.replace('.', 'p')
        maximal, stats = mafia(transactions, support)
        counts, extensions = validate_maximal(maximal, transactions, support)
        exported = serialize_maximal(maximal, len(rows))
        exported.to_csv(output/f'maximal_s{label}.csv', index=False)
        pd.DataFrame(extensions, columns=['items','added_item','extension_count','min_count','extension_frequent']).to_csv(
            output/f'extension_checks_s{label}.csv', index=False)
        fp_path = fp_root/f'itemsets_s{label}.csv'
        fp = pd.read_csv(fp_path)
        fp_sets = {frozenset(json.loads(r.items)):r.support_count for r in fp.itertuples()}
        expected_fp = {items:count for items,count in fp_sets.items() if not any(items < other for other in fp_sets)}
        if maximal != expected_fp:
            raise AssertionError('MAFIA MFIs differ from maximal sets independently derived from FP-Growth.')
        provenance.append(dict(file=str(fp_path.relative_to(root)), sha256=sha256(fp_path)))
        for length, number in sorted(Counter(len(items) for items in maximal).items()):
            histogram.append(dict(min_support=support, length=length, maximal_itemsets=number))
        for confidence in CONFIDENCES:
            raw_rules, recounted = maximal_union_rules(maximal, transactions, confidence)
            rules = serialize_rules(raw_rules, rows, counts)
            rule_path = fp_root/f'rules_s{label}_c{confidence:.2f}.csv'
            fp_rule_count, matched = compare_rules_with_fp(maximal, rules, rule_path)
            for original in pd.read_csv(rule_path).to_dict('records'):
                union = frozenset(json.loads(original['antecedents']) + json.loads(original['consequents']))
                if union not in maximal:
                    containers = [sorted(items) for items in maximal if union < items]
                    omitted.append(dict(min_support=support, min_confidence=confidence,
                                        **original, containing_maximal_itemsets=json.dumps(containers)))
            provenance.append(dict(file=str(rule_path.relative_to(root)), sha256=sha256(rule_path)))
            rules.to_csv(output/f'rules_s{label}_c{confidence:.2f}.csv', index=False)
            comparison.append(dict(min_support=support, min_count=minimum_count(support,len(rows)),
                                   min_confidence=confidence, fp_frequent_itemsets=len(fp), maximal_itemsets=len(maximal),
                                   retained_itemset_fraction=len(maximal)/len(fp) if len(fp) else 0,
                                   max_mfi_length=max(map(len,maximal),default=0), fp_all_rules=fp_rule_count,
                                   maximal_union_rules=len(rules), omitted_fp_rules=fp_rule_count-matched,
                                   positive_lift_rules=int((rules.lift>1).sum()), **stats))
            validations.append(dict(min_support=support,min_confidence=confidence,
                                    exact_frequency_and_maximality=True, complete_maximal_union_rule_equivalence=True))
            if support==BASE_SUPPORT and confidence==BASE_CONFIDENCE:
                baseline_maximal, baseline_rules = exported, rules
            if support==EXPLORATORY_SUPPORT and confidence==EXPLORATORY_CONFIDENCE:
                exploratory_rules = rules
                cache = pd.DataFrame([dict(items=json.dumps(sorted(items)),support_count=count,support=count/len(rows))
                                      for items,count in sorted(recounted.items(),key=lambda pair:(len(pair[0]),tuple(sorted(pair[0]))))])
                cache.to_csv(output/'exploratory_recounted_supports.csv',index=False)
        # Disable one search component at a time to check output invariance.
        for name, options in [('full',{}),('without_pep',{'pep':False}),('without_fhut',{'fhut':False}),
                              ('without_hutmfi',{'hutmfi':False}),('without_dynamic_order',{'dynamic_order':False}),
                              ('plain_dfs_control',{'pep':False,'fhut':False,'hutmfi':False,'dynamic_order':False})]:
            alternate, alternate_stats = mafia(transactions,support,**options)
            if alternate != maximal:
                raise AssertionError('A pruning ablation changed the maximal-itemset result.')
            ablations.append(dict(min_support=support,configuration=name,output_equivalent=True,**alternate_stats))
    baseline_maximal.to_csv(output/'maximal_itemsets.csv',index=False)
    baseline_rules.to_csv(output/'maximal_union_rules.csv',index=False)
    exploratory_rules.to_csv(output/'exploratory_maximal_union_rules.csv',index=False)
    pd.DataFrame(comparison).to_csv(output/'parameter_comparison.csv',index=False)
    pd.DataFrame(histogram).to_csv(output/'maximal_length_distribution.csv',index=False)
    pd.DataFrame(ablations).to_csv(output/'pruning_ablation.csv',index=False)
    pd.DataFrame(omitted).to_csv(output/'omitted_fp_rules.csv',index=False)
    for item in provenance:
        if sha256(root/item['file']) != item['sha256']:
            raise AssertionError('An input file changed during MAFIA mining.')
    summary = dict(transactions=len(rows),vocabulary=len(matrix.columns),items_per_transaction=5,
                   baseline_support=BASE_SUPPORT,baseline_confidence=BASE_CONFIDENCE,
                   baseline_maximal_itemsets=len(baseline_maximal),baseline_rules=len(baseline_rules),
                   exploratory_support=EXPLORATORY_SUPPORT,exploratory_confidence=EXPLORATORY_CONFIDENCE,
                   exploratory_rules=len(exploratory_rules),supports=list(SUPPORTS),confidences=list(CONFIDENCES),
                   algorithm='MAFIA head/tail DFS, vertical integer bitmaps, PEP, leftmost-path FHUT, HUTMFI and ascending-support dynamic reordering',
                   representation='Python arbitrary-precision integers, one transaction bit per observation, AND and bit_count; no adaptive relative-bitmap compression',
                   mfi_repository='maintained inclusion antichain; subset/superset checks use Python frozensets; no specialized MFI index',
                   rules='all disjoint nonempty partitions of maximal unions meeting confidence, with independently recounted subset supports; not the complete association-rule family',
                   paper=PAPER,validation=validations,inputs=provenance,
                   python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,
                   benchmark_claim='node/intersection counters describe work, not measured time or speedup')
    (output/'run_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    summary=run_mafia(parser.parse_args().root)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['inputs','validation']},indent=2))


if __name__=='__main__':main()
