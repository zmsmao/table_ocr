"""
-------------------------------------------------
    File Name:     pool_util
    Description:   线程池，仅用于请求结束后异步清理图片目录
    date:          2023.08
-------------------------------------------------
    Change Activity: 2023.08
-------------------------------------------------
"""
from concurrent.futures import ThreadPoolExecutor

from config.thread_config import ThreadConfig


def pool():
    '''
    创建一个固定大小的线程池。
    '''
    return ThreadPoolExecutor(max_workers=ThreadConfig.pool_number)
