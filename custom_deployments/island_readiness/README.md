# Deployment 

This custom deployment demonstrates an island-ready Open5GS core network that features a MongoDB replica set to synchronize state across multiple cores.

## Setup

### Nodes
This deployment requires a three-node setup.
Two IP addresses need to be configured per node (for core + RAN), and IP connectivity is required between the nodes.
Specify these IP addresses in `.env`.

### Radio
Connect a radio to each node, e.g., following the [USRP Manual](https://files.ettus.com/manual/page_devices.html).

### UE
Set up a UE, e.g., from the [list of srsRAN-compatible UEs](https://docs.srsran.com/projects/project/en/latest/knowledge_base/source/cots_ues/source/index.html#cots-ues).
Programm a SIM card, insert it into the UE, and have the IMSI, KEY, and OPC ready.

### Additional Steps
Configure the `.env` to specify the IP addresses per node.

```zsh
git clone https://github.com/seemoo-lab/island-ready-5g-deployments.git
cd docker_open5gs
vi .env # set Lines 4 - 10 to match your setup
```

### Example:
We run the experiments on three lab computers that share a 10.10.11.0/24 network via the `eno1` interface. Each node connects to an USRP X310 via the `enp1s0f1` interface. The X310s have the IP address 192.168.40.2. We use a Google Pixel 6 with a programmable sysmocom SIM card.

```zsh
# on node1
sudo ip addr add 10.10.11.102/24 dev eno1
sudo ip addr add 10.10.11.202/24 dev eno1
sudo ip addr add 192.168.40.1/24 dev enp1s0f1
```

```zsh
# on node2
sudo ip addr add 10.10.11.104/24 dev eno1
sudo ip addr add 10.10.11.204/24 dev eno1
sudo ip addr add 192.168.40.1/24 dev enp1s0f1
```

```zsh
# on node3
sudo ip addr add 10.10.11.108/24 dev eno1
sudo ip addr add 10.10.11.208/24 dev eno1
sudo ip addr add 192.168.40.1/24 dev enp1s0f1
```


The `.env` file is configured as follows with 'X' modified per node.
```zsh
NODE1_IP=10.10.11.102
NODE2_IP=10.10.11.104
NODE3_IP=10.10.11.108
THIS_IP=10.10.11.10X     # configure per node
USRP_IP=192.168.40.2
GNB_IP=10.10.11.20X      # configure per mode
```



### Start the synchronization component

Start the synchronization component:

```zsh
# on all nodes
scripts/start-sync.sh
```

If you ever need to reset the synchronization, you can use the `reset-sync.sh` scrit. Howerver, note that this will delete all data stored in the MongoDB.

## Experiments

Section V of *Island-Ready 5G Deployments: Decentralized Core Networks for Crisis Connectivity at the Edge* describes three experiments.
The following instructions enable you to reproduce these experiments. Note that verbatim quotes are cited from [the aforementioned paper](https://arxiv.org).

Experiment 1 "shows that the subscriber information is successfully synchronized between the UDMs in core1 and core2. This demonstrates that the sync component correctly synchronizes the state of stateful NFs, which solves the challenge of distributing the 5G control plane."
Experiment 2 "demonstrates that the connect component activates failover core replicas to seamlessly take over connectivity when the active core fails."
Experiment 3 "shows that island-ready 5G systems based on our island-ready core design can transition to island connectivity."


### Experiment 1

(1.1) "We run Open5GS cores on node1 and node2."
```zsh
# on node1 and node2
docker compose -f 5g-active.yaml up -d
```

(1.2) "Open5GS features a web interface to manage the subscriber data in the UDM. We add the subscriber information of the SIM card of ue1 through the webui of core1."
```zsh
# browse NODE1_IP:9999
# or use the script on node1
scripts/add-subscriber.sh
```

(1.3) "We confirm that ue1 can access the website via route radio1, ran1, core1."
```zsh
# on node1
docker compose -f srsgnb.yaml up -d
```
Connect the UE to the 5G network of node1 and verify that you access the Internet.

(1.4) "Next, we observe that the subscriber information is also available in the webui of node2."
```zsh
# browse NODE2_IP:9999 and verify that the added subscriber is there.
# or use the script on node2
scripts/get-subscribers.sh
```

(1.5) "We shut down radio1 and start radio2."
```zsh
# on node1
docker compose -f srsgnb.yaml down

# on node2
docker compose -f srsgnb.yaml up -d
```

(1.6) "We confirm that ue1 can access the website via route radio2, ran2, core2."

Connect the UE to the 5G network of node2 and verify that you access the Internet.

(1.7) Clean up core and RAN deployments:
```zsh
# on node1 and node2
docker compose -f srsgnb.yaml down
docker compose -f 5g-active.yaml down
```


### Experiment 2

(2.1) "We run srsRAN on node1 and node2, but deploy Open5GS only on node1."
```zsh
# on node1
docker compose -f 5g-active.yaml up -d
docker compose -f srsgnb.yaml up -d

# on node2
GNB_AMF_IP=${CORE_IP} docker compose -f srsgnb.yaml up -d
```

(2.2) "We connect ue1 to radio2 and configure ran2 to connect to core1, simulating node1 as an area with an active core and node2 as an area with a failover core."

```zsh
# on node2
scripts/start-connect.sh
```

(2.3) "We confirm that we can access the website from ue1 via route radio2, ran2, core1."

Connect the UE to the 5G network of node2 and verify that you access the Internet.

(2.4) "We terminate core1 on node1 to simulate the active core being unavailable."

```zsh
docker compose -f 5g-active.yaml down
```

(2.5) "We observe that connect2 on node2 detects the unavailability of core1 and activates core2."

The started connection component detects the unavailability of core1, activates an island core on node2, reconfigures the RAN on node2, and terminates.

(2.6) "We confirm that we can access the website from ue1 via route radio2, ran2, core2."

Connect the UE to the 5G network of node2 and verify that you access the Internet.

### Experiment 3

(3.1) "We begin with the same setup as in the second experiment, where node1 hosts an active core and node2 has a failover core."

```zsh
# on node1
docker compose -f 5g-active.yaml up -d
docker compose -f srsgnb.yaml up -d

# on node2
GNB_AMF_IP=${CORE_IP} docker compose -f srsgnb.yaml up -d
scripts/start-connect.sh
```

(3.2) "At the local network edge of node1 and node2, we deploy web applications webapp1 and webapp2, respectively."
```zsh
# on node1 and node2
scripts/serve-webapp.sh
```

(3.3) "We connect ue1 to radio1 and ue2 to radio2. We confirm that both UEs can access both web applications and the website, which shows that global connectivity is intact."

Connect a UE to the 5G network of node1 and verify that you access the Internet, webapp1 on NODE1_IP:8080, and webapp2 on NODE2_IP:8080.
Connect a UE to the 5G network of node2 and verify that you access the Internet, webapp1 on NODE1_IP:8080, and webapp2 on NODE2_IP:8080.

(3.4) "Then, we disconnect node2 from the local lab network to simulate the area’s isolation."

```zsh
# on node2
scripts/isolate-node.sh
```

(3.5) "As a result, the connect component of node2 activates core2, which we confirm by observing that ue2 indicates 5G connectivity."

The started connection component detects the unavailability of core1, activates an island core on node2, reconfigures the RAN on node2, and terminates.

(3.6) "From ue1, we successfully connect to webapp1 and the website, confirming that area node1 was unaffected by the disconnection and is still in normal operation."

Connect a UE to the 5G network of node1 and verify that you access the Internet and webapp1 on NODE1_IP:8080.
Note that there is no access to the webapp2 on NODE2_IP:8080.

(3.7) "From ue2, connecting to webapp1 and the website fails because global connectivity is broken."

Connect a UE to the 5G network of node2 and verify that there is no access to the Internet and webapp1 on NODE1_IP:8080.

(3.8) "However, ue2 can still connect to webapp2 hosted at the local edge of node2."

Connect a UE to the 5G network of node2 and verify that you webapp2 on NODE2_IP:8080.

(3.9) Restore connectivity

```zsh
# on node2
scripts/reconnect-node.sh
```

(3.10) Shutdown cores
```zsh
# on all nodes
scripts/stop-sync.sh

# on node1 and node2
docker compose -f srsgnb.yaml down
scripts/stop-webserver.sh

# on node1
docker compose -f 5g-active.yaml down

# on node2
docker compose -f 5g-island.yaml down
```