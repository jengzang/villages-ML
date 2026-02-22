"""
分析脚本辅助工具 - 自动更新 active_run_ids

此模块提供便捷函数，供分析脚本在完成后自动更新活跃 run_id。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.run_id_manager import RunIDManager


def update_active_run_id(
    analysis_type: str,
    run_id: str,
    script_name: str = None,
    notes: str = None,
    db_path: str = "data/villages.db"
):
    """
    更新活跃 run_id（供分析脚本调用）

    Args:
        analysis_type: 分析类型标识
            - "char_frequency" - 字符频率分析
            - "char_embeddings" - 字符嵌入
            - "char_significance" - 字符显著性
            - "clustering_county" - 县级聚类
            - "ngrams" - N-gram模式
            - "patterns" - 模式倾向性
            - "semantic" - 语义分析
            - "spatial_hotspots" - 空间热点
            - "spatial_integration" - 空间整合
            - "village_features" - 村庄特征
        run_id: 新的 run_id
        script_name: 脚本名称（可选，自动检测）
        notes: 备注说明（可选）
        db_path: 数据库路径（默认 data/villages.db）

    Example:
        >>> # 在分析脚本末尾添加
        >>> from scripts.utils.update_run_id import update_active_run_id
        >>>
        >>> update_active_run_id(
        ...     "spatial_hotspots",
        ...     new_run_id,
        ...     notes=f"空间分析完成，发现{hotspot_count}个热点"
        ... )
    """
    # 自动检测脚本名称
    if script_name is None:
        import inspect
        frame = inspect.currentframe().f_back
        script_name = Path(frame.f_code.co_filename).stem

    try:
        manager = RunIDManager(db_path)
        manager.auto_update_from_script(
            analysis_type=analysis_type,
            run_id=run_id,
            script_name=script_name,
            notes=notes
        )
        print(f"✓ 成功更新 {analysis_type} 的活跃 run_id")
        return True
    except Exception as e:
        print(f"✗ 更新活跃 run_id 失败: {e}")
        return False


# 分析类型映射（方便查找）
ANALYSIS_TYPES = {
    "phase_01": "char_embeddings",
    "phase_02": "semantic",
    "phase_03": "semantic",  # semantic co-occurrence
    "phase_04": "spatial_hotspots",
    "phase_05": "village_features",
    "phase_06": "clustering_county",
    "phase_08": "char_frequency",
    "phase_09": "char_significance",
    "phase_10": "char_significance",
    "phase_12": "ngrams",
    "phase_13": "spatial_hotspots",
    "phase_14": "semantic",
}


if __name__ == "__main__":
    # 测试用例
    print("测试 update_active_run_id 函数...")

    # 示例：更新空间热点的 run_id
    success = update_active_run_id(
        analysis_type="spatial_hotspots",
        run_id="test_run_20260222",
        script_name="test_script",
        notes="测试自动更新功能"
    )

    if success:
        print("✓ 测试成功")
    else:
        print("✗ 测试失败")