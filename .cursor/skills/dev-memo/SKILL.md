---
name: dev-memo
description: Capture and enforce this project's development memo, including architecture decisions, conventions, known pitfalls, and regression checks. Use when the user mentions memo, conventions, historical decisions, avoiding repeated mistakes, or project standards.
---

# Dev Memo

## Purpose
Keep long-lived project knowledge concise, actionable, and easy for the agent to reuse across sessions.

## Required Workflow
1. Read `DECISIONS.md`, `CONVENTIONS.md`, and `../../../docs/ac_os_core_architecture_manifest_v1_2.yaml` before implementation.
2. List which rules apply to the current task.
3. Implement with those rules as constraints.
4. Run through `CHECKLIST.md` before finalizing.
5. If new stable knowledge appears, update one or more memo files in this skill directory.

## What To Record
- Architecture boundaries and module ownership
- Naming and layering conventions
- API contracts and error-handling expectations
- Recurring bugs, root causes, and proven fixes
- Regression and verification checklists

## What Not To Record
- Temporary chat details
- One-off experiments with no reuse value
- Time-sensitive notes without clear validity windows

## Update Triggers
Update memo files when any of the following happens:
- A shared module or public API changes
- A production or high-severity bug is fixed
- A new dependency or framework pattern is introduced
- A repeated review comment reveals a missing rule

## Output Requirements
When finishing a task that used this skill, include:
1. Which memo rules were applied
2. What memo content was added or changed
3. Any remaining risks or follow-up items

## Additional Resources
- [DECISIONS.md](DECISIONS.md)
- [CONVENTIONS.md](CONVENTIONS.md)
- [CHECKLIST.md](CHECKLIST.md)
- [KNOWN_ISSUES.md](KNOWN_ISSUES.md)
- [AC-OS Manifest v1.2](../../../docs/ac_os_core_architecture_manifest_v1_2.yaml)
