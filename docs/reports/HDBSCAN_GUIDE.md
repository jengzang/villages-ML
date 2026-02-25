# HDBSCAN 空间聚类 - 运行指南

**Date:** 2026-02-25
**Status:** 准备就绪

---

## 快速开始

### 方法 1: 一键运行（推荐）

```bash
python run_hdbscan_all.py
```

这个脚本会自动：
1. 检查并安装 hdbscan 库
2. 删除 optimized_kde_v1 重复数据
3. 运行 HDBSCAN 聚类
4. 将结果写入数据库

---

### 方法 2: 分步运行

#### Step 1: 安装 hdbscan

```bash
pip install hdbscan
```

#### Step 2: 运行聚类

```bash
python scripts/core/run_hdbscan_clustering.py \
    --run-id spatial_hdbscan_v1 \
    --min-cluster-size 10 \
    --min-samples 5 \
    --delete-optimized-kde
```

---

## 参数说明

### HDBSCAN 核心参数

**`--min-cluster-size`** (默认: 10)
- 最小聚类大小
- 小于此值的聚类会被标记为噪声
- **推荐值**: 10（适合村庄数据）
- 调整建议:
  - 增大 → 更少、更大的聚类，更多噪声点
  - 减小 → 更多、更小的聚类，更少噪声点

**`--min-samples`** (默认: 5)
- 核心点的最小邻居数
- 影响聚类的密度阈值
- **推荐值**: 5（与 DBSCAN 保持一致）
- 调整建议:
  - 增大 → 更保守，只保留高密度聚类
  - 减小 → 更宽松，包含更多低密度聚类

### 其他参数

**`--run-id`** (默认: spatial_hdbscan_v1)
- 结果的唯一标识符
- 存储在数据库的 run_id 字段

**`--db-path`** (默认: data/villages.db)
- 数据库路径

**`--delete-optimized-kde`**
- 是否删除 optimized_kde_v1 重复数据
- 建议首次运行时添加此参数

---

## 预期结果

基于 285,080 个村庄，使用默认参数 (min_cluster_size=10, min_samples=5)：

### 预期指标

| 指标 | 预期值 | 说明 |
|------|--------|------|
| 聚类数 | 2,000 - 5,000 | 自动确定，无需手动设置 |
| 覆盖率 | 85% - 95% | 被分配到聚类的村庄比例 |
| 噪声点 | 5% - 15% | 未被分配到任何聚类的村庄 |
| 平均聚类大小 | 50 - 150 | 每个聚类的平均村庄数 |
| 平均距离 | 0.5 - 1.5 km | 聚类内村庄到中心的平均距离 |

### 与 DBSCAN 对比

| 算法 | 聚类数 | 覆盖率 | 特点 |
|------|--------|--------|------|
| DBSCAN (eps=0.5km) | 12,791 | 58.8% | 超密集核心 |
| DBSCAN (eps=1.0km) | 4,852 | 92.0% | 标准密度 |
| DBSCAN (eps=2.0km) | 253 | 99.3% | 全域覆盖 |
| **HDBSCAN** | 2,000-5,000 | 85-95% | **自动多密度** |

HDBSCAN 的优势：
- ✅ 一次运行覆盖所有密度
- ✅ 自动识别珠三角密集区和粤北稀疏区
- ✅ 提供聚类概率（置信度）

---

## 运行时间

- **预计时间**: 10-30 分钟
- **内存占用**: 4-8 GB
- **CPU 使用**: 多核并行（自动）

**注意**: HDBSCAN 比 DBSCAN 慢，但这是离线处理，可以接受。

---

## 输出结果

### 数据库表

**1. `spatial_clusters` 表**

新增记录：
- `run_id`: spatial_hdbscan_v1
- `cluster_id`: 聚类 ID (0, 1, 2, ...)
- `cluster_size`: 聚类大小
- `center_lat`, `center_lon`: 聚类中心坐标
- `avg_distance_km`: 平均距离
- `city`, `county`: 主要区域

**2. `village_spatial_features` 表**

新增字段：
- `run_id`: spatial_hdbscan_v1
- `cluster_id`: 村庄所属聚类 (-1 表示噪声点)
- `cluster_probability`: 聚类概率 (0.0 - 1.0)

**聚类概率说明:**
- 1.0: 核心村庄，明确属于该聚类
- 0.5-0.9: 边缘村庄，可能属于该聚类
- 0.0-0.5: 噪声点，不属于任何聚类

---

## 验证结果

运行完成后，使用监控脚本验证：

```bash
python scripts/utils/monitor_spatial_clustering.py
```

预期输出：

```
================================================================================
Spatial Clustering Progress Monitor - 2026-02-25
================================================================================
Total villages in database: 285,860

Target Run IDs Status:
--------------------------------------------------------------------------------
Run ID          | Status    | Clusters | Villages | Coverage | Last Update
--------------------------------------------------------------------------------
spatial_eps_05  | Complete  |   12,791 |  167,969 |   58.8% | 22:19:56
spatial_eps_10  | Complete  |    4,852 |  262,987 |   92.0% | 22:19:52
spatial_eps_20  | Complete  |      253 |  283,756 |   99.3% | 02:12:13
spatial_hdbscan_v1 | Complete | 3,500 |  250,000 |   87.5% | [时间]
```

---

## 参数调优建议

### 如果聚类太多（>5,000）

增大 `min_cluster_size`:

```bash
python scripts/core/run_hdbscan_clustering.py \
    --min-cluster-size 20 \
    --min-samples 5
```

### 如果聚类太少（<1,000）

减小 `min_cluster_size`:

```bash
python scripts/core/run_hdbscan_clustering.py \
    --min-cluster-size 5 \
    --min-samples 3
```

### 如果噪声点太多（>20%）

减小 `min_samples`:

```bash
python scripts/core/run_hdbscan_clustering.py \
    --min-cluster-size 10 \
    --min-samples 3
```

---

## 故障排除

### 问题 1: hdbscan 安装失败

**解决方案:**

```bash
# Windows
pip install --upgrade pip
pip install hdbscan

# 如果还是失败，尝试使用 conda
conda install -c conda-forge hdbscan
```

### 问题 2: 内存不足

**解决方案:**

减小数据规模（采样）或增加系统内存。

### 问题 3: 运行时间过长（>1 小时）

**解决方案:**

这是正常的。HDBSCAN 对大规模数据需要较长时间。可以：
- 在后台运行
- 使用更强的机器
- 考虑使用 DBSCAN 替代

---

## 下一步

运行完成后：

1. ✅ 验证结果（使用监控脚本）
2. ✅ 更新 active_run_ids（如果需要）
3. ✅ 对比 HDBSCAN vs DBSCAN 结果
4. ✅ 更新 API 文档
5. ✅ 测试 API 端点

---

## 文件清单

**新增文件:**
1. `scripts/core/run_hdbscan_clustering.py` - HDBSCAN 聚类脚本
2. `run_hdbscan_all.py` - 一键运行脚本
3. `docs/reports/HDBSCAN_ANALYSIS.md` - HDBSCAN 分析文档
4. `docs/reports/HDBSCAN_GUIDE.md` - 本文档

**需要更新的文件:**
5. `docs/frontend/API_REFERENCE.md` - 添加 HDBSCAN 端点说明
6. `docs/reports/SPATIAL_CLUSTERING_OPTIMIZATION.md` - 添加 HDBSCAN 结果

---

**Status:** 准备就绪
**Next Action:** 运行 `python run_hdbscan_all.py`
