# Assignment implementation plan

Phases 0–11 have been implemented; Phase 5 retains the explicit course-plot coverage limitation documented below. Evidence is in [data_cleaning.md](data_cleaning.md), [data_selection.md](data_selection.md), [data_transformation.md](data_transformation.md), [descriptive_analytics.md](descriptive_analytics.md) and the eight executed notebooks, including [visualization.md](visualization.md), [fp_growth.md](fp_growth.md), [k_medoids.md](k_medoids.md), [mafia.md](mafia.md), [spark_fp_growth.md](spark_fp_growth.md) and [spark_k_medoids.md](spark_k_medoids.md). Phase 12 remains unimplemented and requires approval before starting. Implementation decisions follow the official assignment, validated data characteristics and established analytical methods.

## Requirement mapping

| Official requirement | Phase | Planned implementation and evidence |
|---|---|---|
| Cleaning to remove noisy data | 1 | Reusable cleaning functions; missingness, duplicates, schema and type checks, category aliases, invalid counts, outlier flags, total reconciliation; before/after quality tables and untouched raw hashes. Begin `01_Preprocessing.ipynb`. |
| Select task-relevant attributes | 2 | File/feature rationale, candidate-key uniqueness and overlap checks, explicit join cardinalities, exclusion list and population definitions. Extend preprocessing notebook. |
| Transform data for the task | 3 | Document encodings, denominators, scaling, bin edges and transaction schema; save feature/transaction data and parameters. Extend preprocessing notebook. |
| Exhaustive descriptive analytics | 4 | `02_Descriptive_Analytics.ipynb`: counts, frequencies, mean/median/mode, range, sample variance/SD, quartiles/IQR, skewness, kurtosis and correlations; state, time, demographic and prisoner-category summaries. Record formula conventions and valid denominators. |
| At least 10 unique course plots with key inferences | 5 | `03_Visualization.ipynb`: at least 10 suitable plot types, 300 dpi figures, labels/units, source tables, suitability notes and numeric inferences. Reconcile the slide-coverage gap below before claiming full compliance. |
| Association rules using FP-Growth | 6 | `04_FP_Growth.ipynb`: validated mlxtend FP-Growth; exact support counts, confidence and lift, threshold sensitivity, interpretable aggregate transactions, saved itemsets/rules. |
| Naive Bayesian classification or K-Medoids as relevant | 7 | Recommend K-Medoids only: `05_Classification_or_Clustering.ipynb`, documented PAM medoid swaps, distance/scaling, candidate k values, silhouette, objective and stability; actual representative observations and interpreted cluster profiles. |
| MAFIA and maximal outputs | 8 | `06_MAFIA.ipynb`: faithful MAFIA, bitmap support counting, depth-first head/tail search and documented pruning; compare to maximal sets derived independently from FP-Growth. Validate frequency and absence of frequent one-item extensions. |
| Explicit relevant algorithm outputs and performance measures | 6–10 | Save itemsets/rules, supports, cluster assignments/medoids, objective/silhouette, equivalence checks and benchmark tables; explain all outputs. A dendrogram is relevant to hierarchical clustering, not a required K-Medoids output. |
| Test two listed techniques in PySpark and evaluate enhancement | 9–10 | `07_PySpark.ipynb`: Spark FP-Growth and faithful distributed K-Medoids; compare identical data/parameters and report measured speedup or slowdown. No replacement by K-Means. |
| Clearly commented implementations with explained outputs | 1–12 | Modular Python under `src/`, executable notebooks only when work begins, short comments, saved outputs, parameters and execution instructions. |
| Overall PDF report and source submission | 11 | Complete academic PDF with title, abstract, problem, data, methods, actual results, at least 10 figures/inferences, algorithms, benchmarks, limitations, conclusions, references and appendices. |
| Final completeness and reproducibility | 12 | Requirement compliance table, fresh execution, artifact/figure consistency checks, dependency verification and submission audit; mark any gaps explicitly. |

This table records the project plan, not a completed-project compliance claim. Current evidence covers setup, dataset audit, cleaning, selection, transformation, descriptive analytics, 26 visualization figures, FP-Growth with independently verified itemsets/rules, tested PAM K-Medoids with medoids and stability evaluation, and verified bitmap MAFIA maximal itemsets/rules from maximal unions. Later phases retain their planned status.

## Method choices and original design rationale

The following design notes record the original rationale. Executed outcomes and any differences from the plan are recorded in the phase-status sections below and the current README.

We recommend **K-Medoids** for profiling aggregate state-year prison systems. The dataset contains aggregated counts and capacities, without a natural prisoner-level outcome or labeled examples. A classifier using a contemporaneous occupancy label and its defining population/capacity fields would leak the answer. Predicting legal status from a table already grouped by legal status would also require a substantially different and carefully justified task.

Phase 2 selected five features: occupancy ratio, undertrial share, female share, age 18–30 share and illiterate share. Phase 3 constructs them for 437 complete, compatible, positive-denominator state-years, with saved z-score parameters and discretization rules. The [feature contract](../results/tables/selection/feature_contract.json) specifies their inputs/formulas; [transformation parameters](../results/tables/transformation/parameters.json) record the executed fit scope. We omit complementary share blocks, identifiers and contact fields from the feature representation. Protected demographic attributes may support aggregate description but must not become individual risk labels.

The primary observation is one state/UT-year. Jail-type population/capacity measurements have documented disagreements, so they are not silently substituted for the verified total-level profiles. We distinguish repeated state-year observations from independent states. Phase 3 provides standardized features; Phase 7 will compare justified Manhattan or Euclidean distance settings, examine k=2 through a conservative upper limit supported by the sample size, and use fixed seeds where initialization is random. Medoids must always be actual observations. A faithful PAM implementation avoids reliance on an unverified Python 3.14 binary package. Small hand-checkable examples and an independent trusted implementation/reference will validate it in Phase 7.

Phase 3 prepares 437 state-year transactions with five namespaced profile items each. Occupancy uses fixed 100%/150% boundaries; demographic shares use recorded cohort tertiles. The Boolean representation has fifteen item columns. Identifiers and redundant complementary encodings are excluded, and equal item patterns across different state-years are retained. We do not expand aggregate counts into invented prisoner records or treat zero counts as missing by default. Phase 6 executes support fractions 0.05, 0.10, 0.19 and 0.20 and confidence cutoffs 0.60, 0.70 and 0.80. See its report for the null baseline and separately labeled exploratory results.

MAFIA must follow the original algorithm, with vertical bitmaps, depth-first search, parent-equivalence pruning, head-union-tail pruning and dynamic ordering documented as implemented. Pincer Search is distinct from MAFIA and is not used as a replacement. Maximal itemsets do not preserve subset support counts. We must recount required subsets in the original transactions, or use verified FP-Growth supports, before computing confidence/lift for rules whose unions are maximal. Call these rules derived from maximal unions and explain how this relates to the assignment's ambiguous phrase “maximal association rules (MFIs).” Do not imply they exhaust all rules.

## Spark experiment design

Spark supplies FP-Growth. Its documented clustering estimators do not include K-Medoids. For the second comparison, plan a custom Spark implementation of the same PAM objective and medoid-swap procedure: distribute assignment and candidate-swap cost calculations, reduce costs, and select the best improving swap with deterministic tie-breaking. Keep identical initial medoids, feature order, distance, k, convergence tolerance and stopping criteria in Python and Spark. Only parallelizing data loading while fitting entirely in Python would not constitute a Spark implementation.

Validate FP-Growth using exact transaction counts and integer support counts before floating-point metrics. Spark's built-in rules use single-item consequents; restrict Python rule comparison to the same rule family, while retaining the full Python results separately. Validate K-Medoids with objective values, medoid IDs, assignment distances and labels up to permutation. Floating-point reduction order and tied optima require documented tolerances.

Use the actual final dataset for primary benchmarks. Report end-to-end time including Spark startup separately from warmed algorithm time; materialize Spark actions because execution is lazy. Match output materialization, caching policy and preprocessing scope. Use at least three measured repetitions where practical, record warm-up separately, and report median and spread. Define speedup as Python time divided by Spark time. Record cores, partitions, driver/executor memory, Spark/Python/Java versions, input rows and item counts. If measuring memory, include the JVM as well as the Python process and state the measurement method.

The downloaded data is only 9.22 MB and the proposed aggregate matrix is much smaller. Spark startup and scheduling overhead may dominate. Performance enhancement is an empirical question: report slowdowns honestly and explain why this dataset cannot establish large-data scalability. Do not fabricate or silently replicate data to create a favorable comparison.

Current host: Intel Core i5-12500H, 16 logical CPUs, about 14 GiB reported RAM; Python 3.14.4 and OpenJDK 25.0.5. The current Spark 4.3 documentation lists Python 3.11+ and Java 17/21/25. This supports preliminary feasibility, but PySpark has not been installed or executed in Phase 0. Check the actual pinned release, worker serialization and JVM startup before Phase 9 experiments. Reserve sufficient disk/memory; the initial host check found about 11 GB disk free. Avoid allocating every available core by default.

## Visualization coverage gap

Lecture 4 explicitly covers pie, histogram, dot, stem-and-leaf, scatter and box plots, with a bar-chart comparison. Lectures 20–21 add dendrograms; Lecture 13 includes ROC curves. This does not establish ten suitable unique plot types for aggregate prison profiles. A ROC curve would be inappropriate merely to reach ten when clustering is selected, and rotated or recolored copies are not unique plot types.

A provisional suitable set is bar, pie, histogram, box, scatter, dot, stem-and-leaf for a manageable subset, line for trends, heatmap for profiles/correlation, and area for mutually exclusive category trends. The last three are supplementary to the supplied explicit plot coverage and must be identified as such. We must resolve whether supplementary plots satisfy the course requirement, or obtain additional course references, before marking that requirement fully satisfied. This is a documented planning limitation, not a reason to invent lecture coverage.

## References

- Official local assignment: `question.txt`.
- [Kaggle dataset](https://www.kaggle.com/datasets/rajanand/prison-in-india/data).
- Burdick, Calimlim and Gehrke (2001), [MAFIA: A Maximal Frequent Itemset Algorithm for Transactional Databases](https://www.cs.cornell.edu/johannes/papers/2001/icde2001-mafia.pdf).
- Apache Spark [FP-Growth documentation](https://spark.apache.org/docs/latest/ml-frequent-pattern-mining.html), [clustering estimators](https://spark.apache.org/docs/latest/ml-clustering.html), [system requirements](https://spark.apache.org/docs/latest/) and [Python installation](https://spark.apache.org/docs/latest/api/python/getting_started/install.html), consulted 2026-11-21. Pin release-specific references when Spark is installed.

## Phase 5 implementation status

Ten visualization types are implemented and executed; see [visualization.md](visualization.md). Strict ten-course-types compliance remains unresolved because three types supplement the supplied slide coverage. Phase 6 is documented below.

## Phase 6 implementation status

FP-Growth is implemented with mlxtend 0.25.0 and executed in `04_FP_Growth.ipynb`. The fixed 10% support / 70% confidence baseline returns 75 itemsets and zero rules. The separately reported 5% / 70% exploratory setting returns four rules. All twelve declared parameter combinations pass exact itemset-support and complete rule-set validation. See [fp_growth.md](fp_growth.md) for definitions, technical references, outputs and limitations. Phase 7 is documented below.

## Phase 7 implementation status

A faithful PAM BUILD/best-SWAP implementation is executed in `05_Classification_or_Clustering.ipynb`. Primary Manhattan distance with k=2–8, five starts per setting and a declared 22-profile minimum selects k=2; actual medoids are Kerala–2002 and Jharkhand–2007. Silhouette is 0.1745 and initialization/state-block sensitivity is substantial. The report explicitly discloses the higher-scoring excluded Manhattan k=7 and eligible Euclidean k=7 alternatives. Verification covers exhaustive small examples, every candidate swap of the retained real solution, objectives, assignments and medoid identities. See [k_medoids.md](k_medoids.md). Phase 8 is documented below.

## Phase 8 implementation status

Bitmap MAFIA is implemented in `src/mining/mafia.py` and executed in `06_MAFIA.ipynb`, following the original head/tail search with PEP, FHUT, HUTMFI and dynamic ordering. It returns 60 baseline MFIs at 10% support and 87 exploratory MFIs at 5%. Exact-count, maximality, FP-Growth and pruning-ablation checks pass. Rules use explicitly recounted subset supports; the report demonstrates a valid FP rule omitted by restricting unions to MFIs. Relative bitmap compression and specialized indexing are omitted without performance claims. See [mafia.md](mafia.md). Phase 9 is documented below.

## Phase 9 implementation status

Spark 4.3.0 FP-Growth is executed on the shared 437 transactions. All twelve parameter settings match Python in exact itemset counts and single-consequent rule metrics. Two scenarios have three measured repetitions per engine after excluded warm-ups. Spark is approximately 40–50 times slower in warmed median runtime; no enhancement is claimed. Startup, full configuration, hardware and scoped process/JVM RSS samples are recorded. See [spark_fp_growth.md](spark_fp_growth.md). Phase 10 is documented below.

## Phase 10 implementation status

`08_PySpark_KMedoids.ipynb` independently executes distributed PAM SWAP without rerunning Phase 9 timings. Workers compute distance rows, assignments and all candidate-swap partial costs; the driver combines costs and selects swaps. Two initializations and three paired measured repetitions agree with Python (ARI 1.0; swap-cost differences below 2.3e−12). Warm medians are 0.016449s Python versus 0.194666s Spark, a 30.19× slowdown. Fixed initialization/cached-distance scope, memory, startup and scalability limitations are disclosed in [spark_k_medoids.md](spark_k_medoids.md). Phase 11 is documented below.

## Phase 11 implementation status

The [academic PDF](India_Prison_Analytics_Report.pdf) is compiled from local LaTeX sources, with 91 pages, 42 figures, 35 tables, full global-statistics and maximal-itemset appendices, and the supplied author/course/institution details. Report-specific checks verify references, table layout, embedded artifacts and preserved data hashes. The PDF is retained for the repository; LaTeX source/intermediate files are ignored. See [report_build_manifest.json](report_build_manifest.json). The documented assignment plot-coverage point remains for Phase 12; no full compliance claim is made yet.
