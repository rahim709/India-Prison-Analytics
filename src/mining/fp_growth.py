"""Mine aggregate prison profiles with FP-Growth and verify exact supports."""

import argparse
from collections import Counter
from decimal import Decimal, ROUND_CEILING
import itertools
import json
from pathlib import Path
import platform

import mlxtend
from mlxtend.frequent_patterns import association_rules, fpgrowth
import numpy as np
import pandas as pd

from src.preprocessing.cleaning import sha256
from src.preprocessing.transformation import FEATURES, load_transformed

SUPPORTS = (0.05, 0.10, 0.15, 0.20)
CONFIDENCES = (0.60, 0.70, 0.80)
BASE_SUPPORT = 0.10
BASE_CONFIDENCE = 0.70
EXPLORATORY_SUPPORT = 0.05
EXPLORATORY_CONFIDENCE = 0.70
METRICS = ['antecedent support', 'consequent support', 'support', 'confidence', 'lift', 'leverage']


def minimum_count(support, n):
    if not 0 < support <= 1 or n < 1:
        raise ValueError('Support must be in (0, 1] and transaction count must be positive.')
    return int((Decimal(str(support)) * n).to_integral_value(rounding=ROUND_CEILING))


def load_transactions(root):
    encoded = load_transformed(root, 'transactions_onehot.csv')
    rows = load_transformed(root, 'transactions.jsonl')
    if not rows or encoded.profile_id.duplicated().any():
        raise ValueError('Transactions must be nonempty and have unique profile identities.')
    if encoded.profile_id.tolist() != [r['profile_id'] for r in rows]:
        raise ValueError('Transaction identities are not aligned.')
    matrix = encoded.drop(columns='profile_id')
    if not all(dtype == bool for dtype in matrix.dtypes) or matrix.isna().any().any():
        raise ValueError('The membership matrix must be Boolean and complete.')
    for row, membership in zip(rows, matrix.to_numpy()):
        items = row['items']
        if len(items) != len(set(items)) or len(items) != len(FEATURES):
            raise ValueError('Each transaction must contain five unique feature items.')
        if set(i.split('=', 1)[0] for i in items) != set(FEATURES):
            raise ValueError('Each feature must contribute exactly one item.')
        if set(matrix.columns[membership]) != set(items):
            raise ValueError('JSON transactions and Boolean membership differ.')
    return rows, matrix


def exact_counts(rows):
    # Count every observed subset directly, without using a mining library.
    counts = Counter()
    for row in rows:
        items = sorted(row['items'])
        for length in range(1, len(items) + 1):
            counts.update(frozenset(s) for s in itertools.combinations(items, length))
    return counts


def mine_itemsets(matrix, support):
    minimum_count(support, len(matrix))
    result = fpgrowth(matrix, min_support=support, use_colnames=True, max_len=None)
    return result


def mine_rules(itemsets, n, confidence):
    if not 0 <= confidence <= 1:
        raise ValueError('Confidence must be in [0, 1].')
    if itemsets.empty:
        return pd.DataFrame(columns=['antecedents', 'consequents'] + METRICS)
    return association_rules(itemsets, num_itemsets=n, metric='confidence',
                             min_threshold=confidence, return_metrics=METRICS)


def validate_outputs(itemsets, rules, counts, n, support, confidence):
    cutoff = minimum_count(support, n)
    expected = {items: count for items, count in counts.items() if count >= cutoff}
    actual = {frozenset(r.itemsets): r.support for r in itemsets.itertuples()}
    if len(actual) != len(itemsets) or actual.keys() != expected.keys():
        raise AssertionError('FP-Growth omitted, duplicated or added a frequent itemset.')
    for items, count in expected.items():
        if not np.isclose(actual[items], count / n, atol=1e-12, rtol=0):
            raise AssertionError('Itemset support differs from direct counting.')
    expected_rules = set()
    for union, count in expected.items():
        for length in range(1, len(union)):
            for subset in itertools.combinations(sorted(union), length):
                a = frozenset(subset)
                if count / counts[a] >= confidence:
                    expected_rules.add((a, union - a))
    actual_rules = set()
    for row in rules.to_dict('records'):
        a, b = frozenset(row['antecedents']), frozenset(row['consequents'])
        if not a or not b or a & b:
            raise AssertionError('Invalid rule sides.')
        union = counts[a | b] / n
        sa, sb = counts[a] / n, counts[b] / n
        correct = [sa, sb, union, union / sa, union / (sa * sb), union - sa * sb]
        if not np.allclose([row[m] for m in METRICS], correct, atol=1e-12, rtol=0):
            raise AssertionError('Rule metrics differ from direct counting.')
        actual_rules.add((a, b))
    if actual_rules != expected_rules or len(actual_rules) != len(rules):
        raise AssertionError('Rule generation is incomplete or contains duplicates.')
    return {'frequent_itemsets': len(expected), 'rules': len(expected_rules),
            'exact_itemset_and_rule_validation': True}


def serialize_itemsets(itemsets, counts, n):
    records = [{'items': json.dumps(sorted(r.itemsets)), 'length': len(r.itemsets),
                'support_count': counts[r.itemsets], 'support': counts[r.itemsets] / n}
               for r in itemsets.itertuples()]
    return pd.DataFrame(records, columns=['items', 'length', 'support_count', 'support']).sort_values(
        ['length', 'support_count', 'items'], ascending=[True, False, True]).reset_index(drop=True)


def serialize_rules(rules, rows, counts):
    records = []
    for r in rules.to_dict('records'):
        a, b = r['antecedents'], r['consequents']
        matched = [t for t in rows if a | b <= set(t['items'])]
        record = {side: json.dumps(sorted(r[side])) for side in ['antecedents', 'consequents']}
        record.update({m.replace(' ', '_'): r[m] for m in METRICS})
        record.update(antecedent_count=counts[a], consequent_count=counts[b], support_count=counts[a | b],
                      antecedent_length=len(a), consequent_length=len(b),
                      covered_states=len({t['state'] for t in matched}),
                      covered_years=len({t['year'] for t in matched}))
        records.append(record)
    columns = ['antecedents', 'consequents'] + [m.replace(' ', '_') for m in METRICS] + [
        'antecedent_count', 'consequent_count', 'support_count', 'antecedent_length',
        'consequent_length', 'covered_states', 'covered_years']
    return pd.DataFrame(records, columns=columns).sort_values(
        ['lift', 'confidence', 'support', 'antecedents', 'consequents'],
        ascending=[False, False, False, True, True]).reset_index(drop=True)


def select_interpretable_rules(rules):
    # Short premises and one outcome make the displayed rules easier to read.
    return rules[(rules.lift > 1) & (rules.antecedent_length <= 2)
                 & (rules.consequent_length == 1)].copy().reset_index(drop=True)


def run_fp_growth(root):
    root = Path(root)
    output = root / 'results/tables/fp_growth'
    output.mkdir(parents=True, exist_ok=True)
    input_manifest = json.loads((root / 'results/tables/transformation/transformed_manifest.json').read_text())
    rows, matrix = load_transactions(root)
    counts = exact_counts(rows)
    comparisons, validations = [], []
    for support in SUPPORTS:
        itemsets = mine_itemsets(matrix, support)
        label = f'{support:.2f}'.replace('.', 'p')
        serialize_itemsets(itemsets, counts, len(rows)).to_csv(output / f'itemsets_s{label}.csv', index=False)
        for confidence in CONFIDENCES:
            rules = mine_rules(itemsets, len(rows), confidence)
            checked = validate_outputs(itemsets, rules, counts, len(rows), support, confidence)
            validations.append(dict(min_support=support, min_confidence=confidence, **checked))
            exported_rules = serialize_rules(rules, rows, counts)
            exported_rules.to_csv(output / f'rules_s{label}_c{confidence:.2f}.csv', index=False)
            if support == EXPLORATORY_SUPPORT and confidence == EXPLORATORY_CONFIDENCE:
                exploratory_rules = exported_rules
            comparisons.append(dict(min_support=support, min_count=minimum_count(support, len(rows)),
                                    min_confidence=confidence, itemsets=len(itemsets),
                                    max_itemset_length=int(itemsets.itemsets.map(len).max()) if len(itemsets) else 0,
                                    rules=len(rules), positive_lift_rules=int((rules.lift > 1).sum())))
            if support == BASE_SUPPORT and confidence == BASE_CONFIDENCE:
                baseline_itemsets = serialize_itemsets(itemsets, counts, len(rows))
                baseline_rules = serialize_rules(rules, rows, counts)
    baseline_itemsets.to_csv(output / 'frequent_itemsets.csv', index=False)
    baseline_rules.to_csv(output / 'association_rules.csv', index=False)
    exploratory_rules.to_csv(output / 'exploratory_rules.csv', index=False)
    selected = select_interpretable_rules(exploratory_rules)
    selected.to_csv(output / 'interpretable_rules.csv', index=False)
    occupancy = selected[selected.consequents.map(lambda s: any(i.startswith('occupancy_ratio=') for i in json.loads(s)))]
    occupancy.to_csv(output / 'occupancy_rules.csv', index=False)
    pd.DataFrame(comparisons).to_csv(output / 'parameter_comparison.csv', index=False)
    families = [[c for c in matrix.columns if c.startswith(f + '=')] for f in FEATURES]
    candidates = sum(np.prod([len(families[i]) for i in indices])
                     for k in range(1, 6) for indices in itertools.combinations(range(5), k))
    summary = {'transactions': len(rows), 'states': len({r['state'] for r in rows}),
               'years': sorted({r['year'] for r in rows}), 'vocabulary_size': len(matrix.columns),
               'items_per_transaction': 5, 'distinct_item_patterns': len({tuple(r['items']) for r in rows}),
               'admissible_nonempty_itemsets': int(candidates), 'positive_support_itemsets': len(counts),
               'min_support': BASE_SUPPORT, 'min_count': minimum_count(BASE_SUPPORT, len(rows)),
               'min_confidence': BASE_CONFIDENCE, 'baseline_itemsets': len(baseline_itemsets),
               'baseline_rules': len(baseline_rules), 'exploratory_support': EXPLORATORY_SUPPORT, 'exploratory_confidence': EXPLORATORY_CONFIDENCE,
               'exploratory_rules': len(exploratory_rules), 'interpretable_positive_lift_rules': len(selected),
               'occupancy_rules': len(occupancy), 'max_itemset_length': int(baseline_itemsets.length.max()),
               'unit': 'one selected state-year; not one prisoner',
               'threshold_scope': 'baseline fixed before mining; lower-support setting from declared grid reported explicitly as exploratory after baseline yielded no rules',
               'lift_filter': 'all confidence-qualified baseline rules retained; lift > 1 only for interpretation',
               'validation': validations, 'python': platform.python_version(), 'mlxtend': mlxtend.__version__,
               'pandas': pd.__version__, 'numpy': np.__version__,
               'inputs': [{'file': 'data/processed/transformed/' + s['file'], 'sha256': s['sha256']} for s in input_manifest]}
    for item in summary['inputs']:
        if sha256(root / item['file']) != item['sha256']:
            raise AssertionError('An upstream transformed file changed.')
    (output / 'run_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    summary = run_fp_growth(parser.parse_args().root)
    print(json.dumps({k: v for k, v in summary.items() if k not in ['inputs', 'validation']}, indent=2))


if __name__ == '__main__':
    main()
