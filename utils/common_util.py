"""
-------------------------------------------------
    File Name:     common_util
    Description:   通用工具：文件类型判断、uuid、文本清洗与数字提取
    date:          2023.08
-------------------------------------------------
    Change Activity: 2023.08
-------------------------------------------------
"""
import re
import uuid

IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg', 'webp',
                    'tiff', 'ico', 'jfif', 'pjpeg', 'pjp', 'heic',
                    'bpg', 'raw', 'exif'}
VIDEO_EXTENSIONS = {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'mpeg',
                    '3gp', 'm4v', 'divx', 'vob', 'ogv', 'ogg', 'swf',
                    'asf', 'rm', 'rmvb', 'm2ts', 'mts', 'ts', 'webm',
                    'mpg', 'mp2', 'mpe', 'mpv', 'm2v', 'm4p', 'm4b',
                    'm4r', 'm4a', 'aac', 'flac', 'wav', 'opus'}


def get_file_type(filename):
    '''
    1 图片，2 视频，0 不支持。取不到扩展名时按 0 处理。
    '''
    parts = filename.rsplit('.', 1)
    if len(parts) < 2:
        return 0
    extension = parts[1].lower()
    if extension in IMAGE_EXTENSIONS:
        return 1
    if extension in VIDEO_EXTENSIONS:
        return 2
    return 0


def generate_unique_id():
    '''
    生成 10 位字母数字 id，作为一次请求的文件隔离目录名。
    '''
    uid = uuid.uuid4().hex
    uid = ''.join([c for c in uid if c.isalnum()])
    return uid[:10]


def filter_text(text):
    '''
    只保留中文、字母、数字，去掉所有标点与空白。
    注意：过滤后文本与原文长度不一致，做下标定位时要用原文。
    '''
    pattern = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9]+')
    return pattern.sub('', text)


def filter_chinese_punctuation(input_str):
    '''
    过滤中文符号，保留中文、英文、数字与英文符号。
    '''
    pattern = re.compile(r'[\u4E00-\u9FA5a-zA-Z0-9\u0021-\u007E]+')
    return ''.join(pattern.findall(input_str))


def find_substring_positions(string, substring):
    '''
    返回子串在字符串中的 (起始下标, 结束下标)，未找到返回 (-1, -1)。
    '''
    start_index = string.find(substring)
    if start_index == -1:
        return -1, -1
    return start_index, start_index + len(substring) - 1


def extract_numbers(text):
    '''
    提取文本中的全部数字，返回字符串列表。
    '''
    return re.compile(r'\d+').findall(text)


def filter_numbers(text):
    '''
    去掉文本中的数字，只保留其余部分。
    '''
    return re.sub(r'\d+', '', text)


def extract_text_obj(data):
    '''
    把 PaddleOCR 的返回结果整理成 [坐标, 文本, 置信度] 列表。
    坐标统一转成字符串，与切图文件名的坐标体系保持一致。
    '''
    result = []
    data = data[0]
    for item in data:
        coordinates = item[0]
        text, confidence = item[1]
        int_coordinates = [[str(int(point[0])), str(int(point[1]))] for point in coordinates]
        result.append([int_coordinates, text, confidence])
    return result
