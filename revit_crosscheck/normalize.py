"""編號與欄位值的正規化。

Revit 與文件常見的差異是全形/半形、大小寫、多餘空白，這些不該算成「不一致」。
"""

import re
import unicodedata

_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def normalize_key(value, ignore_hyphen=False):
    """設備編號比對用：全形轉半形、轉大寫、移除空白。"""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).upper()
    text = re.sub(r"\s+", "", text)
    if ignore_hyphen:
        text = re.sub(r"[-_]", "", text)
    return text


def normalize_text(value):
    """一般文字欄位比對用：全形轉半形、不分大小寫、空白壓成一格。"""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    return re.sub(r"\s+", " ", text).strip()


def parse_number(value):
    """從「1,200 mm」「H=2400」這類字串取出第一個數字；取不到回傳 None。"""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = unicodedata.normalize("NFKC", str(value)).replace(",", "")
    match = _NUMBER_RE.search(text)
    return float(match.group()) if match else None
