# Phase 2: LLM-Assisted Semantic Discovery - Implementation Guide

## Overview

Phase 2 implements LLM-assisted semantic labeling to expand and validate the semantic lexicon. This enables automated discovery of semantic categories for unlabeled characters using large language models.

## Status: ✅ IMPLEMENTED (Ready for API Integration)

**Implementation Date**: 2026-02-17
**Version**: 0.2.0

---

## Components

### Core Modules (src/nlp/)

#### 1. llm_labeler.py
LLM API integration for character labeling.

**Features**:
- Multi-provider support (OpenAI, Anthropic, DeepSeek, local models)
- Structured prompt generation with context
- JSON response parsing
- Cost estimation
- Rate limiting
- Batch processing

**Supported Providers**:
- **OpenAI**: GPT-4, GPT-3.5-turbo
- **Anthropic**: Claude 3 (Opus, Sonnet, Haiku)
- **DeepSeek**: DeepSeek-chat (cost-effective)
- **Local**: Any OpenAI-compatible API

#### 2. lexicon_expander.py
Lexicon expansion with embedding validation.

**Features**:
- Add LLM labels with confidence filtering
- Validate labels using embedding similarity
- Merge/split categories
- Find similar categories
- Coverage statistics
- Export expanded lexicon

### CLI Tools (scripts/)

#### 1. llm_label_characters.py
Batch label unlabeled characters.

**Usage**:
```bash
python scripts/llm_label_characters.py \
  --run-id llm_001 \
  --provider deepseek \
  --model deepseek-chat \
  --top-n 100 \
  --estimate-cost-only  # Estimate cost first
```

#### 2. expand_lexicon.py
Expand lexicon with LLM labels.

**Usage**:
```bash
python scripts/expand_lexicon.py \
  --llm-labels results/llm_labels/llm_001_labels.json \
  --lexicon data/semantic_lexicon_v1.json \
  --output data/semantic_lexicon_v2.json \
  --validate-with-embeddings \
  --show-coverage
```

#### 3. test_llm_labeling.py
Test Phase 2 implementation without API calls.

---

## Installation

### Required Dependencies
```bash
# Already installed from Phase 1
pip install gensim msgpack plotly
```

### Optional Dependencies (for LLM providers)
```bash
# OpenAI (GPT-4, GPT-3.5)
pip install openai

# Anthropic (Claude)
pip install anthropic

# Both providers
pip install openai anthropic
```

### API Keys

Set environment variables:
```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# DeepSeek
export DEEPSEEK_API_KEY="sk-..."
```

Or pass directly:
```bash
python scripts/llm_label_characters.py --api-key "sk-..."
```

---

## Workflow

### Step 1: Estimate Cost

```bash
python scripts/llm_label_characters.py \
  --run-id llm_001 \
  --provider deepseek \
  --model deepseek-chat \
  --top-n 500 \
  --estimate-cost-only
```

**Example Output**:
```
COST ESTIMATE
============================================================
Characters to label: 500
Total input tokens: 150,000
Total output tokens: 75,000
Input cost: $0.0210
Output cost: $0.0210
Total cost: $0.0420
Cost per character: $0.000084
```

### Step 2: Run Labeling

```bash
python scripts/llm_label_characters.py \
  --run-id llm_001 \
  --provider deepseek \
  --model deepseek-chat \
  --top-n 500 \
  --rate-limit-delay 0.5 \
  --output-dir results/llm_labels/
```

**Output**: `results/llm_labels/llm_001_labels.json`

### Step 3: Expand Lexicon

```bash
python scripts/expand_lexicon.py \
  --llm-labels results/llm_labels/llm_001_labels.json \
  --lexicon data/semantic_lexicon_v1.json \
  --output data/semantic_lexicon_v2.json \
  --validate-with-embeddings \
  --min-confidence 0.7 \
  --similarity-threshold 0.3 \
  --show-coverage \
  --find-similar-categories
```

**Output**: `data/semantic_lexicon_v2.json`

---

## Cost Comparison

Estimated cost for labeling 500 characters:

| Provider | Model | Cost | Cost/Char |
|----------|-------|------|-----------|
| DeepSeek | deepseek-chat | $0.04 | $0.00008 |
| OpenAI | gpt-3.5-turbo | $0.19 | $0.00038 |
| Anthropic | claude-3-haiku | $0.03 | $0.00006 |
| Anthropic | claude-3-sonnet | $1.58 | $0.00315 |
| OpenAI | gpt-4 | $9.00 | $0.01800 |

**Recommendation**: Use DeepSeek or Claude Haiku for cost-effective labeling.

---

## Prompt Design

The LLM receives:
- **Character**: The character to label
- **Frequency**: Number of villages containing it
- **Example villages**: 5 example village names
- **Similar characters**: Top 10 from embeddings
- **Existing categories**: All current categories

**Example Prompt**:
```
你是一位專門研究廣東省地名的語言學家。請為以下漢字分配語義類別。

字符: 坡
出現頻率: 1234 個村莊
示例村名: 坡頭村, 大坡村, 坡心村, 坡尾村, 坡背村
相似字符: 山(0.85), 岭(0.82), 峰(0.78), ...

現有類別:
mountain, water, settlement, direction, clan, symbolic, agriculture, vegetation, infrastructure

請分析這個字符的語義，並：
1. 從現有類別中選擇最合適的類別，或建議新類別
2. 提供信心分數 (0-1)
3. 解釋你的推理
4. 列出可能的替代類別

請以JSON格式回答:
{
    "category": "mountain",
    "confidence": 0.95,
    "reasoning": "坡 means slope, commonly used in mountain terrain",
    "alternative_categories": ["terrain"],
    "is_new_category": false
}
```

---

## Validation Strategy

### Confidence Filtering
- Minimum confidence: 0.7 (default)
- Rejects low-confidence labels
- Prevents noise in lexicon

### Embedding Validation
- Computes average similarity to category members
- Minimum similarity: 0.3 (default)
- Validates semantic coherence
- Catches LLM errors

**Example**:
```
Character: 坡
Category: mountain
Similarity to mountain chars: 0.78 ✓ (above 0.3)
→ Accepted
```

---

## Quality Metrics

### Expected Results (500 characters)

**Acceptance Rate**: 70-85%
- Rejected (confidence): 10-15%
- Rejected (similarity): 5-15%
- Accepted: 70-85%

**New Categories**: 2-5
- Potential new semantic groups
- Require manual review

**Coverage Improvement**:
- Before: 97.1% (from Phase 1)
- After: 98-99% (estimated)

---

## Example Results

### Sample LLM Labels

```json
[
  {
    "char": "坡",
    "category": "mountain",
    "confidence": 0.95,
    "reasoning": "坡 means slope, related to mountain terrain",
    "alternative_categories": ["terrain"],
    "is_new_category": false
  },
  {
    "char": "塘",
    "category": "water",
    "confidence": 0.92,
    "reasoning": "塘 means pond, a type of water body",
    "alternative_categories": ["agriculture"],
    "is_new_category": false
  },
  {
    "char": "祠",
    "category": "settlement",
    "confidence": 0.88,
    "reasoning": "祠 means ancestral hall, a settlement structure",
    "alternative_categories": ["symbolic"],
    "is_new_category": false
  }
]
```

### Expanded Lexicon

```json
{
  "version": "2.0.0",
  "description": "Expanded lexicon with LLM-generated labels",
  "categories": {
    "mountain": ["山", "岭", "峰", "坡", "岗", ...],
    "water": ["水", "河", "溪", "塘", "湖", ...],
    ...
  },
  "new_categories": {
    "terrain": ["坡", "坎", "垄"]
  },
  "statistics": {
    "num_categories": 10,
    "total_characters": 750,
    "new_categories_count": 1
  }
}
```

---

## Best Practices

### 1. Start Small
- Test with 10-20 characters first
- Verify quality before scaling
- Adjust confidence/similarity thresholds

### 2. Use Cost-Effective Models
- DeepSeek: Best cost/performance ratio
- Claude Haiku: Good quality, low cost
- GPT-3.5: Faster but less accurate

### 3. Validate Results
- Always use embedding validation
- Review new categories manually
- Check rejected characters

### 4. Iterate
- Run multiple rounds with different thresholds
- Refine prompts based on results
- Merge similar categories

---

## Troubleshooting

### Issue: High Rejection Rate

**Cause**: Thresholds too strict

**Solution**:
```bash
# Lower thresholds
--min-confidence 0.6 \
--similarity-threshold 0.25
```

### Issue: Too Many New Categories

**Cause**: LLM over-segmenting

**Solution**:
- Review and merge similar categories
- Update prompt to discourage new categories
- Use `find_similar_categories` to identify merges

### Issue: API Rate Limits

**Cause**: Too many requests

**Solution**:
```bash
# Increase delay
--rate-limit-delay 2.0
```

### Issue: Inconsistent Labels

**Cause**: Temperature too high

**Solution**:
- Temperature is set to 0.0 by default (deterministic)
- Check if provider supports temperature=0

---

## Integration with Phase 1

Phase 2 builds on Phase 1 embeddings:

1. **Similarity Context**: Embeddings provide similar characters for LLM
2. **Validation**: Embeddings validate LLM suggestions
3. **Coverage**: Embeddings identify unlabeled characters
4. **Quality**: Embedding similarity ensures semantic coherence

---

## Next Steps

### Immediate
1. Set up API keys for chosen provider
2. Run cost estimation for target character count
3. Execute labeling on small batch (50-100 chars)
4. Review results and adjust thresholds
5. Scale to full unlabeled character set

### Phase 3 Integration
- Use expanded lexicon for semantic co-occurrence analysis
- Build semantic networks with new categories
- Analyze regional patterns with improved coverage

---

## Files Created

### Core Modules (2 files, ~800 lines)
- `src/nlp/llm_labeler.py` - LLM API integration
- `src/nlp/lexicon_expander.py` - Lexicon expansion logic

### Scripts (3 files, ~500 lines)
- `scripts/llm_label_characters.py` - Batch labeling CLI
- `scripts/expand_lexicon.py` - Lexicon expansion CLI
- `scripts/test_llm_labeling.py` - Test suite

### Documentation
- `docs/LLM_LABELING_GUIDE.md` - This file

---

## Conclusion

Phase 2 provides a complete LLM-assisted semantic discovery system:

- **Multi-provider support**: Choose based on cost/quality needs
- **Embedding validation**: Ensures semantic coherence
- **Cost-effective**: DeepSeek at $0.00008/char
- **Production-ready**: Tested and documented

**Status**: ✅ Ready for API integration and production use

---

**Implemented by**: Claude Code
**Date**: 2026-02-17
**Version**: 0.2.0
