# --- frp 최신 버전 자동 설치(업그레이드 겸용) ------------------------------
set -euo pipefail

tmp=$(mktemp -d)

# ① 최신 태그(v0.62.1 등) 가져오기 ─ jq 없이 처리
TAG=$(curl -fsSL https://api.github.com/repos/fatedier/frp/releases/latest |
        grep '"tag_name"' | sed -E 's/.*"v([^"]+)".*/v\1/')
VER=${TAG#v}               # 앞의 'v' 제거 → 0.62.1

# ② 아키텍처 감지
case $(uname -m) in
  x86_64|amd64)   ARCH=amd64  ;;
  aarch64|arm64)  ARCH=arm64  ;;
  armv7l|armhf)   ARCH=armhf  ;;
  armv6l|arm)     ARCH=arm    ;;
  loongarch64)    ARCH=loong64;;
  mips*)          ARCH=mips   ;;
  *) echo "❌ 지원하지 않는 CPU: $(uname -m)"; exit 1 ;;
esac

# ③ 다운로드 & 압축 해제
URL="https://github.com/fatedier/frp/releases/download/${TAG}/frp_${VER}_linux_${ARCH}.tar.gz"
echo "⬇️  $URL"                       # 참고용 출력
curl -L "$URL" | tar -xz -C "$tmp"

# ④ 바이너리 설치(기존 파일을 덮어써 업그레이드 가능)
sudo install -m755 "$tmp/frp_${VER}_linux_${ARCH}/frps" /usr/local/bin/
sudo install -m755 "$tmp/frp_${VER}_linux_${ARCH}/frpc" /usr/local/bin/

# ⑤ 결과 확인
frps -v
frpc -v

