
#!/bin/bash
source activate table_ocr 


# 启动web.py应用程序，将输出重定向到日志文件
nohup python -u web.py > ./table_ocr.log 2>&1 &

# 记录进程ID到pid文件
echo $! > ./table_ocr.pid

# 退出Anaconda环境
conda deactivate
