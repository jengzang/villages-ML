"""导出广东省自然村名字中所有独特字及其出现次数到 CSV。

统计规则：每个村名内部字符先去重（set），再跨村累计频次。
"""

import csv
import sqlite3
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "villages.db"
OUT_PATH = ROOT / "results" / "char_frequency.csv"


def main():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT 自然村 FROM 广东省自然村")

    counter = Counter()
    total = 0
    for (name,) in cursor:
        if name:
            counter.update(set(name))
        total += 1
        if total % 50000 == 0:
            print(f"已处理 {total} 条...")

    conn.close()
    print(f"总处理 {total} 条村名，独特字 {len(counter)} 个")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["字符", "频次"])
        for char, freq in counter.most_common():
            writer.writerow([char, freq])

    print(f"已导出到 {OUT_PATH}")


if __name__ == "__main__":
    main()
