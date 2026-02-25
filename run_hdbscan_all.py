"""
一键运行：删除 optimized_kde_v1 + 安装 hdbscan + 运行 HDBSCAN 聚类
"""

import subprocess
import sys

def check_and_install_hdbscan():
    """检查并安装 hdbscan"""
    try:
        import hdbscan
        print("[OK] hdbscan 已安装")
        return True
    except ImportError:
        print("[INFO] hdbscan 未安装，正在安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "hdbscan"])
            print("[OK] hdbscan 安装成功")
            return True
        except Exception as e:
            print(f"[ERROR] hdbscan 安装失败: {e}")
            return False

def main():
    print("="*80)
    print("HDBSCAN 空间聚类 - 一键运行")
    print("="*80)

    # 1. 检查并安装 hdbscan
    print("\nStep 1: 检查 hdbscan 库...")
    if not check_and_install_hdbscan():
        print("请手动安装: pip install hdbscan")
        sys.exit(1)

    # 2. 运行 HDBSCAN 聚类脚本
    print("\nStep 2: 运行 HDBSCAN 聚类...")
    cmd = [
        sys.executable,
        "scripts/core/run_hdbscan_clustering.py",
        "--run-id", "spatial_hdbscan_v1",
        "--min-cluster-size", "10",
        "--min-samples", "5",
        "--delete-optimized-kde"
    ]

    try:
        subprocess.check_call(cmd)
        print("\n" + "="*80)
        print("[OK] 完成！")
        print("="*80)
    except Exception as e:
        print(f"\n[ERROR] 运行失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
