import os
import logging
import time
from logging.handlers import RotatingFileHandler

# log配置，实现日志自动按日期生成日志文件
def make_dir(make_dir_path):
    path = make_dir_path.strip()
    if not os.path.exists(path):
        os.makedirs(path)

def getLogHandler():
    # 日志地址
    log_dir_name = "logs/log"
    # 文件名，以日期作为文件名
    log_file_name = 'logger-' + time.strftime('%Y-%m-%d', time.localtime(time.time())) + '.log'
    # 创建日志文件
    log_file_folder = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir)) + os.sep + log_dir_name
    make_dir(log_file_folder)
    log_file_str = log_file_folder + os.sep + log_file_name

    # 默认日志等级的设置
    logging.basicConfig(level=logging.INFO)
    # 创建日志记录器，指明日志保存路径,每个日志的大小，保存日志的上限
    file_log_handler = RotatingFileHandler(log_file_str, maxBytes=1024 * 1024, backupCount=10, encoding='UTF-8')
    # 设置日志的格式                   发生时间    日志等级     日志信息文件名      函数名          行数        日志信息
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)s - %(message)s')
    # 将日志记录器指定日志的格式
    file_log_handler.setFormatter(formatter)

    # 日志等级的设置
    file_log_handler.setLevel(logging.INFO)

    return file_log_handler