# Data transformation report

Phase 3 constructs reproducible numeric and transaction representations for the 437 state-year profiles selected in Phase 2. It produces five continuous features, their standardized representation, five discretized categories per profile, a Boolean item matrix, and JSON inputs for later Spark comparisons. No descriptive analytics, plots, clustering, frequent-itemset mining, association rules or runtime benchmarks have been performed.

## Source aggregation and lineage

The selected cohort, source tables and exclusions are unchanged. We verify all 78 upstream data files against their recorded SHA-256 hashes: 37 raw files, 37 cleaned files and four selected files. Phase 3 reads the selected base, age and education count files, preserving one profile per state/UT-year. The reference file is also hash-verified to freeze the full selection snapshot.

We validate unique state-year base keys, unique source-record IDs and exact category grids before aggregation. Every selected age group has sixteen records: nationality × legal status × gender. Every selected education group has twelve records: schooling level × gender. Numeric counts must be finite, nonmissing, nonnegative and integral. Prisoner and capacity denominators must be strictly positive; no epsilon replacement, zero-share imputation or clipping is applied.

Age_18_30 counts are summed independently over nationality, legal status and gender. Illiterate counts are independently summed over gender and the four mutually exclusive legal statuses. Only those state-year aggregates join the base table, with one-to-one cardinality validation. Native age and education records never join each other. The complete education distribution is also checked against the common population denominator, and each demographic numerator must not exceed that denominator.

`profile_id` is the transparent metadata identifier `state|year`; neither it, state, year nor source-record IDs enter the feature matrix or transaction items. The [profile lineage table](../results/tables/transformation/profile_lineage.csv) links every profile to the original population/capacity source records and the sixteen age/twelve education records used for its numerators. Source IDs refer to the unchanged cleaned/raw observation lineage established earlier.

## Constructed features and data types

| Feature | Formula | Interpretation and bounds |
|---|---|---|
| occupancy_ratio | total_prisoners / total_capacity | Capacity utilization ratio; nonnegative and may exceed 1. A value of 1 corresponds to 100% capacity. |
| undertrial_share | undertrial_prisoners / total_prisoners | Fraction of the same aggregate population recorded as undertrials; in [0,1]. |
| female_share | female_prisoners / total_prisoners | Fraction of the same population recorded as female; in [0,1]. |
| age_18_30_share | age_18_30_count / total_prisoners | Fraction in the source age band labeled 18–30; in [0,1]. |
| illiterate_share | illiterate_count / total_prisoners | Fraction in the source education category Illiterate; in [0,1]. |

Counts retain integer types; constructed features and standardized vectors use float64. Years remain integer metadata and names/identifiers remain strings. No arbitrary integer coding of nominal categories is used. These are aggregate system profiles, not individual prisoner features or causal risk factors. The age-band endpoints inherit the source labels; they do not establish person-level birth-date precision.

The feature order is fixed as occupancy_ratio, undertrial_share, female_share, age_18_30_share, illiterate_share. Every output retains the same 437 profile identities. IDs and raw counts are excluded from standardized distance inputs. We omit complementary composition blocks rather than including every gender, age, education or status share together with their totals. No claim of empirical feature independence is made.

## Standardization for K-Medoids

We fit scikit-learn StandardScaler with centering and scaling on the complete selected cohort. Each state-year has equal weight; profiles are not weighted by prisoner count, and states with more observed years contribute more observations. For feature j, the transformation is z = (x − mean_j) / scale_j, using population variance with ddof=0. A zero-variance feature would have scale 1 under the saved scaler convention. Z-score normalization expresses features in comparable standardized units; it does not make their distributions Gaussian.

The exact parameters, feature order, fit-profile IDs, library version and feature formulas are saved in [parameters.json](../results/tables/transformation/parameters.json). The following values are transformation fit parameters, not a completed descriptive statistical analysis:

| Feature | Fitted mean | Variance ddof=0 | Scale | Fit rows |
|---|---:|---:|---:|---:|
| occupancy_ratio | 1.18993976519 | 0.367015722504 | 0.605818225629 | 437 |
| undertrial_share | 0.664763757518 | 0.0208730052569 | 0.14447492951 | 437 |
| female_share | 0.0382243733897 | 0.000388538180342 | 0.0197113718534 | 437 |
| age_18_30_share | 0.466551862379 | 0.0132644715578 | 0.115171487608 | 437 |
| illiterate_share | 0.276484400587 | 0.0166906777619 | 0.129192405976 | 437 |

The CSV and JSON retain more precision than the displayed values. Standardization is checked against StandardScaler directly, and the stored numeric matrix has column means near zero and population standard deviations near one within numerical tolerance. Original profile values are preserved separately; standardized values can be negative and are not association-mining items. StandardScaler can give extreme observations substantial influence. We retain those observations and do not winsorize or automatically substitute a robust/log transform. Any later sensitivity experiment must be identified explicitly.

## Fit scope and leakage safeguards

The current fit scope is the entire selected cohort for descriptive unsupervised analysis. No train/test accuracy or out-of-sample performance is claimed. Cohort-wide scaling and quantiles are appropriate to describe that fixed cohort, but must not be reused to claim a leakage-free held-out evaluation.

`fit_parameters(features, fit_profile_ids=...)` supports an explicit fitting subset. It records only the supplied IDs and fits both scaling and quantile cuts on those rows. `scale_profiles` and `discretize_profiles` apply the saved parameters without refitting. A regression test compares subset-fitted parameters with independent subset statistics and confirms that applying them to other rows leaves the parameters unchanged. Future state/time holdouts must use that fit/apply separation. Repeated years within a state remain related observations. [Scikit-learn’s preprocessing guidance](https://scikit-learn.org/stable/common_pitfalls.html) supports consistent application of training-fitted transformations.

## Discretization rules

Occupancy uses three fixed, interpretable intervals: x ≤ 1, 1 < x ≤ 1.5, and x > 1.5. The 100% boundary follows the ratio definition; the 150% boundary is a stated analytical choice, not an official safety or legal standard. No threshold was selected by mining rules or optimizing outcomes.

Each of the four demographic shares uses fitted 1/3 and 2/3 quantiles with linear interpolation. The labels lower_tertile, middle_tertile and upper_tertile are relative to the fitted cohort, not universal thresholds or favorable/unfavorable judgments. We use value-based cuts, not rank-based splitting: equal values receive equal labels. Ties can therefore make bin counts unequal. If the two cuts coincide, fitting fails and requires an explicitly revised rule rather than silently forcing three categories.

The comparison rule is identical for all five features: x ≤ first_cut receives the first label; first_cut < x ≤ second_cut receives the second; x > second_cut receives the third. Quantile cut points have full precision in the saved JSON/CSV. Printed approximations below must not replace those saved values during execution.

| Feature | First cut | Second cut | Method |
|---|---:|---:|---|
| occupancy_ratio | 1 | 1.5 | fixed occupancy bands |
| undertrial_share | 0.612653745489 | 0.705517964563 | cohort tertiles |
| female_share | 0.0301701453285 | 0.0433531880577 | cohort tertiles |
| age_18_30_share | 0.41958232002 | 0.483001763595 | cohort tertiles |
| illiterate_share | 0.230263157895 | 0.338156768093 | cohort tertiles |

Occupancy labels are within_capacity, over_100_to_150pct and over_150pct. Share labels are lower_tertile, middle_tertile and upper_tertile. A saved boundary specification and tests at both exact cuts and the next representable value above the upper cut verify the interval semantics. Binning loses within-interval differences; cohort changes can alter quantile cuts, so later algorithms must use the same frozen parameters.

## Transactions and Boolean encoding

One transaction represents one selected state-year and contains exactly one namespaced item from each of the five feature families. For example, an item is `female_share=lower_tertile`. The full vocabulary has fifteen items, and all fifteen occur in these transformed inputs. We encode the nominal categories as Boolean item-membership columns for the Python mining implementations. No ordinal category numbers are passed into clustering.

There are 437 transactions, each of length five. The Boolean matrix is 437 × 15 with exactly 2,185 true cells. Its CSV also includes a profile_id metadata column outside that matrix. Duplicate item patterns across different profile IDs are deliberately preserved: removing them would change the empirical transaction population. Each transaction contains unique items, and no state/year ID, source-record ID, exact population count, complementary duplicate fact or future cluster assignment is included as an item. No aggregate count is expanded into invented prisoner records.

Support in later phases will therefore refer to the fraction of these 437 state-year transactions, not the fraction of prisoners or independent states. This phase does not calculate support, confidence, lift or any frequent itemsets. Min-support and rule thresholds remain Phase 6/8/9 parameters. Exact Boolean decoding is checked against every JSON transaction.

## Python and Spark input equivalence

Numeric Spark inputs are JSON records containing profile_id and an array of five standardized doubles in the recorded feature order. Association inputs are JSON records containing profile_id, state/year metadata and an items array; only items will enter Spark FP-Growth. The [Spark input contract](../results/tables/transformation/spark_input_contract.json) supplies explicit struct/array type metadata, feature order and vector length for the later implementation.

We verify ordinary JSON write/read round trips and exact equality between the exported numeric arrays and the Python matrix. We also verify that every Boolean row decodes to the corresponding transaction item set. This validates saved data equivalence only: PySpark has not been installed or executed in Phase 3, and the schema must still be instantiated and runtime-tested in the Spark phases. No performance or output-equivalence claim about mining algorithms is made. Use the saved vectors without independently refitting a Spark scaler, so benchmark inputs remain identical.

## Outputs and reproducibility

| File under data/processed/transformed | Rows | Contents |
|---|---:|---|
| profile_counts.csv | 437 | Native population/capacity counts and independently aggregated age/illiterate numerators; profile identity. |
| profile_features.csv | 437 | State/year/ID metadata plus five continuous ratios. |
| clustering_features.csv | 437 | ID metadata plus five standardized numeric features in fixed order. |
| discretized_profiles.csv | 437 | State/year/ID metadata plus five nominal bin labels. |
| transactions_onehot.csv | 437 | ID metadata plus fifteen Boolean item columns. |
| transactions.jsonl | 437 | Profile identity and sorted unique item arrays; shared association-mining input. |
| spark_profiles.jsonl | 437 | Profile identity and ordered standardized numeric arrays. |

[transformed_manifest.json](../results/tables/transformation/transformed_manifest.json) records output hashes, formats, row counts and CSV dtypes. `load_transformed(root, filename)` checks the hash before loading and restores saved dtypes. Floating-point CSV values are written with seventeen significant digits; the pinned pandas environment was checked for exact numeric round trips. JSON exports reject NaN/Infinity. [input_provenance.json](../results/tables/transformation/input_provenance.json) records all upstream file hashes. The [environment snapshot](../results/tables/transformation/environment_phase3.json) records Python and installed package versions.

Run `python -m src.preprocessing.transformation`, or execute [01_Preprocessing.ipynb](../notebooks/01_Preprocessing.ipynb), which reproduces Phases 1–3 in order. Scikit-learn 1.9.1 and SciPy 1.18.1 are added to the pinned requirements; other dependencies are unchanged. All operations are deterministic; no random sampling or seed is needed at this phase.

## Verification and limits

Ten Phase 3 tests supplement the fourteen cleaning and nine selection tests. They cover independent numerator summation and rational-formula checks, saved scaler replay, explicit fitting subsets, exact cut boundaries, invalid shares/nonfinite values, missing/duplicate grids, zero denominators, transaction multiplicity, Boolean decoding, JSON vector equality, output identities and manifest integrity. The notebook has twenty-three executable code cells: seven cleaning, eight selection and eight transformation cells. Execution and determinism results are recorded in [verification.json](../results/tables/transformation/verification.json).

The 437-row complete-case cohort retains the Phase 2 selection limitations and does not form a balanced historical panel. Standardization is sensitive to extremes, demographic features can remain correlated, quantile labels are cohort-dependent, and discretization discards numeric detail. Neither the profile nor transaction representation identifies individual prisoners or establishes causality. Full-cohort parameters support the planned descriptive unsupervised work; any future holdout study must refit using training rows only.

## References

- Local assignment `question.txt` and Lecture 5 KDDPhases, slides 15–17: feature construction, aggregation, normalization and discretization.
- [Scikit-learn StandardScaler documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html) for the fitted scaling representation; implementation checked in the installed 1.9.1 environment.
- [Data selection report](data_selection.md) for the cohort, observation units, excluded attributes and denominator compatibility.

Phase 3 is complete. Phase 4 Descriptive Analytics requires separate approval.
