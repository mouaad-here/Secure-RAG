---
name: six-file-context
description: Read the six core context files before starting any unit of work.
---

# Six-File Context Skill

## When to Use
At the start of EVERY session and before EVERY unit execution.

## Files to Read
1. `.ai-context/PROJECT_OVERVIEW.md` — Product purpose, core flows, out-of-scope list
2. `.ai-context/ARCHITECTURE.md` — Tech stack, layer boundaries, invariants
3. `.ai-context/CODE_STANDARDS.md` — TypeScript conventions, file organization, naming
4. `.ai-context/AI_WORKFLOW_RULES.md` — One unit at a time, small steps, no guessing
5. `.ai-context/UI_CONTEXT.md` — Design tokens, color palette, typography, spacing, component patterns
6. `.ai-context/PROGRESS_TRACKER.md` — Current phase, completed units, in-progress units, architecture decisions

## Instructions
Read ALL six files before planning or coding. Update PROGRESS_TRACKER.md after each unit.
