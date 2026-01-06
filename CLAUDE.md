# AI Audit Platform - Workflow-Driven Development Guide

> **Version**: 1.2.0
> **Last Updated**: 2026-01-06
> **Purpose**: Comprehensive workflow guide with concrete tool sequences for Claude Code development

---

## 📋 Table of Contents

1. [How This Guide Works](#how-this-guide-works)
2. [Quick Start Guide](#quick-start-guide)
3. [Core Workflows](#core-workflows)
4. [Subagent Orchestration](#subagent-orchestration)
5. [Global Infrastructure](#global-infrastructure)
6. [MCP Integration](#mcp-integration)
7. [Project Context](#project-context)
8. [Feedback & Improvement](#feedback--improvement)
9. [Emergency Procedures](#emergency-procedures)
10. [Best Practices](#best-practices)

---

## How This Guide Works

### Session Lifecycle & Auto-Loading

**CRITICAL**: This CLAUDE.md file is **automatically loaded** at the start of EVERY session:

```
┌─────────────────────────────────────────┐
│  Session Start (New or Resumed)         │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  CLAUDE.md Auto-Loaded                  │
│  (via system context injection)         │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  Session Initialization Hook            │
│  (reads metrics, git status, etc.)      │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  Ready to Execute Workflows             │
└─────────────────────────────────────────┘
```

**When CLAUDE.md is loaded:**
- ✓ Every new session start
- ✓ When conversation context is summarized (token limit reached)
- ✓ When session is resumed after interruption
- ✓ **NO explicit user request needed** - it's automatic

**What this means:**
- All workflows, slash commands, and best practices are ALWAYS available
- Claude automatically follows these guidelines without being told
- Consistency across all sessions guaranteed

---

### Automatic Tool & Technology Usage

**MCP Servers** (Model Context Protocol):

Claude automatically uses MCP servers **WITHOUT explicit user request** when appropriate:

| MCP Server | Auto-Use Trigger | Purpose |
|------------|------------------|---------|
| **Context7** | Documentation lookup needed | Up-to-date library docs (React, Next.js, etc.) |
| **Greptile** | PR/code review requested | GitHub PR analysis, code review |
| **Playwright** | Browser automation needed | Web scraping, UI testing |

**Example - Automatic MCP Usage**:
```
User: "How do I use React 19's new useActionState hook?"
Claude: [Automatically uses Context7 MCP to get latest React docs]
        [NO need for user to say "use Context7" or "/context7"]
```

**Slash Commands & Skills**:

Claude automatically invokes slash commands/skills when the task matches their purpose:

```
User: "Implement a dashboard feature"
Claude: [Automatically executes /plan-implement-verify workflow]
        [NO need for user to type "/plan-implement-verify"]

User: "Commit my changes"
Claude: [Automatically executes /commit-push-pr]
        [NO need for user to type "/commit-push-pr"]

User: "Review my code quality"
Claude: [Automatically executes /validate-architecture]
        [NO need for user to type "/validate-architecture"]
```

**Auto-Invoked Skills**:

Claude automatically uses skills from three sources:
1. **SuperClaude Skills** (`/sc:*`) - Advanced orchestration and analysis
2. **Installed Plugins** - Official and community plugins
3. **Custom User Skills** - Project-specific workflows

### SuperClaude Skills (Intelligent Orchestration)

| Skill | Auto-Use Trigger | Purpose |
|-------|------------------|---------|
| `/sc:implement` | Feature implementation request | Persona activation for implementation with MCP integration |
| `/sc:analyze` | Code analysis request | Comprehensive quality, security, performance, architecture analysis |
| `/sc:troubleshoot` | Bug/error diagnosis needed | Systematic diagnosis and resolution |
| `/sc:improve` | Code quality improvement | Apply systematic improvements (refactoring, optimization) |
| `/sc:explain` | Code explanation needed | Educational clarity on code/concepts/systems |
| `/sc:design` | Architecture design needed | Design system architecture, APIs, component interfaces |
| `/sc:test` | Testing request | Execute tests with coverage analysis and quality reporting |
| `/sc:research` | Research/investigation needed | Deep web research with adaptive planning |
| `/sc:workflow` | Complex multi-step task | Generate structured implementation workflows |
| `/sc:brainstorm` | Requirements discovery | Interactive Socratic dialogue for requirements |

### Installed Plugin Skills

| Skill | Auto-Use Trigger | Purpose |
|-------|------------------|---------|
| **Code Review & Development** | | |
| `code-review:code-review` | PR review request | Automated code review of pull requests |
| `feature-dev:feature-dev` | Complex feature development | Guided feature development with codebase understanding |
| `validate-architecture` | Before commit or quality check | Deep architecture analysis (OOP, clean code, file size) |
| **Document Generation** | | |
| `document-skills:pdf` | PDF manipulation needed | Extract, create, merge PDFs; fill forms |
| `document-skills:xlsx` | Spreadsheet work needed | Create/edit spreadsheets with formulas, formatting |
| `document-skills:pptx` | Presentation needed | Create/edit PowerPoint presentations |
| `document-skills:doc-coauthoring` | Documentation writing | Structured workflow for co-authoring docs, specs |
| `document-skills:theme-factory` | Styling artifacts | Apply themes to slides, docs, reports, HTML pages |
| **Notion Integration** | | |
| `Notion:notion-search` | Search Notion workspace | Find pages, databases in Notion |
| `Notion:notion-create-page` | Create Notion page | Add new pages to Notion workspace |
| `Notion:notion-create-task` | Create Notion task | Add tasks to Notion tasks database |
| `Notion:notion-database-query` | Query Notion database | Retrieve structured data from Notion databases |
| **Agent & Plugin Development** | | |
| `agent-sdk-dev:new-sdk-app` | Create Agent SDK app | Setup new Claude Agent SDK application (TypeScript/Python) |
| `plugin-dev:create-plugin` | Create plugin | End-to-end plugin creation with component design |
| **LLM & AI Application Development** | | |
| `llm-application-dev:ai-engineer` | LLM application/agent building | Production-ready LLM apps, RAG systems, intelligent agents |
| `llm-application-dev:prompt-engineer` | Prompt optimization needed | Advanced prompting, chain-of-thought, prompt strategies |
| `llm-application-dev:vector-database-engineer` | Vector search/embeddings | Vector databases, semantic search, embeddings optimization |

### Custom User Skills (Project Workflows)

| Skill | Auto-Use Trigger | Purpose |
|-------|------------------|---------|
| **Requirements Discovery** | | |
| `/interview` | **NEW feature OR architecture improvement** | **Deep requirements interview (RUNS FIRST, triggers plan mode)** |
| **Development Workflows** | | |
| `/worktree-setup` | Feature/bugfix start | Create isolated git worktree for parallel development |
| `/plan-implement-verify` | Feature implementation | Full 6-phase development cycle (plan → implement → validate) |
| `/validate-architecture` | Before commit | Architecture validation (unnecessary lines, OOP, file size) |
| `/commit-push-pr` | Ready to commit | Complete git workflow (stage → commit → push → PR) |
| `/subagent-spawn` | Granular task delegation | Launch focused subagent for specific file/module task |
| `/feedback-capture` | After workflow completion | Record metrics for continuous improvement |

**CRITICAL: `/interview` Priority**

The `/interview` skill **MUST run FIRST** for:
- ✓ New feature requests (any feature, regardless of complexity)
- ✓ Architecture improvements or refactoring
- ✓ Complex bug fixes with unclear requirements
- ✓ When user requirements are ambiguous or incomplete

**What `/interview` Does**:
1. **Reads plan file** (if exists) to understand initial context
2. **Conducts deep interview** using AskUserQuestion tool:
   - Technical implementation details (API design, data structures, algorithms)
   - UI/UX design decisions (user flows, visual design, accessibility)
   - Potential concerns and edge cases (error handling, boundary conditions, race conditions)
   - Architecture and design tradeoffs (scalability, maintainability, performance)
3. **Asks non-superficial questions** - goes deep, not obvious/shallow
4. **Continues until complete understanding** - doesn't stop prematurely
5. **Writes comprehensive specification document** - detailed spec with all decisions documented
6. **Enters plan mode** automatically after interview completion

**Interview → Plan → Implement Flow**:
```
User: "Implement a real-time notification system"
  ↓
STEP 1: /interview (AUTOMATIC, FIRST)
  → Ask: "What types of notifications? (push, email, in-app?)"
  → Ask: "How should notifications be prioritized?"
  → Ask: "What happens if user is offline?"
  → Ask: "Should notifications be grouped/batched?"
  → Ask: "What's the expected notification volume per user?"
  → Ask: "How do we handle notification permissions?"
  → ... (continues until complete understanding)
  → Output: comprehensive-notification-spec.md
  ↓
STEP 2: Enter Plan Mode (AUTOMATIC)
  → Use spec to design architecture
  → Break down into 5-8 granular tasks
  → Get user approval
  ↓
STEP 3: /plan-implement-verify
  → Execute implementation with full context
```

**Why Interview First?**
- ❌ **Without interview**: Assumptions, missing requirements, rework
- ✓ **With interview**: Clear requirements, informed decisions, correct implementation first time

**Example Questions from `/interview`**:

```
BAD (superficial):
❌ "Should we add a dashboard?"
❌ "Do you want this to be fast?"
❌ "Should it look good?"

GOOD (deep, technical):
✓ "What metrics are most critical for users to see at-a-glance vs. drill-down?"
✓ "How should we handle data refresh - polling interval, WebSocket, SSE?"
✓ "What's the acceptable latency for real-time updates - <100ms, <1s, <5s?"
✓ "How do we gracefully degrade if the backend is slow/unavailable?"
✓ "What's the data retention policy - how far back should historical data go?"
```

### Skill Selection Logic

**How Claude Chooses**:

```
1. Parse user request
   ↓
2. **FIRST: Check if /interview needed** (CRITICAL)
   - New feature request? → /interview FIRST
   - Architecture improvement? → /interview FIRST
   - Refactoring with unclear scope? → /interview FIRST
   - Requirements ambiguous? → /interview FIRST
   ↓
3. Identify task type:
   - "implement feature" → /interview → plan mode → /plan-implement-verify
   - "review PR" → code-review:code-review
   - "analyze code" → /sc:analyze OR /validate-architecture
   - "fix bug" → /sc:troubleshoot (or /interview if requirements unclear)
   - "create spreadsheet" → document-skills:xlsx
   - "research library" → /sc:research (with Context7 MCP)
   ↓
4. Check context:
   - Is this part of larger workflow? → Use custom workflow skill
   - Is this standalone task? → Use SuperClaude or plugin skill
   ↓
5. Execute skill automatically (no explicit invocation needed)
```

**Priority Order** (when multiple skills match):

**TIER 0 (HIGHEST PRIORITY - Runs BEFORE everything else)**:
- **`/interview`** - Requirements discovery for new features/architecture
  - Triggers automatically for: new features, architecture changes, refactoring
  - **ALWAYS runs before planning or implementation**
  - Outputs: comprehensive specification document
  - Action: Enters plan mode after completion

**TIER 1 (Custom User Skills)** - Project-specific workflows:
- **`/plan-implement-verify`** - Full development cycle (after /interview)
- **`/worktree-setup`** - Git worktree creation
- **`/validate-architecture`** - Architecture validation
- **`/commit-push-pr`** - Git workflow automation

**TIER 2 (SuperClaude Skills)** - Intelligent orchestration:
- `/sc:implement`, `/sc:design`, `/sc:analyze`, `/sc:research`, etc.

**TIER 3 (Plugin Skills)** - Specialized capabilities:
- `code-review:code-review`, `document-skills:*`, `llm-application-dev:*`, etc.

**Example Automatic Selection**:

```
User: "Implement a dashboard with metrics visualization"
→ STEP 1: /interview (TIER 0 - runs FIRST)
   → Deep questions about metrics, refresh rates, user workflows, etc.
   → Output: dashboard-spec.md
→ STEP 2: Enter plan mode automatically
→ STEP 3: /plan-implement-verify (TIER 1)
   → Within workflow: Uses /sc:design for architecture, /sc:implement for code

User: "Refactor authentication system for better scalability"
→ STEP 1: /interview (TIER 0 - architecture improvement)
   → Questions about current bottlenecks, scale requirements, auth patterns
   → Output: auth-refactor-spec.md
→ STEP 2: Enter plan mode
→ STEP 3: Execute refactoring workflow

User: "Review the PR for authentication changes"
→ Auto-selects: code-review:code-review (TIER 3 plugin)
→ No interview needed (not new feature, just review)

User: "Analyze this component for performance issues"
→ Auto-selects: /sc:analyze (TIER 2 SuperClaude)
→ May also use: /validate-architecture for architecture issues
→ No interview needed (analysis task, not implementation)

User: "Create a report spreadsheet with sales data"
→ Auto-selects: document-skills:xlsx (TIER 3 plugin)
→ No interview needed (straightforward document generation)

User: "Research best practices for React Server Components"
→ Auto-selects: /sc:research (TIER 2 SuperClaude)
→ Auto-uses: Context7 MCP for documentation
→ No interview needed (research task, not implementation)

User: "Build a RAG system with vector search"
→ STEP 1: /interview (TIER 0 - new feature)
   → Questions about data sources, embedding models, retrieval strategy
   → Output: rag-system-spec.md
→ STEP 2: Enter plan mode
→ STEP 3: llm-application-dev:ai-engineer (TIER 3 plugin)
   → Auto-uses: llm-application-dev:vector-database-engineer
   → Auto-uses: langchain-docs MCP for documentation
→ Result: Complete RAG implementation

User: "Fix login bug - users can't sign in"
→ Auto-selects: /sc:troubleshoot (TIER 2 SuperClaude)
→ No interview needed (clear bug fix, not new feature)

User: "Fix authentication - it's not working properly but unclear why"
→ STEP 1: /interview (TIER 0 - unclear requirements)
   → Questions about symptoms, expected behavior, edge cases
   → Output: auth-bug-spec.md
→ STEP 2: /sc:troubleshoot with full context
```

**Override Behavior**:
If you want to disable automatic invocation for a specific task, explicitly say:
- "Don't use any slash commands, just do X manually"
- "Skip the normal workflow and directly Y"

---

### Subagent Parallel Execution Mechanics

**HOW Parallel Execution Works:**

```
┌─────────────────────────────────────────────────────────────┐
│  Main Agent (You)                                           │
│  Task: "Implement dashboard feature"                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  Spawn ALL Subagents in SINGLE Message (Parallel Launch)   │
│  ───────────────────────────────────────────────────────────│
│  Task tool call #1: "Create types in src/app/types/..."    │
│  Task tool call #2: "Create component in src/app/..."      │
│  Task tool call #3: "Create hooks in src/app/hooks/..."    │
│  Task tool call #4: "Add mock data in src/app/data/..."    │
│  Task tool call #5: "Update App.tsx routing..."            │
│  [ALL 5 calls in ONE message - NOT sequential messages]    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  Claude Code Orchestrator                                   │
│  Launches 5 subagents SIMULTANEOUSLY in background          │
└─┬──────┬──────┬──────┬──────┬────────────────────────────┘
  │      │      │      │      │
  ▼      ▼      ▼      ▼      ▼
┌───┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐
│ 1 │  │ 2 │  │ 3 │  │ 4 │  │ 5 │  ← Subagents (separate processes)
└─┬─┘  └─┬─┘  └─┬─┘  └─┬─┘  └─┬─┘
  │      │      │      │      │     ← Each runs independently
  │      │      │      │      │     ← Each has PostToolUse validation
  │      │      │      │      │     ← Total time = MAX(duration of slowest)
  ▼      ▼      ▼      ▼      ▼
Done   Done   Done   Done   Done
  │      │      │      │      │
  └──────┴──────┴──────┴──────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  Main Agent Receives ALL Results                            │
│  Duration: ~15 min (not 5×15min = 75min!)                  │
└─────────────────────────────────────────────────────────────┘
```

**Key Mechanisms:**

1. **Single Message Launch** (CRITICAL):
   ```
   ✓ CORRECT (Parallel):
   [Message with 5 Task tool calls] → All 5 run simultaneously

   ✗ WRONG (Sequential):
   [Message with Task #1] → wait → [Message with Task #2] → wait...
   ```

2. **Background Execution**:
   - Each subagent runs in a separate process/thread
   - Main agent doesn't wait sequentially
   - Total time = duration of the SLOWEST subagent (not sum of all)

3. **run_in_background: true** (Optional):
   - Can explicitly set `run_in_background: true` on Task tool
   - Use `TaskOutput` to retrieve results later
   - Useful for very long-running tasks (>30 min)

4. **No Dependencies Between Subagents**:
   - Each subagent must work independently
   - No subagent should depend on another's output
   - If dependencies exist, run sequentially instead

---

## Quick Start Guide

### New Session Initialization

**EVERY session starts in plan mode** unless explicitly instructed otherwise.

```bash
# 1. Check git status
git status

# 2. Review active worktrees (if any)
git worktree list

# 3. Review recent workflow performance
cat ~/.claude/metrics/workflow-success.json | jq '.overallSuccessRate'

# 4. Check for improvement suggestions
cat ~/.claude/metrics/improvement-suggestions.md
```

### Essential Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| **`/interview`** | **Deep requirements discovery** | **FIRST for new features/architecture (automatic)** |
| `/worktree-setup [name]` | Create feature worktree | Start of any feature/bugfix |
| `/plan-implement-verify` | Full feature cycle | Feature implementation (after interview) |
| `/validate-architecture` | Check code quality | Before committing |
| `/commit-push-pr` | Complete git workflow | After validation passes |
| `/feedback-capture` | Record metrics | End of workflow |

### Default Development Flow (New Features)

```
Interview → Plan → Worktree → Implement (Subagents) → Validate → Commit-Push-PR → Feedback
    ↓        ↓         ↓            ↓                    ↓              ↓              ↓
  Deep    Think    Create     Parallel Execution   PostToolUse    Git Workflow   Metrics
Questions  Mode    Branch      (5-8 subagents)      Validation     Automation    Collection
  + Spec
```

### Simplified Flow (Bug Fixes / Simple Tasks)

```
Plan → Worktree → Implement → Validate → Commit-Push-PR → Feedback
  ↓         ↓            ↓         ↓              ↓              ↓
Think    Create      Execute  PostToolUse    Git Workflow   Metrics
Mode    Branch                Validation     Automation    Collection
```

---

## Core Workflows

### WORKFLOW 1: Feature Implementation (Plan-Implement-Verify)

**Trigger**: New feature request
**Duration**: 30-60 minutes
**Success Rate**: Target 90%+
**Command**: `/plan-implement-verify`

#### Phase 1: Planning (10-15 min)

**Tool Sequence**:
```
1. Grep: Search for similar components/patterns
   → pattern: related component names, type definitions
   → scope: src/app/components/, src/app/types/

2. Read: Examine 3-5 reference files
   → files: similar components, integration points, type definitions
   → goal: understand existing patterns

3. Serena: get_symbols_overview (if available)
   → file: reference component
   → depth: 1 (get methods/structure)

4. Think: Design solution architecture
   → considerations:
     - Component structure (composition pattern preferred)
     - Type definitions needed
     - Integration with existing code
     - State management approach
     - Data flow patterns

5. Break down into 5-8 granular tasks
   → each task: <15 minutes, single file/module
   → example tasks:
     1. Define TypeScript interfaces
     2. Create main component structure
     3. Implement business logic hooks
     4. Create sub-components
     5. Add mock data integration
     6. Update routing/navigation
     7. Add styling
     8. Integration testing

6. AskUserQuestion: Get approval on approach
```

#### Phase 2: Worktree Setup (2-3 min)

**Tool Sequence**:
```bash
# Command: /worktree-setup [feature-name]

1. Bash: Ensure clean main branch
   → cd /Users/jaewookim/Desktop/Personal\ Coding/AI\ Audit
   → git checkout main
   → git pull origin main

2. Bash: Create feature worktree
   → git worktree add worktrees/feature-[name] -b feature/[name]

3. Bash: Navigate to worktree
   → cd worktrees/feature-[name]

4. Bash: Verify setup
   → git worktree list
   → git status
```

#### Phase 3: Parallel Implementation (20-40 min)

**Subagent Orchestration** (SPAWN ALL IN PARALLEL):

```
Main Agent: Architecture oversight
├─ Subagent 1: Type Definitions
│  Task: "Create TypeScript interfaces for [feature] in src/app/types/[feature].ts"
│  Expected: Interface definitions with proper exports
│  PostToolUse: Type check validation
│  Duration: 5-10 min
│
├─ Subagent 2: Main Component
│  Task: "Create [FeatureName].tsx in src/app/components/[feature]/ with props and structure"
│  Expected: React component with TypeScript props
│  PostToolUse: Component syntax validation
│  Duration: 10-15 min
│
├─ Subagent 3: Sub-Components
│  Task: "Create sub-components for [feature] ensuring reusability"
│  Expected: Reusable child components
│  PostToolUse: Component validation
│  Duration: 10-15 min
│
├─ Subagent 4: Business Logic
│  Task: "Implement custom hooks for [feature] (use[Feature].ts)"
│  Expected: React hooks with type safety
│  PostToolUse: Logic validation
│  Duration: 10-15 min
│
├─ Subagent 5: Data Integration
│  Task: "Add mock data for [feature] in src/app/data/mock[Feature].ts"
│  Expected: Mock data matching types
│  PostToolUse: Data structure validation
│  Duration: 5-10 min
│
├─ Subagent 6: Integration (Optional)
│  Task: "Update App.tsx routing to include [feature]"
│  Expected: Navigation integration
│  PostToolUse: Integration validation
│  Duration: 5-10 min
│
└─ Subagent 7: Styling (Optional)
   Task: "Add Tailwind styling to [feature] components"
   Expected: Responsive, theme-consistent styling
   PostToolUse: Style validation
   Duration: 5-10 min
```

**Spawn Command**:
```bash
# CRITICAL: Launch ALL subagents in SINGLE message (parallel execution)
/subagent-spawn "Create TypeScript interfaces for [feature]..."
/subagent-spawn "Create [FeatureName].tsx component..."
/subagent-spawn "Create sub-components..."
/subagent-spawn "Implement business logic hooks..."
/subagent-spawn "Add mock data..."
/subagent-spawn "Update App.tsx routing..."
```

#### Phase 4: Integration & Validation (10-15 min)

**Tool Sequence**:
```bash
1. Bash: Type checking
   → cd frontend && npx tsc --noEmit
   → Expected: No type errors

2. Bash: Build validation
   → npm run build
   → Expected: Successful build

3. Bash: Start dev server (manual testing)
   → npm run dev &
   → Action: Test in browser at localhost:5173

4. Manual Checklist:
   - [ ] Component renders without errors
   - [ ] Props typed correctly
   - [ ] State management works
   - [ ] Data flows correctly
   - [ ] Styling matches design system
   - [ ] Responsive on mobile viewport
   - [ ] No console errors in browser
   - [ ] Navigation/routing works

5. Command: /validate-architecture
   → Runs: ~/.claude/hooks/architecture-analyzer.js
   → Checks: Unnecessary lines, OOP principles, file size, code quality
   → Expected: No errors, warnings acceptable

6. Read: Review all changed files
   → Bash: git diff --stat
   → Bash: git diff
   → Verification: All changes intentional
```

#### Phase 5: Commit-Push-PR (5-10 min)

**Tool Sequence**:
```bash
# Command: /commit-push-pr

1. Bash: Stage changes
   → git add -A

2. Create commit message (use template):
   feat: Add [feature] with [key capabilities]

   Detailed explanation:
   - Created [components] with [functionality]
   - Added [types] for type safety
   - Implemented [logic] using [pattern]

   Technical details:
   - Architecture: Composition pattern for reusability
   - Components: [list components]
   - Types: [list types]
   - OOP: Single Responsibility Principle applied

   Testing:
   - Type check: ✓
   - Build: ✓
   - Architecture validation: ✓
   - Manual testing: ✓

   Related:
   - Workflow: plan-implement-verify

   Co-authored-by: Claude Sonnet 4.5 <noreply@anthropic.com>

3. Bash: Commit
   → git commit -m "[paste commit message]"

4. Bash: Push to remote
   → git push -u origin feature/[name]

5. Bash: Create PR (using gh CLI)
   → gh pr create --title "feat: [Feature]" --body "[PR description]"
```

#### Phase 6: Feedback Loop (2-3 min)

**Tool Sequence**:
```bash
# Command: /feedback-capture plan-implement-verify success "notes"

1. Capture metrics
   → Updates: ~/.claude/metrics/workflow-success.json
   → Updates: ~/.claude/metrics/tool-usage.json
   → Duration recorded, success rate updated

2. Analyze for patterns
   → Check: Bottlenecks detected?
   → Check: Auto-update triggers met?
   → Record: Tool usage statistics

3. Generate improvements (if applicable)
   → Updates: ~/.claude/metrics/improvement-suggestions.md
```

---

### WORKFLOW 2: Bug Fix (Fast Track)

**Trigger**: Bug report or error
**Duration**: 10-20 minutes
**Success Rate**: Target 85%+

#### Tool Sequence

```
PHASE 1: Diagnosis (5 min)
──────────────────────────
1. Grep: Find error patterns
   → pattern: error message, stack trace keywords
   → scope: relevant modules

2. Read: Examine relevant files (max 3)
   → files: where error occurs, related functions

3. Bash: Check git history
   → git log --oneline --all --grep="[keyword]" -10
   → goal: find recent related changes

4. Think: Root cause analysis
   → identify: actual cause vs symptom
   → plan: minimal fix required

PHASE 2: Worktree Setup (2 min)
────────────────────────────────
5. Command: /worktree-setup bugfix-[issue-id]
   → creates: worktrees/bugfix-[issue-id]

PHASE 3: Fix Implementation (5-10 min)
───────────────────────────────────────
6. Spawn Subagent 1: Fix primary issue
   → task: specific fix in specific file
   → PostToolUse: Type check + architecture validation

7. Spawn Subagent 2 (optional): Add test/documentation
   → task: prevent regression
   → PostToolUse: Test execution

PHASE 4: Validation (3 min)
───────────────────────────
8. Command: /validate-architecture
   → verify: fix doesn't introduce new issues

9. Manual testing:
   → reproduce: original bug scenario
   → verify: bug is fixed
   → check: no side effects

PHASE 5: Commit-Push-PR (3 min)
────────────────────────────────
10. Command: /commit-push-pr
    → commit type: "fix:"
    → PR description: includes steps to reproduce + fix explanation

PHASE 6: Feedback (1 min)
─────────────────────────
11. Command: /feedback-capture bug-fix success "Issue: [#], Duration: [X]min"
```

---

### WORKFLOW 3: Refactoring (Architecture Improvement)

**Trigger**: Code quality improvement needed
**Duration**: 40-90 minutes
**Success Rate**: Target 80%+

#### Tool Sequence

```
PHASE 1: Analysis (15 min)
──────────────────────────
1. Read: Current implementation
   → files: target files for refactoring

2. Command: /validate-architecture
   → analyze: current issues
   → review: ~/.claude/metrics/architecture-report.json
   → identify: violations of clean code, OOP principles

3. Grep: Find code duplication
   → pattern: repeated code blocks
   → scope: module being refactored

4. Think: Design clean architecture
   → apply: SOLID principles
   → plan: composition over inheritance
   → ensure: no unnecessary lines

5. Break down: refactoring steps
   → task per file/module
   → ensure: each step testable

PHASE 2: Worktree Setup (2 min)
────────────────────────────────
6. Command: /worktree-setup refactor-[area]

PHASE 3: Refactoring (30-60 min)
─────────────────────────────────
7. Spawn multiple subagents (4-8):
   → each: refactor one file/module
   → ensure: extract reusable logic (DRY)
   → apply: proper OOP patterns
   → PostToolUse: validates each change

PHASE 4: Before/After Comparison (10 min)
──────────────────────────────────────────
8. Command: /validate-architecture
   → capture: "before" report
   → compare: improvements
   → verify: issues resolved

9. Bash: Run full test suite
   → ensure: no functionality broken

10. Manual testing:
    → verify: all features still work

PHASE 5: Commit-Push-PR (5 min)
────────────────────────────────
11. Command: /commit-push-pr
    → commit type: "refactor:"
    → PR description: architecture improvements documented

PHASE 6: Feedback (2 min)
─────────────────────────
12. Command: /feedback-capture refactoring success "Improved: [metrics]"
```

---

### WORKFLOW 4: Ralph-Wiggum Loop Prevention

**Trigger**: Long-running task (>10 tool calls without progress)
**Purpose**: Prevent infinite loops and stuck states

#### Auto-Detection

The **ralph-wiggum plugin** automatically detects loops:
- **10+ tool calls** with same pattern
- **Repetitive actions** without progress
- **Escalating retries** on same failure

#### Recovery Sequence

```
STEP 1: Auto-Checkpoint
───────────────────────
→ Ralph-wiggum detects loop
→ Automatically saves current state
→ Pauses execution

STEP 2: Analysis
────────────────
1. Review last 10 tool calls
   → identify: repeating pattern
   → analyze: why stuck

2. Think: Alternative approach
   → question: is task too complex?
   → consider: different strategy
   → evaluate: need to break down further

STEP 3: Decision
────────────────
Option A: Simplify approach
→ reduce scope
→ try different method
→ resume with new strategy

Option B: Delegate to subagent
→ spawn subagent for blocked subtask
→ subagent uses fresh perspective
→ PostToolUse catches issues

Option C: Ask user for clarification
→ AskUserQuestion: explain blocker
→ get: user guidance
→ resume with clarification

STEP 4: Resume
──────────────
→ Apply chosen strategy
→ Monitor for loop recurrence
→ Capture in feedback: bottleneck identified

STEP 5: Feedback
────────────────
→ Record in: ~/.claude/metrics/bottlenecks.json
→ Suggest: workflow improvement if pattern common
```

---

## Subagent Orchestration

### Core Principles

1. **Granular Tasks**: Each subagent = one file/module, <15 min
2. **Parallel Execution**: Launch all subagents in SINGLE message
3. **PostToolUse Validation**: Every subagent change validated automatically
4. **Clear Deliverables**: Exact file path and expected output specified
5. **No Dependencies**: Subagents work independently

### Orchestration Pattern 1: Component Development

```
Main Agent (Oversees architecture)
│
├─ Subagent 1: Types (src/app/types/[feature].ts)
│  ├─ Define interfaces
│  ├─ Export all types
│  └─ PostToolUse: Type check ✓
│
├─ Subagent 2: Main Component (src/app/components/[Feature].tsx)
│  ├─ Component structure
│  ├─ Props with types
│  └─ PostToolUse: Component validation ✓
│
├─ Subagent 3: Sub-Components (src/app/components/[feature]/*)
│  ├─ Reusable children
│  ├─ Composition pattern
│  └─ PostToolUse: Component validation ✓
│
├─ Subagent 4: Logic (src/app/hooks/use[Feature].ts)
│  ├─ Custom React hooks
│  ├─ State management
│  └─ PostToolUse: Logic validation ✓
│
└─ Subagent 5: Data (src/app/data/mock[Feature].ts)
   ├─ Mock data
   ├─ Matches type definitions
   └─ PostToolUse: Data validation ✓
```

### Orchestration Pattern 2: Testing Pipeline

```
Main Agent (Test orchestration)
│
├─ Subagent 1: Unit Tests
│  └─ Individual function tests
│
├─ Subagent 2: Integration Tests
│  └─ Component integration tests
│
├─ Subagent 3: E2E Scenarios
│  └─ User flow tests
│
└─ Subagent 4: Test Documentation
   └─ Test coverage report
```

### Orchestration Pattern 3: Code Quality Enforcement

```
Main Agent (Quality gate validation)
│
├─ Subagent 1: Type Checking
│  └─ npx tsc --noEmit
│
├─ Subagent 2: Lint Validation
│  └─ npx eslint (if configured)
│
├─ Subagent 3: Architecture Analysis
│  └─ ~/.claude/hooks/architecture-analyzer.js
│
└─ Subagent 4: Performance Check
   └─ Bundle size, render performance
```

### Spawn Best Practices

**DO**:
```bash
# ✓ Specific task with file path
/subagent-spawn "Create MetricCard.tsx in src/app/components/dashboard/ with props: metric (DashboardMetric), onClick, className"

# ✓ Clear success criteria
/subagent-spawn "Add 5 sample dashboard metrics to src/app/data/mockDashboard.ts matching DashboardMetric interface"

# ✓ Single responsibility
/subagent-spawn "Fix task status update logic in src/app/hooks/useTaskManager.ts line 45-60"
```

**DON'T**:
```bash
# ✗ Too vague
/subagent-spawn "Improve dashboard"

# ✗ Multiple responsibilities
/subagent-spawn "Create component, add types, integrate with app, and test"

# ✗ No file path
/subagent-spawn "Add some metrics"
```

---

## Global Infrastructure

### PostToolUse Hook

**Location**: `~/.claude/hooks/post-tool-use.sh`
**Purpose**: Automatic validation after every file modification
**Execution**: Auto-triggered by subagents when `strictMode: true`

#### Validation Sequence

```
1. Type Check (if TypeScript)
   → npx tsc --noEmit
   → Exit 1 if errors (strict mode)

2. Build Validation (if skipBuild: false)
   → npm run build
   → Exit 1 if fails (strict mode)

3. Lint Check (if .eslintrc exists)
   → npx eslint
   → Exit 1 if errors (strict mode)

4. Architecture Analysis
   → node ~/.claude/hooks/architecture-analyzer.js
   → Checks:
     * Unnecessary lines
     * File size (<800 lines)
     * Function size (<50 lines)
     * Forbidden patterns (any, console.log, debugger)
     * OOP principles (God classes, public fields)
     * Code duplication
   → Exit 1 if errors (strict mode)

5. Report Generation
   → ~/.claude/metrics/last-validation-report.json
   → ~/.claude/metrics/architecture-report.json (if issues)
```

#### Configuration

**File**: `~/.claude/hooks/hook-config.json`

```json
{
  "skipBuild": false,          // Set true to skip build (faster, less thorough)
  "skipLint": true,            // Set false to enable lint checking
  "strictMode": true,          // Fail on errors (recommended)
  "architectureRules": {
    "maxFileLines": 800,
    "maxFunctionLines": 50,
    "enforceOOP": true,
    "enforceCleanCode": true
  }
}
```

---

### Slash Commands

**Location**: `~/.claude/commands/*.md`
**Purpose**: Reusable workflow automation

| Command | File | Purpose |
|---------|------|---------|
| `/worktree-setup` | `worktree-setup.md` | Create isolated feature worktree |
| `/plan-implement-verify` | `plan-implement-verify.md` | Full feature development cycle |
| `/validate-architecture` | `validate-architecture.md` | Deep code quality analysis |
| `/commit-push-pr` | `commit-push-pr.md` | Complete git workflow |
| `/subagent-spawn` | `subagent-spawn.md` | Launch focused subagent |
| `/feedback-capture` | `feedback-capture.md` | Record workflow metrics |

**Usage**:
```bash
# Direct invocation
/worktree-setup dashboard-metrics

# Nested in workflows
# /plan-implement-verify includes /worktree-setup, /validate-architecture, /commit-push-pr, /feedback-capture
```

---

### Metrics System

**Location**: `~/.claude/metrics/`
**Purpose**: Continuous improvement through feedback loops

#### Files

1. **workflow-success.json**
   - Tracks: success rate, duration, failure points per workflow
   - Updated by: `/feedback-capture`
   - Used for: Identifying reliable vs problematic workflows

2. **tool-usage.json**
   - Tracks: tool usage frequency, duration, success rate
   - Updated by: automatic tool call tracking
   - Used for: Identifying underutilized or overused tools

3. **bottlenecks.json**
   - Tracks: recurring issues, delays, blockers
   - Updated by: failure analysis
   - Used for: Prioritizing workflow improvements

4. **improvement-suggestions.md**
   - Tracks: auto-generated improvement suggestions
   - Updated by: metrics analysis (weekly or every 10 workflows)
   - Used for: Guiding CLAUDE.md updates

#### Auto-Update Triggers

| Trigger | Condition | Action |
|---------|-----------|--------|
| **Failure Pattern** | 3+ workflows fail at same step | Add warning to CLAUDE.md |
| **Unused Tool** | Tool not used in 20+ workflows | Mark as deprecated |
| **New Pattern** | Same approach used 5+ times | Formalize into workflow |
| **Subagent Timeout** | 5+ subagents exceed 15 min | Update task granularity guidance |
| **Architecture Issues** | Same rule violated 3+ times | Add specific rule explanation |

---

## MCP Integration

### Available MCP Servers

The following MCP (Model Context Protocol) servers are available and **automatically used** when appropriate:

**Quick Reference**:
1. **Context7** - General library/framework documentation (React, Next.js, etc.)
2. **Greptile** - GitHub PR review and code analysis
3. **Serena** - Semantic code intelligence (symbol-based navigation)
4. **Sequential Thinking** - Complex problem solving with reasoning chains
5. **LangChain Docs** - LangChain/LangGraph documentation for LLM apps
6. **Playwright** - Browser automation and testing

---

#### 1. Context7 (Documentation Lookup)

**Auto-Use Triggers**:
- User asks about library/framework usage
- Need up-to-date documentation for specific version
- Looking up API reference or examples

**Example Scenarios**:
```
User: "How do I use React Server Components?"
→ Auto-uses: mcp__plugin_context7_context7__query-docs
→ Returns: Latest React docs with examples

User: "What's the syntax for Next.js 15 route handlers?"
→ Auto-uses: mcp__plugin_context7_context7__resolve-library-id + query-docs
→ Returns: Next.js 15 specific documentation
```

**Tool Sequence (Automatic)**:
```
1. mcp__plugin_context7_context7__resolve-library-id
   → Resolves library name to Context7 ID (e.g., "/vercel/next.js")

2. mcp__plugin_context7_context7__query-docs
   → Fetches documentation and code examples
   → Returns: Markdown with syntax, examples, best practices
```

**Manual Override**:
If you don't want Context7 to be used for a specific question, say:
- "Don't look up docs, just use your training knowledge"
- "Answer from memory only"

---

#### 2. Greptile (Code Review & PR Analysis)

**Auto-Use Triggers**:
- User mentions "pull request", "PR", "code review"
- Analyzing GitHub repository code
- Searching for patterns across large codebase

**Example Scenarios**:
```
User: "Review the open PR for the dashboard feature"
→ Auto-uses: mcp__plugin_greptile_greptile__list_pull_requests
→ Auto-uses: mcp__plugin_greptile_greptile__get_merge_request
→ Auto-uses: mcp__plugin_greptile_greptile__list_merge_request_comments
→ Returns: PR summary, comments, review status

User: "What are common issues in Greptile review comments?"
→ Auto-uses: mcp__plugin_greptile_greptile__search_greptile_comments
→ Returns: Pattern analysis of review feedback
```

**Tool Sequence (Automatic)**:
```
1. mcp__plugin_greptile_greptile__list_pull_requests
   → Get list of PRs (by branch, author, or state)

2. mcp__plugin_greptile_greptile__get_merge_request
   → Get detailed PR info (metadata, stats, review analysis)

3. mcp__plugin_greptile_greptile__list_merge_request_comments
   → Get all comments (Greptile reviews + human comments)

4. mcp__plugin_greptile_greptile__trigger_code_review (if needed)
   → Trigger new Greptile review
```

**Custom Context**:
```
5. mcp__plugin_greptile_greptile__list_custom_context
   → Get organization-specific patterns and instructions

6. mcp__plugin_greptile_greptile__create_custom_context
   → Add new custom context (project-specific rules)
```

---

#### 3. Serena (Semantic Code Intelligence)

**Auto-Use Triggers**:
- Exploring codebase structure or understanding code
- Symbol-based operations (find classes, methods, functions)
- Code navigation and dependency analysis
- Refactoring that requires understanding code relationships

**Example Scenarios**:
```
User: "Find all references to UserAuth class"
→ Auto-uses: mcp__serena__find_symbol (name_path_pattern="UserAuth")
→ Auto-uses: mcp__serena__find_referencing_symbols
→ Returns: All locations where UserAuth is used

User: "What methods does the Dashboard component have?"
→ Auto-uses: mcp__serena__get_symbols_overview (depth=1)
→ Returns: Symbol tree with all methods

User: "Rename validateUser to validateUserCredentials"
→ Auto-uses: mcp__serena__rename_symbol
→ Updates: All references throughout codebase
```

**Tool Sequence (Automatic)**:
```
1. mcp__serena__list_dir
   → List files and directories (with recursion)

2. mcp__serena__find_file
   → Find files matching patterns

3. mcp__serena__get_symbols_overview
   → Get high-level symbol tree (classes, methods, functions)

4. mcp__serena__find_symbol
   → Find specific symbols by name path pattern
   → Supports substring matching, depth control

5. mcp__serena__find_referencing_symbols
   → Find all references to a symbol

6. mcp__serena__search_for_pattern
   → Flexible regex search across codebase
```

**Symbolic Editing** (Architecture-Aware):
```
7. mcp__serena__replace_symbol_body
   → Replace entire symbol definition (method, class, function)

8. mcp__serena__insert_after_symbol / insert_before_symbol
   → Insert code at specific symbol locations

9. mcp__serena__rename_symbol
   → Rename symbol throughout entire codebase
```

**Why Serena Over Basic Tools**:
- **Token-efficient**: Read only necessary symbols, not entire files
- **Architecture-aware**: Understands code structure (classes, methods, inheritance)
- **Precise editing**: Symbol-level changes ensure correct placement
- **Dependency tracking**: Find all references automatically

**When to Use Serena vs. Basic Tools**:
```
✓ Use Serena:
- Understanding code structure (classes, methods, functions)
- Finding symbols by name or pattern
- Refactoring (rename, move, extract)
- Dependency analysis (what uses this class?)

✓ Use Basic Tools (Read, Grep, Edit):
- Reading non-code files (markdown, JSON, config)
- Simple text search across all file types
- Small edits within a symbol (few lines)
```

---

#### 4. Sequential Thinking (Complex Problem Solving)

**Auto-Use Triggers**:
- Complex multi-step problem requiring deep reasoning
- Debugging tricky issues with multiple hypotheses
- Architectural decisions with trade-offs
- Planning complex features with many unknowns

**Example Scenarios**:
```
User: "Why is my React component re-rendering infinitely?"
→ Auto-uses: mcp__sequential-thinking__sequentialthinking
→ Process:
  Thought 1: Analyze component dependencies
  Thought 2: Check useEffect dependencies array
  Thought 3: Verify state update patterns
  Thought 4: Generate hypothesis (missing dependency)
  Thought 5: Verify hypothesis by reading code
  Thought 6: Confirm root cause
→ Returns: Definitive answer with reasoning chain

User: "Design a scalable architecture for real-time notifications"
→ Auto-uses: Sequential Thinking for multi-faceted analysis
→ Process: Considers WebSockets, SSE, polling, trade-offs, scales
→ Returns: Comprehensive architecture design with justification
```

**How Sequential Thinking Works**:
```
1. Problem presented
   ↓
2. Break down into thoughts (initially estimate 5-10 thoughts)
   ↓
3. For each thought:
   - Analyze current understanding
   - Generate hypothesis
   - Verify hypothesis (may use other tools: Read, Grep, etc.)
   - Revise if hypothesis wrong (thoughtNumber can go beyond initial estimate)
   ↓
4. Branching if needed:
   - Explore alternative approaches
   - Compare trade-offs
   ↓
5. Converge to solution
   ↓
6. Return final answer with full reasoning chain
```

**Key Features**:
- **Adaptive**: Can add more thoughts if problem is harder than expected
- **Self-correcting**: Can revise previous thoughts if wrong
- **Branching**: Can explore multiple approaches in parallel
- **Transparent**: Shows full reasoning chain to user

**When to Use Sequential Thinking**:
```
✓ Use Sequential Thinking:
- Debugging complex issues (root cause unclear)
- Architectural decisions (multiple valid approaches)
- Performance optimization (need to analyze bottlenecks)
- Feature design (many unknowns, need to explore)

✗ Don't Use Sequential Thinking:
- Simple, straightforward tasks
- Tasks with clear single path
- When speed is critical (adds overhead)
```

---

#### 5. LangChain Docs (LLM Framework Documentation)

**Auto-Use Triggers**:
- User asks about LangChain, LangGraph usage
- Building LLM applications, agents, RAG systems
- Need documentation for LangChain ecosystem

**Example Scenarios**:
```
User: "How do I create a LangGraph agent with memory?"
→ Auto-uses: mcp__langchain-docs__list_doc_sources
→ Auto-uses: mcp__langchain-docs__fetch_docs
→ Returns: LangGraph documentation with agent examples

User: "What's the best way to implement RAG with LangChain?"
→ Auto-uses: langchain-docs for RAG documentation
→ Returns: Step-by-step RAG implementation guide

User: "How do I use vector stores in LangChain?"
→ Auto-uses: langchain-docs for vector store docs
→ Returns: Vector store integration examples
```

**Tool Sequence (Automatic)**:
```
1. mcp__langchain-docs__list_doc_sources
   → Get available documentation sources (LangChain, LangGraph)
   → Returns: URLs to llms.txt files

2. mcp__langchain-docs__fetch_docs
   → Fetch documentation from specific URL
   → Returns: Markdown documentation with code examples
```

**Available Documentation**:
- **LangChain**: Core library for LLM applications
  - Chains, agents, memory, callbacks
  - Prompt templates, output parsers
  - Integrations (OpenAI, Anthropic, etc.)
- **LangGraph**: State machines for agent workflows
  - Graph-based agent orchestration
  - Cycles, conditionals, persistence
  - Human-in-the-loop patterns

**Use Cases**:
```
✓ Building chatbots with memory
✓ Creating RAG (Retrieval Augmented Generation) systems
✓ Implementing multi-agent systems
✓ Vector database integration (Pinecone, Weaviate, Chroma)
✓ Prompt engineering and optimization
✓ LLM chains and workflows
```

**Combine with Skills**:
```
User: "Build a RAG system with LangChain"
→ Auto-uses: langchain-docs MCP (get documentation)
→ Auto-uses: llm-application-dev:ai-engineer (implement RAG)
→ Auto-uses: llm-application-dev:vector-database-engineer (setup vector DB)
→ Result: Complete RAG implementation with best practices
```

---

#### 6. Playwright (Browser Automation)

**Auto-Use Triggers**:
- User mentions "browser", "scraping", "web page", "screenshot"
- UI testing or visual verification needed
- Automated form filling or interaction

**Example Scenarios**:
```
User: "Take a screenshot of localhost:5173"
→ Auto-uses: mcp__plugin_playwright_playwright__browser_navigate
→ Auto-uses: mcp__plugin_playwright_playwright__browser_take_screenshot
→ Returns: Screenshot file

User: "Test the login form on the staging site"
→ Auto-uses: browser_navigate → browser_fill_form → browser_click
→ Returns: Test results with screenshots
```

**Tool Sequence (Automatic)**:
```
1. mcp__plugin_playwright_playwright__browser_navigate
   → Navigate to URL

2. mcp__plugin_playwright_playwright__browser_snapshot
   → Capture accessibility snapshot (better than screenshot for actions)

3. mcp__plugin_playwright_playwright__browser_click / browser_fill_form
   → Interact with page elements

4. mcp__plugin_playwright_playwright__browser_take_screenshot
   → Visual verification (PNG/JPEG)

5. mcp__plugin_playwright_playwright__browser_evaluate
   → Execute JavaScript in page context
```

**Advanced Operations**:
```
6. mcp__plugin_playwright_playwright__browser_run_code
   → Execute complex Playwright scripts

7. mcp__plugin_playwright_playwright__browser_network_requests
   → Monitor network traffic

8. mcp__plugin_playwright_playwright__browser_console_messages
   → Capture console logs (errors, warnings, debug)
```

---

### MCP Usage Best Practices

1. **Trust Automatic Selection**:
   - Claude automatically chooses the right MCP server
   - No need to specify "use Context7" or "use Greptile"
   - Override only if automatic selection is wrong

2. **Combine with Other Tools**:
   ```
   Example workflow #1 (Frontend):
   1. Context7: Get latest React docs
   2. Read: Check existing component patterns
   3. Write: Create new component using learned patterns
   4. Playwright: Test component in browser

   Example workflow #2 (LLM Application):
   1. langchain-docs: Get LangGraph documentation
   2. llm-application-dev:ai-engineer: Design agent architecture
   3. llm-application-dev:vector-database-engineer: Setup vector store
   4. llm-application-dev:prompt-engineer: Optimize prompts
   5. Write: Implement RAG system
   6. Test: Verify semantic search accuracy
   ```

3. **MCP + Subagents**:
   - Subagents can use MCP tools independently
   - Example: Subagent 1 uses Context7 for docs while Subagent 2 uses Greptile for PR review

4. **Performance Considerations**:
   - Context7 queries: ~2-5 seconds
   - Greptile queries: ~3-10 seconds (depends on PR size)
   - langchain-docs: ~2-4 seconds (documentation fetch)
   - Playwright: ~5-15 seconds (depends on page complexity)
   - Serena symbol search: ~1-3 seconds (token-efficient)
   - Sequential Thinking: ~10-30 seconds (complex reasoning)
   - Factor into workflow timing estimates

---

### MCP Limitations & Fallbacks

**Context7**:
- Limitation: Only supports libraries indexed by Context7
- Fallback: Use WebSearch for unindexed libraries
- Alternative: Read local node_modules or docs directly

**Greptile**:
- Limitation: Requires GitHub repository connection
- Fallback: Use `gh` CLI via Bash tool
- Alternative: Manual `git log` and `git diff` analysis

**Playwright**:
- Limitation: Requires browser installation
- Fallback: Use `mcp__plugin_playwright_playwright__browser_install`
- Alternative: Manual testing with `npm run dev`

**LangChain Docs**:
- Limitation: Only supports LangChain and LangGraph documentation
- Fallback: Use Context7 for other LLM libraries (OpenAI, Anthropic SDK)
- Alternative: Use WebSearch for general LLM/AI documentation

**Serena**:
- Limitation: Requires LSP-compatible languages (Python, TypeScript, JavaScript, Java, etc.)
- Fallback: Use basic tools (Read, Grep, Edit) for unsupported languages
- Alternative: Read entire files if symbolic navigation not available

**Sequential Thinking**:
- Limitation: Adds overhead (~10-30 seconds) for simple tasks
- Fallback: Skip for straightforward tasks with clear path
- Alternative: Direct implementation for simple requests

---

## Testing Strategy

### Core Principles

**CRITICAL**: Testing is NOT optional. Every feature MUST have:
1. **High test coverage** (target: 80%+ overall, 90%+ for critical paths)
2. **Multiple testing levels** (unit, integration, E2E)
3. **Comprehensive assertions** (not just "it doesn't crash" - verify actual results)
4. **Edge case testing** (boundary conditions, error states, null/undefined)

---

### Testing Pyramid

```
              ╱╲
             ╱ E2E ╲               ← Few (10-20% of tests)
            ╱────────╲                Slow, comprehensive user flows
           ╱──────────╲
          ╱ Integration ╲           ← Moderate (30-40% of tests)
         ╱──────────────╲             Medium speed, component interactions
        ╱────────────────╲
       ╱   Unit Tests     ╲         ← Many (50-60% of tests)
      ╱────────────────────╲          Fast, isolated functions/components
```

---

### 1. Unit Tests (50-60% of tests)

**What to Test**:
- Individual functions (utilities, helpers, hooks)
- Component rendering (props, state changes)
- Business logic (calculations, validations, transformations)

**Test Structure**:
```typescript
describe('calculateMetricScore', () => {
  it('should return 0 for empty data', () => {
    const result = calculateMetricScore([]);
    expect(result).toBe(0);  // ✓ Verify exact result value
  });

  it('should calculate average correctly', () => {
    const result = calculateMetricScore([10, 20, 30]);
    expect(result).toBe(20);  // ✓ Verify exact calculation
  });

  it('should handle negative numbers', () => {
    const result = calculateMetricScore([-10, 10]);
    expect(result).toBe(0);  // ✓ Verify edge case
  });

  it('should throw error for non-numeric input', () => {
    expect(() => calculateMetricScore(['invalid'])).toThrow();  // ✓ Verify error handling
  });
});
```

**BAD Unit Tests** (avoid these):
```typescript
// ✗ Too vague - doesn't verify actual result
it('should work', () => {
  const result = calculateMetricScore([10, 20]);
  expect(result).toBeDefined();  // ✗ Meaningless assertion
});

// ✗ No edge cases
describe('formatDate', () => {
  it('should format date', () => {
    expect(formatDate('2024-01-01')).toBeTruthy();  // ✗ Doesn't verify format
  });
});
```

---

### 2. Integration Tests (30-40% of tests)

**What to Test**:
- Component interactions (parent-child communication)
- State management across components
- Data flow through hooks and context
- API integration (with mocked backend)

**Test Structure**:
```typescript
describe('DashboardMetrics integration', () => {
  it('should fetch metrics and display them correctly', async () => {
    // Setup: Mock API
    const mockMetrics = [
      { id: 1, name: 'Revenue', value: 10000 },
      { id: 2, name: 'Users', value: 500 }
    ];
    vi.spyOn(api, 'fetchMetrics').mockResolvedValue(mockMetrics);

    // Act: Render component
    render(<DashboardMetrics />);

    // Assert: Loading state
    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    // Assert: Data displayed after fetch
    await waitFor(() => {
      expect(screen.getByText('Revenue')).toBeInTheDocument();
      expect(screen.getByText('10000')).toBeInTheDocument();  // ✓ Verify actual values
      expect(screen.getByText('Users')).toBeInTheDocument();
      expect(screen.getByText('500')).toBeInTheDocument();  // ✓ Verify actual values
    });

    // Assert: API called correctly
    expect(api.fetchMetrics).toHaveBeenCalledTimes(1);
  });

  it('should handle API error gracefully', async () => {
    // Setup: Mock API error
    vi.spyOn(api, 'fetchMetrics').mockRejectedValue(new Error('Network error'));

    // Act: Render component
    render(<DashboardMetrics />);

    // Assert: Error message displayed
    await waitFor(() => {
      expect(screen.getByText(/error loading metrics/i)).toBeInTheDocument();
      expect(screen.getByText(/network error/i)).toBeInTheDocument();  // ✓ Verify error details
    });
  });
});
```

---

### 3. E2E Tests (10-20% of tests)

**What to Test**:
- Complete user flows (login → dashboard → action → result)
- Critical business paths (checkout, payment, data submission)
- Cross-page navigation and state persistence
- Real browser interactions (forms, clicks, navigation)

**Test Structure** (using Playwright):
```typescript
test.describe('Complete audit workflow', () => {
  test('should create audit, run analysis, and view results', async ({ page }) => {
    // Step 1: Navigate to app
    await page.goto('http://localhost:5173');

    // Step 2: Create new audit
    await page.click('[data-testid="create-audit-btn"]');
    await page.fill('[data-testid="audit-name"]', 'Security Audit 2024');
    await page.selectOption('[data-testid="audit-type"]', 'security');
    await page.click('[data-testid="submit-audit"]');

    // Assert: Audit created
    await expect(page.locator('[data-testid="audit-list"]')).toContainText('Security Audit 2024');

    // Step 3: Run analysis
    await page.click('[data-testid="run-analysis"]');

    // Assert: Analysis running (progress indicator)
    await expect(page.locator('[data-testid="progress-bar"]')).toBeVisible();

    // Step 4: Wait for completion
    await page.waitForSelector('[data-testid="analysis-complete"]', { timeout: 30000 });

    // Assert: Results displayed with actual values
    const resultsText = await page.locator('[data-testid="results-summary"]').textContent();
    expect(resultsText).toMatch(/\d+ issues found/);  // ✓ Verify result format
    expect(resultsText).toMatch(/\d+ critical/);  // ✓ Verify specific data

    // Step 5: Verify detailed results
    await page.click('[data-testid="view-details"]');
    const issueCount = await page.locator('[data-testid="issue-item"]').count();
    expect(issueCount).toBeGreaterThan(0);  // ✓ Verify actual issues rendered

    // Step 6: Verify export functionality
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="export-results"]');
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/security-audit.*\.pdf/);  // ✓ Verify file
  });
});
```

---

### 4. Coverage Requirements

**Minimum Coverage Targets**:
- **Overall**: 80%+ (lines, statements, branches)
- **Critical paths**: 90%+ (auth, payments, data processing)
- **Utilities/helpers**: 95%+ (pure functions are easy to test)
- **UI components**: 70%+ (focus on behavior, not implementation)

**Coverage Tools**:
```bash
# Frontend (Vitest)
npm run test:coverage

# Backend (pytest)
source venv/bin/activate
pytest --cov=. --cov-report=html

# View coverage report
# Frontend: open coverage/index.html
# Backend: open htmlcov/index.html
```

**Coverage Enforcement** (in PostToolUse hook or CI):
```bash
# Fail if coverage drops below threshold
vitest run --coverage --coverage.branches=80 --coverage.functions=80 --coverage.lines=80
```

---

### 5. Comprehensive Assertions (Not Just "It Works")

**BAD Assertions** (too shallow):
```typescript
// ✗ Doesn't verify actual result
expect(calculateTotal([10, 20])).toBeTruthy();

// ✗ Doesn't verify correct value
expect(formatCurrency(1000)).toBeDefined();

// ✗ Only checks presence, not content
expect(screen.getByTestId('result')).toBeInTheDocument();
```

**GOOD Assertions** (verify actual results):
```typescript
// ✓ Verifies exact calculation
expect(calculateTotal([10, 20, 30])).toBe(60);

// ✓ Verifies correct formatting
expect(formatCurrency(1000)).toBe('$1,000.00');

// ✓ Verifies actual content
expect(screen.getByTestId('result')).toHaveTextContent('Total: $1,000.00');

// ✓ Verifies structure
const result = parseAPIResponse(mockData);
expect(result).toEqual({
  id: 1,
  name: 'Test',
  metrics: expect.arrayContaining([
    expect.objectContaining({ type: 'revenue' })
  ])
});
```

---

### 6. Testing Workflow Integration

**WORKFLOW 1: Feature Implementation** (Updated):

Phase 4 now includes comprehensive testing:

```bash
4. Testing (BEFORE validation):
   a. Write unit tests for new functions/components
      → Target: 90%+ coverage for new code

   b. Write integration tests for component interactions
      → Target: 80%+ coverage for interactions

   c. Run tests: npm run test
      → Expected: All tests pass

   d. Check coverage: npm run test:coverage
      → Expected: Coverage thresholds met

   e. Manual E2E testing in browser:
      → Test complete user flow
      → Verify edge cases
      → Check error handling
      → Verify result values (not just "it works")

5. Validation & Commit (AFTER testing):
   → /validate-architecture
   → /commit-push-pr
```

**Test-First Development** (Recommended):

```
1. Write failing tests (RED)
   → Define expected behavior

2. Implement feature (GREEN)
   → Make tests pass

3. Refactor (REFACTOR)
   → Improve code quality while tests still pass

4. Verify coverage
   → Ensure targets met
```

---

## Development Environment

### Backend: Python Virtual Environment (venv)

**CRITICAL RULE**: **ALWAYS activate venv before running ANY backend code**.

```bash
# Activate venv (REQUIRED before every backend operation)
source venv/bin/activate

# Now you can run backend commands
python manage.py runserver
pytest
pip install -r requirements.txt

# When done (optional, but good practice)
deactivate
```

**Why venv is MANDATORY**:
- ✓ Isolates dependencies (prevents global Python pollution)
- ✓ Ensures correct package versions
- ✓ Avoids conflicts with system Python
- ✓ Reproducible environment across machines

**PostToolUse Hook Enforcement**:
The PostToolUse hook detects backend Python files and FAILS if venv is not active:
```bash
# In post-tool-use.sh
if [[ -f "requirements.txt" ]] && [[ -z "$VIRTUAL_ENV" ]]; then
  echo "ERROR: Backend Python detected but venv not activated!"
  echo "Run: source venv/bin/activate"
  exit 1
fi
```

---

### CRITICAL: Prevent Duplicate Server Processes

**NEVER run multiple instances** of the same server (frontend or backend):

```bash
# ✗ BAD - Multiple frontends
Terminal 1: npm run dev  (port 5173)
Terminal 2: npm run dev  (ERROR: port already in use)

# ✗ BAD - Multiple backends
Terminal 1: python manage.py runserver  (port 8000)
Terminal 2: python manage.py runserver  (ERROR: port already in use)
```

**Before starting server, ALWAYS check if already running**:

```bash
# Check frontend (Vite on port 5173)
lsof -ti:5173

# Check backend (Django on port 8000)
lsof -ti:8000

# If running, kill it first
kill -9 $(lsof -ti:5173)  # Frontend
kill -9 $(lsof -ti:8000)  # Backend
```

**Automated Check** (in worktree-setup or before server start):

```bash
# Frontend pre-start check
if lsof -ti:5173 > /dev/null; then
  echo "WARNING: Frontend already running on port 5173"
  echo "Kill it? (y/n)"
  read -r response
  if [[ "$response" == "y" ]]; then
    kill -9 $(lsof -ti:5173)
    echo "Killed existing frontend process"
  else
    echo "Aborting. Cannot start duplicate server."
    exit 1
  fi
fi

# Backend pre-start check (similar)
if lsof -ti:8000 > /dev/null; then
  echo "WARNING: Backend already running on port 8000"
  # ... same logic
fi
```

**Claude Workflow Integration**:

When executing workflows that involve server startup:

```
STEP 1: Check for existing processes
  → lsof -ti:5173 (frontend)
  → lsof -ti:8000 (backend)

STEP 2: If found, ASK USER before killing
  → "Frontend already running. Kill and restart? (y/n)"

STEP 3: Only proceed if user confirms OR no existing process

STEP 4: Start server
  → npm run dev (frontend)
  → source venv/bin/activate && python manage.py runserver (backend)
```

---

### Development Environment Checklist

**Before ANY backend work**:
- [ ] `source venv/bin/activate` (verify with `echo $VIRTUAL_ENV`)
- [ ] Check backend not already running: `lsof -ti:8000`
- [ ] Verify dependencies installed: `pip list`

**Before ANY frontend work**:
- [ ] Check frontend not already running: `lsof -ti:5173`
- [ ] Verify node_modules installed: `ls node_modules`
- [ ] Check correct Node version: `node -v` (should match .nvmrc if exists)

**Before committing**:
- [ ] All tests pass: `npm run test` (frontend), `pytest` (backend)
- [ ] Coverage thresholds met: `npm run test:coverage`, `pytest --cov`
- [ ] No servers running: Kill all dev servers before commit
- [ ] PostToolUse hook passes (includes architecture validation)

---

## Project Context

### Technology Stack

- **Frontend**: React 18.3.1, Vite, TypeScript
- **UI**: Tailwind CSS v4, shadcn/ui (50+ components)
- **Charts**: Recharts
- **Forms**: React Hook Form
- **Icons**: Lucide React, MUI Icons
- **Styling**: OKLch color system, responsive design

### File Organization

```
frontend/
├── src/
│   ├── app/
│   │   ├── types/          # TypeScript interfaces
│   │   ├── components/     # React components
│   │   ├── data/           # Mock data
│   │   └── App.tsx         # Main app with routing
│   ├── styles/             # Global styles
│   └── main.tsx            # Entry point
├── index.html
├── package.json
├── vite.config.ts
└── tsconfig.json

root/
├── CLAUDE.md               # This file
├── frontend/               # Frontend application
├── worktrees/              # Feature worktrees (created dynamically)
└── backend/                # Placeholder for future
```

### Naming Conventions

- **Components**: PascalCase (e.g., `DashboardMetrics.tsx`)
- **Types**: PascalCase interfaces (e.g., `DashboardMetric`, `Task`)
- **Files**: PascalCase for components, camelCase for utilities
- **Branches**: `feature/[description]`, `bugfix/[issue]`, `refactor/[area]`
- **Commits**: `[type]: Description` (feat, fix, refactor, style, docs, test, chore)

### Code Quality Standards

#### Core Principles

1. **Single Responsibility per Function**
   - Each function does ONE thing and does it well
   - If a function name requires "and" or "or", split it
   - Function should be <50 lines, ideally <30 lines
   - Example:
     ```typescript
     // ✗ BAD - Multiple responsibilities
     function processUserAndSaveToDatabase(user: User) {
       const validated = validateUser(user);
       const hashed = hashPassword(validated.password);
       database.save(hashed);
       sendWelcomeEmail(user.email);
     }

     // ✓ GOOD - Single responsibility
     function processUser(user: User): ProcessedUser {
       const validated = validateUser(user);
       return hashPassword(validated);
     }
     ```

2. **Clarity Over Cleverness**
   - Code should be immediately understandable
   - Prefer explicit over implicit
   - Avoid single-letter variables (except loop indices)
   - Write code for humans, not machines
   - Example:
     ```typescript
     // ✗ BAD - Clever but unclear
     const r = d.filter(x => x.s > 100).map(x => x.n);

     // ✓ GOOD - Clear and readable
     const highValueCustomers = customers
       .filter(customer => customer.sales > 100)
       .map(customer => customer.name);
     ```

3. **Proactive Class Usage**
   - **Use classes for entities with behavior + state**
   - Classes should be generic and reusable
   - Prefer composition over inheritance
   - Apply OOP patterns: Factory, Strategy, Observer, etc.
   - Example:
     ```typescript
     // ✗ BAD - Procedural with scattered logic
     function calculateAuditScore(data: any) {
       let score = 0;
       // 50 lines of calculation logic...
       return score;
     }

     // ✓ GOOD - Generic, reusable class
     class AuditScoreCalculator {
       constructor(private strategy: ScoringStrategy) {}

       calculate(audit: Audit): AuditScore {
         return this.strategy.computeScore(audit);
       }

       setStrategy(strategy: ScoringStrategy): void {
         this.strategy = strategy;
       }
     }
     ```

4. **SOLID Principles** (Strictly Enforced)
   - **S**ingle Responsibility: One reason to change
   - **O**pen/Closed: Open for extension, closed for modification
   - **L**iskov Substitution: Subtypes must be substitutable
   - **I**nterface Segregation: Many specific interfaces > one general
   - **D**ependency Inversion: Depend on abstractions, not concretions

5. **Clean Code Principles**
   - **DRY**: Don't Repeat Yourself (extract reusable logic)
   - **KISS**: Keep It Simple, Stupid (simplest solution that works)
   - **YAGNI**: You Aren't Gonna Need It (no speculative features)

6. **No Unnecessary Lines**
   - Every line serves a purpose
   - Remove: unused imports, commented code, empty lines (max 1 consecutive)
   - Remove: debug statements (console.log, debugger)
   - Remove: redundant comments (code should be self-documenting)

#### Size Constraints (Strictly Enforced)

7. **File Size**: **Max 800 lines** per file
   - Split if larger
   - Extract related functionality into modules
   - Use barrel exports (index.ts) for cleaner imports

8. **Component Size**: Max 300 lines per component
   - Extract sub-components if larger
   - Separate business logic into custom hooks
   - Move complex rendering into separate components

9. **Function Size**: Max 50 lines per function
   - Ideally <30 lines
   - Extract helper functions if larger
   - Use early returns to reduce nesting

10. **Function Complexity**: Max 3 levels of nesting
    - Use early returns/guards
    - Extract nested logic into separate functions
    - Prefer flat code over deeply nested

#### Type Safety (Zero Tolerance)

11. **Strict TypeScript**
    - No `any` types (use `unknown` if type truly unknown)
    - No type assertions without runtime validation
    - Enable `strict: true` in tsconfig.json
    - All function parameters and returns typed
    - Example:
      ```typescript
      // ✗ BAD
      function process(data: any): any {
        return data.value;
      }

      // ✓ GOOD
      function process<T extends { value: string }>(data: T): string {
        return data.value;
      }
      ```

---

## Feedback & Improvement

### Feedback Loop Mechanism

```
┌─────────────────────────────────────┐
│  1. Execute Workflow                │
│     (plan-implement-verify, etc.)   │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  2. Capture Feedback                │
│     /feedback-capture [workflow]... │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  3. Update Metrics                  │
│     (workflow-success.json, etc.)   │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  4. Analyze Patterns                │
│     (weekly or every 10 workflows)  │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  5. Generate Suggestions            │
│     (improvement-suggestions.md)    │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  6. Review & Approve                │
│     (user decision)                 │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  7. Update CLAUDE.md                │
│     (new version with improvements) │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  8. Reset Metrics & Repeat          │
└─────────────────────────────────────┘
```

### Monthly Review Checklist

- [ ] Review `~/.claude/metrics/workflow-success.json` - overall success rates
- [ ] Review `~/.claude/metrics/bottlenecks.json` - prioritize resolutions
- [ ] Review `~/.claude/metrics/improvement-suggestions.md` - approve changes
- [ ] Update CLAUDE.md with approved improvements
- [ ] Archive old metrics to `~/.claude/metrics/archive/[month]/`
- [ ] Reset counters for new measurement cycle

---

## Emergency Procedures

### Git Conflicts

```
1. STOP current workflow
2. Bash: git status
3. Identify conflicted files
4. Option A: Resolve in current worktree
   → Edit conflicted files manually
   → git add [resolved-files]
   → git commit
5. Option B: Create recovery worktree
   → /worktree-setup recovery-[issue]
   → Resolve in clean environment
6. Resume workflow
```

### Build Failures

```
1. Read: Error output carefully
2. Bash: npm run build > /tmp/build-errors.log 2>&1
3. Grep: Search codebase for error-related code
4. Spawn Subagent: Fix specific error
5. PostToolUse: Validates fix
6. Retry: npm run build
7. Verify: Build succeeds
```

### Infinite Loops (Ralph-Wiggum)

```
1. Auto-Checkpoint: Ralph-wiggum saves state
2. Review: Last 10 tool calls
3. Identify: Repeating pattern
4. Decision:
   → Simplify: Reduce task scope
   → Delegate: Spawn subagent with different approach
   → Escalate: AskUserQuestion for guidance
5. Update: ~/.claude/metrics/bottlenecks.json
6. Resume: With new strategy
```

### Type Check Failures

```
1. Bash: npx tsc --noEmit > /tmp/tsc-errors.log 2>&1
2. Read: /tmp/tsc-errors.log
3. Identify: Type errors (interface mismatches, missing types)
4. Spawn Subagent: Fix type definitions
5. PostToolUse: Type check validation
6. Verify: All type errors resolved
```

### Architecture Validation Failures

```
1. Read: ~/.claude/metrics/architecture-report.json
2. Categorize issues:
   → Errors: Must fix before commit
   → Warnings: Should fix, tech debt acceptable short-term
3. Fix errors:
   → Remove console.log, debugger, any types
   → Split large files (>800 lines)
   → Extract reusable functions (DRY)
4. Command: /validate-architecture
5. Verify: Errors resolved
```

---

## Best Practices

### Planning

1. ✓ **Always start in plan mode** unless explicitly told otherwise
2. ✓ **Research before implementing**: Grep similar patterns, Read reference files
3. ✓ **Break down tasks granularly**: 5-8 tasks, each <15 min
4. ✓ **Design before coding**: Think about architecture, OOP patterns, SOLID principles
5. ✓ **Get user approval**: AskUserQuestion before major implementation

### Implementation

1. ✓ **Use worktrees**: Isolate feature work with `/worktree-setup`
2. ✓ **Parallel subagents**: Launch all in SINGLE message for efficiency
3. ✓ **PostToolUse validation**: Trust the hook, it catches issues early
4. ✓ **Incremental testing**: Test components as they're built
5. ✓ **Manual verification**: Always test in browser before committing

### Code Quality

1. ✓ **Single Responsibility**: Each function does ONE thing, <50 lines (ideally <30)
2. ✓ **Clarity over Cleverness**: Write explicit, readable code for humans
3. ✓ **Proactive Class Usage**: Use classes for entities with behavior + state, apply OOP patterns
4. ✓ **SOLID Principles**: Strictly enforce all five principles
5. ✓ **Type Safety**: Strict TypeScript, zero `any` types
6. ✓ **No Unnecessary Lines**: Delete unused code, debug statements, excessive comments
7. ✓ **File Size Limits**: Max 800 lines per file, 300 per component, 50 per function
8. ✓ **Code Reuse**: Extract duplicated logic (DRY), create reusable classes

### Git Workflow

1. ✓ **Atomic commits**: One logical change per commit
2. ✓ **Descriptive messages**: Explain WHY, not just WHAT
3. ✓ **Clean history**: Rebase before pushing to avoid merge commits
4. ✓ **Validate before commit**: `/validate-architecture` passes
5. ✓ **Link issues**: Reference issue numbers in commits and PRs

### Feedback

1. ✓ **Always capture**: Run `/feedback-capture` after every workflow
2. ✓ **Be specific**: Include duration, subagent count, observations
3. ✓ **Review metrics**: Monthly review of success rates and bottlenecks
4. ✓ **Act on suggestions**: Implement approved improvements from metrics analysis
5. ✓ **Iterate**: CLAUDE.md evolves based on real usage

---

## Quick Reference

### Most Used Tool Sequences

**Start Feature**:
```
/worktree-setup [name] → Grep patterns → Read refs → Think design → Spawn subagents → /validate-architecture → /commit-push-pr → /feedback-capture
```

**Fix Bug**:
```
Grep error → Read files → git log → Think fix → /worktree-setup bugfix-[id] → Spawn subagent → /validate-architecture → /commit-push-pr
```

**Refactor**:
```
/validate-architecture → Read report → Think clean architecture → /worktree-setup refactor-[area] → Spawn subagents → /validate-architecture → Compare before/after → /commit-push-pr
```

### Essential File Paths

- **This guide**: `/Users/jaewookim/Desktop/Personal Coding/AI Audit/CLAUDE.md`
- **Hooks**: `~/.claude/hooks/*.sh`, `~/.claude/hooks/*.js`
- **Commands**: `~/.claude/commands/*.md`
- **Metrics**: `~/.claude/metrics/*.json`, `~/.claude/metrics/*.md`
- **Config**: `~/.claude/hooks/hook-config.json`

### Support

**For issues or improvements**:
1. Check Emergency Procedures above
2. Review `~/.claude/metrics/improvement-suggestions.md`
3. Consult global slash commands in `~/.claude/commands/`
4. Update this CLAUDE.md with new learnings

---

**Remember**: This document is LIVING and should evolve based on feedback loops. Trust the metrics, improve continuously, and always start in plan mode. 🚀
