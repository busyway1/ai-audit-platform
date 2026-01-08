# Specification: AI Audit AX Platform - AI Audit Project Implementation

## Overview

This specification details the implementation of the AI Audit portion of the AI Audit AX Platform - a comprehensive accounting audit automation system. This project encompasses frontend UI components (React/Next.js) for project management, EGA/Task hierarchy visualization, real-time agent streaming, and HITL (Human-in-the-Loop) interfaces, as well as backend enhancements (Python/LangGraph) for partner agents, EGA parsing, task generation, and API endpoints. The implementation enables auditors to manage audit projects, visualize EGAs (Expected General Activities), track hierarchical tasks, receive real-time agent updates, and handle escalation requests requiring human judgment.

## Workflow Type

**Type**: feature

**Rationale**: This is a comprehensive multi-phase feature implementation that adds new capabilities across both frontend and backend services. It involves creating new UI components, state management stores, API endpoints, LangGraph nodes, and agent enhancements - all constituting new feature development rather than refactoring or bug fixes.

## Task Scope

### Services Involved
- **frontend** (primary) - React/Next.js UI components, Zustand stores, SSE streaming hooks
- **backend** (primary) - Python/LangGraph agent nodes, API endpoints, state management

### This Task Will:
- [ ] Create Project Selection UI (store, selector, modal, integration)
- [ ] Create EGA and Task Hierarchy UI (store, list, tree components)
- [ ] Implement Real-time Agent Streaming (SSE hook, conversation panel)
- [ ] Build HITL Interface (store, request cards, queue view)
- [ ] Enhance Partner Agent with deep research and interview workflow
- [ ] Add Manager Agent dynamic staff allocation
- [ ] Create Staff Agent factory and implementations
- [ ] Build EGA parsing and task generation nodes
- [ ] Integrate new nodes into LangGraph workflow
- [ ] Add Project, EGA, and HITL API endpoints

### Out of Scope:
- Database schema migrations (handled in audit-mcp-suite project)
- MCP server creation (mcp-excel-processor is in audit-mcp-suite)
- RAG knowledge base ingestion scripts (handled in audit-mcp-suite)
- Desktop Commander MCP integration (handled in audit-mcp-suite)

## Service Context

### Frontend Service

**Tech Stack:**
- Language: TypeScript
- Framework: Next.js (React)
- State Management: Zustand
- Validation: Zod
- Database Client: @supabase/supabase-js + @supabase/ssr (for SSR/server components)
- Key directories:
  - `frontend/src/app/stores/` - Zustand stores
  - `frontend/src/app/components/` - React components
  - `frontend/src/app/hooks/` - Custom React hooks

**Entry Point:** `frontend/src/app/page.tsx`

**How to Run:**
```bash
cd frontend && npm run dev
```

**Port:** 3000 (default Next.js)

### Backend Service

**Tech Stack:**
- Language: Python 3.10+
- Framework: LangGraph, FastAPI
- AI Integration: LangChain, Claude (Anthropic)
- Streaming: sse-starlette (for SSE endpoints)
- Key directories:
  - `backend/src/agents/` - Agent implementations
  - `backend/src/graph/` - LangGraph workflow
  - `backend/src/graph/nodes/` - Graph nodes
  - `backend/src/api/` - API routes

**Entry Point:** `backend/src/main.py`

**How to Run:**
```bash
cd backend && python -m uvicorn src.main:app --reload
```

**Port:** 8000 (default FastAPI)

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `frontend/src/app/stores/useProjectStore.ts` | frontend | Create new Zustand store for project state management with Supabase CRUD |
| `frontend/src/app/components/layout/ProjectSelector.tsx` | frontend | Create dropdown component for project selection in chat header |
| `frontend/src/app/components/layout/ProjectRegistrationModal.tsx` | frontend | Create modal for new project creation with zod validation |
| `frontend/src/app/components/layout/AppShell.tsx` | frontend | Integrate ProjectSelector into header |
| `frontend/src/app/stores/useEGAStore.ts` | frontend | Create Zustand store for EGA state management |
| `frontend/src/app/components/ega/EGAList.tsx` | frontend | Create EGA card/list view with risk badges and progress |
| `frontend/src/app/components/tasks/TaskHierarchyTree.tsx` | frontend | Create 3-level hierarchy tree (High→Mid→Low) |
| `frontend/src/app/hooks/useStreamingChat.ts` | frontend | Update for real SSE connection with reconnection logic |
| `frontend/src/app/components/agents/AgentConversationPanel.tsx` | frontend | Create conversation panel for Partner/Manager/Staff agents |
| `frontend/src/app/stores/useHITLStore.ts` | frontend | Create Zustand store for HITL requests |
| `frontend/src/app/components/hitl/HITLRequestCard.tsx` | frontend | Create HITL request card with urgency badge and actions |
| `frontend/src/app/components/hitl/HITLQueue.tsx` | frontend | Create HITL request queue view with sorting/filtering |
| `backend/src/agents/partner_agent.py` | backend | Add deep_research() method with RAG + Web integration |
| `backend/src/graph/nodes/interview_node.py` | backend | Create interview workflow node with hybrid questions |
| `backend/src/agents/manager_agent.py` | backend | Add allocate_staff_agents() for dynamic allocation |
| `backend/src/agents/staff_factory.py` | backend | Create factory for specialized Staff agents |
| `backend/src/agents/staff_agents.py` | backend | Implement all Staff agent types with MCP integration |
| `backend/src/graph/nodes/ega_parser.py` | backend | Create EGA extraction from Assigned Workflow documents |
| `backend/src/graph/nodes/task_generator.py` | backend | Create 3-level task hierarchy generation from EGAs |
| `backend/src/graph/nodes/urgency_node.py` | backend | Create urgency score calculation node |
| `backend/src/graph/graph.py` | backend | Integrate new nodes with conditional routing |
| `backend/src/graph/state.py` | backend | Add new fields to AuditState |
| `backend/src/graph/nodes/hitl_interrupt.py` | backend | Create HITL interrupt node for escalations |
| `backend/src/api/routes.py` | backend | Add Project, EGA, and HITL endpoints |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `frontend/src/app/stores/*.ts` | Existing Zustand store pattern with Supabase integration |
| `frontend/src/app/components/**/*.tsx` | Existing React component patterns and styling |
| `frontend/src/app/hooks/*.ts` | Existing custom hook patterns |
| `backend/src/graph/nodes/*.py` | Existing LangGraph node patterns |
| `backend/src/agents/*.py` | Existing agent implementation patterns |
| `backend/src/api/routes.py` | Existing FastAPI endpoint patterns |

## Patterns to Follow

### Zustand Store Pattern (Frontend)

From existing stores:

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { supabase } from '@/lib/supabase';

interface ProjectState {
  projects: Project[];
  selectedProject: Project | null;
  loading: boolean;
  error: string | null;
  fetchProjects: () => Promise<void>;
  selectProject: (project: Project) => void;
  createProject: (data: CreateProjectInput) => Promise<void>;
  updateProject: (id: string, data: UpdateProjectInput) => Promise<void>;
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      // state and actions
    }),
    { name: 'project-store' }
  )
);
```

**Key Points:**
- Use persist middleware for localStorage persistence
- Integrate Supabase for database operations
- Include loading and error states
- Export typed hooks

### LangGraph Node Pattern (Backend)

From existing nodes:

```python
from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver  # Required for checkpointing

class NodeState(TypedDict):
    # State fields
    pass

def node_function(state: NodeState) -> NodeState:
    """Node description."""
    # Process state
    return {
        **state,
        # Updated fields
    }

# Graph compilation with checkpointing
checkpointer = MemorySaver()
compiled_graph = graph.compile(checkpointer=checkpointer)
```

**Key Points:**
- Use TypedDict for state typing
- Return updated state dictionary
- Keep nodes focused on single responsibility
- Log node execution for debugging
- Always use MemorySaver or custom checkpointer for stateful workflows

### Zod Validation Pattern (Frontend)

For form validation (e.g., ProjectRegistrationModal):

```typescript
import { z } from 'zod';

// Define schema
const projectSchema = z.object({
  client_name: z.string().min(1, 'Client name is required'),
  fiscal_year: z.number().int().min(2020).max(2030),
  overall_materiality: z.number().positive(),
  status: z.enum(['planning', 'in_progress', 'completed']),
});

// Infer TypeScript type from schema
type ProjectInput = z.infer<typeof projectSchema>;

// Use safeParse for non-throwing validation
const result = projectSchema.safeParse(formData);
if (!result.success) {
  // Handle errors: result.error.issues
}
```

**Key Points:**
- Use `safeParse()` instead of `parse()` to avoid throwing errors
- Use `z.infer<>` to derive TypeScript types from schemas
- Define schemas close to where they're used (e.g., in modal components)

### SSE Streaming Pattern (Frontend)

```typescript
const useStreamingChat = (taskId: string) => {
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    const eventSource = new EventSource(`/api/stream/${taskId}`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => [...prev, data]);
    };

    eventSource.onerror = () => {
      // Reconnection logic
      eventSource.close();
      setTimeout(() => reconnect(), 3000);
    };

    return () => eventSource.close();
  }, [taskId]);

  return { messages };
};
```

**Key Points:**
- Handle reconnection on error
- Process heartbeat events
- Auto-scroll to latest message
- Clean up on unmount

### SSE Streaming Pattern (Backend)

For FastAPI SSE endpoints:

```python
from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter

router = APIRouter()

async def event_generator(task_id: str):
    """Generate SSE events for task progress."""
    while True:
        # Get updates from task
        update = await get_task_update(task_id)
        if update:
            yield {
                "event": "message",
                "data": json.dumps(update)
            }
        else:
            yield {"event": "heartbeat", "data": ""}
        await asyncio.sleep(0.5)

@router.get("/api/stream/{task_id}")
async def stream_task(task_id: str):
    return EventSourceResponse(event_generator(task_id))
```

**Key Points:**
- Use `sse-starlette` package (pip install sse-starlette)
- Yield dicts with "event" and "data" keys
- Include heartbeat events to keep connection alive
- Use ASGI server (uvicorn) for proper streaming

## Requirements

### Functional Requirements

1. **Project Selection (FE-6.1 to FE-6.4)**
   - Description: Users can select, create, and manage audit projects
   - Acceptance: Dropdown works, modal validates input, selection persists in localStorage

2. **EGA and Task Hierarchy (FE-7.1 to FE-7.3)**
   - Description: Display EGAs with risk levels and 3-level task hierarchy
   - Acceptance: EGA list shows risk badges and progress, tree view expands/collapses correctly

3. **Real-time Agent Streaming (FE-8.1 to FE-8.2)**
   - Description: Live updates from Partner/Manager/Staff agents via SSE
   - Acceptance: Messages stream in real-time, reconnection works, role indicators visible

4. **HITL Interface (FE-9.1 to FE-9.3)**
   - Description: Human-in-the-loop request management
   - Acceptance: Queue shows pending requests sorted by urgency, approve/reject actions work

5. **Partner Agent Enhancement (BE-10.1 to BE-10.2)**
   - Description: Deep research with RAG + Web, interview workflow for audit strategy
   - Acceptance: Multi-source search works, interview generates requirements document

6. **Manager Agent Enhancement (BE-11.1)**
   - Description: Dynamic staff allocation based on risk, skills, and workload
   - Acceptance: Staff agents allocated proportionally to task complexity

7. **Staff Agent System (BE-12.1 to BE-12.2)**
   - Description: Factory for specialized staff agents with MCP tool integration
   - Acceptance: All agent types (Excel_Parser, Standard_Retriever, etc.) can be spawned

8. **EGA Parsing and Task Generation (BE-13.1 to BE-13.3)**
   - Description: Extract EGAs from documents, generate 3-level task hierarchy, calculate urgency
   - Acceptance: EGAs parsed correctly, parent_task_id relationships valid, urgency scores assigned

9. **LangGraph Integration (BE-14.1 to BE-14.3)**
   - Description: Integrate new nodes into workflow with HITL interrupts
   - Acceptance: Full workflow executes, checkpointing works, HITL interrupts trigger correctly

10. **API Endpoints (BE-15.1 to BE-15.3)**
    - Description: REST API for projects, EGAs, and HITL management
    - Acceptance: CRUD operations work, proper error handling

### Edge Cases

1. **Empty Project List** - Show "No projects" message with create button
2. **SSE Connection Drop** - Auto-reconnect with exponential backoff (max 30s)
3. **Large Task Hierarchy** - Virtualize tree for performance (>100 tasks)
4. **Concurrent HITL Responses** - Optimistic locking to prevent duplicate responses
5. **Token Overflow** - Memory manager triggers summarization at 8000 tokens
6. **Invalid EGA Document** - Graceful error with specific parsing failure reason
7. **Agent Timeout** - 30s timeout with retry option for deep_research()
8. **Urgency Threshold Edge** - Clear boundary at exactly threshold value (inclusive >=)

## Implementation Notes

### DO
- Follow the Zustand persist pattern for all stores (localStorage backup)
- Use zod for all form validation (ProjectRegistrationModal)
- Reuse existing Supabase client from `@/lib/supabase`
- Use `create_react_agent` from LangGraph for agent nodes
- Implement TDD: write tests first (Red), then implementation (Green), then refactor
- Keep functions under 50 lines, files under 800 lines per CLAUDE.md
- Use TypeScript strict mode for all frontend code
- Add type hints for all Python functions

### DON'T
- Create new database connections when Supabase client exists
- Use `any` types in TypeScript
- Skip error handling in API endpoints
- Implement drag-and-drop in TaskHierarchyTree (marked optional)
- Create duplicate state management for same data
- Use inline styles - follow existing component styling patterns

## Development Environment

### Start Services

```bash
# Frontend
cd frontend && npm run dev

# Backend
cd backend && python -m uvicorn src.main:app --reload
```

### Service URLs
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Required Environment Variables

**Frontend (Next.js):**
- `NEXT_PUBLIC_SUPABASE_URL`: Supabase project URL (required for client-side access)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase anonymous key (required for client-side access)

**Backend (Python):**
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase service role key
- `OPENAI_API_KEY`: OpenAI API key (for embeddings)
- `ANTHROPIC_API_KEY`: Anthropic API key (for Claude agents)

## Success Criteria

The task is complete when:

1. [ ] **Project Selection**: Dropdown shows projects, modal creates new project with validation
2. [ ] **EGA List**: Risk badges display, progress bars accurate, filtering works
3. [ ] **Task Tree**: 3-level hierarchy renders, expand/collapse functional
4. [ ] **SSE Streaming**: Real-time messages from agents, reconnection works
5. [ ] **HITL Queue**: Pending requests listed, urgency-sorted, actions submit correctly
6. [ ] **Partner Agent**: deep_research() returns multi-source results, interview generates spec
7. [ ] **Staff Factory**: All 4 agent types instantiate with correct MCP tools
8. [ ] **EGA Parser**: Documents parsed, hierarchy extracted, records created
9. [ ] **Task Generator**: 3-level tasks created with proper parent_task_id linking
10. [ ] **LangGraph Workflow**: New nodes integrated, conditional routing works
11. [ ] No console errors in browser or server logs
12. [ ] Existing tests still pass
13. [ ] New functionality verified via browser and API testing

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests

| Test | File | What to Verify |
|------|------|----------------|
| Project Store | `frontend/src/app/stores/__tests__/useProjectStore.test.ts` | fetchProjects, selectProject, createProject, updateProject actions |
| EGA Store | `frontend/src/app/stores/__tests__/useEGAStore.test.ts` | CRUD operations, state updates |
| HITL Store | `frontend/src/app/stores/__tests__/useHITLStore.test.ts` | Request fetching, response submission |
| Partner Agent | `backend/tests/test_partner_agent.py` | deep_research returns results, interview generates spec |
| Staff Factory | `backend/tests/test_staff_factory.py` | All agent types created correctly |
| EGA Parser | `backend/tests/test_ega_parser.py` | Various document formats parsed correctly |
| Task Generator | `backend/tests/test_task_generator.py` | Hierarchy generated with correct relationships |
| Urgency Node | `backend/tests/test_urgency_node.py` | Scores calculated correctly, threshold triggers |

### Integration Tests

| Test | Services | What to Verify |
|------|----------|----------------|
| Project CRUD | frontend ↔ backend ↔ Supabase | Full project lifecycle |
| EGA Parsing Flow | backend ↔ mcp-excel-processor | Document uploaded, EGAs extracted |
| Agent Streaming | frontend ↔ backend SSE | Real-time message delivery |
| HITL Flow | frontend ↔ backend ↔ Supabase | Request created, displayed, responded |

### End-to-End Tests

| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| New Project | 1. Click "New Project" 2. Fill form 3. Submit | Project appears in dropdown, persists on refresh |
| EGA Workflow | 1. Select project 2. Upload workflow doc 3. View EGAs | EGAs listed with tasks hierarchy |
| Agent Chat | 1. Start task 2. View conversation | Messages stream in real-time |
| HITL Response | 1. View queue 2. Select request 3. Approve/Reject | Request removed from queue, workflow continues |

### Browser Verification (Frontend)

| Page/Component | URL | Checks |
|----------------|-----|--------|
| Project Selector | `http://localhost:3000` (header) | Dropdown opens, projects listed, selection highlights |
| Project Modal | Click "New Project" | Form validates, submits, closes on success |
| EGA List | `/egas` or panel | Risk badges colored correctly, progress accurate |
| Task Tree | `/tasks` or panel | Expand/collapse works, 3 levels visible |
| Agent Panel | `/chat` or panel | Messages appear, role icons visible, auto-scroll works |
| HITL Queue | `/hitl` or panel | Sorted by urgency, cards display context |

### Database Verification

| Check | Query/Command | Expected |
|-------|---------------|----------|
| Project created | `SELECT * FROM audit_projects WHERE client_name='...'` | Row exists with correct fields |
| EGAs created | `SELECT * FROM audit_egas WHERE project_id='...'` | EGAs linked to project |
| Tasks hierarchy | `SELECT * FROM audit_tasks WHERE project_id='...' ORDER BY task_level` | High/Mid/Low tasks with parent_task_id |
| HITL request | `SELECT * FROM hitl_requests WHERE status='pending'` | Request visible in queue |

### QA Sign-off Requirements
- [ ] All unit tests pass (frontend and backend)
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] Browser verification complete
- [ ] Database state verified
- [ ] No regressions in existing functionality
- [ ] Code follows established patterns (Zustand, LangGraph)
- [ ] No security vulnerabilities introduced (input validation, auth checks)
- [ ] Performance acceptable (task tree renders <100ms for 100 tasks)
- [ ] Accessibility basics met (keyboard navigation, screen reader labels)

## Task Execution Order

### Parallel Worktrees (AI Audit)

Execute tasks in these worktree groups:

**Worktree 1: project-ui** (P0 - Start First)
1. FE-6.1: Create Project Store
2. FE-6.2: Create Project Selector Component
3. FE-6.3: Create Project Registration Modal
4. FE-6.4: Integrate ProjectSelector into AppShell

**Worktree 2: ega-task-ui** (P1)
1. FE-7.1: Create EGA Store
2. FE-7.2: Create EGA List Component
3. FE-7.3: Create Task Hierarchy Tree Component

**Worktree 3: streaming** (P0)
1. FE-8.1: Update useStreamingChat for Real SSE
2. FE-8.2: Create Agent Conversation Panel

**Worktree 4: hitl-ui** (P1)
1. FE-9.1: Create HITL Request Store
2. FE-9.2: Create HITL Request Card Component
3. FE-9.3: Create HITL Queue View

**Worktree 5: agents** (P0)
1. BE-10.1: Add Deep Research Capability
2. BE-10.2: Add Interview Workflow
3. BE-11.1: Add Dynamic Staff Allocation
4. BE-12.1: Create Staff Agent Factory
5. BE-12.2: Implement Staff Agents with MCP Integration

**Worktree 6: graph-nodes** (P0)
1. BE-13.1: Create EGA Parser Node
2. BE-13.2: Create Task Generation Node
3. BE-13.3: Create Urgency Calculation Node
4. BE-14.1: Update Main Graph with New Nodes
5. BE-14.2: Update State Definition
6. BE-14.3: Add HITL Interrupt Nodes
7. BE-15.1: Add Project Endpoints
8. BE-15.2: Add EGA Endpoints
9. BE-15.3: Add HITL Endpoints

### Critical Path

```
DB Schema (MCP-1.1) ─────────────────────────────────────┐
                                                         │
                                                         ▼
                                                   FE-6.1~6.4
                                                  (Project UI)
                                                         │
                                                         ▼
                                                   FE-7.1~7.3
                                                   (EGA/Task)
                                                         │
                                                         ▼
                                                  BE-13.1~13.3
                                                  (Parser/Gen)
                                                         │
                                                         ▼
                                                  BE-14.1~14.3
                                                  (LangGraph)
```

**Note**: DB Schema (MCP-1.1) is a blocking dependency in audit-mcp-suite project. Frontend tasks can proceed with mock data until schema is ready.

## Dependency Note

This specification depends on the following from **audit-mcp-suite** project:
- **MCP-1.1**: Database schema migration (6 new tables + alterations)
- **MCP-1.2**: RLS policies extension
- **MCP-2.x**: mcp-excel-processor server (for EGA parsing)
- **MCP-4.1**: Urgency calculator module (imported by urgency_node.py)
- **MCP-4.2**: Memory manager module (imported by agents)

If these dependencies are not yet available, implement with:
1. Mock database tables locally for frontend development
2. Create stub implementations for imported modules
3. Add TODO comments marking dependency points
