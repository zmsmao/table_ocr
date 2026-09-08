'''
表格 / 工作票识别服务

启动：python -u web.py
测试页：http://localhost:8111/index      （/process/all）
        http://localhost:8111/vidImg    （/process/vidImg）
'''
import datetime
import os
import traceback
from datetime import timedelta
from multiprocessing import Pool
from threading import Lock

from flask import Flask, request, render_template

from config.file_config import FileConfig
from config.web_config import WebConfig
from service.base_service import com_video_img, common, res, init_worker_engine
from service.base_service import all as ocr_all
from utils import file_util as fiul
from utils.common_util import generate_unique_id, get_file_type
from utils.http_util import error_response, success_response
from utils.pool_util import pool as new_thread_pool


app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(hours=1)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


# 同时最多并行执行的识别任务数，超出的任务在进程池里排队
MAX_PARALLEL_TASKS = 5

# 仅用于请求结束后异步删除图片目录
executor = new_thread_pool()

# 识别任务进程池（懒加载）
# Windows 下子进程会重新导入本模块，因此不能在导入阶段创建 Pool
_ocr_pool = None
_ocr_pool_lock = Lock()


# 修改后：
def get_ocr_pool():
    '''
    懒加载进程池。
    PaddleOCR 单次推理占用内存较大，放到子进程里跑，任务结束后内存可完整归还系统。
    '''
    global _ocr_pool
    with _ocr_pool_lock:
        if _ocr_pool is None:
            # 加入 initializer 使得每个子进程在创建时自动预热模型
            _ocr_pool = Pool(MAX_PARALLEL_TASKS, initializer=init_worker_engine)
        return _ocr_pool


def run_task(func, *args):
    '''
    提交一个识别任务并阻塞等待结果。超出并行上限时自动排队，不会无限 fork。
    '''
    return get_ocr_pool().apply_async(func, args).get()


def cleanup(uuid):
    '''
    请求结束后按需清理本次 uuid 产生的图片目录。
    '''
    if not FileConfig.is_delete_file:
        return
    executor.submit(fiul.dir_delete, fiul.uuid_save_root(uuid))
    executor.submit(fiul.dir_delete, fiul.uuid_cache_root(uuid))


def build_log(name, uuid, error=None):
    '''
    拼接请求日志，保持原有字段顺序。
    '''
    msg = (f'Time: {datetime.datetime.now()}\nMethod: {request.method}'
           f'\nURL: {request.url}\nImage: {name}\nUuidPath: io/save_path/{uuid}')
    if error is None:
        return f'Request Success\n{msg}'
    return f'Request Error\n{msg}\nException: {error}'


def handle_request(uuid, name, func, *args):
    '''
    统一的「执行任务 + 记日志 + 清理目录」，四个接口共用。
    '''
    try:
        results = run_task(func, *args)
        app.logger.info(build_log(name, uuid))
        return success_response(results)
    except Exception as e:
        error_stack = traceback.format_exc()
        app.logger.error(build_log(name, uuid, error_stack))
        return error_response(error_stack)
    finally:
        cleanup(uuid)


def parse_image_request():
    '''
    解析 json 入参并校验后缀合法性，避免拼出越界路径。
    返回 (data, 图片文件名)；校验失败抛 ValueError。
    '''
    data = request.get_json(silent=True)
    if not data or 'image' not in data:
        raise ValueError('请求体必须为 json，且包含 image 字段（图片 base64）')
    name = str(data.get('name') or '')
    suffix = str(data.get('suffix') or '')
    if not suffix.startswith('.') or '..' in suffix or '/' in suffix or '\\' in suffix:
        raise ValueError('suffix 非法，应为 .jpg / .png 这样的图片后缀')
    return data, name + suffix


def get_upload_file_type(filename):
    '''
    判断上传文件类型：1 图片，2 视频，0 不支持。文件名无扩展名时按不支持处理。
    '''
    try:
        return get_file_type(filename)
    except (IndexError, AttributeError):
        return 0


@app.route('/index', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/vidImg', methods=['GET'])
def upload():
    return render_template('vidImg.html')


@app.route('/process/vidImg', methods=['POST'])
def video_and_img():
    '''图片 / 视频通用识别，form-data 上传文件'''
    if 'file' not in request.files:
        return error_response('没有选择文件')
    file = request.files['file']
    if not file.filename:
        return error_response('文件名不能为空')
    file_type = get_upload_file_type(file.filename)
    if file_type == 0:
        return error_response('不支持的文件类型,仅支持图片和视频')
    uuid = generate_unique_id()
    # 先落盘，之后子进程才能按路径识别
    di = fiul.uuid_save_web_file(file, uuid)
    return handle_request(uuid, file.filename, com_video_img, file_type, uuid, di)


@app.route('/process/common', methods=['POST'])
def process_common():
    '''只做整图文字识别'''
    try:
        data, image_name = parse_image_request()
    except ValueError as e:
        error_stack = traceback.format_exc()
        app.logger.error(f"Request Error (/process/common):\n{error_stack}")
        return error_response(error_stack)
    uuid = generate_unique_id()
    return handle_request(uuid, image_name, common, data, uuid)


@app.route('/process/res', methods=['POST'])
def process_res():
    '''工作票结构化提取'''
    try:
        data, image_name = parse_image_request()
    except ValueError as e:
        error_stack = traceback.format_exc()
        app.logger.error(f"Request Error (/process/res):\n{error_stack}")
        return error_response(error_stack)
    uuid = generate_unique_id()
    return handle_request(uuid, image_name, res, data, uuid, None)


@app.route('/process/all', methods=['POST'])
def process_all():
    '''表格分割 + 逐格单独识别'''
    try:
        data, image_name = parse_image_request()
    except ValueError as e:
        error_stack = traceback.format_exc()
        app.logger.error(f"Request Error (/process/all):\n{error_stack}")
        return error_response(error_stack)
    uuid = generate_unique_id()
    return handle_request(uuid, image_name, ocr_all, data, uuid, None)


if __name__ == '__main__':
    # 对外提供服务时建议关掉调试器：TABLE_OCR_DEBUG=0
    debug = os.getenv('TABLE_OCR_DEBUG', '1') == '1'
    app.run(host='0.0.0.0', port=WebConfig.port, debug=debug, threaded=True)