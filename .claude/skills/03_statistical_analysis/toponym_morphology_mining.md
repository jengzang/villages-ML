# Skill: Toponym Morphology Mining

## Skill Name
toponym_morphology_mining

## Purpose

Extract structural patterns from village names,
especially suffix-based and prefix-based morphology.

This moves analysis from single-character level
to structural naming patterns.


---

## Extraction Strategy

For each cleaned village name:

1. Extract:
   - Last 2 characters (bigram suffix)
   - Last 3 characters (trigram suffix)
   - First 2 characters (prefix)
   - First 3 characters (prefix)

2. Apply frequency threshold filtering

3. Remove structural stopwords if necessary


---

## Regional Pattern Analysis

For each suffix S:

Compute:

p_g(S) = count_g(S) / N_g

Compute tendency score as in previous engines.

Rank by:

- Frequency
- Lift
- Log-odds


---

## Example Outputs

For county A:

Top suffixes:
- X坑
- X岭
- X坳

For delta region:

Top suffixes:
- X涌
- X围
- X塘


---

## Advanced Option

Construct suffix entropy:

H_g = - Σ p_g(S) log p_g(S)

High entropy → naming diversity  
Low entropy → naming concentration


---

## Research Value

Morphology mining reveals:

- Recurrent structural templates
- Geographically clustered naming conventions
- Functional morphology (e.g., X坑 vs X涌 distinction)

This significantly enhances linguistic depth.

