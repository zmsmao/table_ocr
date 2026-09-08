import cv2
import numpy as np
import collections
import math
import os
from config.cv_config import CVConfig
import utils.file_util as fiul

def analyze_data(data):
    """
    分析数据，获取去噪后的中位数。
    说明：使用 NumPy 向量化操作替代原有的多重列表推导式，降低时间复杂度。
    """
    arr = np.array(data, dtype=float)
    non_zero = arr[arr != 0]
    zero_count = len(arr) - len(non_zero)
    
    if zero_count > len(non_zero) * 2:
        return 0.0
        
    # 区分正负两部分
    positive = non_zero[non_zero > 0]
    negative = non_zero[non_zero < 0]
    
    # 选择数据量较多部分
    selected_data = positive if len(positive) > len(negative) else negative
    
    if len(selected_data) == 0:
        return 0.0
        
    # 计算统计量      
    return float(np.median(selected_data))

def rotate(image, angle, center=None, scale=1.0):
    """图像旋转"""
    # 修正了原代码中 (w,h) = image.shape[0:2] 的错误赋值，shape前两位为 (h, w)
    h, w = image.shape[:2]
    if center is None:
        center = (w // 2, h // 2)   
    wrap_mat = cv2.getRotationMatrix2D(center, angle, scale)    
    return cv2.warpAffine(image, wrap_mat, (w, h))

def is_inside(src, dst):
    """判断src矩形是否在dst矩形内部"""
    src_x, src_y = zip(*src)
    dst_x, dst_y = zip(*dst)

    return (max(dst_x) <= max(src_x) and min(dst_x) >= min(src_x) and
            max(dst_y) <= max(src_y) and min(dst_y) >= min(src_y))
    
def rm_list(target_list, remove_indices):
    """
    根据索引移除列表元素。
    说明：将原代码中的列表查找 if k not in x_y_remove 优化为 set 集合查找，时间复杂度从 O(N) 降至 O(1)。
    """
    remove_set = set(remove_indices)
    return [val for i, val in enumerate(target_list) if i not in remove_set]

# 灰度化
def cv_gray(root, name):
    image_path = os.path.join(root, name)
    image = cv2.imread(image_path)
    
    # 裁剪图片
    # 说明：移除了原代码中先 imwrite 保存再 imread 读取的冗余磁盘 I/O 操作，直接通过 NumPy 切片完成裁剪。
    if CVConfig.cv_is_split:
        height, width = image.shape[:2]
        image = image[CVConfig.cv_y_head_split : height - CVConfig.cv_y_end_split,
                      CVConfig.cv_x_right_split : width - CVConfig.cv_x_left_split]
                      
    # 灰度图片
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray, image

def cv_gray_path(path):
    image = cv2.imread(path, 1)
    # 灰度图片
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray, image

# 二值化
def cv_adaptiveThreshold(gray):
    binary = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, -7)
    return binary

# 识别横竖线
def cv_x_y(other_path, binary, x_eroded=1, y_eroded=1):
    rows, cols = binary.shape
    scale = 40
    
    # 识别竖线 (原 dilatedcol)
    kernel_col = cv2.getStructuringElement(cv2.MORPH_RECT, (cols // scale, 1))
    eroded_col = cv2.erode(binary, kernel_col, iterations=y_eroded)
    vertical_lines = cv2.dilate(eroded_col, kernel_col, iterations=1)
    cv2.imwrite(os.path.join(other_path, "cvX.jpg"), vertical_lines)

    # 识别横线 (原 dilatedrow)
    kernel_row = cv2.getStructuringElement(cv2.MORPH_RECT, (1, rows // scale))
    eroded_row = cv2.erode(binary, kernel_row, iterations=x_eroded)
    horizontal_lines = cv2.dilate(eroded_row, kernel_row, iterations=1)
    cv2.imwrite(os.path.join(other_path, "cvY.jpg"), horizontal_lines)

    return vertical_lines, horizontal_lines

# 识别表格
def cv_table(other_path, vertical_lines, horizontal_lines):
    # 标识交点：将二值像素点生成图片保存
    bitwise_and = cv2.bitwise_and(vertical_lines, horizontal_lines)
    cv2.imwrite(os.path.join(other_path, CVConfig.cv_point), bitwise_and) 
    
    # 标识表格
    # cv2.imshow("表格整体展示：",merge)
    # cv2.waitKey(0)
    merge = cv2.add(vertical_lines, horizontal_lines)
    table_path = os.path.join(other_path, CVConfig.cv_table)
    cv2.imwrite(table_path, merge)
    return merge, table_path

def _snap_coord(val, coord_list, tolerance):
    """
    辅助函数：坐标吸附。
    说明：提取原代码中冗长且重复的 x, xw, y, yh 遍历匹配逻辑，减少代码冗余并提升可读性。
    """
    for existing in coord_list:
        if abs(val - existing) <= tolerance:
            return existing
    coord_list.append(val)
    return val

def cv_core(merge, table_path):
    # 对二值化图像进行轮廓检测，得到每一个表格的轮廓
    kernel = np.ones((2, 2), np.uint8)
    merge = cv2.dilate(merge, kernel, iterations=1)
    # merge = cv2.GaussianBlur(merge, (1,1), 0)
    # cv2.imshow("ks",merge)
    # cv2.waitKey()
    # cv_draw_max_rect(table_path)
    contours, _ = cv2.findContours(merge, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # 得到原始过滤坐标
    list_result = []
    # 统一化x,y，记录x,y坐标
    x_set, y_set = [0], [0]
    x_result, y_result = [], []
    # 过滤坐标
    x_y_set = set()
    # 排序过滤之后的最终坐标
    x_y_list = []
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        
        # 统一化 x, y，避免因像素偏差导致坐标不一致
        x1 = _snap_coord(x, x_set, CVConfig.pixel_fault_tolerance)
        xw = _snap_coord(x + w, x_set, CVConfig.pixel_fault_tolerance)
        y1 = _snap_coord(y, y_set, CVConfig.pixel_fault_tolerance)
        yh = _snap_coord(y + h, y_set, CVConfig.pixel_fault_tolerance)
        
        # 构建坐标
        rect_points = [(x1, y1), (x1, yh), (xw, y1), (xw, yh)]
        # 构建set可识别的坐标
        coord_tuple = (x1, y1, xw, yh)
        
        if coord_tuple not in x_y_set:
            # 过滤像素过小的图像
            area = abs(y1 - yh) * abs(x1 - xw)
            if area > CVConfig.min_size:
                x_y_set.add(coord_tuple)
                # 构建可排序的坐标
                x_y_list.append((area, x1, rect_points, xw, y1, yh))
                list_result.append(rect_points)
                x_result.extend([x1, xw])
                y_result.extend([y1, yh])
                
    # 统计x, y出现的次数
    x_dict = collections.Counter(x_result)
    y_dict = collections.Counter(y_result)
    x_y_list = sorted(x_y_list, key=lambda item: (item[0], item[2][0]), reverse=True)
    
    # 统计节点：计算每个表格内部包含多少个子表格
    def get_inside_counts(coord_list):
        counts = []
        length = len(coord_list)
        for i in range(length):
            number = sum(1 for u in range(i + 1, length) if is_inside(coord_list[i][2], coord_list[u][2]))
            counts.append((coord_list[i][0], coord_list[i][2], number))
        return counts
        
    inside_counts = get_inside_counts(x_y_list)
    print({'counterls': inside_counts})
    
    # 中间变量及过滤逻辑
    if len(x_y_list) > 1:
        x_y_remove = []
        for j, item in enumerate(x_y_list):
            if j == 0 and inside_counts[0][2] > 0 and inside_counts[1][2] == 0:
                continue
            
            x1_count = x_dict.get(item[1], 0)
            xw_count = x_dict.get(item[3], 0)
            y1_count = y_dict.get(item[4], 0)
            yh_count = y_dict.get(item[5], 0)
            
            if (x1_count == 1 or xw_count == 1) and (y1_count == 1 or yh_count == 1):
                x_y_remove.append(j)
                
        # 散列式表单情况
        if len(x_y_remove) < len(x_y_list):
            x_y_list = rm_list(x_y_list, x_y_remove)
        else:
            lens = len(x_y_list) - 1
            for u in range(len(x_y_list) - 1):
                if not is_inside(x_y_list[u][2], x_y_list[u + 1][2]):
                    lens = u
                    break
            x_y_list = [x_y_list[lens]]
            
        # 计算小表格是否在主表格里或者是已存在于原表格
        if len(x_y_list) > 1:
            x_y_remove = [j for j in range(len(x_y_list)) if not is_inside(x_y_list[0][2], x_y_list[j][2])]
            x_y_list = rm_list(x_y_list, x_y_remove)
            
        # # 二次过滤：(原代码注释保留)
        # if len(x_y_list)>1:
        #     ...
            
    print({'x_y_list': x_y_list})
    return x_y_list

def get_correct(path, save_path):
    gray, image = cv_gray_path(path)
    # 腐蚀、膨胀
    kernel = np.ones((5, 5), np.uint8)
    erode_img = cv2.erode(gray, kernel)
    ero_dil = cv2.dilate(erode_img, kernel)
    # showAndWaitKey("eroDil",eroDil)
    
    # 边缘检测
    canny = cv2.Canny(ero_dil, 50, 150)
    # showAndWaitKey("canny",canny)
    
    # 霍夫变换得到线条
    lines = cv2.HoughLinesP(canny, 0.8, np.pi / 180, 90, minLineLength=100, maxLineGap=10)
    
    # 画出线条并计算斜率
    slopes = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x1 != x2:
                slopes.append(float((y1 - y2) / (x1 - x2)))
                
    # 斜率
    """
    计算角度,因为x轴向右，y轴向下，所有计算的斜率是常规下斜率的相反数，我们就用这个斜率（旋转角度）进行旋转
    """
    median_slope = analyze_data(slopes)
    if median_slope != 0.0:
        angle = np.degrees(math.atan(median_slope))
        print(f'旋转的角度为：{angle}')
        """
        旋转角度大于0，则逆时针旋转，否则顺时针旋转
        """
        rotate_img = rotate(image, angle)
        cv2.imwrite(save_path, rotate_img)
        return True
    return False
        
def cv_end_save(x_y_list, image, coord, main):
    cv_spilt_save(x_y_list, image, coord)
    if not x_y_list:
        return
        
    x_y_list = sorted(x_y_list, key=lambda x: x[2][0][1])
    x, y, w, h = cv2.boundingRect(np.array(x_y_list[0][2]))
    
    if y <= 20:
        for i in range(1, len(x_y_list)):
            x, y, w, h = cv2.boundingRect(np.array(x_y_list[i][2]))
            if y >= 20:
                break
                
    roi = image[y:y+h, x:x+w]
    main_name = f"_{y}_{y+h}_{x}_{x+w}_main.jpg"
    cv2.imwrite(os.path.join(main, main_name), roi)
    
    # 创建一个与原始图像大小相同的掩膜并在掩膜上绘制矩形，进行反转
    mask = np.zeros_like(image)
    cv2.rectangle(mask, (x, y), (x + w, y + h), (255, 255, 255), -1)
    mask = cv2.bitwise_not(mask)
    # 获取除给定坐标以外的图像
    roi_not = cv2.bitwise_and(image, mask)
    cv2.imwrite(os.path.join(main, "_other_coordinate_not.jpg"), roi_not)

    height, width = image.shape[:2]
    if y > 0:
        roi_h = image[0:y, 0:width]
        area = y * width
        if area > CVConfig.min_size / 2:
            head_name = f"0_{y}_{x}_{x+w}_{area}_head.jpg"
            cv2.imwrite(os.path.join(coord, head_name), roi_h)
            
    # if (height-y-h)>0: (原代码注释保留)
    # ...

def cv_spilt_save(x_y_list, image, path):
    if not x_y_list:
        print()
        return
        
    if len(x_y_list) == 1:
        x, y, w, h = cv2.boundingRect(np.array(x_y_list[0][2]))
        roi = image[y:y+h, x:x+w]
        area = h * w
        name = f"{y}_{y+h}_{x}_{x+w}_{area}_coordinate.jpg"
        cv2.imwrite(os.path.join(path, name), roi)
    else:
        for j in range(1, len(x_y_list)):
            pts = x_y_list[j][2]
            xt, yt = pts[0][0], pts[0][1]
            xwt, yht = pts[3][0], pts[3][1]
            
            x, y, w, h = cv2.boundingRect(np.array(pts))
            roi = image[y:y+h, x:x+w]
            area = h * w
            
            if area > CVConfig.min_size:
                name = f"{yt}_{yht}_{xt}_{xwt}_{area}_coordinate.jpg"
                cv2.imwrite(os.path.join(path, name), roi)

def cache_save_cv_gray(cache, path):
    gray, image = cv_gray_path(path)
    cv2.imwrite(cache, gray)
    return cv2.imread(cache, 1)
        
def cv_build(uuid, name):
    root, coord, main, other, txt_result = fiul.uuid_save_mkdirs(uuid)
    save_rotate = fiul.uuid_save_rotate_img(uuid)
    target_path = os.path.join(root, name)
    
    # 初始化
    # cv_draw_max_rect(target_path)
    target_path = cv_init_img(target_path, uuid)
    
    # 调整图片
    if get_correct(target_path, save_rotate):
        target_path = save_rotate
        
    # 获取灰度图片并二值化
    gray, image = cv_gray_path(target_path)
    binary = cv_adaptiveThreshold(gray)
    
    # 获取轮廓线
    vertical_lines, horizontal_lines = cv_x_y(other, binary)
    # 绘制表格
    merge, table_path = cv_table(other, vertical_lines, horizontal_lines)
    
    # 分隔表格和根据容错率优化， 得到每一个表格的轮廓
    x_y_list = cv_core(merge, table_path)
    # #清空表格线 (原代码注释保留)
    # image = clear_border_lines(image,contours,save_line)
    
    # 分隔图片
    cv_end_save(x_y_list, image, coord, main)
    
    return coord, txt_result

def cv_two_split_build(uuid, path, x_e=10, y_e=1):
    pp = fiul.uuid_cache_root(uuid)
    img_name = fiul.get_one_name(path)
    split_path = fiul.uuid_cache_spilt_path(uuid, img_name)
    write_path = fiul.uuid_cache_split_write(uuid, img_name)
    
    image = cv2.imread(path, 1)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv_adaptiveThreshold(gray)
    
    vertical_lines, horizontal_lines = cv_x_y(pp + "/", binary, x_eroded=x_e, y_eroded=y_e)
    x_set = [0]
    ys, xs = np.where(horizontal_lines > 0)
    
    for i in xs:
        _snap_coord(i, x_set, CVConfig.pixel_fault_tolerance)
            
    x_set = sorted(list(set(x_set)))[1:-1]
    height, width = image.shape[:2]
    
    if x_set:
        roi_h = image[0:height, 0:x_set[0]]
        area_h = height * x_set[0]
        cv2.imwrite(os.path.join(split_path, f"0_{height}_0_{x_set[0]}_{area_h}_coordinate.jpg"), roi_h)
        
        ed = width - x_set[-1]
        roi_e = image[0:height, x_set[-1]:width]
        area_e = height * ed
        cv2.imwrite(os.path.join(split_path, f"0_{height}_{x_set[-1]}_{width}_{area_e}_coordinate.jpg"), roi_e)
        
        for i in range(len(x_set) - 1):
            roi = image[0:height, x_set[i]:x_set[i+1]]
            ed = x_set[i+1] - x_set[i]
            cv2.imwrite(os.path.join(split_path, f"0_{height}_{x_set[i]}_{x_set[i+1]}_{ed}_coordinate.jpg"), roi)
            
    return split_path, write_path

def get_transform(input_path, output_path):
    # 读取原始图片
    gray, image = cv_gray_path(input_path)
    gray = cv_adaptiveThreshold(gray)
    # 高斯模糊
    # gray = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 执行轮廓检测
    contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False
        
    # 筛选最大的封闭边框
    max_contour = max(contours, key=cv2.contourArea)
    # cv2.drawContours(src, [max_contour], -1, (0, 255, 0), thickness=2)
    
    # 获取轮廓的外接矩形与四个角点
    x, y, w, h = cv2.boundingRect(max_contour)
    box = np.array([[x, y], [x, y + h], [x + w, y], [x + w, y + h]], dtype=np.int32)
    
    # 寻找最小面积矩形
    # rect = cv2.minAreaRect(max_contour)
    # box = np.int0(cv2.boxPoints(rect))
    # cv2.drawContours(src, [box], -1, (255, 255, 0), thickness=2)
    
    # 获取轮廓的坐标点，近似轮廓为四边形
    epsilon = 0.02 * cv2.arcLength(max_contour, True)
    approx = cv2.approxPolyDP(max_contour, epsilon, True)
    # 多次近似
    approx = mush_approx(approx)
    
    # 获取轮廓的四个端点坐标
    points = approx.squeeze().tolist()
    
    center_x, center_y = image.shape[1] // 2, image.shape[0] // 2
    
    # 定义排序规则函数
    def contour_sort_rule(point):
        px, py = point
        # 根据越上越左、越上越右、越下越左、越下越右的顺序进行排序
        if px <= center_x and py <= center_y: return 1  # 越左越上
        elif px > center_x and py <= center_y: return 2 # 越右越上
        elif px <= center_x and py > center_y: return 3 # 越左越下
        else: return 4                                  # 越右越下
            
    # 无法近似四边形则停止变换，直接返回
    if len(points) > 4:
        return False
        
    # 根据排序规则对坐标点进行排序
    sorted_points = sorted(points, key=contour_sort_rule)
    sorted_box = sorted(box.tolist(), key=contour_sort_rule)
    
    # 打印排序后的坐标点
    print("透视变换----")
    x_set, y_set = get_x_y_set(sorted_points)
    if len(set(x_set)) == 2 and len(set(y_set)) == 2:
        return False
    
    # 组合角点
    res = np.float32(sorted_points[:4])
    dst = np.float32(sorted_box[:4])
    # dst = np.float32([[0, 0], [5000 ,0], [0, 5000], [5000, 5000]])
    
    # 获取透视变换矩阵，进行转换
    M = cv2.getPerspectiveTransform(res, dst)
    src = cv2.warpPerspective(image, M, (image.shape[1], image.shape[0]))
    
    if check_trf_success(src):
        cv2.imwrite(output_path, src)
        return True
    return False

def get_compress(input_path, output_path, target_max_size):
    # 读取原始图片
    image = cv2.imread(input_path)
    if image is None:
        return False
        
    # 获取原始图片的宽度和高度
    height, width = image.shape[:2]
    original_size = os.path.getsize(input_path)

    # 如果原始图片已经小于等于目标大小，则直接保存原始图片
    if original_size < target_max_size:
        return False
    
    # 计算原始图片的大小
    img_area = width * height
    # 计算压缩比例
    compression_ratio = (target_max_size * 1.75 / img_area) ** 0.5
    
    if compression_ratio >= 1:
        return False

    # 计算压缩后的宽度和高度
    compressed_width = int(width * compression_ratio)
    compressed_height = int(height * compression_ratio)

    # 使用 INTER_AREA 进行压缩。说明：相较于 INTER_CUBIC，INTER_AREA 更加适合图像的下采样压缩操作，有效减少摩尔纹。
    compressed_image = cv2.resize(image, (compressed_width, compressed_height), interpolation=cv2.INTER_AREA)
    # 保存压缩后的图片
    cv2.imwrite(output_path, compressed_image)
    return True

def expand_cv_img(src_path):
    '''
    扩展像素,ocr提高识别度
    '''
    file_dir = os.path.dirname(src_path)
    filename = os.path.basename(src_path)
    name, ext = os.path.splitext(filename)
    
    # 读取原始图像 (原代码中部分屏蔽逻辑保留说明)
    # ...获取原始图像宽度高度等计算扩展量的被注释代码...
    
    img = cv2.imread(src_path)
    if img is None:
        return src_path
        
    top = 6  # 顶部边框大小
    bottom = 14  # 底部边框大小
    left = 10 # 左侧边框大小
    right = 10  # 右侧边框大小
    
    # 使用cv2.copyMakeBorder()函数扩展图像，创建一个新的扩展后大小的空白图像
    expanded_img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    tmp_path = os.path.join(file_dir, f"_tmp{ext}")
    cv2.imwrite(tmp_path, expanded_img)
    return tmp_path

def check_trf_success(image):
    # 再次检测，执行轮廓检测
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv_adaptiveThreshold(gray)
    
    contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False
        
    # 筛选最大的封闭边框
    max_contour = max(contours, key=cv2.contourArea)
    epsilon = 0.02 * cv2.arcLength(max_contour, True)
    approx = cv2.approxPolyDP(max_contour, epsilon, True)
    
    # 多次近似
    approx = mush_approx(approx)
    
    # 获取轮廓的四个端点坐标
    points = approx.squeeze().tolist()
    # 无法近似四边形则停止变换，直接返回
    if len(points) > 4:
        return False
        
    print("透视变换check----")
    x_set, y_set = get_x_y_set(points)
    if len(set(x_set)) != 2 and len(set(y_set)) != 2:
        return False
    return True

def mush_approx(approx):
    """
    多次近似。
    说明：使用循环精简了原先冗长的两次重复 cv2.convexHull 判断逻辑。
    """
    for _ in range(2):
        if len(approx) > 4:
            hull = cv2.convexHull(approx)
            approx = hull if len(hull) == 4 else cv2.convexHull(hull)
    return approx
            
def get_x_y_set(points):
    x_set, y_set = [], []
    for x, y in points:
        print(f"Point: ({x}, {y})")
        _snap_coord(y, y_set, CVConfig.pixel_fault_tolerance)
        _snap_coord(x, x_set, CVConfig.pixel_fault_tolerance)
    return x_set, y_set

def clear_border_lines(image, contours, save_line):
    for i in contours:
        cv2.drawContours(image, [i], 0, (255, 255, 255), 2)
    cv2.imwrite(save_line, image)
    _, image = cv_gray_path(save_line)
    return image

def cv_draw_max_rect(src_path):
    gray, image = cv_gray_path(src_path)
    binary = cv_adaptiveThreshold(gray)
    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    max_contour = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(max_contour)
    box = np.int0(cv2.boxPoints(rect))
    
    center_x, center_y = image.shape[1] // 2, image.shape[0] // 2
    
    def contour_sort_rule(point):
        px, py = point
        # 根据越上越左、越上越右、越下越左、越下越右的顺序进行排序
        if px <= center_x and py <= center_y: return 1
        elif px > center_x and py <= center_y: return 2
        elif px <= center_x and py > center_y: return 3
        else: return 4
            
    # 根据排序规则对坐标点进行排序
    box = sorted(box, key=contour_sort_rule)
    y1, x1 = box[0]
    y2, x2 = box[1]
    y4, x4 = box[3]
    
    cv2.line(image, (y1, x1 + 5), (y2 + 20, x2 + 5), (0, 255, 0), thickness=2)
    cv2.line(image, (y1, x1 + 5), (y4, x1 + 100), (0, 255, 0), thickness=2)
    cv2.imwrite(src_path, image)

def cv_init_img(src_path, uuid, is_compress=True):
    '''
    初始化优化图片，使用压缩和透视变换
    '''
    save_compress = fiul.uuid_save_compress_img(uuid)
    save_transform = fiul.uuid_save_transform_img(uuid)
    target = src_path
    
    # 压缩图片
    if is_compress and get_compress(target, save_compress, CVConfig.cv_compress):
        target = save_compress
        
    # 透视转化
    if get_transform(target, save_transform):
        target = save_transform
        
    return target

def cv_sharpening(img_path):
    # 应用锐化内核
    img = cv2.imread(img_path)
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    img = cv2.filter2D(img, -1, kernel)
    cv2.imwrite(img_path, img)
    return img_path

def cv_init_video(video_path, frame_path):
    img_list = []
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)  # 获取视频帧率
    duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps) if fps else 0 # 获取视频时长（秒）
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    if duration < 1:
        return img_list
        
    frame_name = set(int(i * fps) for i in range(1, duration + 1))
    frame_list = []  # 存储帧的列表
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if frame_count in frame_name:
            frame = frame[height - height // 6:, width // 8 : width - width // 8, :]
            frame_list.append(frame)
            
    cap.release()
    
    for i in range(len(frame_list) - 1):
        gray1 = cv2.cvtColor(frame_list[i], cv2.COLOR_BGR2GRAY)
        _, gray1 = cv2.threshold(gray1, 215, 255, cv2.THRESH_BINARY)
        
        gray2 = cv2.cvtColor(frame_list[i + 1], cv2.COLOR_BGR2GRAY)
        _, gray2 = cv2.threshold(gray2, 215, 255, cv2.THRESH_BINARY)
        
        if cal_stderr(gray1, gray2) > 1.5:
            path = os.path.join(frame_path, f"{i}_frame.jpg")
            img_list.append(path)
            cv2.imwrite(path, frame_list[i])
            
    return img_list

def cal_stderr(img, imgo=None):
    if imgo is None:
        return float((img ** 2).sum() / img.size * 100)
    else:
        return float(((img - imgo) ** 2).sum() / img.size * 100)