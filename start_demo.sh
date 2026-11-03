
#!/usr/bin/env bash

MODE="${1:-on}"

case "$MODE" in
    on)
        GAME_QUEUE=1
        ;;
    off)
        GAME_QUEUE=0
        ;;
    *)
        echo "Usage: ./start_demo.sh [on|off]"
        exit 1
        ;;
esac

echo "Starting demo with game traffic on Queue $GAME_QUEUE"

ptyxis --new-window --title="OS-Ken Controller" -- env GAME_QUEUE="$GAME_QUEUE" bash -lc '
cd "$HOME/multiplayer-sdn" || exit 1
source osken-venv/bin/activate || exit 1
osken-manager controller.py
echo "OS-Ken stopped."
exec bash
'

sleep 2

ptyxis --new-window --title="Flask Dashboard" -- bash -lc '
cd "$HOME/multiplayer-sdn" || exit 1
python3 web_server.py
echo "Flask stopped."
exec bash
'

sleep 1

ptyxis --new-window --title="Mininet" -- bash -lc '
cd "$HOME/multiplayer-sdn" || exit 1
sudo mn --custom topology.py --topo game --switch ovsk,protocols=OpenFlow13 --controller=remote,ip=127.0.0.1,port=6653
echo "Mininet stopped."
exec bash
'

sleep 3

xdg-open "http://127.0.0.1:8000/" >/dev/null 2>&1 || true

echo ""
echo "Demo launched with QoS $MODE."
echo "Wait for the mininet> prompt."
echo "Then configure QoS using: sudo bash ~/multiplayer-sdn/setup_qos.sh"
echo "Finally, start the game using: source start_hosts.txt"
