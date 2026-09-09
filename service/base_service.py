"""
表格 / 工作票识别核心服务
架构：多进程高吞吐量模式。依托 Multiprocessing.Pool，由 init_worker_engine 进行模型预热。
"""
import os
import sys
import cv2
from typing import List, Dict, Any, Tuple, Optional
from loguru import logger

# 核心依赖
from paddleocr import PaddleOCR
from rules.base_rules import rules

# 配置与实体域
from config.file_config import FileConfig
from config.model_config import ModelConfig
from config.cv_config import CVConfig
from domain.ocr_result_common import OCRCommon, OCRAll

# 工具类
import utils.common_util as comm
import utils.file_util as fiul
import utils.cv_util as cvut
import utils.geometry_util as geut

# ==============================================================================
# 全局模型缓存 (每个子进程独立拥有一份)
# ==============================================================================
_WORKER_OCR_ENGINE: Optional[PaddleOCR] = None

# 修改后：
def init_worker_engine():
    """
    子进程初始化函数：供 Multiprocessing.Pool 初始化时自动调用。
    生命周期内仅执行一次，避免重复加载模型的极高耗时。
    """
    # 强制配置子进程日志格式与等级，放开 INFO 和 DEBUG 级别拦截
    # 替换为 loguru 的控制台配置
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    global _WORKER_OCR_ENGINE
    if _WORKER_OCR_ENGINE is None:
        logger.info(f"[PID {os.getpid()}] 正在分配显存/内存，预热 PaddleOCR 模型...")
        _WORKER_OCR_ENGINE = PaddleOCR(
            det_model_dir=ModelConfig.model_det_path,
            rec_model_dir=ModelConfig.model_rec_path,
            use_gpu=ModelConfig.is_use_gpu,
            cls_model_dir=ModelConfig.cls_model_dir,
            lang=ModelConfig.lang,
            use_angle_cls=True,
            show_log=False  # 关闭底层繁杂日志，保持控制台整洁
        )
        logger.info(f"[PID {os.getpid()}] 模型加载完成，工作进程就绪！当前配置 GPU: {ModelConfig.is_use_gpu}")

def _get_engine() -> PaddleOCR:
    """
    获取当前进程的模型引擎。
    作为降级机制：如果直接调用未经过 Pool 初始化的进程，会自动进行懒加载预热。
    """
    global _WORKER_OCR_ENGINE
    if _WORKER_OCR_ENGINE is None:
        logger.warning(f"[PID {os.getpid()}] 检测到未预热直接调用，触发懒加载机制！")
        init_worker_engine()
    return _WORKER_OCR_ENGINE

# ==============================================================================
# 核心业务逻辑
# ==============================================================================

def com_video_img(media_type: int, uuid: str, target_dir: str) -> List[str]:
    """处理视频与图片的通用识别逻辑"""
    logger.info(f"[Task={uuid}] 开始执行 com_video_img, Media Type: {media_type}, Target Dir: {target_dir}")
    engine = _get_engine()

    if media_type == 1:
        # 处理图片类型
        logger.debug(f"[Task={uuid}] 准备进行图片压缩与识别...")
        save_compress = fiul.uuid_save_compress_img(uuid)
        target = target_dir
        
        # 压缩验证
        if cvut.get_compress(target, save_compress, CVConfig.cv_compress):
            logger.debug(f"[Task={uuid}] 图片满足压缩条件，将使用压缩后路径: {save_compress}")
            target = save_compress
        else:
            logger.debug(f"[Task={uuid}] 图片无需压缩，使用原路径: {target}")
            
        logger.info(f"[Task={uuid}] 开始调用 OCR 引擎 (rec=True)...")
        result = engine.ocr(target, rec=True)
        extracted_texts = comm.extract_text_obj(result)
        logger.info(f"[Task={uuid}] 图片识别完成，提取文本 {len(extracted_texts)} 条")
        for i, text in enumerate(extracted_texts):
            logger.debug(f"[Task={uuid}] 提取文本条目 {i+1}: {text[1]}")
        return [item[1] for item in extracted_texts]

    if media_type == 2:
        # 处理视频类型
        logger.info(f"[Task={uuid}] 开始提取视频帧并执行批处理...")
        frame = fiul.uuid_save_mkdir_video_frame(uuid)
        img_list = cvut.cv_init_video(target_dir, frame)
        logger.info(f"[Task={uuid}] 视频抽帧完成，共抽取了 {len(img_list)} 帧")
        
        list_txt_no_filter_pj = []
        list_txt_filter_pj = []
        
        for idx, img in enumerate(img_list):
            logger.debug(f"[Task={uuid}] 正在识别第 {idx+1}/{len(img_list)} 帧图像: {img}")
            result = engine.ocr(img)
            lists = comm.extract_text_obj(result)
            
            txt_no_filter_pj = "".join([lst[1] for lst in lists])
            txt_filter_pj = "".join([comm.filter_text(lst[1]) for lst in lists])
            
            if txt_filter_pj:
                list_txt_no_filter_pj.append(txt_no_filter_pj)
                list_txt_filter_pj.append(txt_filter_pj)
            logger.debug(f"[Task={uuid}] 第 {idx+1} 帧识别出文本块 {len(lists)} 个")
                
        if not list_txt_no_filter_pj:
            logger.warning(f"[Task={uuid}] 视频未识别到有效文本")
            return []

        # 过滤重复信息
        logger.info(f"[Task={uuid}] 开始对多帧提取的文本进行去重过滤...")
        res = [list_txt_no_filter_pj[0]]
        for i in range(len(list_txt_no_filter_pj) - 1):
            if list_txt_filter_pj[i].find(list_txt_filter_pj[i + 1]) == -1:
                res.append(list_txt_no_filter_pj[i + 1])
                
        logger.info(f"[Task={uuid}] 视频帧识别完成，去重后保留 {len(res)} 条记录")
        for i, text in enumerate(res):
            logger.debug(f"[Task={uuid}] 最终视频文本条目 {i+1}: {text[:30]}...")
        return res

    logger.warning(f"[Task={uuid}] 未知的 Media Type: {media_type}，直接返回空列表")
    return []


def common(data: Dict[str, Any], uuid: str) -> Any:
    """基础全图 OCR 识别"""
    logger.info(f"[Task={uuid}] 开始基础整图识别 (common)")
    engine = _get_engine()
    
    root_dir, name = _save_and_get_path(data, uuid)
    target_path = f"{root_dir}/{name}"
    logger.debug(f"[Task={uuid}] 图像已落盘至目标路径: {target_path}")
    
    logger.info(f"[Task={uuid}] 调用 OCR 引擎 (det=False)...")
    result = engine.ocr(target_path, det=False)
    logger.info(f"[Task={uuid}] 基础识别完成, 返回结果对象.")
    return result


def res(data: Dict[str, Any], uuid: str, executor: Any = None) -> Any:
    """工作票/规则结构化数据提取"""
    logger.info(f"[Task={uuid}] 开始智能提取识别 (res)")
    engine = _get_engine()
    coord_img_path: List[str] = []
    
    # 智能识别分割
    key_words = ["种", "记录", "带电", "附页"]
    logger.info(f"[Task={uuid}] 执行智能分割，探测关键词: {key_words}")
    name = intelligence_split(
        data=data, 
        uuid=uuid, 
        table_engine=engine, 
        coord_img_path=coord_img_path, 
        is_check_word=False, 
        key_words=key_words
    )
    
    logger.info(f"[Task={uuid}] 智能分割完成，共产生 {len(coord_img_path)} 个切片。开始匹配提取规则...")
    result = rules(coord_img_path=coord_img_path, table_engine=engine, uuid=uuid, name=name)
    logger.info(f"[Task={uuid}] 规则提取完成, 成功返回结构化结果.")
    return result


def all(data: Dict[str, Any], uuid: str, executor: Any = None) -> List[Dict[str, Any]]:
    """表格按坐标完整分割 + 逐格识别装配"""
    logger.info(f"[Task={uuid}] 开始执行全量表格分割与识别 (all)")
    engine = _get_engine()
    coord_img_path: List[str] = []
    
    # 获取智能分割图像切片路径
    logger.debug(f"[Task={uuid}] 调用 intelligence_split 获取切片...")
    name = intelligence_split(data, uuid, engine, coord_img_path, is_check_word=False)
    img_names = fiul.get_file_name(coord_img_path)
    
    objs = []
    total_slices = len(coord_img_path)
    logger.info(f"[Task={uuid}] 共有 {total_slices} 个切片需要分析")
    
    for i, path in enumerate(coord_img_path):
        logger.debug(f"[Task={uuid}] 分析切片 {i+1}/{total_slices}，路径: {path}")
        result = engine.ocr(path)
        one_result = _format_ocr_result(result, name, uuid)
        
        # 从文件名中解析坐标位置
        s_index = str(img_names[i]).split("_")
        obj = OCRAll()
        obj._bbox = [
            [s_index[2], s_index[0]], [s_index[2], s_index[1]],
            [s_index[3], s_index[0]], [s_index[3], s_index[1]]
        ]
        obj._name = name
        obj._result = one_result
        obj._suffix = s_index[-1]
        obj._bbox_path = f"{FileConfig.save_path}/{uuid}/{FileConfig.coord}/{img_names[i]}"
        
        objs.append(obj.__dict__)
        
    logger.info(f"[Task={uuid}] 全量表格分割装配完毕，总装配对象数: {len(objs)}")
    return objs

# ==============================================================================
# 内部工具与支撑函数 (Private Functions)
# ==============================================================================

def _save_and_get_path(data: Dict[str, Any], uuid: str) -> Tuple[str, str]:
    """统一的落盘逻辑"""
    suffix = data.get('suffix', '')
    name = f"{FileConfig.cv_accept_name}{suffix}"
    root_dir = fiul.uuid_save_root(uuid)
    logger.debug(f"[Task={uuid}] 保存图像文件至 {root_dir}/{name}")
    fiul.save_image(data.get('image'), f"{root_dir}/{name}")
    return root_dir, name


def _format_ocr_result(result: Any, name: str, uuid: str) -> List[Dict[str, Any]]:
    """格式化 OCR 返回结果结构"""
    extracted_lists = comm.extract_text_obj(result)
    logger.debug(f"[Task={uuid}] 格式化 OCR 结果，总计 {len(extracted_lists)} 个元素")
    return [
        {
            "_coordinates": item[0],
            "_txt_result": item[1],
            "_name": name,
            "_txt_rate": item[2],
            "_uuid": uuid
        }
        for item in extracted_lists
    ]


def _exec_comm_ocr(path: str, name: str, uuid: str, table_engine: PaddleOCR) -> List[Dict[str, Any]]:
    """针对具体文件的公用 OCR 封装"""
    logger.debug(f"[Task={uuid}] 针对具体文件执行公用 OCR, 路径: {path}")
    result = table_engine.ocr(path)
    return _format_ocr_result(result, name, uuid)


def intelligence_split(
    data: Dict[str, Any], 
    uuid: str, 
    table_engine: PaddleOCR, 
    coord_img_path: List[str], 
    is_check_word: bool = False, 
    key_words: Optional[List[str]] = None
) -> str:
    """
    智能表格轮廓分割。
    通过一次无文本识别（仅轮廓），锁定核心表格坐标区域并裁剪，屏蔽外部无用信息。
    """
    key_words = key_words or []
    logger.info(f"[Task={uuid}] 启动智能表格轮廓分割, is_check_word={is_check_word}")
    
    root_dir, name = _save_and_get_path(data, uuid)
    root_image = f"{root_dir}/{name}"
    target_path = cvut.cv_init_img(root_image, uuid)
    
    image = cv2.imread(target_path)
    if image is None:
        logger.error(f"[Task={uuid}] 无法读取图像文件: {target_path}")
        raise ValueError(f"无法读取图像文件: {target_path}")
        
    height, width, _ = image.shape
    logger.debug(f"[Task={uuid}] 读取图像尺寸: W={width}, H={height}")
    index_list = []
    
    if is_check_word:
        logger.info(f"[Task={uuid}] 开启文本关键词定位, 开始 OCR 完整识别提取坐标...")
        check_index = 0
        ans = _exec_comm_ocr(path=target_path, name=name, uuid=uuid, table_engine=table_engine)
        
        for i, item in enumerate(ans):
            if item['txt_result'] in key_words:
                check_index = i
                logger.debug(f"[Task={uuid}] 匹配到关键词 '{item['txt_result']}'，索引位置为 {i}")
                break
                
        # 保护机制：如果匹配词太靠下（超出行高一半），视为无效或次要表头，从头切分
        tmp_coord = ans[check_index]['coordinates']
        if int(tmp_coord[0][0]) > height / 2:
            logger.warning(f"[Task={uuid}] 匹配词太靠下(Y={tmp_coord[0][0]} > {height/2})，触发保护机制，从头切分")
            check_index = 0
            
        index_list.extend([item['coordinates'] for item in ans[check_index:]])
        logger.debug(f"[Task={uuid}] 关键词定位完毕，共圈定 {len(index_list)} 个有效坐标区域")
    else:
        # 直接使用文本块检测网络 (DBNet) 识别轮廓，不走识别网络，速度极快
        logger.info(f"[Task={uuid}] 直接使用 DBNet 检测网络定位表格轮廓 (rec=False)...")
        ans = table_engine.ocr(target_path, rec=False)
        if ans and ans[0]:
            coordinates = ans[0]
            index_list = [[[int(num) for num in point] for point in block] for block in coordinates]
            logger.debug(f"[Task={uuid}] DBNet 成功定位 {len(index_list)} 个外包络块")
        else:
            logger.warning(f"[Task={uuid}] DBNet 未检测到有效区域轮廓")
        
    # 计算最小包围盒并向外扩张留白区 (Bounding Box Expansion)
    logger.debug(f"[Task={uuid}] 计算最小包围盒并扩张...")
    rectangle = geut.expand_coordinates(
        geut.calculate_bounding_box(index_list), 
        width, height, 
        30, 120, 30, 80
    )
    
    x1, y1 = map(int, rectangle[0])
    x2, y2 = map(int, rectangle[1])
    logger.debug(f"[Task={uuid}] 最终切片区域: [X:{x1}->{x2}, Y:{y1}->{y2}]")
    
    # OpenCV 裁剪图像：切片区域 [Y_start:Y_end, X_start:X_end]
    roi = image[y1:y2, x1:x2]
    image_name = f"{root_dir}/{FileConfig.cv_intelligence_img}"
    cv2.imwrite(image_name, roi)
    logger.info(f"[Task={uuid}] 核心区域已裁剪并保存至: {image_name}")
    
    # 结合传统的 OpenCV 连通域/霍夫曼直线识别表框
    logger.info(f"[Task={uuid}] 调用 OpenCV 直线检测及表框重构 (cv_build)...")
    coord, _ = cvut.cv_build(uuid, FileConfig.cv_intelligence_img)
    logger.debug(f"[Task={uuid}] OpenCV 表框构建完成，获得 {len(coord) if coord else 0} 个区块坐标")
    
    # 将切片存入结果队列
    fiul.list_one_dir(coord, coord_img_path)
    logger.info(f"[Task={uuid}] 切片文件列表初始化完毕")
    
    return name