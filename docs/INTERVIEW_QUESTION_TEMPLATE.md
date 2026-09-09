# Interview question template

> Status: Draft  
> Target level: Beginner / Intermediate / Senior / Staff  
> Applies to: Generic data engineering / Python / SQL / Batch / Streaming / Storage / Platform  
> Source state: Practitioner-derived / Public source verified / Adapted and verified  
> Last reviewed: YYYY-MM

## Using this template

This template is for the standalone interview question banks. It is intentionally
separate from `TOPIC_TEMPLATE.md`, which owns long-form learning material. Source
discovery, question queues, and completion stages are managed by
`INTERVIEW_PREP_WORKFLOW.md`.

The **Interview answer** is the only required answer block. Keep it concise enough
to say aloud in roughly 30–90 seconds. Remove optional blocks that do not improve
the answer. A question bank may link to curriculum guides, but it must not copy a
full guide into the answer.

Restart question numbering at `1` in every topical section. Adapt Python and SQL
examples to the question. State the SQL dialect or processing engine whenever
behavior is not portable.

## Completed question format

````markdown
## Topic name

### 1. Question?

**Interview answer**

Give a direct definition, explain why it matters, and include the main guarantee,
tradeoff, or selection criterion when relevant.

**How it works**

Optionally explain record grain, data ownership, execution plans, laziness,
partitioning, shuffles, event time, consistency, checkpointing, schemas, or other
mechanics hidden by the abstraction.

**Mental walkthrough**

1. Start at the producer, query, job, event, or consumer.
2. Trace validation, state, ownership, partitions, and commit boundaries.
3. Identify success, partial failure, retry, recovery, and downstream effects.

**Example**

```python
# Add the smallest Python example that clarifies the answer.
```

```sql
-- Or add the smallest SQL example; identify its dialect when relevant.
```

**Tradeoffs and pitfalls**

Describe common mistakes, alternatives, scale assumptions, and when the answer
changes.

**Likely follow-ups**

- Add a natural clarification or comparison question.
- Add a production, correctness, failure, scale, governance, or cost scenario.

**Related curriculum**

- Link to a deeper guide, runnable example, test, or recorded piece of evidence.

**Verification note**

- Identify any version-sensitive claim and the primary source/review date.
````

## Example patterns

Use optional examples only when they make the answer easier to explain aloud.

### Concept comparison

Use a decision table when three or more approaches share criteria.

| Requirement | Prefer | Reason | Reconsider when |
| --- | --- | --- | --- |
| Example | Approach | Relevant guarantee | Condition that changes the choice |

### Avoid / Prefer

Place a tempting mistake beside the safer implementation. Name the data error,
operational failure, or scale problem caused by the mistake.

### Failure walkthrough

Use a small duplicate, late event, join explosion, partial write, corrupt file,
schema change, skewed partition, failed retry, or stale consumer to expose the
candidate's mental model.

### Query or execution-plan walkthrough

Ask the candidate to predict results, cardinality, `NULL` behavior, partitions,
shuffle boundaries, or asymptotic cost before giving the answer.

## Quality checklist

- [ ] Question tests a durable concept rather than product trivia
- [ ] Interview answer is direct and speakable in 30–90 seconds
- [ ] Expected level and topic classification are accurate
- [ ] Grain, ownership, or system boundary is explicit when relevant
- [ ] Correctness and failure behavior are addressed
- [ ] Scale assumptions are stated rather than implied
- [ ] Optional example is minimal and technically correct
- [ ] SQL dialect or engine-specific behavior is identified
- [ ] Follow-ups deepen the same concept rather than changing subjects
- [ ] Tradeoffs explain when the answer changes
- [ ] Related learning material is linked when it exists
- [ ] Version-sensitive claims use current primary sources
- [ ] No proprietary interview content or unattributed copied answer is included
