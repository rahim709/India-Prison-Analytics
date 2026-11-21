# Data cleaning report

Phase 1 validates and cleans all 37 downloaded Kaggle tables. We preserve their native observation units and original raw bytes. The cleaned data contains 159,019 records, with unresolved source limitations explicitly flagged. No source-table integration, feature selection, encoding, scaling, transaction construction, descriptive analytics or modeling has been performed.

## Execution and provenance

- Pipeline: `python -m src.preprocessing.cleaning`.
- Executed notebook: [01_Preprocessing.ipynb](../notebooks/01_Preprocessing.ipynb).
- Tests: `python -m unittest discover -s tests -v`.
- All 37 raw SHA-256 hashes must match the Phase 0 inventory before execution and are checked again afterward. Changes cause execution to fail rather than silently use a different dataset.
- Cleaned copies preserve the relative raw filenames under `data/processed/cleaned/`. Conflicting records are saved under `data/processed/quarantine/`.
- `source_record` is the original one-based CSV record number, counting the header as record 1. It is a provenance identifier, not a feature or necessarily a physical line number when CSV quoting spans lines.
- Saved nullable dtypes, column roles and candidate native keys are in [cleaned_schema.json](../results/tables/cleaning/cleaned_schema.json). CSV itself does not store types; use those dtypes or the typed loader when reloading.
- The notebook runner uses the current interpreter and a temporary kernel specification. Jupyter required approved execution outside the sandbox because local sockets are blocked inside it. No global kernel was registered.

## Cleaning decisions

### Schema and missing values

A direct CSV reader validates record widths before constructing any DataFrame. Religion.csv has eight declared fields but nine values per record. Every record was checked for the expected gender/religion vocabulary and numeric count positions, then a `religion` header was inserted between `gender` and `convicts` in the cleaned copy. The raw file was not edited. Unexpected structural changes raise an error.

Missing tokens are empty/whitespace-only fields, NA, N/A, NaN, null and none, matched case-insensitively. Zero is a recorded value, not a missing-value code. Nil in activity/program labels is preserved as a category. One empty CSV record in the women-with-children source is omitted from the cleaned output; it is excluded from both nonblank row baselines.

Before/after cell profiles use the correctly aligned schema even for Religion.csv. All source fields are initially strings to preserve exact parsing and phone-number formatting. There are 2,232 missing cells before cleaning: fourteen numeric cells and 2,218 directory contact/location cells. Two numeric cells are recovered by agreement of two independent same-record equations, leaving twelve numeric cells and the same 2,218 directory missing cells. No mean, median, interpolation or blanket zero imputation is used.

The recovered cells are:

| Source file | Source record | Column | Recovered value | Agreeing totals |
|---|---:|---|---:|---|
| `IPC_crime_inmates_convicted.csv` | 9023 | Male 16-18 years | 0 | Total 16-18 years; Total Male |
| `Other Prison data/SLL_Crime_headwise_distribution_of_inmates_who_convicted.csv` | 8843 | Female 18-30 years | 0 | Total 18-30 years; Total Female |

One age count in Age_group.csv, three training counts and eight goods-value observations remain unknown. The directory missingness consists of 222 phone fields, 730 email fields, 56 Location1 fields and 1,210 Location2 fields. These are not filled from unrelated records.

### Categories and data types

We trim surrounding whitespace, collapse internal whitespace in categorical fields, and apply explicit alias maps from [schema.py](../src/preprocessing/schema.py). Free-text jail names, contacts and addresses are only trimmed; phone numbers stay text so leading zeroes and separators are retained. Geography aliases resolve casing, Chhatisgarh/Chhattisgarh, Tamilnadu/Tamil Nadu, Orissa/Odisha, Uttaranchal/Uttarakhand, Pondicherry/Puducherry, and equivalent abbreviated state/UT names. The canonical names are labels for historical records; Andhra Pradesh and Telangana remain distinct, and no boundary reallocation is attempted.

Crime-head casing, jail-type separators, known sentence-band labels, equivalent parole/release labels and clear trade spelling variants are harmonized. Semantically distinct programs are not combined merely because they appear related. All category/missing-token changes are counted in [category_changes.csv](../results/tables/cleaning/category_changes.csv); its 120,382 changed cells are normalization operations, not 120,382 erroneous records. Numeric repairs are recorded separately.

Counts, year labels and numeric identifiers use nullable Int64; wages and financial measures use nullable Float64. Integer-count checks do not reject legitimate fractional monetary values. Numeric conversion checks reject nonnumeric/nonfinite, negative or fractional counts; years are checked against the known source ranges and is_state against {0,1}. Historical state/UT flags are also compared with the jurisdiction list. This run found no additional invalid numeric/domain values requiring masking and no jurisdiction-flag conflicts. The missing numeric tokens are classified as missing, not parsing failures.

### Duplicates and conflicting keys

Native keys include the dimensions needed to identify the source observation: state/year plus gender, category, legal status, crime head, jail type or indicator as appropriate. The directory key is state, jail type and jail serial number; contact fields are not used to establish uniqueness. Native-grain validation here supports duplicate handling only. Cross-file join selection and validation remain Phase 2 tasks.

Three exact duplicate crime records are removed after normalization. We then quarantine all ten remaining rows belonging to five conflicting crime keys, including both the zero and nonzero versions. A zero record is not assumed to be erroneous solely because another version is nonzero. Original source-record IDs are retained so the decisions can be reversed.

| Conflict | Rows quarantined |
|---|---:|
| Convicted IPC: Assam, 2005, murder | 2 |
| Convicted IPC: Delhi, 2003, murder | 2 |
| Undertrial IPC: Goa, 2004, murder | 2 |
| Undertrial IPC: Karnataka, 2005, other IPC crimes | 2 |
| Convicted SLL: Karnataka, 2003, reported total | 2 |

The duplicate-removal ledger contains the source record and its representative record. Where the representative belongs to a conflicting key, it is subsequently quarantined rather than included in cleaned data. The ledger and quarantine together preserve this lineage.

The vocational-training and goods-production files lack a finer event/jail identifier. We retain all their records, including five exact training duplicates, because equality at this under-specified grain does not prove that records describe the same event. After normalization, 104 training rows and 39 goods rows have repeated candidate keys. They remain flagged as ambiguous and cannot be treated as verified unique state-year-program observations or independent prisoner counts.

## Before and after quality results

| Source file | Before rows | Cleaned rows | Duplicates removed | Quarantined | Missing before | Missing after |
|---|---:|---:|---:|---:|---:|---:|
| `Age_group.csv` | 7,152 | 7,152 | 0 | 0 | 1 | 1 |
| `Caste.csv` | 3,568 | 3,568 | 0 | 0 | 0 | 0 |
| `Death_sentence.csv` | 446 | 446 | 0 | 0 | 0 | 0 |
| `Domicile.csv` | 2,676 | 2,676 | 0 | 0 | 0 | 0 |
| `Education.csv` | 5,346 | 5,346 | 0 | 0 | 0 | 0 |
| `Education_facilities.csv` | 445 | 445 | 0 | 0 | 0 | 0 |
| `IPC_crime_inmates_convicted.csv` | 9,391 | 9,385 | 2 | 4 | 1 | 0 |
| `IPC_crime_inmates_under_trial.csv` | 9,390 | 9,385 | 1 | 4 | 0 | 0 |
| `Inmates_death.csv` | 4,023 | 4,023 | 0 | 0 | 0 | 0 |
| `Inmates_escapee.csv` | 1,788 | 1,788 | 0 | 0 | 0 | 0 |
| `Jail wise population of prison inmates.csv` | 4,023 | 4,023 | 0 | 0 | 0 | 0 |
| `Other Prison data/Budget.CSV` | 1,026 | 1,026 | 0 | 0 | 0 | 0 |
| `Other Prison data/Details_of_electronic_equipments_used_in_prison.CSV` | 3,390 | 3,390 | 0 | 0 | 0 | 0 |
| `Other Prison data/Details_of_inmates_parole_during_the_year.csv` | 1,341 | 1,341 | 0 | 0 | 0 | 0 |
| `Other Prison data/Expenditure.CSV` | 1,368 | 1,368 | 0 | 0 | 0 | 0 |
| `Other Prison data/Expenditure_on_inmates.CSV` | 2,394 | 2,394 | 0 | 0 | 0 | 0 |
| `Other Prison data/Inmates_released.csv` | 8,485 | 8,485 | 0 | 0 | 0 | 0 |
| `Other Prison data/Inmates_suffering_from_mental_ilness.csv` | 442 | 442 | 0 | 0 | 0 | 0 |
| `Other Prison data/Movements_outside_jail_premises.CSV` | 1,025 | 1,025 | 0 | 0 | 0 | 0 |
| `Other Prison data/Number_of_vehicles_available.CSV` | 3,051 | 3,051 | 0 | 0 | 0 | 0 |
| `Other Prison data/Number_of_women_prisoners_with_children.csv` | 446 | 446 | 0 | 0 | 0 | 0 |
| `Other Prison data/Period_of_detention_of_undertrials.csv` | 3,576 | 3,576 | 0 | 0 | 0 | 0 |
| `Other Prison data/Population_and_capacity_of_jails.csv` | 4,023 | 4,023 | 0 | 0 | 0 | 0 |
| `Other Prison data/SLL_Crime_headwise_distribution_of_inmates_who_convicted.csv` | 9,458 | 9,456 | 0 | 2 | 1 | 0 |
| `Other Prison data/SLL_crime_head_wise_distribution_of_inmates_under_trial.csv` | 9,457 | 9,457 | 0 | 0 | 0 | 0 |
| `Other Prison data/Strength_of_officials.CSV` | 36,612 | 36,612 | 0 | 0 | 0 | 0 |
| `Other Prison data/Total_Budget_and_Actual_Expenditure_during_ the_year_2015_2016.csv` | 36 | 36 | 0 | 0 | 0 | 0 |
| `Other Prison data/Training_of_Jail_Officers.CSV` | 1,108 | 1,108 | 0 | 0 | 0 | 0 |
| `Other Prison data/Value_of_goods_produced_by_inmates.csv` | 1,954 | 1,954 | 0 | 0 | 8 | 8 |
| `Prison_details_2015.csv` | 1,397 | 1,397 | 0 | 0 | 2218 | 2218 |
| `Recidivism.csv` | 447 | 447 | 0 | 0 | 0 | 0 |
| `Rehabilitation.csv` | 445 | 445 | 0 | 0 | 0 | 0 |
| `Religion.csv` | 4,460 | 4,460 | 0 | 0 | 0 | 0 |
| `Sentence_period.csv` | 8,940 | 8,940 | 0 | 0 | 0 | 0 |
| `Tranquillity.csv` | 1,336 | 1,336 | 0 | 0 | 0 | 0 |
| `Vocational_training.csv` | 4,122 | 4,122 | 0 | 0 | 3 | 3 |
| `Wages.csv` | 445 | 445 | 0 | 0 | 0 | 0 |

Across all files, **159,032 = 159,019 cleaned + 3 duplicate removals + 10 quarantined records**. Quarantine is exclusion from the cleaned tables, not deletion of raw data. The single blank CSV record is accounted for separately.

Detailed [column profiles](../results/tables/cleaning/quality_columns.csv) report missingness, dtypes, parsing failures, negative values and integrality before and after. The [file summary](../results/tables/cleaning/quality_summary.csv) includes schema repair, duplicate decisions, conflicts, total checks and outlier counts.

## Totals and prevention of double counting

There are 327,282 evaluable within-record equations, including male + female totals, status totals, age totals, capacity/population totals, women/children totals and the fiscal snapshot formulas. Count equations use absolute tolerance 1e-8 and zero relative tolerance. The fiscal snapshot is printed to one decimal place, so absolute tolerance 0.15 accommodates rounding in sums of printed components. These are arithmetic checks, not verification against the original NCRB publication.

Selected known category partitions contribute another 30,922 evaluable checks: jail types, undertrial detention bands, unnatural-death causes, release categories, administrative budget/expenditure/training components and SLL offense subtotals. No such partition check failed. There are 105 incomplete release-partition groups without the required reported-total record; they were not assumed to match or filled. No cross-file totals have been reconciled at this phase.

Four within-record checks fail across three records and are retained as unresolved contradictions:

| Source file | Record | Field | Reported | Calculated from components | Difference |
|---|---:|---|---:|---:|---:|
| `Other Prison data/Inmates_suffering_from_mental_ilness.csv` | 119 | Total Under trial | 49 | 46 | 3 |
| `Other Prison data/Inmates_suffering_from_mental_ilness.csv` | 316 | Grand Total | 160 | 260 | -100 |
| `Other Prison data/Inmates_suffering_from_mental_ilness.csv` | 119 | Total Female | 6 | 0 | 6 |
| `Other Prison data/Number_of_women_prisoners_with_children.csv` | 442 | Total No. of children of  Women Prisoners | 0 | 2 | -2 |

A failed equation does not identify which field is wrong. We therefore preserve both the total and component values and record the contradictions in [total_checks_failed.csv](../results/tables/cleaning/total_checks_failed.csv). Before/after rows in this file refer to the same preserved discrepancies and must not be added together as distinct errors.

The companion row-quality table assigns each cleaned record one scope:

| Scope | Rows |
|---|---:|
| detail | 148,155 |
| reported_total | 6,238 |
| reported_subtotal | 3,159 |
| directory | 1,397 |
| separate_population | 70 |

The typed loader `load_cleaned(root, filename, scope)` requires one explicit scope and attaches matching quality metadata with a one-to-one provenance join. It refuses an all-rows scope to reduce accidental mixing of detail and total records. This metadata join does not integrate source datasets or select modeling features.

Scope labels are a safeguard, not a guarantee of additivity. Legal-status, age and gender totals coexist as columns. Budget/staff indicators can overlap or use different units. Directory number-of-jails values repeat within groups and are not additive per jail row. Different demographic tables describe overlapping marginal populations and must never be concatenated or joined to invent individual-level joint distributions. Select consistent rows, measures, denominators and hierarchy levels in Phase 2 before computing totals.

## Outlier review

We apply Tukey fences Q1 − 1.5 IQR and Q3 + 1.5 IQR, with pandas linear quantiles. Measures are compared within the same available non-geographic categories across state-years; year and state are not pooled as numeric features. For example, offense, gender or staff-role categories define separate reference groups where available. Groups need at least eight nonmissing observations. Numeric identifiers, is_state, years and directory group counts are not outlier-tested.

There are 1,361 positive-IQR measure groups and 945 zero-IQR groups. Zero-IQR groups are explicitly recorded and not flagged using a zero-width fence, which would classify many legitimate nonzero values in sparse indicators as outliers. Full bounds are in [outlier_bounds.csv](../results/tables/cleaning/outlier_bounds.csv); cell-level flags are in [outliers.csv](../results/tables/cleaning/outliers.csv).

The procedure flags **56,018 cells**, all retained. This is not a count of distinct records, errors or prisoners. State-size differences, zero-heavy counts, repeated years and shifts over time can produce valid extreme values. No trimming, winsorization, smoothing or automatic exclusion is applied. These fences are exploratory review indicators, not calibrated anomaly probabilities.

## Verification and remaining limitations

The cleaning rules and artifacts passed fourteen automated checks. They cover schema repair/failure behavior, conservative imputation, conflicting equations, preserved mismatched totals, geography aliases, contact types, zero handling, stable program categories, aggregation scopes, all raw hashes, row accounting, native-key uniqueness, retained ambiguity, raw-to-cleaned numeric reconciliation and row-flag alignment. All seven code cells of the notebook executed without error. A separate pipeline run produced byte-identical cleaned files and quality evidence. Compilation and installed dependency checks passed.

Residual limitations remain explicit: twelve unknown numeric cells, 2,218 unknown directory fields, four arithmetic discrepancies, ten quarantined records, 143 retained rows with ambiguous training/goods keys, and unverified cross-file consistency. Category harmonization does not establish common geographic boundaries or confirm indicator units. Large values have been reviewed statistically but cannot be certified correct without source verification. These limitations must guide later selection rather than be hidden by imputation.

## Independent recheck

A second review reconciled every source record with the cleaned tables, quarantine or duplicate ledger. It compared 1,114,813 nonmissing numeric cells in the cleaned and quarantined representations with the original CSV values using exact decimal comparison. All matched. The only numeric fills were the two explicitly logged recoveries. Each of the three removed records was also confirmed identical to its representative in the raw data. All 56,018 outlier flags referred to preserved values, and notebook outputs matched the saved pipeline summary.

The review found and corrected one category-normalization defect: canonical multiword trade names could split into case variants or change case when normalized again. Canonical alias values now map to themselves. A regression test covers the defect, and both actual program/activity columns were checked for stable normalized labels. Cleaned outputs, quality evidence and the executed notebook were regenerated after the correction. The record counts, numeric repairs, missingness, quarantine decisions and outlier count are unchanged.

The corrected Phase 1 is ready for Phase 2, subject to the documented source limitations. See [verification.json](../results/tables/cleaning/verification.json) for the recorded checks. Phase 2 Data Selection requires separate approval.
