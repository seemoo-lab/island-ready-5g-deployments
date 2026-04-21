#!/bin/bash
set -euo pipefail

set -a
source .env
set +a

NODES=("$NODE1_IP" "$NODE2_IP" "$NODE3_IP")

for ip in "${NODES[@]}"; do
  if [[ "$ip" != "$THIS_IP" ]]; then
    echo "Blocking UDP to $ip"
    sudo iptables -I INPUT -s "$ip" -j DROP
    sudo iptables -I OUTPUT -d "$ip" -j DROP
  fi
done