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
│  │  ├─ img/
│  │  │  └─ planb-nas-icon.png
│  │  └─ js/
│  │     ├─ auth_session.js
│  │     ├─ dashboard.js
│  │     ├─ files.js
│  │     ├─ session_guard.js
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
├─ deploy/
│  ├─ deploy_to_pi.ps1
│  ├─ planb-nas.service
│  ├─ raspberry-pi.env.example
│  └─ remote_install.sh
├─ .env
├─ .env.example
├─ DEPLOY_RASPBERRY_PI.md
├─ requirements.txt
├─ run.py
├─ wsgi.py
└─ README.md
```

<br>

## 환경변수

실제 실행 설정은 `.env`에서 읽습니다. `.env.example`은 참고용 샘플입니다.

<br>

## 역할별 권한

| 역할 | 읽기 | 생성/업로드 | 다운로드 | 이름 변경 | 내용 수정 | 삭제 | 대시보드 |
|------|------|-------------|----------|-----------|-----------|------|----------|
| Admin | 가능 | 가능 | 가능 | 가능 | 불가 | 가능 | 가능 |
| Editor | 가능 | 가능 | 가능 | 가능 | 불가 | 불가 | 가능 |
| Viewer | 가능 | 불가 | 불가 | 불가 | 불가 | 불가 | 불가 |

현재 파일 내용 직접 수정 기능은 비활성화되어 있습니다.  
Admin과 Editor는 파일 및 폴더 이름 변경만 수행할 수 있습니다.

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

`/files` 화면에서 NAS 공유 폴더 또는 설정된 감시 폴더를 웹으로 탐색할 수 있습니다.

지원 기능은 다음과 같습니다.

- 파일 열기
- 파일 및 폴더 생성
- 파일 업로드
- 파일 다운로드
- 파일 및 폴더 이름 변경
- 파일 및 폴더 삭제

현재 사이트에서 직접 수정 가능한 확장자는 다음과 같습니다.

```text
.txt, .md, .csv, .log, .json, .xml, .html, .css, .js, .py
```

이미지, PDF, 동영상 같은 바이너리 파일은 열기/다운로드/삭제 중심으로 처리합니다.

### 변경사항 (2026-07-27)
파일 내용 직접 수정 기능은 현재 비활성화되어 있습니다.
삭제는 관리자만 수행할 수 있으며, 일반 사용자는 생성, 업로드, 다운로드, 이름 변경까지만 가능합니다.

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

## 세션 보호


로그인 성공 시 브라우저 세션 스토리지에 활성 세션 상태를 저장합니다.

이후 보호된 페이지에 접근할 때 세션 상태가 없으면 서버 세션을 정리하고 로그인 화면으로 이동합니다.  
이를 통해 브라우저 재진입 또는 비정상적인 세션 상태에서 보호 페이지가 그대로 노출되는 상황을 줄입니다.

관련 파일:

```text
app/static/js/auth_session.js
app/static/js/session_guard.js
```

<br>

## 주요 API

### 관리자 및 사용자

```
GET    /health
GET    /api/events
GET    /api/users
GET    /api/ip-blocks
GET    /api/security-logs
GET    /dashboard
GET    /file-events
GET    /security-logs
```
관리자 전용:
```
GET    /settings
GET    /users
GET    /blocked-ips
GET    /api/settings
PATCH  /api/settings
PATCH  /api/users/<user_id>
POST   /api/ip-blocks
DELETE /api/ip-blocks/<ip_address>
POST   /files/delete/<subpath>
```
로그인 사용자:
```
GET /files
GET /files/<subpath>
GET /files/open/<subpath>
```
관리자 및 사용자 파일 작업:
```
POST /files/create
POST /files/upload
GET  /files/download/<subpath>
POST /files/rename/<subpath>
세션
GET  /logout
POST /session/logout
```

<br>

## 보안 참고

이 시스템은 웹 포털을 통해 들어오는 파일 작업을 역할 기반으로 제어합니다. 하지만 사용자가 Windows 파일 탐색기에서 NAS 공유 경로에 직접 접근할 수 있다면 웹 권한을 우회할 수 있습니다.

운영 시 권장 구조:

```text
사용자 → SecureNas 웹 포털 → Flask 서버 계정 → NAS 공유 폴더
```

<br>

## 최근 업데이트 내용 (2026-07-27)

이번 작업을 통해 SecureNas Monitor는 단순 파일 이벤트 모니터링 도구에서 NAS 웹 접근 포털에 더 가까운 형태로 확장되었습니다.

- Raspberry Pi 배포 환경 지원 추가
- `wsgi.py` 기반 Gunicorn 실행 구조 추가
- systemd 서비스 파일 추가
- Tailscale을 통한 외부 접속 구성 문서 추가
- CIFS 마운트를 통한 NAS 공유 폴더 연동 방식 정리
- NAS 경로 설정 검증 로직 추가
- Windows 매핑 드라이브 사용 여부 설정 추가
- 파일 이름 변경 기능 추가
- 파일 내용 직접 수정 기능 비활성화
- 사용자 역할의 대시보드 접근 권한 확장
- 파일 이벤트 중복 기록 방지 로직 개선
- SMB 임시 파일 이벤트 필터링 추가
- 브라우저 세션 보호용 클라이언트 스크립트 추가