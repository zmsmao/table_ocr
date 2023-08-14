class ModelConfig:
    #paddleocr 推理
    model_det_path='./model/det/ch/ch_PP-OCRv4_det_infer'
    #paddleocr 识别
    model_rec_path='./model/rec/ch/ch_PP-OCRv4_rec_infer'
    #文本方向分类模型
    cls_model_dir = './model/cls/ch_ppocr_mobile_v2.0_cls_infer'
    #安装gpu版本才开启
    is_use_gpu = False
    #paddleocr 语言支持
    lang='ch'