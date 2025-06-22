# Checkpoint 2: Basic Client - FRP 서버 연결하기

## 🎯 목적: 왜 FRPClient가 필요해?

ProcessManager로 프로세스는 관리할 수 있지만, 실제로 FRP 서버에 연결하려면:

### 문제점들:
1. **복잡한 TOML 설정 파일 작성**
   ```toml
   serverAddr = "example.com"
   serverPort = 7000
   auth.method = "token"
   auth.token = "secret123"
   ```

2. **바이너리 찾기가 어려움**
   - 어디에 설치되어 있지?
   - PATH에 있나?
   - 권한은 있나?

3. **연결 상태 관리**
   - 연결됐는지 어떻게 알지?
   - 재연결은 어떻게?

## 📦 구현 내용: FRPClient & ConfigBuilder

### FRPClient - 메인 클라이언트
```python
class FRPClient:
    """FRP 서버와의 연결을 관리하는 클라이언트"""

    def __init__(self, server: str, port: int = 7000, auth_token: str | None = None):
        self.server = server
        self.port = port
        self.auth_token = auth_token
        self._process_manager: ProcessManager | None = None

    def connect(self) -> bool:
        """서버에 연결"""

    def disconnect(self) -> None:
        """연결 종료"""

    def is_connected(self) -> bool:
        """연결 상태 확인"""
```

### ConfigBuilder - 설정 파일 생성기
```python
class ConfigBuilder:
    """FRP TOML 설정 파일을 생성하는 빌더"""

    def add_server(self, addr: str, port: int = 7000, token: str | None = None):
        """서버 설정 추가"""

    def build(self) -> str:
        """TOML 파일 생성하고 경로 반환"""
```

## 🔧 실제 FRP 설정과 비교

### 기존 방식 (수동 TOML):
```toml
# frpc.toml 파일을 직접 작성
serverAddr = "example.com"
serverPort = 7000
auth.method = "token"
auth.token = "my-secret-token"

[[proxies]]
name = "web"
type = "http"
localPort = 3000
customDomains = ["example.com"]
```

```bash
# 그리고 실행
./frpc -c frpc.toml
```

### FRPClient 방식:
```python
# Python으로 간단하게!
client = FRPClient("example.com", auth_token="my-secret-token")
client.connect()

# 연결 확인
if client.is_connected():
    print("✅ FRP 서버에 연결됨!")
```

## 💡 핵심 기능들

### 1. 자동 바이너리 탐색
```python
@staticmethod
def find_frp_binary() -> str:
    """FRP 바이너리를 자동으로 찾기"""

    # 1. 환경 변수 확인
    if env_path := os.getenv("FRP_BINARY_PATH"):
        return env_path

    # 2. PATH에서 찾기
    if binary := shutil.which("frpc"):
        return binary

    # 3. 일반적인 설치 경로 확인
    common_paths = [
        "/usr/local/bin/frpc",
        "/usr/bin/frpc",
        "/opt/frp/frpc",
        str(Path.home() / "bin" / "frpc"),
    ]

    for path in common_paths:
        if Path(path).exists():
            return path

    raise BinaryNotFoundError("frpc binary not found")
```

### 2. ConfigBuilder로 TOML 생성
```python
def connect(self) -> bool:
    """서버 연결 with 자동 설정 생성"""

    # 1. 설정 빌더 생성
    config_builder = ConfigBuilder()

    # 2. 서버 정보 추가
    config_builder.add_server(
        addr=self.server,
        port=self.port,
        token=self.auth_token
    )

    # 3. TOML 파일 생성 (임시 파일)
    config_path = config_builder.build()

    # 4. ProcessManager로 실행
    self._process_manager = ProcessManager(self._binary_path, config_path)
    return self._process_manager.start()
```

### 3. 실제 TOML 생성 예시
```python
class ConfigBuilder:
    def build(self) -> str:
        """TOML 설정 생성"""
        config = {
            "serverAddr": self._server_addr,
            "serverPort": self._server_port,
        }

        if self._auth_token:
            config["auth.method"] = "token"
            config["auth.token"] = self._auth_token

        # TOML 형식으로 변환
        toml_content = toml.dumps(config)

        # 임시 파일에 저장
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            return f.name
```

### 4. 연결 재시도 로직
```python
def connect(self, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    """연결 with 재시도"""

    for attempt in range(max_retries):
        try:
            if self._attempt_connection():
                logger.info(f"Connected to {self.server}")
                return True
        except ConnectionError as e:
            if attempt == max_retries - 1:
                raise

            logger.warning(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(retry_delay * (2 ** attempt))  # 지수 백오프

    return False
```

## 🔍 사용 예시

### 기본 사용법:
```python
# 1. 클라이언트 생성
client = FRPClient(
    server="example.com",
    port=7000,
    auth_token="my-secret-token"
)

# 2. 연결
if client.connect():
    print("✅ 연결 성공!")

    # 3. 작업 수행...
    while client.is_connected():
        # 터널 생성 등의 작업
        time.sleep(1)

    # 4. 연결 종료
    client.disconnect()
```

### Context Manager 사용:
```python
# 자동 연결/해제
with FRPClient("example.com", auth_token="secret") as client:
    if client.is_connected():
        print("연결됨!")
        # 작업 수행...
# 자동으로 disconnect()
```

### 에러 처리:
```python
try:
    client = FRPClient("wrong-server.com")
    client.connect()
except ConnectionError as e:
    print(f"❌ 연결 실패: {e}")
except BinaryNotFoundError as e:
    print(f"❌ FRP 바이너리를 찾을 수 없음: {e}")
```

## 🔐 보안 기능

### 1. 민감정보 마스킹
```python
def __repr__(self) -> str:
    """디버깅 시 토큰 숨기기"""
    token_display = mask_sensitive_data(self.auth_token) if self.auth_token else None
    return f"FRPClient(server='{self.server}', port={self.port}, auth_token='{token_display}')"

# 출력: FRPClient(server='example.com', port=7000, auth_token='****3456')
```

### 2. 임시 파일 안전 관리
```python
class ConfigBuilder:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """임시 설정 파일 자동 삭제"""
        if self._temp_file and Path(self._temp_file).exists():
            Path(self._temp_file).unlink()
```

## ❓ 자주 묻는 질문

**Q: 왜 TOML을 동적으로 생성해?**
A:
- 사용자가 TOML 문법을 몰라도 됨
- 타입 안전성 보장
- 프로그래밍적 제어 가능

**Q: 바이너리를 못 찾으면?**
A: 세 가지 방법으로 해결:
1. 환경 변수: `export FRP_BINARY_PATH=/path/to/frpc`
2. PATH에 추가: `cp frpc /usr/local/bin/`
3. 직접 지정: `FRPClient(binary_path="/custom/path/frpc")`

**Q: 연결 상태는 어떻게 확인해?**
A: ProcessManager의 상태 + 로그 확인:
```python
def is_connected(self) -> bool:
    return (
        self._process_manager is not None
        and self._process_manager.is_running()
    )
```

**Q: auth.method는 왜 "token"으로 고정?**
A: FRP는 token과 oidc 두 가지 인증을 지원하는데, 대부분 token을 사용합니다. 필요시 확장 가능합니다.

## 🎓 핵심 배운 점

1. **추상화의 중요성**
   - 복잡한 TOML → 간단한 Python API
   - 수동 프로세스 관리 → 자동화

2. **빌더 패턴의 활용**
   - ConfigBuilder로 복잡한 설정 단순화
   - 유연한 확장 가능

3. **자원 관리**
   - Context Manager로 연결 자동 관리
   - 임시 파일 자동 정리

## 🚧 현재 한계점

FRPClient는 서버 연결만 담당합니다. 실제 터널(HTTP, TCP)을 만들려면 추가 기능이 필요합니다.

## 다음 단계

이제 서버에 연결했으니, 실제로 터널을 만들어야 합니다.

→ [Checkpoint 3: Tunnel Management - HTTP/TCP 터널 만들기](checkpoint-03-tunnel-management.md)
