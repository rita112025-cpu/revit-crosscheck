"""比對模型明細表與文件，產生差異清單。"""

from dataclasses import dataclass

from .normalize import normalize_key, normalize_text, parse_number

MISSING_IN_DOCS = "文件沒有"
MISSING_IN_MODEL = "模型沒有"
MISMATCH = "數值不符"
DUPLICATE = "編號重複"
UNPARSABLE = "無法解析數字"

ISSUE_ORDER = [MISMATCH, MISSING_IN_DOCS, MISSING_IN_MODEL, DUPLICATE, UNPARSABLE]


@dataclass
class Issue:
    kind: str
    key: str
    field: str = ""
    model_value: str = ""
    docs_value: str = ""
    model_source: str = ""
    docs_source: str = ""
    note: str = ""


def _index(table, side, ignore_hyphen, issues):
    """以正規化後的編號建索引；重複的編號回報後只保留第一筆比對。"""
    index = {}
    for record in table.records:
        norm = normalize_key(record.key, ignore_hyphen)
        if norm in index:
            first = index[norm]
            issues.append(Issue(
                kind=DUPLICATE,
                key=record.key,
                model_source=f"{first.source}、{record.source}" if side == "model" else "",
                docs_source=f"{first.source}、{record.source}" if side == "docs" else "",
                note=f"{'模型' if side == 'model' else '文件'}內重複，只用第一筆比對",
            ))
            continue
        index[norm] = record
    return index


def _compare_field(spec, model_record, docs_record):
    model_raw = model_record.values.get(spec["model"], "")
    docs_raw = docs_record.values.get(spec["docs"], "")
    base = dict(
        key=model_record.key,
        field=spec["name"],
        model_value=str(model_raw),
        docs_value=str(docs_raw),
        model_source=model_record.source,
        docs_source=docs_record.source,
    )

    if spec.get("type") == "number":
        model_num, docs_num = parse_number(model_raw), parse_number(docs_raw)
        if model_num is None and docs_num is None:
            return None
        if model_num is None or docs_num is None:
            return Issue(kind=UNPARSABLE, note="其中一邊取不到數字", **base)
        tolerance = float(spec.get("tolerance", 0))
        diff = abs(model_num - docs_num)
        if diff > tolerance:
            return Issue(kind=MISMATCH, note=f"差 {diff:g}（容許 {tolerance:g}）", **base)
        return None

    if normalize_text(model_raw) != normalize_text(docs_raw):
        return Issue(kind=MISMATCH, **base)
    return None


def _check_columns(table, columns, label):
    missing = [name for name in columns if name not in table.headers]
    if missing:
        raise ValueError(f"{label}（{table.path}）找不到欄位：{missing}；現有欄位：{[h for h in table.headers if h]}")


def compare(model_table, docs_table, config):
    fields = config.get("fields", [])
    ignore_hyphen = config.get("ignore_hyphen", False)
    _check_columns(model_table, [f["model"] for f in fields], "模型")
    _check_columns(docs_table, [f["docs"] for f in fields], "文件")

    issues = []
    model_index = _index(model_table, "model", ignore_hyphen, issues)
    docs_index = _index(docs_table, "docs", ignore_hyphen, issues)

    for norm, model_record in model_index.items():
        docs_record = docs_index.get(norm)
        if docs_record is None:
            issues.append(Issue(kind=MISSING_IN_DOCS, key=model_record.key, model_source=model_record.source))
            continue
        for spec in fields:
            issue = _compare_field(spec, model_record, docs_record)
            if issue:
                issues.append(issue)

    for norm, docs_record in docs_index.items():
        if norm not in model_index:
            issues.append(Issue(kind=MISSING_IN_MODEL, key=docs_record.key, docs_source=docs_record.source))

    issues.sort(key=lambda i: (ISSUE_ORDER.index(i.kind), normalize_key(i.key)))
    matched = len(model_index.keys() & docs_index.keys())
    return issues, matched
