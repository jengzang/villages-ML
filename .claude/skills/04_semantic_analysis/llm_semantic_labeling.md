# Skill 06: LLM Semantic Labeling (Offline Only)

## Skill Name
llm_semantic_labeling_offline

## Purpose

Use a Large Language Model (LLM) to enrich semantic interpretation
of high-frequency characters, suffixes, or clusters.

This skill is optional but strategically important for:

- deeper semantic abstraction
- discovering latent semantic families
- preparing research material for NLP / LLM integration
- enhancing cluster interpretability

This skill must be executed offline.
It must NOT run on the 2-core / 2GB production server.


---

# Part A: Scope of LLM Labeling

LLM should NOT process all 200k village names.
That would be inefficient and unnecessary.

Instead, label:

1) Top N characters (e.g., top 500–2000 by frequency)
2) Top N suffixes (bigram/trigram)
3) Cluster descriptors
4) Optional: region semantic summaries

This reduces cost and increases signal quality.


---

# Part B: Input Preparation

For character labeling:

Prepare table:

- char
- global_frequency
- example_village_names (top 5 samples)

For suffix labeling:

- suffix
- frequency
- example_village_names

For cluster labeling:

- cluster_id
- top distinguishing features
- representative regions


---

# Part C: Prompt Strategy (Deterministic)

The prompt must enforce structured JSON output.

Example prompt (character labeling):

"You are a linguistic analyst.  
Given the Chinese character below and example village names,  
classify it into one or more semantic categories:

Categories:
- 山地地形
- 水系相关
- 聚落形态
- 方位空间
- 宗族姓氏
- 象征信仰
- 农业耕作
- 植物生态
- 交通基础设施
- 其他

Return JSON only:
{
  "char": "...",
  "categories": [...],
  "confidence": 0-1,
  "explanation": "..."
}"

Strict requirement:
- JSON only
- no additional commentary


---

# Part D: API Strategy

This skill must support pluggable providers:

- DeepSeek API
- OpenAI API
- Other compatible LLM endpoint

Implementation requirements:

- rate limiting
- retry logic
- timeout handling
- logging of failed calls


---

# Part E: Output Artifacts

Directory:
`results/<run_id>/llm_labels/`

Files:

- char_labels.json
- suffix_labels.json
- cluster_labels.json

Metadata:

- model_name
- temperature (default 0)
- date
- total_cost_estimate (if available)


---

# Part F: Integration with Existing Lexicons

LLM output may:

- confirm existing lexicon category
- suggest new category
- flag ambiguous cases

This skill must NOT automatically modify lexicon.
Human review required before lexicon update.


---

# Part G: Cost & Performance Constraints

- Temperature = 0 (deterministic)
- Batch size controlled
- Estimate token cost before full run

Example:
- 1000 characters labeling → manageable cost


---

# Acceptance Criteria

1) JSON-structured outputs
2) Logging of API calls
3) Reproducible labeling configuration
4) No online runtime dependency
