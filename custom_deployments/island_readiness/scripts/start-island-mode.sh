#!/bin/bash
set -euo pipefail

set -a
source .env
set +a

MONGO_HOST=${NODE2_IP}
MONGO_PORT="27017"

echo "Waiting for MongoDB on ${MONGO_HOST}:${MONGO_PORT} ..."
until mongosh --quiet --host "${MONGO_HOST}:${MONGO_PORT}" --eval 'db.adminCommand({ ping: 1 }).ok' >/dev/null 2>&1; do
  sleep 1
done

echo "MongoDB is reachable. Reconfiguring replica set '${MONGO_RS_NAME}' to single node ${MONGO_HOST}:${MONGO_PORT} ..."

mongosh --host "${MONGO_HOST}:${MONGO_PORT}" <<EOF
try {
  print("Current rs.status():");
  printjson(rs.status());
} catch (e) {
  print("rs.status() failed:");
  print(e);
}

cfg = rs.conf();
print("Current rs.conf():");
printjson(cfg);

/* Keep the surviving node's ORIGINAL _id, which is 1 */
cfg.members = [
  {
    _id: 1,
    host: "${MONGO_HOST}:${MONGO_PORT}",
    priority: 1,
    votes: 1
  }
];

cfg.version = cfg.version + 1;

print("Applying forced reconfig...");
printjson(rs.reconfig(cfg, { force: true }));

print("Waiting a bit for election...");
sleep(5000);

print("New rs.status():");
printjson(rs.status());

print("New rs.conf():");
printjson(rs.conf());
EOF

echo
echo "Done."
echo "Use this MongoDB URI:"
echo "  mongodb://${MONGO_HOST}:${MONGO_PORT}/open5gs?replicaSet=${RS_NAME}"
