# Data selection report

Phase 2 selects task-relevant sources, attributes and comparable state-year observations. We establish a shared cohort of **437 state-years** for the planned K-Medoids and association-mining tasks, while retaining broader source-specific descriptive views. No ratios, encodings, scaling, bins, transactions, models or descriptive statistical results have been generated. All Phase 1 cleaned files and original raw files remain unchanged.

## Selected tasks and observation units

We retain K-Medoids as the single classification/clustering choice. These data describe aggregate prison systems, without individual prisoner records or a natural individual-level prediction target. The primary unit is one state/UT-year. Repeated years from the same state are related observations; the cohort is not an independent sample of 437 states or prisoners. FP-Growth and MAFIA will use the same state-year profiles after transformation into transactions in Phase 3. Python/Spark comparisons will share the same selected cohort and feature definitions.

Descriptive analysis has separate native observation units: state-year-jail-type, state-year-gender-demographic-category, state-year-crime-head and other source-specific groups. We retain those dimensions and do not manufacture joint prisoner records from marginal tables. The five core feature formulas below are specified for later computation, not calculated in Phase 2.

## File decisions

Every one of the 37 cleaned CSV files was reviewed. Four sources support the primary profiles. Twenty-seven sources have selected descriptive-view definitions; ten administrative or temporally incompatible sources are deferred. A descriptive candidate is not a promise to sum every indicator or analyze every possible combination. The assignment explicitly calls for task-relevant selection; the selected scope centers on historical prisoner populations, composition and supporting outcomes. Deferred sources remain unchanged and available if later scope needs justify them.

| Source file | Primary profiles | Descriptive candidate | Rationale |
|---|---|---|---|
| `Age_group.csv` | Yes | Yes | Primary profile source; explicit common-cohort and denominator checks required. Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Caste.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Death_sentence.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Domicile.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Education.csv` | Yes | Yes | Primary profile source; explicit common-cohort and denominator checks required. Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Education_facilities.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `IPC_crime_inmates_convicted.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `IPC_crime_inmates_under_trial.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Inmates_death.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Inmates_escapee.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Jail wise population of prison inmates.csv` | Yes | Yes | Primary profile source; explicit common-cohort and denominator checks required. Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Other Prison data/Budget.CSV` | No | Deferred | Administrative budget indicators cover only 2001–2010; outside the selected population/demographic scope, with units requiring verification. |
| `Other Prison data/Details_of_electronic_equipments_used_in_prison.CSV` | No | Deferred | Equipment inventory is outside the selected prisoner-profile scope and has shorter temporal coverage. |
| `Other Prison data/Details_of_inmates_parole_during_the_year.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Other Prison data/Expenditure.CSV` | No | Deferred | Administrative spending indicators cover only 2001–2010; outside the selected population/demographic scope, with units requiring verification. |
| `Other Prison data/Expenditure_on_inmates.CSV` | No | Deferred | Administrative spending indicators cover only 2001–2010; outside the selected population/demographic scope, with units requiring verification. |
| `Other Prison data/Inmates_released.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Other Prison data/Inmates_suffering_from_mental_ilness.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Other Prison data/Movements_outside_jail_premises.CSV` | No | Deferred | Movement indicators are flows rather than prisoner-profile attributes; shorter temporal coverage. |
| `Other Prison data/Number_of_vehicles_available.CSV` | No | Deferred | Vehicle inventory is outside the selected prisoner-profile scope and has shorter temporal coverage. |
| `Other Prison data/Number_of_women_prisoners_with_children.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Other Prison data/Period_of_detention_of_undertrials.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Other Prison data/Population_and_capacity_of_jails.csv` | Yes | Yes | Primary profile source; explicit common-cohort and denominator checks required. Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Other Prison data/SLL_Crime_headwise_distribution_of_inmates_who_convicted.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Other Prison data/SLL_crime_head_wise_distribution_of_inmates_under_trial.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Other Prison data/Strength_of_officials.CSV` | No | Deferred | Overlapping staff hierarchies require a separate resource study; not prisoner demographic observations. |
| `Other Prison data/Total_Budget_and_Actual_Expenditure_during_ the_year_2015_2016.csv` | No | Deferred | Separate 2015–2016 fiscal cross-section cannot join to 2001–2013 on state alone. |
| `Other Prison data/Training_of_Jail_Officers.CSV` | No | Deferred | Officer training is a separate administrative population; not prisoner vocational training. |
| `Other Prison data/Value_of_goods_produced_by_inmates.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Prison_details_2015.csv` | No | Deferred | Separate 2015 jail directory; contacts and jail identifiers are irrelevant to historical state-year profiles. |
| `Recidivism.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Rehabilitation.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Religion.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Sentence_period.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Tranquillity.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Vocational_training.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |
| `Wages.csv` | No | Yes | Historical prisoner statistics retained for source-specific descriptive analysis; do not combine overlapping populations. |

Full decisions are saved in [file_decisions.csv](../results/tables/selection/file_decisions.csv).

## Attribute selection

| Planned feature | Selected native inputs | Selection rationale |
|---|---|---|
| Occupancy ratio | Total prisoners from the population file; total capacity from the capacity file | Capacity pressure rather than absolute population size. |
| Undertrial share | Total_Under_trial and Grand_Total from reported population totals | One legal-status composition measure; omit the complementary status-share block. |
| Female share | Total_Female and Grand_Total from reported population totals | Aggregate gender composition rather than both complementary gender shares. |
| Age 18–30 share | age_18_30 with nationality, legal-status and gender grouping fields | One age-profile measure; compare the complete age distribution to the reference before admitting a state-year. |
| Illiterate share | Education label, gender and the four legal-status count columns | One education-profile measure; admit only complete education distributions matching the reference. |

The [feature contract](../results/tables/selection/feature_contract.json) records these future formulas and sources. The numerator counts must be aggregated independently within each demographic source in Phase 3 before division by the verified common population denominator. The selected count files deliberately do not contain any of these ratio columns.

State and year are retained for identity, grouping, coverage and later benchmark alignment; source-record numbers provide provenance. None is a numeric distance feature or transaction item. Category labels in the age/education inputs are grouping or predicate fields, not independent encoded predictors. The other age counts and the eight gender/status population cells are validation evidence rather than extra primary features.

We exclude is_state, jail serial numbers, telephone/email/address fields, raw population-size features, complementary age/gender/status shares and repeated combined totals from the primary feature specification. Caste and religion remain descriptive-only, rather than inputs to aggregate clustering or individual risk classification. Selected gender/age/education composition also requires careful aggregate interpretation; no individual decisions or causal conclusions are supported. No claim of statistical feature independence or low correlation is made before Phase 4.

The column-level [attribute decisions](../results/tables/selection/attribute_decisions.csv) distinguish selected descriptive measures, keys, provenance, primary numerator/denominator inputs, grouping fields, validation-only fields and exclusions. Descriptive views choose atomic male/female counts rather than including their combined total as an additional additive field. Women-with-children counts retain mothers and children as different measures, not a combined population. Capacity and population are also separate quantities with different denominators. The capacity file’s “Number of Central Jails” header is retained literally; its use across jail-type rows requires interpretation as a source field, not proof that every record refers to central jails.

## Key validation and permissible joins

| Relationship | Keys and cardinality | Finding and permitted use |
|---|---|---|
| Jail population ↔ capacity, native level | State, year, jail type; one-to-one | 4,023 matched rows and no key duplication. Of 12,069 male/female/combined population comparisons, eight cells disagree across four rows. Native-key matching alone does not establish measurement agreement. |
| Reported population totals ↔ reported capacity totals | State, year; one-to-one | 447 matched rows. All 1,341 male/female/combined population comparisons agree. These verified totals form the profile reference. |
| Age or education native records → selected cohort keys | State, year; many-to-one filter | Membership filtering preserves native records. It does not multiply rows or join one demographic distribution onto another. |
| Native age ↔ native education | State, year would be many-to-many | Forbidden: this would create fictional joint age/education observations and multiply counts. Aggregate each source independently in Phase 3, then validate a one-to-one profile join. |
| 2015/2015–2016 sources ↔ historical statistics | Joining on state alone | Forbidden: dates and geographic boundaries differ. |

All joins used by the pipeline declare pandas cardinality validation and reject null keys. The population/capacity join is outer-checked before any matched output is accepted, so unmatched records cannot disappear silently. The [join contracts](../results/tables/selection/join_contracts.json) record accepted and rejected integration patterns.

The jail-type disagreements are in Punjab (2007: Central and District Jail) and Odisha (2005: District and Sub Jail). Their state-year totals agree across the two files. We retain those state-years at the verified total level for profiles but do not reconcile or silently overwrite the conflicting jail-type measures. The eight individual differences are in [native_population_disagreements.csv](../results/tables/selection/native_population_disagreements.csv).

## Marginal population compatibility

Each demographic source is checked against the same 447 reference state-years. Category grids use the explicit levels in the source schemas, not a row-count approximation. For age, the expected grid is two nationality categories × four statuses × two genders = sixteen records. For education it is six schooling levels × two genders = twelve records. No observed category pair may be duplicated or missing. All selected demographic measures must be nonmissing.

We then compare each of the eight gender × legal-status count cells against the jail-population reference. This catches contradictions that cancel in a grand total. These sums are used only as selection/denominator validation; they are not saved as transformed features or interpreted as analytical findings. A partially missing sum is not treated as zero.

| Marginal source | Reference keys | Present keys | Complete grids | Complete, nonmissing and population-compatible keys |
|---|---:|---:|---:|---:|
| `Age_group.csv` | 447 | 447 | 447 | 444 |
| `Caste.csv` | 447 | 446 | 446 | 431 |
| `Domicile.csv` | 447 | 446 | 446 | 445 |
| `Education.csv` | 447 | 446 | 444 | 444 |
| `Religion.csv` | 447 | 446 | 446 | 446 |

The full [marginal compatibility table](../results/tables/selection/marginal_compatibility.csv) records presence, expected/observed rows, missing cells, disagreeing fields and eligibility for every reference key. These counts describe data suitability, not prisoner distributions.

The primary cohort excludes three age cases: Tripura 2004 and Uttar Pradesh 2001 disagree on male detainee/other counts despite matching grand totals; West Bengal 2013 contains the missing youngest-age count. It excludes three education cases: Karnataka 2003 is absent, while Maharashtra 2010 and Tamil Nadu 2002 have incomplete category grids and disagreeing population cells. These newly observed cross-file issues were not within the scope of Phase 1’s within-file consistency checks. No cleaned source value is changed to force agreement.

## Primary cohort and denominator exclusions

The observed reference contains 447 state-year records over 2001–2013 and 35 historical state/UT labels. The 35 × 13 grid has 455 possible keys; eight Arunachal Pradesh keys for 2001–2008 are absent. We record them in [absent_reference_keys.csv](../results/tables/selection/absent_reference_keys.csv), without inventing zero counts or implying a balanced panel.

Of the 447 observed reference keys, 441 have complete compatible age and education data. Four of those report zero prisoners in Lakshadweep. Their population counts are preserved as valid recorded zeros, but demographic shares would be 0/0, so they are excluded from ratio-based profiles. We do not replace zero denominators with an epsilon or define an unsupported zero share. All retained profile capacities and prisoner denominators are strictly positive.

| Excluded state/UT | Year | Reason |
|---|---:|---|
| Karnataka | 2003 | Age/education completeness or population compatibility |
| Lakshadweep | 2004 | Zero prisoner denominator; demographic proportions undefined |
| Lakshadweep | 2006 | Zero prisoner denominator; demographic proportions undefined |
| Lakshadweep | 2012 | Zero prisoner denominator; demographic proportions undefined |
| Lakshadweep | 2013 | Zero prisoner denominator; demographic proportions undefined |
| Maharashtra | 2010 | Age/education completeness or population compatibility |
| Tamil Nadu | 2002 | Age/education completeness or population compatibility |
| Tripura | 2004 | Age/education completeness or population compatibility |
| Uttar Pradesh | 2001 | Age/education completeness or population compatibility |
| West Bengal | 2013 | Age/education completeness or population compatibility |

Thus **447 observed reference keys = 437 profile keys + 6 incompatible/incomplete marginal keys + 4 zero-denominator keys**. The eight absent keys are outside this accounting. Exclusion metadata is saved in [profile_exclusions.csv](../results/tables/selection/profile_exclusions.csv) and the complete reference eligibility map in [cohort_eligibility.csv](../results/tables/selection/cohort_eligibility.csv). The complete-case cohort can differ systematically from excluded records; this selection limitation must accompany later cluster and association interpretations.

## Saved selected inputs

| File under data/processed/selected | Rows | Purpose |
|---|---:|---|
| population_capacity_reference.csv | 447 | Verified state-year counts and provenance, including atomic population cells for comparability checks. Validation reference, not a model matrix. |
| profile_base_counts.csv | 437 | State/year, two source IDs and four native counts: prisoners, capacity, female prisoners and undertrials. |
| profile_age_counts.csv | 6,992 | Sixteen native records per selected state-year; nationality/status/gender dimensions and age_18_30 counts. |
| profile_education_counts.csv | 5,244 | Twelve native records per selected state-year; education/gender dimensions and four legal-status count columns. |

These files are projections, filters and a verified reference join. They preserve source-record IDs and unchanged source values. There is no source-table many-to-many join, feature ratio, coding of categories, scaling, binning or transaction expansion. Saved dtypes and hashes are in [selected_manifest.json](../results/tables/selection/selected_manifest.json).

## Source-specific descriptive views

To avoid storing another full copy of 27 cleaned tables, [descriptive_views.json](../results/tables/selection/descriptive_views.json) specifies their selected native fields, row policy and native keys. `load_descriptive_view(root, filename)` materializes one view with key names standardized to state/year. It returns eligible records by default; use `eligible_only=False` only to inspect all source rows and their explicit eligibility flags.

The view policy excludes reported total/subtotal rows, missing selected-measure groups, contradictory source-total groups and ambiguous native keys. For fixed category sets, it also checks full state-year grids, so quarantined IPC crime keys cannot silently become partial crime totals. The five demographic marginal views additionally require population compatibility. Training and goods activity categories are variable by location, so a global Cartesian grid is inappropriate; instead any state-year with an ambiguous or missing detail record is excluded as a whole. This does not certify that unreported training/goods programs are zero or that different programs contain distinct participants.

Outlier flags are retained as metadata and do not trigger selection exclusions. Coverage differs by descriptive source and may exceed the 437-key primary cohort when positive population denominators are unnecessary for count descriptions. The [source-view coverage table](../results/tables/selection/source_view_coverage.csv) records eligible rows, native key duplicates and state-year coverage. It does not establish that different sources are additive or have equal coverage. In Phase 4, report the coverage used for each result and consider a stable comparison cohort before interpreting national time trends. Financial/wage units still need source verification before unit-specific comparisons.

## Leakage and interpretation safeguards

There is no classification target and no supervised split at this phase. We do not invent labels from contemporaneous feature thresholds and report them as an independently predicted outcome. State/year IDs and source IDs are excluded from model distances and transaction items. Cluster assignments will never be recycled as inputs to produce apparently predictive association rules. We use one age share, one education share, one gender share and one status share rather than complete redundant compositions, and do not put raw scale-dominated population counts into the planned clustering representation.

The same five profile quantities will be discretized for FP-Growth/MAFIA only after explicit Phase 3 rules. The transformation must not duplicate equivalent facts as multiple items or make source rows stand for invented prisoners. Any future holdout evaluation must fit learned scaling/bins/feature decisions on training data only and consider grouping by state or time. Descriptive clustering itself has no classifier accuracy claim; repeated state-years limit independence and generalization.

## Execution and verification

Run `python -m src.preprocessing.selection` from the repository root, or execute [01_Preprocessing.ipynb](../notebooks/01_Preprocessing.ipynb) with the provided notebook runner. No new dependency is required. All nine Phase 2 tests and fourteen Phase 1 regression tests passed. Tests verify null-key rejection, declared join cardinalities, marginal missingness, unchanged numeric source values, denominator safety, cohort accounting, exact provenance, source-specific eligibility, absence of Phase 3 features and manifest integrity. The notebook contains seven Phase 1 and eight Phase 2 executable cells. Final execution/determinism evidence is saved in [verification.json](../results/tables/selection/verification.json).

## Methodological references

Selection uses separate checks for schema, entity identity, redundant totals, irrelevant identifiers and compatible denominators. The [dataset audit](dataset_audit.md) records source-table observation units. Feature decisions follow measured coverage and consistency rather than treating every numeric column as suitable input.

Phase 2 is complete. Phase 3 will independently aggregate selected marginal counts, calculate the five ratios, scale appropriate features and define reproducible discretization/transaction rules after approval.
