# Table OCR · 表格与工作票结构化识别服务 (Table & Ticket OCR Service)

基于 **Flask + PaddleOCR + OpenCV** 的表格与工作票结构化识别服务。
支持倾斜矫正、形态学切格、逐格 OCR 识别及规则匹配，出来的是可直接落库的结构化 JSON。

![Python](https://img.shields.io/badge/Python-3.9.23-3776AB?logo=python&logoColor=white)
![PaddleOCR](https://img.shields.io/badge/PaddleOCR-2.7.3-00B4D8)
![OpenCV](https://img.shields.io/badge/OpenCV-4.6-5C3EE8?logo=opencv&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1.3-000000?logo=flask&logoColor=white)

> **文档导航**
> 本文是入门入口，只覆盖安装启动与整体认知。
> 接口参数、响应字段、全量配置、产物目录与排障手册一律见 **[docs/API.md](docs/API.md)**。

---

## 核心特性：表格切分、OCR识别与结构化提取 (Key Features)

| 能力 (Capability) | 说明 (Description) |
| --- | --- |
| 通用文字识别 (General OCR) | 整图 OCR，返回文本框坐标、识别文本与置信度 |
| 表格切分 (Table Extraction) | 形态学提取横竖表格线，定位单元格并逐格切图 |
| 逐格识别 (Cell-by-cell OCR) | 每个格子单独放大 + 锐化后识别，避免整图识别的串行错乱 |
| 工作票结构化 (Structured Parsing)| 按票种规则抽取表头与正文字段，输出结构化 JSON |
| 图片/视频通用 (Image/Video OCR) | 图片直接识别；视频自动抽帧后逐帧识别并去重 |
| 倾斜矫正 (Skew Correction) | 霍夫直线检测整体倾角并反向旋转，拍歪的表格也能正常切格 |

处理链路：

```
上传 → 落盘 → 压缩 → 倾斜矫正 → 二值化 → 提取表格线
     → 定位单元格 → 逐格切图 → 逐格 OCR → 规则匹配 → 结构化 JSON
```

---

## 效果展示

原图 vs 按坐标还原后的 23 个格子（验证切格精度）：

![compare](https://9774b64ab3064c8088fb9293d5a96af2.app.workbuddy.link/compare.jpg)

23 个切图网格铺开（看每个格子的内容）：

![cells](https://9774b64ab3064c8088fb9293d5a96af2.app.workbuddy.link/cells.jpg)

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
├── docs        # 详细文档
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

conda：

```bash
conda create -n table_ocr python=3.9.23 -y
conda activate table_ocr
```

venv：

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

后台运行可用项目自带脚本：`sh start.sh` 启动，`sh shutdown.sh` 停止。

服务默认监听 `0.0.0.0:8111`。调试模式默认开启，生产环境建议关闭：

```bash
TABLE_OCR_DEBUG=0 python -u web.py
```

### 4. 验证

浏览器打开 <http://localhost:8111/index>，上传 `io/input_path/result` 下的测试图片即可看到识别结果。

---

## 接口总览

端口在 `config/web_config.py` 中修改，默认 `8111`。

| 方法 | 路径 | 用途 | 入参 |
| --- | --- | --- | --- |
| POST | `/process/common` | 整图文字识别，不切格 | JSON |
| POST | `/process/all` | 表格切分 + 逐格独立识别 | JSON |
| POST | `/process/res` | 工作票结构化提取（**仅电力工作票有效**） | JSON |
| POST | `/process/vidImg` | 图片 / 视频通用识别 | `multipart/form-data`，字段名 `file` |
| GET | `/index` | 上传测试页 | — |
| GET | `/vidImg` | 图片 / 视频上传测试页（模板缺失） | — |

三个 JSON 接口的入参一致：

```json
{"image": "图片 base64", "name": "0002", "suffix": ".jpg"}
```

所有接口共用同一层响应信封，业务数据放在 `splicing_data`：

```json
{"msg": "操作成功", "splicing_data": {}, "code": 200}
```

失败时 `splicing_data` 不存在，原因在 `msg` 里，HTTP 状态码为 500。

完整的参数说明、调用示例（curl / Python）、响应字段表见 [docs/API.md](docs/API.md#二接口详解)。

---

## 常用配置

配置位于 `config/`，都是静态类属性，**改完重启生效**。这里只列最常改的三项：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `WebConfig.port` | `8111` | 服务端口 |
| `ModelConfig.is_use_gpu` | `False` | 装了 GPU 版飞桨才改成 `True` |
| `FileConfig.is_delete_file` | `False` | 请求结束后是否删除 uuid 目录，**长期运行建议改 `True`** |

切格效果不佳时再动这两个：`CVConfig.pixel_fault_tolerance`（表格线合并容差，默认 8）、`CVConfig.min_size`（最小格面积，默认 2500）。

五份配置类的全量参数表见 [docs/API.md](docs/API.md#五配置参考)。

---

## 切图产物

每次请求在 `io/save_path/{uuid}/` 下生成全部产物，业务要的格子图在 `coord/` 子目录。

文件名本身就是坐标系：

```
y_yh_x_xw_序号_suffix.jpg      例：300_360_172_886_3_coordinate.jpg
```

`y` / `yh` 是格子上下边界，`x` / `xw` 是左右边界，`suffix` 取 `head`（表头）/ `coordinate`（中间表格）/ `end`（表尾）。

规则层直接解析文件名还原几何，按坐标做相邻格推理，把散落的识别结果拼装成 JSON——理解这一点是读懂 `rules/` 的关键。

完整产物目录结构见 [docs/API.md](docs/API.md#四切图产物与命名规则)。

---

## 已知限制

- **不支持一图多页**，也不支持一张图里多个不连续的表格。
- **表格线必须相对完整**。断线会导致相邻格子连成一片，进而串格；拍摄时尽量保证表格清晰、平整、光线均匀。
- **倾斜可以矫正，曲面畸变不能**。整体拍歪（平面内旋转）由霍夫直线矫正处理；纸张弯曲、卷边、褶皱属于非刚性形变，OpenCV 无法处理，需要引入文档矫形模型。
- **`/vidImg` 测试页模板缺失**，访问会报模板找不到，接口本身可用。
- 每个请求生成的 uuid 目录默认不清理，长期运行需关注磁盘占用。

---

## 常见问题

**protobuf 版本不兼容** — `pip install protobuf==3.20.2`

**numpy 相关报错** — 飞桨 2.x 不支持 numpy 2.x，确认 `pip install "numpy<2"`

**模型加载失败** — 必须在项目根目录启动，模型路径相对当前工作目录解析

更多排障条目（切格串行、字段抽不到、中文路径失败等）见 [docs/API.md](docs/API.md#七排障手册)。

---

## 依赖

完整清单见 `requirements.txt`。

`opencv-python` / `opencv-contrib-python` / `opencv-python-headless` 三个包都提供 `cv2` 模块，会互相覆盖，最终生效版本取决于安装顺序——`requirements.txt` 中的顺序即验证过的可用顺序，不要调整。

根级 `opencv_controller_img.py` 与 `paddleocr_test.py` 是独立调试脚本，不在服务链路上，运行需要额外装 `matplotlib`。

---

## License

本项目仅供学习与内部使用。
