# Skill 05: Semantic Lexicon Builder

## Skill Name
semantic_lexicon_builder

## Purpose

Build and maintain structured semantic lexicons for natural village name analysis.

These lexicons categorize Chinese characters (and optionally bi-grams) into semantic groups such as:

- Mountain / Terrain
- Water Systems
- Settlement Structure
- Directional / Spatial Orientation
- Clan / Surname
- Symbolic / Religious
- Agriculture
- Vegetation
- Transportation / Infrastructure

The lexicons serve as the foundation for:

- Semantic classification
- Virtual Term Frequency (VTF)
- Regional semantic tendency analysis
- Cluster interpretation

This skill does NOT require model training.


---

## Design Principles

- Lexicons must be version-controlled
- All changes must be recorded in README
- Lexicons must be explainable and transparent
- Categories must remain mutually interpretable (overlap allowed but documented)
- No black-box inference

Lexicons should be stored as:

- JSON
- Python dictionary
- Or SQLite table

Structure:

{
  "category_name": ["char1", "char2", ...]
}


---

# Core Semantic Lexicons

Below are the initial semantic categories.

All entries are Chinese characters or short tokens.

These lists are intentionally broad and may be refined later.


---

## 1️⃣ Mountain / Terrain Related (山地地形类)

山  
岭  
峰  
岗  
冈  
坡  
坳  
坑  
峒  
峪  
峦  
岩  
石  
崖  
台  
垄  
坝  
坪  
坜  
崇  
嶂  
峻  
岐  
岗  
顶  
脊  
塝  
壁  
丘  
陂  
塱  
坎  
岔  
峡  
峤  
岑  
岫  
屿  
屺  
屹  
岗子  
岭头  
岭下  
岭上  
石岗  
石岭  
石岩  
石背  
石坎  
石壁  
石坡  
石坑  
石岗  
石峰  
石顶  


---

## 2️⃣ Water System Related (水系相关类)

江  
河  
溪  
涌  
沥  
港  
塘  
湖  
泉  
渠  
沟  
渡  
湾  
滩  
洲  
滨  
涧  
汀  
淀  
淤  
泊  
潭  
池  
圳  
洪  
潮  
浪  
津  
渚  
滨  
沿  
浦  
滘  
濠  
溪口  
溪尾  
溪头  
河口  
河边  
河背  
河坝  
河湾  
河涌  
江口  
江边  
江背  
江尾  
江湾  
江岸  
水口  
水尾  
水头  
水边  
水背  
水塘  
水圳  
水湾  
水渠  
水闸  
水埗  
水围  
水浸  
水湄  
沥尾  
沥头  
沥口  
沥边  
涌口  
涌边  
涌尾  
港口  
港尾  
港边  
港湾  
塘尾  
塘口  
塘头  
塘边  
湖尾  
湖口  
湖边  
泉口  
泉头  
渡口  
渡头  


---

## 3️⃣ Settlement Structure (聚落形态类)

围  
墟  
圩  
坊  
里  
巷  
街  
寨  
庄  
村  
社  
队  
组  
片  
屯  
堡  
坊  
屋  
楼  
堂  
祠  
埠  
市  
场  
塆  
坊  
宅  
村头  
村尾  
村口  
村边  
寨下  
寨上  
寨尾  
寨口  
围屋  
围内  
围外  
围尾  
围口  


---

## 4️⃣ Direction / Spatial Orientation (方位类)

东  
西  
南  
北  
中  
上  
下  
前  
后  
内  
外  
左  
右  
里  
外  
旁  
侧  
边  
口  
尾  
头  
上村  
下村  
东村  
西村  
南村  
北村  
前村  
后村  
中村  


---

## 5️⃣ Clan / Surname (宗族姓氏类)

陈  
李  
黄  
张  
刘  
林  
何  
梁  
罗  
吴  
周  
徐  
郑  
谢  
赖  
邓  
曾  
叶  
冯  
朱  
钟  
卢  
潘  
蔡  
郭  
邱  
苏  
曹  
高  
袁  
许  
唐  
戴  
萧  
赖  
欧  
欧阳  
司徒  
上官  
梁屋  
陈屋  
李屋  
黄屋  


---

## 6️⃣ Symbolic / Religious / Auspicious (象征信仰类)

龙  
凤  
虎  
龟  
麟  
仙  
佛  
观  
寺  
庙  
堂  
宫  
神  
灵  
福  
禄  
寿  
吉  
祥  
瑞  
安  
泰  
昌  
兴  
盛  
荣  
华  
宝  
明  
光  
文  
武  
圣  
贤  
德  
信  
义  


---

## 7️⃣ Agriculture / Field / Rural Production (农业耕作类)

田  
地  
畔  
畴  
畔  
畲  
圃  
园  
畜  
牧  
禾  
稻  
谷  
仓  
塘  
堤  
坡地  
水田  
旱田  
农  
耕  
耕地  


---

## 8️⃣ Vegetation / Ecology (植物生态类)

林  
木  
树  
松  
竹  
梅  
花  
草  
茶  
果  
榕  
杉  
柏  
柳  
枫  
杨  
桐  
榄  
桃  
李  
蕉  
荷  
藤  
蔗  
槐  
杏  
樟  
桉  


---

## 9️⃣ Transportation / Infrastructure (交通基础设施类)

桥  
路  
站  
埠  
码头  
渡口  
车  
铁  
隧  
道  
港  
码  
渡  
驿  
站  
圩市  


---

## Lexicon Storage

The lexicon must be saved in:

lexicon_v1.json

Each category stored as:

{
  "mountain": [...],
  "water": [...],
  "settlement": [...],
  ...
}

Each change requires:

- README update
- Version increment


---

# Skill 07: Virtual Term Frequency Engine

## Skill Name
virtual_term_frequency_engine

## Purpose

Implement Virtual Term Frequency (VTF) to measure semantic family usage across regions.

This engine aggregates characters belonging to a semantic category
and treats them as a single "virtual token".

This enables:

- Semantic-level frequency analysis
- Regional semantic tendency comparison
- Mountain vs Water distribution analysis


---

## Mathematical Definition

For region g and semantic category C:

VTF(C, g) = Σ n_{g,c}, where c ∈ C

p_g(C) = VTF(C,g) / N_g

Global baseline:

p(C) = VTF(C,all) / N

Tendency score:

T_g(C) = p_g(C) / p(C)

Optional:
- log(T_g(C))
- Laplace smoothing


---

## Output Fields

For each region:

- region_name
- category
- VTF_count
- region_ratio
- global_ratio
- tendency_score
- rank_within_region


---

## Performance Constraints

- Must operate on precomputed char frequency tables
- No real-time heavy computation
- Fully script-based


---

## Research Value

This engine allows analysis such as:

- Which counties show strongest water-related naming bias?
- Is mountainous naming clustered in northern Guangdong?
- Do delta regions show strong hydrological lexical dominance?

This bridges pure statistics and semantic interpretation.

