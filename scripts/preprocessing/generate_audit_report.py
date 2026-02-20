"""Generate comprehensive audit report for prefix cleaning.

This script analyzes the prefix cleaning results and generates a detailed report.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_audit_report(conn: sqlite3.Connection, output_path: Path):
    """Generate comprehensive audit report."""
    cursor = conn.cursor()

    report_lines = []
    report_lines.append("# Prefix Cleaning Audit Report")
    report_lines.append("")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    # Section 1: Executive Summary
    report_lines.append("## Executive Summary")
    report_lines.append("")

    cursor.execute("SELECT COUNT(*) FROM prefix_cleaning_audit_log")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(是否去除) FROM prefix_cleaning_audit_log")
    removed = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(需要人工审核) FROM prefix_cleaning_audit_log")
    review = cursor.fetchone()[0] or 0

    cursor.execute("SELECT AVG(最终置信度) FROM prefix_cleaning_audit_log WHERE 是否去除=1")
    avg_conf = cursor.fetchone()[0] or 0

    report_lines.append(f"- Total villages processed: {total:,}")
    report_lines.append(f"- Prefixes removed: {removed:,} ({100*removed/total:.2f}%)")
    report_lines.append(f"- Needs manual review: {review:,} ({100*review/total:.2f}%)")
    report_lines.append(f"- Average confidence (removed): {avg_conf:.3f}")
    report_lines.append("")

    # Section 2: Removal Rate by City
    report_lines.append("## Removal Rate by City")
    report_lines.append("")

    query = """
    SELECT
        市级,
        COUNT(*) as total,
        SUM(是否去除) as removed,
        ROUND(100.0 * SUM(是否去除) / COUNT(*), 2) as removal_rate,
        ROUND(AVG(CASE WHEN 是否去除=1 THEN 最终置信度 END), 3) as avg_confidence
    FROM prefix_cleaning_audit_log
    GROUP BY 市级
    ORDER BY removal_rate DESC
    """
    df_city = pd.read_sql(query, conn)

    report_lines.append("| City | Total | Removed | Removal Rate | Avg Confidence |")
    report_lines.append("|------|-------|---------|--------------|----------------|")
    for _, row in df_city.iterrows():
        report_lines.append(
            f"| {row['市级']} | {row['total']:,} | {row['removed']:,} | "
            f"{row['removal_rate']:.2f}% | {row['avg_confidence']:.3f} |"
        )
    report_lines.append("")

    # Section 3: Most Common Removed Prefixes
    report_lines.append("## Most Common Removed Prefixes (Top 50)")
    report_lines.append("")

    query = """
    SELECT
        去除的前缀 as prefix,
        COUNT(*) as count,
        ROUND(AVG(最终置信度), 3) as avg_confidence
    FROM prefix_cleaning_audit_log
    WHERE 是否去除 = 1
    GROUP BY 去除的前缀
    ORDER BY count DESC
    LIMIT 50
    """
    df_prefix = pd.read_sql(query, conn)

    report_lines.append("| Prefix | Count | Avg Confidence |")
    report_lines.append("|--------|-------|----------------|")
    for _, row in df_prefix.iterrows():
        report_lines.append(
            f"| {row['prefix']} | {row['count']:,} | {row['avg_confidence']:.3f} |"
        )
    report_lines.append("")

    # Section 4: Match Source Distribution
    report_lines.append("## Match Source Distribution")
    report_lines.append("")

    query = """
    SELECT
        匹配来源 as source,
        COUNT(*) as count,
        ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM prefix_cleaning_audit_log WHERE 是否去除=1), 2) as percentage
    FROM prefix_cleaning_audit_log
    WHERE 是否去除 = 1
    GROUP BY 匹配来源
    ORDER BY count DESC
    """
    df_source = pd.read_sql(query, conn)

    report_lines.append("| Match Source | Count | Percentage |")
    report_lines.append("|--------------|-------|------------|")
    for _, row in df_source.iterrows():
        report_lines.append(
            f"| {row['source']} | {row['count']:,} | {row['percentage']:.2f}% |"
        )
    report_lines.append("")

    # Section 5: Confidence Distribution
    report_lines.append("## Confidence Distribution")
    report_lines.append("")

    query = """
    SELECT
        CASE
            WHEN 最终置信度 >= 0.9 THEN '0.9-1.0'
            WHEN 最终置信度 >= 0.8 THEN '0.8-0.9'
            WHEN 最终置信度 >= 0.7 THEN '0.7-0.8'
            WHEN 最终置信度 >= 0.6 THEN '0.6-0.7'
            ELSE '<0.6'
        END as confidence_range,
        COUNT(*) as count
    FROM prefix_cleaning_audit_log
    WHERE 是否去除 = 1
    GROUP BY confidence_range
    ORDER BY confidence_range DESC
    """
    df_conf = pd.read_sql(query, conn)

    report_lines.append("| Confidence Range | Count |")
    report_lines.append("|------------------|-------|")
    for _, row in df_conf.iterrows():
        report_lines.append(f"| {row['confidence_range']} | {row['count']:,} |")
    report_lines.append("")

    # Section 6: Sample Cases for Review
    report_lines.append("## Sample Cases Needing Review (Top 20)")
    report_lines.append("")

    query = """
    SELECT
        市级, 区县级, 乡镇级, 行政村,
        自然村_原始, 前缀候选, 匹配来源, 最终置信度
    FROM prefix_cleaning_audit_log
    WHERE 需要人工审核 = 1
    ORDER BY 最终置信度 ASC
    LIMIT 20
    """
    df_review = pd.read_sql(query, conn)

    if len(df_review) > 0:
        report_lines.append("| City | County | Township | Admin Village | Natural Village | Prefix Candidate | Match Source | Confidence |")
        report_lines.append("|------|--------|----------|---------------|-----------------|------------------|--------------|------------|")
        for _, row in df_review.iterrows():
            report_lines.append(
                f"| {row['市级']} | {row['区县级']} | {row['乡镇级']} | {row['行政村']} | "
                f"{row['自然村_原始']} | {row['前缀候选']} | {row['匹配来源']} | {row['最终置信度']:.3f} |"
            )
    else:
        report_lines.append("No cases need review.")
    report_lines.append("")

    # Section 7: Random Sample Verification
    report_lines.append("## Random Sample Verification (100 cases)")
    report_lines.append("")

    query = """
    SELECT
        市级, 区县级, 乡镇级, 行政村,
        自然村_原始, 自然村_去前缀, 去除的前缀, 匹配来源, 最终置信度
    FROM prefix_cleaning_audit_log
    WHERE 是否去除 = 1
    ORDER BY RANDOM()
    LIMIT 100
    """
    df_sample = pd.read_sql(query, conn)

    report_lines.append("| City | County | Township | Admin Village | Original | After Removal | Removed Prefix | Match Source | Confidence |")
    report_lines.append("|------|--------|----------|---------------|----------|---------------|----------------|--------------|------------|")
    for _, row in df_sample.iterrows():
        report_lines.append(
            f"| {row['市级']} | {row['区县级']} | {row['乡镇级']} | {row['行政村']} | "
            f"{row['自然村_原始']} | {row['自然村_去前缀']} | {row['去除的前缀']} | "
            f"{row['匹配来源']} | {row['最终置信度']:.3f} |"
        )
    report_lines.append("")

    # Section 8: Cross-City Disambiguation Check
    report_lines.append("## Cross-City Disambiguation Check")
    report_lines.append("")

    query = """
    SELECT
        行政村,
        COUNT(DISTINCT 市级) as city_count,
        GROUP_CONCAT(DISTINCT 市级) as cities
    FROM prefix_cleaning_audit_log
    WHERE 是否去除 = 1
    GROUP BY 行政村
    HAVING COUNT(DISTINCT 市级) > 1
    ORDER BY city_count DESC
    LIMIT 20
    """
    df_disambig = pd.read_sql(query, conn)

    if len(df_disambig) > 0:
        report_lines.append("**WARNING: The following administrative villages appear in multiple cities:**")
        report_lines.append("")
        report_lines.append("| Admin Village | City Count | Cities |")
        report_lines.append("|---------------|------------|--------|")
        for _, row in df_disambig.iterrows():
            report_lines.append(
                f"| {row['行政村']} | {row['city_count']} | {row['cities']} |"
            )
        report_lines.append("")
        report_lines.append("This is expected for common village names. Verify that matching was done within correct geographic scope.")
    else:
        report_lines.append("✓ No cross-city disambiguation issues detected.")
    report_lines.append("")

    # Write report
    report_content = "\n".join(report_lines)
    output_path.write_text(report_content, encoding='utf-8')
    logger.info(f"Report written to: {output_path}")


def main():
    """Generate audit report."""
    db_path = Path(__file__).parent.parent / "data" / "villages.db"
    output_path = Path(__file__).parent.parent / "docs" / "PREFIX_CLEANING_AUDIT_REPORT.md"

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return

    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))

    # Check if audit log exists
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='prefix_cleaning_audit_log'"
    )
    if not cursor.fetchone():
        logger.error("Audit log table not found. Run create_audit_log.py first.")
        conn.close()
        return

    # Generate report
    logger.info("Generating audit report...")
    generate_audit_report(conn, output_path)

    conn.close()
    logger.info("Audit report generation complete!")


if __name__ == "__main__":
    main()
