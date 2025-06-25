# Checkpoint 9: 비개발자 친화적 CLI 인터페이스

## Status: 📋 Planned
This checkpoint is planned but not yet implemented.
Priority may change based on K8s integration progress.

## 개요
비개발자도 쉽게 사용할 수 있는 직관적인 CLI 인터페이스를 구현합니다. 복잡한 설정 없이 간단한 명령어로 로컬 서비스를 인터넷에 공유할 수 있도록 합니다.

## 목표
- **접근성**: 기술적 배경 없이도 사용 가능
- **직관성**: 자연어에 가까운 명령어 구조
- **안전성**: 자동 설정과 검증으로 오류 최소화
- **편의성**: 원클릭 공유와 자동 관리

## CLI 명령어 구조

### 1. 초기 설정 (`cli-frpcc setup`)
```bash
cli-frpcc setup

# 대화형 설정 마법사
✨ FRP Wrapper 설정을 시작합니다!

🌐 서버 주소를 입력하세요: your-server.com
🔑 인증 토큰을 입력하세요: [입력 숨김]
📁 설정을 저장할 위치: ~/.frp-wrapper/config.toml

✅ 설정이 완료되었습니다!
🚀 이제 'cli-frpcc share 3000'으로 바로 공유할 수 있습니다.
```

**설정 파일 자동 생성:**
```toml
# ~/.frp-wrapper/config.toml
[server]
address = "your-server.com"
port = 7000
auth_token = "***"

[defaults]
auto_open_browser = true
show_qr_code = true
```

### 2. 즉시 공유 (`cli-frpc share`)
```bash
# 가장 간단한 사용법
cli-frpc share 3000

🚀 포트 3000을 공유하는 중...
📡 서버에 연결 중... ✅
🔗 터널 생성 중... ✅

🌐 공개 URL: https://your-server.com/app-abc123/
📱 QR 코드:
  ████ ▄▄▄▄▄ █▀█ █ ▄▄▄▄▄ ████
  ████ █   █ █▀▀▀█ █   █ ████
  ████ █▄▄▄█ ▄ █▄▀ █▄▄▄█ ████

🎯 브라우저에서 자동으로 열까요? (Y/n): y
🌍 브라우저가 열렸습니다!

💡 팁: Ctrl+C로 종료하거나 'cli-frpc stop app-abc123'로 중지할 수 있습니다.
```

### 3. 명명된 터널 (`cli-frpc tunnel`)
```bash
# 이름을 지정한 터널
cli-frpc tunnel 3000 --name myapp

🚀 'myapp' 터널을 생성하는 중...
🌐 공개 URL: https://your-server.com/myapp/
💾 터널이 백그라운드에서 실행됩니다.

# 경로 지정
cli-frpc tunnel 8080 --name api --path /api/v1

🚀 'api' 터널을 생성하는 중...
🌐 공개 URL: https://your-server.com/api/v1/
```

### 4. 터널 관리 (`cli-frpc list`, `cli-frpc stop`)
```bash
# 실행 중인 터널 목록
cli-frpc list

📋 실행 중인 터널:
┌──────────┬──────┬─────────────────────────────────┬────────────┐
│ 이름     │ 포트 │ 공개 URL                        │ 상태       │
├──────────┼──────┼─────────────────────────────────┼────────────┤
│ myapp    │ 3000 │ https://your-server.com/myapp/  │ 🟢 활성    │
│ api      │ 8080 │ https://your-server.com/api/v1/ │ 🟢 활성    │
│ test-app │ 5000 │ https://your-server.com/test/   │ 🔴 비활성  │
└──────────┴──────┴─────────────────────────────────┴────────────┘

💡 팁: 'cli-frpc logs myapp'로 로그를 확인할 수 있습니다.

# 특정 터널 중지
cli-frpc stop myapp

🛑 'myapp' 터널을 중지하는 중...
✅ 터널이 중지되었습니다.

# 모든 터널 중지
cli-frpc stop --all

🛑 모든 터널을 중지하는 중...
✅ 3개의 터널이 중지되었습니다.
```

### 5. 로그 및 상태 확인 (`cli-frpc logs`, `cli-frpc status`)
```bash
# 특정 터널 로그
cli-frpc logs myapp

📊 'myapp' 터널 로그:
2024-01-15 14:30:15 [INFO] 터널 시작됨 (포트: 3000)
2024-01-15 14:30:16 [INFO] 서버 연결 성공
2024-01-15 14:30:17 [INFO] 공개 URL 활성화: https://your-server.com/myapp/
2024-01-15 14:32:45 [INFO] 요청 수신: GET /myapp/
2024-01-15 14:32:46 [INFO] 응답 전송: 200 OK

# 실시간 로그 (tail -f 방식)
cli-frpc logs myapp --follow

# 전체 시스템 상태
cli-frpc status

🖥️  FRP Wrapper 상태:
┌─────────────────┬──────────────────┐
│ 서버 연결       │ 🟢 연결됨        │
│ 실행 중인 터널  │ 2개              │
│ 총 전송량       │ 1.2 MB          │
│ 마지막 활동     │ 2분 전           │
└─────────────────┴──────────────────┘
```

### 6. 고급 기능

**포트 자동 감지:**
```bash
# 현재 디렉토리에서 실행 중인 서비스 감지
cli-frpc auto

🔍 실행 중인 서비스를 찾는 중...
✅ 포트 3000에서 Node.js 앱 발견
✅ 포트 8080에서 Python Flask 앱 발견

어떤 서비스를 공유하시겠습니까?
1) Node.js 앱 (포트 3000)
2) Python Flask 앱 (포트 8080)
선택 (1-2): 1

🚀 Node.js 앱을 공유하는 중...
```

**설정 관리:**
```bash
# 현재 설정 확인
cli-frpc config show

📋 현재 설정:
서버: your-server.com:7000
인증: ✅ 설정됨
자동 브라우저 열기: 활성화
QR 코드 표시: 활성화

# 서버 변경
cli-frpc config server new-server.com

✅ 서버가 'new-server.com'으로 변경되었습니다.

# 토큰 재설정
cli-frpc config token

🔑 새 인증 토큰을 입력하세요: [입력 숨김]
✅ 토큰이 업데이트되었습니다.
```

## 구현 아키텍처

### 파일 구조
```
src/frp_wrapper/
├── cli/
│   ├── __init__.py
│   ├── main.py          # 메인 CLI 엔트리포인트
│   ├── commands/
│   │   ├── setup.py     # 초기 설정 마법사
│   │   ├── share.py     # 즉시 공유
│   │   ├── tunnel.py    # 명명된 터널 관리
│   │   ├── list.py      # 터널 목록
│   │   ├── stop.py      # 터널 중지
│   │   ├── logs.py      # 로그 확인
│   │   ├── status.py    # 상태 확인
│   │   ├── config.py    # 설정 관리
│   │   └── auto.py      # 자동 감지
│   ├── utils/
│   │   ├── config.py    # 설정 파일 관리
│   │   ├── display.py   # 컬러풀한 출력
│   │   ├── qr.py        # QR 코드 생성
│   │   ├── browser.py   # 브라우저 열기
│   │   └── daemon.py    # 백그라운드 프로세스
│   └── templates/       # 설정 템플릿
```

### 주요 의존성
```toml
[project.optional-dependencies]
cli = [
    "click>=8.0",         # CLI 프레임워크
    "rich>=13.0",         # 컬러풀한 터미널 출력
    "rich-click>=1.6",    # Rich + Click 통합
    "psutil>=5.9",        # 프로세스 관리
    "qrcode[pil]>=7.4",   # QR 코드 생성
    "pyfiglet>=0.8",      # ASCII 아트
]

[project.scripts]
cli-frpc = "frp_wrapper.cli.main:cli"
```

### 핵심 컴포넌트

**1. 설정 관리 (ConfigManager)**
```python
# src/frp_wrapper/cli/utils/config.py
class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".frp-wrapper"
        self.config_file = self.config_dir / "config.toml"
        self.tunnels_file = self.config_dir / "tunnels.json"

    def setup_wizard(self) -> bool:
        """대화형 설정 마법사"""

    def save_tunnel(self, name: str, config: TunnelConfig):
        """터널 정보 저장"""

    def load_tunnels(self) -> Dict[str, TunnelConfig]:
        """저장된 터널 목록 로드"""
```

**2. 백그라운드 프로세스 관리 (DaemonManager)**
```python
# src/frp_wrapper/cli/utils/daemon.py
class DaemonManager:
    def start_tunnel(self, name: str, port: int, path: str = None) -> str:
        """백그라운드에서 터널 시작"""

    def stop_tunnel(self, name: str) -> bool:
        """터널 중지"""

    def list_tunnels(self) -> List[TunnelInfo]:
        """실행 중인 터널 목록"""

    def get_tunnel_logs(self, name: str) -> Iterator[str]:
        """터널 로그 스트림"""
```

**3. 시각적 출력 (DisplayUtils)**
```python
# src/frp_wrapper/cli/utils/display.py
from rich.console import Console
from rich.table import Table
from rich.progress import track

class DisplayUtils:
    def show_welcome(self):
        """환영 메시지와 ASCII 아트"""

    def show_tunnel_table(self, tunnels: List[TunnelInfo]):
        """터널 목록을 테이블로 표시"""

    def show_qr_code(self, url: str):
        """QR 코드 생성 및 표시"""

    def show_progress(self, steps: List[str]):
        """진행 상황 표시"""
```

## 사용자 경험 개선사항

### 1. 스마트 기본값
- 가장 일반적인 포트 (3000, 8080, 5000) 자동 감지
- 프로젝트 이름 기반 터널 이름 추천
- 사용 패턴 학습으로 개인화된 기본값

### 2. 오류 처리 및 도움말
```bash
frp share 99999

❌ 오류: 포트 99999는 유효하지 않습니다.
💡 일반적으로 사용되는 포트: 3000, 8080, 5000
💡 사용법: frp share <포트번호>
💡 예시: frp share 3000
```

### 3. 자동 복구
- 네트워크 연결 끊김 시 자동 재연결
- 프로세스 중단 시 자동 재시작
- 설정 파일 손상 시 백업에서 복구

### 4. 통계 및 모니터링
```bash
frp stats

📊 사용 통계 (지난 7일):
┌─────────────┬─────────┬──────────┬───────────┐
│ 터널 이름   │ 요청 수 │ 전송량   │ 평균 응답 │
├─────────────┼─────────┼──────────┼───────────┤
│ myapp       │ 1,234   │ 45.2 MB  │ 120ms     │
│ api         │ 567     │ 12.8 MB  │ 89ms      │
└─────────────┴─────────┴──────────┴───────────┘

🏆 가장 인기있는 터널: myapp
⚡ 가장 빠른 응답: api
```

## 보안 및 안전성

### 1. 토큰 보안
- 설정 파일 권한 제한 (600)
- 메모리에서 토큰 자동 정리
- 토큰 유효성 실시간 검증

### 2. 프로세스 격리
- 각 터널을 독립 프로세스로 실행
- 시스템 리소스 사용량 모니터링
- 비정상 종료 시 자동 정리

### 3. 네트워크 보안
- HTTPS 강제 사용
- 잘못된 요청 필터링
- 로컬 접근만 허용하는 바인딩

## 테스트 전략

### 1. 단위 테스트
```python
# tests/cli/test_commands.py
def test_share_command_with_valid_port():
    """유효한 포트로 share 명령 테스트"""

def test_setup_wizard_interactive():
    """대화형 설정 마법사 테스트"""

def test_auto_detect_services():
    """실행 중인 서비스 자동 감지 테스트"""
```

### 2. 통합 테스트
```python
# tests/cli/test_integration.py
def test_full_tunnel_lifecycle():
    """터널 생성-사용-중지 전체 과정 테스트"""

def test_daemon_mode():
    """백그라운드 모드 테스트"""
```

### 3. 사용성 테스트
- 비개발자 대상 사용성 테스트
- 다양한 터미널 환경에서 호환성 테스트
- 접근성 (스크린 리더 등) 테스트

## 문서화

### 1. 인라인 도움말
```bash
frp --help
frp share --help
frp tunnel --help
```

### 2. 튜토리얼
- 5분 퀵 스타트 가이드
- 단계별 스크린샷 포함
- 일반적인 사용 사례별 예제

### 3. 트러블슈팅
- 자주 발생하는 문제와 해결책
- 로그 해석 가이드
- 네트워크 문제 진단 도구

## 배포 전략

### 1. 점진적 롤아웃
1. 내부 테스트 (Alpha)
2. 개발자 커뮤니티 테스트 (Beta)
3. 일반 사용자 릴리스 (Stable)

### 2. 패키징
```bash
# pip로 CLI 포함 설치
pip install frp-wrapper[cli]

# 독립 실행 파일 (PyInstaller)
frp-wrapper-standalone.exe
```

### 3. 업데이트 메커니즘
```bash
cli-frpc update

🔍 업데이트 확인 중...
✅ 새 버전 v0.2.0 발견!

📝 변경사항:
- 새로운 자동 감지 기능
- 향상된 QR 코드 생성
- 버그 수정 및 성능 개선

🚀 업데이트하시겠습니까? (Y/n): y
⬇️  다운로드 중... ████████████ 100%
✅ 업데이트 완료! 재시작해주세요.
```

이 CLI 인터페이스를 통해 개발자가 아닌 사용자도 복잡한 설정 없이 `cli-frpc share 3000` 같은 간단한 명령어로 로컬 서비스를 인터넷에 공유할 수 있습니다.
