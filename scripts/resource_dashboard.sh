#!/bin/bash
# Real-time Resource Dashboard
# Usage: ./resource_dashboard.sh

while true; do
    clear
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                    🖥️  OZA System Resource Dashboard                         ║"
    echo "║                         $(date '+%Y-%m-%d %H:%M:%S')                              ║"
    echo "╠══════════════════════════════════════════════════════════════════════════════╣"
    echo ""

    # Container stats
    echo "📦 Container Resources:"
    echo "────────────────────────────────────────────────────────────────────────────────"
    printf "%-22s %8s %15s %8s %18s\n" "CONTAINER" "CPU %" "MEMORY" "MEM %" "NET I/O"
    echo "────────────────────────────────────────────────────────────────────────────────"

    docker stats --no-stream --format "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}" 2>/dev/null | \
    grep "^oza_" | \
    while IFS=$'\t' read -r name cpu mem mem_pct net; do
        printf "%-22s %8s %15s %8s %18s\n" "$name" "$cpu" "$mem" "$mem_pct" "$net"
    done

    echo ""
    echo "────────────────────────────────────────────────────────────────────────────────"

    # Total summary
    TOTAL_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" 2>/dev/null | grep -v "^$" | \
        awk -F'/' '{gsub(/[^0-9.]/,"",$1); sum+=$1} END {printf "%.0f", sum}')
    TOTAL_CPU=$(docker stats --no-stream --format "{{.CPUPerc}}" 2>/dev/null | grep -v "^$" | \
        awk '{gsub(/%/,"",$1); sum+=$1} END {printf "%.1f", sum}')

    echo ""
    echo "📊 Summary:"
    echo "   Total CPU:    ${TOTAL_CPU}%"
    echo "   Total Memory: ${TOTAL_MEM}MB"
    echo ""
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Press Ctrl+C to exit"

    sleep 5
done
