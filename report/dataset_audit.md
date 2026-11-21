# Dataset audit

Phase 0 inspects source structure and coverage only. No cleaning, feature transformation, descriptive statistics, plots, or models have been performed.

## Source and acquisition

- Dataset: Indian Prison Statistics, uploaded by Rajanand on Kaggle.
- Source: https://www.kaggle.com/datasets/rajanand/prison-in-india/data
- Downloaded on 2026-11-21 with the official Kaggle CLI 2.2.5.
- License reported by the downloader: CC BY-SA 4.0. Retain source attribution and observe share-alike terms when distributing adapted data.
- The public download succeeded without credentials. The separate metadata endpoint required authentication, so dataset version and publisher metadata were not retrieved. SHA-256 hashes identify the exact files used.
- Statistical tables appear to reproduce Indian prison reporting; verify original NCRB definitions and units before interpreting indicators. Kaggle is the verified acquisition source, not proof of every field definition.
- The CLI archive was about 1.11 MiB. Extracted CSVs total 9,215,877 bytes (8.79 MiB), so raw CSVs are retained in the submission rather than ignored.

## Inventory

All 37 CSV files, including uppercase extensions and nested directories, were inspected. There are 159,032 nonblank data records across heterogeneous tables. This is a record count, not a number of prisoners. One empty record is reported separately.

| Raw file | Bytes | Records | Header fields | Record widths | Time coverage |
|---|---:|---:|---:|---|---|
| `Age_group.csv` | 375,058 | 7,152 | 10 | 10 | 2001–2013 |
| `Caste.csv` | 140,223 | 3,568 | 9 | 9 | 2001–2013 |
| `Death_sentence.csv` | 10,165 | 446 | 5 | 5 | 2001–2013 |
| `Domicile.csv` | 150,512 | 2,676 | 9 | 9 | 2001–2013 |
| `Education.csv` | 292,129 | 5,346 | 9 | 9 | 2001–2013 |
| `Education_facilities.csv` | 12,938 | 445 | 6 | 6 | 2001–2013 |
| `IPC_crime_inmates_convicted.csv` | 616,103 | 9,391 | 18 | 18 | 2001–2013 |
| `IPC_crime_inmates_under_trial.csv` | 638,964 | 9,390 | 18 | 18 | 2001–2013 |
| `Inmates_death.csv` | 242,585 | 4,023 | 6 | 6 | 2001–2013 |
| `Inmates_escapee.csv` | 88,443 | 1,788 | 6 | 6 | 2001–2013 |
| `Jail wise population of prison inmates.csv` | 263,177 | 4,023 | 18 | 18 | 2001–2013 |
| `Other Prison data/Budget.CSV` | 43,597 | 1,026 | 4 | 4 | 2001–2010 |
| `Other Prison data/Details_of_electronic_equipments_used_in_prison.CSV` | 104,751 | 3,390 | 4 | 4 | 2001–2010 |
| `Other Prison data/Details_of_inmates_parole_during_the_year.csv` | 100,933 | 1,341 | 6 | 6 | 2001–2013 |
| `Other Prison data/Expenditure.CSV` | 80,545 | 1,368 | 4 | 4 | 2001–2010 |
| `Other Prison data/Expenditure_on_inmates.CSV` | 127,641 | 2,394 | 4 | 4 | 2001–2010 |
| `Other Prison data/Inmates_released.csv` | 598,680 | 8,485 | 6 | 6 | 2001–2013 |
| `Other Prison data/Inmates_suffering_from_mental_ilness.csv` | 22,871 | 442 | 17 | 17 | 2001–2013 |
| `Other Prison data/Movements_outside_jail_premises.CSV` | 70,967 | 1,025 | 4 | 4 | 2001–2010 |
| `Other Prison data/Number_of_vehicles_available.CSV` | 81,316 | 3,051 | 4 | 4 | 2001–2010 |
| `Other Prison data/Number_of_women_prisoners_with_children.csv` | 18,115 | 446 | 12 | 12 | 2001–2013 |
| `Other Prison data/Period_of_detention_of_undertrials.csv` | 133,372 | 3,576 | 6 | 6 | 2001–2013 |
| `Other Prison data/Population_and_capacity_of_jails.csv` | 191,693 | 4,023 | 10 | 10 | 2001–2013 |
| `Other Prison data/SLL_Crime_headwise_distribution_of_inmates_who_convicted.csv` | 692,445 | 9,458 | 18 | 18 | 2001–2013 |
| `Other Prison data/SLL_crime_head_wise_distribution_of_inmates_under_trial.csv` | 708,459 | 9,457 | 18 | 18 | 2001–2013 |
| `Other Prison data/Strength_of_officials.CSV` | 2,231,750 | 36,612 | 5 | 5 | 2001–2010 |
| `Other Prison data/Total_Budget_and_Actual_Expenditure_during_ the_year_2015_2016.csv` | 2,296 | 36 | 9 | 9 | 2015–2016, filename only |
| `Other Prison data/Training_of_Jail_Officers.CSV` | 51,547 | 1,108 | 4 | 4 | 2001–2010 |
| `Other Prison data/Value_of_goods_produced_by_inmates.csv` | 71,130 | 1,954 | 4 | 4 | 2001–2013 |
| `Prison_details_2015.csv` | 178,844 | 1,397 | 14 | 14 | 2015, filename only |
| `Recidivism.csv` | 10,775 | 447 | 4 | 4 | 2001–2013 |
| `Rehabilitation.csv` | 11,052 | 445 | 5 | 5 | 2001–2013 |
| `Religion.csv` | 184,122 | 4,460 | 8 | 9 | Header mismatch; see below |
| `Sentence_period.csv` | 459,029 | 8,940 | 9 | 9 | 2001–2013 |
| `Tranquillity.csv` | 59,451 | 1,336 | 8 | 8 | 2001–2013 |
| `Vocational_training.csv` | 139,166 | 4,122 | 4 | 4 | 2001–2013 |
| `Wages.csv` | 11,033 | 445 | 5 | 5 | 2001–2013 |

Column names, exact time values, raw geographic labels and per-file hashes are recorded in [dataset_inventory.json](../results/tables/dataset_inventory.json). The compact inventory is also available as [CSV](../results/tables/dataset_inventory.csv).

## Observation units and relationships

| File family | Native unit and candidate key | Relevance and integration limits |
|---|---|---|
| Jail population; jail population and capacity | State/UT × year × jail type | Core population, legal status, gender and overcrowding profiles. Candidate one-to-one alignment after harmonizing labels and checking keys. Each file has 4,023 records; this does not prove exact key agreement. |
| Age_group | State/UT × year × nationality category × legal status × gender | Core age profiles; four age-count fields. Aggregate to an agreed level before joining other demographic tables. |
| Caste; Domicile; Education; Religion | State/UT × year × gender × respective demographic category | Marginal demographic distributions with legal-status counts. Never join these categories to fabricate individual joint demographic records. Religion requires schema repair first. |
| IPC and SLL crime tables | State/UT × year × crime head, with separate convicted and undertrial files | Crime and legal-status context. Age/gender counts coexist with derived totals; identify crime subtotals before aggregation. |
| Sentence_period; Period_of_detention_of_undertrials | State/UT × year × sentence/detention band, plus gender where present | Convict sentence lengths and undertrial detention durations represent distinct populations. |
| Death_sentence; Recidivism; Rehabilitation; Education_facilities; Wages | Usually State/UT × year | Contextual counts or rates/pay values. Validate uniqueness and units individually. Admissions and releases are flows, unlike prison population snapshots. |
| Inmates_death; Inmates_escapee; Tranquillity; Inmates_released; parole | State/UT × year × event/detail | Supporting outcomes. Event categories may include totals or overlap; do not add indiscriminately. |
| Vocational_training; Value_of_goods_produced_by_inmates | State/UT × year × program/activity | Rehabilitation and economic context; participants may attend multiple programs. Currency is explicit for goods, but many financial fields require source-unit confirmation. |
| Budget; Expenditure; Expenditure_on_inmates; electronic equipment; vehicles; movements; training officers | Area_Name × TimePeriod × indicator | Administrative tables cover 2001–2010. Pivot only after checking uniqueness and aggregate/component distinctions. |
| Strength_of_officials | Area_Name × TimePeriod × indicator × staff subgroup | Staffing profiles; totals and constituent ranks must remain separate. |
| women prisoners with children; mental illness | State/UT × year | Supporting population summaries; narrower coverage and denominator definitions require validation. |
| Prison_details_2015 | Individual jail directory, with state and jail-type group information | Separate cross-section with 1,397 records. Contact/location fields are irrelevant for predictive features. Repeated number-of-jails fields are group attributes, not additive values. |
| Budget and actual expenditure 2015–2016 | State/UT × fiscal period inferred from filename | Separate 36-row cross-section; never join to 2001–2013 merely on state. |

These are candidate keys inferred from schemas. Uniqueness, key overlap, cardinality and actual joins belong to Phases 1–2; no joins were performed in this audit.

## Coverage and structural cautions

- Most historical tables contain year labels 2001–2013. Presence of all 13 year values does not establish a complete balanced state-year panel.
- Historical tables commonly contain 35 state/UT labels, but raw spelling/case variations raise counts to 36, 40, 43 or 70 in some files. These are distinct strings, not validated geographic entity counts. The inventory preserves all original labels.
- Examples include Chhatisgarh/Chhattisgarh, Tamilnadu/Tamil Nadu, Orissa/Odisha, Uttaranchal/Uttarakhand, Pondicherry/Puducherry, abbreviated island names, uppercase values and leading spaces. Harmonize documented aliases later; do not automatically merge genuine boundary changes.
- The 2015 directory includes Telangana, unlike the 2001–2013 historical period, and has only 35 distinct jurisdiction labels. Do not assume present-day coverage or backfill missing territories.
- Religion.csv has 8 header fields but 9 fields in every one of its 4,460 nonblank records. The fifth record field contains religion labels, suggesting an omitted religion header between gender and convicts. This is a proposed Phase 1 repair requiring explicit validation; the audit deliberately does not assign shifted fields.
- The women-with-children file contains one blank record. Its 446 nonblank records are counted separately from that blank record.
- Jail type includes Total/TOTAL, and the capacity file also uses SUB JAIL/SUB_JAIL. Totals must be reconciled with components rather than added to them.
- Many tables contain male, female and combined totals together. Select one consistent additive representation. Do not sum total columns and their components.
- Cross-file population figures can describe the same people. Combining overlapping tables by concatenation would double count; use separate views or validated joins.
- Counts are aggregate observations, not prisoner-level records. Association support will describe the fraction of aggregate transactions. Demographic correlations cannot establish individual risk or causal effects.
- Missingness, duplicate detection, numeric validity, outliers and total reconciliation remain Phase 1 work. No values were altered or dropped.

## Reproduce the audit

Run `python -m src.utils.audit_dataset` from the repository root. The script uses the standard CSV reader, verifies record widths, records coverage only for structurally consistent schemas, and hashes raw bytes. Output files are deterministic for identical raw input.

The current raw files are small enough for GitHub. The official download command is in the README. Check for existing CSVs first; do not repeat the download when the manifest matches.
