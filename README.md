# India Prison Analytics

**Descriptive and Predictive Analytics on Indian Prison Statistics**

We analyze historical Indian prison statistics to study population, capacity, legal status and demographic patterns. The project includes data preparation, descriptive statistics, visualization, association mining, K-Medoids clustering and two Python–PySpark comparisons.

**Current status:** Phases 0–11 are implemented. The academic PDF is complete; the final requirement-compliance audit remains. The latest recorded project verification contains **78 passing tests**.

[Download the academic report](report/India_Prison_Analytics_Report.pdf) — 91 pages, 42 figures, complete methodology, results, references and appendices.

## Objectives

- Preserve the original data and document cleaning, selection and transformation.
- Describe prison conditions through appropriate statistics and visualizations.
- Generate association rules with FP-Growth and maximal itemsets with MAFIA.
- Identify representative aggregate profiles using K-Medoids.
- Compare Python and Spark outputs, execution times and process-memory observations.
- Present reproducible evidence, assumptions and limitations in the final report.

## Dataset

Source: [Indian Prison Statistics](https://www.kaggle.com/datasets/rajanand/prison-in-india/data), uploaded by Rajanand. The snapshot was downloaded on **21 November 2026** using the Kaggle CLI. The downloader reports **CC BY-SA 4.0**; applicable attribution and share-alike terms apply to adapted data.

The dataset contains **37 CSV files**, **159,032 nonblank records**, and approximately **9.22 MB** of CSV data. Most statistical tables cover **2001–2013**; some administrative and financial files describe other periods. These are aggregate records, not individual prisoner histories.

Raw files are preserved. We select **437 compatible state-year profiles** from 35 historical jurisdictions for mining and clustering. A separate population/capacity reference covers 447 state-years; descriptive analyses state their own eligible coverage. Historical geography, changing coverage and repeated years within states limit interpretation.

See the [dataset audit](report/dataset_audit.md), [file inventory](results/tables/dataset_inventory.json) and [selection methodology](report/data_selection.md).

## Completed work

| Phase | Work completed | Main evidence |
| --- | --- | --- |
| 1 — Cleaning | Repaired the religion header, standardized documented categories, removed three confirmed duplicate records, quarantined ten conflicting records, and recovered two independently verifiable counts. | [Cleaning report](report/data_cleaning.md) |
| 2 — Selection | Validated observation keys, denominators and source coverage; selected four primary sources and defined 27 descriptive source views. | [Selection report](report/data_selection.md) |
| 3 — Transformation | Constructed five ratios, saved z-score parameters and bin boundaries, and prepared matching Python/Spark inputs. | [Transformation report](report/data_transformation.md) |
| 4 — Descriptive analysis | Generated 22 statistical tables covering distributions, state/year comparisons, demographics and correlations. | [Descriptive report](report/descriptive_analytics.md) |
| 5 — Visualization | Generated 26 meaningful figures with titles, units, source data and interpretations. | [Visualization notebook](notebooks/03_Visualization.ipynb) |
| 6 — FP-Growth | Mined frequent itemsets and rules across 12 support/confidence settings and verified exact counts. | [FP-Growth report](report/fp_growth.md) |
| 7 — K-Medoids | Compared k=2–8 and two distances, identified real medoids, and assessed initialization/geographic sensitivity. | [Clustering report](report/k_medoids.md) |
| 8 — MAFIA | Implemented bitmap maximal-itemset search, checked maximality, and generated rules using recounted subset supports. | [MAFIA report](report/mafia.md) |
| 9 — Spark FP-Growth | Verified all 12 parameter settings against Python and measured repeated runtimes. | [Spark FP-Growth report](report/spark_fp_growth.md) |
| 10 — Spark K-Medoids | Distributed PAM cost calculations, verified optimization trajectories, and measured repeated runtimes. | [Spark K-Medoids report](report/spark_k_medoids.md) |
| 11 — Academic report | Compiled a detailed LaTeX PDF using saved statistics, 42 figures, algorithms, benchmarks and appendices. | [Final PDF](report/India_Prison_Analytics_Report.pdf) |

## Methods and findings

### Data preprocessing

Cleaning retains **159,019 records** in 37 cleaned source tables. Missing and contradictory values that cannot be resolved from valid evidence remain documented. Outliers are flagged and retained. Native marginal tables are aggregated independently before validated state-year joins, preventing row multiplication and double counting.

The five profile features are occupancy ratio, undertrial share, female share, age-18–30 share and illiterate share. Clustering uses saved standardized numeric values. Association mining uses one categorical item per feature: fixed occupancy bands and cohort-relative demographic tertiles. Identifiers and raw count magnitudes do not enter the mining features.

There are **437 transactions**, each containing five unique items from a 15-item vocabulary. Repeated patterns across different state-years are retained. One transaction represents a state-year, so support is not a proportion of prisoners.

### Descriptive analysis and visualization

The fixed 34-jurisdiction panel shows prisoner-count growth of **31.33%**, compared with **51.41%** capacity growth over 2001–2013. Its pooled occupancy falls from **136.53% to 118.43%**. In the available 2013 reference, undertrials account for **67.60%** of **411,992** reported prisoners. Uttar Pradesh has the largest count (**83,518**); Chhattisgarh has the highest reported occupancy (**260.96%**).

The visualization notebook begins with population, overcrowding, capacity and legal status, followed by demographic composition, convicted IPC patterns and feature relationships. Each analysis cell contains plotting code, renders the figure directly and saves a 300 dpi image. Duplicate analytical views are omitted. Crime-head plots describe recorded convicted inmates, not crime incidence or victim counts.

See the [descriptive notebook](notebooks/02_Descriptive_Analytics.ipynb), [visualization notebook](notebooks/03_Visualization.ipynb), [figure catalogue](results/plots/plot_catalog.json) and [visualization interpretations](report/visualization.md).

### FP-Growth

The baseline **10% support / 70% confidence** produces **75 frequent itemsets and no qualifying rules**. The exploratory **5% / 70%** setting produces **166 itemsets and four rules**, with confidence **73.21–73.91%** and lift **1.777–2.205**. We retain the null baseline rather than presenting only the lower-threshold results.

All twelve settings are checked against independent transaction counts. Confidence expresses conditional co-occurrence, not prediction accuracy. See the [executed notebook](notebooks/04_FP_Growth.ipynb), [baseline itemsets](results/tables/fp_growth/frequent_itemsets.csv), [exploratory rules](results/tables/fp_growth/exploratory_rules.csv) and [parameter comparison](results/tables/fp_growth/parameter_comparison.csv).

### K-Medoids

We apply PAM using Manhattan distance on standardized features. Among k=2–8 candidates with at least 22 profiles per cluster, the declared selection rule chooses **k=2**. The medoids are **Kerala–2002** and **Jharkhand–2007**, representing **270** and **167** profiles. Their cluster median occupancies are **90.74%** and **160.38%**.

Average silhouette is **0.1745**, with 23 negative-silhouette profiles. Initialization and state-block sensitivity indicate weak, exploratory grouping. The report discloses the higher-scoring excluded Manhattan k=7 candidate and the different Euclidean selection. These clusters are not stable classes of people or permanent labels for states.

See the [executed notebook](notebooks/05_Classification_or_Clustering.ipynb), [medoids](results/tables/k_medoids/medoids.csv), [assignments](results/tables/k_medoids/cluster_assignments.csv) and [sensitivity results](results/tables/k_medoids/state_block_stability.csv).

### MAFIA

The implementation uses vertical integer bitmaps, head/tail depth-first search, parent-equivalence pruning, FHUT, HUTMFI and dynamic ordering. At **10% support**, it returns **60 maximal pairs**; at **5%**, it returns **87 maximal sets**, including 64 triples. Results match exact counting and independently derived FP-Growth maximal sets.

Maximal itemsets do not preserve exact subset supports. We recount the required supports before calculating confidence and lift. At 5% support / 60% confidence, maximal unions generate **15 rules**, compared with **16** complete FP-Growth rules. The omitted rule demonstrates why maximal-union rules are not the complete rule family.

See the [executed notebook](notebooks/06_MAFIA.ipynb), [maximal itemsets](results/tables/mafia/maximal_itemsets.csv), [exploratory rules](results/tables/mafia/exploratory_maximal_union_rules.csv) and [omitted-rule analysis](results/tables/mafia/omitted_fp_rules.csv).

### Python and PySpark comparisons

Both Spark implementations run locally with two threads and two partitions. FP-Growth agrees with Python in itemsets and comparable single-consequent rules. Spark PAM agrees in medoid identities, partitions (**ARI 1.0**), assignment distances and swap trajectories.

The table below uses the latest saved benchmark CSVs. Each setting has one excluded warm-up and three measured repetitions per engine. Speedup is Python median divided by Spark median; the slowdown column shows the reciprocal.

| Experiment | Python median (s) | Spark median (s) | Spark / Python time |
| --- | --- | --- | --- |
| FP-Growth, 5% support / 70% confidence | 0.004644 | 0.186462 | 40.15× |
| FP-Growth, 10% support / 70% confidence | 0.003667 | 0.184746 | 50.38× |
| PAM K-Medoids, k=2 | 0.006449 | 0.194666 | 30.19× |

**No performance enhancement is observed on this small dataset.** The reports distinguish warmed mining/optimization scope from startup and preparation costs. PAM uses identical saved initialization and prepared distance matrices on both sides. RSS measurements describe scoped process footprints, including the JVM/workers for Spark; they are not isolated algorithm-allocation measurements.

See the [Spark FP-Growth notebook](notebooks/07_PySpark.ipynb), [Spark K-Medoids notebook](notebooks/08_PySpark_KMedoids.ipynb) and [benchmark records](results/benchmarks/). The separate notebooks allow either experiment to be repeated independently.

## Project structure

```text
India-Prison-Analytics/
├── data/
│   ├── raw/                    # unchanged Kaggle CSVs
│   └── processed/              # cleaned, selected and transformed data
├── notebooks/                  # eight executed analysis notebooks
├── src/
│   ├── preprocessing/
│   ├── analytics/
│   ├── mining/
│   └── utils/
├── results/
│   ├── plots/
│   ├── tables/
│   └── benchmarks/
├── report/                     # final PDF, methods and verification records
├── tests/
├── slides/                     # local reference materials, ignored by Git
├── question.txt                # local assignment, ignored by Git
├── README.md
├── requirements.txt
└── .gitignore
```

## Installation and execution

The tested environment uses **Python 3.14.4**, **Java 25**, **PySpark 4.3.0** and the versions pinned in [requirements.txt](requirements.txt). The Spark JSON/RDD paths are verified; pandas-conversion, Arrow and pandas-on-Spark APIs are not covered by these checks.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

The dataset is already present. Download only when the raw CSVs are absent:

```bash
kaggle datasets download -d rajanand/prison-in-india -p data/raw --unzip
```

If authentication is required, use the Kaggle CLI configuration and keep credentials outside version control. The raw religion header is repaired only in the cleaned copy; avoid interpreting that raw file with default parsing before applying preprocessing.

Run notebooks from top to bottom, or use the provided runner:

```bash
python -m src.utils.execute_notebook notebooks/01_Preprocessing.ipynb
python -m src.utils.execute_notebook notebooks/02_Descriptive_Analytics.ipynb
python -m src.utils.execute_notebook notebooks/03_Visualization.ipynb
python -m src.utils.execute_notebook notebooks/04_FP_Growth.ipynb
python -m src.utils.execute_notebook notebooks/05_Classification_or_Clustering.ipynb
python -m src.utils.execute_notebook notebooks/06_MAFIA.ipynb
python -m src.utils.execute_notebook notebooks/07_PySpark.ipynb
python -m src.utils.execute_notebook notebooks/08_PySpark_KMedoids.ipynb
python -m unittest discover -s tests -q
```

Jupyter and local Spark require local socket access. Analysis modules can also run from the repository root; their reports list the corresponding commands. Repeating benchmarks produces new timing observations. Spark console settings suppress routine startup/progress messages while retaining errors.

## Verification and limitations

The latest recorded checks include **78 passing tests**, unchanged hashes for **85 raw/prepared input files**, exact mining comparisons, medoid/swap checks and successful notebook execution. Verification records are stored alongside the outputs. This documentation update does not rerun notebooks or benchmarks.

Historical aggregate data, related state-years, source-definition differences, missing values and unequal geographic coverage restrict interpretation. Scaling/binning uses the selected cohort and does not establish held-out predictive performance. Rule confidence is not accuracy; implementation ARI is agreement between partitions, not classification performance. Weak clustering and Spark slowdowns are reported as observed.

The final compliance review must confirm the assignment's plot-coverage requirement. The [implementation plan](report/implementation_plan.md) records that open point and the remaining submission work. No complete-project compliance claim is made yet.


## Academic PDF report

The [report](report/India_Prison_Analytics_Report.pdf) includes the title page, abstract, contents, lists of figures/tables, dataset audit, preprocessing, descriptive analysis, visualization interpretations, FP-Growth, PAM, MAFIA, both Spark comparisons, limitations, conclusion, references and appendices. It is prepared for **Abdur Rahim (CS23I1019), IIITDM Kancheepuram**, for **Analytics and Systems of Big Data — End Sem Hackathon**.

The compiled PDF is retained in the repository. LaTeX source and intermediate files remain in the ignored local `report/.latex/` directory. The [build manifest](report/report_build_manifest.json) records PDF/source-artifact hashes and report-specific checks. No analysis cells or benchmark runs were repeated to typeset the report.

**Remaining phase:** Phase 12 — final reproducibility and requirement-compliance audit.

## References

- [Original dataset](https://www.kaggle.com/datasets/rajanand/prison-in-india/data).
- [mlxtend FP-Growth](https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/fpgrowth/) and [association rules](https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/).
- [PAM methodology](https://stat.ethz.ch/R-manual/R-devel/library/cluster/html/pam.html).
- [Original MAFIA paper](https://www.cs.cornell.edu/johannes/papers/2001/icde2001-mafia.pdf).
- [Spark frequent-pattern mining](https://spark.apache.org/docs/latest/ml-frequent-pattern-mining.html) and [RDD programming](https://spark.apache.org/docs/latest/rdd-programming-guide.html).

## Author

**Abdur Rahim** · **CS23I1019**
**IIITDM Kancheepuram**
Analytics and Systems of Big Data — End Sem Hackathon
[GitHub](https://github.com/rahim709)
