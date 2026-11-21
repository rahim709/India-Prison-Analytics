"""Partition state-year profiles using deterministic best-swap PAM."""

import argparse
import itertools
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
import sklearn
from sklearn.metrics import adjusted_rand_score, silhouette_samples, silhouette_score

from src.preprocessing.cleaning import sha256
from src.preprocessing.transformation import FEATURES, load_transformed

K_VALUES = tuple(range(2, 9))
PRIMARY_METRIC = 'cityblock'
METRICS = ('cityblock', 'euclidean')
SEEDS = (42, 43, 44, 45)
TOL = 1e-10
MAX_ITER = 100
MIN_CLUSTER_FRACTION = 0.05


def validate_distances(distances):
    d = np.asarray(distances, dtype=float)
    if d.ndim != 2 or d.shape[0] != d.shape[1] or len(d) == 0:
        raise ValueError('Distances must form a nonempty square matrix.')
    if not np.isfinite(d).all() or (d < 0).any():
        raise ValueError('Distances must be finite and nonnegative.')
    if not np.allclose(d, d.T, atol=1e-12, rtol=0) or not np.allclose(np.diag(d), 0, atol=1e-12, rtol=0):
        raise ValueError('Distances must be symmetric with a zero diagonal.')
    return d


def assign(distances, medoids):
    medoids = np.sort(np.asarray(medoids, dtype=int))
    local = distances[:, medoids]
    labels = local.argmin(axis=1)
    # A medoid represents itself when identical profiles give tied distances.
    labels[medoids] = np.arange(len(medoids))
    nearest = local[np.arange(len(distances)), labels]
    return labels, nearest


def build_medoids(d, k):
    medoids = [int(np.argmin(d.sum(axis=0)))]
    nearest = d[:, medoids[0]]
    while len(medoids) < k:
        candidates = np.setdiff1d(np.arange(len(d)), medoids)
        costs = np.minimum(nearest[:, None], d[:, candidates]).sum(axis=0)
        chosen = int(candidates[np.flatnonzero(costs <= costs.min() + TOL)[0]])
        medoids.append(chosen)
        nearest = np.minimum(nearest, d[:, chosen])
    return np.sort(medoids)


def swap_costs(d, medoids):
    """Evaluate every medoid/nonmedoid swap using nearest two distances."""
    candidates = np.setdiff1d(np.arange(len(d)), medoids)
    local = d[:, medoids]
    labels = local.argmin(axis=1)
    first = local.min(axis=1)
    second = np.partition(local, 1, axis=1)[:, 1] if len(medoids) > 1 else np.full(len(d), np.inf)
    costs = np.empty((len(medoids), len(candidates)))
    for position in range(len(medoids)):
        # Removing the closest medoid exposes the second closest alternative.
        remaining = np.where(labels == position, second, first)
        costs[position] = np.minimum(remaining[:, None], d[:, candidates]).sum(axis=0)
    return candidates, costs


def pam(distances, k, initial_medoids=None, tol=TOL, max_iter=MAX_ITER):
    d = validate_distances(distances)
    if not isinstance(k, (int, np.integer)) or not 1 <= k <= len(d):
        raise ValueError('k must be an integer between one and the number of profiles.')
    if not np.isfinite(tol) or tol < 0 or not isinstance(max_iter, int) or max_iter < 0:
        raise ValueError('Tolerance and iteration limit must be nonnegative.')
    if initial_medoids is None:
        medoids = build_medoids(d, k)
    else:
        raw = np.asarray(initial_medoids)
        if raw.ndim != 1 or len(raw) != k or not np.issubdtype(raw.dtype, np.integer):
            raise ValueError('Initial medoids must be k integer row indices.')
        medoids = np.sort(raw.astype(int))
        if len(set(medoids)) != k or medoids.min() < 0 or medoids.max() >= len(d):
            raise ValueError('Initial medoid indices must be unique and in range.')
    initial = medoids.copy()
    labels, nearest = assign(d, medoids)
    history = [dict(step=0, cost=float(nearest.sum()), removed=None, added=None,
                    medoid_indices=medoids.tolist())]
    for iteration in range(max_iter + 1):
        candidates, costs = swap_costs(d, medoids)
        current = float(nearest.sum())
        if costs.size == 0 or costs.min() >= current - tol:
            return dict(medoids=medoids, labels=labels, distances=nearest, cost=current,
                        initial_medoids=initial, swaps=len(history)-1, converged=True, history=history)
        if iteration == max_iter:
            raise RuntimeError('PAM reached its iteration limit before convergence.')
        choices = np.argwhere((costs <= costs.min() + tol) & (costs < current - tol))
        position, candidate_position = choices[0]
        removed, added = int(medoids[position]), int(candidates[candidate_position])
        proposed = np.sort(np.append(np.delete(medoids, position), added))
        labels, nearest = assign(d, proposed)
        if nearest.sum() >= current - tol:
            raise AssertionError('A selected swap did not improve the objective.')
        medoids = proposed
        history.append(dict(step=len(history), cost=float(nearest.sum()), removed=removed,
                            added=added, medoid_indices=medoids.tolist()))


def reference_swap_costs(d, medoids):
    # Independently replace each medoid and recompute all assignments from scratch.
    candidates = np.setdiff1d(np.arange(len(d)), medoids)
    costs = np.empty((len(medoids), len(candidates)))
    for i in range(len(medoids)):
        for j, candidate in enumerate(candidates):
            proposed = list(medoids)
            proposed[i] = candidate
            costs[i, j] = d[:, proposed].min(axis=1).sum()
    return candidates, costs


def load_profiles(root):
    raw = load_transformed(root, 'profile_features.csv')
    scaled = load_transformed(root, 'clustering_features.csv')
    if raw.profile_id.tolist() != scaled.profile_id.tolist() or raw.profile_id.duplicated().any():
        raise ValueError('Original and standardized profile identities must align and be unique.')
    if list(scaled.columns) != ['profile_id'] + FEATURES:
        raise ValueError('Standardized feature order differs from the saved contract.')
    order = np.argsort(scaled.profile_id.to_numpy())
    raw, scaled = raw.iloc[order].reset_index(drop=True), scaled.iloc[order].reset_index(drop=True)
    x = scaled[FEATURES].to_numpy(dtype=float)
    if not np.isfinite(x).all():
        raise ValueError('Clustering features must be finite.')
    return raw, scaled, x


def fit_starts(d, k, seeds=SEEDS):
    fits = [('build', None, pam(d, k))]
    for seed in seeds:
        initial = np.sort(np.random.default_rng(seed).choice(len(d), size=k, replace=False))
        fits.append(('random', seed, pam(d, k, initial)))
    best_cost = min(fit['cost'] for _, _, fit in fits)
    best = min((fit for _, _, fit in fits if fit['cost'] <= best_cost + TOL),
               key=lambda fit: tuple(fit['medoids']))
    return best, fits


def run_clustering(root):
    root = Path(root)
    output = root / 'results/tables/k_medoids'
    output.mkdir(parents=True, exist_ok=True)
    raw, scaled, x = load_profiles(root)
    summaries, start_rows, best_fits, distance_matrices = [], [], {}, {}
    minimum_size = int(np.ceil(MIN_CLUSTER_FRACTION * len(raw)))
    for metric in METRICS:
        d = cdist(x, x, metric=metric)
        np.fill_diagonal(d, 0)
        distance_matrices[metric] = d
        for k in K_VALUES:
            best, fits = fit_starts(d, k)
            best_fits[metric, k] = best
            sizes = np.bincount(best['labels'], minlength=k)
            pairwise_ari = [adjusted_rand_score(a[2]['labels'], b[2]['labels'])
                            for a, b in itertools.combinations(fits, 2)]
            summaries.append(dict(metric=metric, k=k, objective=best['cost'],
                                  objective_per_profile=best['cost']/len(raw),
                                  silhouette=silhouette_score(d, best['labels'], metric='precomputed'),
                                  min_cluster_size=int(sizes.min()), max_cluster_size=int(sizes.max()),
                                  eligible=bool(sizes.min() >= minimum_size),
                                  mean_start_ari=float(np.mean(pairwise_ari)), min_start_ari=float(min(pairwise_ari)),
                                  best_swaps=best['swaps']))
            for initialization, seed, fit in fits:
                start_rows.append(dict(metric=metric, k=k, initialization=initialization,
                                       seed=seed, selected_for_metric_k=bool(fit is best), objective=fit['cost'], swaps=fit['swaps'],
                                       silhouette=silhouette_score(d, fit['labels'], metric='precomputed'),
                                       ari_to_best=adjusted_rand_score(best['labels'], fit['labels']),
                                       initial_medoids=json.dumps(raw.iloc[fit['initial_medoids']].profile_id.tolist()),
                                       final_medoids=json.dumps(raw.iloc[fit['medoids']].profile_id.tolist())))
    comparison = pd.DataFrame(summaries)
    eligible = comparison[(comparison.metric == PRIMARY_METRIC) & comparison.eligible]
    if eligible.empty:
        raise ValueError('No candidate meets the declared minimum cluster size; revise the plan explicitly.')
    chosen = eligible.sort_values(['silhouette', 'k'], ascending=[False, True]).iloc[0]
    unrestricted = comparison[comparison.metric == PRIMARY_METRIC].sort_values(['silhouette', 'k'], ascending=[False, True]).iloc[0]
    euclidean_choice = comparison[(comparison.metric == 'euclidean') & comparison.eligible].sort_values(['silhouette', 'k'], ascending=[False, True]).iloc[0]
    k = int(chosen.k)
    fit = best_fits[PRIMARY_METRIC, k]
    d = distance_matrices[PRIMARY_METRIC]
    # Relabel by increasing raw occupancy of the medoids for readable cluster IDs.
    medoids = fit['medoids']
    medoid_order = sorted(range(k), key=lambda j: (raw.iloc[medoids[j]].occupancy_ratio,
                                                   raw.iloc[medoids[j]].profile_id))
    remap = {old: new for new, old in enumerate(medoid_order)}
    labels = np.array([remap[int(label)] for label in fit['labels']])
    silhouette = silhouette_samples(d, labels, metric='precomputed')
    assignments = raw.copy()
    assignments['cluster'] = labels
    assignments['medoid_profile_id'] = [raw.iloc[medoids[old]].profile_id for old in fit['labels']]
    assignments['distance_to_medoid'] = fit['distances']
    assignments['silhouette'] = silhouette
    representatives = raw.iloc[medoids[medoid_order]].copy()
    representatives.insert(0, 'cluster', range(k))
    groups = assignments.groupby('cluster')
    cluster_sizes = groups.agg(profiles=('profile_id', 'size'), states=('state', 'nunique'),
                              years=('year', 'nunique'), mean_silhouette=('silhouette', 'mean'),
                              negative_silhouettes=('silhouette', lambda a: int((a < 0).sum())),
                              mean_distance=('distance_to_medoid', 'mean')).reset_index()
    cluster_sizes['profile_share'] = cluster_sizes.profiles / len(raw)
    feature_summaries = groups[FEATURES].agg(['mean', 'median', 'min', 'max', 'std'])
    feature_summaries.columns = ['_'.join(c) for c in feature_summaries.columns]
    feature_summaries = feature_summaries.reset_index()
    scaled_means = scaled[FEATURES].assign(cluster=labels).groupby('cluster').mean().reset_index()
    trace = pd.DataFrame(fit['history'])
    trace['medoid_indices'] = trace.medoid_indices.map(json.dumps)
    # This slow check is independent of the vectorized nearest-two swap calculation.
    candidates, reference = reference_swap_costs(d, fit['medoids'])
    fast_candidates, fast = swap_costs(d, fit['medoids'])
    if not np.array_equal(candidates, fast_candidates) or not np.allclose(reference, fast, atol=1e-9, rtol=0):
        raise AssertionError('Vectorized swap costs differ from full reassignment.')
    gap = float(max(0, fit['cost'] - reference.min()))
    if gap > TOL:
        raise AssertionError('The chosen solution admits an improving one-medoid swap.')
    euclidean_labels = best_fits['euclidean', k]['labels']
    metric_ari = adjusted_rand_score(fit['labels'], euclidean_labels)
    stability = []
    states = np.array(sorted(raw.state.unique()))
    for seed in range(100, 110):
        selected_states = np.random.default_rng(seed).choice(states, size=int(np.ceil(.8*len(states))), replace=False)
        indices = np.flatnonzero(raw.state.isin(selected_states).to_numpy())
        subset = d[np.ix_(indices, indices)]
        subset_fit, _ = fit_starts(subset, k, seeds=(seed, seed+1000))
        stability.append(dict(seed=seed, initialization_seeds=json.dumps([seed, seed+1000]), retained_states=len(selected_states), retained_profiles=len(indices),
                              k=k, ari_on_retained_profiles=adjusted_rand_score(labels[indices], subset_fit['labels']),
                              objective_per_retained_profile=subset_fit['cost']/len(indices),
                              medoid_profile_ids=json.dumps(raw.iloc[indices[subset_fit['medoids']]].profile_id.tolist())))
    stability = pd.DataFrame(stability)
    frames = {'candidate_k_comparison.csv': comparison, 'initialization_runs.csv': pd.DataFrame(start_rows),
              'cluster_assignments.csv': assignments, 'medoids.csv': representatives,
              'cluster_sizes.csv': cluster_sizes, 'cluster_feature_summary.csv': feature_summaries,
              'cluster_standardized_means.csv': scaled_means, 'objective_trace.csv': trace,
              'state_block_stability.csv': stability,
              'state_cluster_counts.csv': pd.crosstab(assignments.state, assignments.cluster).reset_index(),
              'year_cluster_counts.csv': pd.crosstab(assignments.year, assignments.cluster).reset_index()}
    for name, frame in frames.items():
        frame.to_csv(output / name, index=False, float_format='%.17g')
    inputs = json.loads((root / 'results/tables/transformation/transformed_manifest.json').read_text())
    for spec in inputs:
        if sha256(root / 'data/processed/transformed' / spec['file']) != spec['sha256']:
            raise AssertionError('An upstream transformed file changed.')
    summary = dict(profiles=len(raw), features=FEATURES, distance=PRIMARY_METRIC,
                   selected_k=k, k_candidates=list(K_VALUES), primary_metric_fixed_before_analysis=True,
                   selection='best silhouette among primary-metric solutions with every cluster >= ceil(0.05*n); objective-best of five starts per candidate',
                   minimum_cluster_size=minimum_size, silhouette=float(chosen.silhouette),
                   unrestricted_primary_best_k=int(unrestricted.k),
                   unrestricted_primary_silhouette=float(unrestricted.silhouette),
                   unrestricted_primary_min_cluster_size=int(unrestricted.min_cluster_size),
                   eligible_euclidean_best_k=int(euclidean_choice.k),
                   eligible_euclidean_best_silhouette=float(euclidean_choice.silhouette),
                   objective=fit['cost'], objective_per_profile=fit['cost']/len(raw), swaps=fit['swaps'],
                   converged=fit['converged'], tol=TOL, max_iter=MAX_ITER, random_seeds=list(SEEDS),
                   initialization_runs=len(start_rows), selected_start_mean_ari=float(chosen.mean_start_ari),
                   selected_start_min_ari=float(chosen.min_start_ari),
                   negative_silhouette_profiles=int((silhouette < 0).sum()),
                   euclidean_same_k_ari=float(metric_ari),
                   state_block_stability_mean_ari=float(stability.ari_on_retained_profiles.mean()),
                   state_block_stability_min_ari=float(stability.ari_on_retained_profiles.min()),
                   state_block_stability_max_ari=float(stability.ari_on_retained_profiles.max()),
                   state_block_seeds=list(range(100,110)),
                   state_block_scope='retain 80% of jurisdictions without replacement, fixed cohort scaling, BUILD plus two random starts; overlap ARI is descriptive sensitivity, not held-out accuracy',
                   medoid_profile_ids=representatives.profile_id.tolist(),
                   initial_medoid_profile_ids=raw.iloc[fit['initial_medoids']].profile_id.tolist(),
                   exact_swap_validation=True, best_remaining_swap_improvement=gap,
                   algorithm='PAM greedy BUILD plus exhaustive globally best improving one-medoid SWAP; random starts also use the same SWAP stage',
                   tie_policy='sorted profile IDs; candidate/removed-index order within tolerance; medoids represent themselves for zero-distance assignment ties; final cluster IDs follow medoid occupancy',
                   python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__, sklearn=sklearn.__version__,
                   upstream_transformed_hashes=inputs,
                   limitations='local optimum only; fixed-cohort preprocessing; repeated state-years; internal validation rather than predictive accuracy')
    (output / 'run_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    summary = run_clustering(parser.parse_args().root)
    print(json.dumps({key:value for key,value in summary.items() if key != 'upstream_transformed_hashes'}, indent=2))


if __name__ == '__main__':
    main()
