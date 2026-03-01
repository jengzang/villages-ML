# Phase 17: LLM 子类别标注验证报告
**生成时间：** 2026-02-25 18:35:52
---

## 总体统计

- **匹配**：179 个字符
- **不匹配**：42 个字符
- **仅 LLM 标注**：18 个字符
- **仅 v3 标注**：92 个字符
- **准确率**：81.0%

---

## 不匹配的字符

| 字符 | 父类别 | LLM 标注 | v3 标注 |
|------|--------|----------|----------|
| 中 | direction | direction_center | direction_inside |
| 侧 | direction | direction_inside | direction_outside |
| 冈 | mountain | mountain_ridge | mountain_slope |
| 后 | direction | direction_cardinal | direction_horizontal |
| 围 | settlement | settlement_fort | settlement_district |
| 场 | settlement | settlement_market | agriculture_garden |
| 坊 | settlement | settlement_village | settlement_district |
| 坝 | mountain | mountain_plateau | agriculture_irrigation |
| 坳 | mountain | mountain_valley | mountain_slope |
| 堂 | symbolic | symbolic_virtue | symbolic_religion |
| 塱 | mountain | mountain_valley | mountain_plateau |
| 屯 | settlement | settlement_fort | settlement_village |
| 山 | mountain | mountain_rock | mountain_peak |
| 屿 | mountain | mountain_rock | water_island |
| 岗 | mountain | mountain_ridge | mountain_slope |
| 岭 | mountain | mountain_ridge | mountain_peak |
| 巷 | settlement | settlement_building | infrastructure_road |
| 旁 | direction | direction_inside | direction_outside |
| 杉 | vegetation | vegetation_forest | vegetation_pine |
| 李 | clan | clan_li | vegetation_fruit |
| 杨 | vegetation | vegetation_forest | vegetation_other |
| 柏 | vegetation | vegetation_forest | vegetation_pine |
| 树 | vegetation | vegetation_other | vegetation_forest |
| 梅 | vegetation | vegetation_flower | vegetation_fruit |
| 槐 | vegetation | vegetation_flower | vegetation_other |
| 浦 | water | water_shore | water_bay |
| 涧 | water | water_stream | water_river |
| 渠 | water | water_stream | agriculture_irrigation |
| 渡 | water | water_river | infrastructure_port |
| 溪 | water | water_stream | water_river |
| 滘 | water | water_stream | water_bay |
| 滩 | water | water_shore | water_beach |
| 濠 | water | water_river | water_bay |
| 灵 | symbolic | symbolic_virtue | symbolic_religion |
| 畔 | agriculture | agriculture_irrigation | agriculture_field |
| 畜 | agriculture | agriculture_storage | agriculture_activity |
| 社 | settlement | settlement_village | settlement_group |
| 街 | settlement | settlement_market | infrastructure_road |
| 边 | direction | direction_end | direction_outside |
| 里 | settlement | settlement_village | direction_inside |
| 隧 | infrastructure | infrastructure_road | infrastructure_transport |
| 黄 | clan | clan_huang | color |

---

## 仅 LLM 标注的字符（v3 中未定义）

| 字符 | 父类别 | LLM 标注 |
|------|--------|----------|
| 丘 | mountain | mountain_plateau |
| 坜 | mountain | mountain_valley |
| 垄 | mountain | mountain_ridge |
| 塝 | mountain | mountain_slope |
| 屹 | mountain | mountain_rock |
| 屺 | mountain | mountain_rock |
| 岑 | mountain | mountain_peak |
| 岔 | mountain | mountain_valley |
| 岫 | mountain | mountain_valley |
| 峤 | mountain | mountain_peak |
| 峻 | mountain | mountain_peak |
| 崇 | mountain | mountain_peak |
| 水 | water | water_stream |
| 洪 | water | water_river |
| 浪 | water | water_shore |
| 淤 | water | water_river |
| 潮 | water | water_bay |
| 陂 | mountain | mountain_slope |

---

## 仅 v3 标注的字符（LLM 未标注）

| 字符 | 父类别 | v3 标注 |
|------|--------|----------|
| 一 | number | number_small |
| 七 | number | number_large |
| 三 | number | number_small |
| 九 | number | number_large |
| 二 | number | number_small |
| 五 | number | number_small |
| 井 | water | water_spring |
| 亭 | infrastructure | infrastructure_station |
| 仁 | symbolic | symbolic_virtue |
| 今 | unknown | time |
| 低 | direction | direction_vertical |
| 八 | number | number_large |
| 六 | number | number_large |
| 关 | direction | direction_opening |
| 冬 | unknown | time |
| 初 | number | number_ordinal |
| 十 | number | number_large |
| 古 | unknown | time |
| 和 | symbolic | symbolic_peace |
| 喜 | symbolic | symbolic_fortune |
| 四 | number | number_small |
| 圆 | unknown | shape |
| 城 | settlement | settlement_fort |
| 夏 | unknown | time |
| 大 | size | size_large |
| 央 | direction | direction_center |
| 宁 | symbolic | symbolic_peace |
| 宽 | size | size_large |
| 富 | symbolic | symbolic_prosperity |
| 小 | size | size_small |
| 尖 | unknown | shape |
| 岛 | water | water_island |
| 岸 | water | water_shore |
| 巅 | mountain | mountain_peak |
| 川 | water | water_river |
| 巨 | size | size_large |
| 平 | unknown | shape |
| 广 | size | size_large |
| 康 | symbolic | symbolic_peace |
| 廪 | agriculture | agriculture_storage |
| 微 | size | size_small |
| 心 | direction | direction_center |
| 扁 | unknown | shape |
| 新 | unknown | time |
| 方 | unknown | shape |
| 旧 | unknown | time |
| 春 | unknown | time |
| 晚 | unknown | time |
| 智 | symbolic | symbolic_virtue |
| 曲 | unknown | shape |
| 朗 | symbolic | symbolic_light |
| 朝 | unknown | time |
| 森 | vegetation | vegetation_forest |
| 沙 | water | water_beach |
| 泽 | water | water_lake |
| 洼 | water | water_lake |
| 浅 | size | size_short |
| 深 | size | size_long |
| 玉 | symbolic | symbolic_treasure |
| 珍 | symbolic | symbolic_treasure |
| 白 | unknown | color |
| 直 | unknown | shape |
| 短 | size | size_short |
| 礼 | symbolic | symbolic_virtue |
| 秋 | unknown | time |
| 端 | direction | direction_end |
| 笋 | vegetation | vegetation_bamboo |
| 第 | number | number_ordinal |
| 紫 | unknown | color |
| 红 | unknown | color |
| 细 | size | size_small |
| 绿 | unknown | color |
| 耀 | symbolic | symbolic_light |
| 老 | number | number_ordinal |
| 莲 | vegetation | vegetation_flower |
| 菊 | vegetation | vegetation_flower |
| 蓝 | unknown | color |
| 角 | direction | direction_end |
| 贵 | symbolic | symbolic_prosperity |
| 辉 | symbolic | symbolic_light |
| 近 | size | size_short |
| 远 | size | size_long |
| 金 | unknown | color |
| 银 | unknown | color |
| 长 | size | size_long |
| 门 | direction | direction_opening |
| 集 | settlement | settlement_market |
| 青 | unknown | color |
| 鹤 | symbolic | symbolic_animal |
| 鹿 | symbolic | symbolic_animal |
| 麦 | agriculture | agriculture_crop |
| 黑 | unknown | color |
