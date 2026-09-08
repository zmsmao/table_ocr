# Table OCR · 表格与工作票识别服务

基于 **Flask + PaddleOCR + OpenCV** 的表格 / 工作票结构化识别服务。
一张照片进去，经过矫正、切格、逐格 OCR、规则匹配，出来的是可直接落库的结构化 JSON。

![Python](https://img.shields.io/badge/Python-3.9.23-3776AB?logo=python&logoColor=white)
![PaddleOCR](https://img.shields.io/badge/PaddleOCR-2.7.3-00B4D8)
![OpenCV](https://img.shields.io/badge/OpenCV-4.6-5C3EE8?logo=opencv&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1.3-000000?logo=flask&logoColor=white)

---

## 效果展示

原图 vs 按坐标还原后的 23 个格子（验证切格精度）：

![compare](https://9774b64ab3064c8088fb9293d5a96af2.app.workbuddy.link/compare.jpg)

23 个切图网格铺开（看每个格子的内容）：

![cells](https://9774b64ab3064c8088fb9293d5a96af2.app.workbuddy.link/cells.jpg)

处理链路：

```
上传 → 落盘 → 压缩 → 倾斜矫正 → 二值化 → 提取表格线
     → 定位单元格 → 逐格切图 → 逐格 OCR → 规则匹配 → 结构化 JSON
```

---

## 目录结构

```
table_ocr
├── adapter     # 票种路由分发
├── cache       # 临时图片缓存
├── config      # 路径 / 模型 / 算法参数 / 端口
├── domain      # 请求与响应实体
├── io          # 图片主存储目录，每次请求一个 uuid 子目录
├── model       # OCR 推理模型（PP-OCRv4）
├── normal      # 字段规则备忘
├── rules       # 规则匹配（按票种拆分）
│   └── common  # 通用几何与表头解析
├── service     # 业务编排
├── templates   # 测试页模板
├── utils       # 工具类
├── web.py      # 服务入口
└── requirements.txt
```

---

## 快速开始

| 项目 | 版本 |
| --- | --- |
| Python | 3.9.23 |
| 磁盘 | 模型与缓存约 1 GB |

```bash
conda create -n table_ocr python=3.9.23 -y
conda activate table_ocr
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python -u web.py
```

GPU 版本需把 `paddlepaddle` 换成 `paddlepaddle-gpu`，并把 `config/model_config.py` 里的 `is_use_gpu` 改为 `True`。

服务默认监听 `0.0.0.0:8111`。调试模式默认开启，生产环境 `TABLE_OCR_DEBUG=0 python -u web.py` 关闭。

打开 <http://localhost:8111/index> 上传 `io/input_path/result` 下的测试图片即可看到识别结果。

---

## 接口文档

端口在 `config/web_config.py` 中修改，默认 `8111`。

**统一响应格式**

成功：`{msg: "操作成功", splicing_data: {}, code: 200}`
失败：`{msg: "错误原因", code: 500}`

### POST /process/common

整图 OCR，不切格。

```json
{"image": "base64 字符串", "name": "0002", "suffix": ".jpg"}
```

返回 `[{"coordinates":[[]], "txt_result":"...", "name":"...", "txt_rate":"...", "uuid":"..."}]`。

### POST /process/all

表格切分 + 逐格独立识别，参数同上。

返回每个切格的位置与识别结果，`suffix` 取值 `head` / `coordinate` / `end`。

### POST /process/res

**仅对电力工作票有效**。参数同上。

返回结构化 JSON，`splicing_data.table_body` 包含 `head`（监护人 / 电话 / 单位班组 / 人数 / 起止时间 / 编号）与 `body`（工作任务 / 安全措施 / 其他安全措施等）。

### POST /process/vidImg

图片 / 视频通用识别。`multipart/form-data` 上传，字段名 `file`。视频自动抽帧后逐帧识别。

### 测试页面

| 路径 | 说明 |
| --- | --- |
| GET /index | 上传测试页 |
| GET /vidImg | 图片 / 视频上传测试页（模板文件缺失） |

---

## 配置说明

全部配置位于 `config/`，均为静态类属性，改完重启生效。

| 类 | 常用项 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `WebConfig` | port | `8111` | 服务端口 |
| `ModelConfig` | is_use_gpu | `False` | GPU 版才改成 `True` |
| `FileConfig` | is_delete_file | `False` | 请求结束是否删除 uuid 目录，线上建议改 `True` |
| `CVConfig` | pixel_fault_tolerance | `8` | 表格线合并容差（像素） |
| `CVConfig` | min_size | `2500` | 小于该面积的格子当作噪声丢弃 |
| `CVConfig` | cv_compress | `1.3 MB` | 图片压缩目标大小 |

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

规则层直接解析文件名还原几何，按坐标做相邻格推理，把散落的识别结果拼装成 JSON。理解这一点是读懂 `rules/` 的关键。

---

## 已知限制

- 不支持一图多页，不支持一张图里多个不连续表格。
- 表格线必须相对完整。断线会导致相邻格子连成一片。
- 倾斜（平面内旋转）可以矫正；纸张弯曲、卷边、褶皱这类非刚性形变无法处理，需引入文档矫形模型。
- `/vidImg` 测试页模板缺失。
- `io/save_path/{uuid}` 默认不清理，长期运行需关注磁盘。

---

## 常见问题

**protobuf 版本不兼容**：`pip install protobuf==3.20.2`

**numpy 相关错误**：飞桨 2.x 不支持 numpy 2.x，确认 `pip install "numpy<2"`

**模型加载失败**：检查启动目录是否为项目根，模型路径相对于工作目录解析。

---

## 依赖

完整清单见 `requirements.txt`。`opencv-python` / `opencv-contrib-python` / `opencv-python-headless` 三个包都提供 `cv2` 模块，安装顺序不可调整；`Werkzeug` 由 Flask 3.1.3 自动解析。根级 `opencv_controller_img.py` 与 `paddleocr_test.py` 是独立调试脚本，需要额外安装 `matplotlib`。