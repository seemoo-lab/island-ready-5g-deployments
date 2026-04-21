#!/bin/bash

docker exec -it webui bash -lc 'DB_URI="mongodb://${MONGO_IP}:27017/open5gs" misc/db/open5gs-dbctl showpretty'

