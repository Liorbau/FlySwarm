---
name: skill-builder
description: >-
  Author, structure, and validate FlySwarm Agent Skills (SKILL.md) the right way.
  Use when creating a new skill, refactoring or fixing an existing skill, reviewing
  a SKILL.md, or when the user mentions building/authoring a skill. The heart skill
  every other FlySwarm skill is built through: it interviews to a tight spec,
  scaffolds from the project template, applies Anthropic + Cursor authoring
  conventions and FlySwarm house rules, and gates on a mechanical validator.
disable-model-invocation: true
inputs:
  - name: skill_request
    type: string
    required: true
    description: Description of the skill to author, refactor, or review.
outputs:
  - name: skill_path
    type: string
    required: true
    description: Path to the created/updated SKILL.md.
  - name: validation_passed
    type: boolean
    required: true
    description: Whether scripts/validate_skill.py passed for the skill.
  - name: summary
    type: string
    required: true
    description: What the skill does and how it was built.
---

# Skill Builder — the heart of FlySwarm skills

Build every FlySwarm skill **through this skill**: interview to a tight spec,
scaffold from the template, write the body to convention, and pass the validator
before declaring done.

Read [template.md](template.md) when scaffolding. Run `scripts/validate_skill.py`
to gate. Keep this file lean; it is loaded on trigger.

## How skills load (why "lean" matters)

Skills use three-level progressive disclosure — design to it:

1. **Metadata** (`name` + `description`) — *always* in context (~100 words). The
   description is the sole trigger signal, so invest in it.
2. **SKILL.md body** — loaded only when the skill triggers; keep it < 500 lines.
3. **Bundled resources** (`references/`, `scripts/`, `assets/`) — loaded only when
   referenced. Scripts can *execute* without being read into context.

Push anything heavy or rarely-needed down a level instead of bloating the body.

## Workflow

Copy this checklist and track progress:

```
Skill build:
- [ ] Phase 1: Interview to a shared spec
- [ ] Phase 2: Decide structure (single vs multi-file)
- [ ] Phase 3: Scaffold from template.md
- [ ] Phase 4: Write the body (conventions + house rules)
- [ ] Phase 5: Validate (hard gate) + test on real prompts
```

### Phase 1 — Interview to a shared spec

Resolve these one at a time. For each, **recommend an answer** and **explore the
codebase/docs instead of asking** when the answer is discoverable. Ask the user
only when blocked or when the choice is product-significant.

- **Purpose**: the one specific task this skill performs.
- **Trigger scenarios (WHEN)**: concrete phrases/situations that should invoke it,
  plus any **negative triggers** (when *not* to use it). These shape the description.
- **Name**: lowercase/hyphens, `^[a-z0-9-]{1,64}$`, **must equal the directory
  name**, must not contain `anthropic`/`claude`, specific not vague.
- **Location**: project skill at `.claude/skills/<name>/` (FlySwarm default) vs
  personal `~/.cursor/skills/<name>/`. Never write to `~/.cursor/skills-cursor/`.
- **Domain knowledge**: only what the agent doesn't already know.
- **Architecture touch**: does it route work to `packages/contracts|domain|adapters`
  or `config/`? If so, capture the boundary rules it must enforce.
- **Tool needs**: which tools it uses → consider `allowed-tools`/`disallowed-tools`.
- **Verification**: how a run is checked (fixture/test/manual review).
- **Verbatim copy**: if the user gives exact wording, use it **verbatim** — don't
  paraphrase or wrap it in extra headings.

Stop only when the spec is unambiguous.

### Phase 2 — Decide structure

- **Single file** (`SKILL.md` only): default for focused skills.
- **Multi-file**: when the body would exceed ~500 lines or needs heavy detail, move
  it into `references/` (docs), `scripts/` (executables), `assets/` (templates/data).
  Add a table of contents to any reference file over ~300 lines.
- Reference files **one level deep**: a sibling file or one level into
  `references/`, `scripts/`, or `assets/`. No deeper nesting; no backslash paths.

### Phase 3 — Scaffold from template

Create `.claude/skills/<name>/SKILL.md` from [template.md](template.md). Delete the
sections the skill doesn't need (e.g. the boundary table for non-architecture skills).

### Phase 4 — Write the body

Apply all three rule sets.

**Description (the trigger) — get this right first**
- Third person; state **WHAT** it does **and WHEN** to use it.
- **Put the key use case first** (listings truncate long descriptions).
- Be slightly **"pushy"** about when to trigger; list concrete **trigger keywords**
  and **negative triggers**; mention file types if relevant.
- ≤ 1024 chars; **no XML tags** (`<`/`>`); keep frontmatter ~100 words.

**Body authoring**
- **Concise**: assume a smart agent; only add what it doesn't know.
- **Imperative voice** ("Run…", "Map…"), and **explain the why**, not just the what,
  so the agent adapts to edge cases.
- Match **degrees of freedom** to fragility: prose for open tasks, templates for
  preferred patterns, exact scripts for fragile/consistency-critical steps.
- Use workflow **checklists**, output **templates**, and **feedback loops**.
- **Consistent terminology**: one term per concept throughout.
- State whether the agent should **execute** a script or **read** it as reference.

**FlySwarm house rules (enforce in every generated skill)**
- Lives in `.claude/skills/`; non-secret config in `config/`; secrets in `.env`
  (git-ignored) with placeholders mirrored in `.env.example`. Never embed secrets/PII.
- Respect `CLAUDE.md` boundaries: vendors/external services reached only via adapters
  in `packages/adapters`; business/agent code depends on contracts
  (`packages/contracts`) and the canonical domain (`packages/domain`), never on raw
  vendor shapes. Provider/source/storage swaps stay **config-only**.
- Stay within current session scope (`CLAUDE.md` §2) and the selected layer; don't
  scaffold future swarm agents/DBs/live APIs unless explicitly asked.

**Optional frontmatter (use when it helps)**
- `allowed-tools`: pre-approve tools while active; **always scope `Bash`**, e.g.
  `Bash(python:*) Read Grep`. Never bare `Bash`.
- `disallowed-tools`: remove tools from the pool while active (e.g. exclude
  `AskUserQuestion` for an autonomous/background skill).

### Phase 5 — Validate (hard gate) + test

Run the validator and fix everything it reports before finishing:

```bash
python .claude/skills/skill-builder/scripts/validate_skill.py .claude/skills/<name>
```

It checks: frontmatter parses; `name` regex + no reserved words + matches the
directory name; entry file is exactly `SKILL.md`; `description` present, ≤ 1024 chars,
no XML tags (warns on missing WHEN trigger / non-third-person); body ≤ 500 lines;
references resolve and are one level deep (sibling or `references/|scripts/|assets/`);
no Windows paths; skill under a `skills/` dir. **Finish only when it exits clean.**

The validator is mechanical. Also **test on 2–3 realistic prompts**, watch how the
skill triggers and behaves, then tighten the description and prune anything that
didn't help. Capture recurring mistakes back into the skill.

## Anti-patterns

- ❌ Vague names (`helper`, `utils`) or vague/first-person descriptions.
- ❌ Putting "when to use" info only in the body instead of the description.
- ❌ Verbose explanations of things the agent already knows; SKILL.md over 500 lines.
- ❌ Deeply nested references; reference files > 300 lines without a table of contents.
- ❌ Bare `Bash` in `allowed-tools`; time-sensitive instructions; mixed terminology.
- ❌ Embedding secrets/PII or letting a generated skill bypass FlySwarm boundaries.
- ❌ Declaring done before the validator passes.

## Resources

- Fill-in-the-blanks skeleton: [template.md](template.md)
- Mechanical validator: `scripts/validate_skill.py`
- Conventions: Anthropic Agent Skills spec & best-practices; Cursor `create-skill`.
