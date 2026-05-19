#!/bin/sh
# SPDX-License-Identifier: MIT

echo "Press the AX6600 LED button within 10 seconds."
for gpio in /sys/class/gpio/gpio*/value; do
	[ -f "$gpio" ] || continue
	name=$(basename "$(dirname "$gpio")")
	before=$(cat "$gpio" 2>/dev/null || true)
	sleep 1
	after=$(cat "$gpio" 2>/dev/null || true)
	if [ "$before" != "$after" ]; then
		echo "${name#gpio}"
	fi
done
