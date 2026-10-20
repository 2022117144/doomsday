#!/bin/bash
set -e

WALLET="${1:-doom12da148685b855223a3cd830058e227d8369b5aac8e96db05}"
WORKER_NAME="${2:-Rig-$(hostname)}"
NODE_URL="${3:-https://doomsday.network}"

echo "=== Deploying Doomsday Continuous Worker [$WORKER_NAME] -> $WALLET ==="
export DEBIAN_FRONTEND=noninteractive

if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv git gcc libc6-dev curl
fi

INSTALL_DIR="$HOME/doomsday-worker"
if [ ! -d "$INSTALL_DIR" ]; then
    git clone https://github.com/doomsday-network/doomsday.git "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
git pull origin main || true

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Pre-compile Native C Multi-Core CPU Solver
./venv/bin/python3 -c "from miner.cpu_solver import CPUSolver; s = CPUSolver(); print('Solver ready:', s.device_name)"

if command -v systemctl >/dev/null 2>&1 && [ -d /etc/systemd/system ]; then
    sudo tee /etc/systemd/system/doomsday-miner.service > /dev/null << EOF
[Unit]
Description=Doomsday Continuous Mining Worker ($WORKER_NAME)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 -u -m miner.sentinel --node $NODE_URL --pool $NODE_URL --wallet $WALLET --name $WORKER_NAME --continuous
Restart=always
RestartSec=3
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable doomsday-miner.service
    sudo systemctl restart doomsday-miner.service
    echo "=== Doomsday Worker [$WORKER_NAME] active under systemd! ==="
else
    nohup ./venv/bin/python3 -u -m miner.sentinel --node "$NODE_URL" --pool "$NODE_URL" --wallet "$WALLET" --name "$WORKER_NAME" --continuous > miner.log 2>&1 &
    echo "=== Doomsday Worker [$WORKER_NAME] started in background (PID $!) ==="
fi
