
def calculate_bounding_box(rectangles):
    '''
    寻找最大矩阵节点
    '''
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

    return [[str(min_x), str(min_y)], [str(max_x), str(min_y)], [str(max_x), str(max_y)], [str(min_x), str(max_y)]]


def find_source_coordinates(target_coordinate, source_coordinate):
    '''
    矩阵匹配
    '''
    source_area = calculate_area(source_coordinate)
    intersection_area = calculate_intersection_area(target_coordinate, source_coordinate)
    if intersection_area / source_area >= 0.9:
        return source_coordinate
    return []
    


def calculate_area(coordinates):
    x1, y1 = map(int, coordinates[0])
    x2, y2 = map(int, coordinates[2])

    return (x2 - x1) * (y2 - y1)


def calculate_intersection_area(target_coordinates, source_coordinates):
    target_x1, target_y1 = map(int, target_coordinates[0])
    target_x2, target_y2 = map(int, target_coordinates[2])

    source_x1, source_y1 = map(int, source_coordinates[0])
    source_x2, source_y2 = map(int, source_coordinates[2])

    intersection_x1 = max(target_x1, source_x1)
    intersection_y1 = max(target_y1, source_y1)
    intersection_x2 = min(target_x2, source_x2)
    intersection_y2 = min(target_y2, source_y2)

    width = intersection_x2 - intersection_x1
    height = intersection_y2 - intersection_y1

    if width > 0 and height > 0:
        return width * height
    else:
        return 0
    

def expand_coordinates(coordinate, max_x_range, max_y_range, x_left,x_right, y_top,y_tail):
    '''
    扩展矩阵
    '''
    x1, y1 = map(int, coordinate[0])
    x2, y2 = map(int, coordinate[2])

    expanded_x1 = max(x1 - x_left, 0)
    expanded_y1 = max(y1 - y_top, 0)
    expanded_x2 = min(x2 + x_right, max_x_range)
    expanded_y2 = min(y2 + y_tail, max_y_range)

    return [[str(expanded_x1), str(expanded_y1)], [str(expanded_x2), str(expanded_y2)]]
