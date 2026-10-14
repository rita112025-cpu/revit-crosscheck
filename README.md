# revit-crosscheck

比對 **Revit 明細表** 與 **設備表／IO List**，列出對不上的編號與欄位，每筆差異都附上兩邊的出處（檔名＋列號）。

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

1. 安裝（只需要 openpyxl）

   ```bash
   pip install openpyxl
   ```

2. 用範例資料試跑

   ```bash
   python -m revit_crosscheck --model examples/model_schedule.txt --docs examples/equipment_list.csv --config examples/mapping.json
   ```

3. 打開 `crosscheck-report/crosscheck.html` 看報告；`crosscheck.csv` 可以直接用 Excel 篩選。

## 用在自己的專案

1. **Revit 匯出明細表**：開啟明細表 →「檔案」→「匯出」→「報告」→「明細表」，存成 `.txt`。
   標題列、群組標題、空白列都不用刪，程式會自己找欄位標題。
2. **準備文件**：`.xlsx`、`.csv`、`.txt` 都可以。Excel 有多張工作表時，在設定檔指定 `sheet`。
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

## 資料安全

全部在本機執行，不連網、不上傳。請不要把業主的設備表或模型匯出檔 commit 進 repo（`.gitignore` 已排除報告資料夾）。

## 下一步規劃

- [ ] 從規範書 PDF 擷取表格當作比對來源
- [ ] pyRevit 按鈕：在 Revit 裡一鍵匯出加比對
- [ ] 一次比對多份文件（設備表＋IO List＋規範）
