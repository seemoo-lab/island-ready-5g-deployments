#!/bin/bash

docker exec -it webui bash -lc 'DB_URI="mongodb://${MONGO_IP}:27017/open5gs" misc/db/open5gs-dbctl add 001010000009931 9000C3B505F27D9EBDB8F6E44AD5FD6A A18810EBBD651628E8FE45B1964A20E4'

