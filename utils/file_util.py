"""
-------------------------------------------------
    File Name:     file_util
    Description:   文件读写与 uuid 目录体系
                   每次请求一个 uuid，图片统一落在 io/save_path/{uuid} 下
    date:          2023.08
-------------------------------------------------
    Change Activity: 2023.08
-------------------------------------------------
"""
import base64
import logging
import os
import shutil

from config.file_config import FileConfig

logger = logging.getLogger(__name__)

file_config = FileConfig()


def get_extension_file(file_name):
    '''
    取文件扩展名，包含点号，如 .jpg
    '''
    return os.path.splitext(file_name)[1]


def save_image(base64_data, save_path):
    '''
    把 base64 图片数据落盘。
    '''
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    try:
        with open(save_path, 'wb') as f:
            f.write(base64.b64decode(base64_data))
        return True
    except Exception as e:
        logger.error('保存图片失败 %s: %s', save_path, e)
        return False


def write_result(result_text, output_path):
    '''
    把识别结果写成 txt，便于排查。
    '''
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result_text)


def dir_delete(dir_path):
    '''
    删除目录及其内容。目录不存在时静默返回。
    '''
    if not os.path.isdir(dir_path):
        return
    try:
        shutil.rmtree(dir_path)
    except OSError as e:
        logger.error('删除目录失败 %s: %s', dir_path, e)


def list_one_dir(path, coord_img_path):
    '''
    把 path 下的文件（不含子目录）追加进 coord_img_path。
    '''
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if not os.path.isdir(file_path):
            coord_img_path.append(file_path)


def get_file_name(coord_img_path):
    '''
    取文件名列表（不含扩展名）。
    '''
    return [os.path.basename(name).split('.')[0] for name in coord_img_path]


def get_one_name(path):
    '''
    取单个文件名（不含扩展名）。
    '''
    return os.path.basename(path).split('.')[0]


def sort_file_path(coord_img_path):
    '''
    按切图文件名的第一段（y 坐标）升序排序，保证从上往下处理。
    '''
    res = [(int(os.path.basename(i).split('.')[0].split('_')[0]), i) for i in coord_img_path]
    return [item[1] for item in sorted(res, key=lambda x: x[0])]


def current_path():
    '''
    当前文件绝对路径。
    '''
    return os.path.abspath(__file__)


def parent_path():
    '''
    项目根目录。utils 位于根目录下，因此取上两级目录。
    '''
    return os.path.dirname(os.path.dirname(current_path()))


def uuid_save_root(uuid):
    '''
    io/save_path/{uuid}
    '''
    root = parent_path() + "/" + file_config.save_path + "/" + uuid
    os.makedirs(root, exist_ok=True)
    return root


def uuid_cache_root(uuid):
    '''
    cache/{uuid}
    '''
    return parent_path() + "/" + file_config.img_cache + "/" + uuid


def uuid_save_mkdirs(uuid):
    '''
    建好本次请求需要的全部子目录，返回 (root, coord, main, other, txt_result)。
    '''
    root = uuid_save_root(uuid)
    coord = root + "/" + file_config.coord
    main = root + "/" + file_config.main
    other = root + "/" + file_config.other
    txt_result = root + "/" + file_config.txt_result
    for path in (coord, main, other, txt_result):
        os.makedirs(path, exist_ok=True)
    return root, coord, main, other, txt_result


def uuid_save_mkdir_video_frame(uuid):
    '''
    视频抽帧存放目录。
    '''
    frame = uuid_save_root(uuid) + "/" + file_config.frame
    os.makedirs(frame, exist_ok=True)
    return frame


def uuid_save_video_img(uuid, suffix):
    '''
    上传的视频/图片落盘路径。
    '''
    root = uuid_save_root(uuid) + "/"
    di = root + file_config.cv_video_img_name + suffix
    os.makedirs(os.path.dirname(root), exist_ok=True)
    return di


def uuid_save_web_file(file, uuid):
    '''
    保存前端上传的文件，返回落盘路径。
    '''
    suffix = get_extension_file(file_name=file.filename)
    di = uuid_save_video_img(uuid, suffix)
    file.save(di)
    return di


def uuid_save_rotate_img(uuid):
    '''
    倾斜矫正后的图片路径。
    '''
    return uuid_save_root(uuid) + "/" + file_config.cv_rotate_img


def uuid_save_compress_img(uuid):
    '''
    压缩后的图片路径。
    '''
    return uuid_save_root(uuid) + "/" + file_config.cv_compress_img


def uuid_save_transform_img(uuid):
    '''
    透视变换后的图片路径。
    '''
    return uuid_save_root(uuid) + "/" + file_config.cv_transform_img
