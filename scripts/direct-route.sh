#!/usr/bin/env bash

set -euo pipefail

ACTION="${1:-}"
DIRECT_ROUTE_IP="${DIRECT_ROUTE_IP:-}"
PRIORITY="100"

if [[ ! "${DIRECT_ROUTE_IP}" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    echo "DIRECT_ROUTE_IP must be an IPv4 address" >&2
    exit 2
fi

rule_exists() {
    ip -4 rule show \
        | awk \
            -v priority="${PRIORITY}:" \
            -v destination="${DIRECT_ROUTE_IP}" '
                $1 == priority &&
                $2 == "to" &&
                ($3 == destination || $3 == destination "/32") &&
                $4 == "lookup" &&
                $5 == "main" {
                    found = 1
                }
                END { exit found ? 0 : 1 }
            '
}

case "${ACTION}" in
    start)
        if ! rule_exists; then
            ip -4 rule add \
                priority "${PRIORITY}" \
                to "${DIRECT_ROUTE_IP}/32" \
                lookup main
        fi
        ;;
    stop)
        if rule_exists; then
            ip -4 rule del \
                priority "${PRIORITY}" \
                to "${DIRECT_ROUTE_IP}/32" \
                lookup main
        fi
        ;;
    *)
        echo "Usage: direct-route.sh <start|stop>" >&2
        exit 2
        ;;
esac
