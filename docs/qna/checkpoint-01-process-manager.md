# Checkpoint 1: Process Manager 이해하기

## 🎯 목적: 왜 ProcessManager가 필요해?

FRP를 사용하려면 `frpc` 바이너리를 실행해야 합니다. 하지만...

### 문제점들:
1. **프로세스 시작/종료 관리가 번거로움**
   ```bash
   # 시작
   ./frpc -c config.toml &
   echo $! > frpc.pid

   # 종료
   kill $(cat frpc.pid)
   ```

2. **에러 처리가 어려움**
   - 바이너리가 없으면?
   - 실행 권한이 없으면?
   - 프로세스가 죽으면?

3. **상태 확인이 복잡함**
   ```bash
   ps aux | grep frpc
   ```

## 📦 구현 내용: ProcessManager

ProcessManager는 이 모든 걸 Python으로 깔끔하게 처리합니다:

```python
# src/frp_wrapper/core/process.py
class ProcessManager:
    """FRP 바이너리 프로세스를 관리하는 클래스"""

    def __init__(self, binary_path: str, config_path: str):
        self._binary_path = binary_path
        self._config_path = config_path
        self._process: subprocess.Popen[str] | None = None

    def start(self) -> bool:
        """프로세스 시작"""

    def stop(self) -> None:
        """프로세스 종료"""

    def is_running(self) -> bool:
        """실행 중인지 확인"""
```

## 🔧 실제 FRP 실행 방식 비교

### 기존 방식 (수동):
```bash
# 1. 설정 파일 작성
cat > frpc.toml << EOF
serverAddr = "example.com"
serverPort = 7000
[[proxies]]
name = "web"
type = "http"
localPort = 3000
EOF

# 2. 프로세스 실행
./frpc -c frpc.toml

# 3. 수동으로 모니터링...
```

### ProcessManager 방식:
```python
# 설정 파일 경로와 바이너리 경로만 주면 끝!
manager = ProcessManager("/usr/bin/frpc", "config.toml")
manager.start()

# 실행 중인지 확인
if manager.is_running():
    print("FRP가 실행 중입니다!")

# 종료
manager.stop()
```

## 💡 핵심 기능들

### 1. 바이너리 검증
```python
def _validate_binary(self) -> None:
    """FRP 바이너리가 올바른지 확인"""
    binary = Path(self._binary_path)

    if not binary.exists():
        raise BinaryNotFoundError(f"FRP binary not found: {self._binary_path}")

    if not binary.is_file():
        raise ValueError(f"Not a file: {self._binary_path}")

    # 실행 권한 확인 (Unix 권한: 0o111 = --x--x--x)
    if not binary.stat().st_mode & 0o111:
        raise PermissionError(f"Not executable: {self._binary_path}")
```

### 2. 안전한 프로세스 시작
```python
def start(self) -> bool:
    """프로세스 시작 with 에러 처리"""
    if self.is_running():
        return True  # 이미 실행 중

    cmd = [self._binary_path, "-c", self._config_path]

    try:
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True  # 독립 세션으로 실행
        )
        return True
    except Exception as e:
        logger.error(f"Failed to start process: {e}")
        raise ProcessError(f"Cannot start FRP: {e}") from e
```

### 3. Graceful Shutdown
```python
def stop(self, timeout: float = 5.0) -> None:
    """안전하게 프로세스 종료"""
    if not self._process:
        return

    # 1. SIGTERM으로 정상 종료 시도
    self._process.terminate()

    try:
        # 2. timeout 동안 기다림
        self._process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        # 3. 안 끝나면 강제 종료
        logger.warning("Process didn't stop gracefully, forcing...")
        self._process.kill()
        self._process.wait()
```

### 4. Context Manager 지원
```python
with ProcessManager("/usr/bin/frpc", "config.toml") as manager:
    # 자동으로 시작됨
    print("FRP is running!")
    # 작업 수행...
# 자동으로 정리됨 (stop 호출)
```

## 🔍 실제 동작 예시

### 성공 시나리오:
```python
# 1. ProcessManager 생성
manager = ProcessManager("/usr/bin/frpc", "/tmp/frpc.toml")

# 2. 프로세스 시작
if manager.start():
    print("✅ FRP 시작됨!")
    print(f"PID: {manager._process.pid}")

# 3. 상태 확인
while manager.is_running():
    print("실행 중...")
    time.sleep(1)

# 4. 종료
manager.stop()
print("✅ FRP 종료됨!")
```

### 에러 처리:
```python
try:
    # 잘못된 바이너리 경로
    manager = ProcessManager("/wrong/path/frpc", "config.toml")
except BinaryNotFoundError as e:
    print(f"❌ 바이너리를 찾을 수 없음: {e}")

try:
    # 실행 권한 없음
    manager = ProcessManager("/etc/passwd", "config.toml")
except PermissionError as e:
    print(f"❌ 실행 권한 없음: {e}")
```

## ❓ 자주 묻는 질문

**Q: subprocess.Popen을 쓰는 이유는?**
A:
- 비동기 실행 가능
- stdout/stderr 캡처 가능
- 세밀한 프로세스 제어 가능
- PID로 상태 추적 가능

**Q: start_new_session=True는 왜 필요해?**
A: 프로세스를 독립 세션으로 실행해서:
- Python 프로그램이 종료되어도 FRP는 계속 실행
- Ctrl+C 시그널이 전파되지 않음

**Q: is_running()은 어떻게 동작해?**
A:
```python
def is_running(self) -> bool:
    if not self._process:
        return False

    # poll()이 None이면 아직 실행 중
    return self._process.poll() is None
```

**Q: 로그는 어떻게 처리해?**
A: stdout/stderr를 파이프로 캡처해서 Python 로거로 전달:
```python
stdout, stderr = self._process.communicate()
if stdout:
    logger.info(f"FRP output: {stdout.decode()}")
if stderr:
    logger.error(f"FRP error: {stderr.decode()}")
```

## 🎓 핵심 배운 점

1. **프로세스 관리는 예외 처리가 중요**
   - 바이너리 검증
   - 권한 확인
   - 타임아웃 처리

2. **Context Manager로 자원 관리 자동화**
   - `__enter__`에서 시작
   - `__exit__`에서 정리
   - 예외가 발생해도 정리 보장

3. **Graceful Shutdown 패턴**
   - SIGTERM → 대기 → SIGKILL
   - 데이터 손실 방지

## 다음 단계

ProcessManager만으로는 FRP 서버에 연결할 수 없습니다. 설정 파일을 만들고 연결을 관리하는 기능이 필요합니다.

→ [Checkpoint 2: Basic Client - FRP 서버 연결하기](checkpoint-02-basic-client.md)
