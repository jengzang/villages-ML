#!/usr/bin/env python3
"""
Quick Cost Estimation

Estimate LLM labeling costs without API keys.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nlp.llm_labeler import LLMLabeler


def main():
    print("=" * 60)
    print("LLM LABELING COST ESTIMATION")
    print("=" * 60)

    # Test different scenarios
    scenarios = [
        ("Small test", 50),
        ("Medium batch", 200),
        ("Large batch", 500),
        ("Full unlabeled set", 1000),
    ]

    # Test different models
    models = [
        ("DeepSeek", "deepseek", "deepseek-chat"),
        ("Claude Haiku", "anthropic", "claude-3-haiku"),
        ("Claude Sonnet", "anthropic", "claude-3-sonnet"),
        ("GPT-3.5", "openai", "gpt-3.5-turbo"),
        ("GPT-4", "openai", "gpt-4"),
    ]

    for scenario_name, num_chars in scenarios:
        print(f"\n{scenario_name} ({num_chars} characters):")
        print("-" * 60)

        for model_name, provider, model in models:
            # Create labeler without initializing client
            labeler = LLMLabeler.__new__(LLMLabeler)
            labeler.provider = provider
            labeler.model = model

            cost = labeler.estimate_cost(num_chars)

            print(f"{model_name:15s}: ${cost['total_cost_usd']:7.4f}  "
                  f"(${cost['cost_per_character']:.6f}/char)")

    print("\n" + "=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)
    print("For cost-effective labeling:")
    print("  1. DeepSeek: Best cost/performance ratio ($0.00008/char)")
    print("  2. Claude Haiku: Good quality, low cost ($0.00006/char)")
    print("  3. GPT-3.5: Faster but less accurate ($0.00038/char)")
    print("\nFor highest quality:")
    print("  1. GPT-4: Most accurate but expensive ($0.01800/char)")
    print("  2. Claude Sonnet: Good balance ($0.00315/char)")


if __name__ == "__main__":
    main()
