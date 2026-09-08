# Table OCR · 接口与配置详解

> 本文是 [README.md](../README.md) 的配套详版，覆盖**全部接口、响应字段、配置项、产物目录与排障手册**。
> 首次使用请先按 README 完成环境搭建与服务启动，再回到本文查阅接口细节。

![Python](https://img.shields.io/badge/Python-3.9.23-3776AB?logo=python&logoColor=white)
![PaddleOCR](https://img.shields.io/badge/PaddleOCR-2.7.3-00B4D8)
![OpenCV](https://img.shields.io/badge/OpenCV-4.6-5C3EE8?logo=opencv&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1.3-000000?logo=flask&logoColor=white)
![Docs](https://img.shields.io/badge/Docs-接口与配置-4B8BBE?logo=readthedocs&logoColor=white)

---

## 目录

- [一、通用约定](#一通用约定)
  - [1.1 服务地址与限制](#11-服务地址与限制)
  - [1.2 统一响应信封](#12-统一响应信封)
  - [1.3 错误响应](#13-错误响应)
  - [1.4 并发与超时](#14-并发与超时)
- [二、接口详解](#二接口详解)
  - [2.1 POST /process/common — 整图文字识别](#21-post-processcommon--整图文字识别)
  - [2.2 POST /process/all — 表格切分 + 逐格识别](#22-post-processall--表格切分--逐格识别)
  - [2.3 POST /process/res — 工作票结构化提取](#23-post-processres--工作票结构化提取)
  - [2.4 POST /process/vidImg — 图片 / 视频通用识别](#24-post-processvidimg--图片--视频通用识别)
  - [2.5 测试页面](#25-测试页面)
- [三、工作票字段参考](#三工作票字段参考)
- [四、切图产物与命名规则](#四切图产物与命名规则)
- [五、配置参考](#五配置参考)
- [六、处理链路与中间产物](#六处理链路与中间产物)
- [七、排障手册](#七排障手册)

---

## 一、通用约定

### 1.1 服务地址与限制

| 项目 | 值 | 备注 |
| --- | --- | --- |
| 默认地址 | `http://localhost:8111` | 端口改 `config/web_config.py` 的 `WebConfig.port` |
| 监听网卡 | `0.0.0.0` | 局域网内其他机器可直接访问 |
| 单请求体上限 | 16 MB | `web.py` 的 `MAX_CONTENT_LENGTH`，超出返回 413 |
| 请求编码 | UTF-8 | 响应头 `application/json; charset=utf-8`，中文不做 ASCII 转义 |
| 鉴权 | 无 | 本项目定位为内网开箱即用服务，未内置鉴权，请勿直接暴露公网 |

四个业务接口均为 `POST`，其中三个接收 JSON（图片以 base64 传入），一个接收 `multipart/form-data` 文件上传。

### 1.2 统一响应信封

所有接口都套同一层信封，业务数据放在 `splicing_data` 里：

```json
{
    "msg": "操作成功",
    "splicing_data": {},
    "code": 200
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `msg` | String | 固定为 `操作成功`，失败时为错误原因 |
| `splicing_data` | Any | 业务数据，类型随接口而定：对象、数组或字符串数组 |
| `code` | int | 固定为 `200`，失败时为 `500` |

HTTP 状态码与信封里的 `code` 保持一致：成功 200，失败 500。

### 1.3 错误响应

失败时 `splicing_data` 字段**不存在**，错误原因放在 `msg`：

```json
{
    "msg": "Traceback (most recent call last):\n  ...",
    "code": 500
}
```

**注意**：当前实现把完整的 Python 异常堆栈写入 `msg`。排查问题时很方便，但也意味着内部路径与代码结构会暴露给调用方。**对外开放前建议改成固定文案，把堆栈只写日志。**

常见触发原因：

| 现象 | 原因 |
| --- | --- |
| `请求体必须为 json，且包含 image 字段` | 未传 `image`，或 `Content-Type` 不是 `application/json` |
| `suffix 非法，应为 .jpg / .png 这样的图片后缀` | `suffix` 不以 `.` 开头，或含 `/` `\` `..` |
| `没有选择文件` / `文件名不能为空` | `/process/vidImg` 未传 `file` 字段 |
| `不支持的文件类型,仅支持图片和视频` | 扩展名不在支持列表内，见 [2.4](#24-post-processvidimg--图片--视频通用识别) |
| `无法读取图像文件: ...` | base64 解出的内容不是有效图片，或路径含非 ASCII 字符 |

### 1.4 并发与超时

服务启动时不会预加载模型，第一个请求会触发模型加载，耗时数秒到数十秒不等，属正常现象。

识别任务跑在独立的进程池里（最多 5 个并行），池在首个请求到达时创建，每个子进程通过 `init_worker_engine` 预加载一份 PaddleOCR 模型，之后复用。超出 5 个的请求会在池中排队，不会无限创建进程。

这么设计的原因：PaddleOCR 单次推理占用内存较大，放到子进程里，任务结束后内存可完整归还系统；而模型只在子进程初始化时加载一次，避免每请求重复加载。

请求本身是同步阻塞的（提交到池后立即等待结果），客户端需要设置足够的超时时间，建议 120 秒以上。

---

## 二、接口详解

### 2.1 POST /process/common — 整图文字识别

对整张图做一次 OCR，不做切格，适合纯文本段落或只想拿到全文的场景。

**请求**

```
POST /process/common
Content-Type: application/json
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `image` | String | 是 | 图片内容的 base64 编码（不含 `data:image/...;base64,` 前缀） |
| `name` | String | 是 | 图片名称，会作为落盘文件名的主体部分 |
| `suffix` | String | 是 | 图片后缀，必须以 `.` 开头，如 `.jpg` / `.png` |

```json
{
    "image": "iVBORw0KGgoAAAANSUhEUgAA...",
    "name": "0002",
    "suffix": ".jpg"
}
```

`suffix` 会直接参与文件路径拼接，因此做了白名单式校验：必须以 `.` 开头，且不能包含 `/`、`\`、`..`。传入 `../../evil` 这类值会被直接拒绝。

**调用示例**

```bash
curl -X POST http://localhost:8111/process/common \
  -H "Content-Type: application/json" \
  -d "{\"image\":\"$(base64 -w 0 0002.jpg)\",\"name\":\"0002\",\"suffix\":\".jpg\"}"
```

```python
import base64
import requests

with open('0002.jpg', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')

resp = requests.post(
    'http://localhost:8111/process/common',
    json={'image': b64, 'name': '0002', 'suffix': '.jpg'},
    timeout=120,
).json()

for item in resp['splicing_data']:
    print(item)
```

**响应**

`splicing_data` 为数组，每个元素对应一个识别出的文本行：

```json
{
    "msg": "操作成功",
    "splicing_data": [
        {
            "coordinates": [[12, 30], [240, 28], [241, 58], [13, 60]],
            "txt_result": "工作票",
            "name": "0002",
            "txt_rate": 0.9871,
            "uuid": "74afd5a2"
        }
    ],
    "code": 200
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `coordinates` | Array | 文本框四角坐标，顺序为 左上 → 右上 → 右下 → 左下 |
| `txt_result` | String | 识别出的文本 |
| `name` | String | 请求时传入的图片名称 |
| `txt_rate` | Float | 置信度，0 ~ 1，越高越可信 |
| `uuid` | String | 本次请求的目录 id，产物在 `io/save_path/{uuid}` |

> **实现说明**：当前 `service/base_service.py` 的 `common()` 直接返回 PaddleOCR 引擎的原始输出，未走统一的实体封装，因此实际返回结构与上面的定义存在出入（详见 [七、排障手册](#七排障手册) 第 7 条）。调用时建议先打印一次实际响应再写解析逻辑。

---

### 2.2 POST /process/all — 表格切分 + 逐格识别

先定位表格区域并切成若干小格，再对每个格子单独识别。相比整图识别，逐格识别能避免多行文本串在一起导致的错乱。

**请求**

```
POST /process/all
Content-Type: application/json
```

请求参数与 [2.1](#21-post-processcommon--整图文字识别) 完全一致（`image` / `name` / `suffix`）。

**调用示例**

```bash
curl -X POST http://localhost:8111/process/all \
  -H "Content-Type: application/json" \
  -d "{\"image\":\"$(base64 -w 0 0002.jpg)\",\"name\":\"0002\",\"suffix\":\".jpg\"}"
```

**响应**

`splicing_data` 为数组，每个元素对应一个切出的格子：

```json
{
    "msg": "操作成功",
    "splicing_data": [
        {
            "_bbox": [[172, 300], [172, 360], [886, 300], [886, 360]],
            "_name": "0002.jpg",
            "_result": [
                {
                    "_coordinates": [[8, 6], [96, 6], [96, 30], [8, 30]],
                    "_txt_result": "工作任务",
                    "_name": "0002.jpg",
                    "_txt_rate": 0.9932,
                    "_uuid": "74afd5a2"
                }
            ],
            "_suffix": "coordinate",
            "_bbox_path": "io/save_path/74afd5a2/coord/300_360_172_886_3_coordinate"
        }
    ],
    "code": 200
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `_bbox` | Array | 该格子在**裁剪后表格图**中的四角坐标，与文件名里的 `y_yh_x_xw` 对应 |
| `_result` | Array | 该格子内识别出的所有文本行，字段同 [2.1](#21-post-processcommon--整图文字识别) |
| `_name` | String | 图片名称 |
| `_suffix` | String | 格子类型：`head` 表头 / `coordinate` 中间表格 / `end` 表尾 |
| `_bbox_path` | String | 该格子切图文件的相对路径（不含扩展名） |

> **为什么字段名带下划线前缀**：实体类 `OCRAll` 声明的字段是 `bbox` / `result` / `suffix` / `bbox_path` / `name`，但装配时写入的是带 `_` 前缀的同名属性，两者并存于返回字典中——不带前缀的那组恒为 `null`，有效数据在带前缀的那组。这是历史遗留，属于待修项，改之前请保持按带前缀的字段解析。

---

### 2.3 POST /process/res — 工作票结构化提取

**本接口只对电力工作票有效**，其他版式的表格走规则匹配不会有正确结果。

它在 [2.2](#22-post-processall--表格切分--逐格识别) 的基础上多做一步：把逐格识别出的文本按票种规则归位到具体业务字段。

**请求**

```
POST /process/res
Content-Type: application/json
```

请求参数与 [2.1](#21-post-processcommon--整图文字识别) 完全一致（`image` / `name` / `suffix`）。

**调用示例**

```python
import base64
import requests

with open('0002.jpg', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')

resp = requests.post(
    'http://localhost:8111/process/res',
    json={'image': b64, 'name': '0002', 'suffix': '.jpg'},
    timeout=180,
).json()

data = resp['splicing_data']
print(data['table_head'], data['table_type'])
print(data['table_body']['head'])
print(data['table_body']['body'])
```

**响应**

```json
{
    "msg": "操作成功",
    "splicing_data": {
        "img_name": "0002.jpg",
        "uuid_path": "io/save_path/74afd5a2",
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
                "responsible": null,
                "other": [],
                "all": null
            }
        }
    },
    "code": 200
}
```

顶层字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `img_name` | String | 图片名称（含后缀） |
| `uuid_path` | String | 本次请求产物目录，`io/save_path/{uuid}` |
| `table_head` | String | 表头标识，当前规则只能区分「工作票」与「附页」 |
| `table_type` | String | 票种类型，由关键字匹配得出 |
| `table_body.head` | Object | 表头字段，全部为 String，抽不到时为 `null` |
| `table_body.body` | Object | 正文字段，多为 List\<String\>，抽不到时为 `null` 或 `[]` |

字段完整含义见 [三、工作票字段参考](#三工作票字段参考)。

---

### 2.4 POST /process/vidImg — 图片 / 视频通用识别

按上传文件的扩展名自动分流：图片直接识别，视频抽帧后逐帧识别并去重。

**请求**

```
POST /process/vidImg
Content-Type: multipart/form-data
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file` | File | 是 | 图片或视频文件，表单字段名必须为 `file` |

支持的扩展名（不区分大小写）：

| 类型 | 扩展名 |
| --- | --- |
| 图片 | `png` `jpg` `jpeg` `gif` `bmp` `svg` `webp` `tiff` `ico` `jfif` `pjpeg` `pjp` `heic` `bpg` `raw` `exif` |
| 视频 | `mp4` `avi` `mkv` `mov` `wmv` `flv` `mpeg` `3gp` `m4v` `divx` `vob` `ogv` `ogg` `swf` `asf` `rm` `rmvb` `m2ts` `mts` `ts` `webm` `mpg` `mp2` `mpe` `mpv` `m2v` `m4p` `m4b` `m4r` `m4a` `aac` `flac` `wav` `opus` |

**调用示例**

```bash
curl -X POST http://localhost:8111/process/vidImg \
  -F "file=@0002.jpg"
```

```python
import requests

with open('0002.jpg', 'rb') as f:
    resp = requests.post(
        'http://localhost:8111/process/vidImg',
        files={'file': f},
        timeout=180,
    ).json()

print(resp['splicing_data'])
```

**响应**

`splicing_data` 为字符串数组：

| 上传类型 | 数组内容 |
| --- | --- |
| 图片 | 每个元素为识别出的**一行文本**（按文本框顺序） |
| 视频 | 每个元素为**一帧的完整文本拼接**，已按相邻帧做重复过滤 |

```json
{
    "msg": "操作成功",
    "splicing_data": [
        "工作票",
        "编号:20240611001",
        "工作任务:更换10kV线路开关"
    ],
    "code": 200
}
```

若视频中未识别到任何有效文本，返回空数组 `[]`。

---

### 2.5 测试页面

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/index` | 上传测试页，走 `/process/all` |
| GET | `/vidImg` | 图片 / 视频上传测试页，走 `/process/vidImg` |

> `/vidImg` 页面依赖 `templates/vidImg.html`，当前仓库未提供该模板，访问会报模板找不到。**接口本身正常可用**，用上面的 curl / Python 示例调用即可。

---

## 三、工作票字段参考

`/process/res` 返回的两组字段完整含义如下。

### 表头 `table_body.head`

全部为 String 类型，未抽取到时为 `null`。

| 字段 | 中文含义 | 说明 |
| --- | --- | --- |
| `guardian` | 监护人 | 工作票监护人姓名 |
| `telephone` | 电话 | 联系电话 |
| `dept` | 单位与班组 | 工作单位及班组名称 |
| `duty_number` | 人数 | 工作班人员数量 |
| `start_time` | 开始时间 | 计划工作开始时间 |
| `end_time` | 结束时间 | 计划工作结束时间 |
| `number` | 编号 | 工作票编号 |
| `head` | 表头标识 | 取值为「工作票」或「附页」 |

### 正文 `table_body.body`

多为 List\<String\> 类型，未抽取到时为 `null` 或 `[]`。

| 字段 | 中文含义 | 说明 |
| --- | --- | --- |
| `work_task` | 工作任务 | 本次作业的具体内容 |
| `measure_main` | 工作要求的安全措施 | 主表「工作要求的安全措施」栏内容 |
| `measure_other` | 其他安全措施和注意事项 | 多用于附页 |
| `responsible` | 调度或单位负责的安全措施 | 由「调度 / 措施」等关键字定位 |
| `other` | 安全措施之前的内容 | 尚未抽取到安全措施栏之前的内容，多用于附页 |
| `all` | 兜底全量 | 预留字段，当前一般为 `null` |

字段抽取依赖关键字匹配（如「工作任务」「工作要求的安全措」「其他安全措施和注意事项」），OCR 漏字会导致整段失配。排查时先用 [2.2](#22-post-processall--表格切分--逐格识别) 看格子里的原始文本是否识别正确。

---

## 四、切图产物与命名规则

### 4.1 产物目录

每个请求生成一个 10 位 uuid 目录，全部产物都在里面：

```
io/save_path/{uuid}
├──  accept_cv.jpg          # 原始接收图（文件名前缀含一个空格，配置如此）
├── compress_cv.jpg         # 压缩后
├── rotate_cv.jpg           # 倾斜矫正后
├── transform_cv.jpg        # 透视变换后
├── intelligence_cv.jpg     # 智能定位裁剪出的主表区域
├── cv.jpg                  # 灰度 / 二值化中间图
├── main/                   # 正文区域图
├── other/                  # cvX.jpg / cvY.jpg / cv_point.jpg / cv_table.jpg 等调试图
├── coord/                  # ★ 切出的格子图，业务真正要的东西
├── frame/                  # 视频抽帧结果
└── split/                  # 二次切分（按需）
```

> `accept_cv.jpg` 的文件名前缀确实带一个空格，来自 `FileConfig.cv_accept_name = ' accept_cv'`。这是历史遗留，脚本里若按文件名精确匹配需要注意。

`coord/` 是关键产物——表格被切成的小格子，每格一个 jpg。`rules/` 下的逻辑就是读这个目录，靠文件名还原几何关系。

### 4.2 命名规则

```
y_yh_x_xw_序号_suffix.jpg
```

示例：`300_360_172_886_3_coordinate.jpg`

| 片段 | 值 | 含义 |
| --- | --- | --- |
| `y` | `300` | 格子上边界纵坐标 |
| `yh` | `360` | 格子下边界纵坐标 |
| `x` | `172` | 格子左边界横坐标 |
| `xw` | `886` | 格子右边界横坐标 |
| `序号` | `3` | 切图顺序 |
| `suffix` | `coordinate` | 格子类型 |

`suffix` 取值：

| 取值 | 含义 |
| --- | --- |
| `head` | 表头区域（签发栏等） |
| `coordinate` | 中间表格的普通格子 |
| `end` | 表尾区域 |

**设计要点：文件名本身就是坐标系。** 规则层不需要额外数据结构，直接把文件名按下划线切开就能还原每个格子的位置，再按坐标做相邻格推理，把散落的识别结果拼装成结构化 JSON。理解这一点是读懂 `rules/` 的关键。

注意坐标是相对**裁剪后的主表图**（`intelligence_cv.jpg`），不是原图。

---

## 五、配置参考

全部配置位于 `config/`，都是静态类属性，**改完需要重启服务**。

### WebConfig — `config/web_config.py`

| 项 | 默认值 | 说明 |
| --- | --- | --- |
| `port` | `8111` | 服务监听端口 |

### ModelConfig — `config/model_config.py`

| 项 | 默认值 | 说明 |
| --- | --- | --- |
| `model_det_path` | `./model/det/ch/ch_PP-OCRv4_det_infer` | 文本检测模型 |
| `model_rec_path` | `./model/rec/ch/ch_PP-OCRv4_rec_infer` | 文本识别模型 |
| `cls_model_dir` | `./model/cls/ch_ppocr_mobile_v2.0_cls_infer` | 方向分类模型 |
| `is_use_gpu` | `False` | 装了 GPU 版飞桨才改成 `True` |
| `lang` | `ch` | 识别语言 |

模型路径相对**当前工作目录**解析，因此必须在项目根目录启动服务，否则会找不到模型。

### CVConfig — `config/cv_config.py`

| 项 | 默认值 | 说明 |
| --- | --- | --- |
| `pixel_fault_tolerance` | `8` | 表格线合并容差（像素）。相邻线距离小于该值会被视为同一条线。切格串行时可适当调小 |
| `min_size` | `2500` | 最小格面积，小于该值的轮廓当作噪声丢弃 |
| `cv_compress` | `1.3 * 1024 * 1024` | 图片压缩目标大小（字节） |
| `cvX` / `cvY` | `/cvX.jpg` `/cvY.jpg` | 横向 / 纵向表格线调试图文件名 |
| `cv_table` | `/cv_table.jpg` | 表格线合成调试图文件名 |
| `cv_point` | `/cv_point.jpg` | 角点标记调试图文件名 |
| `cv_x_right_split` | `100` | 右侧切分阈值 |
| `cv_x_left_split` | `100` | 左侧切分阈值 |
| `cv_y_head_split` | `200` | 表头切分阈值 |
| `cv_y_end_split` | `200` | 表尾切分阈值 |
| `cv_is_split` | `False` | 是否启用二次切分 |

### FileConfig — `config/file_config.py`

| 项 | 默认值 | 说明 |
| --- | --- | --- |
| `save_path` | `io/save_path` | 产物主目录 |
| `img_cache` | `cache` | 缓存目录 |
| `coord` | `coord` | 切图子目录名 |
| `main` | `main` | 正文子目录名 |
| `other` | `other` | 调试图子目录名 |
| `frame` | `frame` | 视频帧子目录名 |
| `is_delete_file` | `False` | 请求结束后是否删除本次 uuid 目录，**长期运行建议改 `True`** |
| `cv_accept_name` | `' accept_cv'` | 接收图文件名主体（注意前缀空格） |
| `cv_compress_img` | `compress_cv.jpg` | 压缩图文件名 |
| `cv_rotate_img` | `rotate_cv.jpg` | 矫正图文件名 |
| `cv_transform_img` | `transform_cv.jpg` | 透视变换图文件名 |
| `cv_intelligence_img` | `intelligence_cv.jpg` | 智能裁剪图文件名 |
| `cv_draw_max_rect` | `draw_cv.jpg` | 最大矩形标记图文件名 |
| `cv_video_img_name` | `video_img_cv` | 视频帧文件名前缀 |
| `suffix_jpg` | `.jpg` | 默认图片后缀 |
| `split_path` / `split_write` | `split` / `write` | 二次切分目录 |

### ThreadConfig — `config/thread_config.py`

| 项 | 默认值 | 说明 |
| --- | --- | --- |
| `pool_number` | `5` | 线程池大小（仅用于请求结束后异步删目录） |
| `is_open_threads` | `False` | 多线程开关，当前未启用 |
| `thread_number` | `2` | 线程数，当前未启用 |

---

## 六、处理链路与中间产物

以 `/process/res` 为例，一次请求的完整流程：

| 步骤 | 函数 | 产物 | 说明 |
| --- | --- | --- | --- |
| 1 | 落盘 | ` accept_cv.jpg` | base64 解码写入 uuid 目录 |
| 2 | `get_compress` | `compress_cv.jpg` | 按 `cv_compress` 目标大小等比压缩 |
| 3 | `get_transform` | `transform_cv.jpg` | 透视矫正（条件触发） |
| 4 | `get_correct` | `rotate_cv.jpg` | 霍夫直线检测倾角并反向旋转 |
| 5 | `cv_gray_path` + `cv_adaptiveThreshold` | `cv.jpg` | 灰度化 + 自适应二值化 |
| 6 | `cv_x_y` | `cvX.jpg` `cvY.jpg` | 形态学提取横竖表格线 |
| 7 | `cv_table` | `cv_table.jpg` | 横竖线合成得到完整表格骨架 |
| 8 | `cv_core` | `cv_point.jpg` | 求单元格轮廓，过滤噪声 |
| 9 | `cv_spilt_save` | `coord/*.jpg` | 按轮廓逐格切图并命名 |
| 10 | 智能定位 | `intelligence_cv.jpg` | 先用 det-only OCR 找文本框包围盒，外扩后裁出主表 |
| 11 | 逐格 OCR | — | 每格先放大再锐化，然后单独识别 |
| 12 | 规则匹配 | — | 按票种规则把文本归位到业务字段 |

其中 10 是前置步骤：先用文本检测网络（不跑识别网络，速度快）找出所有文本框的包围盒，向外扩张留白后裁出主表区域，再对这张裁剪图做 2–9 的切格，能显著减少页面边角噪声的干扰。

调试建议：切格效果不好时，直接看 `other/` 下的 `cvX.jpg` / `cvY.jpg` / `cv_table.jpg`——表格线提取得干不干净一眼就能看出来，比反复调参数猜要快得多。

---

## 七、排障手册

### 1. protobuf 版本不兼容

```
ImportError: cannot import name 'builder' from 'google.protobuf.internal'
```

```bash
pip install protobuf==3.20.2
```

### 2. numpy 相关报错

飞桨 2.x 不支持 numpy 2.x：

```bash
pip install "numpy<2"
```

### 3. Linux 下动态链接库错误

```bash
conda install nomkl
```

### 4. 模型加载失败或找不到模型

模型内置在 `model/` 目录，路径相对当前工作目录解析。**必须在项目根目录执行 `python -u web.py`**，在别的目录下启动会找不到模型。

### 5. 首次请求特别慢

正常。模型在首个请求到达时才加载，且进程池也是懒加载。之后同一进程内复用。

### 6. 切格串行、串格或丢格

| 现象 | 排查方向 |
| --- | --- |
| 相邻格子连成一片 | 表格线断裂。看 `other/cv_table.jpg` 确认，拍摄时尽量保证表格线清晰 |
| 格子被整体丢弃 | `CVConfig.min_size` 过大，调小 |
| 相邻表格线被合并成一格 | `CVConfig.pixel_fault_tolerance` 过大，调小（默认 8） |
| 表格区域定位偏了 | 看 `intelligence_cv.jpg`，智能定位的包围盒外扩参数是固定的（左 30、右 120、上 30、下 80），特殊版式可能不适用 |

### 7. `/process/common` 返回结构对不上文档

当前实现直接返回 PaddleOCR 引擎的原始输出，没有走统一的实体封装，所以字段可能与 [2.1](#21-post-processcommon--整图文字识别) 的定义不一致（例如拿不到 `uuid`、坐标是原始格式）。

处理方式二选一：按实际返回写解析，或改造 `service/base_service.py` 的 `common()` 让它复用 `_format_ocr_result`。

### 8. 图片路径含中文时识别失败

Windows 下 `cv2.imread` / `cv2.imwrite` 对非 ASCII 路径会静默失败（返回 `None` 而不报错）。**建议把项目放在纯英文路径下**，不要 clone 到中文目录。

### 9. 磁盘持续增长

`FileConfig.is_delete_file` 默认 `False`，每个请求的 uuid 目录都会保留，方便排查但也意味着磁盘只增不减。线上或长期运行请改成 `True`，或定期清理 `io/save_path/`。

### 10. 视频识别结果为空

可能原因：视频中没有清晰文字，或抽帧得到的帧全部无有效文本（此时返回 `[]`）。先用短视频试，确认单帧图片能识别再排查视频。

---

## 相关文档

- [README.md](../README.md) — 项目简介、快速开始、能力总览
- [requirements.txt](../requirements.txt) — 依赖清单与版本
