# BigDataExample agent guide

## 1. Working with the user

1.1. Number substantive points in commentary and final responses so the user can
refer to a specific number when answering, correcting, or extending a task.

1.2. Use `1.`, `2.`, `3.` for main points and `1.1.`, `1.2.` for nested points.
Keep numbering stable within a response. Number questions and choices separately
when more than one is present. Not for files, but for terminal or conversational responses.

1.3. The goal is thorough progression from beginner data concepts to senior data
engineering, not a quick tool tutorial.

1.4. Prefer acting on clear requests. Ask for clarification only when a missing
choice would materially change the result.

## 2. Repository guide

2.1. `BigDataExample` is a Python- and SQL-first data-engineering curriculum.
Learning material is the current focus; interview-question material is a separate
future workflow.

2.2. Use the root `README.md` to navigate source, SQL, data, tests, notebooks,
scripts, infrastructure, and documentation.

2.3. Documentation responsibilities are:

- `docs/README.md`: curriculum purpose, organization, and learning path.
- `docs/COVERAGE.md`: permanent area/topic inventory and current evidence status.
- `docs/TOPIC_TEMPLATE.md`: required structure for learning guides.
- `docs/INTERVIEW_PREP_WORKFLOW.md`: interview sources, queues, and stage prompts.
- `docs/INTERVIEW_QUESTION_TEMPLATE.md`: structure for standalone interview banks.

## 3. Minimal task routing

3.1. When building a new curriculum area, read:

- `docs/TOPIC_TEMPLATE.md`
- The requested area's inventory in `docs/COVERAGE.md`
- Existing files in the requested area, if any

Use `docs/README.md` only when the task changes curriculum organization, learning
order, or area-level conventions.

3.2. When updating an existing topic, read its guide, its coverage entry, and the
relevant template sections. Inspect adjacent guides only when needed for
prerequisites, terminology, or links.

3.3. For interview-question work, read `docs/INTERVIEW_PREP_WORKFLOW.md` and only
the files required by the requested stage. Capture needs the workflow alone;
Consolidate also needs the completed banks; Complete also needs
`docs/INTERVIEW_QUESTION_TEMPLATE.md` and the relevant completed bank. Do not load
the learning template unless the task needs a curriculum link or deeper concept.

3.4. For executable Python, SQL, data, test, or infrastructure work, use the root
`README.md` and the owning topic guide as the navigation contract.

3.5. Do not read every documentation file by default. Load only the sources routed
above or directly relevant to the requested task.

## 4. General repository rules

4.1. Follow the user's requested scope and the local templates. Do not introduce
new curriculum areas, tools, dependencies, or policies without a task-driven need.

4.2. Preserve unrelated user changes and keep learning material separate from
standalone interview banks.

4.3. Update `docs/COVERAGE.md` when topic scope, artifacts, verification, or status
changes. Record only evidence that actually ran, and identify important evidence
that remains pending.

4.4. Verify changed executable artifacts in proportion to risk and report the
exact result. Use current primary sources for version-sensitive technical claims.

4.5. Repository paths use kebab case. For example, the human title
`01 Big Data and Data Engineering Foundations` maps to
`docs/01-big-data-and-data-engineering-foundations/`.

4.6. Do not hard-wrap Markdown prose. Keep each paragraph, list item, and table row on one source line unless Markdown syntax or meaning requires a deliberate line break; rely on the IDE or editor for visual wrapping. Preserve code blocks and intentional semantic breaks.
