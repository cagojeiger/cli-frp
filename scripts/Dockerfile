# FRP Server Docker Image
FROM ubuntu:22.04

# Metadata
LABEL maintainer="FRP Wrapper Team"
LABEL description="FRP Server with SSL support"
LABEL version="1.0"

# Environment variables
ENV FRP_VERSION=0.52.3
ENV FRP_USER=frp
ENV FRP_HOME=/opt/frp
ENV FRP_CONFIG_DIR=/etc/frp
ENV FRP_LOG_DIR=/var/log/frp
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
        wget \
        curl \
        tar \
        openssl \
        ca-certificates \
        certbot \
        python3-certbot-nginx \
        cron \
        supervisor && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create FRP user and directories
RUN useradd --system --home-dir $FRP_HOME --shell /bin/false $FRP_USER && \
    mkdir -p $FRP_HOME $FRP_CONFIG_DIR $FRP_LOG_DIR && \
    chown -R $FRP_USER:$FRP_USER $FRP_HOME $FRP_CONFIG_DIR $FRP_LOG_DIR

# Download and install FRP
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then FRP_ARCH="amd64"; \
    elif [ "$ARCH" = "arm64" ]; then FRP_ARCH="arm64"; \
    elif [ "$ARCH" = "armhf" ]; then FRP_ARCH="arm"; \
    else echo "Unsupported architecture: $ARCH" && exit 1; fi && \
    wget -q "https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_${FRP_ARCH}.tar.gz" -O /tmp/frp.tar.gz && \
    cd /tmp && \
    tar -xzf frp.tar.gz && \
    cp "frp_${FRP_VERSION}_linux_${FRP_ARCH}/frps" $FRP_HOME/ && \
    cp "frp_${FRP_VERSION}_linux_${FRP_ARCH}/frpc" $FRP_HOME/ && \
    chown $FRP_USER:$FRP_USER $FRP_HOME/frps $FRP_HOME/frpc && \
    chmod 755 $FRP_HOME/frps $FRP_HOME/frpc && \
    rm -rf /tmp/frp*

# Copy configuration template
COPY frps.toml.template $FRP_CONFIG_DIR/frps.toml
RUN chown $FRP_USER:$FRP_USER $FRP_CONFIG_DIR/frps.toml && \
    chmod 640 $FRP_CONFIG_DIR/frps.toml

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose ports
EXPOSE 7000 80 443 7500

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7500/healthz || exit 1

# Set working directory
WORKDIR $FRP_HOME

# Use supervisor to manage processes
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
