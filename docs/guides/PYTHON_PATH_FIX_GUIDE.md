# Python 路径问题修复

## 问题描述

运行 `train_char_embeddings.py` 时出现错误：
```
ModuleNotFoundError: No module named 'src'
```

## 根本原因

脚本中的 Python 路径设置不正确：

```python
# 错误的设置
sys.path.insert(0, str(Path(__file__).parent.parent))
```

对于位于 `scripts/core/` 的脚本：
- `Path(__file__).parent` = `scripts/core/`
- `Path(__file__).parent.parent` = `scripts/` ❌ (错误！)
- `Path(__file__).parent.parent.parent` = 项目根目录 ✓ (正确！)

## 修复内容

修复了以下3个脚本的路径设置：

### 1. `scripts/core/train_char_embeddings.py`
```python
# 修复前
sys.path.insert(0, str(Path(__file__).parent.parent))

# 修复后
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

### 2. `scripts/core/run_morphology_analysis.py`
```python
# 修复前
sys.path.insert(0, str(Path(__file__).parent.parent))

# 修复后
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

### 3. `scripts/core/run_semantic_analysis.py`
```python
# 修复前
sys.path.insert(0, str(Path(__file__).parent.parent))

# 修复后
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

## 验证

修复后，导入测试成功：
```bash
$ python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('scripts/core/train_char_embeddings.py').parent.parent.parent)); from src.nlp import CharacterEmbeddingTrainer, EmbeddingStorage; print('Import successful')"

WARNING:root:UMAP not available. Install with: pip install umap-learn
Import successful
```

## 其他脚本

检查发现以下脚本已经使用了正确的路径设置（`.parent.parent.parent`）：
- ✓ `scripts/core/compute_significance_only.py`
- ✓ `scripts/core/populate_village_ngrams.py`
- ✓ `scripts/core/run_frequency_analysis.py`
- ✓ `scripts/core/run_tendency_with_significance.py`

## 注意事项

**UMAP 警告**：
```
WARNING:root:UMAP not available. Install with: pip install umap-learn
```

这是一个可选依赖的警告，不影响核心功能。如果需要使用 UMAP 降维功能，可以安装：
```bash
pip install umap-learn
```

## 现在可以运行

修复后，可以正常运行训练脚本：
```bash
python scripts/core/train_char_embeddings.py \
    --run-id run_01_20260305 \
    --db-path data/villages.db \
    --vector-size 100 \
    --window 3 \
    --min-count 2 \
    --epochs 15 \
    --model-type skipgram \
    --precompute-similarities \
    --top-k 50
```
