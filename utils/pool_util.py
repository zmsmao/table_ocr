from concurrent.futures import ThreadPoolExecutor
from config.thread_config import ThreadConfig

def pool():
    pool=ThreadPoolExecutor(max_workers=ThreadConfig.pool_number)
    return pool