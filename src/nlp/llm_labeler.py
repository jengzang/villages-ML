"""
LLM Labeler

Integrates with LLM APIs to generate semantic labels for characters.
"""

import json
import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LabelingResult:
    """Result of LLM labeling for a character."""
    char: str
    category: str
    confidence: float
    reasoning: str
    alternative_categories: List[str]
    is_new_category: bool


class LLMLabeler:
    """
    Integrates with LLM APIs to label characters semantically.

    Supports multiple providers:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - DeepSeek
    - Local models (via OpenAI-compatible API)
    """

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 500,
    ):
        """
        Initialize LLM labeler.

        Args:
            provider: API provider ('openai', 'anthropic', 'deepseek', 'local')
            model: Model name
            api_key: API key (or from environment)
            base_url: Base URL for API (for local models)
            temperature: Sampling temperature (0 for deterministic)
            max_tokens: Maximum tokens in response
        """
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Get API key from parameter or environment
        if api_key:
            self.api_key = api_key
        else:
            env_var = f"{provider.upper()}_API_KEY"
            self.api_key = os.getenv(env_var)
            if not self.api_key and provider != "local":
                logger.warning(f"No API key found for {provider}. Set {env_var} environment variable.")

        self.base_url = base_url
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize API client based on provider."""
        if self.provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                logger.error("OpenAI package not installed. Install with: pip install openai")

        elif self.provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.error("Anthropic package not installed. Install with: pip install anthropic")

        elif self.provider == "deepseek":
            try:
                import openai
                # DeepSeek uses OpenAI-compatible API
                self.client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.deepseek.com"
                )
            except ImportError:
                logger.error("OpenAI package not installed. Install with: pip install openai")

        elif self.provider == "local":
            try:
                import openai
                self.client = openai.OpenAI(
                    api_key=self.api_key or "dummy",
                    base_url=self.base_url or "http://localhost:8000/v1"
                )
            except ImportError:
                logger.error("OpenAI package not installed. Install with: pip install openai")

    def create_labeling_prompt(
        self,
        char: str,
        frequency: int,
        example_villages: List[str],
        similar_chars: List[Tuple[str, float]],
        existing_categories: List[str],
    ) -> str:
        """
        Create prompt for character labeling.

        Args:
            char: Character to label
            frequency: Number of villages containing this character
            example_villages: Example village names
            similar_chars: Similar characters from embeddings
            existing_categories: Existing semantic categories

        Returns:
            Formatted prompt string
        """
        similar_chars_str = ", ".join([f"{c}({s:.2f})" for c, s in similar_chars[:10]])
        examples_str = ", ".join(example_villages[:5])
        categories_str = ", ".join(existing_categories)

        prompt = f"""你是一位專門研究廣東省地名的語言學家。請為以下漢字分配語義類別。

字符: {char}
出現頻率: {frequency} 個村莊
示例村名: {examples_str}
相似字符: {similar_chars_str}

現有類別:
{categories_str}

請分析這個字符的語義，並：
1. 從現有類別中選擇最合適的類別，或建議新類別
2. 提供信心分數 (0-1)
3. 解釋你的推理
4. 列出可能的替代類別

請以JSON格式回答:
{{
    "category": "類別名稱",
    "confidence": 0.95,
    "reasoning": "推理過程",
    "alternative_categories": ["替代1", "替代2"],
    "is_new_category": false
}}"""

        return prompt

    def label_character(
        self,
        char: str,
        frequency: int,
        example_villages: List[str],
        similar_chars: List[Tuple[str, float]],
        existing_categories: List[str],
    ) -> Optional[LabelingResult]:
        """
        Label a single character using LLM.

        Args:
            char: Character to label
            frequency: Village count
            example_villages: Example village names
            similar_chars: Similar characters from embeddings
            existing_categories: Existing categories

        Returns:
            LabelingResult or None if failed
        """
        if not self.client:
            logger.error("LLM client not initialized")
            return None

        prompt = self.create_labeling_prompt(
            char, frequency, example_villages, similar_chars, existing_categories
        )

        try:
            if self.provider in ["openai", "deepseek", "local"]:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一位語言學專家，專門研究中文地名語義。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                content = response.choices[0].message.content

            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                content = response.content[0].text

            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return None

            # Parse JSON response
            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result_dict = json.loads(content)

            return LabelingResult(
                char=char,
                category=result_dict["category"],
                confidence=result_dict["confidence"],
                reasoning=result_dict["reasoning"],
                alternative_categories=result_dict.get("alternative_categories", []),
                is_new_category=result_dict.get("is_new_category", False),
            )

        except Exception as e:
            logger.error(f"Error labeling character '{char}': {e}")
            return None

    def batch_label_characters(
        self,
        characters_data: List[Dict],
        existing_categories: List[str],
        rate_limit_delay: float = 1.0,
    ) -> List[LabelingResult]:
        """
        Label multiple characters in batch.

        Args:
            characters_data: List of dicts with char, frequency, examples, similar_chars
            existing_categories: Existing semantic categories
            rate_limit_delay: Delay between API calls (seconds)

        Returns:
            List of LabelingResult objects
        """
        results = []

        for i, char_data in enumerate(characters_data):
            logger.info(f"Labeling character {i+1}/{len(characters_data)}: {char_data['char']}")

            result = self.label_character(
                char=char_data["char"],
                frequency=char_data["frequency"],
                example_villages=char_data["example_villages"],
                similar_chars=char_data["similar_chars"],
                existing_categories=existing_categories,
            )

            if result:
                results.append(result)

            # Rate limiting
            if i < len(characters_data) - 1:
                time.sleep(rate_limit_delay)

        logger.info(f"Labeled {len(results)}/{len(characters_data)} characters")
        return results

    def estimate_cost(
        self,
        num_characters: int,
        avg_prompt_tokens: int = 300,
        avg_completion_tokens: int = 150,
    ) -> Dict[str, float]:
        """
        Estimate API cost for labeling.

        Args:
            num_characters: Number of characters to label
            avg_prompt_tokens: Average prompt tokens per character
            avg_completion_tokens: Average completion tokens

        Returns:
            Dictionary with cost estimates
        """
        # Pricing per 1M tokens (as of 2024)
        pricing = {
            "gpt-4": {"input": 30.0, "output": 60.0},
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
            "claude-3-opus": {"input": 15.0, "output": 75.0},
            "claude-3-sonnet": {"input": 3.0, "output": 15.0},
            "claude-3-haiku": {"input": 0.25, "output": 1.25},
            "deepseek-chat": {"input": 0.14, "output": 0.28},
        }

        model_pricing = pricing.get(self.model, {"input": 1.0, "output": 2.0})

        total_input_tokens = num_characters * avg_prompt_tokens
        total_output_tokens = num_characters * avg_completion_tokens

        input_cost = (total_input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (total_output_tokens / 1_000_000) * model_pricing["output"]
        total_cost = input_cost + output_cost

        return {
            "num_characters": num_characters,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "input_cost_usd": input_cost,
            "output_cost_usd": output_cost,
            "total_cost_usd": total_cost,
            "cost_per_character": total_cost / num_characters if num_characters > 0 else 0,
        }
