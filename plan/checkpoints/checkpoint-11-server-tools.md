# Checkpoint 11: FRP 서버 관리 도구 (CLI & TUI)

## 개요
FRP 서버를 효율적으로 관리하고 모니터링할 수 있는 CLI 및 TUI 도구를 구현합니다. 서버 설치부터 실시간 모니터링, 클라이언트 관리까지 전체 서버 라이프사이클을 지원합니다.

## 목표
- **서버 자동화**: FRP 서버 설치, 설정, 시작/중지 자동화
- **실시간 모니터링**: 연결된 클라이언트, 터널, 트래픽 모니터링
- **보안 관리**: 인증, 접근 제어, 화이트리스트 관리
- **성능 최적화**: 리소스 사용량 분석 및 최적화 제안
- **운영 편의성**: 로그 관리, 백업, 복구 기능

## 명령어 구조

### CLI 도구: `cli-frps`

#### 1. 서버 설치 및 초기 설정
```bash
# FRP 서버 설치
cli-frps install

🔍 최신 FRP 서버 버전 확인 중... (v0.55.1)
⬇️  FRP 서버 다운로드 중... ████████████ 100%
📁 설치 위치: /opt/frp-server/
🔧 기본 설정 파일 생성 중...

✅ FRP 서버 설치 완료!
🚀 'cli-frps setup'으로 초기 설정을 시작하세요.

# 초기 설정 마법사
cli-frps setup

🎯 FRP 서버 초기 설정을 시작합니다!

🌐 서버 바인드 주소 (0.0.0.0):
🔌 바인드 포트 (7000):
🔑 인증 토큰 생성: [자동 생성] abc123def456...
📊 대시보드 활성화 (Y/n): y
🌍 대시보드 포트 (7500):
👤 대시보드 사용자명: admin
🔐 대시보드 비밀번호: [입력 숨김]

📋 설정 요약:
├─ 서버 주소: 0.0.0.0:7000
├─ 인증 토큰: abc123def456...
├─ 대시보드: http://localhost:7500
└─ 설정 파일: /opt/frp-server/frps.toml

✅ 설정이 완료되었습니다!
🚀 'cli-frps start'로 서버를 시작하세요.
```

#### 2. 서버 관리
```bash
# 서버 시작
cli-frps start

🚀 FRP 서버 시작 중...
📡 포트 7000에서 수신 대기...
🌍 대시보드: http://localhost:7500
✅ 서버가 성공적으로 시작되었습니다! (PID: 12345)

# 서버 상태 확인
cli-frps status

🖥️  FRP 서버 상태:
┌─────────────────┬──────────────────────────┐
│ 상태            │ 🟢 실행 중 (2h 15m)      │
│ PID             │ 12345                    │
│ 바인드 포트     │ 0.0.0.0:7000             │
│ 대시보드        │ http://localhost:7500    │
│ 연결된 클라이언트│ 3개                      │
│ 활성 터널       │ 7개                      │
│ 총 전송량       │ 245.8 MB (↑) 189.2 MB (↓)│
│ 메모리 사용량   │ 45.2 MB                  │
│ CPU 사용률      │ 2.3%                     │
└─────────────────┴──────────────────────────┘

# 서버 중지
cli-frps stop

🛑 FRP 서버 종료 중...
📡 새 연결 차단...
⏳ 기존 연결 정리 중... (3개 클라이언트)
✅ 서버가 안전하게 종료되었습니다.

# 서버 재시작
cli-frps restart

🔄 FRP 서버 재시작 중...
🛑 기존 서버 종료... ✅
🚀 새 서버 시작... ✅
📡 포트 7000에서 수신 대기...
✅ 서버가 성공적으로 재시작되었습니다!
```

#### 3. 클라이언트 관리
```bash
# 연결된 클라이언트 목록
cli-frps clients

📋 연결된 클라이언트:
┌─────────────┬─────────────────┬─────────────┬──────────┬──────────────┐
│ 클라이언트  │ IP 주소         │ 연결 시간   │ 터널 수  │ 전송량       │
├─────────────┼─────────────────┼─────────────┼──────────┼──────────────┤
│ dev-laptop  │ 192.168.1.100   │ 2h 15m      │ 3        │ 145.2 MB     │
│ prod-server │ 203.0.113.50    │ 1h 30m      │ 2        │ 89.6 MB      │
│ staging-vm  │ 10.0.0.25       │ 45m         │ 2        │ 23.4 MB      │
└─────────────┴─────────────────┴─────────────┴──────────┴──────────────┘

# 특정 클라이언트 상세 정보
cli-frps client dev-laptop

🖥️  클라이언트 정보: dev-laptop
├─ IP 주소: 192.168.1.100:52341
├─ 연결 시간: 2024-01-15 12:15:30 (2h 15m 전)
├─ 인증: ✅ 성공
├─ 버전: frpc/0.55.1
├─ OS: Windows 11
├─ 활성 터널: 3개
├─ 총 요청: 1,245
├─ 전송량: 145.2 MB (↑) 98.7 MB (↓)
├─ 평균 응답시간: 89ms
└─ 마지막 활동: 2초 전

📡 터널 목록:
├─ myapp (3000 → /myapp/) - 1,089 요청
├─ api (8080 → /api/v1/) - 134 요청
└─ dev (5000 → /dev/) - 22 요청

# 클라이언트 연결 해제
cli-frps disconnect dev-laptop

⚠️  클라이언트 'dev-laptop' 연결을 해제하시겠습니까? (y/N): y
🔌 연결 해제 중...
📡 3개 터널 종료됨
✅ 클라이언트가 연결 해제되었습니다.
```

#### 4. 터널 관리
```bash
# 모든 터널 목록
cli-frps tunnels

📋 활성 터널:
┌──────────────┬─────────────┬──────────┬────────────────┬──────────┬──────────────┐
│ 터널명       │ 클라이언트  │ 로컬포트 │ 공개 경로      │ 상태     │ 요청/분      │
├──────────────┼─────────────┼──────────┼────────────────┼──────────┼──────────────┤
│ myapp        │ dev-laptop  │ 3000     │ /myapp/        │ 🟢 활성  │ 125          │
│ api          │ dev-laptop  │ 8080     │ /api/v1/       │ 🟢 활성  │ 45           │
│ prod-web     │ prod-server │ 80       │ /              │ 🟢 활성  │ 289          │
│ prod-api     │ prod-server │ 8000     │ /api/          │ 🟢 활성  │ 156          │
│ staging-app  │ staging-vm  │ 3000     │ /staging/      │ 🟡 지연  │ 12           │
│ dev-site     │ dev-laptop  │ 5000     │ /dev/          │ 🔴 오류  │ 0            │
└──────────────┴─────────────┴──────────┴────────────────┴──────────┴──────────────┘

# 터널 상세 정보
cli-frps tunnel myapp

🔗 터널 상세 정보: myapp
├─ 소유자: dev-laptop (192.168.1.100)
├─ 로컬 주소: localhost:3000
├─ 공개 URL: https://example.com/myapp/
├─ 생성 시간: 2024-01-15 12:20:15 (2h 10m 전)
├─ 상태: 🟢 활성
├─ 총 요청: 1,089
├─ 성공률: 98.7% (1,075/1,089)
├─ 평균 응답시간: 89ms
├─ 전송량: 67.8 MB (↑) 45.3 MB (↓)
└─ 마지막 요청: 2초 전

📊 최근 1시간 통계:
├─ 요청 수: ████████████████████ 125/분
├─ 응답시간: ████████░░░░░░░░░░ 89ms (평균)
├─ 오류율: ██░░░░░░░░░░░░░░░░░░ 1.3%
└─ 대역폭: ████████████░░░░░░░░ 2.3 MB/분

# 문제 있는 터널 강제 종료
cli-frps kill dev-site

⚠️  터널 'dev-site'를 강제 종료하시겠습니까? (y/N): y
🔌 터널 종료 중...
✅ 터널이 종료되었습니다.
```

#### 5. 로그 관리
```bash
# 실시간 로그 확인
cli-frps logs

[실시간 로그 스트림]
2024-01-15 14:30:15 [INFO ] 새 클라이언트 연결: dev-laptop (192.168.1.100)
2024-01-15 14:30:16 [INFO ] 터널 생성: myapp -> 192.168.1.100:3000
2024-01-15 14:30:45 [WARN ] 느린 응답: myapp (2.3초)
2024-01-15 14:31:12 [ERROR] 터널 연결 실패: dev-site (연결 거부됨)
2024-01-15 14:31:30 [INFO ] 요청 처리: GET /myapp/api/users (89ms)

# 특정 레벨 로그만 표시
cli-frps logs --level error

[오류 로그만 표시]
2024-01-15 14:31:12 [ERROR] 터널 연결 실패: dev-site (연결 거부됨)
2024-01-15 14:25:33 [ERROR] 인증 실패: 192.168.1.200 (잘못된 토큰)
2024-01-15 14:18:45 [ERROR] 대역폭 한도 초과: prod-server

# 로그 저장
cli-frps logs --save server-logs-$(date +%Y%m%d).log

📁 로그를 저장하는 중...
✅ 로그가 'server-logs-20240115.log'에 저장되었습니다.
```

#### 6. 설정 관리
```bash
# 현재 설정 확인
cli-frps config show

📋 현재 서버 설정:
┌─────────────────┬────────────────────────┐
│ 바인드 주소     │ 0.0.0.0:7000           │
│ 인증 토큰       │ abc123...              │
│ 대시보드        │ :7500 (활성)           │
│ 최대 클라이언트 │ 100                    │
│ 연결 타임아웃   │ 90초                   │
│ 하트비트 간격   │ 30초                   │
│ 로그 레벨       │ INFO                   │
└─────────────────┴────────────────────────┘

# 설정 변경
cli-frps config set max_clients 200

✅ 최대 클라이언트 수가 200으로 변경되었습니다.
🔄 설정을 적용하려면 서버를 재시작하세요.

# 설정 백업
cli-frps config backup

📁 설정 백업 중...
✅ 설정이 'frps-config-backup-20240115.toml'에 백업되었습니다.
```

#### 7. 보안 관리
```bash
# 접근 제어 목록 관리
cli-frps security whitelist

📋 허용된 클라이언트:
├─ 192.168.1.0/24 (로컬 네트워크)
├─ 203.0.113.50 (prod-server)
└─ 198.51.100.25 (staging-server)

# IP 화이트리스트에 추가
cli-frps security allow 10.0.0.0/8

✅ IP 범위 '10.0.0.0/8'가 화이트리스트에 추가되었습니다.

# 차단된 IP 목록
cli-frps security blacklist

📋 차단된 클라이언트:
├─ 192.168.1.200 (인증 실패 5회)
├─ 203.0.113.100 (무차별 대입 공격)
└─ 198.51.100.50 (비정상 트래픽)

# 인증 토큰 재생성
cli-frps security regenerate-token

⚠️  새 토큰을 생성하면 모든 클라이언트가 재연결해야 합니다.
계속하시겠습니까? (y/N): y

🔑 새 인증 토큰 생성 중...
✅ 새 토큰: xyz789abc123def456...
📋 모든 클라이언트에게 새 토큰을 배포하세요.
```

#### 8. 성능 분석
```bash
# 서버 성능 통계
cli-frps stats

📊 서버 성능 통계 (지난 24시간):
┌─────────────────┬────────────────────────┐
│ 총 연결 수      │ 1,245                  │
│ 평균 동시 연결  │ 15                     │
│ 최대 동시 연결  │ 23                     │
│ 총 요청 수      │ 45,678                 │
│ 평균 응답시간   │ 156ms                  │
│ 총 전송량       │ 2.3 GB                 │
│ 평균 CPU 사용률 │ 3.2%                   │
│ 평균 메모리 사용│ 58.4 MB                │
└─────────────────┴────────────────────────┘

📈 시간대별 트래픽:
00-06: ████░░░░░░░░░░░░░░░░ 20%
06-12: ████████████████░░░░ 80%
12-18: ████████████████████ 100% ← 피크 시간
18-24: ████████░░░░░░░░░░░░ 40%

🔍 최적화 제안:
├─ CPU: 현재 사용률이 낮습니다 (3.2%)
├─ 메모리: 적정 수준입니다 (58.4 MB)
├─ 네트워크: 대역폭 사용률 65% (적정)
└─ 💡 피크 시간(12-18시) 대비 권장: 최대 연결 수 50개
```

### TUI 도구: `tui-frps`

#### 메인 대시보드
```
┌─ FRP Server Manager ──────────────────────────────────────────────────┐
│ 서버: example.com:7000   상태: 🟢 실행중 (2h 15m)   업타임: 99.8%      │
├───────────────────────────────────────────────────────────────────────┤
│ ■ Dashboard  ○ Clients  ○ Tunnels  ○ Logs  ○ Security  ○ Config      │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ 📊 실시간 통계                    🔗 활성 터널: 7개                    │
│ ┌─ 연결 상태 ─────┐               ├─ myapp (dev-laptop)               │
│ │ 클라이언트: 3개  │               ├─ api (dev-laptop)                 │
│ │ 터널: 7개        │               ├─ prod-web (prod-server)           │
│ │ 요청/분: 245     │               ├─ prod-api (prod-server)           │
│ │ 응답시간: 89ms   │               ├─ staging-app (staging-vm)         │
│ └─────────────────┘               └─ admin-panel (staging-vm)         │
│                                                                       │
│ 📈 시간대별 트래픽                 ⚠️  최근 이벤트                      │
│ ████████████████████ 100%         ├─ 14:30 새 클라이언트 연결          │
│ ████████████░░░░░░░░ 60%          ├─ 14:25 터널 생성: admin-panel     │
│ ████████░░░░░░░░░░░░ 40%          ├─ 14:23 느린 응답: staging-app     │
│ ████░░░░░░░░░░░░░░░░ 20%          └─ 14:20 인증 실패: 192.168.1.200  │
│                                                                       │
│ 💾 리소스 사용량                   🚨 알림                             │
│ CPU:  ████░░░░░░ 25%              ├─ staging-app 응답시간 증가         │
│ RAM:  ████████░░ 65%              ├─ 디스크 사용량 80% 초과           │
│ DISK: ████████░░ 75%              └─ 5분간 3회 인증 실패 감지         │
│ NET:  ████████░░ 70%                                                  │
│                                                                       │
│ <r>efresh <s>tart <x>stop <c>lients <t>unnels <l>ogs <q>uit          │
└───────────────────────────────────────────────────────────────────────┘
```

#### 클라이언트 관리 화면
```
┌─ Client Management ───────────────────────────────────────────────────┐
│ Filter: [all_______________] Sort: connection_time ↓  Auto-refresh: ✓ │
├───────────────────────────────────────────────────────────────────────┤
│ CLIENT      │ IP ADDRESS      │ CONNECTED   │ TUNNELS │ TRAFFIC    │ ST│
├─────────────┼─────────────────┼─────────────┼─────────┼────────────┼───┤
│ > dev-laptop│ 192.168.1.100   │ 2h 15m      │ 3       │ 145.2 MB   │🟢 │
│   prod-srv  │ 203.0.113.50    │ 1h 30m      │ 2       │ 89.6 MB    │🟢 │
│   staging   │ 10.0.0.25       │ 45m         │ 2       │ 23.4 MB    │🟡 │
├───────────────────────────────────────────────────────────────────────┤
│ Details: dev-laptop                                                   │
│ ├─ IP: 192.168.1.100:52341        ├─ Version: frpc/0.55.1            │
│ ├─ Connected: 2h 15m ago          ├─ OS: Windows 11                  │
│ ├─ Auth: ✅ Success               ├─ Last ping: 2s ago               │
│ ├─ Tunnels: 3 active             ├─ Avg response: 89ms              │
│ └─ Traffic: 145.2MB ↑ 98.7MB ↓    └─ Total requests: 1,245          │
│                                                                       │
│ Active Tunnels:                                                       │
│ ├─ myapp (3000 → /myapp/) - 1,089 requests                          │
│ ├─ api (8080 → /api/v1/) - 134 requests                             │
│ └─ dev (5000 → /dev/) - 22 requests                                  │
├───────────────────────────────────────────────────────────────────────┤
│ <d>isconnect <k>ill <b>an <i>nfo <m>essage <r>efresh <q>uit          │
└───────────────────────────────────────────────────────────────────────┘
```

#### 터널 모니터링 화면
```
┌─ Tunnel Monitor ──────────────────────────────────────────────────────┐
│ Active: 7  Inactive: 1  Total Requests: 12,456  Avg Response: 89ms   │
├───────────────────────────────────────────────────────────────────────┤
│ NAME         │CLIENT      │LOCAL │PATH        │STATUS   │REQ/MIN│RESP │
├──────────────┼────────────┼──────┼────────────┼─────────┼───────┼─────┤
│ > myapp      │dev-laptop  │3000  │/myapp/     │🟢 ACTIVE│ 125   │89ms │
│   api        │dev-laptop  │8080  │/api/v1/    │🟢 ACTIVE│ 45    │156ms│
│   prod-web   │prod-server │80    │/           │🟢 ACTIVE│ 289   │67ms │
│   prod-api   │prod-server │8000  │/api/       │🟢 ACTIVE│ 156   │123ms│
│   staging    │staging-vm  │3000  │/staging/   │🟡 SLOW  │ 12    │2.3s │
│   admin      │staging-vm  │8888  │/admin/     │🟢 ACTIVE│ 8     │234ms│
│   dev-site   │dev-laptop  │5000  │/dev/       │🔴 ERROR │ 0     │-    │
├───────────────────────────────────────────────────────────────────────┤
│ Tunnel Details: myapp                                                 │
│ ┌─ Performance ──────────────┐ ┌─ Recent Activity ─────────────────────┐│
│ │ Requests: ████████████ 125 │ │ 14:30:15 GET /myapp/api/users (89ms) ││
│ │ Success:  ████████████ 98% │ │ 14:30:12 POST /myapp/auth (156ms)    ││
│ │ Errors:   ██░░░░░░░░░░ 2%  │ │ 14:30:08 GET /myapp/dashboard (45ms) ││
│ │ Avg Time: ████████░░░ 89ms │ │ 14:30:05 GET /myapp/static/app.css   ││
│ └────────────────────────────┘ └───────────────────────────────────────┘│
│                                                                       │
│ ⚠️  Issues Detected:                                                   │
│ ├─ staging: Response time > 2s (threshold: 1s)                       │
│ ├─ dev-site: Connection refused (port 5000 not listening)            │
│ └─ prod-api: Error rate 5% (last 10 minutes)                         │
├───────────────────────────────────────────────────────────────────────┤
│ <k>ill <r>estart <d>etails <f>ilter <e>xport <h>ealth <q>uit         │
└───────────────────────────────────────────────────────────────────────┘
```

#### 로그 뷰어 화면
```
┌─ Server Logs ─────────────────────────────────────────────────────────┐
│ Level: [ALL ▼] Client: [ALL ▼] Follow: ✓ Filter: [error______________]│
├───────────────────────────────────────────────────────────────────────┤
│ 2024-01-15 14:30:15 [INFO ] 새 클라이언트 연결: dev-laptop            │
│ 2024-01-15 14:30:16 [INFO ] 터널 생성: myapp -> 192.168.1.100:3000   │
│ 2024-01-15 14:30:17 [INFO ] HTTP 요청: GET /myapp/ -> 200 (89ms)     │
│ 2024-01-15 14:30:45 [WARN ] 느린 응답: staging-app (2.3초)           │
│ 2024-01-15 14:31:12 [ERROR] 터널 연결 실패: dev-site (연결 거부됨)     │
│ 2024-01-15 14:31:15 [INFO ] 재연결 시도: dev-site (1/3)              │
│ 2024-01-15 14:31:30 [ERROR] 재연결 실패: dev-site (연결 거부됨)       │
│ 2024-01-15 14:31:45 [WARN ] 클라이언트 하트비트 지연: staging-vm      │
│ 2024-01-15 14:32:00 [INFO ] HTTP 요청: POST /api/auth -> 200 (156ms) │
│ 2024-01-15 14:32:15 [ERROR] 인증 실패: 192.168.1.200 (잘못된 토큰)    │
│ 2024-01-15 14:32:30 [INFO ] 터널 복구: staging-app                   │
│ │                                                                     │
│ ████████████████████████████████████████████████ [following logs...] │
├───────────────────────────────────────────────────────────────────────┤
│ ⚠️  Error Summary (Last Hour):                                        │
│ ├─ Connection Errors: 12 (dev-site 포트 미사용)                       │
│ ├─ Auth Failures: 5 (IP: 192.168.1.200)                             │
│ ├─ Timeout Errors: 3 (staging-vm 네트워크 지연)                       │
│ └─ Rate Limit: 2 (prod-server 요청 한도 초과)                         │
├───────────────────────────────────────────────────────────────────────┤
│ <c>lear <s>ave <f>ilter <w>rap <e>xport <p>ause <q>uit               │
└───────────────────────────────────────────────────────────────────────┘
```

#### 보안 관리 화면
```
┌─ Security Management ─────────────────────────────────────────────────┐
│ ■ Access Control  ○ Auth Logs  ○ Rate Limiting  ○ SSL/TLS            │
├───────────────────────────────────────────────────────────────────────┤
│ 🔐 Access Control Lists                                               │
│                                                                       │
│ ✅ Whitelist (허용된 IP):                                              │
│ ├─ 192.168.1.0/24      (로컬 네트워크)        - 3 active connections │
│ ├─ 203.0.113.50/32     (prod-server)          - 1 active connection  │
│ ├─ 10.0.0.0/8          (내부 네트워크)         - 0 active connections │
│ └─ 198.51.100.25/32    (staging-server)       - 1 active connection  │
│                                                                       │
│ ❌ Blacklist (차단된 IP):                                              │
│ ├─ 192.168.1.200/32    차단 사유: 인증 실패 5회 (2h ago)              │
│ ├─ 203.0.113.100/32    차단 사유: 무차별 대입 공격 (1d ago)           │
│ └─ 198.51.100.50/32    차단 사유: 비정상 트래픽 (3h ago)              │
│                                                                       │
│ 🔑 Authentication:                                                    │
│ ├─ 현재 토큰: abc123def456... (생성: 2d ago)                          │
│ ├─ 토큰 만료: 30일 후                                                 │
│ ├─ 인증 성공률: 94.2% (지난 24시간)                                   │
│ └─ 실패 시도: 23회 (차단: 5개 IP)                                     │
│                                                                       │
│ ⚠️  보안 알림:                                                         │
│ ├─ 192.168.1.200에서 5분간 3회 인증 실패                             │
│ ├─ 토큰 만료 30일 전 알림                                            │
│ └─ 비정상 트래픽 패턴 감지: 203.0.113.100                            │
├───────────────────────────────────────────────────────────────────────┤
│ <a>dd <r>emove <b>lock <u>nblock <t>oken <l>ogs <q>uit               │
└───────────────────────────────────────────────────────────────────────┘
```

## 구현 아키텍처

### 파일 구조
```
src/frp_wrapper/
├── server/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py              # CLI 메인 엔트리포인트
│   │   ├── commands/
│   │   │   ├── install.py       # 서버 설치
│   │   │   ├── setup.py         # 초기 설정
│   │   │   ├── control.py       # 시작/중지/재시작
│   │   │   ├── clients.py       # 클라이언트 관리
│   │   │   ├── tunnels.py       # 터널 관리
│   │   │   ├── logs.py          # 로그 관리
│   │   │   ├── config.py        # 설정 관리
│   │   │   ├── security.py      # 보안 관리
│   │   │   └── stats.py         # 성능 통계
│   │   └── utils/
│   │       ├── installer.py     # FRP 서버 설치 로직
│   │       ├── config_gen.py    # 설정 파일 생성
│   │       └── validator.py     # 설정 검증
│   ├── tui/
│   │   ├── __init__.py
│   │   ├── app.py               # TUI 메인 애플리케이션
│   │   ├── screens/
│   │   │   ├── dashboard.py     # 메인 대시보드
│   │   │   ├── clients.py       # 클라이언트 관리
│   │   │   ├── tunnels.py       # 터널 모니터링
│   │   │   ├── logs.py          # 로그 뷰어
│   │   │   ├── security.py      # 보안 관리
│   │   │   └── config.py        # 설정 화면
│   │   ├── widgets/
│   │   │   ├── server_status.py # 서버 상태 위젯
│   │   │   ├── client_table.py  # 클라이언트 테이블
│   │   │   ├── tunnel_monitor.py# 터널 모니터링
│   │   │   ├── log_stream.py    # 로그 스트림
│   │   │   ├── performance.py   # 성능 차트
│   │   │   └── security_panel.py# 보안 패널
│   │   └── styles/
│   │       ├── server.tcss      # 서버용 스타일
│   │       └── themes/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── server_manager.py    # 서버 프로세스 관리
│   │   ├── client_monitor.py    # 클라이언트 모니터링
│   │   ├── tunnel_tracker.py    # 터널 추적
│   │   ├── log_parser.py        # 로그 파싱
│   │   ├── metrics_collector.py # 메트릭 수집
│   │   └── security_manager.py  # 보안 관리
│   └── api/
│       ├── __init__.py
│       ├── dashboard_api.py     # 대시보드 API 연동
│       ├── metrics_api.py       # 메트릭 API
│       └── config_api.py        # 설정 API
```

### 핵심 컴포넌트

**1. 서버 관리자 (ServerManager)**
```python
from dataclasses import dataclass
from pathlib import Path
import subprocess
import psutil

@dataclass
class ServerConfig:
    bind_addr: str = "0.0.0.0"
    bind_port: int = 7000
    token: str = ""
    dashboard_port: int = 7500
    dashboard_user: str = "admin"
    dashboard_pwd: str = ""
    log_level: str = "info"
    max_clients: int = 100

class ServerManager:
    """FRP 서버 프로세스 관리."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.process: subprocess.Popen | None = None
        self.pid_file = Path("/var/run/frp-server.pid")

    def start(self) -> bool:
        """서버 시작."""
        if self.is_running():
            return True

        cmd = [
            "/opt/frp-server/frps",
            "-c", str(self.config_path)
        ]

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )

        # PID 파일 저장
        self.pid_file.write_text(str(self.process.pid))
        return self.wait_for_startup()

    def stop(self) -> bool:
        """서버 중지."""
        if not self.is_running():
            return True

        if self.process:
            self.process.terminate()
            self.process.wait(timeout=10)

        self.pid_file.unlink(missing_ok=True)
        return True

    def is_running(self) -> bool:
        """서버 실행 상태 확인."""
        if not self.pid_file.exists():
            return False

        try:
            pid = int(self.pid_file.read_text().strip())
            return psutil.pid_exists(pid)
        except (ValueError, OSError):
            return False

    def get_stats(self) -> dict:
        """서버 통계 수집."""
        if not self.is_running():
            return {}

        pid = int(self.pid_file.read_text().strip())
        process = psutil.Process(pid)

        return {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "connections": len(process.connections()),
            "uptime": time.time() - process.create_time(),
        }
```

**2. 클라이언트 모니터 (ClientMonitor)**
```python
from typing import Dict, List
import requests
import json

@dataclass
class ClientInfo:
    name: str
    address: str
    connected_at: datetime
    tunnels: List[str]
    bytes_in: int
    bytes_out: int
    last_ping: datetime

class ClientMonitor:
    """FRP 대시보드 API를 통한 클라이언트 모니터링."""

    def __init__(self, dashboard_url: str, user: str, password: str):
        self.dashboard_url = dashboard_url
        self.auth = (user, password)
        self.session = requests.Session()

    def get_clients(self) -> List[ClientInfo]:
        """연결된 클라이언트 목록."""
        try:
            response = self.session.get(
                f"{self.dashboard_url}/api/proxy/tcp",
                auth=self.auth
            )
            response.raise_for_status()

            clients = []
            for proxy in response.json().get("proxies", []):
                client = ClientInfo(
                    name=proxy["name"],
                    address=proxy["remote_addr"],
                    connected_at=datetime.fromisoformat(proxy["start_time"]),
                    tunnels=[proxy["name"]],
                    bytes_in=proxy["today_traffic_in"],
                    bytes_out=proxy["today_traffic_out"],
                    last_ping=datetime.now()
                )
                clients.append(client)

            return clients
        except Exception as e:
            logger.error(f"Failed to get clients: {e}")
            return []

    def disconnect_client(self, client_name: str) -> bool:
        """클라이언트 연결 해제."""
        try:
            response = self.session.delete(
                f"{self.dashboard_url}/api/proxy/tcp/{client_name}",
                auth=self.auth
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to disconnect client {client_name}: {e}")
            return False
```

**3. 설정 생성기 (ServerConfigGenerator)**
```python
import toml
from pathlib import Path

class ServerConfigGenerator:
    """FRP 서버 설정 파일 생성."""

    def __init__(self, config: ServerConfig):
        self.config = config

    def generate(self, output_path: Path) -> bool:
        """TOML 설정 파일 생성."""
        config_dict = {
            "bindAddr": self.config.bind_addr,
            "bindPort": self.config.bind_port,
            "auth": {
                "method": "token",
                "token": self.config.token
            },
            "webServer": {
                "addr": "0.0.0.0",
                "port": self.config.dashboard_port,
                "user": self.config.dashboard_user,
                "password": self.config.dashboard_pwd
            },
            "log": {
                "to": "/var/log/frp-server.log",
                "level": self.config.log_level,
                "maxLogFile": 3
            },
            "transport": {
                "maxPoolCount": self.config.max_clients,
                "heartbeatTimeout": 90,
                "tls": {
                    "enable": True
                }
            }
        }

        try:
            with open(output_path, 'w') as f:
                toml.dump(config_dict, f)
            return True
        except Exception as e:
            logger.error(f"Failed to generate config: {e}")
            return False
```

## 패키지 설정

```toml
# pyproject.toml에 추가
[project.optional-dependencies]
server = [
    "psutil>=5.9",          # 시스템 모니터링
    "requests>=2.31",       # HTTP API 클라이언트
    "toml>=0.10",          # 설정 파일 처리
    "rich>=13.0",          # CLI 출력
]

server-tui = [
    "frp-wrapper[server]",
    "textual>=0.50.0",     # TUI 프레임워크
]

[project.scripts]
cli-frpc = "frp_wrapper.cli.main:cli"
tui-frpc = "frp_wrapper.tui.app:main"
cli-frps = "frp_wrapper.server.cli.main:cli"
tui-frps = "frp_wrapper.server.tui.app:main"
```

## 설치 및 사용

```bash
# 서버 관리 도구 설치
pip install frp-wrapper[server,server-tui]

# 서버 설치 및 설정
cli-frps install
cli-frps setup

# 서버 시작
cli-frps start

# TUI로 서버 모니터링
tui-frps
```

## 통합 관리 시나리오

### 1. 개발 환경 설정
```bash
# 개발자 로컬에서 클라이언트 실행
cli-frpc setup --server dev-server.com
cli-frpc share 3000 --name myapp

# 서버 관리자가 모니터링
tui-frps  # 실시간 대시보드에서 새 연결 확인
```

### 2. 프로덕션 배포
```bash
# 서버 설치 및 보안 설정
cli-frps install --production
cli-frps security allow 203.0.113.0/24  # 회사 IP만 허용
cli-frps config set max_clients 500

# 클라이언트에서 프로덕션 연결
cli-frpc tunnel 80 --name prod-web --server prod-server.com
```

### 3. 문제 해결
```bash
# 서버에서 문제 클라이언트 확인
cli-frps clients --filter slow-response
cli-frps disconnect problematic-client

# 클라이언트에서 재연결
cli-frpc reconnect --retry 3
```

이렇게 클라이언트(`cli-frpc`, `tui-frpc`)와 서버(`cli-frps`, `tui-frps`) 도구를 명확히 구분하여, FRP 생태계의 전체 라이프사이클을 효율적으로 관리할 수 있는 통합 솔루션을 제공합니다.
