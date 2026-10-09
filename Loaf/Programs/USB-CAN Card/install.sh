#!/bin/sh
set -e
cat > /etc/udev/rules.d/99-mcp2210.rules <<'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="04d8", ATTRS{idProduct}=="00de", TAG+="uaccess"
KERNEL=="hidraw*", ATTRS{idVendor}=="04d8", ATTRS{idProduct}=="00de", TAG+="uaccess"
EOF

mv /etc/udev/rules.d/99-mcp2210.rules /etc/udev/rules.d/70-mcp2210.rules
udevadm control --reload-rules && udevadm trigger

echo done
