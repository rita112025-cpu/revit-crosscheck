"""命令列入口。

離開碼：0 = 沒有差異，1 = 有差異，2 = 設定或檔案錯誤。
有差異回 1，方便之後接到批次檔或 CI 自動擋下。
"""

import argparse
import json
import sys
from pathlib import Path

from .compare import compare
from .readers import ReadError, read_table
from .report import summary_counts, write_csv, write_html


def build_parser():
    parser = argparse.ArgumentParser(
        prog="revit-crosscheck",
        description="比對 Revit 明細表與設備表／IO List，列出對不上的編號與欄位。",
    )
    parser.add_argument("--model", required=True, help="Revit 匯出的明細表（.txt / .csv / .xlsx）")
    parser.add_argument("--docs", required=True, help="要對照的文件表格（.xlsx / .csv / .txt / .pdf）")
    parser.add_argument("--config", required=True, help="欄位對應設定 JSON")
    parser.add_argument("--out", default="crosscheck-report", help="報告輸出資料夾（預設 crosscheck-report）")
    return parser


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    for side in ("model", "docs"):
        if "key" not in config.get(side, {}):
            raise ValueError(f"設定檔缺少 {side}.key（編號欄位名稱）")
    for spec in config.get("fields", []):
        for required in ("name", "model", "docs"):
            if required not in spec:
                raise ValueError(f"fields 內每一項都要有 {required}：{spec}")
    return config


def _read_side(path, side):
    return read_table(
        path,
        side["key"],
        sheet=side.get("sheet"),
        pages=side.get("pages"),
        table_settings=side.get("pdf_table_settings"),
    )


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        model = _read_side(args.model, config["model"])
        docs = _read_side(args.docs, config["docs"])
        issues, matched = compare(model, docs, config)
    except (ReadError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "crosscheck.csv"
    html_path = out_dir / "crosscheck.html"
    write_csv(issues, csv_path)
    write_html(issues, html_path, args.model, args.docs, matched)

    print(f"模型 {len(model.records)} 筆、文件 {len(docs.records)} 筆，兩邊都有 {matched} 筆")
    if issues:
        for kind, count in summary_counts(issues):
            print(f"  {kind}：{count}")
    else:
        print("  沒有差異")
    print(f"報告：{html_path}")
    print(f"      {csv_path}")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
