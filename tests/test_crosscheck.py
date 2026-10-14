import csv
import json
import tempfile
import unittest
from pathlib import Path

from revit_crosscheck.cli import main
from revit_crosscheck.compare import (
    DUPLICATE, MISMATCH, MISSING_IN_DOCS, MISSING_IN_MODEL, UNPARSABLE, compare,
)
from revit_crosscheck.normalize import normalize_key, normalize_text, parse_number
from revit_crosscheck.readers import ReadError, read_table

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

CONFIG = {
    "model": {"key": "標記"},
    "docs": {"key": "設備編號"},
    "fields": [
        {"name": "系統", "model": "系統類型", "docs": "系統", "type": "text"},
        {"name": "安裝高度", "model": "偏移", "docs": "安裝高度(mm)", "type": "number", "tolerance": 10},
    ],
}


class NormalizeTests(unittest.TestCase):
    def test_key_fullwidth_case_and_spaces(self):
        self.assertEqual(normalize_key("ｓｐ－００５ "), "SP-005")

    def test_key_ignore_hyphen(self):
        self.assertEqual(normalize_key("SP-005", ignore_hyphen=True), normalize_key("SP005"))

    def test_text(self):
        self.assertEqual(normalize_text("  Ｐa  "), normalize_text("PA"))

    def test_number(self):
        self.assertEqual(parse_number("1,200 mm"), 1200.0)
        self.assertEqual(parse_number("H=2400"), 2400.0)
        self.assertEqual(parse_number(2400), 2400.0)
        self.assertIsNone(parse_number("待確認"))
        self.assertIsNone(parse_number(""))


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_revit_export_skips_title_and_blank_rows(self):
        table = read_table(EXAMPLES / "model_schedule.txt", "標記")
        self.assertEqual([r.key for r in table.records][:2], ["SP-001", "SP-002"])
        self.assertEqual(len(table.records), 7)
        self.assertEqual(table.records[0].source, "model_schedule.txt:4")

    def test_utf16_export(self):
        path = self.dir / "utf16.txt"
        path.write_bytes("\"標記\"\t\"偏移\"\n\"A-1\"\t\"100\"\n".encode("utf-16"))
        table = read_table(path, "標記")
        self.assertEqual(table.records[0].values["偏移"], "100")

    def test_big5_csv(self):
        path = self.dir / "big5.csv"
        path.write_bytes("設備編號,系統\nA-1,廣播\n".encode("cp950"))
        self.assertEqual(read_table(path, "設備編號").records[0].values["系統"], "廣播")

    def test_excel_with_sheet_and_title_row(self):
        import openpyxl
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "設備表"
        sheet.append(["設備表 Rev.B"])
        sheet.append(["設備編號", "系統"])
        sheet.append(["SP-001", "PA"])
        sheet.append([None, None])
        sheet.append(["SP-002", "PA"])
        path = self.dir / "docs.xlsx"
        workbook.save(path)
        table = read_table(path, "設備編號", sheet="設備表")
        self.assertEqual([r.key for r in table.records], ["SP-001", "SP-002"])
        self.assertEqual(table.records[1].source, "docs.xlsx!設備表:5")

    def test_missing_key_column(self):
        with self.assertRaises(ReadError):
            read_table(EXAMPLES / "model_schedule.txt", "不存在的欄位")

    def test_missing_sheet(self):
        import openpyxl
        path = self.dir / "docs.xlsx"
        openpyxl.Workbook().save(path)
        with self.assertRaises(ReadError):
            read_table(path, "設備編號", sheet="沒有這張")


class CompareTests(unittest.TestCase):
    def run_examples(self):
        model = read_table(EXAMPLES / "model_schedule.txt", "標記")
        docs = read_table(EXAMPLES / "equipment_list.csv", "設備編號")
        return compare(model, docs, CONFIG)

    def test_example_findings(self):
        issues, matched = self.run_examples()
        found = {(i.kind, i.key, i.field) for i in issues}
        self.assertEqual(matched, 6)
        self.assertEqual(found, {
            (MISMATCH, "SP-003", "系統"),
            (MISMATCH, "SP-004", "安裝高度"),
            (MISSING_IN_DOCS, "DS-002", ""),
            (MISSING_IN_MODEL, "SP-006", ""),
        })

    def test_within_tolerance_not_reported(self):
        issues, _ = self.run_examples()
        self.assertFalse(any(i.key.strip().upper() == "SP-005" for i in issues))

    def test_issue_keeps_both_sources(self):
        issues, _ = self.run_examples()
        sp004 = next(i for i in issues if i.key == "SP-004")
        self.assertEqual(sp004.model_source, "model_schedule.txt:7")
        self.assertEqual(sp004.docs_source, "equipment_list.csv:6")

    def test_duplicate_and_unparsable(self):
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "m.csv"
            docs_path = Path(tmp) / "d.csv"
            model_path.write_text("標記,系統類型,偏移\nA-1,PA,100\nA-1,PA,200\n", encoding="utf-8")
            docs_path.write_text("設備編號,系統,安裝高度(mm)\nA-1,PA,待確認\n", encoding="utf-8")
            issues, _ = compare(read_table(model_path, "標記"), read_table(docs_path, "設備編號"), CONFIG)
        kinds = [i.kind for i in issues]
        self.assertIn(DUPLICATE, kinds)
        self.assertIn(UNPARSABLE, kinds)

    def test_unknown_field_column_raises(self):
        model = read_table(EXAMPLES / "model_schedule.txt", "標記")
        docs = read_table(EXAMPLES / "equipment_list.csv", "設備編號")
        bad = dict(CONFIG, fields=[{"name": "x", "model": "不存在", "docs": "系統"}])
        with self.assertRaises(ValueError):
            compare(model, docs, bad)


class CliTests(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = main([
                "--model", str(EXAMPLES / "model_schedule.txt"),
                "--docs", str(EXAMPLES / "equipment_list.csv"),
                "--config", str(EXAMPLES / "mapping.json"),
                "--out", tmp,
            ])
            self.assertEqual(code, 1)
            with open(Path(tmp) / "crosscheck.csv", encoding="utf-8-sig") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[0][:2], ["類型", "編號"])
            self.assertEqual(len(rows), 5)
            html = (Path(tmp) / "crosscheck.html").read_text(encoding="utf-8")
            self.assertIn("SP-006", html)

    def test_no_differences_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            same = Path(tmp) / "same.csv"
            same.write_text("編號,高度\nA-1,100\n", encoding="utf-8")
            config = Path(tmp) / "c.json"
            config.write_text(json.dumps({
                "model": {"key": "編號"}, "docs": {"key": "編號"},
                "fields": [{"name": "高度", "model": "高度", "docs": "高度", "type": "number"}],
            }), encoding="utf-8")
            code = main(["--model", str(same), "--docs", str(same), "--config", str(config), "--out", tmp])
            self.assertEqual(code, 0)

    def test_bad_config_returns_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "c.json"
            config.write_text('{"model": {}}', encoding="utf-8")
            code = main([
                "--model", str(EXAMPLES / "model_schedule.txt"),
                "--docs", str(EXAMPLES / "equipment_list.csv"),
                "--config", str(config), "--out", tmp,
            ])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
