#!/bin/bash

set -e

FRP_VERSION="0.52.3"
FRP_USER="frp"
FRP_HOME="/opt/frp"
FRP_CONFIG_DIR="/etc/frp"
FRP_LOG_DIR="/var/log/frp"
SYSTEMD_SERVICE_FILE="/etc/systemd/system/frps.service"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

detect_arch() {
    local arch=$(uname -m)
    case $arch in
        x86_64)
            echo "amd64"
            ;;
        aarch64|arm64)
            echo "arm64"
            ;;
        armv7l)
            echo "arm"
            ;;
        *)
            log_error "Unsupported architecture: $arch"
            exit 1
            ;;
    esac
}

install_dependencies() {
    log_info "Installing dependencies..."
    
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update
        apt-get install -y wget curl tar systemd openssl
    elif command -v yum >/dev/null 2>&1; then
        yum update -y
        yum install -y wget curl tar systemd openssl
    elif command -v dnf >/dev/null 2>&1; then
        dnf update -y
        dnf install -y wget curl tar systemd openssl
    else
        log_error "Unsupported package manager. Please install wget, curl, tar, systemd, and openssl manually."
        exit 1
    fi
}

create_frp_user() {
    log_info "Creating FRP user..."
    
    if ! id "$FRP_USER" >/dev/null 2>&1; then
        useradd --system --home-dir "$FRP_HOME" --shell /bin/false "$FRP_USER"
        log_info "Created user: $FRP_USER"
    else
        log_info "User $FRP_USER already exists"
    fi
}

create_directories() {
    log_info "Creating directories..."
    
    mkdir -p "$FRP_HOME"
    mkdir -p "$FRP_CONFIG_DIR"
    mkdir -p "$FRP_LOG_DIR"
    
    chown -R "$FRP_USER:$FRP_USER" "$FRP_HOME"
    chown -R "$FRP_USER:$FRP_USER" "$FRP_CONFIG_DIR"
    chown -R "$FRP_USER:$FRP_USER" "$FRP_LOG_DIR"
    
    chmod 755 "$FRP_HOME"
    chmod 755 "$FRP_CONFIG_DIR"
    chmod 755 "$FRP_LOG_DIR"
}

install_frp() {
    log_info "Downloading FRP version $FRP_VERSION..."
    
    local arch=$(detect_arch)
    local download_url="https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_${arch}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    cd "$temp_dir"
    wget -q "$download_url" -O frp.tar.gz
    
    log_info "Extracting FRP..."
    tar -xzf frp.tar.gz
    
    local frp_dir="frp_${FRP_VERSION}_linux_${arch}"
    
    cp "$frp_dir/frps" "$FRP_HOME/"
    cp "$frp_dir/frpc" "$FRP_HOME/"
    
    chown "$FRP_USER:$FRP_USER" "$FRP_HOME/frps" "$FRP_HOME/frpc"
    chmod 755 "$FRP_HOME/frps" "$FRP_HOME/frpc"
    
    ln -sf "$FRP_HOME/frps" /usr/local/bin/frps
    ln -sf "$FRP_HOME/frpc" /usr/local/bin/frpc
    
    cd /
    rm -rf "$temp_dir"
    
    log_info "FRP installed successfully"
}

generate_config() {
    log_info "Generating default configuration..."
    
    cat > "$FRP_CONFIG_DIR/frps.toml" << 'EOF'

bindAddr = "0.0.0.0"
bindPort = 7000
vhostHTTPPort = 80
vhostHTTPSPort = 443

auth.token = "CHANGE_THIS_TOKEN"

log.level = "info"
log.maxDays = 3
log.to = "/var/log/frp/frps.log"

maxPoolCount = 5
transport.heartbeatTimeout = 90

EOF

    chown "$FRP_USER:$FRP_USER" "$FRP_CONFIG_DIR/frps.toml"
    chmod 640 "$FRP_CONFIG_DIR/frps.toml"
    
    log_warn "Please edit $FRP_CONFIG_DIR/frps.toml and change the default auth token!"
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > "$SYSTEMD_SERVICE_FILE" << EOF
[Unit]
Description=FRP Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=$FRP_USER
Group=$FRP_USER
ExecStart=$FRP_HOME/frps -c $FRP_CONFIG_DIR/frps.toml
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=frps

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$FRP_LOG_DIR $FRP_CONFIG_DIR

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable frps
    
    log_info "Systemd service created and enabled"
}

setup_firewall() {
    log_info "Setting up firewall rules..."
    
    if command -v ufw >/dev/null 2>&1; then
        ufw allow 7000/tcp comment "FRP Server Control Port"
        ufw allow 80/tcp comment "FRP HTTP"
        ufw allow 443/tcp comment "FRP HTTPS"
        log_info "UFW rules added"
    elif command -v firewall-cmd >/dev/null 2>&1; then
        firewall-cmd --permanent --add-port=7000/tcp
        firewall-cmd --permanent --add-port=80/tcp
        firewall-cmd --permanent --add-port=443/tcp
        firewall-cmd --reload
        log_info "Firewalld rules added"
    else
        log_warn "No supported firewall found. Please manually open ports 7000, 80, and 443"
    fi
}

generate_token() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

main() {
    log_info "Starting FRP Server installation..."
    
    check_root
    install_dependencies
    create_frp_user
    create_directories
    install_frp
    generate_config
    create_systemd_service
    setup_firewall
    
    local secure_token=$(generate_token)
    
    log_info "Installation completed successfully!"
    echo
    log_warn "IMPORTANT: Please complete the following steps:"
    echo "1. Edit $FRP_CONFIG_DIR/frps.toml and set a secure auth token"
    echo "   Suggested token: $secure_token"
    echo "2. Configure your domain and SSL settings if needed"
    echo "3. Start the service: systemctl start frps"
    echo "4. Check status: systemctl status frps"
    echo "5. View logs: journalctl -u frps -f"
    echo
    log_info "For SSL setup, run: ./setup-ssl.sh"
}

main "$@"
