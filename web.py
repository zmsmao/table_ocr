from flask import Flask,request,render_template
from config.web_config import WebConfig
from config.file_config import FileConfig
from service.base_service import common,res,all
from utils.http_util import success_response,error_response
import utils.file_util as fiul
import utils.common_util as comm
from datetime import timedelta
from utils.pool_util import pool
from logs.log_handle import getLogHandler
import datetime


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['LOGGER_HANDLER_POLICY'] = 'always'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(hours=1)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
# 添加日志配置
app.logger.addHandler(getLogHandler())
# 激活上下文
ctx = app.app_context()
ctx.push()

@app.route('/index',methods=['GET'])
def html():
    return render_template('index.html')


@app.route('/process/common', methods=['POST'])
def process_common():
    data=request.json
    uuid=comm.generate_unique_id()
    try:
        #服务类
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
        #服务类
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
        if FileConfig.is_delete_file:
            root=fiul.uuid_save_root(uuid)
            cache=fiul.uuid_cache_root(uuid)
            executor.submit( fiul.dir_delete(root))
            executor.submit( fiul.dir_delete(cache))

# 注册UserController路由
if __name__ == '__main__':
    #开启服务
    executor=pool()
    app.run(host='0.0.0.0', port=WebConfig.port, debug=True, threaded=True, processes=1)
    '''
    app.run()中可以接受两个参数，分别是threaded和processes，用于开启线程支持和进程支持。
    1.threaded : 多线程支持，默认为False，即不开启多线程;
    2.processes：进程数量，默认为1.
    '''