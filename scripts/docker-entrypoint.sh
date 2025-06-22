#!/bin/bash
set -e


FRP_CONFIG_FILE="/etc/frp/frps.toml"
FRP_USER="frp"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

generate_config() {
    log "Generating FRP configuration from environment variables..."
    
    cat > "$FRP_CONFIG_FILE" << EOF

bindAddr = "0.0.0.0"
bindPort = 7000
vhostHTTPPort = 80
vhostHTTPSPort = 443

auth.token = "${FRP_AUTH_TOKEN:-change_this_token}"

EOF

    if [ -n "$FRP_SUBDOMAIN_HOST" ]; then
        echo "subDomainHost = \"$FRP_SUBDOMAIN_HOST\"" >> "$FRP_CONFIG_FILE"
        echo "" >> "$FRP_CONFIG_FILE"
    fi

    cat >> "$FRP_CONFIG_FILE" << EOF
log.level = "info"
log.maxDays = 7
log.to = "/var/log/frp/frps.log"

maxPoolCount = 10
transport.heartbeatTimeout = 90

EOF

    if [ "$SSL_ENABLED" = "true" ]; then
        if [ -n "$LETSENCRYPT_DOMAINS" ]; then
            local primary_domain=$(echo "$LETSENCRYPT_DOMAINS" | cut -d',' -f1)
            cat >> "$FRP_CONFIG_FILE" << EOF
tlsCertFile = "/etc/letsencrypt/live/$primary_domain/fullchain.pem"
tlsKeyFile = "/etc/letsencrypt/live/$primary_domain/privkey.pem"

EOF
        fi
    fi

    if [ "$FRP_DASHBOARD_ENABLED" = "true" ]; then
        cat >> "$FRP_CONFIG_FILE" << EOF
[webServer]
port = 7500
user = "${FRP_DASHBOARD_USER:-admin}"
password = "${FRP_DASHBOARD_PASSWORD:-change_this_password}"

EOF
    fi

    chown "$FRP_USER:$FRP_USER" "$FRP_CONFIG_FILE"
    chmod 640 "$FRP_CONFIG_FILE"
    
    log "Configuration generated successfully"
}

setup_ssl() {
    if [ "$SSL_ENABLED" = "true" ] && [ -n "$LETSENCRYPT_EMAIL" ] && [ -n "$LETSENCRYPT_DOMAINS" ]; then
        log "Setting up SSL certificates..."
        
        local primary_domain=$(echo "$LETSENCRYPT_DOMAINS" | cut -d',' -f1)
        local cert_path="/etc/letsencrypt/live/$primary_domain/fullchain.pem"
        
        if [ ! -f "$cert_path" ]; then
            log "Obtaining SSL certificates for: $LETSENCRYPT_DOMAINS"
            
            local domain_args=""
            IFS=',' read -ra DOMAIN_ARRAY <<< "$LETSENCRYPT_DOMAINS"
            for domain in "${DOMAIN_ARRAY[@]}"; do
                domain=$(echo "$domain" | xargs) # trim whitespace
                domain_args="$domain_args -d $domain"
            done
            
            certbot certonly \
                --standalone \
                --email "$LETSENCRYPT_EMAIL" \
                --agree-tos \
                --non-interactive \
                $domain_args || {
                log "Failed to obtain SSL certificates"
                exit 1
            }
            
            log "SSL certificates obtained successfully"
        else
            log "SSL certificates already exist"
        fi
    fi
}

setup_cert_renewal() {
    if [ "$SSL_ENABLED" = "true" ]; then
        log "Setting up certificate auto-renewal..."
        
        cat > /usr/local/bin/renew-certs.sh << 'EOF'
#!/bin/bash
certbot renew --quiet --post-hook "supervisorctl restart frps"
EOF
        chmod +x /usr/local/bin/renew-certs.sh
        
        echo "0 */12 * * * root /usr/local/bin/renew-certs.sh" > /etc/cron.d/cert-renewal
        chmod 644 /etc/cron.d/cert-renewal
        
        log "Certificate auto-renewal configured"
    fi
}

validate_config() {
    log "Validating configuration..."
    
    if [ "$FRP_AUTH_TOKEN" = "change_this_token" ]; then
        log "WARNING: Using default auth token. Please set FRP_AUTH_TOKEN environment variable."
    fi
    
    if [ "$FRP_DASHBOARD_ENABLED" = "true" ] && [ "$FRP_DASHBOARD_PASSWORD" = "change_this_password" ]; then
        log "WARNING: Using default dashboard password. Please set FRP_DASHBOARD_PASSWORD environment variable."
    fi
    
    log "Configuration validation completed"
}

main() {
    log "Starting FRP Server container..."
    
    generate_config
    
    setup_ssl
    
    setup_cert_renewal
    
    validate_config
    
    service cron start
    
    log "FRP Server container initialization completed"
    
    exec "$@"
}

main "$@"
