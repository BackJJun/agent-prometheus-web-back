# Prometheus Web Backend Phase 1 Implementation Plan

## 목표

`C:\workspace\pmts-agent-web-back`에 Python 3.12 + FastAPI 기반 backend를 처음부터 구축한다.

1차 목표는 제품 기능에 필요한 실제 API 기반을 구축하는 것이다. React frontend의 mock 데이터는 frontend에서 제거하고, backend는 mock 구조가 아니라 제품 도메인 기준으로 API를 제공한다. RAG, LLM 응답 생성, repository sync 자동화는 후순위로 둔다.

## 확정 인프라

| 항목 | 값 |
|---|---|
| PostgreSQL container | postgre-pgvector |
| PostgreSQL image | pgvector/pgvector:pg17 |
| PostgreSQL version | 17.10 |
| DB name | agent_pmts |
| DB user | crux |
| DB password | crux5748#@12 |
| DB port | 5432 |
| Required extensions | pgcrypto, vector |
| Keycloak URL | http://localhost:18080 |
| Keycloak realm | agent-pmts |
| Frontend client | agent-pmts-web |
| Backend audience | agent-pmts-api |
| Test user | dev@prometheus.local |
| Test password | dev5748#@12 |

## 기본 원칙

- `users`는 web/plg 공통 사용자 기준이다.
- 사용자 등록은 web에서 시작되더라도 Keycloak에도 생성되어야 한다.
- 내부 `users.id`는 Keycloak user id 값과 동일하게 저장한다.
- 로그인과 비밀번호 관리는 Keycloak이 담당한다.
- backend는 Keycloak JWT 검증과 내부 사용자 매핑만 담당한다.
- web chat은 backend가 생성/저장한다.
- plugin history는 backend에서 읽기 전용으로만 제공한다.
- plugin 데이터 저장은 bridge 책임이다.
- dashboard는 web/plg/document/repository 상태를 통합 조회한다.
- pgvector 기반 embedding/RAG는 1차 MVP 이후 구현한다.

## 프로젝트 구조

```text
C:\workspace\pmts-agent-web-back
  app/
    main.py
    core/
      config.py
      database.py
      security.py
      keycloak.py
      exceptions.py
    api/
      router.py
      deps.py
      routes/
        health.py
        me.py
        dashboard.py
        chat.py
        plugin_history.py
        documents.py
        repositories.py
        monitoring.py
        settings.py
    models/
      common.py
      web.py
      plugin.py
    schemas/
      common.py
      dashboard.py
      chat.py
      plugin_history.py
      documents.py
      repositories.py
      monitoring.py
      settings.py
    repositories/
      dashboard_repository.py
      chat_repository.py
      plugin_history_repository.py
      document_repository.py
      repository_repository.py
    services/
      dashboard_service.py
      chat_service.py
      plugin_history_service.py
      document_service.py
      repository_service.py
      user_service.py
  migrations/
  tests/
  pyproject.toml
  alembic.ini
  .env.example
```

## 1단계: 프로젝트 골격

### 체크리스트

- [x] `pyproject.toml` 생성
- [x] Python 3.12 기준 dependency 정리
- [x] FastAPI `app/main.py` 생성
- [x] `.env.example` 생성
- [x] 공통 설정 `app/core/config.py` 생성
- [x] API router 구조 생성
- [x] `GET /health` 구현

### 검증

- [x] `uvicorn app.main:app --reload` 실행 가능
- [x] `GET /health` 응답 성공

## 2단계: DB 연결

### 체크리스트

- [x] async SQLAlchemy 설정
- [x] asyncpg 연결
- [x] session dependency 구현
- [x] `GET /health/db` 구현
- [x] `pgcrypto`, `vector` extension 확인 로직 구현

### 검증

- [x] `agent_pmts` DB 연결 성공
- [x] `pgcrypto` extension 확인
- [x] `vector` extension 확인
- [x] DB 연결 실패 시 명확한 오류 반환

## 3단계: Keycloak 인증

### 체크리스트

- [x] JWKS fetch 구현
- [x] JWKS caching 구현
- [x] JWT signature 검증
- [x] issuer 검증
- [x] audience `agent-pmts-api` 검증
- [x] `iss + sub` 기반 `user_auth_identities` 조회
- [x] 내부 `users` 자동 생성 또는 조회 구현
- [x] `user_auth_identities` 자동 생성 또는 조회 구현
- [x] `GET /api/me` 구현

### 검증

- [x] Keycloak test user token으로 `/api/me` 성공
- [x] 잘못된 token 거부
- [x] audience 없는 token 거부
- [x] 만료 token 거부

## 4단계: Dashboard API

### 체크리스트

- [x] `GET /api/dashboard/summary` 구현
- [x] web chat count 조회
- [x] plugin task count 조회
- [x] document indexing count 조회
- [x] repository connection count 조회
- [x] recent plugin failures 조회
- [x] recent document jobs 조회
- [x] recent commits 조회

### 검증

- [x] 빈 DB에서도 500 없이 기본값 반환
- [x] dashboard 제품 화면에 필요한 실제 응답 구조 제공
- [x] query timeout 또는 DB 오류 시 명확한 오류 반환

## 5단계: Web Chat API

### 체크리스트

- [x] `GET /api/chat/sessions` 구현
- [x] `POST /api/chat/sessions` 구현
- [x] `GET /api/chat/sessions/{session_id}` 구현
- [x] `GET /api/chat/sessions/{session_id}/messages` 구현
- [x] `POST /api/chat/sessions/{session_id}/messages` 구현
- [x] 초기 assistant 응답 placeholder 저장
- [x] session archive 처리 구현

### 검증

- [x] 세션 생성 가능
- [x] 메시지 저장 가능
- [x] 세션별 메시지 조회 가능
- [x] 사용자/workspace 기준 조회 제한 가능
- [x] 삭제/아카이브된 세션 처리 확인

## 6단계: Plugin History Read-only API

### 체크리스트

- [x] `GET /api/plugin-histories` 구현
- [x] `GET /api/plugin-histories/{task_id}` 구현
- [x] `GET /api/plugin-histories/{task_id}/messages` 구현
- [x] `GET /api/plugin-histories/{task_id}/events` 구현
- [x] `GET /api/plugin-histories/{task_id}/files` 구현
- [x] 입력/수정/삭제 API를 만들지 않음

### 검증

- [x] plg 데이터가 없어도 빈 목록 반환
- [x] read-only 원칙 유지
- [x] task detail 화면에 필요한 구조 반환
- [x] plugin task가 없을 때 404 반환

## 7단계: Documents API

### 체크리스트

- [x] `GET /api/documents` 구현
- [x] `POST /api/documents` 구현
- [x] `GET /api/documents/{id}` 구현
- [x] `GET /api/documents/{id}/versions` 구현
- [x] `GET /api/documents/index-jobs` 구현
- [x] 일반 문서와 코드 문서 구분 필드 정리
- [x] 초기 파일 업로드는 metadata 중심으로 구현

### 검증

- [x] 일반 문서 목록 조회 가능
- [x] 코드 문서 목록 조회 가능
- [x] indexing status 조회 가능
- [x] document version 조회 가능

## 8단계: Repositories API

### 체크리스트

- [x] `GET /api/repository-providers` 구현
- [x] `GET /api/repository-groups` 구현
- [x] `GET /api/repository-connections` 구현
- [x] `GET /api/repository-connections/{id}` 구현
- [x] `GET /api/repository-connections/{id}/branches` 구현
- [x] `GET /api/repository-connections/{id}/commits` 구현

### 검증

- [x] provider 목록 조회 가능
- [x] group 목록 조회 가능
- [x] repository connection 목록 조회 가능
- [x] branch 목록 조회 가능
- [x] commit 목록 조회 가능
- [x] Gitea/GitLab 저장소 조회 화면에 필요한 실제 응답 구조 제공

## 9단계: Monitoring / Settings API

### 체크리스트

- [x] `GET /api/monitoring/events` 구현
- [x] `GET /api/monitoring/health-checks` 구현
- [x] `GET /api/settings/llm-providers` 구현
- [x] `GET /api/settings/llm-models` 구현
- [x] notification settings 조회 API 구현

### 검증

- [x] monitoring 화면이 빈 데이터에서도 정상 렌더링 가능
- [x] settings 화면이 빈 데이터에서도 정상 렌더링 가능

## 10단계: 테스트 / 품질

### 체크리스트

- [x] pytest 설정
- [x] ruff 설정
- [x] health/db 테스트
- [x] auth 테스트
- [x] dashboard 테스트
- [x] chat API 테스트
- [x] plugin history read-only 테스트
- [x] documents API 테스트
- [x] repositories API 테스트

### 검증 명령

```powershell
pytest
ruff check .
ruff format --check .
```

## 추천 구현 순서

1. 프로젝트 골격
2. DB 연결
3. Keycloak 인증
4. `/api/me`
5. Dashboard API
6. Web Chat API
7. Plugin History read-only API
8. Documents API
9. Repositories API
10. Monitoring / Settings API
11. frontend 실제 API 연동

## 1차 완료 기준

- [x] FastAPI 서버가 로컬에서 실행된다.
- [x] DB health check가 성공한다.
- [x] Keycloak token으로 `/api/me`가 성공한다.
- [x] Dashboard API가 빈 DB에서도 정상 응답한다.
- [x] Web Chat 세션과 메시지를 생성/조회할 수 있다.
- [x] Plugin History API가 읽기 전용으로 동작한다.
- [x] Documents / Repositories 목록 API가 제품 화면에서 사용할 수 있는 형태로 응답한다.
- [x] pytest 기본 테스트가 통과한다.
- [ ] frontend가 제품 기능 API를 기준으로 실제 데이터를 조회/생성할 수 있다.

## 후순위 작업

- 실제 LLM 응답 streaming
- SSE 기반 chat streaming
- document file storage
- document parsing worker
- embedding 생성
- pgvector similarity search
- codeRAG
- repository sync worker
- plugin bridge sync API 강화
- production Keycloak 설정 분리