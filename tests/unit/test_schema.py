from src.schema import get_schema


def test_guangdong_preprocessed_language_column_uses_dialect_distribution():
    schema = get_schema("guangdong")

    assert schema.language_col_preprocessed == "方言分布"
