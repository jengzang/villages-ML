# Villages ML Project

广东省自然村机器学习项目 (Guangdong Province Natural Villages Machine Learning Project)

## 项目简介 (Project Overview)

This project focuses on analyzing and modeling village data from Guangdong Province, China. The dataset includes geographic coordinates, administrative divisions, and language distribution information for natural villages.

## 数据结构 (Data Structure)

The project uses a SQLite database (`data/villages.db`) containing information about villages including:
- Administrative hierarchy (city, county, township, village committee)
- Village names and pinyin romanization
- Geographic coordinates (longitude, latitude)
- Language distribution
- Data sources and update timestamps

## 开发环境 (Development Environment)

### Requirements

- Python 3.8+
- See `requirements.txt` for Python dependencies

### Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
source venv/Scripts/activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 自定义技能 (Custom Skills)

This project includes custom Claude Code skills in `.claude/skills/`. Use them by typing `/skill-name` in Claude Code CLI.

## 频率分析管道 (Frequency Analysis Pipeline)

### 运行分析 (Running Analysis)

```bash
# Run frequency analysis pipeline
python scripts/run_frequency_analysis.py --run-id run_003

# Results will be saved to results/run_003/
```

### 数据库持久化 (Database Persistence)

Analysis results are automatically persisted to the SQLite database in the following tables:

- `analysis_runs`: Run metadata and configuration
- `char_frequency_global`: Global character frequency statistics
- `char_frequency_regional`: Regional character frequency (city/county/township levels)
- `regional_tendency`: Regional tendency analysis (lift, log-odds, z-score)

### 查询结果 (Querying Results)

Use the query script to retrieve analysis results from the database:

```bash
# List all analysis runs
python scripts/query_results.py --list-runs

# Query global frequency (top 20 characters)
python scripts/query_results.py --run-id run_002 --type global --top 20

# Query regional frequency for a specific region
python scripts/query_results.py --run-id run_002 --type regional --level city --region 广州市 --top 20

# Query character tendency across regions
python scripts/query_results.py --run-id run_002 --type char-tendency --char 村 --level city

# Query region tendency profile (most characteristic characters)
python scripts/query_results.py --run-id run_002 --type region-profile --level city --region 广州市 --top 20

# Query top polarized characters (highest absolute tendency)
python scripts/query_results.py --run-id run_002 --type polarized --level city --top 20

# Save results to CSV
python scripts/query_results.py --run-id run_002 --type global --top 100 --output results.csv
```

### 查询接口 (Query API)

You can also use the Python query API directly:

```python
import sqlite3
from src.data.db_query import (
    get_latest_run_id,
    get_global_frequency,
    get_regional_frequency,
    get_char_tendency_by_region,
    get_top_polarized_chars,
    get_region_tendency_profile
)

# Connect to database
conn = sqlite3.connect('data/villages.db')

# Get latest run
run_id = get_latest_run_id(conn)

# Query global frequency
df = get_global_frequency(conn, run_id, top_n=20)
print(df)

# Query character tendency across cities
df = get_char_tendency_by_region(conn, run_id, '村', 'city')
print(df)

conn.close()
```

## License

TBD
