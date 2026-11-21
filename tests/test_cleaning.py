"""Check cleaning decisions that could otherwise alter the meaning of the data."""

import csv
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.preprocessing.cleaning import (check_totals, equations, infer_missing,
                                        load_cleaned, missing_mask, read_raw, sha256)
from src.preprocessing.schema import category_value, column_roles, row_scope


ROOT = Path(__file__).resolve().parents[1]


class CleaningRulesTest(unittest.TestCase):
    def test_religion_repair_keeps_record_alignment(self):
        frame, _, width, repaired = read_raw(ROOT / "data/raw/Religion.csv")
        self.assertEqual(width, 8)
        self.assertTrue(repaired)
        self.assertEqual(frame.iloc[0]["state_name"], "A & N Islands")
        self.assertEqual(frame.iloc[0]["religion"], "Christian")
        self.assertEqual(len(frame.columns), 9)

    def test_unexpected_width_fails_instead_of_shifting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.csv"
            path.write_text("a,b\n1,2,3\n")
            with self.assertRaises(ValueError):
                read_raw(path)

    def test_recovery_requires_two_agreeing_equations(self):
        frame = pd.DataFrame({"a": pd.array([pd.NA], dtype="Int64"),
                              "b": [2], "ab": [5], "c": [4], "ac": [7]})
        events = []
        infer_missing(frame, [("ab", ["a", "b"])], events, "example")
        self.assertTrue(pd.isna(frame.at[0, "a"]))
        infer_missing(frame, [("ab", ["a", "b"]), ("ac", ["a", "c"])], events, "example")
        self.assertEqual(frame.at[0, "a"], 3)
        self.assertEqual(len(events), 1)

    def test_conflicting_equations_do_not_impute(self):
        frame = pd.DataFrame({"a": pd.array([pd.NA], dtype="Int64"),
                              "b": [2], "ab": [5], "c": [4], "ac": [9]})
        infer_missing(frame, [("ab", ["a", "b"]), ("ac", ["a", "c"])], [], "example")
        self.assertTrue(pd.isna(frame.at[0, "a"]))

    def test_mismatch_is_flagged_without_overwriting_total(self):
        frame = pd.DataFrame({"Male": [2], "Female": [3], "Total": [6]})
        findings = check_totals(frame, equations(frame.columns), "example", "after")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["calculated"], 5)
        self.assertEqual(frame.at[0, "Total"], 6)

    def test_aliases_do_not_merge_changed_boundaries(self):
        self.assertEqual(category_value("state_name", " CHHATISGARH "), "Chhattisgarh")
        self.assertEqual(category_value("state_name", "Telangana"), "Telangana")
        self.assertNotEqual(category_value("state_name", "Telangana"), "Andhra Pradesh")

    def test_contacts_are_text_and_zeros_are_not_missing(self):
        roles = column_roles("Prison_details_2015.csv", ["State / UT Name", "Jail Type",
                              "Jail Sl.No.", "Contact No."])
        self.assertIn("Contact No.", roles["text"])
        self.assertNotIn("Contact No.", roles["numeric"])
        self.assertFalse(missing_mask(pd.Series(["0", "0.0", "Nil"])).any())

    def test_program_aliases_share_stable_canonical_labels(self):
        for column in ["vocational_trainings_program", "Vocation/Activity"]:
            variants = ["Electrical Motor Vinding", "Electrical Motor Winding",
                        "electrical motor winding", "Eiectrical Motarvinding"]
            self.assertEqual({category_value(column, v) for v in variants}, {"Electrical Motor Winding"})
            for value in ["Embrodary Unit", "Embroidery Unit", "D.T.P.", "DTP", *variants]:
                canonical = category_value(column, value)
                self.assertEqual(category_value(column, canonical), canonical)

    def test_scopes_distinguish_subtotals_and_civil_population(self):
        self.assertEqual(row_scope({"TYPE OF JAIL": "Total"}, "x"), "reported_total")
        self.assertEqual(row_scope({"details": "Un-natural Deaths"}, "x"), "reported_subtotal")
        self.assertEqual(row_scope({"CRIME HEAD": "(C) CIVIL AND OTHER CASES"}, "x"), "separate_population")
        with self.assertRaises(ValueError):
            load_cleaned(ROOT, "Age_group.csv", "all")


class CleanedArtifactsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = ROOT / "results/tables/cleaning"
        cls.specs = json.loads((cls.reports / "cleaned_schema.json").read_text())

    def test_all_raw_hashes_match_phase0(self):
        for item in json.loads((ROOT / "results/tables/dataset_inventory.json").read_text()):
            self.assertEqual(sha256(ROOT / "data/raw" / item["file"]), item["sha256"])

    def test_row_accounting_and_native_key_uniqueness(self):
        summary = pd.read_csv(self.reports / "quality_summary.csv")
        self.assertTrue((summary.rows_before == summary.rows_after + summary.duplicates_removed
                         + summary.quarantined_rows).all())
        for spec in self.specs:
            frame = pd.read_csv(ROOT / "data/processed/cleaned" / spec["file"], dtype=spec["dtypes"])
            self.assertFalse(frame.source_record.duplicated().any())
            if spec["grain"] == "validated_unique_keys":
                self.assertFalse(frame.duplicated(spec["roles"]["keys"]).any(), spec["file"])
            for c in spec["roles"]["numeric"]:
                self.assertTrue(frame[c].dropna().ge(0).all(), (spec["file"], c))
                if c not in spec["roles"]["continuous"]:
                    self.assertTrue(frame[c].dropna().mod(1).eq(0).all())

    def test_unexplained_missingness_and_ambiguous_records_are_preserved(self):
        age = pd.read_csv(ROOT / "data/processed/cleaned/Age_group.csv")
        self.assertEqual(age.age_16_18.isna().sum(), 1)
        summary = pd.read_csv(self.reports / "quality_summary.csv").set_index("file")
        self.assertEqual(summary.loc["Vocational_training.csv", "rows_after"], 4122)
        self.assertEqual(summary.loc["Vocational_training.csv", "duplicates_removed"], 0)

    def test_quality_flags_align_with_all_output_records(self):
        flags = pd.read_csv(self.reports / "row_flags.csv")
        self.assertFalse(flags.duplicated(["file", "source_record"]).any())
        for spec in self.specs:
            frame = pd.read_csv(ROOT / "data/processed/cleaned" / spec["file"])
            self.assertEqual(set(frame.source_record), set(flags.loc[flags.file.eq(spec["file"]), "source_record"]))

    def test_raw_to_cleaned_reconciliation_preserves_numeric_cells(self):
        ledger = pd.read_csv(self.reports / "excluded_records.csv")
        repairs = pd.read_csv(self.reports / "cell_actions.csv")
        approved = {(r.file, r.source_record, r.column): Decimal(str(r.new_value))
                    for r in repairs.itertuples() if r.action == "recover_from_agreeing_totals"}
        seen_repairs = set()
        for spec in self.specs:
            filename = spec["file"]
            with (ROOT / "data/raw" / filename).open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                columns = next(reader)
                raw = {i: row for i, row in enumerate(reader, start=2)
                       if row and any(v.strip() for v in row)}
            if filename == "Religion.csv":
                columns.insert(4, "religion")
            represented = {}
            for directory in ["cleaned", "quarantine"]:
                path = ROOT / "data/processed" / directory / filename
                if not path.exists():
                    continue
                with path.open(encoding="utf-8-sig", newline="") as handle:
                    for row in csv.DictReader(handle):
                        source = int(row["source_record"])
                        self.assertNotIn(source, represented)
                        represented[source] = row
            duplicates = ledger[ledger.file.eq(filename) & ledger.disposition.eq("duplicate_removed")]
            self.assertEqual(set(raw), set(represented) | set(duplicates.source_record))
            self.assertFalse(set(represented) & set(duplicates.source_record))
            for row in duplicates.itertuples():
                self.assertEqual(raw[row.source_record], raw[int(row.retained_record)])
            for source, row in represented.items():
                original = dict(zip(columns, raw[source]))
                for column in spec["roles"]["numeric"]:
                    before, after = original[column].strip(), row[column]
                    identity = (filename, source, column)
                    if before.casefold() in {"", "na", "n/a", "nan", "null", "none"}:
                        if after:
                            self.assertIn(identity, approved)
                            self.assertEqual(Decimal(after), approved[identity])
                            seen_repairs.add(identity)
                    else:
                        self.assertEqual(Decimal(before), Decimal(after), identity)
        self.assertEqual(seen_repairs, set(approved))


if __name__ == "__main__":
    unittest.main()
