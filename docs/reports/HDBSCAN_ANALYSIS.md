# HDBSCAN vs DBSCAN 对比分析

**Date:** 2026-02-25
**Context:** 考虑是否在 spatial_clusters 表中添加 HDBSCAN 聚类结果

---

## 算法对比

### DBSCAN (Density-Based Spatial Clustering of Applications with Noise)

**核心参数:**
- `eps`: 邻域半径（固定值）
- `min_samples`: 最小样本数

**优点:**
- ✅ 简单直观，参数含义明确
- ✅ 可以发现任意形状的聚类
- ✅ 能识别噪声点
- ✅ 不需要预设聚类数量
- ✅ 计算速度快 (O(n log n) with BallTree)

**缺点:**
- ❌ 需要手动调整 eps 参数
- ❌ 对不同密度的聚类效果不佳
- ❌ eps 参数对结果影响很大

**当前实现:**
- spatial_eps_05 (eps=0.5km): 超密集核心
- spatial_eps_10 (eps=1.0km): 标准密度
- spatial_eps_20 (eps=2.0km): 全域覆盖

---

### HDBSCAN (Hierarchical DBSCAN)

**核心参数:**
- `min_cluster_size`: 最小聚类大小
- `min_samples`: 最小样本数（可选）
- `cluster_selection_epsilon`: 聚类选择阈值（可选）

**优点:**
- ✅ **自动选择 eps 参数** - 不需要手动调优
- ✅ **处理不同密度的聚类** - 可以同时发现密集和稀疏的聚类
- ✅ **层次化结构** - 提供聚类树状图
- ✅ **更鲁棒** - 对参数变化不敏感
- ✅ **提供聚类概率** - 每个点属于聚类的置信度

**缺点:**
- ❌ 计算复杂度更高 (O(n² log n) 最坏情况)
- ❌ 内存占用更大
- ❌ 需要额外安装 hdbscan 库
- ❌ 结果解释相对复杂

---

## 对广东村庄数据的适用性分析

### 数据特征

**广东省村庄分布特点:**
1. **密度差异大**: 珠三角极密集，粤北粤西稀疏
2. **多尺度聚集**: 城市核心区、城乡结合部、农村地区密度不同
3. **数据规模**: 285,080 个村庄

### DBSCAN 的表现

**当前 DBSCAN 结果:**

| Run ID | eps | 聚类数 | 覆盖率 | 平均距离 | 评价 |
|--------|-----|--------|--------|----------|------|
| spatial_eps_05 | 0.5km | 12,791 | 58.8% | 0.40km | ✅ 捕获超密集区域 |
| spatial_eps_10 | 1.0km | 4,852 | 92.0% | 1.09km | ✅ 标准密度，推荐 |
| spatial_eps_20 | 2.0km | 253 | 99.3% | 2.43km | ✅ 全域覆盖 |

**问题:**
- 需要运行 3 次才能覆盖不同密度区域
- 每个 run_id 只能捕获特定密度的聚类
- 用户需要选择使用哪个 eps 参数

### HDBSCAN 的潜在优势

**理论优势:**
1. **一次运行覆盖所有密度**
   - 不需要 eps_05, eps_10, eps_20 三个版本
   - 自动识别珠三角密集区和粤北稀疏区

2. **更准确的聚类边界**
   - 在密度变化的区域（如城乡结合部）表现更好
   - 减少"边界村庄"的误分类

3. **提供聚类置信度**
   - 可以标识"核心村庄"和"边缘村庄"
   - 有助于后续分析

**实际考虑:**
1. **计算成本**
   - 285K 村庄，HDBSCAN 可能需要 10-30 分钟
   - 内存占用可能达到 4-8GB
   - 对于离线处理，这是可接受的

2. **结果可解释性**
   - DBSCAN: "eps=1km 内的村庄聚在一起"（直观）
   - HDBSCAN: "基于密度层次结构自动分组"（复杂）

---

## 建议：是否添加 HDBSCAN？

### 方案 A: 不添加 HDBSCAN（推荐）

**理由:**

1. **当前 DBSCAN 已经足够好**
   - 3 个 eps 参数已经覆盖了所有使用场景
   - 覆盖率从 58.8% 到 99.3%，满足不同分析需求
   - 结果直观易懂

2. **避免选择困难**
   - 用户已经需要在 3 个 DBSCAN 结果中选择
   - 再添加 HDBSCAN 会增加 4 种选择
   - 前端需要解释"什么时候用 HDBSCAN vs DBSCAN"

3. **维护成本**
   - 需要安装新依赖 (hdbscan)
   - 需要更新文档和 API
   - 需要解释 HDBSCAN 的参数和结果

4. **性能考虑**
   - HDBSCAN 运行时间更长
   - 如果需要重新生成，成本更高

**结论:** 当前 DBSCAN 三层体系已经很完善，不需要 HDBSCAN。

---

### 方案 B: 添加 HDBSCAN（实验性）

**适用场景:**

如果有以下需求，可以考虑添加：

1. **研究需求**
   - 需要发表论文，对比不同聚类算法
   - 需要分析"密度变化区域"的村庄分布

2. **自动化需求**
   - 希望减少手动调参（不需要选择 eps）
   - 希望一次运行得到所有密度的聚类

3. **高级分析需求**
   - 需要聚类置信度信息
   - 需要层次化的聚类结构

**实现方案:**

```python
import hdbscan

# HDBSCAN 聚类
clusterer = hdbscan.HDBSCAN(
    min_cluster_size=5,      # 最小聚类大小
    min_samples=5,           # 最小样本数
    metric='haversine',      # 使用球面距离
    cluster_selection_epsilon=0.0,  # 不设置 eps 阈值
    cluster_selection_method='eom'  # Excess of Mass
)

labels = clusterer.fit_predict(coords_rad)
probabilities = clusterer.probabilities_  # 聚类概率
```

**存储方案:**

在 `spatial_clusters` 表中添加新的 run_id:
- `spatial_hdbscan_v1`: HDBSCAN 聚类结果

可选：扩展表结构添加 `cluster_probability` 字段

**预期结果:**
- 聚类数: 1,000 - 5,000（自动确定）
- 覆盖率: 85% - 95%
- 噪声点: 5% - 15%

---

## 最终建议

### 推荐：方案 A（不添加 HDBSCAN）

**原因:**
1. ✅ 当前 DBSCAN 三层体系已经很完善
2. ✅ 覆盖了所有使用场景（超密集、标准、全域）
3. ✅ 结果直观易懂，易于向用户解释
4. ✅ 维护成本低
5. ✅ 没有明确的业务需求需要 HDBSCAN

**如果未来有需求:**
- 可以作为实验性功能添加
- 作为独立的 run_id 存储
- 不影响现有的 DBSCAN 结果

---

## 替代方案：优化现有 DBSCAN

如果觉得当前 3 个 eps 参数还不够，可以考虑：

### 方案 C: 添加更多 eps 参数（不推荐）

例如：
- spatial_eps_03 (0.3km): 极密集核心
- spatial_eps_15 (1.5km): 中等覆盖

**问题:** 会导致选择困难，不建议

### 方案 D: 提供 eps 参数推荐工具（可选）

创建一个工具，根据用户的分析目标推荐 eps 参数：

```python
def recommend_eps(analysis_goal):
    if analysis_goal == "urban_core":
        return "spatial_eps_05"  # 城市核心区
    elif analysis_goal == "general":
        return "spatial_eps_10"  # 一般分析
    elif analysis_goal == "full_coverage":
        return "spatial_eps_20"  # 全域覆盖
```

这样可以简化用户的选择过程。

---

## 总结

**建议：不添加 HDBSCAN**

当前的 DBSCAN 三层体系（eps_05, eps_10, eps_20）已经：
- ✅ 覆盖了所有密度范围
- ✅ 满足了所有分析需求
- ✅ 结果直观易懂
- ✅ 维护成本低

除非有明确的研究或业务需求，否则不建议添加 HDBSCAN。

**如果一定要添加:**
- 作为实验性功能
- 独立的 run_id (spatial_hdbscan_v1)
- 不替代现有 DBSCAN 结果
- 需要充分测试和文档说明

---

**Decision:** ❌ 不添加 HDBSCAN
**Reason:** 当前方案已经足够好，没有明确需求
**Alternative:** 如果未来有需求，可以随时添加
