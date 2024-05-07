from flask import Flask,request,render_template
from config.web_config import WebConfig
from config.file_config import FileConfig
from service.base_service import common,res,all,com_video_img
from utils.http_util import success_response,error_response
import utils.file_util as fiul
import utils.common_util as comm
from datetime import timedelta
import utils.pool_util as pout
from logs.log_handle import getLogHandler
import datetime
import json
from multiprocessing import Pool
from threading import Lock



app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['LOGGER_HANDLER_POLICY'] = 'always'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(hours=1)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
# app.config['FLASK_DEBUG'] = False
# 添加日志配置
app.logger.addHandler(getLogHandler())
# 激活上下文
ctx = app.app_context()
ctx.push()

@app.route('/index',methods=['GET'])
def html():
    return render_template('index.html')

@app.route('/vidImg',methods=['GET'])
def upload():
    return render_template('vidImg.html')

@app.route("/process/vidImg",methods=['POST'])
def video_and_img():
    try:
        # 检查是否有文件被上传
        if 'file' not in request.files:
            log_message = f'Request Error\nTime: {datetime.datetime.now()}\nMethod: {request.method}\nURL: {request.url}\nException: {"没有选择文件"}'
            app.logger.error(log_message)
            return error_response("没有选择文件")
        file = request.files['file']
        # 检查文件名是否为空
        if file.filename == '':
            log_message = f'Request Error\nTime: {datetime.datetime.now()}\nMethod: {request.method}\nURL: {request.url}\nException: {"文件名不能为空"}'
            app.logger.error(log_message)
            return error_response("文件名不能为空")
        # 检查文件类型
        file_type =comm.get_file_type(file.filename)
        if file_type == 0:
            log_message = f'Request Error\nTime: {datetime.datetime.now()}\nMethod: {request.method}\nURL: {request.url}\nException: {"不支持的文件类型,仅支持图片和视频"}'
            app.logger.error(log_message)
            return error_response("不支持的文件类型,仅支持图片和视频")
        uuid=comm.generate_unique_id()
        di = fiul.uuid_save_web_file(file,uuid)
        flag_pool = False
        if counter[0] <sitePro:
            counter[0] += 1
            flag_pool = True
            pool = Pool(1)
            result = pool.apply_async(com_video_img, (file_type,uuid,di))
            # 获取任务的返回结果
            results = result.get()
        else:
            results = com_video_img(file_type,uuid,di)
        return success_response(results)
    except Exception as e:
        app.logger.error(str(e))
        return error_response(str(e))
    finally:
        if flag_pool:
            counter[0] -= 1
            pool.close()
        if FileConfig.is_delete_file:
            root=fiul.uuid_save_root(uuid)
            fiul.dir_delete(root)

# counter = 0
# counter_lock = Lock()

# @app.teardown_request
# def decrement_counter(exception=None):
#     global counter
#     counter_lock.acquire()
#     counter -= 1
#     counter_lock.release()

# @app.before_request
# def decrement_counter():
#     global counter
#     counter_lock.acquire()
#     counter += 1
#     counter_lock.release()


@app.route('/process/common', methods=['POST'])
def process_common():
    data=request.json
    uuid=comm.generate_unique_id()
    try:
        #服务类
        # # 创建一个进程池对象
        # # 提交任务到进程池
        flag_pool = False
        if counter[0] <sitePro:
            counter[0] += 1
            flag_pool = True
            pool = Pool(1)
            result = pool.apply_async(common, (data,uuid))
            # 获取任务的返回结果
            results = result.get()
        else:
            results=common(data=data,uuid=uuid)
        name = data['name']+data['suffix']
        save_path = 'io/save_path/'+uuid
        log_message = f'Request Success\nTime: {datetime.datetime.now()}\nMethod: {request.method}\nURL: {request.url}\nImage: {name}\nUuidPath: {save_path}'
        app.logger.info(log_message)
        return success_response(results)
    except Exception as e:
        print(e)
        log_message = f'Request Error\nTime: {datetime.datetime.now()}\nMethod: {request.method}\nURL: {request.url}\nException: {str(e)}'
        app.logger.error(log_message)
        return error_response(str(e))
    finally:
        if flag_pool:
            counter[0] -= 1
            pool.close()
        if FileConfig.is_delete_file:
            root=fiul.uuid_save_root(uuid)
            cache=fiul.uuid_cache_root(uuid)
            executor.submit( fiul.dir_delete(root))
            executor.submit( fiul.dir_delete(cache))

@app.route('/process/res', methods=['POST'])
def process_res():
    data=request.json
    uuid=comm.generate_unique_id()
    try:
        flag_pool = False
        #服务类
        if counter[0] <sitePro:
            flag_pool = True
            counter[0] += 1
            pool = Pool(1)
            result = pool.apply_async(res, (data,uuid,None))
            # 获取任务的返回结果
            results = result.get()
        else:
            results=res(data=data,uuid=uuid,executor=executor)
        name = data['name']+data['suffix']
        save_path = 'io/save_path/'+uuid
        log_message = f'Request Success\nTime: {datetime.datetime.now()}\nMethod: {request.method}\nURL: {request.url}\nImage: {name}\nUuidPath: {save_path}'
        app.logger.info(log_message)
        return success_response(results)
    except Exception as e:
        print(e)
        log_message = f'Request Error\nTime: {datetime.datetime.now()}\nMethod: {request.method}\nURL: {request.url}\nException: {str(e)}'
        app.logger.error(log_message)
        return error_response(str(e))
    finally:
        if flag_pool:
            counter[0] -= 1
            pool.close()
        if FileConfig.is_delete_file:
            root=fiul.uuid_save_root(uuid)
            cache=fiul.uuid_cache_root(uuid)
            executor.submit( fiul.dir_delete(root))
            executor.submit( fiul.dir_delete(cache))

@app.route('/process/all', methods=['POST'])
def process_all():
    data=request.json
    uuid=comm.generate_unique_id()
    try:
        #服务类
        flag_pool = False
        #服务类
        if counter[0] <sitePro:
            flag_pool = True
            counter[0] += 1
            pool = Pool(1)
            result = pool.apply_async(all, (data,uuid,None))
            # 获取任务的返回结果
            results = result.get()
        else:
            results=all(data=data,uuid=uuid,executor=executor)
        name = data['name']+data['suffix']
        save_path = 'io/save_path/'+uuid
        log_message = f'Request Success\nTime: {datetime.datetime.now()}\nMethod: {request.method}\nURL: {request.url}\nImage: {name}\nUuidPath: {save_path}'
        app.logger.info(log_message)
        return success_response(results)
    except Exception as e:
        print(e)
        log_message = f'Request Error\nTime: {datetime.datetime.now()}\nMethod: {request.method}\nURL: {request.url}\nException: {str(e)}'
        app.logger.error(log_message)
        return error_response(str(e))
    finally:
        if flag_pool:
            counter[0] -= 1
            pool.close()
        if FileConfig.is_delete_file:
            root=fiul.uuid_save_root(uuid)
            cache=fiul.uuid_cache_root(uuid)
            executor.submit( fiul.dir_delete(root))
            executor.submit( fiul.dir_delete(cache))

# 注册UserController路由
if __name__ == '__main__':
    #开启服务
    executor=pout.pool()
    #进程计数
    counter = [0]
    sitePro = 5
    app.run(host='0.0.0.0', port=WebConfig.port, debug=True, threaded=True, processes=1)
    '''
    app.run()中可以接受两个参数，分别是threaded和processes，用于开启线程支持和进程支持。
    1.threaded : 多线程支持，默认为False，即不开启多线程;
    2.processes：进程数量，默认为1.
    '''