# AI Audit Platform - Backend

> AI 기반 회계 감사 자동화 플랫폼의 백엔드 서비스

## 목차

- [프로젝트 개요](#프로젝트-개요)
- [기술 스택](#기술-스택)
- [시스템 아키텍처](#시스템-아키텍처)
- [사전 요구사항](#사전-요구사항)
- [설치 방법](#설치-방법)
- [실행 방법](#실행-방법)
- [API 엔드포인트](#api-엔드포인트)
- [프로젝트 구조](#프로젝트-구조)
- [환경 변수](#환경-변수)
- [테스트](#테스트)
- [데이터베이스 마이그레이션](#데이터베이스-마이그레이션)

---

## 프로젝트 개요

AI Audit Platform 백엔드는 LangGraph 기반의 멀티 에이전트 워크플로우를 통해 회계 감사 업무를 자동화합니다.

### 주요 기능

- **멀티 에이전트 워크플로우**: Partner → Manager → Staff 계층 구조의 AI 에이전트 협업
- **Human-in-the-Loop (HITL)**: 중요 의사결정 시점에서 사람의 승인/거부 처리
- **실시간 스트리밍**: SSE(Server-Sent Events)를 통한 에이전트 메시지 실시간 전달
- **EGA 파싱**: Excel 문서에서 감사 업무(EGA) 자동 추출
- **긴급도 계산**: 중요성, 위험도, AI 신뢰도를 기반으로 업무 우선순위 산정
- **상태 영속성**: PostgresSaver를 통한 워크플로우 상태 저장 및 복구

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| **웹 프레임워크** | FastAPI |
| **워크플로우 엔진** | LangGraph |
| **LLM** | OpenAI GPT-4o / GPT-4o-mini |
| **LLM 프레임워크** | LangChain |
| **데이터베이스** | PostgreSQL (Supabase) |
| **상태 저장** | LangGraph PostgresSaver / MemorySaver |
| **실시간 통신** | SSE (sse-starlette) |
| **ORM/클라이언트** | supabase-py |
| **비동기 처리** | asyncio, uvicorn |
| **테스트** | pytest, pytest-asyncio |

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                             │
├─────────────────────────────────────────────────────────────────────┤
│  REST API (/api/*)  │  SSE Stream (/api/stream/*)  │  Supabase RT  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Application (main.py)                   │
├─────────────────────────────────────────────────────────────────────┤
│  CORS Middleware  │  Route Registration  │  Lifespan Management    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │  Routes   │   │    SSE    │   │ Services  │
            │  (REST)   │   │ Streaming │   │   (Sync)  │
            └───────────┘   └───────────┘   └───────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow Engine                         │
├─────────────────────────────────────────────────────────────────────┤
│  Interview Node → Partner Planning → EGA Parser → Task Generator    │
│         ↓                ↓                              ↓           │
│  Wait for HITL → Urgency Node → HITL Interrupt → Manager Subgraph  │
│                                                         ↓           │
│                                              Final Aggregation      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │ PostgreSQL│   │  Supabase │   │   Tools   │
            │  Saver    │   │   Client  │   │ (Analyzer)│
            └───────────┘   └───────────┘   └───────────┘
```

### LangGraph 워크플로우

```
START
  │
  ▼
Interview Node (감사 전략 인터뷰)
  │
  ▼
Wait for Interview Completion (HITL)
  │ (승인 시)
  ▼
Partner Planning (감사 계획 생성)
  │
  ▼
Wait for Approval (HITL)
  │ (승인 시)
  ▼
EGA Parser (문서에서 EGA 추출)
  │
  ▼
Task Generator (3단계 태스크 계층 생성)
  │
  ▼
Urgency Node (긴급도 점수 계산)
  │ (임계값 초과 시)
  ▼
HITL Interrupt (고긴급도 에스컬레이션)
  │ (승인 시)
  ▼
Manager Dispatch (병렬 Manager 서브그래프 실행)
  │
  ▼
Final Aggregation (결과 집계)
  │
  ▼
END
```

---

## 사전 요구사항

- **Python**: 3.11 이상
- **PostgreSQL**: Supabase 프로젝트 또는 로컬 PostgreSQL
- **OpenAI API Key**: GPT-4o 접근 권한

---

## 설치 방법

### 1. 저장소 클론

```bash
cd /path/to/AI\ Audit
```

### 2. 가상환경 생성 및 활성화

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate
```

### 3. 의존성 설치

```bash
# 기본 의존성 설치 스크립트 실행
./install_dependencies.sh

# 또는 수동 설치
pip install -r requirements.txt  # requirements.txt가 있는 경우

# 또는 주요 패키지 수동 설치
pip install fastapi uvicorn langchain langchain-openai langgraph
pip install supabase python-dotenv sse-starlette
pip install psycopg2-binary pytest pytest-asyncio
```

### 4. 환경 변수 설정

```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일을 편집하여 실제 값 입력
```

---

## 실행 방법

### 개발 서버 실행

```bash
# 가상환경 활성화 확인
source venv/bin/activate

# backend 디렉토리에서 실행
cd backend

# uvicorn으로 서버 시작 (자동 리로드)
uvicorn src.main:app --reload --port 8000

# 또는 Python 모듈로 실행
python -m src.main
```

### 프로덕션 서버 실행

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 서버 상태 확인

```bash
# 루트 엔드포인트
curl http://localhost:8000/

# 헬스체크
curl http://localhost:8000/api/health

# API 문서
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

---

## API 엔드포인트

### 헬스체크

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 서비스 기본 정보 |
| GET | `/api/health` | 헬스체크 (LangGraph, Supabase 상태) |

### 프로젝트 관리

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/projects/start` | 감사 프로젝트 시작 (워크플로우 실행) |
| POST | `/api/projects` | 프로젝트 생성 (CRUD) |
| GET | `/api/projects` | 프로젝트 목록 조회 |
| GET | `/api/projects/{id}` | 프로젝트 상세 조회 |
| PUT | `/api/projects/{id}` | 프로젝트 수정 |
| DELETE | `/api/projects/{id}` | 프로젝트 삭제 |

### 태스크 관리

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/tasks/approve` | 태스크 승인/거부 (워크플로우 재개) |

### EGA (Engagement Area) 관리

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/projects/{id}/egas` | EGA 목록 조회 |
| GET | `/api/projects/{id}/egas/{ega_id}` | EGA 상세 조회 |
| POST | `/api/projects/{id}/egas` | EGA 수동 생성 |
| PUT | `/api/projects/{id}/egas/{ega_id}` | EGA 수정 |
| DELETE | `/api/projects/{id}/egas/{ega_id}` | EGA 삭제 |
| POST | `/api/projects/{id}/egas/parse` | Excel 파일에서 EGA 파싱 |

### HITL (Human-in-the-Loop) 관리

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/hitl/pending` | 대기 중인 HITL 요청 목록 |
| GET | `/api/hitl` | 전체 HITL 요청 목록 (필터링) |
| GET | `/api/hitl/{id}` | HITL 요청 상세 조회 |
| POST | `/api/hitl/{id}/respond` | HITL 요청 응답 (승인/거부/에스컬레이션) |

### SSE 스트리밍

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/stream/{task_id}` | 에이전트 메시지 실시간 스트리밍 |
| GET | `/api/stream/{task_id}?message=...` | 메시지 전송 후 응답 스트리밍 |

---

## 프로젝트 구조

```
backend/
├── src/
│   ├── main.py                 # FastAPI 애플리케이션 진입점
│   ├── __init__.py
│   │
│   ├── api/                    # API 레이어
│   │   ├── __init__.py
│   │   ├── sse.py              # SSE 스트리밍 엔드포인트
│   │   └── routes/
│   │       ├── __init__.py     # 라우터 통합
│   │       ├── schemas.py      # Pydantic 스키마 정의
│   │       ├── projects.py     # 프로젝트 CRUD + 워크플로우
│   │       ├── tasks.py        # 태스크 승인
│   │       ├── egas.py         # EGA 관리
│   │       ├── hitl.py         # HITL 큐 관리
│   │       └── health.py       # 헬스체크
│   │
│   ├── graph/                  # LangGraph 워크플로우
│   │   ├── __init__.py
│   │   ├── graph.py            # 부모 그래프 정의
│   │   ├── subgraph.py         # Manager 서브그래프
│   │   ├── state.py            # AuditState, TaskState 정의
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── partner.py          # Partner 에이전트 노드
│   │       ├── manager.py          # Manager 에이전트 노드
│   │       ├── interview_node.py   # 인터뷰 노드
│   │       ├── ega_parser.py       # EGA 파싱 노드
│   │       ├── urgency_node.py     # 긴급도 계산 노드
│   │       ├── hitl_interrupt.py   # HITL 인터럽트 노드
│   │       ├── reranker_node.py    # 리랭킹 노드
│   │       ├── multihop_node.py    # 멀티홉 추론 노드
│   │       └── task_generator/     # 태스크 생성기
│   │           ├── __init__.py
│   │           ├── core.py
│   │           ├── models.py
│   │           ├── hierarchy.py
│   │           ├── constants.py
│   │           └── utils.py
│   │
│   ├── agents/                 # AI 에이전트 정의
│   │   ├── __init__.py
│   │   ├── partner_agent.py    # Partner (전략 수립)
│   │   ├── manager_agent.py    # Manager (업무 조율)
│   │   ├── staff_agents.py     # Staff (실행)
│   │   └── staff_factory.py    # Staff 에이전트 팩토리
│   │
│   ├── tools/                  # LangChain 도구
│   │   ├── __init__.py
│   │   ├── financial_analyzer.py   # 재무 분석 도구
│   │   ├── workpaper_generator.py  # 조서 생성 도구
│   │   └── test_tools.py
│   │
│   ├── db/                     # 데이터베이스 레이어
│   │   ├── __init__.py
│   │   ├── checkpointer.py     # PostgresSaver 설정
│   │   └── supabase_client.py  # Supabase 클라이언트
│   │
│   └── services/               # 비즈니스 로직 서비스
│       ├── __init__.py
│       ├── mcp_client.py       # MCP 클라이언트
│       └── task_sync.py        # 태스크 동기화
│
├── tests/                      # 테스트
│   ├── conftest.py             # pytest 공통 설정
│   ├── test_*.py               # 단위 테스트
│   ├── unit/                   # 단위 테스트
│   │   ├── test_agents/
│   │   ├── test_tools/
│   │   ├── test_db/
│   │   └── test_graph/
│   └── integration/            # 통합 테스트
│       ├── test_fastapi_routes.py
│       ├── test_end_to_end.py
│       ├── test_sse_streaming.py
│       └── test_supabase_sync.py
│
├── supabase/
│   └── migrations/             # 데이터베이스 마이그레이션
│       ├── 001_initial_schema.sql
│       └── 002_hitl_requests.sql
│
├── docs/                       # 문서
├── venv/                       # 가상환경 (git 제외)
├── .env                        # 환경 변수 (git 제외)
├── .env.example                # 환경 변수 예시
├── pytest.ini                  # pytest 설정
├── install_dependencies.sh     # 의존성 설치 스크립트
└── README.md                   # 이 문서
```

---

## 환경 변수

`.env.example` 파일을 참조하여 `.env` 파일을 생성하세요.

### 필수 환경 변수

```bash
# OpenAI API
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# PostgreSQL (LangGraph PostgresSaver)
POSTGRES_CONNECTION_STRING=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres
```

### 선택적 환경 변수

```bash
# 애플리케이션 설정
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=INFO

# Redis (선택)
# REDIS_URL=redis://localhost:6379/0
```

### Supabase 자격 증명 얻기

1. [Supabase Dashboard](https://supabase.com/dashboard)에 접속
2. 프로젝트 선택 → Settings → API
3. Project URL, anon key, service_role key 복사
4. Settings → Database → Connection string (Direct) 복사

---

## 테스트

### 테스트 실행

```bash
# 가상환경 활성화
source venv/bin/activate

# 전체 테스트 실행
pytest

# 특정 테스트 파일 실행
pytest tests/test_ega_parser.py

# 단위 테스트만 실행
pytest tests/unit/

# 통합 테스트만 실행
pytest tests/integration/

# 상세 출력
pytest -v

# 커버리지 포함
pytest --cov=src --cov-report=html

# 특정 마커 테스트
pytest -m integration  # 통합 테스트
pytest -m "not slow"   # 느린 테스트 제외
```

### pytest 설정 (pytest.ini)

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
python_files = test_*.py
python_classes = Test*
python_functions = test_*
pythonpath = .
markers =
    integration: marks tests as integration tests
    slow: marks tests as slow
```

---

## 데이터베이스 마이그레이션

### 마이그레이션 파일 위치

```
supabase/migrations/
├── 001_initial_schema.sql   # 초기 스키마 (projects, tasks, messages 등)
└── 002_hitl_requests.sql    # HITL 요청 테이블
```

### 마이그레이션 적용

#### Supabase Dashboard 사용 (권장)

1. Supabase Dashboard → SQL Editor
2. 마이그레이션 SQL 파일 내용 붙여넣기
3. Run 클릭

#### 스크립트 사용

```bash
# 의존성 설치
./install_dependencies.sh

# 마이그레이션 적용 (스크립트가 있는 경우)
python apply_migration.py

# 스키마 검증
python verify_schema.py
```

---

## 개발 가이드

### 코드 스타일

- **Python 버전**: 3.11+
- **타입 힌트**: 모든 함수에 타입 힌트 사용
- **비동기**: FastAPI 라우트는 `async def` 사용
- **로깅**: `logging` 모듈 사용 (`print` 사용 금지)

### 새 API 엔드포인트 추가

1. `src/api/routes/`에 새 라우트 파일 생성 또는 기존 파일 수정
2. `src/api/routes/schemas.py`에 Pydantic 모델 추가
3. `src/api/routes/__init__.py`에 라우터 등록
4. 테스트 작성 (`tests/` 디렉토리)

### 새 LangGraph 노드 추가

1. `src/graph/nodes/`에 새 노드 파일 생성
2. `src/graph/graph.py`에서 노드 import 및 그래프에 추가
3. 필요시 `src/graph/state.py`에 상태 필드 추가
4. 테스트 작성

---

## 문제 해결

### 포트 충돌

```bash
# 8000번 포트 사용 중인 프로세스 확인
lsof -i :8000

# 프로세스 종료
kill -9 <PID>
```

### 가상환경 문제

```bash
# 가상환경 재생성
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### LangGraph 초기화 실패

- `.env` 파일의 `POSTGRES_CONNECTION_STRING` 확인
- Supabase 프로젝트가 활성 상태인지 확인
- 네트워크 연결 확인

---

## 라이선스

이 프로젝트는 내부용으로 개발되었습니다.

---

## 연락처

문의사항이 있으시면 프로젝트 관리자에게 연락하세요.
