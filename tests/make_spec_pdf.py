"""產生 examples/spec_table.pdf：模擬規範書裡跨頁的設備表。

只在需要重新產生範例時執行，平常測試直接讀已提交的 PDF。
需要 reportlab 與 Windows 內建的標楷體（kaiu.ttf）：

    pip install reportlab
    python tests/make_spec_pdf.py
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT = "Kai"
OUTPUT = Path(__file__).resolve().parent.parent / "examples" / "spec_table.pdf"

HEADER = ["設備編號", "設備名稱", "系統", "安裝高度(mm)", "備註"]
PAGE1_ROWS = [
    ["SP-001", "天花喇叭 6W", "PA", "2400", ""],
    ["SP-002", "天花喇叭 6W", "PA", "2400", ""],
    ["SP-003", "天花喇叭 6W", "BGM", "2400", "第二次會議\n改為 BGM"],
    ["SP-004", "天花\n喇叭 6W", "PA", "2400", ""],
]
# 第 2 頁接續同一張表，但沒有重複標題列
PAGE2_ROWS = [
    ["SP-005", "壁掛喇叭 10W", "PA", "2705", ""],
    ["SP-006", "天花喇叭 6W", "PA", "2400", "月台延伸段新增"],
    ["DS-001", "顯示器 55吋", "PIS", "2200", ""],
]
# 同一頁另一張無關的表，不該被讀進來
DRAWING_LIST = [["圖號", "圖名"], ["E-101", "弱電平面圖"], ["E-102", "弱電系統圖"]]


def _table(rows, widths):
    table = Table(rows, colWidths=widths)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def main():
    pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/kaiu.ttf"))
    body = ParagraphStyle("body", fontName=FONT, fontSize=12, leading=18)
    widths = [70, 110, 50, 90, 140]
    story = [
        Paragraph("第 5 章 弱電設備規範", body),
        Spacer(1, 8),
        Paragraph("5.3 廣播及顯示設備一覽表如下，安裝高度以完成面起算。", body),
        Spacer(1, 12),
        _table([HEADER] + PAGE1_ROWS, widths),
        PageBreak(),
        _table(PAGE2_ROWS, widths),
        Spacer(1, 24),
        Paragraph("5.4 相關圖說", body),
        Spacer(1, 8),
        _table(DRAWING_LIST, [80, 160]),
    ]
    SimpleDocTemplate(str(OUTPUT), pagesize=A4, title="弱電設備規範（範例）").build(story)
    print(f"已產生 {OUTPUT}")


if __name__ == "__main__":
    main()
