"""Explicit column roles and conservative category corrections for the source files."""

import re


STATE_COLUMNS = {
    "state_name", "STATE/UT", "State_UT_name", "Area_Name", "State / UT Name",
    "State/UT (Col. No. 2)", "State/UT",
}
TEXT_COLUMNS = STATE_COLUMNS | {
    "category", "type", "gender", "caste", "domicile", "education", "religion",
    "CRIME HEAD", "details", "detail", "Jail_Type", "Indicator_Name",
    "Electronic_equipments_used", "DETAILS", "Number of Vehicles Available",
    "PERIOD OF DETENTION", "TYPE OF JAIL", "Subgroup_Val", "Vocation/Activity",
    "Category", "Jail Type", "Jail Name", "Contact No.", "VC for Remand Purpose",
    "VC for Trial Purpose", "VC for Other Purpose", "Location1", "Location2",
    "Email ID", "sentence_period", "vocational_trainings_program",
}
FREE_TEXT = {"Jail Name", "Contact No.", "Location1", "Location2", "Email ID"}
MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none"}
CANONICAL_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu & Kashmir",
    "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
    "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal", "Andaman & Nicobar Islands", "Chandigarh",
    "Dadra & Nagar Haveli", "Daman & Diu", "Delhi", "Lakshadweep", "Puducherry",
]
UNION_TERRITORIES = {
    "Andaman & Nicobar Islands", "Chandigarh", "Dadra & Nagar Haveli",
    "Daman & Diu", "Delhi", "Lakshadweep", "Puducherry",
}
STATE_ALIASES = {name.casefold(): name for name in CANONICAL_STATES}
STATE_ALIASES.update({
    "a & n islands": "Andaman & Nicobar Islands",
    "andaman and nicobar islands": "Andaman & Nicobar Islands",
    "d & n haveli": "Dadra & Nagar Haveli",
    "dadra and nagar haveli": "Dadra & Nagar Haveli",
    "daman and diu": "Daman & Diu", "chhatisgarh": "Chhattisgarh",
    "tamilnadu": "Tamil Nadu", "orissa": "Odisha", "uttaranchal": "Uttarakhand",
    "pondicherry": "Puducherry", "jammu and kashmir": "Jammu & Kashmir",
})

# These are spelling/format corrections, not mergers of distinct courses or trades.
PROGRAM_ALIASES = {
    "phenyle": "Phenyl", "phyenyle": "Phenyl", "dyaing": "Dyeing",
    "masanary": "Masonry", "masary": "Masonry", "plumbering": "Plumbing",
    "embrodary unit": "Embroidery Unit", "electrical motor vinding": "Electrical Motor Winding",
    "eiectrical motarvinding": "Electrical Motor Winding", "d.t.p.": "DTP",
    "dtp": "DTP", "tailouring": "Tailoring", "nil": "Nil",
}
# Canonical spellings must map to themselves when cleaning is repeated.
PROGRAM_ALIASES.update({value.casefold(): value for value in list(PROGRAM_ALIASES.values())})


def token(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def category_value(column, value):
    value = re.sub(r"\s+", " ", value.strip())
    if column in STATE_COLUMNS:
        return STATE_ALIASES.get(value.casefold(), value)
    if column in {"Jail_Type", "TYPE OF JAIL", "Jail Type"}:
        key = value.replace("_", " ").casefold()
        names = ["Central Jail", "District Jail", "Sub Jail", "Women Jail", "Open Jail",
                 "Special Jail", "Borstal School", "Others", "Total"]
        return {x.casefold(): x for x in names}.get(key, value)
    if column == "sentence_period":
        return {"3 less than 6 months": "3 - 6 months",
                "10 less than 3 months": "Less than 3 months"}.get(value.casefold(), value)
    if column in {"vocational_trainings_program", "Vocation/Activity"}:
        return PROGRAM_ALIASES.get(value.casefold(), value.casefold().capitalize())
    if column == "CRIME HEAD":
        return value.upper()
    if column == "DETAILS":
        for prefix, label in [("F1 ", "Number of persons released on parole"),
                              ("F2 ", "Number of parole absconders"),
                              ("F3 ", "Number of parole absconders rearrested")]:
            if value.startswith(prefix):
                return "Parole released - " + label
    if column == "details":
        # Later release records omit the convict prefix used in earlier years.
        released = {
            "Released after completion of conviction", "Premature release", "Released on appeal",
            "Released on bail", "Pardons", "Transferred to other States",
            "Other Releases (due to illness,transferred to Mental hospital)",
        }
        if value in released:
            value = "Convicts Released - " + value
        return value.replace("illness,transferred", "illness, transferred")
    return value


def column_roles(filename, columns):
    text = [c for c in columns if c in TEXT_COLUMNS]
    numeric = [c for c in columns if c not in text]
    identifiers = [c for c in numeric if c.lower() in {"year", "timeperiod", "is_state"}
                   or "Sl.No." in c or c.startswith("S.No.")]
    measures = [c for c in numeric if c not in identifiers]
    continuous = set()
    if filename in {"Wages.csv", "Value_of_goods_produced_by_inmates.csv"}:
        continuous.update(measures)
    if filename in {"Budget.CSV", "Expenditure.CSV", "Expenditure_on_inmates.CSV"}:
        continuous.add("Data_Value")
    if filename.startswith("Total_Budget_and_Actual_"):
        continuous.update(measures)
    keys = [c for c in text if c not in FREE_TEXT]
    keys += [c for c in numeric if c.lower() in {"year", "timeperiod"}]
    if filename == "Prison_details_2015.csv":
        keys = ["State / UT Name", "Jail Type", "Jail Sl.No."]
    return {"text": text, "numeric": numeric, "identifiers": identifiers,
            "measures": measures, "continuous": sorted(continuous), "keys": keys}


def row_scope(row, filename):
    if filename == "Prison_details_2015.csv":
        return "directory"
    for column in ["Jail_Type", "TYPE OF JAIL", "PERIOD OF DETENTION", "CRIME HEAD",
                   "details", "Indicator_Name", "Vocation/Activity", "Subgroup_Val"]:
        value = str(row.get(column, "")).casefold()
        if value.startswith("total") or value.startswith("(c) civil"):
            return "separate_population" if value.startswith("(c) civil") else "reported_total"
        if value == "un-natural deaths" or value in {"officers", "other cadres"}:
            return "reported_subtotal"
    return "detail"
