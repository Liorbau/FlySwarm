---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
inputs:
  - name: plan
    type: string
    required: true
    description: The plan, design, or idea to interrogate.
outputs:
  - name: resolved_decisions
    type: array
    required: true
    description: The resolved decision points and their agreed answers.
  - name: summary
    type: string
    required: true
    description: Shared-understanding summary of the final design.
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time.

If a question can be answered by exploring the codebase, explore the codebase instead.
