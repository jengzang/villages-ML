# Integration Guide

This guide shows how to integrate the tendency analysis skill with existing codebases and applications.

## Integration with Existing Project

### Using with the Main Application

Integrate with the existing `main.py` application:

```python
# In your main.py
from tendency_analysis.scripts.analyzer import TendencyAnalyzer
from tendency_analysis.scripts.data_loader import load_village_data

def feature_analyze_tendencies():
    """Feature 5: Analyze naming tendencies by town."""
    print("\\n=== 村庄名称倾向性分析 ===")

    # Load data (reuse existing parser)
    from data_parser import parse_village_file
    data = parse_village_file("阳春村庄名录.txt")

    # Create analyzer
    analyzer = TendencyAnalyzer(data)

    # Get user input
    print("\\n请选择分析范围:")
    print("1. 分析所有镇")
    print("2. 分析特定镇")
    choice = input("请输入选项 (1-2): ")

    if choice == "1":
        target_town = None
    elif choice == "2":
        target_town = input("请输入镇名称 (例如: 春城街道): ")
    else:
        print("无效选项")
        return

    # Get parameters
    try:
        n = int(input("请输入n值 (建议1-3): ") or "1")
        high_threshold = float(input("请输入高倾向阈值 (建议10-20): ") or "10")
        low_threshold = float(input("请输入低倾向阈值 (建议20-30): ") or "20")
    except ValueError:
        print("输入无效，使用默认值")
        n, high_threshold, low_threshold = 1, 10, 20

    # Run analysis
    print("\\n正在分析...")
    results = analyzer.analyze_tendencies(
        n=n,
        target_town=target_town,
        high_threshold=high_threshold,
        low_threshold=low_threshold
    )

    # Display results
    analyzer.print_results(results)

    # Optional: export results
    export = input("\\n是否导出结果? (y/n): ")
    if export.lower() == 'y':
        from tendency_analysis.scripts.data_loader import export_results
        format_choice = input("选择格式 (json/markdown/txt): ") or "txt"
        filename = f"tendency_results.{format_choice}"
        export_results(results, filename, format=format_choice)
        print(f"结果已导出到: {filename}")
```

### Add to Main Menu

```python
# In main.py main menu
def main():
    while True:
        print("\\n=== 阳春市村庄名录查询系统 ===")
        print("1. 查询村庄名录")
        print("2. 查询字/词频率")
        print("3. 查询最常见字符")
        print("4. 查询重名村庄")
        print("5. 分析村名倾向性")  # New feature
        print("6. 查询村庄信息")
        print("7. 添加村庄信息")
        print("0. 退出")

        choice = input("请选择功能: ")

        if choice == "5":
            feature_analyze_tendencies()
        # ... other features
```

## API Integration

Create a REST API for tendency analysis:

```python
from flask import Flask, request, jsonify
from tendency_analysis.scripts.optimized_analyzer import OptimizedTendencyAnalyzer
from tendency_analysis.scripts.data_loader import load_village_data

app = Flask(__name__)

# Load data once at startup
data = load_village_data("阳春村庄名录.txt")
analyzer = OptimizedTendencyAnalyzer(data)

@app.route('/api/analyze', methods=['POST'])
def analyze_tendencies():
    """
    Analyze tendencies with custom parameters.

    Request body:
    {
        "n": 1,
        "target_town": "春城街道",  // optional
        "high_threshold": 10,
        "low_threshold": 20,
        "display_threshold": 5
    }
    """
    params = request.json

    try:
        results = analyzer.analyze_tendencies(
            n=params.get('n', 1),
            target_town=params.get('target_town'),
            high_threshold=params.get('high_threshold', 10),
            low_threshold=params.get('low_threshold', 20),
            display_threshold=params.get('display_threshold', 5)
        )

        return jsonify({
            'status': 'success',
            'results': results
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/character/<char>', methods=['GET'])
def get_character_stats(char):
    """Get statistics for a specific character."""
    try:
        stats = analyzer.get_char_statistics(char)
        return jsonify({
            'status': 'success',
            'character': char,
            'statistics': stats
        })
    except KeyError:
        return jsonify({
            'status': 'error',
            'message': f'Character {char} not found'
        }), 404

@app.route('/api/towns', methods=['GET'])
def list_towns():
    """List all available towns."""
    return jsonify({
        'status': 'success',
        'towns': list(analyzer.town_total_counts.keys())
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### API Usage Examples

```bash
# Analyze all towns
curl -X POST http://localhost:5000/api/analyze \\
  -H "Content-Type: application/json" \\
  -d '{"n": 1, "high_threshold": 10, "low_threshold": 20}'

# Analyze specific town
curl -X POST http://localhost:5000/api/analyze \\
  -H "Content-Type: application/json" \\
  -d '{"n": 1, "target_town": "春城街道", "high_threshold": 10}'

# Get character statistics
curl http://localhost:5000/api/character/田

# List all towns
curl http://localhost:5000/api/towns
```

## Command-Line Interface

Create a CLI tool:

```python
#!/usr/bin/env python3
"""
Command-line interface for tendency analysis.

Usage:
    tendency-cli analyze [--town TOWN] [--n N] [--high HIGH] [--low LOW]
    tendency-cli character CHAR
    tendency-cli export [--format FORMAT] [--output FILE]
"""

import argparse
from tendency_analysis.scripts.optimized_analyzer import OptimizedTendencyAnalyzer
from tendency_analysis.scripts.data_loader import load_village_data, export_results
from tendency_analysis.scripts.formatter import format_results_markdown

def main():
    parser = argparse.ArgumentParser(description='Village name tendency analysis')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze tendencies')
    analyze_parser.add_argument('--town', type=str, help='Target town')
    analyze_parser.add_argument('--n', type=int, default=1, help='Group size')
    analyze_parser.add_argument('--high', type=float, default=10, help='High threshold')
    analyze_parser.add_argument('--low', type=float, default=20, help='Low threshold')
    analyze_parser.add_argument('--display', type=float, default=5, help='Display threshold')

    # Character command
    char_parser = subparsers.add_parser('character', help='Get character statistics')
    char_parser.add_argument('char', type=str, help='Character to query')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export results')
    export_parser.add_argument('--format', choices=['json', 'markdown', 'txt', 'html'],
                               default='markdown', help='Output format')
    export_parser.add_argument('--output', type=str, default='results', help='Output file')

    args = parser.parse_args()

    # Load data
    print("Loading data...")
    data = load_village_data("阳春村庄名录.txt")
    analyzer = OptimizedTendencyAnalyzer(data)

    if args.command == 'analyze':
        print("Analyzing...")
        results = analyzer.analyze_tendencies(
            n=args.n,
            target_town=args.town,
            high_threshold=args.high,
            low_threshold=args.low,
            display_threshold=args.display
        )
        analyzer.print_results(results)

    elif args.command == 'character':
        try:
            stats = analyzer.get_char_statistics(args.char)
            print(f"\\nCharacter: {args.char}")
            print(f"Overall frequency: {stats['overall_frequency']:.2%}")
            print(f"Appears in {stats['town_count']} towns")
            print(f"Total count: {stats['total_count']}")
            print(f"Highest: {stats['max_frequency']:.2%} in {stats['max_town']}")
            print(f"Lowest: {stats['min_frequency']:.2%} in {stats['min_town']}")
        except KeyError:
            print(f"Character '{args.char}' not found")

    elif args.command == 'export':
        print("Analyzing...")
        results = analyzer.analyze_tendencies(n=1)
        output_file = f"{args.output}.{args.format}"
        export_results(results, output_file, format=args.format)
        print(f"Results exported to {output_file}")

if __name__ == '__main__':
    main()
```

### CLI Usage Examples

```bash
# Analyze all towns
python tendency-cli.py analyze

# Analyze specific town
python tendency-cli.py analyze --town 春城街道 --n 1 --high 10

# Get character statistics
python tendency-cli.py character 田

# Export results
python tendency-cli.py export --format markdown --output my_results
```

## Web Application Integration

Integrate with a web application:

```python
# Django view example
from django.http import JsonResponse
from django.views import View
from tendency_analysis.scripts.optimized_analyzer import OptimizedTendencyAnalyzer
from tendency_analysis.scripts.data_loader import load_village_data

class TendencyAnalysisView(View):
    # Load analyzer once at class level
    data = load_village_data("阳春村庄名录.txt")
    analyzer = OptimizedTendencyAnalyzer(data)

    def post(self, request):
        import json
        params = json.loads(request.body)

        results = self.analyzer.analyze_tendencies(
            n=params.get('n', 1),
            target_town=params.get('target_town'),
            high_threshold=params.get('high_threshold', 10),
            low_threshold=params.get('low_threshold', 20)
        )

        return JsonResponse({
            'status': 'success',
            'results': results
        })
```

## Database Integration

Store results in a database:

```python
import sqlite3
from datetime import datetime

def save_results_to_db(results, analyzer, db_path='tendency_results.db'):
    """Save analysis results to SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            parameters TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER,
            town TEXT,
            character TEXT,
            tendency_type TEXT,
            tendency_value REAL,
            reference_towns TEXT,
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        )
    ''')

    # Insert analysis record
    timestamp = datetime.now().isoformat()
    cursor.execute(
        'INSERT INTO analyses (timestamp, parameters) VALUES (?, ?)',
        (timestamp, 'n=1, high_threshold=10, low_threshold=20')
    )
    analysis_id = cursor.lastrowid

    # Insert results
    for town, town_results in results.items():
        for char, value, ref_towns in town_results['high_tendency']:
            cursor.execute(
                'INSERT INTO results VALUES (NULL, ?, ?, ?, ?, ?, ?)',
                (analysis_id, town, char, 'high', value, ','.join(ref_towns))
            )

        for char, value, ref_towns in town_results['low_tendency']:
            cursor.execute(
                'INSERT INTO results VALUES (NULL, ?, ?, ?, ?, ?, ?)',
                (analysis_id, town, char, 'low', value, ','.join(ref_towns))
            )

    conn.commit()
    conn.close()
    print(f"Results saved to database: {db_path}")

# Usage
results = analyzer.analyze_tendencies(n=1)
save_results_to_db(results, analyzer)
```

## Jupyter Notebook Integration

Use in Jupyter notebooks for interactive analysis:

```python
# In Jupyter notebook
%matplotlib inline
import matplotlib.pyplot as plt
from tendency_analysis.scripts.optimized_analyzer import OptimizedTendencyAnalyzer
from tendency_analysis.scripts.data_loader import load_village_data

# Load data
data = load_village_data("阳春村庄名录.txt")
analyzer = OptimizedTendencyAnalyzer(data)

# Interactive analysis
def analyze_and_plot(town_name):
    results = analyzer.analyze_tendencies(n=1, target_town=town_name)
    town_results = results[town_name]

    # Plot high tendency
    chars = [c for c, _, _ in town_results['high_tendency'][:10]]
    values = [v for _, v, _ in town_results['high_tendency'][:10]]

    plt.figure(figsize=(12, 5))
    plt.bar(chars, values, color='green', alpha=0.7)
    plt.title(f'{town_name} - High Tendency Characters')
    plt.ylabel('Tendency Value (%)')
    plt.grid(axis='y', alpha=0.3)
    plt.show()

# Use with ipywidgets for interactive selection
from ipywidgets import interact, Dropdown

towns = list(analyzer.town_total_counts.keys())
interact(analyze_and_plot, town_name=Dropdown(options=towns))
```

## Testing Integration

Write tests for your integration:

```python
import unittest
from tendency_analysis.scripts.analyzer import TendencyAnalyzer

class TestTendencyIntegration(unittest.TestCase):
    def setUp(self):
        # Sample data for testing
        self.data = {
            "Town1": {
                "村民委员会": ["Committee1"],
                "自然村": {
                    "Committee1": ["田心村", "田边村", "田头村"]
                }
            },
            "Town2": {
                "村民委员会": ["Committee2"],
                "自然村": {
                    "Committee2": ["城东村", "城西村", "城南村"]
                }
            }
        }
        self.analyzer = TendencyAnalyzer(self.data)

    def test_analyze_all_towns(self):
        results = self.analyzer.analyze_tendencies(n=1)
        self.assertIn("Town1", results)
        self.assertIn("Town2", results)

    def test_analyze_specific_town(self):
        results = self.analyzer.analyze_tendencies(n=1, target_town="Town1")
        self.assertIn("Town1", results)
        self.assertNotIn("Town2", results)

    def test_high_tendency_structure(self):
        results = self.analyzer.analyze_tendencies(n=1)
        for town, town_results in results.items():
            self.assertIn("high_tendency", town_results)
            self.assertIn("low_tendency", town_results)
            self.assertIsInstance(town_results["high_tendency"], list)

if __name__ == '__main__':
    unittest.main()
```

## Next Steps

- See [Basic Usage](basic-usage.md) for getting started
- See [Advanced Usage](advanced-usage.md) for complex scenarios
- See [API Reference](../references/api-reference.md) for complete documentation
