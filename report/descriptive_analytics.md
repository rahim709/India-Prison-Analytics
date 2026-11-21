# Descriptive analytics report

Phase 4 describes the 27 sources selected for historical prisoner-population analysis. It covers counts and record frequencies; mean, median and mode; range, sample variance and standard deviation; quartiles and IQR; skewness and kurtosis; state/year trends; legal status; demographic distributions; supporting indicators; and correlations. We generate **22 statistical tables**, including 131 global measure summaries and 2,659 source/category-stratified summaries. All results come from the saved dataset. No plots, mining algorithms, models or benchmarks have been run.

## Analysis populations and coverage

The verified population reference has 447 state-years over 2001–2013, covering 34 historical state/UT labels through 2008 and 35 afterward. Arunachal Pradesh is absent in 2001–2008. The balanced time-trend panel keeps the same 34 jurisdictions for all thirteen years, giving 442 observations. The separate profile analysis retains the 437 state-years selected in Phases 2–3. These are different analysis populations and are labeled in the outputs.

Each descriptive source uses its Phase 2 quality and completeness rules. Source-year coverage is recorded in [source_year_coverage.csv](../results/tables/descriptive/source_year_coverage.csv). Demographic marginal tables additionally require matching population denominators. The common intersection of all five demographic source key sets contains 426 state-years, saved for comparisons requiring common coverage; it is not a reconstruction of individual joint demographics or a balanced panel. Ten previously deferred administrative or temporally incompatible sources remain outside this selected analytical scope.

The raw, cleaned, selected and transformed files remain unchanged. We verify 85 upstream file hashes. The input snapshot and result hashes are recorded in [input_provenance.json](../results/tables/descriptive/input_provenance.json) and [table_manifest.json](../results/tables/descriptive/table_manifest.json).

## Statistical definitions

All numeric summaries state their source, measure and observation scope. Source summaries describe reported values at the selected native grain, such as state-year-jail-type or state-year-gender-education category. They are not automatically statistics of individual prisoners. Counts of native rows, nonmissing observations, zeros and distinct values are reported separately. State/year/source-record IDs and quality flags are excluded from numeric measurement summaries. The [measure dictionary](../results/tables/descriptive/measure_dictionary.csv) records native keys, units and overlap cautions.

Sample variance uses the squared-deviation sum divided by n−1; sample standard deviation is its square root. These are descriptive conventions and do not assert independent random sampling. Mean and median use nonmissing values. Q1 and Q3 use linear interpolation; Q2 is the median and IQR is Q3−Q1. Quartile conventions can differ from median-of-halves hand calculations, so this choice is fixed explicitly.

Modes use exact stored-value frequencies, without rounding values to manufacture a mode. All tied modes are recorded with their frequency and count. When every value is unique, the series is marked all_values_unique and no informative modal list is printed. Empty/singleton samples retain undefined sample variances as missing. Skewness is the bias-corrected Fisher–Pearson sample coefficient for n≥3; kurtosis is unbiased Fisher excess kurtosis for n≥4, with normal-reference value zero. Both are undefined for constant series, rather than forced to zero. Phase 3 scaler variances use ddof=0; the ddof=1 statistics here can therefore differ without any input change.

Native record frequencies describe dataset layout. For example, equal numbers of education-category rows do not imply equal prisoner populations in those categories. Weighted demographic counts use prisoner numerators and their own compatible population denominators. We never sum stock counts across years and call them distinct people, add total rows to component rows, or combine overlapping source tables into a larger prisoner count. Wages remain rates/values in unverified source units and are not summed into national wage totals.

## Year-wise findings

The following all-available counts are reproduced from verified state-year totals:

| Year | Jurisdictions | Reported prisoners | Capacity | Pooled occupancy % | Undertrial share % | Female share % |
|---|---:|---:|---:|---:|---:|---:|
| 2001 | 34 | 313,635 | 229,713 | 136.53 | 70.41 | 3.54 |
| 2002 | 34 | 322,357 | 229,874 | 140.23 | 69.19 | 3.74 |
| 2003 | 34 | 326,519 | 233,543 | 139.81 | 66.66 | 3.91 |
| 2004 | 34 | 331,391 | 235,012 | 141.01 | 65.52 | 3.91 |
| 2005 | 34 | 358,368 | 246,497 | 145.38 | 66.15 | 3.90 |
| 2006 | 34 | 373,271 | 263,911 | 141.44 | 65.70 | 3.93 |
| 2007 | 34 | 376,396 | 277,304 | 135.73 | 66.61 | 4.09 |
| 2008 | 34 | 384,753 | 297,777 | 129.21 | 67.04 | 4.14 |
| 2009 | 35 | 376,969 | 307,052 | 122.77 | 66.37 | 4.09 |
| 2010 | 35 | 368,998 | 320,450 | 115.15 | 65.07 | 4.08 |
| 2011 | 35 | 372,926 | 332,782 | 112.06 | 64.68 | 4.30 |
| 2012 | 35 | 385,135 | 343,169 | 112.23 | 66.17 | 4.40 |
| 2013 | 35 | 411,992 | 347,859 | 118.44 | 67.60 | 4.41 |

The available series rises from 313,635 reported prisoners in 2001 to 411,992 in 2013, but its jurisdiction count changes. On the fixed 34-jurisdiction panel, prisoner counts rise from 313,635 to 411,900 (**31.33%**) while reported capacity rises from 229,713 to 347,803 (**51.41%**). Pooled occupancy falls from **136.53% to 118.43%** in that fixed panel. The capacity/count relationship explains this ratio change arithmetically, without identifying a causal policy effect. The observed series is not monotonic: the saved annual table includes both increases and decreases.

Pooled occupancy is the ratio of summed prisoners to summed capacity. In 2013 the all-available pooled ratio is 118.44%, while the unweighted mean of jurisdiction ratios is 104.33%. They answer different questions and must not be substituted for each other. The all-available data contain nineteen jurisdictions above their reported capacity in 2013. These describe this dataset’s reported populations/capacities, not independently certified contemporary prison conditions.

See [year_summary_available.csv](../results/tables/descriptive/year_summary_available.csv), [year_summary_balanced.csv](../results/tables/descriptive/year_summary_balanced.csv) and [state_year_totals.csv](../results/tables/descriptive/state_year_totals.csv). Year changes in the available series carry its changing coverage; the balanced series supports the fixed-panel comparison.

## State-wise findings

In the latest source year, 2013, Uttar Pradesh has the largest reported prisoner count: **83,518**, or **20.27%** of the available total. Its reported occupancy is **172.02%**. These are prison-system counts and capacity ratios, not incarceration rates per resident or rankings of crime incidence.

| State/UT | Reported prisoners in 2013 | Capacity | Occupancy % |
|---|---:|---:|---:|
| Uttar Pradesh | 83,518 | 48,550 | 172.02 |
| Madhya Pradesh | 34,708 | 26,967 | 128.71 |
| Bihar | 31,259 | 35,681 | 87.61 |
| Punjab | 27,449 | 18,629 | 147.35 |
| Maharashtra | 27,400 | 24,544 | 111.64 |
| West Bengal | 22,778 | 20,585 | 110.65 |
| Rajasthan | 19,293 | 16,622 | 116.07 |
| Jharkhand | 18,220 | 14,243 | 127.92 |

Chhattisgarh has the highest reported 2013 occupancy ratio, **260.96%** (15,840 prisoners / 6,070 capacity), followed by Delhi at **216.83%** (13,552 / 6,250). Absolute inmate counts and capacity pressure therefore produce different rankings. Small denominators can also create large ratios in smaller jurisdictions.

The [latest snapshot](../results/tables/descriptive/latest_state_snapshot.csv) saves both count and occupancy ranks. [state_numeric_summary.csv](../results/tables/descriptive/state_numeric_summary.csv) describes each jurisdiction’s available years, including its first/last year, without summing annual stocks as distinct individuals.

## Prisoner-category and gender findings

In 2013 the reference reports 278,503 undertrials (**67.60%**), 129,608 convicts (**31.46%**), 3,113 detenues (**0.76%**) and 768 others (**0.19%**). These legal-status counts partition the available total. Undertrials form the largest recorded category; these descriptive counts do not explain individual case duration or predict an outcome.

There are 18,188 recorded female prisoners (**4.41%**) and 393,804 male prisoners (**95.59%**) in 2013. The available female share was 3.54% in 2001. We describe the source’s reported gender categories and do not infer individual risk or population disparity from these proportions.

## Demographic findings with source-specific denominators

Age data in 2013 exclude West Bengal because its youngest-age field is missing. The retained age distribution covers **34 jurisdictions and 389,214 prisoners**, or **94.47% of the available population reference**. Within that covered population, age 30–50 accounts for 174,717 (**44.89%**) and age 18–30 for 163,478 (**42.00%**). These are counts within reported age bands; exact individual ages, mean age or median age cannot be recovered without additional assumptions.

Education data for 2013 cover all 35 available jurisdictions. The source records 174,645 prisoners in Below Class X (**42.39%**) and 118,409 in Illiterate (**28.74%**). These are separate categories in the validated source partition. We do not treat education-level record frequencies as prisoner percentages.

The following 2013 marginal distributions retain each source’s own denominator. Counts across dimensions are not additive:

| Dimension | Source category | Prisoners | Covered prisoners | Covered jurisdictions | Share % |
|---|---|---:|---:|---:|---:|
| age_group | age_16_18 | 33 | 389,214 | 34 | 0.01 |
| age_group | age_18_30 | 163,478 | 389,214 | 34 | 42.00 |
| age_group | age_30_50 | 174,717 | 389,214 | 34 | 44.89 |
| age_group | age_50_above | 50,986 | 389,214 | 34 | 13.10 |
| nationality | Foreigners | 3,871 | 389,214 | 34 | 0.99 |
| nationality | Indians | 385,343 | 389,214 | 34 | 99.01 |
| caste | OBC | 130,242 | 411,992 | 35 | 31.61 |
| caste | Others | 144,955 | 411,992 | 35 | 35.18 |
| caste | SC | 89,489 | 411,992 | 35 | 21.72 |
| caste | ST | 47,306 | 411,992 | 35 | 11.48 |
| domicile | Belongs to State | 374,830 | 411,992 | 35 | 90.98 |
| domicile | Belongs to other Country | 7,201 | 411,992 | 35 | 1.75 |
| domicile | Belongs to other State | 29,961 | 411,992 | 35 | 7.27 |
| education | Below Class X | 174,645 | 411,992 | 35 | 42.39 |
| education | Class X and above but below graduate | 85,130 | 411,992 | 35 | 20.66 |
| education | Graduate | 22,385 | 411,992 | 35 | 5.43 |
| education | Holding technical degree/diploma etc | 4,250 | 411,992 | 35 | 1.03 |
| education | Illiterate | 118,409 | 411,992 | 35 | 28.74 |
| education | Post-Graduate | 7,173 | 411,992 | 35 | 1.74 |
| religion | Christian | 17,705 | 411,992 | 35 | 4.30 |
| religion | Hindu | 287,987 | 411,992 | 35 | 69.90 |
| religion | Muslim | 81,086 | 411,992 | 35 | 19.68 |
| religion | Others | 6,633 | 411,992 | 35 | 1.61 |
| religion | Sikh | 18,581 | 411,992 | 35 | 4.51 |

A population_coverage_fraction of 1 means agreement with the full available reference for that year, not independent certification that all Indian prisons were captured. Nationality and domicile also describe different source concepts and need not have matching foreign-country counts. No general-population baselines are supplied, so these distributions do not establish overrepresentation, discrimination, causal effects or individual risks.

The [state-year marginal table](../results/tables/descriptive/demographic_state_year.csv) and [annual marginal table](../results/tables/descriptive/demographic_year.csv) preserve those denominators. [Gender-conditional](../results/tables/descriptive/demographic_gender_year.csv) and [legal-status-conditional](../results/tables/descriptive/demographic_status_year.csv) distributions use only dimensions jointly observed within the same source. For example, the 2013 education source records 80,393 illiterate undertrials out of 278,503 undertrials (**28.87%**), versus 36,507 out of 129,608 convicts (**28.17%**). This is an aggregate description of recorded groups, not evidence that education caused their legal status.

## Distribution shape of the selected profiles

The 437-profile cohort is unweighted by prisoner count. Its distributions summarize state-year profiles, not the distribution of characteristics across individual prisoners:

| Feature | Mean | Median | Sample SD | Q1 | Q3 | IQR | Skewness | Excess kurtosis |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| occupancy_ratio | 1.189940 | 1.103260 | 0.606513 | 0.808238 | 1.423792 | 0.615553 | 1.566316 | 4.981243 |
| undertrial_share | 0.664764 | 0.656228 | 0.144641 | 0.587604 | 0.751006 | 0.163402 | -0.285606 | 1.720328 |
| female_share | 0.038224 | 0.036292 | 0.019734 | 0.026396 | 0.048511 | 0.022115 | 0.623203 | 1.138909 |
| age_18_30_share | 0.466552 | 0.454276 | 0.115303 | 0.400798 | 0.515337 | 0.114540 | 0.438525 | 3.671952 |
| illiterate_share | 0.276484 | 0.291490 | 0.129340 | 0.191167 | 0.365441 | 0.174274 | -0.113165 | -0.135553 |

Occupancy has mean 1.18994, median 1.10326, skewness 1.56632 and excess kurtosis 4.98124 in this cohort. This indicates a right-tailed profile distribution with extreme values; it does not by itself identify errors or justify deleting them. The maximum recorded profile occupancy is 5.0 across the historical cohort, not necessarily in 2013. All earlier outlier-preservation decisions remain in force. Full mode lists, minima/maxima, counts and sample variances are available in [numeric_summary.csv](../results/tables/descriptive/numeric_summary.csv); source/category and annual distributions are in their corresponding summary tables.

## Correlation findings

Among the five selected profile features, the largest absolute off-diagonal pooled Pearson correlation is between illiterate_share and occupancy_ratio: **r=0.35432**, with **437 paired state-years**. Spearman correlation for the same pair is **0.41465**. Within-state-centered correlations are 0.30642 (Pearson) and 0.25503 (Spearman); the 2013 cross-section has 33 selected jurisdictions and Pearson correlation 0.30055. These different summaries indicate dependence on the observation scope. They do not establish causal effects, remove all confounding or create 437 independent geographic observations.

Count correlations can also reflect state size, while ratio correlations can reflect shared denominators. [correlations.csv](../results/tables/descriptive/correlations.csv) records Pearson/Spearman coefficients, scope, optional year and pairwise nonmissing sample size. We provide no p-values, confidence intervals or significance claims from the pooled repeated-state data.

## Crime and supporting indicators

Crime distributions remain separate for IPC/SLL and convicted/undertrial sources. Their percentages use complete eligible counts within the same statute/status source and year. In 2013, murder accounts for **68,199 of 113,678 reported convicted IPC counts (59.99%)** and **60,110 of 226,542 reported undertrial IPC counts (26.53%)**. These are not percentages of all prisoners or estimates of crime incidence in the resident population. IPC/SLL source totals are not combined with civil or other case rows to create unsupported unique-person totals.

[indicator_year.csv](../results/tables/descriptive/indicator_year.csv) records separate measures and categories for deaths, escape/rearrest, detention, releases, education facilities, rehabilitation, vocational training, goods, wages and other selected outcomes. Summing differently defined flows/indicators can double count people. Training participants can attend multiple programs; releases or rearrests are not disjoint unique-person populations. Monetary goods values remain nominal source rupees, without inflation adjustment. Wages retain their unverified original currency/time units and are summarized without adding rates. Death counts are not divided by a point-in-time inmate stock and labeled a mortality risk.

A further cross-field issue occurs in Recidivism.csv: Andaman & Nicobar Islands, 2002, reports zero admitted convicts and nineteen habitual offenders. We retain both raw reported counts, flag the invalid subset/denominator pair, and leave its habitual/admissions share undefined. Annual share calculations use only valid count pairs, while separate reported-count columns preserve the discrepancy. Twenty-six state-year admission denominators are zero; none is replaced with an epsilon or an invented zero fraction. Habitual/admissions shares do not measure a longitudinal probability of reoffending.

## Generated table inventory

| Table | Purpose |
|---|---|
| [numeric_summary.csv](../results/tables/descriptive/numeric_summary.csv) | 131 global source/reference/profile measure summaries with complete requested statistics. |
| [stratified_numeric_summary.csv](../results/tables/descriptive/stratified_numeric_summary.csv) | 2,659 native-category measure summaries; no pooling of unlike category definitions. |
| [annual_numeric_summary.csv](../results/tables/descriptive/annual_numeric_summary.csv) | Native-measure distributions by source/year with contributing jurisdiction counts. |
| [categorical_record_frequencies.csv](../results/tables/descriptive/categorical_record_frequencies.csv) | Native row counts and row fractions for keys/categories; not prisoner proportions. |
| [source_year_coverage.csv](../results/tables/descriptive/source_year_coverage.csv) | Coverage of each selected source/year against the available population reference. |
| [measure_dictionary.csv](../results/tables/descriptive/measure_dictionary.csv) | Native units, keys and population-overlap cautions. |
| [state_year_totals.csv](../results/tables/descriptive/state_year_totals.csv) | 447 verified population/capacity observations and defined ratios. |
| [state_numeric_summary.csv](../results/tables/descriptive/state_numeric_summary.csv) | Per-jurisdiction distributions over available years. |
| [year_summary_available.csv](../results/tables/descriptive/year_summary_available.csv) | All-available annual totals, pooled ratios and changes. |
| [year_summary_balanced.csv](../results/tables/descriptive/year_summary_balanced.csv) | Fixed 34-jurisdiction annual totals and ratios. |
| [latest_state_snapshot.csv](../results/tables/descriptive/latest_state_snapshot.csv) | 2013 reference counts, shares and count/occupancy ranks. |
| [demographic_state_year.csv](../results/tables/descriptive/demographic_state_year.csv) | Separate marginal prisoner distributions at state-year level. |
| [demographic_gender_state_year.csv](../results/tables/descriptive/demographic_gender_state_year.csv) | Gender-conditional marginal distributions and denominators. |
| [demographic_year.csv](../results/tables/descriptive/demographic_year.csv) | Annual marginal counts, weighted shares and coverage. |
| [common_demographic_cohort_keys.csv](../results/tables/descriptive/common_demographic_cohort_keys.csv) | 426 source-key intersections for explicit common-coverage comparisons. |
| [demographic_status_year.csv](../results/tables/descriptive/demographic_status_year.csv) | Annual within-source legal-status-conditional distributions. |
| [demographic_gender_year.csv](../results/tables/descriptive/demographic_gender_year.csv) | Annual within-source gender-conditional distributions. |
| [correlations.csv](../results/tables/descriptive/correlations.csv) | Pooled, within-year and within-state-centered correlation results with paired n. |
| [recidivism_state_year.csv](../results/tables/descriptive/recidivism_state_year.csv) | Reported admission/habitual counts, pair-validity flags and defined shares. |
| [recidivism_year.csv](../results/tables/descriptive/recidivism_year.csv) | Reported annual counts and separately validated ratio cohorts. |
| [crime_year.csv](../results/tables/descriptive/crime_year.csv) | Separate statute/status/year/head counts and within-source fractions. |
| [indicator_year.csv](../results/tables/descriptive/indicator_year.csv) | Source/category/measure-specific annual reported-value summaries. |

## Reproducibility and verification

Run `python -m src.analytics.descriptive` or execute [02_Descriptive_Analytics.ipynb](../notebooks/02_Descriptive_Analytics.ipynb) with the supplied runner. Phase 4 adds no dependencies. Twelve new descriptive checks supplement the thirty-three earlier regression tests. They validate independent statistical formulas, mode/constant/small-sample behavior, undefined denominators, weighted aggregation, balanced-panel identity, demographic partitions, category-record frequencies, correlation coefficients, crime denominators, source/output hashes and invalid admission pairs. The descriptive notebook has eleven executable cells. Final execution and reproducibility checks are recorded in [verification.json](../results/tables/descriptive/verification.json).

## Limitations and references

These are historical aggregate source statistics, not independent person-level observations. Unequal coverage, recorded zeros, missing/contradictory values, historical geography, possible reporting-definition differences, related state-years and nonunique program/event participants constrain interpretation. No individual attributes or unobserved joint demographic combinations are inferred. Source selection and exclusions follow [data_selection.md](data_selection.md); profile construction follows [data_transformation.md](data_transformation.md).

The analysis covers task-relevant distributions, five-number summaries, outliers, associations and compatible group comparisons. Statistical conventions are explicit in [methods.json](../results/tables/descriptive/methods.json) and checked against independent Python statistics/SciPy calculations. The [official Kaggle dataset](https://www.kaggle.com/datasets/rajanand/prison-in-india/data) remains the acquisition source; the analysis does not independently verify every original source definition.

Phase 4 is complete. Phase 5 Data Visualization requires separate approval.
