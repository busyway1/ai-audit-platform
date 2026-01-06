# AI Audit Platform - Workflow-Driven Development Guide

> **Version**: 2.0.0
> **Last Updated**: 2026-01-06
> **Purpose**: Modular workflow guide with streamlined core principles and external reference documentation

---

## 📋 Table of Contents

1. [🎯 Core Philosophy (READ THIS FIRST)](#-core-philosophy-read-this-first)
2. [How This Guide Works](#how-this-guide-works)
3. [Quick Start Guide](#quick-start-guide)
4. [Subagent Orchestration](#subagent-orchestration)
5. [Global Infrastructure](#global-infrastructure)
6. [Emergency Procedures](#emergency-procedures)
7. [Best Practices](#best-practices)
8. [Quick Reference](#quick-reference)
9. [📚 External References](#-external-references)

---

## 🎯 Core Philosophy (READ THIS FIRST)

### Context Preservation is CRITICAL

**Main conversation context** is precious and limited. To preserve it:
- ✓ **DEFAULT to subagents** for ANY non-trivial work (>5 min)
- ✓ **Offload execution** to subagents, keep only oversight in main context
- ✓ **Main agent role**: Architecture design, orchestration, review
- ✗ **NEVER execute** long implementations directly in main conversation

### Aggressive Parallelization (CPU is NOT a constraint)

**Hardware assumption**: Sufficient CPU for 10+ simultaneous subagents

**Parallel execution rules**:
1. **10+ subagents is NORMAL** for complex features (not excessive)
2. **Launch ALL independent tasks** in SINGLE message
3. **No artificial limits** - use as many subagents as needed
4. **Time = MAX(slowest)** not SUM(all) - exploit this!

**Example**: Feature with 15 independent subtasks
- ✓ Spawn all 15 in parallel → Total time: ~15-30 min
- ✗ Do sequentially → Total time: ~225 min (15 × 15min)
- **Savings**: 87-93% faster!

### Hierarchical Review Process

**Quality gates at every level**:

```
Main Agent (Architecture + Final Review)
   ↓ spawns 10+ subagents
Subagent Layer 1 (Implementation + Initial Validation)
   ↓ each can spawn sub-subagents if needed
Sub-subagent Layer 2 (Granular tasks + Unit validation)
   ↓
PostToolUse Hook (Automatic validation at ALL layers)
```

**Example hierarchy**:
```
Main: Implement dashboard feature
├─ Subagent 1: Types + Type Tests
│  ├─ Sub 1a: Interface definitions
│  └─ Sub 1b: Type unit tests
├─ Subagent 2: Main Component + Component Tests
│  ├─ Sub 2a: Component implementation
│  ├─ Sub 2b: Component unit tests
│  └─ Sub 2c: Component integration tests
├─ Subagent 3-7: Sub-components (5 parallel)
├─ Subagent 8-10: Hooks + Hook Tests (3 parallel)
├─ Subagent 11: Mock Data + Data Tests
├─ Subagent 12: Integration + Routing
├─ Subagent 13: Styling + Responsive Tests
├─ Subagent 14: E2E Tests
└─ Subagent 15: Documentation

Total: 15 parallel subagents (some with sub-subagents)
Time: ~20-30 min (not 15×15min = 225min!)
Main context used: Minimal (only orchestration)
```

### When to NOT Use Subagents (Rare)

**ONLY do directly if ALL conditions met**:
1. Task is trivial (<5 min)
2. Task cannot be parallelized
3. Task requires real-time user interaction (AskUserQuestion)
4. Task is purely conversational/explanatory

**Examples**:
- ✓ Direct: "Explain what this function does" (conversational)
- ✓ Direct: "Add one console.log line" (<5 min)
- ✗ Subagent: "Fix type errors" (use subagent even if seems small)
- ✗ Subagent: "Write tests" (ALWAYS use subagent for testing)

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

### MCP Auto-Use Logic (IF-THEN Pattern Matching)

```
Parse user query
    ↓
IF (query about library OR framework OR API documentation)
   → Auto-use: Context7 MCP
   → Action: resolve-library-id → query-docs
   → Example: "How do I use React 19's useActionState?"
   ↓
ELSE IF (PR review OR code review OR GitHub analysis)
   → Auto-use: Greptile MCP
   → Action: list_pull_requests → get_merge_request → list_merge_request_comments
   → Example: "Review the open PR for authentication changes"
   ↓
ELSE IF (browser|scraping|screenshot|UI testing)
   → Auto-use: Playwright MCP
   → Action: browser_navigate → browser_snapshot → browser_take_screenshot
   → Example: "Take a screenshot of localhost:5173"
   ↓
ELSE IF (LangChain|LangGraph|RAG|agent workflow)
   → Auto-use: langchain-docs MCP
   → Action: list_doc_sources → fetch_docs
   → Example: "How do I create a LangGraph agent with memory?"
   ↓
ELSE IF (semantic code search OR symbol navigation OR refactoring)
   → Auto-use: Serena MCP
   → Action: find_symbol → find_referencing_symbols → replace_symbol_body
   → Example: "Find all references to UserAuth class"
   ↓
ELSE IF (complex problem solving OR debugging OR architectural decisions)
   → Auto-use: Sequential Thinking MCP
   → Action: Multi-step reasoning with hypothesis generation and verification
   → Example: "Why is my React component re-rendering infinitely?"
```

**Example - Automatic MCP Usage**:
```
User: "How do I use React 19's new useActionState hook?"
Claude: [Automatically uses Context7 MCP to get latest React docs]
        [NO need for user to say "use Context7" or "/context7"]
```

**For detailed MCP documentation**, see: [MCP Integration Guide](.claude/docs/MCP-GUIDE.md)

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

### Skill Selection Logic (IF-THEN Execution)

```
Parse user request
    ↓
IF (new feature OR architecture improvement OR unclear refactoring scope)
   → TIER 0: Execute /interview (mandatory first step)
   → Output: Comprehensive specification document
   → Action: Enter plan mode automatically
   ↓
ELSE IF (implement|feature|build) + (component|page|system)
   → TIER 1: Execute /plan-implement-verify (after /interview)
   → Within workflow: Uses /sc:design for architecture, /sc:implement for code
   ↓
ELSE IF (review PR OR code review)
   → TIER 3: Execute code-review:code-review
   → No /interview needed (not new feature)
   ↓
ELSE IF (analyze OR performance OR security)
   → TIER 2: Execute /sc:analyze
   → May also use /validate-architecture
   → No /interview needed (analysis task)
   ↓
ELSE IF (fix|bug|error) + (clear symptoms)
   → TIER 2: Execute /sc:troubleshoot
   → No /interview needed (clear bug fix)
   ↓
ELSE IF (fix|bug) + (unclear root cause)
   → TIER 0: Execute /interview (get symptoms, expected behavior)
   → TIER 2: Execute /sc:troubleshoot with full context
   ↓
ELSE IF (research|investigate|best practices)
   → TIER 2: Execute /sc:research
   → Auto-uses Context7 MCP for documentation
   → No /interview needed (research task)
   ↓
ELSE IF (document generation: spreadsheet|pdf|presentation)
   → TIER 3: Execute document-skills:* (xlsx, pdf, pptx)
   → No /interview needed (straightforward document generation)
   ↓
ELSE IF (LLM application: RAG|agent|vector search)
   → TIER 0: Execute /interview (data sources, architecture, strategy)
   → TIER 3: Execute llm-application-dev:ai-engineer
   → Auto-uses llm-application-dev:vector-database-engineer
   → Auto-uses langchain-docs MCP
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

### External Reference Loading Protocol

**RULE**: Some docs are auto-loaded via hooks, others require manual Read.

#### Auto-Loaded Docs (Already in Context)

The following docs are **automatically injected at session start** via `~/.claude/hooks/pre-session-start.sh`:

1. ✓ **WORKFLOW-1-FEATURE-IMPLEMENTATION.md** (477 lines)
   - When to use: Feature implementation with 10-15 parallel subagents
   - Phases: Planning, Worktree Setup, Parallel Implementation, Validation, Commit-Push-PR, Feedback

2. ✓ **WORKFLOW-2-BUG-FIX.md** (88 lines)
   - When to use: Bug fixes (fast-track 10-20 min resolution)
   - Phases: Diagnosis, Worktree Setup, Fix, Validation, Commit-Push-PR, Feedback

3. ✓ **WORKFLOW-3-REFACTORING.md** (95 lines)
   - When to use: Code quality improvements, architecture refactoring
   - Phases: Analysis, Worktree Setup, Refactoring, Before/After Comparison, Commit-Push-PR, Feedback

4. ✓ **TESTING-GUIDE.md** (325 lines)
   - When to use: Writing tests, checking coverage, test methodology
   - Content: Test pyramid, unit/integration/E2E testing, coverage requirements, assertions

5. ✓ **PROJECT-CONTEXT.md** (189 lines)
   - When to use: Code quality checks, SOLID principles, file size limits, type safety
   - Content: Tech stack, file organization, code quality standards, size constraints

**Total auto-loaded**: 1,174 lines (~4,700 tokens per session)

**Action**: ✓ These docs are ALWAYS available - DO NOT use Read tool for them.

---

#### Context-Sensitive Docs (Auto-Loaded by Pre-Tool-Use Hook)

The following doc is **automatically injected when relevant tool detected** via `~/.claude/hooks/pre-tool-use.sh`:

1. **SETUP.md** (149 lines)
   - **Trigger**: Bash tool with backend keywords (manage.py, pytest, python, venv, pip)
   - **Content**: Python venv activation, server management, port checking
   - **Action**: ✓ Auto-loaded when you use backend tools - no manual Read needed

---

#### Manual Read Required (Context-Dependent)

The following docs are NOT auto-loaded and REQUIRE manual Read:

**1. MCP Integration** (when MCP servers mentioned):
```
IF (user mentions Context7|Greptile|Serena|Playwright|Sequential Thinking|LangChain|MCP)
   → Read(.claude/docs/MCP-GUIDE.md)
   → Content: MCP auto-use triggers, tool sequences, best practices (460 lines)
```

**2. Loop Prevention** (when emergency detected):
```
IF (stuck state|infinite loop|ralph-wiggum triggered|>10 tool calls without progress)
   → Read(.claude/docs/workflows/WORKFLOW-4-LOOP-PREVENTION.md)
   → Content: Recovery sequence, decision tree, resume strategy (88 lines)
```

**3. Templates** (when specific template needed):
```
IF (need commit message format)
   → Read(.claude/prompts/commit-message.md)

IF (need PR description format)
   → Read(.claude/prompts/pr-description.md)

IF (need architecture review checklist)
   → Read(.claude/prompts/architecture-review.md)

IF (need subagent spawn template)
   → Read(.claude/prompts/subagent-spawn.md)

IF (need workflow breakdown template)
   → Read(.claude/prompts/workflow-breakdown.md)
```

---

#### Summary Table

| Doc | Loading Method | When | Manual Read? |
|-----|---------------|------|--------------|
| WORKFLOW-1 | Session-start hook | Every session | ✗ No |
| WORKFLOW-2 | Session-start hook | Every session | ✗ No |
| WORKFLOW-3 | Session-start hook | Every session | ✗ No |
| TESTING-GUIDE | Session-start hook | Every session | ✗ No |
| PROJECT-CONTEXT | Session-start hook | Every session | ✗ No |
| SETUP | Pre-tool-use hook | Backend tool used | ✗ No (auto) |
| MCP-GUIDE | Manual | MCP mentioned | ✓ YES |
| WORKFLOW-4 | Manual | Emergency | ✓ YES |
| Templates | Manual | Template needed | ✓ YES |

---

#### Compliance Checklist

**After Session Start, Verify**:
- [ ] 5 core docs are available (check session-start hook output)
- [ ] You understand all 3 workflows (WORKFLOW-1/2/3)
- [ ] You know test pyramid (TESTING-GUIDE)
- [ ] You know code quality rules (PROJECT-CONTEXT)

**Before Backend Work**:
- [ ] SETUP.md was auto-loaded (check pre-tool-use hook output)
- [ ] venv activation verified
- [ ] No duplicate servers running

**When Context-Dependent Docs Needed**:
- [ ] Manually Read MCP-GUIDE if MCP mentioned
- [ ] Manually Read WORKFLOW-4 if loop detected
- [ ] Manually Read templates if specific format needed

**If ANY checkbox unchecked → Stop and load missing docs**

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

**For detailed workflow documentation**, see: [Workflow Index](.claude/docs/workflows/INDEX.md)

### Simplified Flow (Bug Fixes / Simple Tasks)

```
Plan → Worktree → Implement → Validate → Commit-Push-PR → Feedback
  ↓         ↓            ↓         ↓              ↓              ↓
Think    Create      Execute  PostToolUse    Git Workflow   Metrics
Mode    Branch                Validation     Automation    Collection
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

### Overview

This section provides high-level overview of global infrastructure components.
**For detailed documentation, see**: [Infrastructure Index](.claude/docs/infrastructure/INDEX.md)

### PostToolUse Hook

**Purpose**: Automatic validation after every file modification
**Location**: `~/.claude/hooks/post-tool-use.sh`
**Trigger**: Auto-triggered by subagents when `strictMode: true`

**What it validates**:
1. **Type Check** (if TypeScript)
   - Runs: `npx tsc --noEmit`
   - Exits with error if type errors found

2. **Build Validation** (if skipBuild: false)
   - Runs: `npm run build`
   - Exits with error if build fails

3. **Architecture Analysis** (always)
   - Runs: `node ~/.claude/hooks/architecture-analyzer.js`
   - Checks:
     * Unnecessary lines (console.log, debugger, commented code)
     * File size (<800 lines)
     * Function size (<50 lines)
     * Forbidden patterns (any, public fields in classes)
     * OOP principles (God classes, Single Responsibility)
     * Code duplication (DRY violations)
   - Exits with error if issues found (strict mode)

**Configuration**: `~/.claude/hooks/hook-config.json`

**For full validation sequence and configuration**, see:
[PostToolUse Hook Details](.claude/docs/infrastructure/POST-TOOL-USE.md)

---

### Slash Commands

**Purpose**: Reusable workflow automation
**Location**: `~/.claude/commands/*.md`

**Available commands**:

| Command | Purpose | Phase |
|---------|---------|-------|
| `/worktree-setup` | Create isolated feature worktree | Project setup |
| `/plan-implement-verify` | Full feature development cycle | Implementation |
| `/validate-architecture` | Deep code quality analysis | Quality gate |
| `/commit-push-pr` | Complete git workflow | Deployment |
| `/subagent-spawn` | Launch focused subagent | Orchestration |
| `/feedback-capture` | Record workflow metrics | Feedback loop |

**Usage**:
```bash
# Direct invocation
/worktree-setup dashboard-metrics

# Nested in workflows
# /plan-implement-verify includes /worktree-setup, /validate-architecture, /commit-push-pr, /feedback-capture
```

**For detailed command documentation**, see:
[Slash Commands Reference](.claude/docs/infrastructure/SLASH-COMMANDS.md)

---

### Metrics System

**Purpose**: Continuous improvement through feedback loops
**Location**: `~/.claude/metrics/`

**Key files**:

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

**Auto-Update Triggers**:

| Trigger | Condition | Action |
|---------|-----------|--------|
| **Failure Pattern** | 3+ workflows fail at same step | Add warning to CLAUDE.md |
| **Unused Tool** | Tool not used in 20+ workflows | Mark as deprecated |
| **New Pattern** | Same approach used 5+ times | Formalize into workflow |
| **Subagent Timeout** | 5+ subagents exceed 15 min | Update task granularity guidance |
| **Architecture Issues** | Same rule violated 3+ times | Add specific rule explanation |

**For metrics system details and auto-update triggers**, see:
[Metrics System Details](.claude/docs/infrastructure/METRICS-SYSTEM.md)

---

## Emergency Procedures (IF-THEN Response)

```
Identify emergency type
    ↓
IF (git conflict detected)
   → STOP current workflow
   → Bash: git status
   → Identify conflicted files
   → IF (simple conflict)
      → Option A: Resolve in-place (edit conflicted files, git add, git commit)
   → ELSE IF (complex conflict)
      → Option B: /worktree-setup recovery-[issue] (clean environment)
   → Resume workflow after resolution
   ↓
ELSE IF (build failure)
   → Bash: npm run build > /tmp/build-errors.log 2>&1
   → Read: /tmp/build-errors.log
   → Grep: Search codebase for error pattern
   → Spawn Subagent: Fix specific error
   → PostToolUse: Validates fix
   → Bash: npm run build (retry)
   → Verify: Build succeeds
   ↓
ELSE IF (infinite loop detected by ralph-wiggum)
   → Auto-Checkpoint: Ralph-wiggum saves state
   → Read: WORKFLOW-4-LOOP-PREVENTION.md
   → Review: Last 10 tool calls
   → Identify: Repeating pattern
   → IF (task too complex)
      → Option A: Simplify (reduce scope, try different method)
   → ELSE IF (same approach repeatedly failing)
      → Option B: Spawn subagent (fresh perspective, PostToolUse catches issues)
   → ELSE IF (unclear requirements)
      → Option C: AskUserQuestion (get guidance)
   → Update: ~/.claude/metrics/bottlenecks.json
   → Resume with new strategy
   ↓
ELSE IF (type check failures)
   → Bash: npx tsc --noEmit > /tmp/tsc-errors.log 2>&1
   → Read: /tmp/tsc-errors.log
   → Identify: Type errors (interface mismatches, missing types, `any` usage)
   → Spawn Subagent: Fix type definitions
   → PostToolUse: Type check validation
   → Verify: All errors resolved
   ↓
ELSE IF (architecture validation failures)
   → Read: ~/.claude/metrics/architecture-report.json
   → Categorize issues:
      - Errors: Must fix before commit (console.log, debugger, any types, files >800 lines)
      - Warnings: Should fix, tech debt acceptable short-term
   → Fix errors: Remove debug statements, split large files, extract reusable functions
   → Bash: /validate-architecture (retry)
   → Verify: Errors resolved
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

**For code quality standards**, see: [Project Context](.claude/docs/PROJECT-CONTEXT.md)

### Code Quality

1. ✓ **Single Responsibility**: Each function does ONE thing, <50 lines (ideally <30)
2. ✓ **Clarity over Cleverness**: Write explicit, readable code for humans
3. ✓ **Proactive Class Usage**: Use classes for entities with behavior + state, apply OOP patterns
4. ✓ **SOLID Principles**: Strictly enforce all five principles
5. ✓ **Type Safety**: Strict TypeScript, zero `any` types
6. ✓ **No Unnecessary Lines**: Delete unused code, debug statements, excessive comments
7. ✓ **File Size Limits**: Max 800 lines per file, 300 per component, 50 per function
8. ✓ **Code Reuse**: Extract duplicated logic (DRY), create reusable classes

**For comprehensive quality standards**, see: [Project Context - Code Quality](.claude/docs/PROJECT-CONTEXT.md#code-quality-standards)

### Git Workflow

1. ✓ **Atomic commits**: One logical change per commit
2. ✓ **Descriptive messages**: Explain WHY, not just WHAT
3. ✓ **Clean history**: Rebase before pushing to avoid merge commits
4. ✓ **Validate before commit**: `/validate-architecture` passes
5. ✓ **Link issues**: Reference issue numbers in commits and PRs

**For commit templates**, see: [Commit Message Template](.claude/prompts/commit-message.md)

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
```bash
/worktree-setup [name] → Grep patterns → Read refs → Think design → Spawn subagents → /validate-architecture → /commit-push-pr → /feedback-capture
```
**Detailed guide**: [Workflow 1: Feature Implementation](.claude/docs/workflows/WORKFLOW-1-FEATURE-IMPLEMENTATION.md)

**Fix Bug**:
```bash
Grep error → Read files → git log → Think fix → /worktree-setup bugfix-[id] → Spawn subagent → /validate-architecture → /commit-push-pr
```
**Detailed guide**: [Workflow 2: Bug Fix](.claude/docs/workflows/WORKFLOW-2-BUG-FIX.md)

**Refactor**:
```bash
/validate-architecture → Read report → Think clean architecture → /worktree-setup refactor-[area] → Spawn subagents → /validate-architecture → Compare before/after → /commit-push-pr
```
**Detailed guide**: [Workflow 3: Refactoring](.claude/docs/workflows/WORKFLOW-3-REFACTORING.md)

**Prevent Loops**:
```bash
Ralph-wiggum detects loop → Auto-checkpoint → Analyze pattern → Try alternative → Resume OR Ask user
```
**Detailed guide**: [Workflow 4: Loop Prevention](.claude/docs/workflows/WORKFLOW-4-LOOP-PREVENTION.md)

---

### Essential File Paths

**Core Configuration**:
- This guide: `/Users/jaewookim/Desktop/Personal Coding/AI Audit/CLAUDE.md`
- Documentation index: `.claude/docs/INDEX.md`
- Workflow index: `.claude/docs/workflows/INDEX.md`
- Template index: `.claude/prompts/INDEX.md`

**Global Infrastructure**:
- Hooks: `~/.claude/hooks/*.sh`, `~/.claude/hooks/*.js`
- Commands: `~/.claude/commands/*.md`
- Metrics: `~/.claude/metrics/*.json`, `~/.claude/metrics/*.md`
- Config: `~/.claude/hooks/hook-config.json`

**Project-Local**:
- Frontend: `/Users/jaewookim/Desktop/Personal Coding/AI Audit/frontend/`
- Worktrees: `/Users/jaewookim/Desktop/Personal Coding/AI Audit/worktrees/`
- Backend: `/Users/jaewookim/Desktop/Personal Coding/AI Audit/backend/` (placeholder)

---

### Common References

**Quick Links for Frequent Lookups**:

| Need | Reference |
|------|-----------|
| **Workflow steps** | [Workflow Index](.claude/docs/workflows/INDEX.md) |
| **MCP server usage** | [MCP Integration Guide](.claude/docs/MCP-GUIDE.md) |
| **Testing methodology** | [Testing Strategy](.claude/docs/TESTING-GUIDE.md) |
| **Environment setup** | [Development Environment](.claude/docs/SETUP.md) |
| **Code quality rules** | [Project Context](.claude/docs/PROJECT-CONTEXT.md#code-quality-standards) |
| **Commit format** | [Commit Message Template](.claude/prompts/commit-message.md) |
| **PR format** | [PR Description Template](.claude/prompts/pr-description.md) |
| **Subagent spawning** | [Subagent Spawn Template](.claude/prompts/subagent-spawn.md) |
| **Architecture review** | [Architecture Review Template](.claude/prompts/architecture-review.md) |

**Token Savings**:
- Core CLAUDE.md: ~1,220 lines (reduced from 2,766 lines)
- Reduction: **56% smaller** while preserving ALL content
- External docs: ~1,546 lines (on-demand loading)
- Total preserved: 2,766 lines (no content loss)

---

## 📚 External References

### Core Documentation

- **[Documentation Index](.claude/docs/INDEX.md)** - Central navigation hub
- **[MCP Integration Guide](.claude/docs/MCP-GUIDE.md)** - MCP servers, auto-use triggers, best practices (436 lines)
- **[Testing Strategy](.claude/docs/TESTING-GUIDE.md)** - Test pyramid, coverage requirements, assertions (303 lines)
- **[Development Environment](.claude/docs/SETUP.md)** - Python venv, server management, checklist (131 lines)
- **[Project Context](.claude/docs/PROJECT-CONTEXT.md)** - Tech stack, file organization, code quality standards (174 lines)

### Workflows (652 lines total)

- **[Workflow Index](.claude/docs/workflows/INDEX.md)** - All workflows overview
- **[Workflow 1: Feature Implementation](.claude/docs/workflows/WORKFLOW-1-FEATURE-IMPLEMENTATION.md)** - 10-15 parallel subagents, 8 phases
- **[Workflow 2: Bug Fix](.claude/docs/workflows/WORKFLOW-2-BUG-FIX.md)** - Fast-track resolution, 6 phases
- **[Workflow 3: Refactoring](.claude/docs/workflows/WORKFLOW-3-REFACTORING.md)** - Architecture improvement, 6 phases
- **[Workflow 4: Loop Prevention](.claude/docs/workflows/WORKFLOW-4-LOOP-PREVENTION.md)** - Ralph-Wiggum recovery, 5 steps

### Templates (200 lines total)

- **[Template Index](.claude/prompts/INDEX.md)** - All templates overview
- **[Subagent Spawn Template](.claude/prompts/subagent-spawn.md)** - Pattern for spawning subagents
- **[Workflow Breakdown Template](.claude/prompts/workflow-breakdown.md)** - 10-15 task breakdown
- **[Commit Message Template](.claude/prompts/commit-message.md)** - Standardized commit format
- **[PR Description Template](.claude/prompts/pr-description.md)** - Pull request template
- **[Architecture Review Template](.claude/prompts/architecture-review.md)** - Quality checklist

### Infrastructure (123 lines total)

- **[Infrastructure Index](.claude/docs/infrastructure/INDEX.md)** - Infrastructure overview
- **[PostToolUse Hook](.claude/docs/infrastructure/POST-TOOL-USE.md)** - Automatic validation details
- **[Slash Commands](.claude/docs/infrastructure/SLASH-COMMANDS.md)** - Command reference
- **[Metrics System](.claude/docs/infrastructure/METRICS-SYSTEM.md)** - Feedback loop details

### Usage Notes

**When to reference external docs**:
- ✓ When you need detailed workflow steps → Workflows
- ✓ When you need MCP tool specifics → MCP Guide
- ✓ When you need testing methodology → Testing Guide
- ✓ When you need environment setup help → Setup Guide
- ✓ When you need a template → Templates

**Auto-loading behavior**:
- ✗ External docs are NOT auto-loaded every session
- ✓ Core CLAUDE.md IS auto-loaded every session
- ✓ Reference external docs on-demand when needed
- ✓ Links are relative paths (work from any location)

---

**Remember**: This modular structure preserves all content while reducing token usage by 56%. Core philosophy and orchestration remain immediately accessible, while detailed reference material is one click away.

**Support**:
1. Check [Emergency Procedures](#emergency-procedures) for common issues
2. Review `~/.claude/metrics/improvement-suggestions.md` for workflow improvements
3. Consult global slash commands in `~/.claude/commands/`
4. Update this CLAUDE.md with new learnings via feedback loop
