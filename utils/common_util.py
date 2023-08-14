import uuid
from config.file_config import FileConfig
import re


def generate_unique_id():
    """
    生成长度为8的只包含字母和数字的唯一ID
    """
    uid = uuid.uuid4().hex  # 生成UUID
    uid = ''.join([c for c in uid if c.isalnum()])  # 过滤非字母和数字字符
    uid = uid[:10]  # 截取前8个字符
    return uid

def average_split_list(lst, n):
    """
    将list平均分为n组，无法分组的则放在最后一组即可。
    :param lst: 要分组的list。
    :param n: 分成几组。
    :return: 分组后的结果，一个嵌套的list。
    """
    # 计算每组元素个数和剩余元素个数
    quotient, remainder = divmod(len(lst), n)
    
    # 将list分成n组
    groups = [lst[i * quotient:(i + 1) * quotient] for i in range(n)]
    
    # 将剩余元素放入最后一组
    if remainder > 0:
        groups[-1] += lst[n * quotient:]
    
    return groups

def extract_first_element(data):
    result = ""
    for k in data:
        result += str(k[0])+"  "+str(k[1])+ "\n"
    return result

def filter_text(text):
    pattern = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9]+') # 匹配不是中文字符、字母和数字的字符集合
    result = pattern.sub('', text) # 将匹配结果替换为空字符串
    return result

def extract_text_coordinates(data):
    result = []
    for i in range(len(data[0])):
        coordinates = [(int(x), int(y)) for x, y in data[0][i]]
        text = data[1][i][0]
        rate = data[1][i][1]
        result.append([text,rate, coordinates])
    return result

def extract_text_obj(data):
    result = []
    data=data[0]
    for item in data:
        coordinates = item[0]
        text, confidence = item[1]
        # Convert coordinates to int
        int_coordinates = [[str(int(point[0])), str(int(point[1]))] for point in coordinates]
        # Append processed data to result
        result.append([int_coordinates, text, confidence])
    return result

def find_substring_positions(string, substring):
    if len(substring) == 1:
        start_index = string.find(substring)
        end_index = start_index
    else:
        start_index = string.find(substring)
        if start_index == -1:
            end_index = -1
        else:
            end_index = start_index + len(substring) - 1
    return start_index, end_index


def filter_chinese_punctuation(input_str):
    """过滤掉中文符号，保留数字，英文，英文符号，中文"""
    # 使用正则表达式匹配中文字符和英文字符，数字，英文符号
    # \u4E00-\u9FA5 匹配所有中文字符
    # a-zA-Z0-9 匹配所有英文字符和数字
    # \u0021-\u007E 匹配所有英文符号
    pattern = re.compile(r'[\u4E00-\u9FA5a-zA-Z0-9\u0021-\u007E]+')
    # 使用正则表达式匹配结果
    matches = pattern.findall(input_str)
    # 将所有匹配结果连接成一个字符串
    return ''.join(matches)

def filter_non_chinese(text):
    """
    过滤文本中的中文符号，保留其他文本
    """
    non_chinese_pattern = re.compile(r'[^\u4e00-\u9fa5]')
    non_chinese_text = non_chinese_pattern.sub('', text)
    return non_chinese_text

def similarity(s1, s2):
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return 1 - dp[m][n] / max(m, n)

def extract_numbers(text):
    """
    从文本字符串中提取数字。
    """
    # 使用正则表达式来匹配数字
    pattern = re.compile(r'\d+')
    # 在文本中查找匹配的数字
    matches = pattern.findall(text)
    # 将找到的数字作为字符串返回
    return matches

def filter_numbers(text):
    """
    从文本字符串中过滤掉所有数字，只保留文本部分。
    """
    # 使用正则表达式将所有数字替换为空字符串
    pattern = re.compile(r'\d+')
    filtered_text = re.sub(pattern, '', text)
    # 返回过滤后的文本
    return filtered_text