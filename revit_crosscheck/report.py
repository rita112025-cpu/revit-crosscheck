"""輸出差異報告：CSV（給 Excel 篩選）與 HTML（給開會投影）。"""

import csv
import html
from collections import Counter
from datetime import datetime
from pathlib import Path

from .compare import ISSUE_ORDER

CSV_COLUMNS = [
    ("kind", "類型"),
    ("key", "編號"),
    ("field", "欄位"),
    ("model_value", "模型值"),
    ("docs_value", "文件值"),
    ("note", "說明"),
    ("model_source", "模型出處"),
    ("docs_source", "文件出處"),
]

KIND_COLORS = {
    "數值不符": "#c0392b",
    "文件沒有": "#d35400",
    "模型沒有": "#8e44ad",
    "編號重複": "#2c3e50",
    "無法解析數字": "#7f8c8d",
}


def write_csv(issues, path):
    # utf-8-sig 讓 Excel 直接開啟時中文不亂碼
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow([label for _, label in CSV_COLUMNS])
        for issue in issues:
            writer.writerow([getattr(issue, attr) for attr, _ in CSV_COLUMNS])


def summary_counts(issues):
    counts = Counter(issue.kind for issue in issues)
    return [(kind, counts[kind]) for kind in ISSUE_ORDER if counts[kind]]


def write_html(issues, path, model_path, docs_path, matched):
    esc = html.escape
    summary = "".join(
        f'<li><span class="badge" style="background:{KIND_COLORS[kind]}">{esc(kind)}</span> {count}</li>'
        for kind, count in summary_counts(issues)
    ) or "<li>沒有差異</li>"
    rows = "".join(
        "<tr>"
        f'<td><span class="badge" style="background:{KIND_COLORS[i.kind]}">{esc(i.kind)}</span></td>'
        f"<td><b>{esc(i.key)}</b></td><td>{esc(i.field)}</td>"
        f"<td>{esc(i.model_value)}</td><td>{esc(i.docs_value)}</td><td>{esc(i.note)}</td>"
        f'<td class="src">{esc(i.model_source)}</td><td class="src">{esc(i.docs_source)}</td>'
        "</tr>"
        for i in issues
    )
    page = f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revit 交叉比對報告</title>
<style>
:root {{ --bg:#fff; --fg:#1d1d1f; --muted:#666; --line:#e3e3e3; --head:#f5f5f7; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1b1b1d; --fg:#eee; --muted:#aaa; --line:#333; --head:#26262a; }} }}
body {{ margin:0; padding:24px 16px; background:var(--bg); color:var(--fg);
  font-family:"Microsoft JhengHei","Noto Sans TC",system-ui,sans-serif; }}
h1 {{ font-size:22px; margin:0 0 8px; }}
.meta {{ color:var(--muted); font-size:13px; line-height:1.7; }}
ul.summary {{ list-style:none; padding:0; display:flex; flex-wrap:wrap; gap:16px; font-size:16px; }}
.badge {{ color:#fff; border-radius:4px; padding:2px 8px; font-size:13px; white-space:nowrap; }}
.wrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; }}
th, td {{ border-bottom:1px solid var(--line); padding:8px; text-align:left; vertical-align:top; }}
th {{ background:var(--head); position:sticky; top:0; }}
td.src {{ color:var(--muted); font-size:12px; }}
</style></head><body>
<h1>Revit 交叉比對報告</h1>
<div class="meta">
模型：{esc(str(model_path))}<br>文件：{esc(str(docs_path))}<br>
兩邊都有的編號：{matched} 筆 ・ 產生時間：{datetime.now():%Y-%m-%d %H:%M}
</div>
<ul class="summary">{summary}</ul>
<div class="wrap"><table>
<thead><tr><th>類型</th><th>編號</th><th>欄位</th><th>模型值</th><th>文件值</th><th>說明</th><th>模型出處</th><th>文件出處</th></tr></thead>
<tbody>{rows}</tbody></table></div>
</body></html>
"""
    Path(path).write_text(page, encoding="utf-8")
