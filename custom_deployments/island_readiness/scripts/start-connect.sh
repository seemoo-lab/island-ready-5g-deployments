#!/bin/bash

set -a
source .env
set +a

CORE_IP=${NODE1_IP}

# docker compose -f srsgnb.yaml down
# docker compose -f sa-deploy.yaml down
docker compose -f 5g-failover.yaml up -d

# GNB_AMF_IP=${CORE_IP} docker compose -f srsgnb.yaml up -d 

while true; do
    if ! nc -u -z -w 2 "$CORE_IP" "2152" > /dev/null 2>&1; then
			docker compose -f srsgnb.yaml down
			sleep 4
			source .env-island
			docker compose -f 5g-island.yaml up -d
			sleep 25
			docker compose -f srsgnb.yaml up -d 
			break	
    fi
    sleep 5
done
