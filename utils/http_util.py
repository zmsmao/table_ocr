from flask import Response
import json


# 处理响应成功的函数
def success_response(data):
    # 构建响应 JSON 数据
    response_data = {
        # 'image_result': image_result,
        'msg':'操作成功',
        'splicing_data':data,
        'code':200
        # 'source_data':results
    }
    
    response = Response(
        response=json.dumps(response_data, ensure_ascii=False).encode('utf-8'),
        status=200,
        mimetype='application/json'
    )
    # 返回响应 JSON 数据
    return response

# 处理响应失败的函数
def error_response(message='操作失败', status_code=500):
    # 构建响应 JSON 数据
    response_data = {
        # 'image_result': image_result,
        'msg':message,
        'code':500
        # 'source_data':results
    }
    response = Response(
        response=json.dumps(response_data, ensure_ascii=False).encode('utf-8'),
        status=status_code,
        mimetype='application/json'
    )
    # 返回响应 JSON 数据
    return response
