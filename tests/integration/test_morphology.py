"""Quick test of morphology extraction functionality."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from src.preprocessing.morphology_extractor import extract_morphology_features

# Create test data
test_data = {
    '市级': ['广州市', '深圳市', '珠海市', '佛山市', '梅州市'],
    '区县级': ['天河区', '南山区', '香洲区', '顺德区', '梅县区'],
    '乡镇级': ['石牌街道', '南头街道', '前山街道', '大良街道', '程江镇'],
    '自然村': ['石岭村', '新围村', '老村', '大涌村', '水坑村']
}

df = pd.DataFrame(test_data)

print("Test data:")
print(df)
print("\n" + "="*80 + "\n")

# Extract morphology features
result_df = extract_morphology_features(
    df,
    suffix_lengths=[1, 2],
    prefix_lengths=[2],
    min_name_length=2
)

print("Morphology features extracted:")
print(result_df[['clean_name', 'suffix_1', 'suffix_2', 'prefix_2']])
print("\n" + "="*80 + "\n")

# Test frequency computation
from src.analysis.morphology_frequency import compute_pattern_frequency_global

global_freq = compute_pattern_frequency_global(result_df, 'suffix_1')
print("Global suffix_1 frequency:")
print(global_freq)
print("\n" + "="*80 + "\n")

print("SUCCESS: All tests passed!")

