from concurrent.futures import ThreadPoolExecutor
from config.thread_config import ThreadConfig

def pool():
    pool=ThreadPoolExecutor(max_workers=ThreadConfig.pool_number)
    return pool

# def mpPool():
#     # 创建进程池
#     pool = Pool(ThreadConfig.pool_number)
#     return pool

# def instancesOCR():
#     return [PaddleOCR() for i in range(ThreadConfig.pool_number)]

# # 处理请求的函数
# def handle_request(request_queue:list,instances:list):
#     while True:
#         if request_queue:
#             request = request_queue.pop(0)  # 取出队列中的请求
#             instance = None
#             for obj in instances:
#                 if obj is not None:
#                     instance = obj
#                     break
#             if instance is not None:
#                 result = instance.ocr(request)  # 处理请求
#                 print(result)
#                 instances[instances.index(instance)] = None  # 将实例设为已使用
#             else:
#                 time.sleep(1)  # 暂停1秒
#         else:
#             time.sleep(1)  # 暂停1秒