#!/usr/bin/env bash

set -euo pipefail

PORTS=(s1-eth1 s1-eth2 s1-eth3)

MAX_RATE=10000000
Q0_MIN=1000000
Q1_MIN=8000000

echo "Configuring QoS queues..."

# Make sure Mininet has created all switch ports.
for port in "${PORTS[@]}"; do
    if ! sudo ovs-vsctl list Port "$port" >/dev/null 2>&1; then
        echo "Error: $port does not exist."
        echo "Start Mininet and wait for the mininet> prompt first."
        exit 1
    fi
done

# Configure Queue 0 and Queue 1 on every switch port.
for port in "${PORTS[@]}"; do
    sudo ovs-vsctl \
        -- --id=@q0 create Queue \
        other-config:min-rate="$Q0_MIN" \
        other-config:max-rate="$MAX_RATE" \
        -- --id=@q1 create Queue \
        other-config:min-rate="$Q1_MIN" \
        other-config:max-rate="$MAX_RATE" \
        -- --id=@qos create QoS \
        type=linux-htb \
        other-config:max-rate="$MAX_RATE" \
        queues:0=@q0 queues:1=@q1 \
        -- set Port "$port" qos=@qos

    echo "$port configured."
done

echo ""
echo "QoS configuration complete."

# Display the resulting configuration.
for port in "${PORTS[@]}"; do
    sudo ovs-appctl qos/show "$port"
done
