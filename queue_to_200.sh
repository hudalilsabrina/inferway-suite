#!/usr/bin/env bash
# Queue: tunggu batch yang jalan, lalu lanjut batch sampai total key >= TARGET.
# Usage: ./queue_to_200.sh [TARGET] [BATCH_SIZE]
cd "$(dirname "$0")"
TARGET="${1:-200}"
BATCH="${2:-60}"

count_keys() { grep -c "inferway_live_" accounts.txt 2>/dev/null || echo 0; }

echo "[queue] target=$TARGET batch=$BATCH | start: $(count_keys) key"

# tunggu batch.py yang sedang jalan selesai (pakai pola [b] agar tak self-match)
while pgrep -f "[b]atch\.py" >/dev/null 2>&1; do
  echo "[queue] menunggu batch berjalan... $(count_keys) key | $(date +%H:%M:%S)"
  sleep 60
done

# loop sampai target
while [ "$(count_keys)" -lt "$TARGET" ]; do
  CUR=$(count_keys)
  NEED=$((TARGET - CUR))
  N=$BATCH
  [ "$NEED" -lt "$N" ] && N=$NEED
  # sisakan buffer kalau ada kegagalan (~10%)
  N=$(( N + N/10 + 1 ))
  echo "[queue] $(date +%H:%M:%S) | $CUR key | butuh $NEED | jalankan batch $N"
  xvfb-run -a .venv/bin/python batch.py "$N" --delay 10 >> data/_queue.log 2>&1
  echo "[queue] batch selesai -> $(count_keys) key"
  sleep 5
done

echo "[queue] DONE: $(count_keys) key (target $TARGET) @ $(date)"
