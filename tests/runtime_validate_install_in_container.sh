#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

mkdir -p /tmp/fakebin
cat > /tmp/fakebin/systemctl <<'EOF'
#!/usr/bin/env bash
echo '[stub-systemctl] called' >> /tmp/systemctl.log
exit 0
EOF
chmod +x /tmp/fakebin/systemctl

PATH="/tmp/fakebin:$PATH" bash ./install.sh

test -f /etc/systemd/system/fugginnas.service
grep -q 'ExecStart=/usr/bin/python3 /repo/app.py' /etc/systemd/system/fugginnas.service
grep -q 'WorkingDirectory=/repo' /etc/systemd/system/fugginnas.service

line_count="$(wc -l /tmp/systemctl.log | awk '{print $1}')"
test "$line_count" -eq 3

echo "RUNTIME_OK"
