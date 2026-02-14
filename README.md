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

## License

TBD
