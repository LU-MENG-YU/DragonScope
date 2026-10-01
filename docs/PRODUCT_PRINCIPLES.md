# Product principles — v0.2

1. **Public-first**：任何人打開網站，都只看到公開資訊。
2. **Private-by-presence**：只有本地資料真的被匯入，狀態總覽才出現。
3. **No fake private inference**：不從公開資料猜測體重、體脂、傷勢、內部 workload、營養或其他非公開狀態。
4. **Calendar is the temporal spine**：賽程、比分、陣容、異動、新聞與本地測量共用時間座標。
5. **Big picture before case**：預設路徑是球隊 → 軍別 → 位置 → 個人，不以「先選球員」作為入口。
6. **Overview, not analysis**：本地層只提供 latest / delta / public context；不做推論統計、模型或 SHAP。
7. **Metric-agnostic**：不把系統寫死成 EV / FF / InBody；任意可解析數值欄位都能成為狀態 metric。
8. **Source provenance**：公開事件保留來源、原始 URL、時間與來源健康狀態。
9. **Last-known-good**：外部來源失敗時保留最後成功快取。
10. **Adapter isolation**：每個外部來源獨立，網站 UI 不依賴來源私有格式。
11. **Low maintenance**：純靜態網站、IndexedDB、無帳號、無後端、無 OAuth 優先。
12. **No causal theater**：時間上的相鄰只呈現為脈絡，不自動宣稱「因為連續出賽所以體重下降」。
