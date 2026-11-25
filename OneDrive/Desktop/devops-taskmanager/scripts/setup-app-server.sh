#!/usr/bin/env bash
# Run on the App EC2 instance (Ubuntu 24.04) as the ubuntu user: bash setup-app-server.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR=/opt/taskmgr

bash "$SCRIPT_DIR/install-docker.sh"
sudo usermod -aG docker "$USER"

# Small instances (1-2 GB RAM) need swap headroom for MySQL.
if ! sudo swapon --show | grep -q /swapfile; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

sudo mkdir -p "$DEPLOY_DIR/db" "$DEPLOY_DIR/backups"
sudo chown -R "$USER:$USER" "$DEPLOY_DIR"

if [ ! -f "$DEPLOY_DIR/.env" ]; then
    cat > "$DEPLOY_DIR/.env" <<EOF
DOCKERHUB_USER=your-dockerhub-username
IMAGE_TAG=latest
DB_NAME=taskmgr
DB_USER=taskmgr
DB_PASSWORD=$(openssl rand -hex 16)
DB_ROOT_PASSWORD=$(openssl rand -hex 16)
LOG_LEVEL=INFO
EOF
    chmod 600 "$DEPLOY_DIR/.env"
    echo "Created $DEPLOY_DIR/.env with random DB passwords - set DOCKERHUB_USER in it."
fi

cp "$SCRIPT_DIR/backup-mysql.sh" "$SCRIPT_DIR/restore-mysql.sh" "$DEPLOY_DIR/"
chmod +x "$DEPLOY_DIR"/*.sh

echo "Done. Log out and back in (or run 'newgrp docker') for docker group membership to apply."
