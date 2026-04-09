# Codex Workflow Guidelines

> Goal: keep the useful parts of the Claude command workflows, but adapt them into a lighter Codex-friendly operating model that improves task completion speed and reliability.

## Background

The current Claude commands under `~/.claude/commands/` are:

- `bugfix.md`
- `full-dev.md`
- `full-dev-design.md`
- `full-dev-impl.md`
- `iterate.md`

These commands are valuable because they encode repeatable development discipline instead of relying on one-off prompting. The main migration question is not whether Codex should have workflows, but how heavy those workflows should be by default.

---

## Part 1: Problems In The Current Claude Command Flows

### 1. Capability dependencies are not stable enough

Some flows assume specific skills or command names exist and are callable everywhere, such as:

- `health`
- `plan-devex-review`
- `/superpowers:brainstorm`

That makes the workflow readable, but fragile. If a skill name changes, does not exist in a given environment, or behaves differently than assumed, the workflow breaks in the middle.

### 2. The default flow is too heavy

The current `full-dev` model chains ideation, review, TDD, QA, shipping, and learning into one default path. This is excellent for large feature work, but too expensive for many normal engineering tasks.

Typical problems:

- small tasks inherit large-process overhead
- users may only want implementation and verification, not release work
- the agent spends time on process that does not always increase task success

### 3. Confirmation points are overused

Several commands require explicit user confirmation at multiple points:

- severity classification
- workflow routing
- review-skill selection
- plan handoff

The intent is good, but too many confirmation gates reduce momentum. The commands also do not always define when the agent should proceed automatically versus stop and wait.

### 4. Scope heuristics are useful but too rigid

Rules like “under 100 changed lines” or “no more than 5 files” are helpful as rough signals, but they are not reliable as hard boundaries.

Examples:

- a 20-line auth change may be high risk
- a 150-line UI cleanup may still be low risk

So the heuristics are directionally useful, but should not be the sole workflow router.

### 5. TDD is treated as universal without exception handling

The commands strongly enforce:

- write failing test first
- confirm fail
- write minimal fix
- confirm pass

This is usually good, but the workflows do not define what to do when:

- the code is legacy and hard to test
- the bug is only reproducible manually
- no test harness exists in the relevant area
- testability needs preparatory refactoring

Without an exception path, the workflow can become blocked instead of helpful.

### 6. Shipping is too tightly coupled to implementation

`ship` appears as a normal closing phase in multiple commands. That couples three separate concerns:

- changing code
- verifying behavior
- creating release artifacts or PRs

In practice, many tasks only need the first two.

### 7. Learning is over-automated

`learn` is valuable when a task reveals reusable patterns, root-cause lessons, or long-term rules. It is not equally valuable for every small change. Making it a standard final phase risks adding noise rather than durable knowledge.

### 8. Documentation requirements are sometimes too heavy

The design-doc and implementation-plan pattern is excellent for complex work. But if applied too broadly, it slows down routine feature work and low-risk changes.

### 9. Failure loops are underspecified

The commands define quality gates like:

- all tests pass
- no high-severity review issues remain
- QA clean enough to continue

But they do not always specify:

- what exact step to return to when a gate fails
- how many times to retry
- when to escalate to the user

### 10. The commands behave more like team SOP than task-local guidance

They are strong as a philosophy and governance layer, but they can be too broad as per-task execution commands. A good execution workflow should help with the current task first, and governance second.

---

## Part 2: Migration Problems When Bringing This To Codex

### 1. Codex does not share Claude’s command model

These Claude files are command-style orchestration prompts. Codex works more naturally with:

- repository instructions such as `AGENTS.md`
- reusable skills
- project-local workflow docs
- plan/tool-assisted execution

So this is not a direct command-port exercise.

### 2. Skill names and capability boundaries differ

Even when the intent is the same, Codex may expose it differently. For example:

- a named Claude skill may not exist in Codex
- a Codex skill may be stricter or broader
- some capabilities are better represented as validation commands, not skills

This means a direct 1:1 mapping is brittle.

### 3. Codex favors autonomous progress by default

Codex is generally better when it:

- makes reasonable assumptions
- keeps moving
- only stops at meaningful decision points

If the Claude command confirmation structure is copied directly, Codex will feel slower and less effective.

### 4. Codex should not default to a full lifecycle for every task

The heavy end-to-end orchestration style is not the best default fit. Codex is stronger when the workflow starts with the narrowest path that can safely solve the task, then upgrades only when needed.

### 5. Release actions should be explicit in Codex

Creating PRs, pushing branches, or deploying should usually happen because the user asked for them, not because the workflow always reaches a final “ship” phase.

### 6. Nested orchestration becomes hard to maintain

If Codex adds a large meta-workflow that then invokes multiple other process skills, the system can become layered and opaque:

- workflow document
- workflow skill
- sub-skills
- tool execution

That makes debugging the process harder than debugging the code.

---

## Part 3: Recommended Codex Workflow Model

The right model for Codex is:

**light by default, heavier only when justified**

In practice:

- keep the workflow mindset
- keep the routing logic
- reduce mandatory steps
- turn heavy phases into conditional phases

### Core principle

Use the shortest verifiable path first, then upgrade process depth only when risk, ambiguity, or scope demands it.

---

## Part 4: Recommended Main Flows For Codex

### 1. `iterate` — default small-change workflow

Use for:

- local improvements
- small feature tweaks
- copy/config/UI adjustments
- low-risk implementation work with known scope

Default flow:

1. understand the requested change
2. inspect affected code and nearby tests
3. add or update the most relevant test when practical
4. implement the smallest correct change
5. run targeted validation
6. broaden validation only if risk warrants it

Upgrade out of `iterate` if:

- the change crosses major module boundaries
- public API contracts change
- new dependencies are required
- architecture choices must be made
- the problem turns out to be root-cause debugging work

### 2. `bugfix` — root-cause-oriented fix workflow

Use for:

- reported bugs
- regressions
- unexpected runtime behavior
- reproducible failures or error reports

Default flow:

1. reproduce or confirm the bug
2. investigate enough to identify root cause
3. write a failing regression test when practical
4. apply the minimal root-cause fix
5. verify the bug is resolved
6. verify adjacent behavior is not broken

Fallback when strict TDD is not practical:

- document why a failing automated test cannot be written first
- use the smallest credible manual or integration reproduction
- still require pre-fix and post-fix verification

### 3. `full-dev-design` — planning workflow for larger work

Use for:

- new features
- larger enhancements
- architecture or API decisions
- UI/UX changes with meaningful product impact

Default flow:

1. clarify goal, scope, and success criteria
2. propose 2-3 approaches with tradeoffs
3. recommend one approach
4. capture the design in a concise document
5. run design/engineering review only where relevant
6. produce an implementation plan

This flow should be used selectively, not for every normal task.

### 4. `full-dev-impl` — execution workflow for planned work

Use for:

- tasks that already have a design or implementation plan
- larger work that benefits from staged execution

Default flow:

1. read the approved plan
2. execute one small task at a time
3. validate each task
4. keep changes incremental
5. do a broader verification pass at the end

This flow should not repeat planning unless implementation reveals a real design issue.

---

## Part 5: What Should Become Conditional Instead Of Default

### 1. Shipping

Only trigger shipping-style actions when the user explicitly wants:

- branch/push/PR creation
- release prep
- deployment

### 2. Learning capture

Only trigger knowledge capture when the task reveals:

- reusable bug patterns
- infrastructure lessons
- new team conventions
- repeated sources of failure worth documenting

### 3. Formal design review

Only trigger design review when:

- the task affects UI/UX meaningfully
- there are multiple solution paths
- product behavior needs alignment before coding

### 4. Full QA

Only trigger heavier QA when:

- the task affects UI
- the user journey is high-value
- the change surface is large enough to justify it

---

## Part 6: Recommended Decision Rules For Codex

Codex should usually stop and ask the user only for these decisions:

1. **Workflow upgrade**
   - Is this still a small change, or should it move to a design/planning flow?

2. **Architecture/API choice**
   - Is a meaningful structural decision required?

3. **Release intent**
   - Should this stop after implementation and verification, or continue into PR/push/release actions?

Everything else should generally proceed automatically with reasonable assumptions.

---

## Part 7: Practical Mapping Advice

Instead of porting the Claude commands as-is, split them across three layers:

### Layer 1: Project policy

Put stable workflow guidance in project docs or `AGENTS.md`, such as:

- when to use `iterate`
- when to escalate to `bugfix`
- when to require design/planning
- when shipping is explicit rather than default

### Layer 2: Reusable execution skills

Represent the recurring workflows as lightweight Codex-compatible skills or standard operating prompts:

- `iterate`
- `bugfix`
- `full-dev-design`
- `full-dev-impl`

Each should define:

- use cases
- default steps
- upgrade signals
- stop conditions
- deliverables

### Layer 3: Concrete validation commands

Replace vague workflow dependencies like `health` with explicit checks, such as:

- targeted tests
- full relevant test suite
- lint
- typecheck
- build
- manual verification commands for the affected surface

This makes the workflow more robust and easier to execute across environments.

---

## Part 8: Bottom-Line Recommendation

Codex should absolutely use workflows, but not as a rigid full-stack ritual for every task.

The recommended operating model is:

- **default:** `iterate`
- **if it is a bug:** switch to `bugfix`
- **if it is a larger or ambiguous feature:** use `full-dev-design`
- **if there is already a plan:** use `full-dev-impl`
- **if release work is requested:** explicitly enter shipping actions
- **if durable lessons emerge:** explicitly capture learning

In short:

**keep the discipline, reduce the ceremony**

That preserves the strengths of the original Claude commands while making the workflow better aligned with how Codex completes real work efficiently.
