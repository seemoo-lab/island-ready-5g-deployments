#!/usr/bin/env bash
set -euo pipefail

# --- get env ---

set -a
source .env
set +a

# --- helpers ---

wait_mongo() {
  local host="$1"
  local port="${2:-27017}"

  echo "Waiting for Mongo on ${host}:${port} ..."
  until nc -z "$host" "$port" >/dev/null 2>&1; do
    sleep 1
  done
}

# --- config ---

HOSTS=(${NODE1_IP} ${NODE2_IP} ${NODE3_IP})



############################################################
############################################################
############################################################

docker compose -f 5g-failover.yaml up -d

echo "Waiting until all Mongo instances respond ..."
for host in "${HOSTS[@]}"; do
  wait_mongo "$host"
done
echo "All MongoDB instances are ready."

if [[ "$THIS_IP" == "$MONGO_RS_PRIMARY" ]]; then
echo "Attempting to initialize the replica set ..."
  mongosh --host ${MONGO_RS_PRIMARY}:27017 <<EOF
try {
  rs.status();
  print('Replica set already initialized.');
} catch (e) {
  printjson(rs.initiate({
    _id: '${MONGO_RS_NAME}',
    members: [
      { _id: 0, host: '${NODE1_IP}:27017'},
      { _id: 1, host: '${NODE2_IP}:27017'},
      { _id: 2, host: '${NODE3_IP}:27017'}
    ]
  }));
}
EOF
  sleep 15
else
  echo "Waiting for init and primary election ..."
  sleep 20
fi

echo "Replica set status:"
mongosh --eval 'rs.status()'