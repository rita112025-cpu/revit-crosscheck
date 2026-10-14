"""從規範書 PDF 擷取設備表。

規範書的表格常跨頁，而且續頁不一定重複標題列。判斷規則：
1. 第一個含有編號欄位的表格列，就是標題列。
2. 之後的表格若有完全相同的標題列，視為同一張表（每頁重複標題的情況）。
3. 若某頁最後一張表被採用，下一頁第一張表欄數相同又沒有標題，視為續表。
4. 其他表格（例如圖說清單）一律略過。

只處理有文字層的 PDF；掃描檔要先 OCR。
"""

import re
from pathlib import Path

from .readers import ReadError, Table, make_record


def _join_lines(text):
    """儲存格內的換行：中文接中文直接相連，其他情況補一個空白。"""
    parts = [part.strip() for part in text.split("\n") if part.strip()]
    if not parts:
        return ""
    joined = parts[0]
    for part in parts[1:]:
        if not joined[-1].isascii() and not part[0].isascii():
            joined += part
        else:
            joined += " " + part
    return joined


def _clean_cell(value):
    return _join_lines(str(value)) if value is not None else ""


def parse_pages(spec, page_count):
    """把 "1-3,5" 轉成頁碼清單（從 1 起算）；None 表示全部頁。"""
    if spec is None or str(spec).strip() == "":
        return list(range(1, page_count + 1))
    pages = []
    for part in str(spec).split(","):
        part = part.strip()
        match = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", part)
        if not match:
            raise ReadError(f"頁碼格式看不懂：「{part}」（範例：\"3-5,8\"）")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start < 1 or end < start or end > page_count:
            raise ReadError(f"頁碼 {part} 超出範圍（這份 PDF 共 {page_count} 頁）")
        pages.extend(range(start, end + 1))
    return pages


def _find_header(rows, key_column):
    for index, row in enumerate(rows):
        if key_column in row:
            return index
    return None


def read_pdf_table(path, key_column, pages=None, table_settings=None):
    try:
        import pdfplumber
    except ImportError as exc:
        raise ReadError("讀取 PDF 需要 pdfplumber：pip install pdfplumber") from exc

    name = Path(path).name
    headers = None
    key_position = None
    continuing = False
    has_text = False
    table = None

    with pdfplumber.open(path) as pdf:
        for page_number in parse_pages(pages, len(pdf.pages)):
            page = pdf.pages[page_number - 1]
            if (page.extract_text() or "").strip():
                has_text = True
            page_tables = page.extract_tables(table_settings or {})
            last_accepted = False

            for table_number, raw_rows in enumerate(page_tables, start=1):
                rows = [[_clean_cell(cell) for cell in row] for row in raw_rows]
                header_index = _find_header(rows, key_column)

                if headers is None:
                    if header_index is None:
                        last_accepted = False
                        continue
                    headers = rows[header_index]
                    key_position = headers.index(key_column)
                    table = Table(path=str(path), headers=headers)
                    start = header_index + 1
                elif header_index is not None and rows[header_index] == headers:
                    start = header_index + 1
                elif header_index is None and continuing and table_number == 1 and len(rows[0]) == len(headers):
                    start = 0
                else:
                    last_accepted = False
                    continue

                for row_index in range(start, len(rows)):
                    source = f"{name}:p{page_number}:表{table_number}:列{row_index + 1}"
                    record = make_record(headers, rows[row_index], key_position, source)
                    if record:
                        table.records.append(record)
                last_accepted = True

            continuing = last_accepted

    if table is None:
        if not has_text:
            raise ReadError(f"{path} 沒有文字層，看起來是掃描檔，需要先 OCR 才能擷取表格")
        raise ReadError(f"{path} 的表格裡找不到編號欄位「{key_column}」；"
                        "若表格沒有框線，可在設定檔加 \"pdf_table_settings\": {\"vertical_strategy\": \"text\", \"horizontal_strategy\": \"text\"}")
    return table
