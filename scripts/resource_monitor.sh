#!/bin/bash
# Docker Resource Monitor Script
# Usage: ./resource_monitor.sh [interval_seconds] [duration_minutes]

INTERVAL=${1:-10}  # デフォルト10秒間隔
DURATION=${2:-60}  # デフォルト60分間
LOG_DIR="./logs/resource"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/resource_${TIMESTAMP}.csv"

echo "timestamp,container,cpu_percent,mem_usage_mb,mem_limit_mb,mem_percent,net_in_mb,net_out_mb,block_in_mb,block_out_mb" > "$LOG_FILE"

END_TIME=$(($(date +%s) + DURATION * 60))

echo "📊 Resource monitoring started"
echo "   Interval: ${INTERVAL}s"
echo "   Duration: ${DURATION}min"
echo "   Log file: $LOG_FILE"
echo ""

while [ $(date +%s) -lt $END_TIME ]; do
    CURRENT_TIME=$(date +"%Y-%m-%d %H:%M:%S")

    docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}}" 2>/dev/null | \
    grep "^oza_" | \
    while IFS=',' read -r name cpu mem mem_pct net block; do
        # Parse memory usage
        mem_usage=$(echo "$mem" | awk -F'/' '{print $1}' | sed 's/[^0-9.]//g')
        mem_limit=$(echo "$mem" | awk -F'/' '{print $2}' | sed 's/[^0-9.]//g')

        # Parse network I/O
        net_in=$(echo "$net" | awk -F'/' '{print $1}' | sed 's/[^0-9.]//g')
        net_out=$(echo "$net" | awk -F'/' '{print $2}' | sed 's/[^0-9.]//g')

        # Parse block I/O
        block_in=$(echo "$block" | awk -F'/' '{print $1}' | sed 's/[^0-9.]//g')
        block_out=$(echo "$block" | awk -F'/' '{print $2}' | sed 's/[^0-9.]//g')

        # Remove % from cpu and mem_pct
        cpu=$(echo "$cpu" | sed 's/%//')
        mem_pct=$(echo "$mem_pct" | sed 's/%//')

        echo "$CURRENT_TIME,$name,$cpu,$mem_usage,$mem_limit,$mem_pct,$net_in,$net_out,$block_in,$block_out" >> "$LOG_FILE"
    done

    echo -ne "\r⏱️  $(date +%H:%M:%S) - Logging..."
    sleep $INTERVAL
done

echo ""
echo "✅ Monitoring complete. Log saved to: $LOG_FILE"
