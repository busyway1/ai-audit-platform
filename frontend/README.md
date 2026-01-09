# AI Audit Platform - Frontend

AI 기반 감사 자동화 플랫폼의 프론트엔드 애플리케이션입니다. React, TypeScript, Vite를 기반으로 구축되었으며, 현대적인 UI/UX를 제공합니다.

> 원본 Figma 디자인: https://www.figma.com/design/oYDaYzBmT3CWeaItTGhhkQ/AI-%EA%B0%90%EC%82%AC-%ED%94%8C%EB%9E%AB%ED%8F%BC-UI-UX

## 기술 스택

### Core

- **React 18.3** - UI 라이브러리
- **TypeScript 5.9** - 타입 안전성
- **Vite 6.3** - 빌드 도구 및 개발 서버
- **TanStack Router** - 타입 안전한 라우팅

### Styling

- **Tailwind CSS 4.1** - 유틸리티 기반 CSS
- **Radix UI** - 접근성 높은 헤드리스 UI 컴포넌트
- **shadcn/ui** - Radix UI 기반 컴포넌트 라이브러리
- **Lucide React** - 아이콘
- **Motion** - 애니메이션

### State Management

- **Zustand** - 경량 상태 관리
- **React Hook Form** - 폼 상태 관리
- **Zod** - 스키마 유효성 검사

### Data & Backend Integration

- **Supabase** - 실시간 데이터베이스 및 인증
- **SSE (Server-Sent Events)** - 실시간 스트리밍 통신

### Charts & Visualization

- **Recharts** - 차트 라이브러리

### Testing

- **Vitest** - 단위 테스트
- **Testing Library** - 컴포넌트 테스트
- **Playwright** - E2E 테스트

## 필수 요구사항

- **Node.js** 18.0 이상 (권장: v24.x)
- **npm** 또는 **pnpm**
- **백엔드 서버** - Python FastAPI 기반 (`../backend`)

## 설치

```bash
# 의존성 설치
npm install

# 환경 변수 설정
cp .env.example .env
```

## 환경 변수

`.env` 파일에 다음 환경 변수를 설정하세요:

```env
# Supabase 설정
# https://app.supabase.com 에서 프로젝트 값을 가져오세요
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key

# 백엔드 API 설정
VITE_API_URL=http://localhost:8080

# API 요청 타임아웃 (밀리초, 기본값: 30000)
VITE_API_TIMEOUT=30000

# 디버그 모드 (선택사항)
# VITE_DEBUG=false
```

## 실행

### 개발 서버

```bash
npm run dev
```

개발 서버가 `http://localhost:5173`에서 시작됩니다.

### 프로덕션 빌드

```bash
npm run build
```

빌드 결과물은 `dist/` 폴더에 생성됩니다.

## 스크립트

| 스크립트 | 설명 |
|----------|------|
| `npm run dev` | 개발 서버 시작 (HMR 지원) |
| `npm run build` | 프로덕션 빌드 |
| `npm run test` | 단위 테스트 실행 |
| `npm run test:ui` | Vitest UI로 테스트 실행 |
| `npm run test:coverage` | 테스트 커버리지 리포트 |
| `npm run test:e2e` | Playwright E2E 테스트 |
| `npm run test:e2e:ui` | Playwright UI 모드로 E2E 테스트 |
| `npm run test:e2e:debug` | E2E 테스트 디버그 모드 |
| `npm run test:e2e:report` | E2E 테스트 리포트 보기 |

## 프로젝트 구조

```
frontend/
├── src/
│   ├── app/
│   │   ├── App.tsx              # 앱 진입점 및 라우터 설정
│   │   ├── components/          # React 컴포넌트
│   │   │   ├── agents/          # AI 에이전트 관련 컴포넌트
│   │   │   ├── artifacts/       # 아티팩트 렌더링 컴포넌트
│   │   │   ├── ega/             # EGA (Engagement Gap Analysis) 컴포넌트
│   │   │   ├── figma/           # Figma 관련 컴포넌트
│   │   │   ├── hitl/            # Human-in-the-Loop 컴포넌트
│   │   │   ├── layout/          # 레이아웃 컴포넌트 (AppShell, ChatInterface 등)
│   │   │   ├── settings/        # 설정 페이지 컴포넌트
│   │   │   ├── tasks/           # 태스크 관리 컴포넌트
│   │   │   ├── ui/              # shadcn/ui 기본 컴포넌트
│   │   │   └── workspace/       # 워크스페이스 레이아웃 컴포넌트
│   │   ├── data/                # 목업 데이터
│   │   ├── hooks/               # 커스텀 React 훅
│   │   │   ├── useArtifactUpdates.ts
│   │   │   ├── useRealtimeSync.ts
│   │   │   ├── useStreamingChat.ts
│   │   │   └── useTaskActions.ts
│   │   ├── stores/              # Zustand 스토어
│   │   │   ├── useArtifactStore.ts
│   │   │   ├── useChatStore.ts
│   │   │   ├── useEGAStore.ts
│   │   │   ├── useEntityStore.ts
│   │   │   ├── useHITLStore.ts
│   │   │   ├── useProjectStore.ts
│   │   │   ├── useSessionStore.ts
│   │   │   └── useTaskStore.ts
│   │   └── types/               # TypeScript 타입 정의
│   │       ├── audit.ts         # 감사 도메인 타입
│   │       └── supabase.ts      # Supabase 타입
│   ├── config/                  # 설정 파일
│   │   └── api.ts               # API 설정
│   ├── lib/                     # 유틸리티 라이브러리
│   │   └── supabase.ts          # Supabase 클라이언트
│   ├── styles/                  # 전역 스타일
│   │   ├── fonts.css
│   │   ├── index.css
│   │   ├── tailwind.css
│   │   └── theme.css
│   ├── test/                    # 테스트 설정
│   └── main.tsx                 # 엔트리 포인트
├── e2e/                         # E2E 테스트
│   ├── *.spec.ts                # 테스트 스펙 파일
│   ├── utils/                   # E2E 유틸리티
│   ├── fixtures/                # 테스트 픽스처
│   └── screenshots/             # 테스트 스크린샷
├── public/                      # 정적 파일
├── vite.config.ts               # Vite 설정
├── vitest.config.ts             # Vitest 설정
├── playwright.config.ts         # Playwright 설정
├── tsconfig.json                # TypeScript 설정
├── tailwind.config.ts           # Tailwind 설정
└── package.json
```

## 주요 페이지 및 라우트

| 경로 | 컴포넌트 | 설명 |
|------|----------|------|
| `/` | AppShell | 메인 채팅 인터페이스 |
| `/workspace/dashboard` | Dashboard | 감사 대시보드 |
| `/workspace/financial-statements` | FinancialStatements | 재무제표 뷰어 |
| `/workspace/tasks` | TaskHierarchyTree | 태스크 계층 관리 |
| `/workspace/issues` | IssueTracker | 이슈 트래커 |
| `/workspace/documents` | Documents | 문서 관리 |
| `/workspace/working-papers` | WorkingPaperViewer | 조서 뷰어 |
| `/workspace/egas` | EGAList | EGA 목록 |
| `/workspace/hitl` | HITLQueue | Human-in-the-Loop 큐 |
| `/settings/agent-tools` | AgentToolsSettings | AI 에이전트 도구 설정 |
| `/settings/preferences` | UserPreferences | 사용자 설정 |

## 컴포넌트 아키텍처

### 레이아웃 구조

```
AppShell
├── NavigationRail (좌측 네비게이션)
├── ChatInterface (AI 채팅)
├── ArtifactPanel (아티팩트 표시)
│   └── ArtifactTabBar
└── [Content Area]
    ├── WorkspaceLayout (작업 공간)
    └── SettingsLayout (설정)
```

### 상태 관리

- **useChatStore**: 채팅 메시지 및 스트리밍 상태
- **useProjectStore**: 프로젝트 및 감사 데이터
- **useTaskStore**: 태스크 계층 및 상태
- **useArtifactStore**: 아티팩트 데이터 및 탭 관리
- **useHITLStore**: Human-in-the-Loop 요청 관리
- **useEGAStore**: Engagement Gap Analysis 관리
- **useEntityStore**: 엔티티 캐싱 및 상태
- **useSessionStore**: 세션 정보

### 커스텀 훅

- **useStreamingChat**: SSE 기반 AI 채팅 스트리밍
- **useRealtimeSync**: Supabase 실시간 동기화
- **useArtifactUpdates**: 아티팩트 업데이트 구독
- **useTaskActions**: 태스크 CRUD 작업

## UI 컴포넌트 (shadcn/ui)

Radix UI 기반의 접근성 높은 컴포넌트를 사용합니다:

- Accordion, Alert, Avatar, Badge, Button, Card
- Checkbox, Dialog, Dropdown Menu, Form, Input
- Label, Popover, Progress, Radio Group, Select
- Separator, Sheet, Skeleton, Slider, Switch
- Table, Tabs, Textarea, Toggle, Tooltip
- 그 외 다수...

## 테스트

### 단위 테스트

```bash
# 테스트 실행
npm run test

# 커버리지 포함
npm run test:coverage
```

커버리지 임계값: 80% (lines, functions, branches, statements)

### E2E 테스트

```bash
# E2E 테스트 실행 (백엔드 자동 시작)
npm run test:e2e

# UI 모드로 실행
npm run test:e2e:ui
```

E2E 테스트는 프론트엔드와 백엔드 서버를 자동으로 시작합니다.

## 개발 가이드

### 새 컴포넌트 추가

1. `src/app/components/` 아래 적절한 디렉토리에 생성
2. TypeScript와 JSDoc으로 타입 정의
3. 필요시 Zustand 스토어 연결
4. 단위 테스트 작성 (`__tests__/` 디렉토리)

### 새 페이지 추가

1. `src/app/App.tsx`에 라우트 정의
2. 컴포넌트 생성 및 연결
3. 네비게이션에 링크 추가

### 스타일링

- Tailwind CSS 유틸리티 클래스 사용
- `src/styles/theme.css`에서 테마 변수 정의
- `class-variance-authority`로 컴포넌트 변형 관리

## 라이선스

Private - All Rights Reserved

## 문의

프로젝트 관련 문의사항은 이슈를 통해 남겨주세요.
