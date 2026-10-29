import socket
import time
import json
from pathlib import Path
import os

HOST = "10.0.0.1"
PORT = 5000
STATE_FILE = Path(__file__).resolve().parent / "state.json"

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((HOST, PORT))

players = {
    "P1": None,
    "P2": None
}

addresses = {}

stats = {
    player: {
        "last_sequence": 0,
        "total": 0,
        "received": 0,
        "lost": 0,
        "duplicates": 0,
        "out_of_order": 0,
        "packet_rate": 0.0,
        "rate_start": time.time(),
        "rate_packets": 0,
        "last_seen": None,
        "latency_ms": None,
        "average_latency_ms": None,
        "jitter_ms": None,
        "previous_latency_ms": None,
        "latency_samples": 0
    }
    for player in players
}


def save_state():
    dashboard_stats = {}

    for player, player_stats in stats.items():
        total_expected = player_stats["received"] + player_stats["lost"]
        loss_percentage = (
            player_stats["lost"] / total_expected * 100
            if total_expected > 0 else 0
        )

        dashboard_stats[player] = {
            "total": player_stats["total"],
            "received": player_stats["received"],
            "lost": player_stats["lost"],
            "duplicates": player_stats["duplicates"],
            "out_of_order": player_stats["out_of_order"],
            "loss_percentage": round(loss_percentage, 2),
            "packet_rate": round(player_stats["packet_rate"], 2),
            "latency_ms": (
                round(player_stats["latency_ms"], 2)
                if player_stats["latency_ms"] is not None else None
            ),
            "average_latency_ms": (
                round(player_stats["average_latency_ms"], 2)
                if player_stats["average_latency_ms"] is not None else None
            ),
            "jitter_ms": (
                round(player_stats["jitter_ms"], 2)
                if player_stats["jitter_ms"] is not None else None
            ),
            "last_seen": player_stats["last_seen"],
            "online": (
                player_stats["last_seen"] is not None
                and time.time() - player_stats["last_seen"] < 2
            )
        }

    state = {
        "players": players,
        "stats": dashboard_stats,
        "updated_at": time.time()
    }

    temp_file = STATE_FILE.with_suffix(".tmp")

    with open(temp_file, "w") as file:
        json.dump(state, file)

    os.replace(temp_file, STATE_FILE)


print("UDP Game Server started")
print("Waiting for players...")

while True:
    data, address = server.recvfrom(1024)

    try:
        message = data.decode()
        parts = message.split(",")

        if len(parts) < 6:
            continue

        player_id = parts[0]
        sequence = int(parts[1])
        x = parts[2]
        y = parts[3]
        action = parts[4]
        timestamp = float(parts[5])
    except (UnicodeDecodeError, ValueError):
        continue

    if player_id not in players:
        continue

    player_stats = stats[player_id]

    if sequence == 1 and player_stats["last_sequence"] > 1:
        print(player_id, "restarted; resetting sequence")
        player_stats["last_sequence"] = 0

    addresses[player_id] = address

    current_time = time.time()
    player_stats["total"] += 1
    player_stats["rate_packets"] += 1
    player_stats["last_seen"] = current_time

    elapsed = current_time - player_stats["rate_start"]
    if elapsed >= 1:
        player_stats["packet_rate"] = player_stats["rate_packets"] / elapsed
        player_stats["rate_packets"] = 0
        player_stats["rate_start"] = current_time

    if sequence > player_stats["last_sequence"]:
        if player_stats["last_sequence"] > 0:
            if sequence > player_stats["last_sequence"] + 1:
                player_stats["lost"] += sequence - player_stats["last_sequence"] - 1

        player_stats["received"] += 1
        player_stats["last_sequence"] = sequence

        players[player_id] = {
            "sequence": sequence,
            "x": x,
            "y": y,
            "action": action,
            "timestamp": timestamp
        }

        addresses[player_id] = address
        packet_status = "New packet"

    elif sequence == player_stats["last_sequence"]:
        player_stats["duplicates"] += 1
        packet_status = "Duplicate packet"

    else:
        player_stats["out_of_order"] += 1
        packet_status = "Out-of-order packet"

    latency_ms = max(0, current_time - timestamp) * 1000
    player_stats["latency_ms"] = latency_ms
    samples = player_stats["latency_samples"]

    if samples == 0:
        player_stats["average_latency_ms"] = latency_ms
        player_stats["jitter_ms"] = 0.0
    else:
        previous_latency = player_stats["previous_latency_ms"]
        variation = abs(latency_ms - previous_latency)
        player_stats["jitter_ms"] += (variation - player_stats["jitter_ms"]) / (samples + 1)
        player_stats["average_latency_ms"] += (
            latency_ms - player_stats["average_latency_ms"]
        ) / (samples + 1)

    player_stats["previous_latency_ms"] = latency_ms
    player_stats["latency_samples"] += 1

    save_state()

    print("\nReceived from", player_id)
    print("Sequence:", sequence)
    print("Status:", packet_status)
    print("Address:", address)
    print("Latency:", round(latency_ms, 2), "ms")

    print("\nCurrent Game State:")
    print("P1:", players["P1"])
    print("P2:", players["P2"])

    print("\nPacket Statistics:")
    for player in ["P1", "P2"]:
        player_stats = stats[player]
        total_expected = player_stats["received"] + player_stats["lost"]
        loss_percentage = (
            player_stats["lost"] / total_expected * 100
            if total_expected > 0 else 0
        )

        print(
            player,
            "- Total:", player_stats["total"],
            "Received:", player_stats["received"],
            "Lost:", player_stats["lost"],
            "Duplicates:", player_stats["duplicates"],
            "Out-of-order:", player_stats["out_of_order"],
            "Loss:", round(loss_percentage, 2), "%",
            "PPS:", round(player_stats["packet_rate"], 2)
        )

    game_state = str(players)
    for player in addresses:
        server.sendto(game_state.encode(), addresses[player])

    print("Game state sent to", len(addresses), "player(s)")
