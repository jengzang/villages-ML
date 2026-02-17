# 實際運行LLM標記 - 設置指南

## 演示結果總結

剛才的演示成功展示了完整工作流程：
- ✅ 識別了20個未標記字符（最高頻率：新15,229個村莊，大14,231個村莊）
- ✅ 生成了模擬LLM標籤
- ✅ 使用嵌入驗證（18個被拒絕，2個被接受）
- ✅ 擴展了詞典
- ✅ 生成了報告

## 實際運行選項

### 選項A：使用DeepSeek（推薦 - 最便宜）

**成本**: $0.0042 (50字符) | $0.042 (500字符)

#### 步驟1：獲取API密鑰
1. 訪問 https://platform.deepseek.com/
2. 註冊賬號
3. 獲取API密鑰

#### 步驟2：設置環境變量
```bash
# Windows (PowerShell)
$env:DEEPSEEK_API_KEY="sk-..."

# Windows (CMD)
set DEEPSEEK_API_KEY=sk-...

# Linux/Mac
export DEEPSEEK_API_KEY="sk-..."
```

#### 步驟3：運行標記（小測試）
```bash
python scripts/llm_label_characters.py \
  --run-id llm_deepseek_001 \
  --provider deepseek \
  --model deepseek-chat \
  --top-n 50 \
  --rate-limit-delay 0.5
```

#### 步驟4：擴展詞典
```bash
python scripts/expand_lexicon.py \
  --llm-labels results/llm_labels/llm_deepseek_001_labels.json \
  --lexicon data/semantic_lexicon_v1.json \
  --output data/semantic_lexicon_v2.json \
  --validate-with-embeddings \
  --show-coverage
```

---

### 選項B：使用OpenAI GPT-3.5（快速但較貴）

**成本**: $0.0187 (50字符) | $0.1875 (500字符)

#### 步驟1：獲取API密鑰
1. 訪問 https://platform.openai.com/
2. 創建API密鑰

#### 步驟2：設置環境變量
```bash
export OPENAI_API_KEY="sk-..."
```

#### 步驟3：運行標記
```bash
python scripts/llm_label_characters.py \
  --run-id llm_gpt35_001 \
  --provider openai \
  --model gpt-3.5-turbo \
  --top-n 50
```

---

### 選項C：使用Anthropic Claude Haiku（高質量低成本）

**成本**: $0.0131 (50字符) | $0.1313 (500字符)

#### 步驟1：安裝Anthropic包
```bash
pip install anthropic
```

#### 步驟2：獲取API密鑰
1. 訪問 https://console.anthropic.com/
2. 創建API密鑰

#### 步驟3：設置環境變量
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

#### 步驟4：運行標記
```bash
python scripts/llm_label_characters.py \
  --run-id llm_claude_001 \
  --provider anthropic \
  --model claude-3-haiku-20240307 \
  --top-n 50
```

---

## 推薦工作流程

### 階段1：小規模測試（50字符）
```bash
# 1. 估算成本
python scripts/estimate_llm_cost.py

# 2. 運行小測試
python scripts/llm_label_characters.py \
  --run-id llm_test_001 \
  --provider deepseek \
  --top-n 50

# 3. 檢查結果
cat results/llm_labels/llm_test_001_labels.json

# 4. 擴展詞典
python scripts/expand_lexicon.py \
  --llm-labels results/llm_labels/llm_test_001_labels.json \
  --lexicon data/semantic_lexicon_v1.json \
  --output data/semantic_lexicon_v2_test.json \
  --validate-with-embeddings \
  --min-confidence 0.7 \
  --similarity-threshold 0.3
```

### 階段2：中等規模（200字符）
如果測試結果滿意：
```bash
python scripts/llm_label_characters.py \
  --run-id llm_medium_001 \
  --provider deepseek \
  --top-n 200
```

### 階段3：大規模（500-1000字符）
如果質量穩定：
```bash
python scripts/llm_label_characters.py \
  --run-id llm_full_001 \
  --provider deepseek \
  --top-n 1000
```

---

## 質量控制

### 調整閾值

如果接受率太低（<50%）：
```bash
python scripts/expand_lexicon.py \
  --min-confidence 0.6 \
  --similarity-threshold 0.25
```

如果接受率太高（>90%）：
```bash
python scripts/expand_lexicon.py \
  --min-confidence 0.8 \
  --similarity-threshold 0.35
```

### 檢查新類別

```bash
# 查看建議的新類別
python scripts/expand_lexicon.py \
  --find-similar-categories
```

---

## 無API密鑰的替代方案

### 選項1：繼續使用演示模式
```bash
python scripts/demo_llm_labeling.py
```
- 使用基於嵌入的模擬標籤
- 無成本
- 質量較低但可用於測試

### 選項2：手動標記
1. 導出未標記字符列表
2. 手動分配類別
3. 使用expand_lexicon.py導入

### 選項3：使用本地模型
```bash
# 使用Ollama或其他本地LLM
python scripts/llm_label_characters.py \
  --provider local \
  --base-url http://localhost:11434/v1 \
  --model llama2
```

---

## 預期結果

### 小測試（50字符）
- 運行時間：2-5分鐘
- 成本：$0.004-0.02
- 接受率：60-80%
- 新類別：0-2個

### 中等規模（200字符）
- 運行時間：10-20分鐘
- 成本：$0.017-0.075
- 接受率：65-80%
- 新類別：1-3個

### 大規模（1000字符）
- 運行時間：1-2小時
- 成本：$0.084-0.375
- 接受率：70-85%
- 新類別：2-5個
- 覆蓋率提升：97.1% → 98-99%

---

## 故障排除

### 問題：API密鑰錯誤
```
OpenAIError: The api_key client option must be set
```
**解決**：檢查環境變量是否正確設置

### 問題：速率限制
```
RateLimitError: Rate limit exceeded
```
**解決**：增加延遲
```bash
--rate-limit-delay 2.0
```

### 問題：高拒絕率
**原因**：閾值太嚴格
**解決**：降低閾值（見上文"質量控制"）

---

## 下一步

完成LLM標記後：
1. 分析擴展後的詞典
2. 可視化新類別
3. 與Phase 1嵌入集成
4. 進入Phase 3（語義網絡分析）

---

**當前狀態**：
- ✅ Phase 1完成（字符嵌入）
- ✅ Phase 2完成（LLM標記系統）
- ⏳ 等待API密鑰以運行實際標記
- 📋 準備進入Phase 3

**推薦行動**：
1. 如果有API密鑰 → 運行小測試（50字符）
2. 如果沒有API密鑰 → 繼續Phase 3或使用演示模式
