#!/bin/bash

set -e

FRP_CONFIG_DIR="/etc/frp"
CERTBOT_EMAIL=""
DOMAINS=""
WEBROOT_PATH="/var/www/html"

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

show_usage() {
    echo "Usage: $0 -e EMAIL -d DOMAIN1,DOMAIN2,..."
    echo
    echo "Options:"
    echo "  -e EMAIL    Email address for Let's Encrypt registration"
    echo "  -d DOMAINS  Comma-separated list of domains"
    echo "  -w PATH     Webroot path (default: $WEBROOT_PATH)"
    echo "  -h          Show this help message"
    echo
    echo "Example:"
    echo "  $0 -e admin@example.com -d example.com,www.example.com"
}

parse_args() {
    while getopts "e:d:w:h" opt; do
        case $opt in
            e)
                CERTBOT_EMAIL="$OPTARG"
                ;;
            d)
                DOMAINS="$OPTARG"
                ;;
            w)
                WEBROOT_PATH="$OPTARG"
                ;;
            h)
                show_usage
                exit 0
                ;;
            \?)
                log_error "Invalid option: -$OPTARG"
                show_usage
                exit 1
                ;;
        esac
    done
    
    if [[ -z "$CERTBOT_EMAIL" || -z "$DOMAINS" ]]; then
        log_error "Email and domains are required"
        show_usage
        exit 1
    fi
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

install_certbot() {
    log_info "Installing certbot..."
    
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    elif command -v yum >/dev/null 2>&1; then
        yum install -y epel-release
        yum install -y certbot python3-certbot-nginx
    elif command -v dnf >/dev/null 2>&1; then
        dnf install -y certbot python3-certbot-nginx
    else
        log_error "Unsupported package manager"
        exit 1
    fi
}

setup_webroot() {
    log_info "Setting up webroot directory..."
    
    mkdir -p "$WEBROOT_PATH"
    chown -R www-data:www-data "$WEBROOT_PATH" 2>/dev/null || chown -R nginx:nginx "$WEBROOT_PATH" 2>/dev/null || true
    chmod 755 "$WEBROOT_PATH"
}

obtain_certificate() {
    log_info "Obtaining SSL certificate..."
    
    local domain_args=""
    IFS=',' read -ra DOMAIN_ARRAY <<< "$DOMAINS"
    for domain in "${DOMAIN_ARRAY[@]}"; do
        domain=$(echo "$domain" | xargs) # trim whitespace
        domain_args="$domain_args -d $domain"
    done
    
    if certbot certonly \
        --webroot \
        --webroot-path="$WEBROOT_PATH" \
        --email "$CERTBOT_EMAIL" \
        --agree-tos \
        --non-interactive \
        $domain_args; then
        log_info "Certificate obtained successfully using webroot method"
    else
        log_warn "Webroot method failed, trying standalone method..."
        
        systemctl stop frps 2>/dev/null || true
        
        if certbot certonly \
            --standalone \
            --email "$CERTBOT_EMAIL" \
            --agree-tos \
            --non-interactive \
            $domain_args; then
            log_info "Certificate obtained successfully using standalone method"
        else
            log_error "Failed to obtain certificate"
            systemctl start frps 2>/dev/null || true
            exit 1
        fi
        
        systemctl start frps 2>/dev/null || true
    fi
}

update_frp_config() {
    log_info "Updating FRP configuration..."
    
    local primary_domain=$(echo "$DOMAINS" | cut -d',' -f1 | xargs)
    local cert_path="/etc/letsencrypt/live/$primary_domain/fullchain.pem"
    local key_path="/etc/letsencrypt/live/$primary_domain/privkey.pem"
    
    cp "$FRP_CONFIG_DIR/frps.toml" "$FRP_CONFIG_DIR/frps.toml.backup"
    
    if ! grep -q "tlsCertFile" "$FRP_CONFIG_DIR/frps.toml"; then
        cat >> "$FRP_CONFIG_DIR/frps.toml" << EOF

tlsCertFile = "$cert_path"
tlsKeyFile = "$key_path"
EOF
        log_info "SSL configuration added to FRP config"
    else
        log_info "SSL configuration already exists in FRP config"
    fi
}

setup_auto_renewal() {
    log_info "Setting up automatic certificate renewal..."
    
    cat > /etc/letsencrypt/renewal-hooks/post/frp-reload.sh << 'EOF'
#!/bin/bash
systemctl reload frps 2>/dev/null || systemctl restart frps
EOF
    
    chmod +x /etc/letsencrypt/renewal-hooks/post/frp-reload.sh
    
    certbot renew --dry-run
    
    log_info "Auto-renewal configured successfully"
}

main() {
    log_info "Starting SSL setup for FRP Server..."
    
    parse_args "$@"
    check_root
    install_certbot
    setup_webroot
    obtain_certificate
    update_frp_config
    setup_auto_renewal
    
    log_info "SSL setup completed successfully!"
    echo
    log_info "Certificate information:"
    certbot certificates
    echo
    log_warn "Please restart FRP server to apply SSL configuration:"
    echo "  systemctl restart frps"
    echo
    log_info "To test certificate renewal:"
    echo "  certbot renew --dry-run"
}

main "$@"
