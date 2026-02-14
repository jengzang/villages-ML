# Skill: Numbered Village Normalization (Non-Destructive)

## Skill Name
`numbered_village_normalization`

## Purpose

This skill normalizes villages with trailing Chinese numeral suffixes for statistical aggregation purposes.

This skill must NOT modify the database.

It only affects analytical processing logic.


---

## Problem Description

Some villages are subdivided and named with trailing Chinese numerals:

Examples:

- 东村一村
- 东村二村
- 南岭一
- 南岭二
- 北岗三村

These represent subdivisions of the same base village.


---

## Detection Rules

The system should detect trailing Chinese numerals:

- 一 二 三 四 五 六 七 八 九 十

Possible patterns:

- 村名 + 数字
- 村名 + 数字 + 村

Only detect if numeral appears at the end.


---

## Normalization Rule

For statistical purposes only:

- Remove trailing Chinese numeral suffix
- Aggregate such villages under the same base name

Examples:

- 东村一村 → 东村
- 东村二村 → 东村
- 南岭一 → 南岭

The original database must remain unchanged.


---

## Usage Scope

This normalization applies only to:

- Frequency counting
- Tendency analysis
- Clustering
- Aggregation

It must not affect:

- Database values
- Display names
- Query results


---

## Design Philosophy

This skill prevents artificial inflation of village counts.

It improves:

- Frequency accuracy
- Tendency robustness
- Semantic clustering reliability

It is a statistical-layer normalization, not a data-layer correction.
