"""
-------------------------------------------------
    File Name:     geometry_util
    Description:   坐标与矩形计算（纯计算，不依赖 OpenCV）
    date:          2023.08
-------------------------------------------------
    Change Activity: 2023.08
-------------------------------------------------
"""


def calculate_bounding_box(rectangles):
    '''
    求一组矩形的最小外接矩形。

    坐标统一用字符串返回，与切图文件名的命名保持一致。
    rectangles 为空时返回全零矩形，避免调用方拿到 inf 后在 int() 处崩溃。
    '''
    if not rectangles:
        return [['0', '0'], ['0', '0'], ['0', '0'], ['0', '0']]

    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')

    for rectangle in rectangles:
        for point in rectangle:
            x, y = map(int, point)
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    return [[str(min_x), str(min_y)], [str(max_x), str(min_y)],
            [str(max_x), str(max_y)], [str(min_x), str(max_y)]]


def calculate_area(coordinates):
    '''
    矩形面积，取左上与右下两点计算。
    '''
    x1, y1 = map(int, coordinates[0])
    x2, y2 = map(int, coordinates[2])
    return (x2 - x1) * (y2 - y1)


def expand_coordinates(coordinate, max_x_range, max_y_range, x_left, x_right, y_top, y_tail):
    '''
    把矩形向四周外扩指定像素，并限制在图片范围内。参数顺序为 左、右、上、下。
    '''
    x1, y1 = map(int, coordinate[0])
    x2, y2 = map(int, coordinate[2])

    expanded_x1 = max(x1 - x_left, 0)
    expanded_y1 = max(y1 - y_top, 0)
    expanded_x2 = min(x2 + x_right, max_x_range)
    expanded_y2 = min(y2 + y_tail, max_y_range)

    return [[str(expanded_x1), str(expanded_y1)], [str(expanded_x2), str(expanded_y2)]]


def is_inside(src, dst):
    '''
    判断 dst 矩形是否完全落在 src 矩形内部（含边界）。
    坐标可能是字符串（来自文件名）或整数（来自 OpenCV），统一转 int 再比较。
    '''
    src_x = [int(p[0]) for p in src]
    src_y = [int(p[1]) for p in src]
    dst_x = [int(p[0]) for p in dst]
    dst_y = [int(p[1]) for p in dst]
    return (max(dst_x) <= max(src_x) and min(dst_x) >= min(src_x) and
            max(dst_y) <= max(src_y) and min(dst_y) >= min(src_y))
