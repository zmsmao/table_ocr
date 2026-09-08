"""
-------------------------------------------------
    File Name:     cv_util
    Description:   表格线检测与单元格切分
                   输入一张表格图，输出切好的单元格图片（文件名携带坐标）
    date:          2023.08
-------------------------------------------------
    Change Activity: 2023.08
-------------------------------------------------
"""
import collections
import logging
import os
from typing import NamedTuple

import cv2
import numpy as np

from config.cv_config import CVConfig
import utils.file_util as fiul
import utils.image_util as imut
from utils.geometry_util import is_inside

logger = logging.getLogger(__name__)

# 次大表格区域面积占主表格的比例超过此值，才认为主表格被切碎并告警
FRAME_SPLIT_RATIO = 0.2


class Cell(NamedTuple):
    '''
    单元格。字段顺序与旧的六元组一致，仍可用下标访问。

    points 是四点坐标，顺序为 左上、左下、右上、右下。
    is_frame 为 True 表示这是整张表格的外框，不是真正的单元格，切图时会被丢弃。
    '''
    area: int
    x1: int
    points: list
    xw: int
    y1: int
    yh: int
    is_frame: bool = False


def rm_list(x_y_list, x_y_remove):
    '''
    按下标剔除元素。x_y_remove 传 set 才能避免 O(n*m) 的成员判断。
    '''
    return [item for k, item in enumerate(x_y_list) if k not in x_y_remove]


def cv_x_y(other, binary, x_eroded=1, y_eroded=1):
    '''
    用形态学分别提取横线与竖线。
    中间结果会存到 other 目录下（cvX.jpg / cvY.jpg），排查切分问题时很有用。
    '''
    rows, cols = binary.shape
    scale = 40
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(cols // scale, 1), 1))
    eroded = cv2.erode(binary, kernel, iterations=y_eroded)
    dilatedcol = cv2.dilate(eroded, kernel, iterations=1)
    cv2.imwrite(os.path.join(other, "cvX.jpg"), dilatedcol)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(rows // scale, 1)))
    eroded = cv2.erode(binary, kernel, iterations=x_eroded)
    dilatedrow = cv2.dilate(eroded, kernel, iterations=1)
    cv2.imwrite(os.path.join(other, "cvY.jpg"), dilatedrow)

    return dilatedcol, dilatedrow


def cv_table(other, dilatedcol, dilatedrow):
    '''
    合并横竖线得到表格骨架，并输出交点图便于排查。
    '''
    bitwise_and = cv2.bitwise_and(dilatedcol, dilatedrow)
    cv2.imwrite(other + CVConfig.cv_point, bitwise_and)
    merge = cv2.add(dilatedcol, dilatedrow)
    cv2.imwrite(other + CVConfig.cv_table, merge)
    return merge


def cv_core(merge):
    '''
    从表格骨架中提取单元格。

    用 findContours 的层级信息区分三种轮廓：
        顶层（parent = -1）   -> 整表外框
        顶层直接子轮廓        -> 单元格
        更深层（洞中岛）      -> 噪点，丢弃

    返回按面积倒序的 Cell 列表：识别到外框时它固定在第 0 位且 is_frame=True，
    真正要切图的单元格在其后。识别不到外框时列表里全是单元格，不会误吞格子。

    顶层轮廓多于一个说明表格线断裂，只保留面积最大的那块，并打 warning。
    '''
    kernel = np.ones((2, 2), np.uint8)
    merge = cv2.dilate(merge, kernel, iterations=1)
    found = cv2.findContours(merge, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # OpenCV 3.x 返回 (image, contours, hierarchy)，4.x 返回 (contours, hierarchy)
    contours, hierarchy = found[-2], found[-1]
    hierarchy = hierarchy[0] if hierarchy is not None and len(hierarchy) else []

    frames = []
    cells = []
    # 统一化 x/y：差值在容差内视为同一条线。不要预置 0，
    # 否则靠近原点的真实边界会被吸附到 0，引入整体偏移。
    x_set = []
    y_set = []
    # 外框与最外圈格子的边界常常完全重合（容差 8 通常大于线宽），
    # 共用一套去重会导致格子被当成外框的重复项吃掉，所以分开记。
    frame_seen = set()
    cell_seen = set()

    for index, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        x1 = _merge_coordinate(x, x_set)
        xw = _merge_coordinate(x + w, x_set)
        y1 = _merge_coordinate(y, y_set)
        yh = _merge_coordinate(y + h, y_set)

        temp = [(x1, y1), (x1, yh), (xw, y1), (xw, yh)]
        temp_boo = (x1, y1, xw, yh)
        area = abs(y1 - yh) * abs(x1 - xw)
        if area <= CVConfig.min_size:
            continue

        level = _contour_level(hierarchy, index)
        if level == 0:
            if temp_boo in frame_seen:
                continue
            frame_seen.add(temp_boo)
            frames.append(Cell(area, x1, temp, xw, y1, yh))
        elif level == 1:
            if temp_boo in cell_seen:
                continue
            cell_seen.add(temp_boo)
            cells.append(Cell(area, x1, temp, xw, y1, yh))
        # level >= 2：格子内部的小噪点，不是有效单元格

    frames.sort(key=lambda c: c.area, reverse=True)
    cells.sort(key=lambda c: (c.area, c.points[0]), reverse=True)
    if len(frames) > 1:
        # 页面上总会有零星线条（页眉页脚、手写笔迹），只有次大块面积达到
        # 主表格的一定比例，才说明主表格本身被切碎了，值得告警。
        ratio = frames[1].area / float(frames[0].area)
        if ratio >= FRAME_SPLIT_RATIO:
            logger.warning('表格被切成 %d 块（次大面积占比 %.0f%%），表格线可能存在断裂，'
                           '仅保留最大的一块', len(frames), ratio * 100)
        else:
            logger.debug('除主表格外还有 %d 块零散区域，占比 %.0f%%，忽略',
                         len(frames) - 1, ratio * 100)

    x_y_list = [frames[0]._replace(is_frame=True)] if frames else []
    x_y_list.extend(cells)
    if not x_y_list:
        logger.warning('未从表格骨架中检出任何单元格')
        return x_y_list

    logger.debug('外框: %s，单元格 %d 个',
                 x_y_list[0].points if frames else None,
                 len(x_y_list) - (1 if frames else 0))

    # 统计每条坐标线被多少个单元格引用
    x_result = []
    y_result = []
    for cell in x_y_list:
        x_result.append(cell.x1)
        x_result.append(cell.xw)
        y_result.append(cell.y1)
        y_result.append(cell.yh)
    x_dict = collections.Counter(x_result)
    y_dict = collections.Counter(y_result)

    if len(x_y_list) > 1:
        x_y_remove = set()
        for j, cell in enumerate(x_y_list):
            # 外框本来就是包住所有格子的，不参与"孤线"判定
            if cell.is_frame:
                continue
            x1 = x_dict.get(cell.x1)
            xw = x_dict.get(cell.xw)
            y1 = y_dict.get(cell.y1)
            yh = y_dict.get(cell.yh)
            # 只被引用一次的边界线，说明是误检出来的孤立格
            if (x1 == 1 or xw == 1) and (y1 == 1 or yh == 1):
                x_y_remove.add(j)

        cell_count = len(x_y_list) - (1 if frames else 0)
        if len(x_y_remove) < cell_count:
            x_y_list = rm_list(x_y_list, x_y_remove)
        else:
            # 散列式表单：只保留第一个能包住其它格子的外框。
            # 全程嵌套时兜底取第 0 个（最大的），原实现取的是最后一个（最小的）。
            lens = 0
            for u in range(0, len(x_y_list) - 1):
                if not is_inside(x_y_list[u].points, x_y_list[u + 1].points):
                    lens = u
                    break
            x_y_list = [x_y_list[lens]]

        # 丢掉不在主表格外框内的小表格
        if len(x_y_list) > 1:
            x_y_remove = {j for j, cell in enumerate(x_y_list)
                          if j > 0 and not is_inside(x_y_list[0].points, cell.points)}
            x_y_list = rm_list(x_y_list, x_y_remove)

    logger.debug('x_y_list: %s', [(c.area, c.points[0], c.points[3], c.is_frame) for c in x_y_list])
    return x_y_list


def _contour_level(hierarchy, index):
    '''
    返回轮廓层级：0=顶层外框，1=外框内的单元格，2=更深的噪点。
    拿不到层级信息时按 1 处理，宁可多留也不要误删。
    '''
    if index >= len(hierarchy):
        return 1
    parent = int(hierarchy[index][3])
    if parent < 0:
        return 0
    if parent >= len(hierarchy):
        return 1
    return 1 if int(hierarchy[parent][3]) < 0 else 2


def _merge_coordinate(value, exist_set):
    '''
    若 value 与已有坐标线差值在容差内，则复用已有值，否则登记为新坐标线。
    有多条线都在容差内时取最后一条（与原实现保持一致，通常是更接近的那条）。
    '''
    merged = None
    for item in exist_set:
        if abs(value - item) <= CVConfig.pixel_fault_tolerance:
            merged = item
    if merged is not None:
        return merged
    exist_set.append(value)
    return value


def cv_spilt_save(x_y_list, image, path):
    '''
    把每个单元格裁成小图存到 path 目录。

    外框（is_frame=True）不是单元格，会被丢掉——整表图在 main 目录已经存过。
    识别不到外框时列表里全是单元格，此时一个都不会少。
    '''
    cells = [c for c in x_y_list if not c.is_frame]
    if not cells:
        # 一个格子都没切出来时，退化成把最大的矩形存下来
        cells = x_y_list[:1]
    for cell in cells:
        xt = cell.points[0][0]
        yt = cell.points[0][1]
        xwt = cell.points[3][0]
        yht = cell.points[3][1]
        x, y, w, h = cv2.boundingRect(np.array(cell.points))
        roi = image[y:y + h, x:x + w]
        if h * w > CVConfig.min_size:
            cv2.imwrite(path + '/' + '%s_%s_%s_%s_%s_coordinate.jpg'
                        % (yt, yht, xt, xwt, h * w), roi)


def cv_end_save(x_y_list, image, coord, main):
    '''
    保存整表外框、表头，并把外框以外的区域存成对照图。

    文件名格式：y_yh_x_xw_面积_后缀.jpg，后缀为 head / coordinate / main。
    '''
    cv_spilt_save(x_y_list, image, coord)
    if not x_y_list:
        return

    height, width = image.shape[0:2]
    # [MODIFIED] 动态计算顶部容差，代替固定的 20 像素，防止不同分辨率下误切
    y_threshold = max(20, int(height * 0.02))

    cells = [c for c in x_y_list if not c.is_frame] or x_y_list
    cells = sorted(cells, key=lambda c: c.points[0][1])
    x, y, w, h = cv2.boundingRect(np.array(cells[0].points))
    if y <= y_threshold:
        # 顶部有细长条（或残留的外框）时向下找第一行真正的单元格；
        # 全都贴顶就回到第一行，不能停在最后一行。
        for cell in cells[1:]:
            x, y, w, h = cv2.boundingRect(np.array(cell.points))
            if y >= y_threshold:
                break
        else:
            x, y, w, h = cv2.boundingRect(np.array(cells[0].points))

    roi = image[y:y + h, x:x + w]
    cv2.imwrite(main + '/_' + '%s_%s_%s_%s_main.jpg' % (y, y + h, x, x + w), roi)

    mask = np.zeros_like(image)
    cv2.rectangle(mask, (x, y), (x + w, y + h), (255, 255, 255), -1)
    roi_not = cv2.bitwise_and(image, cv2.bitwise_not(mask))
    cv2.imwrite(main + '/_other_coordinate_not.jpg', roi_not)

    # 外框以上的部分视为表头
    if y > 0 and (y - 0) * width > CVConfig.min_size / 2:
        roi_h = image[0:y, 0:width]
        cv2.imwrite(coord + '/' + '%s_%s_%s_%s_%s_head.jpg'
                    % (0, y, x, x + w, y * width), roi_h)


def cv_build(uuid, name):
    '''
    表格切分主入口：预处理 -> 灰度二值 -> 提取表格线 -> 切格保存。
    返回 (切图目录, 识别结果目录)。
    '''
    root, coord, main, other, txt_result = fiul.uuid_save_mkdirs(uuid)
    save_rotate = fiul.uuid_save_rotate_img(uuid)
    target_path = root + "/" + name
    # 压缩 + 透视矫正
    target_path = imut.cv_init_img(target_path, uuid)
    # 倾斜矫正
    if imut.get_correct(target_path, save_rotate):
        target_path = save_rotate
    # 灰度 + 二值
    gray, image = imut.cv_gray_path(target_path)
    binary = imut.cv_adaptiveThreshold(gray)
    # 提取横竖线并合成表格
    dilatedcol, dilatedrow = cv_x_y(other, binary)
    merge = cv_table(other, dilatedcol, dilatedrow)
    # 求单元格并落盘
    x_y_list = cv_core(merge)
    cv_end_save(x_y_list, image, coord, main)
    return coord, txt_result