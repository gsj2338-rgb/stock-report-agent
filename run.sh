#!/bin/bash
cd /Users/miracle/Desktop/주식리포트

TODAY=$(date +%Y-%m-%d)
LOCK_FILE="logs/last_run.txt"

# 오늘 이미 실행했으면 종료
if [ -f "$LOCK_FILE" ] && [ "$(cat $LOCK_FILE)" = "$TODAY" ]; then
    exit 0
fi

# 평일(월~금)에만 실행
DAY=$(date +%u)
if [ "$DAY" -ge 6 ]; then
    exit 0
fi

/usr/bin/python3 main.py >> logs/run.log 2>&1

# 성공하면 오늘 날짜 저장
if [ $? -eq 0 ]; then
    echo "$TODAY" > "$LOCK_FILE"
fi
