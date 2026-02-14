# Skill: Regional Semantic Contrast Analysis

## Skill Name
regional_semantic_contrast_analysis

## Purpose

Quantitatively measure semantic differences between regions.

Instead of only computing regional intensity,
this skill identifies which semantic categories
distinctively characterize each region.


---

## Contrast Metrics

### 1️⃣ Lift Ratio

Lift(C, g) =
  p_g(C) / p_global(C)

Where:
p_g(C) = SemanticIntensity(C,g)

Interpretation:
- >1 means overrepresented
- <1 means underrepresented


---

### 2️⃣ Log-Odds with Informative Prior

For robustness:

log_odds(C,g) =
  log( (n_g,C + α) / (N_g - n_g,C + α) )
  - log( (n_global,C + α) / (N_global - n_global,C + α) )

α = smoothing constant

This avoids small-sample inflation.


---

### 3️⃣ KL Divergence (Optional)

Measure full semantic profile divergence:

D_KL(RegionProfile_g || ProvinceProfile)

This gives an overall deviation score.


---

## Output

For each region:

- Top overrepresented categories
- Top underrepresented categories
- Contrast score
- Divergence score


---

## Interpretation Layer

Example conclusions:

- Northern regions show strong positive log-odds in mountain-related lexicon
- Delta regions show high lift in water-related lexicon
- Certain counties show unusually high clan-index concentration

This deepens statistical rigor beyond raw frequency.

