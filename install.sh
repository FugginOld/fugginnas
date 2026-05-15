#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing system packages"
apt-get update -qq
apt-get install -y python3-pip python3-venv mergerfs snapraid mdadm samba nfs-kernel-server linux-headers-$(dpkg --print-architecture)

echo "==> Installing Python dependencies"
python3 -m venv /opt/fugginnas/venv
/opt/fugginnas/venv/bin/pip install -r "$REPO_DIR/requirements.txt"

echo "==> Writing systemd unit"
cat > /etc/systemd/system/fugginnas.service <<EOF
[Unit]
Description=FugginNAS configuration wizard
After=network.target

[Service]
Type=simple
WorkingDirectory=$REPO_DIR
ExecStart=/opt/fugginnas/venv/bin/python3 $REPO_DIR/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

echo "==> Enabling and starting fugginnas"
systemctl daemon-reload
systemctl enable fugginnas
systemctl start fugginnas

echo "==> Done. Open http://localhost:7070 in your browser."
