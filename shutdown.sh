#!/bin/bash
pid=$(cat ./table_ocr.pid)

# 杀死web.py应用程序进程
if [ -n "$pid" ]; then
    kill $pid
    echo "web.py应用程序已停止。"
else
    echo "未找到web.py应用程序的进程ID。"
fi
