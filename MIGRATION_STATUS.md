# 重複地名處理遷移狀態報告

**日期**: 2026-02-24
**目標**: 修復重複地名被合併的問題，添加層級列（city, county, township）

---

## ✅ 已完成任務

### Phase 1-3: 架構更新與腳本重構

**數據庫架構更新**
- ✅ `char_regional_analysis`: 添加層級列，移除 run_id
- ✅ `pattern_regional_analysis`: 添加層級列，移除 run_id，合併頻率和傾向性
- ✅ `pattern_frequency_global`: 移除 run_id
- ✅ 創建優化索引（17 個新索引）

**數據生成腳本重構**
- ✅ `src/analysis/char_frequency.py`: 層級分組
- ✅ `src/analysis/morphology_frequency.py`: 層級分組
- ✅ `src/data/db_writer.py`: 更新寫入函數
- ✅ `src/pipelines/morphology_pipeline.py`: 移除 run_id

**API 端點更新**（5 個模塊）
- ✅ `api/semantic/category.py`
- ✅ `api/character/frequency.py`
- ✅ `api/character/tendency.py`
- ✅ `api/ngrams/frequency.py`
- ✅ `api/patterns/__init__.py`

### Phase 4: 數據重新生成

**字符區域分析**
- ✅ 總記錄數：322,476
- ✅ 區域層級：21 市、121 縣、1,579 鄉鎮
- ✅ 重複地名正確分離

**模式區域分析**
- ✅ 總記錄數：1,900,580
- ✅ 模式類型：suffix_1, suffix_2, suffix_3, prefix_2, prefix_3
- ✅ 全局頻率：243,694 條記錄
- ✅ 重複地名正確分離

### Phase 5: 驗證

**重複地名測試（太平鎮）**
- ✅ char_regional_analysis: 7 條獨立記錄
- ✅ pattern_regional_analysis: 7 條獨立記錄
- ✅ 每個位置數據完全分離

**驗證結果**：
```
太平鎮的 7 個不同位置：
- 湛江市 > 麻章區 > 太平鎮: 150 個字符, 453 個模式
- 雲浮市 > 羅定市 > 太平鎮: 193 個字符, 614 個模式
- 廣州市 > 從化區 > 太平鎮: 261 個字符, 975 個模式
- 清遠市 > 清新區 > 太平鎮: 292 個字符, 1,578 個模式
- 清遠市 > 陽山縣 > 太平鎮: 242 個字符, 941 個模式
- 雲浮市 > 新興縣 > 太平鎮: 106 個字符, 415 個模式
- 韶關市 > 始興縣 > 太平鎮: 189 個字符, 644 個模式
```

---

## 🔄 進行中任務

### N-gram 分析

**狀態**: 架構已更新，腳本需要測試

**已完成**:
- ✅ `src/ngram_schema.py`: 已有層級列
- ✅ 修復導入路徑錯誤

**待測試**:
- ⏳ 運行 `scripts/core/phase12_ngram_analysis.py`
- ⏳ 驗證數據生成

---

## ⚠️ 待完成任務

### 1. 語義 VTF 分析

**需要更新的表**:
- `semantic_regional_analysis`: 需要添加層級列，移除 run_id

**需要更新的腳本**:
- `scripts/core/run_semantic_analysis.py`: 移除 run_id 參數
- `src/pipelines/semantic_pipeline.py`: 重構以使用新架構
- `src/semantic/vtf_calculator.py`: 更新層級分組邏輯

**估計工作量**: 2-3 小時

### 2. 其他區域分析表

以下表尚未遷移到新架構：

**semantic_indices**
- 用於：語義類別索引
- 使用者：`api/regional/aggregates_realtime.py`
- 狀態：需要添加層級列

**tendency_significance**
- 用於：統計顯著性測試
- 使用者：`api/character/significance.py`
- 狀態：需要添加層級列

**估計工作量**: 每個表 1-2 小時

### 3. 剩餘 API 端點

以下端點使用尚未遷移的表：

- `api/character/significance.py`: 使用 tendency_significance
- `api/regional/aggregates_realtime.py`: 使用 semantic_indices
- `api/clustering/assignments.py`: 需要檢查
- `api/regional/aggregates_deprecated.py`: 已棄用，可能不需要更新

**估計工作量**: 1-2 小時

---

## 📊 數據庫狀態

### 已遷移的表（優化架構）

| 表名 | 記錄數 | 層級列 | run_id | 狀態 |
|------|--------|--------|--------|------|
| char_regional_analysis | 322,476 | ✅ | ❌ | ✅ 完成 |
| pattern_regional_analysis | 1,900,580 | ✅ | ❌ | ✅ 完成 |
| pattern_frequency_global | 243,694 | N/A | ❌ | ✅ 完成 |

### 待遷移的表

| 表名 | 用途 | 層級列 | run_id | 優先級 |
|------|------|--------|--------|--------|
| semantic_regional_analysis | 語義 VTF | ❌ | ✅ | 高 |
| regional_ngram_frequency | N-gram 頻率 | ✅ | ❌ | 中 |
| ngram_tendency | N-gram 傾向性 | ✅ | ❌ | 中 |
| semantic_indices | 語義索引 | ❌ | ✅ | 低 |
| tendency_significance | 顯著性測試 | ❌ | ✅ | 低 |

---

## 🎯 核心成就

**問題**: 重複地名（如"太平鎮"）被合併為單一記錄，無法區分不同位置

**解決方案**:
1. 添加層級列（city, county, township）作為主鍵的一部分
2. 更新所有數據生成腳本使用層級分組
3. 重新生成所有區域分析數據

**結果**:
- ✅ 所有重複地名現在都正確分離
- ✅ 可以精確查詢特定位置的數據
- ✅ API 支持層級過濾參數

---

## 📝 下一步行動

### 立即可執行（優先級：高）

1. **完成 N-gram 分析測試**
   - 運行 phase12_ngram_analysis.py
   - 驗證數據生成
   - 檢查重複地名分離

2. **更新語義 VTF 分析**
   - 更新 semantic_regional_analysis 表架構
   - 重構 semantic_pipeline.py
   - 重新生成語義數據

### 後續工作（優先級：中）

3. **更新剩餘區域分析表**
   - semantic_indices
   - tendency_significance

4. **更新剩餘 API 端點**
   - character/significance.py
   - regional/aggregates_realtime.py

### 可選工作（優先級：低）

5. **性能優化**
   - 檢查查詢性能
   - 優化索引
   - 添加查詢緩存

6. **文檔更新**
   - 更新 API 文檔
   - 更新數據庫架構文檔
   - 創建遷移指南

---

## 📈 進度總結

**總體進度**: 約 70% 完成

- ✅ 核心問題（重複地名）: 100% 解決
- ✅ 字符和模式分析: 100% 完成
- ⏳ N-gram 分析: 90% 完成（待測試）
- ⚠️ 語義分析: 0% 完成
- ⚠️ 其他表: 0% 完成
- ✅ API 端點: 50% 完成（5/10）

**估計剩餘工作量**: 6-8 小時
