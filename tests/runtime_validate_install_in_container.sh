#!/usr/bin/env bash
# Real runtime validation of install.sh inside a Debian 12 container.
# Runs apt-get for real, uses real pip, verifies Flask is importable.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

# Stub only systemctl — systemd is not running inside Docker
mkdir -p /tmp/fakebin
cat > /tmp/fakebin/systemctl <<'EOF'
#!/usr/bin/env bash
echo "[stub-systemctl] $*" >> /tmp/systemctl.log
exit 0
EOF
chmod +x /tmp/fakebin/systemctl

# Run install.sh with real apt-get and real python3/pip
PATH="/tmp/fakebin:$PATH" bash ./install.sh

# ── Assert systemd unit was written correctly ─────────────────────────────────
test -f /etc/systemd/system/fugginnas.service \
  || { echo "FAIL: fugginnas.service not written"; exit 1; }

grep -q 'ExecStart=/opt/fugginnas/venv/bin/python3 /repo/app.py' \
  /etc/systemd/system/fugginnas.service \
  || { echo "FAIL: ExecStart line wrong"; exit 1; }

grep -q 'WorkingDirectory=/repo' \
  /etc/systemd/system/fugginnas.service \
  || { echo "FAIL: WorkingDirectory missing"; exit 1; }

# ── Assert systemctl was called with the right subcommands ────────────────────
grep -q 'daemon-reload' /tmp/systemctl.log \
  || { echo "FAIL: systemctl daemon-reload not called"; exit 1; }

grep -q 'enable fugginnas' /tmp/systemctl.log \
  || { echo "FAIL: systemctl enable not called"; exit 1; }

grep -q 'start fugginnas' /tmp/systemctl.log \
  || { echo "FAIL: systemctl start not called"; exit 1; }

# ── Assert venv exists and Flask is importable ────────────────────────────────
test -x /opt/fugginnas/venv/bin/python3 \
  || { echo "FAIL: venv python3 not found"; exit 1; }

/opt/fugginnas/venv/bin/python3 -c "import flask; print('Flask', flask.__version__)" \
  || { echo "FAIL: flask not importable from venv"; exit 1; }

echo "RUNTIME_OK"
