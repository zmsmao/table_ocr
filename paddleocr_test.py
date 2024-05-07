from paddleocr import PPStructure,draw_structure_result,PaddleOCR
from config.model_config import ModelConfig
import cv2
import os
import numpy as np

table_engine =PPStructure(det_model_dir=ModelConfig.model_det_path,
                            rec_model_dir=ModelConfig.model_rec_path,
                            use_gpu= ModelConfig.is_use_gpu,
                            cls_model_dir=ModelConfig.cls_model_dir,
                            lang=ModelConfig.lang,use_angle_cls=True,
                            layout_model_dir=".\model\layout\ppyolov2_r50vd_dcn_365e_publaynet")
# def expand_cv_img(src_path):
#     '''
#     扩展像素,ocr提高识别度
#     '''
#     file_dir =os.path.dirname(src_path)
#     filename = os.path.basename(src_path)
#     s=filename.split('.')[0]
#     fx = filename.split('.')[1]
#     # # 读取原始图像
#     # img = cv2.imread(src_path)
#     # # 获取原始图像的宽度和高度
#     # original_height, original_width = img.shape[:2]
#     # # 扩展后的边框大小
#     # border_size = 10
#     # # 计算扩展后的宽度和高度
#     # expanded_width = original_width + 2 * border_size
#     # expanded_height = original_height + 2 * border_size
#     # # 创建扩展后的图像
#     # expanded_img = cv2.resize(img, (expanded_width, expanded_height))
    
#     # # 读取原始图像
#     # expansion_factor = 1.21
#     # original_image = cv2.imread(src_path)

#     # # 获取原始图像的宽度和高度
#     # original_height, original_width = original_image.shape[:2]

#     # # 计算扩展后的图像的目标宽度和高度
#     # target_width = int(original_width * expansion_factor)
#     # target_height = int(original_height * expansion_factor)

#     # # 计算水平和垂直的填充量
#     # horizontal_padding = int((target_width - original_width) / 2)
#     # vertical_padding = int((target_height - original_height) / 2)

#     # # 创建一个新的扩展后大小的空白图像
#     # expanded_img = cv2.copyMakeBorder(original_image, vertical_padding, vertical_padding,
#     #                                     horizontal_padding, horizontal_padding, cv2.BORDER_CONSTANT,value=[255,255,255])
#     img = cv2.imread(src_path)
#     # height, width, channels = img.shape
#     # img=img[1:height-1,1:width-1]
#     top = 6  # 顶部边框大小
#     bottom = 14  # 底部边框大小
#     left = 10 # 左侧边框大小
#     right = 10  # 右侧边框大小
#     # 使用cv2.copyMakeBorder()函数扩展图像
#     expanded_img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[255, 255, 255])

#     tmp = "tmp."+fx
#     cv2.imwrite(tmp,expanded_img)
#     return tmp


img_path = 'io\input_path\\real\现场拍照图片\IMG_20231205_120650.jpg'
res=table_engine(img_path);
print(res)

from PIL import Image
font_path = './doc/fonts/simfang.ttf' # PaddleOCR下提供字体包
image = Image.open(img_path).convert('RGB')
im_show = draw_structure_result(image, res,font_path=font_path)
im_show = Image.fromarray(im_show)
im_show.save('result.jpg')
