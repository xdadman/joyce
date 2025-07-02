#!/bin/bash

# IP Range Scanner Script
# Usage: ./scan_subnet.sh [subnet] [port]
# Example: ./scan_subnet.sh 10.72.3 80

# Default values
SUBNET="${1:-10.0.0}"
PORT="${2:-80}"

echo "Scanning subnet: ${SUBNET}.1-254"
echo "Port: ${PORT}"
echo "Starting scan..."
echo "=========================="

# Loop through IPs 1 to 254
for i in {1..254}; do
    IP="${SUBNET}.${i}"

    # Perform curl with timeout
    echo -n "Checking ${IP}: "

    # Use curl with timeout and suppress output, capture exit code
    if curl -s --connect-timeout 3 --max-time 5 "http://${IP}:${PORT}" > /dev/null 2>&1; then
        echo "✓ RESPONDING"
    else
        echo "✗ No response"
    fi
done

echo "=========================="
echo "Scan complete!"
