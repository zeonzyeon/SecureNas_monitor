# 🖥️ SecureNas monitor

NAS 공유 폴더의 파일 접근 이벤트를 실시간으로 탐지하고, 웹 포털에서 역할 기반(RBAC)으로 파일 접근을 제어하는 보안 모니터링 시스템입니다.

<br>

## 문제 정의
NAS가 전세계 보안 환경에서 가장 인기있는 '은닉 인프라'로 사용되는 상황에서 정상 계정으로 위장한 악성 접근 및 내부자의 비정상적 대량 데이터 반출 행위를 Storage 레벨에서 식별하고, 확인할 수 있는 솔루션이 부재된 상황

<br>

## 주요 기능

- NAS 또는 로컬 테스트 폴더의 파일 생성/수정/삭제 이벤트 실시간 탐지
- SQLite 기반 이벤트/사용자/로그 저장
- 회원가입 및 로그인
- 관리자 승인 후 계정 활성화
- 역할 기반 접근 제어
- 로그인 실패 누적 시 IP 자동 차단
- 관리자 대시보드 및 상세 관리 페이지
- 웹에서 파일 열기/생성/업로드/다운로드/수정/삭제
- Settings 화면에서 감시 경로 직접 변경

<br>

## 개발환경

| 구분 | 내용 |
|------|------|
| 개발 언어 | Python |
| 백엔드 | Flask |
| 프론트엔드 | HTML5, CSS3, JavaScript |
| 데이터베이스 | SQLite3 |
| 파일 모니터링 | Watchdog |

<br>

## 프로젝트 구조

```text
SecureNas_monitor/
├─ app/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ db.py
│  ├─ models.py
│  ├─ nas_paths.py
│  ├─ routes.py
│  ├─ auth/
│  │  ├─ __init__.py
│  │  ├─ decorators.py
│  │  ├─ models.py
│  │  └─ routes.py
│  ├─ monitor/
│  │  ├─ __init__.py
│  │  ├─ event_handler.py
│  │  └─ watcher.py
│  ├─ static/
│  │  ├─ css/
│  │  │  ├─ auth.css
│  │  │  ├─ dashboard.css
│  │  │  └─ files.css
│  │  └─ js/
│  │     ├─ dashboard.js
│  │     └─ settings.js
│  └─ templates/
│     ├─ blocked_ips.html
│     ├─ dashboard.html
│     ├─ edit_file.html
│     ├─ file_events.html
│     ├─ files.html
│     ├─ login.html
│     ├─ register.html
│     ├─ security_logs.html
│     ├─ settings.html
│     └─ users.html
├─ .env
├─ .env.example
├─ requirements.txt
├─ run.py
└─ README.md
```

<br>

## 환경변수

실제 실행 설정은 `.env`에서 읽습니다. `.env.example`은 참고용 샘플입니다.

<br>

## 역할별 권한

| 역할 | 읽기 | 생성/업로드 | 다운로드 | 수정 | 삭제 | 대시보드 |
| --- | --- | --- | --- | --- | --- | --- |
| 관리자 | 가능 | 가능 | 가능 | 가능 | 가능 | 가능 |
| 사용자 | 가능 | 가능 | 가능 | 가능 | 불가 | 불가 |
| 열람자 | 가능 | 불가 | 불가 | 불가 | 불가 | 불가 |

<br>

## 화면

- `/login`: 로그인
- `/register`: 회원가입
- `/files`: 파일 관리
- `/dashboard`: 관리자 대시보드
- `/users`: 사용자 승인 및 역할 관리
- `/file-events`: 파일 이벤트 전체보기
- `/security-logs`: 보안 로그 전체보기
- `/blocked-ips`: IP 차단 관리
- `/settings`: 감시 경로 설정

관리자로 로그인하면 기본적으로 대시보드로 이동합니다. 일반 사용자와 열람자는 파일 관리로 이동합니다.
파일 관리 작업은 대시보드의 `파일 관리` 버튼 또는 `/files`에서 수행합니다.

<br>

## 파일 관리 기능

`/files`에서 NAS 공유 폴더를 웹으로 탐색합니다.

- 파일 열기
- 파일/폴더 생성
- 파일 업로드
- 파일 다운로드
- 파일 수정
- 파일/폴더 삭제

현재 사이트에서 직접 수정 가능한 확장자는 다음과 같습니다.

```text
.txt, .md, .csv, .log, .json, .xml, .html, .css, .js, .py
```

이미지, PDF, 동영상 같은 바이너리 파일은 열기/다운로드/삭제 중심으로 처리합니다.

<br>

## 관리자 대시보드

관리자 대시보드에서는 요약 정보와 최근 기록을 확인합니다.

- 최근 등록된 사용자
- 최근 파일 이벤트
- 최근 보안 로그

사용자 승인, 파일 이벤트, 보안 로그는 각 패널의 `전체보기` 버튼으로 상세 페이지에 이동합니다.

<br>

## 로그인 실패 및 IP 차단

로그인 실패가 `LOGIN_MAX_FAILED_ATTEMPTS`에 도달하면 해당 IP가 자동 차단됩니다.

기본 설정:

```text
3회 실패 시 10분 차단
```

차단된 IP에서 로그인 화면 또는 로그인 요청이 들어오면 차단 안내가 표시되고, 시도 내역은 로그인 로그에 기록됩니다.

관련 DB 테이블:

- `login_logs`: 로그인 성공/실패, 차단 시도, IP 차단/해제 이벤트 기록
- `ip_blocks`: IP별 실패 횟수, 차단 상태, 차단 만료 시각 저장

<br>

## 주요 API

관리자 전용:

```text
GET    /health
GET    /api/settings
PATCH  /api/settings
GET    /api/events
GET    /api/users
PATCH  /api/users/<user_id>
GET    /api/ip-blocks
POST   /api/ip-blocks
DELETE /api/ip-blocks/<ip_address>
GET    /api/security-logs
```

로그인 사용자:

```text
GET /files
GET /files/<subpath>
GET /files/open/<subpath>
```

관리자/사용자:

```text
POST /files/create
POST /files/upload
GET  /files/download/<subpath>
```

관리자/사용자 파일 수정:

```text
GET  /files/edit/<subpath>
POST /files/edit/<subpath>
```

관리자 전용 파일 작업:

```text
POST /files/delete/<subpath>
```

<br>

## 보안 참고

이 시스템은 웹 포털을 통해 들어오는 파일 작업을 역할 기반으로 제어합니다. 하지만 사용자가 Windows 파일 탐색기에서 NAS 공유 경로에 직접 접근할 수 있다면 웹 권한을 우회할 수 있습니다.

운영 시 권장 구조:

```text
사용자 → SecureNas 웹 포털 → Flask 서버 계정 → NAS 공유 폴더
```
