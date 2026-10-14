import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from revit_crosscheck.cli import main
from revit_crosscheck.pdf_reader import _join_lines, parse_pages, read_pdf_table
from revit_crosscheck.readers import ReadError, read_table

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
HAS_PDFPLUMBER = importlib.util.find_spec("pdfplumber") is not None
HEADER = ["編號", "系統", "高度"]


def fake_pdfplumber(pages):
    """用假的 pdfplumber 測跨頁規則；pages 是 [(頁面文字, [表格, ...]), ...]。"""
    class Page:
        def __init__(self, text, tables):
            self._text, self._tables = text, tables

        def extract_text(self):
            return self._text

        def extract_tables(self, settings):
            return self._tables

    class Pdf:
        def __init__(self):
            self.pages = [Page(text, tables) for text, tables in pages]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    module = types.ModuleType("pdfplumber")
    module.open = lambda path: Pdf()
    return mock.patch.dict(sys.modules, {"pdfplumber": module})


class HelperTests(unittest.TestCase):
    def test_join_lines(self):
        self.assertEqual(_join_lines("天花\n喇叭 6W"), "天花喇叭 6W")
        self.assertEqual(_join_lines("第二次會議\n改為 BGM"), "第二次會議改為 BGM")
        self.assertEqual(_join_lines("2400\nmm"), "2400 mm")
        self.assertEqual(_join_lines("\n"), "")

    def test_parse_pages(self):
        self.assertEqual(parse_pages(None, 3), [1, 2, 3])
        self.assertEqual(parse_pages("1-2, 4", 5), [1, 2, 4])
        self.assertEqual(parse_pages(3, 5), [3])

    def test_parse_pages_errors(self):
        with self.assertRaises(ReadError):
            parse_pages("abc", 5)
        with self.assertRaises(ReadError):
            parse_pages("4-9", 5)
        with self.assertRaises(ReadError):
            parse_pages("0", 5)


class CrossPageRuleTests(unittest.TestCase):
    def read(self, pages, key="編號"):
        with fake_pdfplumber(pages):
            return read_pdf_table("spec.pdf", key)

    def test_repeated_header_each_page(self):
        table = self.read([
            ("文字", [[HEADER, ["A-1", "PA", "100"]]]),
            ("文字", [[HEADER, ["A-2", "PA", "200"]]]),
        ])
        self.assertEqual([r.key for r in table.records], ["A-1", "A-2"])
        self.assertEqual(table.records[1].source, "spec.pdf:p2:表1:列2")

    def test_continuation_without_header(self):
        table = self.read([
            ("文字", [[HEADER, ["A-1", "PA", "100"]]]),
            ("文字", [[["A-2", "PA", "200"]]]),
        ])
        self.assertEqual([r.key for r in table.records], ["A-1", "A-2"])

    def test_no_continuation_when_another_table_ends_the_page(self):
        # 第 1 頁設備表之後還有別的表，所以第 2 頁開頭的同欄數表格不算續表
        table = self.read([
            ("文字", [[HEADER, ["A-1", "PA", "100"]], [["圖號", "圖名", "版次"], ["E-1", "平面圖", "B"]]]),
            ("文字", [[["X-9", "無關", "1"]]]),
        ])
        self.assertEqual([r.key for r in table.records], ["A-1"])

    def test_no_continuation_when_column_count_differs(self):
        table = self.read([
            ("文字", [[HEADER, ["A-1", "PA", "100"]]]),
            ("文字", [[["E-1", "平面圖"]]]),
        ])
        self.assertEqual([r.key for r in table.records], ["A-1"])

    def test_different_header_table_ignored(self):
        table = self.read([
            ("文字", [[HEADER, ["A-1", "PA", "100"]], [["編號", "名稱"], ["Z-1", "別的表"]]]),
        ])
        self.assertEqual([r.key for r in table.records], ["A-1"])

    def test_header_split_across_lines(self):
        table = self.read([("文字", [[["設備\n編號", "系統"], ["A-1", "PA"]]])], key="設備編號")
        self.assertEqual(table.headers, ["設備編號", "系統"])

    def test_scanned_pdf_message(self):
        with self.assertRaisesRegex(ReadError, "OCR"):
            self.read([("", []), ("  ", [])])

    def test_key_column_not_found_message(self):
        with self.assertRaisesRegex(ReadError, "找不到編號欄位"):
            self.read([("有文字", [[["圖號", "圖名"], ["E-1", "平面圖"]]])])


@unittest.skipUnless(HAS_PDFPLUMBER, "需要 pdfplumber")
class ExamplePdfTests(unittest.TestCase):
    def test_reads_cross_page_table_and_skips_other_tables(self):
        table = read_table(EXAMPLES / "spec_table.pdf", "設備編號")
        keys = [r.key for r in table.records]
        self.assertEqual(keys, ["SP-001", "SP-002", "SP-003", "SP-004", "SP-005", "SP-006", "DS-001"])
        self.assertNotIn("E-101", keys)

    def test_multiline_cell_joined(self):
        table = read_table(EXAMPLES / "spec_table.pdf", "設備編號")
        sp004 = next(r for r in table.records if r.key == "SP-004")
        self.assertEqual(sp004.values["設備名稱"], "天花喇叭 6W")

    def test_page_selection(self):
        table = read_table(EXAMPLES / "spec_table.pdf", "設備編號", pages="1")
        self.assertEqual(len(table.records), 4)

    def test_end_to_end_matches_csv_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = main([
                "--model", str(EXAMPLES / "model_schedule.txt"),
                "--docs", str(EXAMPLES / "spec_table.pdf"),
                "--config", str(EXAMPLES / "mapping_pdf.json"),
                "--out", tmp,
            ])
            self.assertEqual(code, 1)
            report = (Path(tmp) / "crosscheck.csv").read_text(encoding="utf-8-sig")
        self.assertIn("SP-003,系統,PA,BGM", report)
        self.assertIn("spec_table.pdf:p2:表1:列2", report)


if __name__ == "__main__":
    unittest.main()
