# revit-crosscheck

比對 **Revit 明細表** 與 **設備表／IO List／規範書 PDF**，列出對不上的編號與欄位，每筆差異都附上兩邊的出處（檔名＋列號）。

開會前不用再逐筆翻 Excel 對模型。

## 它會抓出什麼

| 類型 | 意思 |
|---|---|
| 數值不符 | 兩邊都有這個編號，但欄位值不同（數字可設容許誤差） |
| 文件沒有 | 模型裡有，文件裡找不到 |
| 模型沒有 | 文件裡有，模型裡還沒畫 |
| 編號重複 | 同一邊出現兩次以上 |
| 無法解析數字 | 數字欄位寫成「待確認」之類的文字 |

比對編號時會自動忽略全形／半形、大小寫和多餘空白，所以 `ｓｐ－００５ ` 和 `SP-005` 視為同一個編號。

## 快速開始（約 5 分鐘）

1. 安裝（要讀 PDF 才需要 pdfplumber）

   ```bash
   pip install openpyxl pdfplumber
   ```

2. 用範例資料試跑

   ```bash
   python -m revit_crosscheck --model examples/model_schedule.txt --docs examples/equipment_list.csv --config examples/mapping.json
   ```

3. 打開 `crosscheck-report/crosscheck.html` 看報告；`crosscheck.csv` 可以直接用 Excel 篩選。

## 用在自己的專案

1. **Revit 匯出明細表**：開啟明細表 →「檔案」→「匯出」→「報告」→「明細表」，存成 `.txt`。
   標題列、群組標題、空白列都不用刪，程式會自己找欄位標題。
2. **準備文件**：`.xlsx`、`.csv`、`.txt`、`.pdf` 都可以。Excel 有多張工作表時，在設定檔指定 `sheet`；PDF 見下方〈從規範書 PDF 擷取〉。
3. **複製 `examples/mapping.json` 改欄位名稱**：

```json
{
  "model": { "key": "標記" },
  "docs":  { "key": "設備編號", "sheet": "設備表" },
  "ignore_hyphen": false,
  "fields": [
    { "name": "系統",     "model": "系統類型", "docs": "系統",         "type": "text" },
    { "name": "安裝高度", "model": "偏移",     "docs": "安裝高度(mm)", "type": "number", "tolerance": 10 }
  ]
}
```

| 設定 | 說明 |
|---|---|
| `model.key` / `docs.key` | 兩邊「編號」欄位的標題文字 |
| `docs.sheet` | Excel 工作表名稱；`null` 表示第一張 |
| `ignore_hyphen` | `true` 時 `SP-005` 與 `SP005` 視為相同 |
| `fields[].type` | `text`：文字比對；`number`：從「2400 mm」這類字串取數字比對 |
| `fields[].tolerance` | 數字容許誤差，單位跟資料一致 |

## 從規範書 PDF 擷取

```bash
python -m revit_crosscheck --model examples/model_schedule.txt --docs examples/spec_table.pdf --config examples/mapping_pdf.json
```

程式會在 PDF 裡找「含有編號欄位的表格」，其他表格（圖說清單等）自動略過。跨頁的表格會接起來：

- 每頁重複標題列 → 接上
- 續頁沒有標題列 → 只有在「上一頁最後一張是設備表」且「欄數相同」時才接上
- 儲存格內換行：中文接中文直接相連（`天花⏎喇叭` → `天花喇叭`），其他補空白（`2400⏎mm` → `2400 mm`）

出處格式：`spec.pdf:p2:表1:列3` ＝ 第 2 頁、該頁第 1 張表、第 3 列。

PDF 專用設定（放在 `docs` 底下）：

| 設定 | 說明 |
|---|---|
| `pages` | 只讀這些頁，例如 `"12-15,18"`；`null` 表示全部 |
| `pdf_table_settings` | 傳給 pdfplumber 的表格偵測設定。表格沒有框線時試 `{"vertical_strategy": "text", "horizontal_strategy": "text"}` |

限制：

- **掃描檔不支援**，需要先 OCR（程式會提示）。
- 同一份 PDF 只取一種標題的表格；欄位不同的第二張設備表會被略過。
- 合併儲存格、斜線表頭等複雜版面可能讀錯，請先用 `pages` 限縮範圍並對照報告出處抽查。
- 目前只用程式產生的範例 PDF 測試過，還沒有用真實規範書驗證。

## 離開碼

| 碼 | 意思 |
|---|---|
| 0 | 沒有差異 |
| 1 | 有差異（報告已產生） |
| 2 | 設定或檔案錯誤 |

## 支援的編碼

Revit 匯出的 UTF-16、UTF-8（含 BOM）、繁中 Windows 常見的 Big5（cp950）都會自動判斷。

## 測試

```bash
python -m unittest discover -s tests
```

範例 PDF 由 `tests/make_spec_pdf.py` 產生（需要 reportlab 與 Windows 標楷體），平常測試不需要重新產生。

## 資料安全

全部在本機執行，不連網、不上傳。請不要把業主的設備表或模型匯出檔 commit 進 repo（`.gitignore` 已排除報告資料夾）。

## 下一步規劃

- [x] 從規範書 PDF 擷取表格當作比對來源（有文字層的 PDF）
- [ ] pyRevit 按鈕：在 Revit 裡一鍵匯出加比對
- [ ] 一次比對多份文件（設備表＋IO List＋規範）
