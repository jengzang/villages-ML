# Phase 17: LLM 子类别标注验证报告（改进版）
**生成时间：** 2026-02-25 20:05:35
**改进：** 基于 v3_expanded 的完整类别体系（75 个子类别）
---

## 总体统计

- **总字符数**：313 个
- **匹配**：236 个字符
- **不匹配**：77 个字符
- **准确率**：75.4%

---

## 不匹配的字符

| 字符 | LLM 标注 | v3 标注 | 说明 |
|------|----------|---------|------|
| 蔗 | agriculture_crop | vegetation_other | 跨类别 |
| 塱 | agriculture_field | mountain_plateau | 跨类别 |
| 场 | agriculture_field | agriculture_garden | 同类别内 |
| 圳 | agriculture_irrigation | water_stream | 跨类别 |
| 黄 | clan_huang | color | 跨类别 |
| 李 | clan_li | vegetation_fruit | 跨类别 |
| 杨 | clan_other | vegetation_other | 跨类别 |
| 老 | clan_other | number_ordinal | 跨类别 |
| 武 | clan_wu | symbolic_virtue | 跨类别 |
| 前 | direction_cardinal | direction_horizontal | 同类别内 |
| 左 | direction_cardinal | direction_horizontal | 同类别内 |
| 右 | direction_cardinal | direction_horizontal | 同类别内 |
| 方 | direction_cardinal | shape | 跨类别 |
| 中 | direction_center | direction_inside | 同类别内 |
| 旁 | direction_center | direction_outside | 同类别内 |
| 近 | direction_center | size_short | 跨类别 |
| 后 | direction_end | direction_horizontal | 同类别内 |
| 边 | direction_end | direction_outside | 同类别内 |
| 远 | direction_end | size_long | 跨类别 |
| 侧 | direction_vertical | direction_outside | 同类别内 |
| 直 | direction_vertical | shape | 跨类别 |
| 堤 | infrastructure_bridge | agriculture_irrigation | 跨类别 |
| 港 | infrastructure_port | water_port | 跨类别 |
| 隧 | infrastructure_road | infrastructure_transport | 同类别内 |
| 嶂 | mountain_peak | mountain_ridge | 同类别内 |
| 尖 | mountain_peak | shape | 跨类别 |
| 岭 | mountain_ridge | mountain_peak | 同类别内 |
| 岗 | mountain_ridge | mountain_slope | 同类别内 |
| 冈 | mountain_ridge | mountain_slope | 同类别内 |
| 坳 | mountain_valley | mountain_slope | 同类别内 |
| 坎 | mountain_valley | mountain_slope | 同类别内 |
| 谷 | mountain_valley | agriculture_crop | 跨类别 |
| 涧 | mountain_valley | water_river | 跨类别 |
| 洼 | mountain_valley | water_lake | 跨类别 |
| 塆 | mountain_valley | settlement_village | 跨类别 |
| 二 | number_ordinal | number_small | 同类别内 |
| 六 | number_small | number_large | 同类别内 |
| 七 | number_small | number_large | 同类别内 |
| 八 | number_small | number_large | 同类别内 |
| 九 | number_small | number_large | 同类别内 |
| 十 | number_small | number_large | 同类别内 |
| 古 | other | time | 跨类别 |
| 堂 | settlement_building | symbolic_religion | 跨类别 |
| 亭 | settlement_building | infrastructure_station | 跨类别 |
| 广 | settlement_building | size_large | 跨类别 |
| 里 | settlement_district | direction_inside | 跨类别 |
| 巷 | settlement_district | infrastructure_road | 跨类别 |
| 屯 | settlement_fort | settlement_village | 同类别内 |
| 围 | settlement_fort | settlement_district | 同类别内 |
| 关 | settlement_fort | direction_opening | 跨类别 |
| 郭 | settlement_fort | clan_other | 跨类别 |
| 街 | settlement_market | infrastructure_road | 跨类别 |
| 社 | settlement_village | settlement_group | 同类别内 |
| 畲 | settlement_village | agriculture_field | 跨类别 |
| 高 | size_large | clan_other | 跨类别 |
| 灵 | symbolic_fortune | symbolic_religion | 同类别内 |
| 富 | symbolic_fortune | symbolic_prosperity | 同类别内 |
| 贵 | symbolic_fortune | symbolic_prosperity | 同类别内 |
| 平 | symbolic_peace | shape | 跨类别 |
| 春 | symbolic_prosperity | time | 跨类别 |
| 圣 | symbolic_religion | symbolic_virtue | 同类别内 |
| 金 | symbolic_treasure | color | 跨类别 |
| 银 | symbolic_treasure | color | 跨类别 |
| 铁 | symbolic_treasure | infrastructure_transport | 跨类别 |
| 初 | time | number_ordinal | 跨类别 |
| 梅 | vegetation_flower | vegetation_fruit | 同类别内 |
| 柏 | vegetation_other | vegetation_pine | 同类别内 |
| 杉 | vegetation_other | vegetation_pine | 同类别内 |
| 泽 | water_pond | water_lake | 同类别内 |
| 坝 | water_shore | agriculture_irrigation | 跨类别 |
| 浦 | water_shore | water_bay | 同类别内 |
| 畔 | water_shore | agriculture_field | 跨类别 |
| 溪 | water_stream | water_river | 同类别内 |
| 滘 | water_stream | water_bay | 同类别内 |
| 濠 | water_stream | water_bay | 同类别内 |
| 深 | water_stream | size_long | 跨类别 |
| 浅 | water_stream | size_short | 跨类别 |

---

## 按父类别统计准确率

| 父类别 | 总字符数 | 匹配数 | 准确率 |
|--------|----------|--------|--------|
| agriculture | 21 | 15 | 71.4% |
| clan | 32 | 30 | 93.8% |
| color | 10 | 7 | 70.0% |
| direction | 27 | 17 | 63.0% |
| infrastructure | 14 | 9 | 64.3% |
| mountain | 25 | 18 | 72.0% |
| number | 13 | 5 | 38.5% |
| settlement | 21 | 17 | 81.0% |
| shape | 7 | 3 | 42.9% |
| size | 13 | 8 | 61.5% |
| symbolic | 53 | 47 | 88.7% |
| time | 10 | 8 | 80.0% |
| vegetation | 32 | 26 | 81.2% |
| water | 35 | 26 | 74.3% |
