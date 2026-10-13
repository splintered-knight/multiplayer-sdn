Multiplayer Game Communication Network

An SDN-controlled network that prioritizes real-time multiplayer game traffic with live QoS monitoring on a web dashboard.

🌟 Overview

Traditional networks treat all data packets equally, causing lag, packet loss, and high jitter in fast-paced multiplayer games. This project implements a Software-Defined Networking (SDN) architecture using Mininet, an OS-Ken controller, and an OpenFlow 1.3 switch to dynamically prioritize UDP game traffic while tracking performance metrics live.

🏗️ Architecture & Design

The system is structured into three main layers:

Control Plane:

Powered by the OS-Ken controller running OpenFlow 1.3 over TCP port 6653.

Learns MAC addresses and installs dynamic flow rules to route UDP port 5000 game traffic into a high-priority queue (Queue 1).

Data Plane & Game Simulation:

Emulated via Mininet in a star topology (topology.py).

Hosts:

h1 (Game Server): IP 10.0.0.1, running server.py on UDP port 5000.

h2 (Player 1): IP 10.0.0.2, running client.py.

h3 (Player 2): IP 10.0.0.3, running client2.py.

Clients transmit position and action updates 10 times per second; the server processes them and broadcasts the shared state back.

Monitoring & Visualization:

The server calculates packet loss, latency, jitter, and packet rate, writing them to state.json.

A Flask server exposes this data, and the web dashboard polls it every 200 ms to render real-time stats.

🛠️ Implementation Details

Key Design Decisions

Packet Format: player, sequence, x, y, action, timestamp

Traffic Classification: Controller matches UDP port 5000 and assigns OFPActionSetQueue(1).

Flow Rules: Priority 100 for game traffic, Priority 10 for default traffic.

Reliability Tracking: Sequence numbers identify packet loss, duplicates, and out-of-order delivery.

QoS Metrics: Timestamp differences calculate latency, average latency, and running jitter.

🚀 Getting Started

Prerequisites

Ensure you have the following installed on your environment (Ubuntu/Mininet VM recommended):

Python 3

Mininet

OS-Ken Controller

OpenFlow 1.3 compatible switch (ovs-testcontroller or Open vSwitch)

Flask (for the web dashboard)

Network Launch Command

Start the customized Mininet star topology with a remote OpenFlow 1.3 controller:

sudo mn --custom topology.py --topo game --controller remote --switch ovsk,protocols=OpenFlow13
