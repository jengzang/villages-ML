# Run_ID 管理 - 快速参考指南

## 概述

Run_ID 动态管理系统已实施，采用**双重保障策略**确保系统始终使用正确的 run_id。

## 三种使用方式

### 方式 1: 自动更新（推荐）⭐

在分析脚本末尾添加一行代码：

```python
from scripts.utils.update_run_id import update_active_run_id

# 分析完成后
update_active_run_id(
    "spatial_hotspots",  # 分析类型
    new_run_id,          # 新生成的 run_id
    notes="空间分析完成"  # 备注（可选）
)
```

**分析类型列表:**
- `char_frequency` - 字符频率
- `char_embeddings` - 字符嵌入
- `char_significance` - 字符显著性
- `clustering_county` - 县级聚类
- `ngrams` - N-gram 模式
- `patterns` - 模式倾向性
- `semantic` - 语义分析
- `spatial_hotspots` - 空间热点
- `spatial_integration` - 空间整合
- `village_features` - 村庄特征

### 方式 2: 手动更新（通过 API）

```bash
curl -X PUT "http://localhost:8000/api/admin/run-ids/active/spatial_hotspots" \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "final_04_20260222_150000",
    "updated_by": "admin",
    "notes": "新的空间分析运行"
  }'
```

### 方式 3: 什么都不做（智能回退）

系统会自动检测并使用最新的 run_id。无需任何操作！

## 常用命令

### 查询当前配置

```bash
# 查询所有活跃 run_id
curl "http://localhost:8000/api/admin/run-ids/active"

# 查询特定分析类型
curl "http://localhost:8000/api/admin/run-ids/active/spatial_hotspots"

# 查询可用的 run_id 列表
curl "http://localhost:8000/api/admin/run-ids/available/spatial_hotspots"
```

### 使用 API 端点

```bash
# 使用活跃版本（默认）
curl "http://localhost:8000/api/spatial/hotspots"

# 显式指定版本
curl "http://localhost:8000/api/spatial/hotspots?run_id=final_03_20260219_225259"
```

## 工作原理

### 智能回退机制

1. API 首先尝试使用配置的 run_id
2. 如果配置的版本不存在，自动查找最新版本
3. 如果找到最新版本，自动使用并打印警告
4. 如果没有任何可用版本，返回错误

**示例:**
```
配置: "final_03_20260219_225259" (不存在)
数据库: "final_04_20260222_150000" (最新)
结果: 自动使用 "final_04_20260222_150000"
```

### 自动更新机制

1. 分析脚本完成后调用 `update_active_run_id()`
2. 更新 `active_run_ids` 表
3. 刷新内存缓存
4. 下次 API 调用自动使用新版本

## 常见问题

### Q: 运行新分析后，API 会自动使用新数据吗？

**A:** 有三种情况：

1. **如果脚本包含自动更新代码**: 是，立即生效
2. **如果没有自动更新代码**: 是，智能回退会自动使用最新版本
3. **如果想手动控制**: 使用 API 手动更新

### Q: 如何知道当前使用的是哪个 run_id？

**A:** 查询 API：
```bash
curl "http://localhost:8000/api/admin/run-ids/active/spatial_hotspots"
```

### Q: 如何回退到之前的版本？

**A:** 使用 API 更新：
```bash
curl -X PUT "http://localhost:8000/api/admin/run-ids/active/spatial_hotspots" \
  -d '{"run_id": "old_run_id_here"}'
```

### Q: 智能回退会影响性能吗？

**A:** 不会。验证逻辑仅在首次调用时执行，之后使用内存缓存。

### Q: 如何查看所有可用的 run_id？

**A:** 使用 API：
```bash
curl "http://localhost:8000/api/admin/run-ids/available/spatial_hotspots"
```

## 最佳实践

### 1. 在分析脚本中添加自动更新

**推荐做法:**
```python
# scripts/core/phase_04_spatial_analysis.py

from scripts.utils.update_run_id import update_active_run_id

# ... 分析代码 ...

# 末尾添加
update_active_run_id(
    "spatial_hotspots",
    run_id,
    notes=f"空间分析完成，发现{len(hotspots)}个热点"
)
```

### 2. 使用有意义的 run_id

**推荐格式:**
- `{type}_{version}_{timestamp}` - 例如: `final_04_20260222_150000`
- `{type}_{iteration}` - 例如: `cluster_001`, `cluster_002`

### 3. 添加备注说明

```python
update_active_run_id(
    "spatial_hotspots",
    run_id,
    notes="空间分析完成，发现8个热点，使用 DBSCAN 算法"
)
```

### 4. 定期检查配置

```bash
# 每周检查一次
curl "http://localhost:8000/api/admin/run-ids/active"
```

## 故障排除

### 问题: API 返回 404 错误

**原因:** 没有可用的 run_id

**解决:**
1. 运行相应的分析脚本生成数据
2. 或手动设置一个有效的 run_id

### 问题: 智能回退使用了错误的版本

**原因:** 最新版本不是你想要的版本

**解决:**
```bash
# 手动设置正确的版本
curl -X PUT "http://localhost:8000/api/admin/run-ids/active/spatial_hotspots" \
  -d '{"run_id": "correct_run_id"}'
```

### 问题: 更新后 API 仍使用旧版本

**原因:** 缓存未刷新

**解决:**
```bash
# 刷新缓存
curl -X POST "http://localhost:8000/api/admin/run-ids/refresh"
```

## 相关文档

- 完整实施报告: `docs/reports/RUN_ID_MANAGEMENT_IMPLEMENTATION_REPORT.md`
- API 参考: `docs/frontend/API_REFERENCE.md`
- 项目指南: `CLAUDE.md`

## 支持

如有问题，请查看：
1. 完整实施报告（详细技术说明）
2. API 文档（端点使用说明）
3. 项目 README（项目概述）