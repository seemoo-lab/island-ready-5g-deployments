#!/usr/bin/env bash

./stop-sync.sh
docker volume rm -f docker_open5gs_mongodbdata
./start-sync.sh