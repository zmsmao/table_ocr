#### 表格识别

**注意事项**

1. 不支持一图多页的情况识别
2. 不支持一图多表格识别
3. 尽量保证图片中的表格清晰准确
4. 图片中表格倾斜无法识别
5. 图片尽量无外边框，或者是外边框尽量小

##### 架构说明

```bash
web_ocr
    ├── cache  #临时存储图片 
    ├── config #配置
    ├── domain #接受实体和响应实体
    ├── io     #图片主要存储路径
    ├── logs   #日志模块
    ├── model  #ocr模型 
    ├── normal #暂定
    ├── rules  #rules规则匹配
    ├── service #服务类
    ├── utils   #工具类
    └── web.py  #web启动文件
```


##### 环境准备

 - 安装Anaconda linux版本

   https://mirrors.tuna.tsinghua.edu.cn/anaconda/archive/

   1.  下载此版本： Anaconda3-2022.10-Linux-x86_64.sh
   2.  保存到**Linux**上的/opt文件夹中
   3.  使用以下指令：

   >```bash
   >cd /opt
   >
   >chmod 777 Anaconda3-2022.10-Linux-x86_64.sh
   >
   >sh Anaconda3-2022.10-Linux-x86_64.sh -b -p /opt/anaconda3
   >
   >echo 'export PATH="/opt/anaconda3/bin:$PATH"' >> ~/.bashrc
   >
   >source ~/.bashrc
   >
   >#切换环境之前要先激活环境，即使用如下指令
   >source activate
   >
   >#退出虚拟环境
   >conda deactivate 
   >```

- 安装Anaconda window版本

  https://blog.csdn.net/qq_45344586/article/details/124028689

- 创建环境

  1. 此处为加速下载，使用清华源

     ```bash
     conda create --name table_ocr python=3.7.4 --channel https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
     ```

  2. 切换环境

     ```bash
     conda activate table_ocr 
     ```

  3. 安装飞浆

     ```bash
     cpu版本：
     conda install paddlepaddle==2.4.2 --channel https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/Paddle/
     gpu版本：
     conda install paddlepaddle-gpu==2.4.2 cudatoolkit=11.7 -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/Paddle/ -c conda-forge
     之后添加环境变量：
     conda env config vars set LD_LIBRARY_PATH=$LD_LIBRARY_PATH:anaconda安装的路径/env/虚拟环境名称/include:anaconda安装的路径/env/虚拟环境名称/lib
     conda env config vars list
     gpu版本安装路径：
     https://www.paddlepaddle.org.cn/documentation/docs/zh/2.4/install/conda/linux-conda.html
     ```

  4. 安装ocr

     ```bash
     pip install "paddleocr==2.6.1.3" -i https://pypi.tuna.tsinghua.edu.cn/simple
     ```

  5. 其他安装依赖 使用vscode时需要初始化conda init 再切换环境，如果正常能切换环境则不再需要，之后查看环境pip list 看看是否还需要安装

     ```bash
     pip install opencv-python==4.6.0.66 -i https://pypi.tuna.tsinghua.edu.cn/simple
     pip install opencv-python-headless==4.8.0.74 -i https://pypi.tuna.tsinghua.edu.cn/simple 
     pip install opencv-contrib-python==4.6.0.66  -i https://pypi.tuna.tsinghua.edu.cn/simple 
     pip install Flask==2.2.5 -i https://pypi.tuna.tsinghua.edu.cn/simple
     pip install shutilwhich -i https://pypi.tuna.tsinghua.edu.cn/simple
     ```

  6. bug解决

     ```bash
     # 解决protobuf 不兼容问题。
     pip install protobuf==3.20.0
     # 解决linux动态链接库bug
     conda install nomkl
     ```

- 启动程序

  1. 使用指令`python -u web.py` 即可启动程序

     **注意**：第一次启动一定要测试请求，需下载模型
  2. 可使用 http://localhost:8111/index 测试页面使用，具体测试图片在 io/input_path/result

##### 接口说明

端口为 8111，可在config文件夹上的WebConfig配置

总体的返回参数为：

```json
成功的返回参数
{
    "msg":"操作成功",
    "splicing_data":data,
    "code":200
}
失败的返回参数
{
    "msg":message,
    "code":500
}
```

> **/process/vidImg**
>
> 说明：此方法是识别图片和视频的通用接口

  1. 请求方式
     post/file

  2. 请求参数

     ```json
     上传文件即可
     ```

   3. 返回值

      ```json
      {
          "msg":"操作成功",
          "splicing_data":[],
          "code":200
      }
      ```

  4. 启动程序之后有测试页面，访问http://localhost:8111/vidImg,测试上传文件即可。


> **/process/common**
>
> 说明：此方法只是识别图片

1. 请求方式
   post/json

2. 请求参数

   ```json
    {
       "image":"", #图片base64
   	"name":"0002", #图片名称
       "suffix":".jpg" #图片后缀
    }
   ```

 3. 返回值

    ```json
    [{
        "coordinates":[[]], #文本坐标
        "txt_result":"", #识别文本结果
        "name":"", #上传图片名称
        "txt_rate":"", # 文本识别率
        "uuid":"" #存储位置id
    }]
    ```



> **/process/all**
>
> 说明：此方法只是对表格进行了分割和单独识别。


2. 请求方式

   post/json

3. 请求参数

   ```json
   {
       "image":"", #图片base64
   	"name":"0002", #图片名称
       "suffix":".jpg" #图片后缀
   }
   ```

4. 返回值

   ```json
   [{
       "bbox": [[]], #分割图片坐标
       "result": [
       		[{
                   "coordinates":[[]], #文本坐标
                   "txt_result":"", #识别文本结果
                   "name":"", #上传图片名称
                   "txt_rate":"", # 文本识别率
                   "uuid":"" #存储位置id
   			}]
       ], 
      	"name":"0002", #图片名称
       "suffix": "后缀 分head end coordinate 表示图片头，尾和中间表格",
   	"uuid": #存储位置id
   }]
   ```



> **/process/res**
>
> 说明: 这个请求方法只对工作票文字识别提取有用 其他测试无效。

2. 请求方式

   post/json

3. 请求参数

   ```json
   {
       "image":"", #图片base64
   	"name":"0002", #图片名称
       "suffix":".jpg" #图片后缀
   }
   ```

4. 返回值

   ```json
   {
       "msg":"操作成功",
       "splicing_data":{
           "img_name":"0002.jpg", #图片名称
           "uuid":"io/save_path/74afd5a2", #分隔图片存储的位置
           "table_head":"附页", # 表头,由于是特定规则 只能区分工作票和附页
           "table_type":"表头"
           "table_body":{
               "head":{ # 字段都为String类型
                   "guardian":null, # 监护人
                   "telephone":null, #电话
                   "dept":null, # 单位和班组
                   "duty_number":null, # 人数
                   "start_time":null, # 开始时间
                   "end_time":null, #结束时间
                   "number":null, # 编号
                   "head":"附页"
               },
               "body":{ # 字段都为List<String>类型
                   "work_task":[], # 工作任务
                   "measure_main":null, # 工作要求的安全措施
                   "measure_other":[], # 其他安全措施和注意事项 一般用于附页
                   "other":[], #在还没有提取到到‘安全措施和注意事项’的前的内容 一般用于附页
                   "all":null, #暂定
                   "responsible":null #调度或设单位负责的安全措施
               }
           }
       },
       "code":200
   }
   ```
