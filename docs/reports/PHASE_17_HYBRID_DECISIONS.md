# Phase 17: 智能混合决策报告

**生成时间：** 2026-02-25 20:07:09

---

## 决策统计

- **总字符数**：313 个
- **LLM 采用**：7 个字符
- **v3 保留**：71 个字符
- **两者一致**：235 个字符
- **混合规则**：46 条

---

## 关键决策（应用混合规则）

| 字符 | v3 标注 | LLM 标注 | 最终选择 | 来源 | 理由 |
|------|---------|----------|----------|------|------|
| 七 | number_large | number_small | number_large | v3 | 数值大于5应为 large |
| 九 | number_large | number_small | number_large | v3 | 数值大于5应为 large |
| 二 | number_small | number_ordinal | number_small | v3 | 数值小于等于5应为 small |
| 亭 | infrastructure_station | settlement_building | infrastructure_station | v3 | 亭是驿站建筑 |
| 八 | number_large | number_small | number_large | v3 | 数值大于5应为 large |
| 六 | number_large | number_small | number_large | v3 | 数值大于5应为 large |
| 冈 | mountain_slope | mountain_ridge | mountain_slope | v3 | 冈通常指山坡 |
| 前 | direction_horizontal | direction_cardinal | direction_horizontal | v3 | 前后是水平方位 |
| 十 | number_large | number_small | number_large | v3 | 数值大于5应为 large |
| 右 | direction_horizontal | direction_cardinal | direction_horizontal | v3 | 左右是水平方位 |
| 后 | direction_horizontal | direction_end | direction_horizontal | v3 | 前后是水平方位 |
| 圣 | symbolic_virtue | symbolic_religion | symbolic_virtue | v3 | 圣指圣贤美德 |
| 圳 | water_stream | agriculture_irrigation | water_stream | v3 | 圳在广东指水渠 |
| 坎 | mountain_slope | mountain_valley | mountain_slope | v3 | 坎通常指山坡 |
| 坝 | agriculture_irrigation | water_shore | agriculture_irrigation | v3 | 坝主要用于农业水利 |
| 坳 | mountain_slope | mountain_valley | mountain_slope | v3 | 坳通常指山坡凹处 |
| 堂 | symbolic_religion | settlement_building | symbolic_religion | v3 | 堂多指祠堂、庙堂 |
| 堤 | agriculture_irrigation | infrastructure_bridge | agriculture_irrigation | v3 | 堤坝主要用于农业水利 |
| 尖 | shape | mountain_peak | shape | v3 | 尖指形状 |
| 岗 | mountain_slope | mountain_ridge | mountain_slope | v3 | 岗通常指山坡 |
| 岭 | mountain_peak | mountain_ridge | mountain_peak | v3 | 岭通常指山峰 |
| 左 | direction_horizontal | direction_cardinal | direction_horizontal | v3 | 左右是水平方位 |
| 巷 | infrastructure_road | settlement_district | infrastructure_road | v3 | 巷是道路 |
| 平 | shape | symbolic_peace | shape | v3 | 平指形状 |
| 方 | shape | direction_cardinal | shape | v3 | 方指形状 |
| 李 | vegetation_fruit | clan_li | clan_li | LLM | 在村名中更可能是姓氏而非水果 |
| 杨 | vegetation_other | clan_other | clan_other | LLM | 在村名中更可能是姓氏而非植物 |
| 武 | symbolic_virtue | clan_wu | clan_wu | LLM | 在村名中更可能是姓氏而非美德 |
| 浦 | water_bay | water_shore | water_bay | v3 | 浦指水湾 |
| 涧 | water_river | mountain_valley | water_river | v3 | 涧是山间小河 |
| 渠 | agriculture_irrigation | agriculture_irrigation | agriculture_irrigation | LLM | 渠主要用于农业灌溉 |
| 港 | water_port | infrastructure_port | water_port | v3 | 在村名中主要指水运港口 |
| 溪 | water_river | water_stream | water_river | v3 | 溪是小河流 |
| 滘 | water_bay | water_stream | water_bay | v3 | 滘在广东指水湾 |
| 濠 | water_bay | water_stream | water_bay | v3 | 濠指护城河或水湾 |
| 灵 | symbolic_religion | symbolic_fortune | symbolic_religion | v3 | 灵多指神灵 |
| 畔 | agriculture_field | water_shore | agriculture_field | v3 | 畔指田边 |
| 直 | shape | direction_vertical | shape | v3 | 直指形状 |
| 街 | infrastructure_road | settlement_market | infrastructure_road | v3 | 街是道路 |
| 郭 | clan_other | settlement_fort | clan_other | LLM | 在村名中更可能是姓氏而非堡垒 |
| 里 | direction_inside | settlement_district | direction_inside | v3 | 里主要表示方位 |
| 金 | color | symbolic_treasure | color | v3 | 金在村名中多指颜色 |
| 铁 | infrastructure_transport | symbolic_treasure | infrastructure_transport | v3 | 铁多指交通设施 |
| 银 | color | symbolic_treasure | color | v3 | 银在村名中多指颜色 |
| 高 | clan_other | size_large | clan_other | LLM | 在村名中更可能是姓氏而非大小 |
| 黄 | color | clan_huang | clan_huang | LLM | 在村名中更可能是姓氏而非颜色 |

---

## 不一致但未指定规则（默认保留 v3）

| 字符 | v3 标注 | LLM 标注 | 最终选择 |
|------|---------|----------|----------|
| 中 | direction_inside | direction_center | direction_inside |
| 侧 | direction_outside | direction_vertical | direction_outside |
| 关 | direction_opening | settlement_fort | direction_opening |
| 初 | number_ordinal | time | number_ordinal |
| 古 | time | other | time |
| 围 | settlement_district | settlement_fort | settlement_district |
| 场 | agriculture_garden | agriculture_field | agriculture_garden |
| 塆 | settlement_village | mountain_valley | settlement_village |
| 塱 | mountain_plateau | agriculture_field | mountain_plateau |
| 富 | symbolic_prosperity | symbolic_fortune | symbolic_prosperity |
| 屯 | settlement_village | settlement_fort | settlement_village |
| 嶂 | mountain_ridge | mountain_peak | mountain_ridge |
| 广 | size_large | settlement_building | size_large |
| 旁 | direction_outside | direction_center | direction_outside |
| 春 | time | symbolic_prosperity | time |
| 杉 | vegetation_pine | vegetation_other | vegetation_pine |
| 柏 | vegetation_pine | vegetation_other | vegetation_pine |
| 梅 | vegetation_fruit | vegetation_flower | vegetation_fruit |
| 泽 | water_lake | water_pond | water_lake |
| 洼 | water_lake | mountain_valley | water_lake |
| 浅 | size_short | water_stream | size_short |
| 深 | size_long | water_stream | size_long |
| 畲 | agriculture_field | settlement_village | agriculture_field |
| 社 | settlement_group | settlement_village | settlement_group |
| 老 | number_ordinal | clan_other | number_ordinal |
| 蔗 | vegetation_other | agriculture_crop | vegetation_other |
| 谷 | agriculture_crop | mountain_valley | agriculture_crop |
| 贵 | symbolic_prosperity | symbolic_fortune | symbolic_prosperity |
| 边 | direction_outside | direction_end | direction_outside |
| 近 | size_short | direction_center | size_short |
| 远 | size_long | direction_end | size_long |
| 隧 | infrastructure_transport | infrastructure_road | infrastructure_transport |
