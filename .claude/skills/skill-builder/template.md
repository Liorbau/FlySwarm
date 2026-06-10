# SKILL.md template (FlySwarm)

Copy the block below into `.claude/skills/<name>/SKILL.md` and fill the
`<PLACEHOLDERS>`. Delete any section the skill doesn't need (e.g. the boundary
table for non-architecture skills, or optional frontmatter).

Rules while filling it in:
- `name`: lowercase letters/numbers/hyphens, `^[a-z0-9-]{1,64}$`, **must equal the
  directory name**, must not contain `anthropic`/`claude`, specific (not
  `helper`/`utils`).
- `description`: third person, ≤ 1024 chars, **no XML tags** (`<`/`>`). State
  **WHAT** and **WHEN**, put the key use case first, list trigger phrases (and
  negative triggers). This is the only trigger signal — invest in it.
- Keep `disable-model-invocation: true` unless the skill should auto-invoke from
  ambient context.
- Write the body in **imperative voice** and **explain the why**, not just the what.
- Keep SKILL.md under 500 lines; move heavy detail into `references/`, executables
  into `scripts/`, templates/data into `assets/`; link one level deep. Add a table
  of contents to any reference file over ~300 lines.

```markdown
---
name: <skill-name>
description: >-
  <WHAT this skill does, key use case first, third person.> Use when <WHEN to
  trigger: concrete scenarios and phrases>. Do not use for <negative triggers>.
disable-model-invocation: true
# Optional — uncomment as needed (always scope Bash; never bare Bash):
# allowed-tools: Read Grep Bash(python:*)
# disallowed-tools: AskUserQuestion
---

# <Skill Title>

<One or two sentences: the specific task this skill performs and its goal.>

## House rules

- Non-secret config in `config/`; secrets in `.env` (git-ignored), placeholders in
  `.env.example`. Never commit secrets or PII.
- External services/vendors reached only through adapters in `packages/adapters`;
  depend on contracts (`packages/contracts`) and the canonical domain
  (`packages/domain`), never on raw vendor shapes.
- Provider/source/storage swaps stay config-only. Stay within current session
  scope (see CLAUDE.md).

## Workflow

Copy this checklist and track progress:

\`\`\`
<Skill> progress:
- [ ] Step 1: <first action>
- [ ] Step 2: <next action>
- [ ] Step 3: <verify>
\`\`\`

### Step 1 — <name>
<Imperative instruction. Explain why it matters. Prefer exploring code/docs over
guessing.>

### Step 2 — <name>
<Imperative instruction + reasoning.>

### Step 3 — Verify
<How a run is checked: fixture/test/manual review. State the gate that must pass.>

## Where things live (delete if the skill doesn't touch the architecture)

| Concern | Destination | Notes |
|---|---|---|
| Contract / interface | `packages/contracts/src/` | Protocol + dataclasses, vendor-neutral. |
| Canonical domain objects | `packages/domain/src/` | Entities / value objects. |
| Vendor/adapter implementation | `packages/adapters/src/<area>/` | All vendor-specific code isolated here. |
| Non-secret routing/config | `config/<thing>.yaml` | Selection + tunables, no secrets. |
| Secrets | `.env` (+ `.env.example` placeholder) | Never committed. |

## Anti-patterns

- ❌ <a specific wrong way to do this task>
- ❌ <leaking vendor shapes / embedding secrets / bypassing boundaries>

## Resources (optional)

- <Detailed reference: [references/<topic>.md](references/<topic>.md)>
- <Worked examples: [references/examples.md](references/examples.md)>
```
