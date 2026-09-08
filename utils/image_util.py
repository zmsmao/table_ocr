"""
-------------------------------------------------
    File Name:     image_util
    Description:   单张图片的预处理（灰度/二值/压缩/透视矫正/旋转/锐化/扩边/视频抽帧）
                   只负责把图片处理得更好识别，不关心表格结构
    date:          2023.08
-------------------------------------------------
    Change Activity: 2023.08
-------------------------------------------------
"""
import logging
import math
import os

import cv2
import numpy as np

from config.cv_config import CVConfig
import utils.file_util as fiul

logger = logging.getLogger(__name__)


def rotate(image, angle, scale=1.0):
    '''
    仿射旋转，中心取图像几何中心。

    画布按旋转后的外接矩形扩大：不扩的话四角内容会被裁掉（1920 宽的图转 3 度约损失 50px）。
    文档图用白色填充边框，避免黑边被后续形态学当成内容。
    '''
    height, width = image.shape[0:2]
    center = (width / 2.0, height / 2.0)
    wrap_mat = cv2.getRotationMatrix2D(center, angle, scale)
    cos = abs(wrap_mat[0, 0])
    sin = abs(wrap_mat[0, 1])
    new_width = int(height * sin + width * cos)
    new_height = int(height * cos + width * sin)
    # 把旋转后的图像平移到新画布中心
    wrap_mat[0, 2] += new_width / 2.0 - center[0]
    wrap_mat[1, 2] += new_height / 2.0 - center[1]
    return cv2.warpAffine(image, wrap_mat, (new_width, new_height),
                          borderValue=(255, 255, 255))


def cv_gray_path(path):
    '''
    读图并返回 (灰度图, 原图)。
    '''
    image = cv2.imread(path, 1)
    if image is None:
        raise ValueError('图片读取失败或格式不支持: %s' % path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray, image


def cv_adaptiveThreshold(gray):
    '''
    自适应二值化，把背景与前景反转（表格线变白）。
    '''
    # [MODIFIED] 直接使用 cv2.THRESH_BINARY_INV 避免在 Python 层分配临时取反矩阵
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY_INV, 35, -7)


def get_correct(path, save_path, min_angle=0.5, max_angle=15.0):
    '''
    用霍夫直线检测整体倾斜角度并旋转矫正。
    返回 True 表示已生成矫正后的图片（save_path），False 表示无需矫正或放弃矫正。

    min_angle / max_angle 是安全边界：低于 min_angle 不值得重采样，
    高于 max_angle 说明检测到的多半不是表格线，宁可不转也不要把图转废。
    '''
    gray, image = cv_gray_path(path)
    kernel = np.ones((5, 5), np.uint8)
    erode_img = cv2.erode(gray, kernel)
    ero_dil = cv2.dilate(erode_img, kernel)
    canny = cv2.Canny(ero_dil, 50, 150)
    lines = cv2.HoughLinesP(canny, 0.8, np.pi / 180, 90, minLineLength=100, maxLineGap=10)
    # 图里没有足够长的直线时 HoughLinesP 返回 None
    if lines is None:
        return False
    # OpenCV 4.x 返回 (N, 1, 4)，5.x 返回 (N, 4)，统一成 (N, 4)
    lines = np.asarray(lines).reshape(-1, 4)

    # 关键点：角度必须归一化到 (-45, 45]。
    # 表格里近横线的斜率是 ±0.05 量级、近竖线是 ±19 量级，直接对斜率取中位数会被竖线带偏，
    # 列多行数少时竖线占多数，会算出 -87 度这种荒谬角度把整张图转废。
    # 表格线方向以 90 度为周期（横线与竖线等价），折叠到 (-45, 45] 后两者才是同一个值。
    angles = []
    for x1, y1, x2, y2 in lines:
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            continue
        angle = math.degrees(math.atan2(dy, dx))
        angles.append((angle + 45) % 90 - 45)
    # 没有可用直线时不要拿着空列表去取中位数（np.median([]) 是 nan，会一路传到旋转矩阵）
    if not angles:
        return False

    angle = float(np.median(angles))
    if abs(angle) < min_angle:
        return False
    if abs(angle) > max_angle:
        logger.warning('倾斜角度 %.2f 度超出阈值 %s，放弃矫正: %s', angle, max_angle, path)
        return False

    logger.debug('旋转的角度为: %s', angle)
    rotate_img = rotate(image, angle)
    cv2.imwrite(save_path, rotate_img)
    return True


def get_compress(input_path, output_path, target_max_size):
    '''
    按目标字节数等比压缩。返回 True 表示已生成压缩图（output_path）。
    原始文件本身小于目标值时不做处理。
    '''
    image = cv2.imread(input_path)
    if image is None:
        return False
    if os.path.getsize(input_path) < target_max_size:
        return False

    width = image.shape[1]
    height = image.shape[0]
    original_size = width * height
    compression_ratio = (target_max_size * 1.75 / original_size) ** 0.5
    if compression_ratio >= 1:
        return False

    # [MODIFIED] 下采样（缩小图片）时使用 cv2.INTER_AREA 代替 INTER_CUBIC 以防锯齿及提升效率
    compressed_image = cv2.resize(
        image,
        (int(width * compression_ratio), int(height * compression_ratio)),
        interpolation=cv2.INTER_AREA)
    cv2.imwrite(output_path, compressed_image)
    return True


def mush_approx(approx):
    '''
    多次用凸包逼近，尽量把轮廓收敛成四边形。
    '''
    for _ in range(2):
        if len(approx) > 4:
            hull = cv2.convexHull(approx)
            approx = hull if len(hull) == 4 else cv2.convexHull(hull)
    return approx


def get_x_y_set(points):
    '''
    按像素容差归并角点的 x/y，返回去重后的坐标集合。
    '''
    x_set = []
    y_set = []
    for point in points:
        x, y = point
        logger.debug('Point: (%s, %s)', x, y)
        temp_index = 0
        y1 = y
        for index in range(len(y_set)):
            if abs(y1 - y_set[index]) <= CVConfig.pixel_fault_tolerance:
                temp_index = index
                y1 = y_set[index]
        if temp_index == 0:
            y_set.append(y1)
        temp_index = 0
        x1 = x
        for index in range(len(x_set)):
            if abs(x1 - x_set[index]) <= CVConfig.pixel_fault_tolerance:
                temp_index = index
                x1 = x_set[index]
        if temp_index == 0:
            x_set.append(x1)
    return x_set, y_set


def contour_sort_rule(point, width, height):
    '''
    角点排序：左上、右上、左下、右下。
    注意：OpenCV 坐标是 (x=列, y=行)，所以 x 与宽度比、y 与高度比。
    '''
    x, y = point
    if x <= width // 2 and y <= height // 2:
        return 1
    elif x > width // 2 and y <= height // 2:
        return 2
    elif x <= width // 2 and y > height // 2:
        return 3
    else:
        return 4


def check_trf_success(image):
    '''
    透视变换后再次检测：变换结果是否已接近规整矩形。
    '''
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv_adaptiveThreshold(gray)
    contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False
    max_contour = max(contours, key=cv2.contourArea)
    approx = mush_approx(cv2.approxPolyDP(max_contour, 0.02 * cv2.arcLength(max_contour, True), True))
    points = approx.squeeze().tolist()
    if not isinstance(points, list) or len(points) != 4:
        return False
    logger.debug('透视变换 check ----')
    x_set, y_set = get_x_y_set(points)
    return len(set(x_set)) != 2 and len(set(y_set)) != 2


def get_transform(input_path, output_path):
    '''
    透视变换：把拍歪的表格拉正。
    返回 True 表示已生成变换后的图片（output_path），False 表示放弃变换。
    '''
    gray, image = cv_gray_path(input_path)
    gray = cv_adaptiveThreshold(gray)
    contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False
    max_contour = max(contours, key=cv2.contourArea)

    height, width = image.shape[0:2]
    x, y, w, h = cv2.boundingRect(max_contour)
    # 外接矩形四角，作为变换的目标点
    box = np.intp([(x, y), (x, y + h), (x + w, y), (x + w, y + h)])

    approx = mush_approx(cv2.approxPolyDP(max_contour, 0.02 * cv2.arcLength(max_contour, True), True))
    points = approx.squeeze().tolist()
    # 不足或超过四个角点则无法做透视变换
    if not isinstance(points, list) or len(points) != 4:
        return False

    logger.debug('透视变换 ----')
    sorted_points = sorted(points, key=lambda p: contour_sort_rule(p, width, height))
    sorted_box = sorted(box, key=lambda p: contour_sort_rule(p, width, height))
    x_set, y_set = get_x_y_set(sorted_points)
    # 角点已经很规整，说明没拍歪，不必变换
    if len(set(x_set)) == 2 and len(set(y_set)) == 2:
        return False

    src = np.float32(sorted_points)
    dst = np.float32(sorted_box)
    matrix = cv2.getPerspectiveTransform(src, dst)
    result = cv2.warpPerspective(image, matrix, (width, height))
    if check_trf_success(result):
        cv2.imwrite(output_path, result)
        return True
    return False


def cv_sharpening(img_path):
    '''
    锐化后覆盖原文件，返回文件路径。
    '''
    image = cv2.imread(img_path)
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    image = cv2.filter2D(image, -1, kernel)
    cv2.imwrite(img_path, image)
    return img_path


def expand_cv_img(src_path):
    '''
    给切图补一圈白边再送去 OCR，能明显提升贴边文字的识别率。
    返回临时文件路径（与原图同目录）。
    '''
    file_dir = os.path.dirname(src_path)
    filename = os.path.basename(src_path)
    fx = filename.split('.')[1]
    img = cv2.imread(src_path)
    expanded_img = cv2.copyMakeBorder(img, 6, 14, 10, 10,
                                      cv2.BORDER_CONSTANT, value=[255, 255, 255])
    tmp = os.path.join(file_dir, '_tmp.' + fx)
    cv2.imwrite(tmp, expanded_img)
    return tmp


def cv_init_img(src_path, uuid, is_compress=True):
    '''
    识别前的统一预处理：先按需压缩，再做透视矫正。
    返回最终可用的图片路径。
    '''
    save_compress = fiul.uuid_save_compress_img(uuid)
    save_transform = fiul.uuid_save_transform_img(uuid)
    target = src_path
    if is_compress:
        if get_compress(target, save_compress, CVConfig.cv_compress):
            target = save_compress
    if get_transform(target, save_transform):
        target = save_transform
    return target


def cv_init_video(video_path, frame_path):
    '''
    按秒抽帧，并剔除相邻帧差异过小的重复帧，返回帧图片路径列表。
    '''
    img_list = []
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps:
        cap.release()
        return img_list
    duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if duration < 1:
        cap.release()
        return img_list

    frame_name = [int(i * fps) for i in range(1, int(duration) + 1)]
    
    # [MODIFIED] 优化内存：移除 frame_list 预存机制，改为边读流边计算的双帧比对
    frame_count = 0
    sample_index = 0
    prev_gray = None
    prev_frame = None
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if frame_count in frame_name:
            # 只保留下方 1/6 区域（通常是字幕/标题条）
            frame = frame[height - height // 6:, width // 8:width - width // 8, :]
            
            # 实时转换当前帧为灰度二值化图像
            gray_curr = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, gray_curr = cv2.threshold(gray_curr, 215, 255, cv2.THRESH_BINARY)
            
            # 若存在上一帧，则计算差异并落盘
            if prev_gray is not None:
                if cal_stderr(prev_gray, gray_curr) > 1.5:
                    path = frame_path + "/" + str(sample_index - 1) + "_frame.jpg"
                    img_list.append(path)
                    cv2.imwrite(path, prev_frame)
            
            # 滚动替换缓存帧
            prev_gray = gray_curr
            prev_frame = frame
            sample_index += 1
            
    cap.release()
    return img_list


def cal_stderr(img, imgo=None):
    '''
    图像差异度量，用于视频抽帧时判断相邻帧是否变化。
    '''
    if imgo is None:
        return (img ** 2).sum() / img.size * 100
    return ((img - imgo) ** 2).sum() / img.size * 100