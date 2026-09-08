# Table OCR · 表格与工作票识别服务

基于 **Flask + PaddleOCR + OpenCV** 的表格 / 工作票结构化识别服务。
一张照片进去，经过矫正、切格、逐格 OCR、规则匹配，出来的是可直接落库的结构化 JSON。

![Python](https://img.shields.io/badge/Python-3.9.23-3776AB?logo=python&logoColor=white)
![PaddleOCR](https://img.shields.io/badge/PaddleOCR-2.7.3-00B4D8)
![OpenCV](https://img.shields.io/badge/OpenCV-4.6-5C3EE8?logo=opencv&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1.3-000000?logo=flask&logoColor=white)

---

## 目录

- [能力一览](#能力一览)
- [效果展示](#效果展示)
- [目录结构](#目录结构)
- [快速开始](#快速开始)
- [接口文档](#接口文档)
- [配置说明](#配置说明)
- [切图命名规则](#切图命名规则)
- [已知限制](#已知限制)
- [常见问题](#常见问题)

---

## 能力一览

| 能力 | 说明 |
| --- | --- |
| 通用文字识别 | 整图 OCR，返回文本框坐标、识别文本、置信度 |
| 表格切分 | 形态学提取横竖表格线，定位单元格并逐格切图 |
| 逐格识别 | 对切出的每个格子单独放大 + 锐化后识别，避免整图识别的串行错乱 |
| 工作票结构化 | 按票种规则抽取表头与正文字段，输出结构化 JSON |
| 图片 / 视频通用 | 上传图片直接识别，上传视频自动抽帧后逐帧识别 |
| 倾斜矫正 | 霍夫直线检测整体倾角并反向旋转，拍歪的表格也能正常切格 |

处理链路：

```
上传 → 落盘 → 压缩 → 倾斜矫正 → 二值化 → 提取表格线
     → 定位单元格 → 逐格切图 → 逐格 OCR → 规则匹配 → 结构化 JSON
```

---

## 效果展示

切图结果存放在 `io/save_path/{uuid}/coord`，一张表格会被切成若干小格，每格一个 jpg：

![](https://img.picui.cn/free/2024/06/11/6668007fcd012.png)

仓库内自带测试图片，位于 `io/input_path/result`，可直接用于验证。

---

## 目录结构

```
table_ocr
├── adapter     # 票种路由分发
├── cache       # 临时图片缓存
├── config      # 配置（路径 / 模型 / 算法参数 / 端口）
├── domain      # 请求与响应实体
├── io          # 图片主存储目录，每次请求一个 uuid 子目录
├── model       # OCR 推理模型（PP-OCRv4）
├── normal      # 字段规则备忘
├── rules       # 规则匹配（按票种拆分）
│   └── common  # 通用几何与表头解析
├── service     # 业务编排层
├── templates   # 测试页面
├── utils       # 工具类（图像处理 / 文件 / 通用 / 几何 / HTTP / 线程池）
├── web.py      # 服务入口
├── requirements.txt
└── start.sh / shutdown.sh
```

---

## 快速开始

### 环境要求

| 项目 | 版本 |
| --- | --- |
| Python | 3.9.23 |
| 操作系统 | Linux / Windows（Windows 下建议用 conda 终端） |
| 磁盘 | 模型与缓存约 1 GB |

### 1. 创建虚拟环境

使用 conda：

```bash
conda create -n table_ocr python=3.9.23 -y
conda activate table_ocr
```

或使用 venv：

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

需要 GPU 加速时，把 CPU 版飞桨换成 GPU 版（CUDA 11.8 示例）：

```bash
pip uninstall paddlepaddle
pip install paddlepaddle-gpu==2.6.2.post118 -f https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html
```

然后把 `config/model_config.py` 里的 `is_use_gpu` 改为 `True`。

### 3. 启动服务

```bash
python -u web.py
```

后台运行可使用项目自带脚本：

```bash
sh start.sh        # 启动
sh shutdown.sh     # 停止
```

服务默认监听 `0.0.0.0:8111`。

调试模式默认开启，生产环境建议关闭：

```bash
TABLE_OCR_DEBUG=0 python -u web.py
```

### 4. 验证

浏览器打开 <http://localhost:8111/index>，上传 `io/input_path/result` 下的测试图片即可看到识别结果。

---

## 接口文档

端口在 `config/web_config.py` 中修改，默认 `8111`。

### 统一响应格式

成功：

```json
{
    "msg": "操作成功",
    "splicing_data": {},
    "code": 200
}
```

失败：

```json
{
    "msg": "错误原因",
    "code": 500
}
```

---

### 1. POST /process/common

整图文字识别，不做切格。

请求（`application/json`）：

```json
{
    "image": "base64 字符串",
    "name": "0002",
    "suffix": ".jpg"
}
```

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| image | 是 | 图片 base64 编码 |
| name | 是 | 图片名称 |
| suffix | 是 | 图片后缀，必须以 `.` 开头，如 `.jpg` / `.png` |

响应：

```json
[{
    "coordinates": [[]],
    "txt_result": "识别文本",
    "name": "0002",
    "txt_rate": "置信度",
    "uuid": "存储位置 id"
}]
```

---

### 2. POST /process/all

表格切分 + 逐格独立识别。

请求参数与 `/process/common` 相同。

响应：

```json
[{
    "bbox": [[]],
    "result": [[{
        "coordinates": [[]],
        "txt_result": "识别文本",
        "name": "图片名称",
        "txt_rate": "置信度",
        "uuid": "存储位置 id"
    }]],
    "name": "0002",
    "suffix": "head / coordinate / end，分别表示表头、中间表格、表尾",
    "uuid": "存储位置 id"
}]
```

---

### 3. POST /process/res

工作票结构化提取。**仅对电力工作票有效**，其他表格无效。

请求参数与 `/process/common` 相同。

响应：

```json
{
    "msg": "操作成功",
    "splicing_data": {
        "img_name": "0002.jpg",
        "uuid": "74afd5a2",
        "table_head": "附页",
        "table_type": "表头",
        "table_body": {
            "head": {
                "guardian": null,
                "telephone": null,
                "dept": null,
                "duty_number": null,
                "start_time": null,
                "end_time": null,
                "number": null,
                "head": "附页"
            },
            "body": {
                "work_task": [],
                "measure_main": null,
                "measure_other": [],
                "other": [],
                "all": null,
                "responsible": null
            }
        }
    },
    "code": 200
}
```

字段含义：

| 分组 | 字段 | 类型 | 含义 |
| --- | --- | --- | --- |
| head | guardian | String | 监护人 |
| head | telephone | String | 电话 |
| head | dept | String | 单位与班组 |
| head | duty_number | String | 人数 |
| head | start_time | String | 开始时间 |
| head | end_time | String | 结束时间 |
| head | number | String | 编号 |
| body | work_task | List | 工作任务 |
| body | measure_main | List | 工作要求的安全措施 |
| body | measure_other | List | 其他安全措施和注意事项 |
| body | other | List | 安全措施之前的内容（多用于附页） |
| body | responsible | List | 调度或单位负责的安全措施 |

---

### 4. POST /process/vidImg

图片 / 视频通用识别。

请求：`multipart/form-data`，字段名 `file`。

| 上传类型 | 处理方式 |
| --- | --- |
| 图片 | 直接识别 |
| 视频 | 自动抽帧后逐帧识别 |

响应：

```json
{
    "msg": "操作成功",
    "splicing_data": [],
    "code": 200
}
```

---

### 测试页面

| 路径 | 说明 |
| --- | --- |
| GET /index | 上传测试页 |
| GET /vidImg | 图片 / 视频上传测试页（模板文件 `templates/vidImg.html` 当前缺失） |

---

## 配置说明

全部配置位于 `config/` 目录，均为静态类属性，改完重启生效。

| 文件 | 类 | 用途 |
| --- | --- | --- |
| `config/web_config.py` | `WebConfig` | 服务端口 |
| `config/model_config.py` | `ModelConfig` | 模型路径、是否 GPU、识别语言 |
| `config/cv_config.py` | `CVConfig` | 像素容差、最小格面积、压缩目标大小、调试图文件名 |
| `config/file_config.py` | `FileConfig` | 存储目录名、中间图文件名、是否保留源图 |
| `config/thread_config.py` | `ThreadConfig` | 线程池参数 |

常用项：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `WebConfig.port` | `8111` | 服务端口 |
| `ModelConfig.is_use_gpu` | `False` | 装了 GPU 版飞桨才改成 `True` |
| `FileConfig.is_delete_file` | `False` | 请求结束后是否删除本次 uuid 目录，线上建议改 `True` |
| `CVConfig.pixel_fault_tolerance` | `8` | 表格线合并容差（像素），切格串行时可适当调小 |
| `CVConfig.min_size` | `2500` | 小于该面积的格子会被当作噪声丢弃 |
| `CVConfig.cv_compress` | `1.3 MB` | 图片压缩目标大小 |

---

## 切图命名规则

切图文件名本身就是坐标系：

```
y_yh_x_xw_序号_suffix.jpg
```

| 片段 | 含义 |
| --- | --- |
| `y` / `yh` | 格子上下边界的纵坐标 |
| `x` / `xw` | 格子左右边界的横坐标 |
| `序号` | 切图顺序 |
| `suffix` | `head` 表头 / `coordinate` 中间表格 / `end` 表尾 |

规则层直接解析文件名还原每个格子的几何位置，再按坐标做相邻格推理，把散落的识别结果拼装成结构化 JSON。理解这一点是读懂 `rules/` 的关键。

---

## 已知限制

- **不支持一图多页**，也不支持一张图里多个不连续的表格。
- **表格线必须相对完整**。断线会导致相邻格子连成一片，进而串格；拍摄时尽量保证表格清晰、平整、光线均匀。
- **倾斜可以矫正，曲面畸变不能**。整体拍歪（平面内旋转）由霍夫直线矫正处理；纸张弯曲、卷边、褶皱属于非刚性形变，OpenCV 无法处理，需要引入文档矫形模型。
- **`/vidImg` 测试页模板缺失**，访问会报模板找不到，接口本身可用。
- 每个请求会在 `io/save_path/` 下生成一个 uuid 目录，默认不清理，长期运行需关注磁盘占用（改 `FileConfig.is_delete_file = True`）。

---

## 常见问题

**1. 报 protobuf 版本不兼容**

```bash
pip install protobuf==3.20.2
```

**2. 报 numpy 相关错误**

飞桨 2.x 不支持 numpy 2.x，确认版本：

```bash
pip install "numpy<2"
```

**3. Linux 下报动态链接库错误**

```bash
conda install nomkl
```

**4. 模型加载失败**

仓库 `model/` 目录已内置 PP-OCRv4 的检测、识别与方向分类模型，路径配置在 `config/model_config.py`。若提示模型不存在，检查启动目录是否为项目根目录——模型路径是相对当前工作目录解析的。

**5. 服务启动后访问接口就很慢**

首次识别需要加载模型，属正常现象。生产环境建议关闭调试模式并保持服务常驻。

**6. 切格结果串行或缺失**

优先检查原图表格线是否清晰。可调小 `CVConfig.pixel_fault_tolerance` 让相邻表格线不再被合并，或调大 `CVConfig.min_size` 过滤掉噪声格。

---

## 依赖说明

完整清单见 `requirements.txt`，核心依赖：

| 依赖 | 版本 | 作用 |
| --- | --- | --- |
| paddlepaddle | 2.6.2 | 推理框架 |
| paddleocr | 2.7.3 | OCR 能力封装 |
| opencv-python | 4.6.0.66 | 图像处理与切格 |
| opencv-contrib-python | 4.6.0.66 | 扩展图像处理 |
| opencv-python-headless | 4.8.0.74 | 无图形界面环境支持 |
| numpy | 1.26.4 | 数值计算 |
| Flask | 3.1.3 | Web 服务 |
| urllib3 | 2.5.0 | HTTP 客户端 |
| Pillow | 10.4.0 | 图像读写 |

`opencv-python`、`opencv-contrib-python`、`opencv-python-headless` 三个包都提供 `cv2` 模块，会互相覆盖，最终生效的版本取决于安装顺序。`requirements.txt` 中的顺序即验证过的可用顺序，不要随意调整。

`Werkzeug` 由 Flask 3.1.3 自动解析（要求 >= 3.1），未单独锁定。

`opencv_controller_img.py` 与 `paddleocr_test.py` 是两个独立调试脚本，不在服务链路上，运行它们需要额外安装 `matplotlib`：

```bash
pip install matplotlib -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## License

本项目仅供学习与内部使用。
