#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

mkdir -p /tmp/fakebin

# Stub apt-get to avoid slow/flaky package installation in CI
cat > /tmp/fakebin/apt-get <<'EOF'
#!/usr/bin/env bash
echo "[stub-apt-get] $*" >> /tmp/apt-get.log
exit 0
EOF
chmod +x /tmp/fakebin/apt-get

# Stub python3 so venv creation is fast and offline; a fake pip is placed in the venv
cat > /tmp/fakebin/python3 <<'EOF'
#!/usr/bin/env bash
if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then
    dir="$3"
    mkdir -p "$dir/bin"
    printf '#!/usr/bin/env bash\necho "[stub-pip] $*" >> /tmp/pip.log\nexit 0\n' > "$dir/bin/pip"
    chmod +x "$dir/bin/pip"
else
    exec /usr/bin/python3 "$@"
fi
EOF
chmod +x /tmp/fakebin/python3

# Stub systemctl and record each invocation with its arguments for targeted assertions
cat > /tmp/fakebin/systemctl <<'EOF'
#!/usr/bin/env bash
echo "[stub-systemctl] $*" >> /tmp/systemctl.log
exit 0
EOF
chmod +x /tmp/fakebin/systemctl

PATH="/tmp/fakebin:$PATH" bash ./install.sh

test -f /etc/systemd/system/fugginnas.service
grep -q 'ExecStart=/opt/fugginnas/venv/bin/python3 /repo/app.py' /etc/systemd/system/fugginnas.service
grep -q 'WorkingDirectory=/repo' /etc/systemd/system/fugginnas.service

grep -q 'daemon-reload' /tmp/systemctl.log
grep -q 'enable fugginnas' /tmp/systemctl.log
grep -q 'start fugginnas' /tmp/systemctl.log

echo "RUNTIME_OK"
