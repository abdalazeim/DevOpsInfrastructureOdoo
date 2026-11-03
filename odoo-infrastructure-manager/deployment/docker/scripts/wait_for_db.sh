#!/bin/bash
set -e

HOST="${1:-db}"
PORT="${2:-5432}"
TIMEOUT="${3:-60}"

echo "⏳ Waiting for PostgreSQL at $HOST:$PORT (timeout: ${TIMEOUT}s)..."

for i in $(seq 1 $TIMEOUT); do
    if command -v pg_isready &> /dev/null; then
        if pg_isready -h "$HOST" -p "$PORT" -q 2>/dev/null; then
            echo "✅ PostgreSQL is ready after ${i}s"
            exit 0
        fi
    else
        if exec 6<>/dev/tcp/"$HOST"/"$PORT" 2>/dev/null; then
            exec 6>&-
            echo "✅ PostgreSQL is ready after ${i}s"
            exit 0
        fi
    fi
    sleep 1
done

echo "❌ PostgreSQL did not become ready within ${TIMEOUT}s"
exit 1
