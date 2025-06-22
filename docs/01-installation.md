# 설치 가이드

## 시스템 요구사항

### 최소 요구사항
- Python 3.8 이상
- pip 또는 conda
- 운영체제: Linux, macOS, Windows
- 메모리: 128MB 이상
- 네트워크: 인터넷 연결

### 권장 사양
- Python 3.10 이상
- 메모리: 256MB 이상
- FRP 서버에 대한 안정적인 네트워크 연결

## 설치 방법

### 1. pip를 사용한 설치 (권장)

```bash
# 최신 안정 버전 설치
pip install frp-wrapper

# 특정 버전 설치
pip install frp-wrapper==1.0.0

# 개발 버전 설치
pip install git+https://github.com/yourusername/frp-wrapper.git
```

### 2. conda를 사용한 설치

```bash
# conda-forge 채널에서 설치
conda install -c conda-forge frp-wrapper

# 환경 생성과 함께 설치
conda create -n frp-env python=3.10 frp-wrapper
conda activate frp-env
```

### 3. 소스에서 설치

```bash
# 저장소 클론
git clone https://github.com/yourusername/frp-wrapper.git
cd frp-wrapper

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 또는
venv\Scripts\activate  # Windows

# 개발 모드로 설치
pip install -e .

# 또는 일반 설치
pip install .
```

### 4. Docker를 사용한 설치

```dockerfile
# Dockerfile
FROM python:3.10-slim

RUN pip install frp-wrapper

WORKDIR /app
COPY . .

CMD ["python", "your_script.py"]
```

```bash
# Docker 이미지 빌드
docker build -t my-frp-app .

# 컨테이너 실행
docker run -it --rm my-frp-app
```

## FRP 바이너리 설치

FRP Python Wrapper는 FRP 바이너리가 필요합니다. 자동으로 다운로드하거나 수동으로 설치할 수 있습니다.

### 자동 검색

FRP Python Wrapper는 시스템에 설치된 FRP 바이너리를 자동으로 찾습니다:

```python
from frp_wrapper import FRPClient

# FRPClient가 자동으로 frpc 바이너리를 찾습니다
client = FRPClient("your-server.com")

# 또는 직접 경로 지정
client = FRPClient("your-server.com", frp_path="/usr/local/bin/frpc")
```

### 수동 설치

#### Linux/macOS
```bash
# 최신 버전 확인
FRP_VERSION=$(curl -s https://api.github.com/repos/fatedier/frp/releases/latest | grep tag_name | cut -d '"' -f 4 | sed 's/v//')

# 다운로드 (Linux AMD64 예시)
wget https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_amd64.tar.gz

# 압축 해제
tar -xzf frp_${FRP_VERSION}_linux_amd64.tar.gz

# 바이너리 설치
sudo cp frp_${FRP_VERSION}_linux_amd64/frpc /usr/local/bin/
sudo chmod +x /usr/local/bin/frpc

# 확인
frpc --version
```

#### Windows
```powershell
# PowerShell에서 실행
$FRP_VERSION = "0.51.0"
$ARCH = "amd64"  # 또는 "386", "arm64"

# 다운로드
Invoke-WebRequest -Uri "https://github.com/fatedier/frp/releases/download/v$FRP_VERSION/frp_${FRP_VERSION}_windows_$ARCH.zip" -OutFile "frp.zip"

# 압축 해제
Expand-Archive -Path "frp.zip" -DestinationPath "."

# PATH에 추가 또는 특정 위치로 복사
Copy-Item "frp_${FRP_VERSION}_windows_$ARCH\frpc.exe" "C:\Program Files\frp\frpc.exe"
```

### 패키지 매니저를 통한 설치

#### Homebrew (macOS)
```bash
brew install frp
```

#### APT (Ubuntu/Debian)
```bash
# 현재 공식 저장소에는 없으므로 수동 설치 필요
```

#### Snap
```bash
sudo snap install frp
```

## 설치 확인

### Python 패키지 확인
```python
import frp_wrapper
print(frp_wrapper.__version__)
```

### CLI 확인
```bash
# frp-wrapper 버전 확인
python -c "import frp_wrapper; print(frp_wrapper.__version__)"

# frpc 바이너리 확인
frpc --version
```

### 테스트 실행
```python
from frp_wrapper import FRPClient, BinaryNotFoundError

# 클라이언트 생성 테스트
try:
    client = FRPClient("test.example.com")
    print("클라이언트 생성 성공!")
    print(f"FRP 바이너리 위치: {client._frp_path}")
except BinaryNotFoundError:
    print("FRP 바이너리를 찾을 수 없습니다. 설치가 필요합니다.")
except Exception as e:
    print(f"오류: {e}")
```

## 개발 환경 설정

### 1. 가상환경 설정
```bash
# venv 사용
python -m venv frp-env
source frp-env/bin/activate  # Linux/macOS
frp-env\Scripts\activate     # Windows

# virtualenv 사용
virtualenv frp-env
source frp-env/bin/activate

# conda 사용
conda create -n frp-env python=3.10
conda activate frp-env
```

### 2. 개발 의존성 설치
```bash
# 개발 모드로 설치
pip install -e ".[dev]"

# 또는 requirements-dev.txt 사용
pip install -r requirements-dev.txt
```

### 3. 테스트 환경 설정
```bash
# 테스트 실행
pytest

# 커버리지 포함
pytest --cov=frp_wrapper

# 특정 테스트만 실행
pytest tests/test_client.py
```

## 환경별 설치

### AWS EC2
```bash
# Amazon Linux 2
sudo yum update -y
sudo yum install -y python3 python3-pip

# Python 패키지 설치
pip3 install frp-wrapper

# FRP 바이너리 설치
wget https://github.com/fatedier/frp/releases/download/v0.51.0/frp_0.51.0_linux_amd64.tar.gz
tar -xzf frp_0.51.0_linux_amd64.tar.gz
sudo cp frp_0.51.0_linux_amd64/frpc /usr/local/bin/
```

### Google Cloud Platform
```bash
# Debian/Ubuntu 기반
sudo apt-get update
sudo apt-get install -y python3-pip

pip3 install frp-wrapper
```

### Raspberry Pi
```bash
# ARM 아키텍처용 FRP 다운로드
wget https://github.com/fatedier/frp/releases/download/v0.51.0/frp_0.51.0_linux_arm.tar.gz
tar -xzf frp_0.51.0_linux_arm.tar.gz
sudo cp frp_0.51.0_linux_arm/frpc /usr/local/bin/

# Python 패키지 설치
pip3 install frp-wrapper
```

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  frp-client:
    build: .
    environment:
      - FRP_SERVER=tunnel.example.com
      - FRP_TOKEN=${FRP_TOKEN}
    volumes:
      - ./config:/app/config
    restart: unless-stopped
```

## 문제 해결

### 일반적인 설치 문제

#### 1. pip 버전 오류
```bash
# pip 업그레이드
python -m pip install --upgrade pip
```

#### 2. 권한 오류
```bash
# 사용자 설치
pip install --user frp-wrapper

# 또는 가상환경 사용 (권장)
```

#### 3. 의존성 충돌
```bash
# 새로운 가상환경에서 설치
python -m venv clean-env
source clean-env/bin/activate
pip install frp-wrapper
```

#### 4. SSL 인증서 오류
```bash
# 인증서 업데이트
pip install --upgrade certifi
```

### 플랫폼별 문제

#### macOS
```bash
# Xcode Command Line Tools 설치
xcode-select --install
```

#### Windows
```powershell
# Visual C++ 재배포 가능 패키지 설치
# https://aka.ms/vs/17/release/vc_redist.x64.exe
```

#### Linux
```bash
# 필수 패키지 설치
sudo apt-get install -y python3-dev build-essential
```

## 업그레이드

### pip 업그레이드
```bash
# 최신 버전으로 업그레이드
pip install --upgrade frp-wrapper

# 특정 버전으로 업그레이드
pip install --upgrade frp-wrapper==1.2.0
```

### 버전 확인
```python
# 버전 확인
import frp_wrapper
print(f"현재 버전: {frp_wrapper.__version__}")

# 변경사항은 CHANGELOG.md 참조
```

## 제거

### pip 제거
```bash
pip uninstall frp-wrapper
```

### 완전 제거
```bash
# Python 패키지 제거
pip uninstall frp-wrapper

# FRP 바이너리 제거
sudo rm /usr/local/bin/frpc
sudo rm /usr/local/bin/frps

# 설정 파일 제거 (선택)
rm -rf ~/.frp_wrapper
```

## 다음 단계

설치가 완료되었다면:
- 🚀 [빠른 시작 가이드](00-quickstart.md)로 첫 터널 만들기
- 📖 [기본 사용법](02-basic-usage.md)에서 자세한 사용 방법 학습
- 🔧 [설정 가이드](../spec/03-configuration.md)에서 상세 설정 방법 확인
