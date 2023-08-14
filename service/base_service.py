import json
import utils.common_util as comm
import utils.file_util as fiul
import utils.cv_util as cvut
from domain.ocr_result_common import OCRCommon,OCRAll
from config.file_config import FileConfig
from config.model_config import ModelConfig
from config.thread_config import ThreadConfig
from paddleocr import PaddleOCR
from rules.base_rules import rules


def common(data,uuid):
    # det_model_dir=ModelConfig.model_det_path,
    # rec_model_dir=ModelConfig.model_rec_path,
    # use_gpu= ModelConfig.is_use_gpu,
    # cls_model_dir=ModelConfig.cls_model_dir,
    # lang=FileConfig.lang,use_angle_cls=True
    table_engine = PaddleOCR(det_model_dir=ModelConfig.model_det_path,
                            rec_model_dir=ModelConfig.model_rec_path,
                            use_gpu= ModelConfig.is_use_gpu,
                            cls_model_dir=ModelConfig.cls_model_dir,
                            lang=ModelConfig.lang,use_angle_cls=True)
    root,name=com_path(data=data,uuid=uuid)
    result=table_engine.ocr(root)
    return one_json(result,name,uuid)


def res(data,uuid,executor):
    list_name=[]
    txt_name=[]
    # det_model_dir=ModelConfig.model_det_path,
    # rec_model_dir=ModelConfig.model_rec_path,
    # use_gpu= ModelConfig.is_use_gpu,
    # cls_model_dir=ModelConfig.cls_model_dir,
    # lang=FileConfig.lang,use_angle_cls=True
    table_engine = PaddleOCR(det_model_dir=ModelConfig.model_det_path,
                            rec_model_dir=ModelConfig.model_rec_path,
                            use_gpu= ModelConfig.is_use_gpu,
                            cls_model_dir=ModelConfig.cls_model_dir,
                            lang=ModelConfig.lang,use_angle_cls=True)
    coord,txt_result,name=cv_path(data,uuid)
    fiul.list_one_dir(coord,list_name)
    txt_name=fiul.get_file_name(list_name)
    result=rules(list_name=list_name,txt_name=txt_name,table_engine=table_engine,uuid=uuid,name=name)
    return result
    
    
def all(data,uuid,executor):
    list_name=[]
    txt_name=[]
    # det_model_dir=ModelConfig.model_det_path,
    # rec_model_dir=ModelConfig.model_rec_path,
    # use_gpu= ModelConfig.is_use_gpu,
    # cls_model_dir=ModelConfig.cls_model_dir,
    # lang=FileConfig.lang,use_angle_cls=True
    table_engine = PaddleOCR(det_model_dir=ModelConfig.model_det_path,
                            rec_model_dir=ModelConfig.model_rec_path,
                            use_gpu= ModelConfig.is_use_gpu,
                            cls_model_dir=ModelConfig.cls_model_dir,
                            lang=ModelConfig.lang,use_angle_cls=True)
    coord,txt_result,name=cv_path(data,uuid)
    fiul.list_one_dir(coord,list_name)
    txt_name=fiul.get_file_name(list_name)
    objs=[]
    for i in range(len(list_name)):
        result=table_engine.ocr(list_name[i])
        one=one_json(result,name,uuid)
        #0,1,2,3 y y+h x x+w 后缀
        s_index=str(txt_name[i]).split("_")
        obj=OCRAll()
        obj._bbox=[[s_index[2],s_index[0]],[s_index[2],s_index[1]]
                ,[s_index[3],s_index[0]],[s_index[3],s_index[1]]]
        obj._name=name
        obj._result=one
        obj._suffix=s_index[-1]
        obj._bbox_path = FileConfig.save_path+"/"+uuid+"/"+FileConfig.coord+"/"+txt_name[i]
        objs.append(obj.__dict__())
    return objs

def com_path(data,uuid):
    image = data['image']
    suffix = data['suffix']
    name = data['name']
    name=name+suffix
    root=fiul.uuid_save_img(uuid,name)
    fiul.save_image(image,root)
    return root,name

def cv_path(data,uuid):
    root,name=com_path(data,uuid)
    coord,txt_result=cvut.cv_build(uuid,name)
    return coord,txt_result,name


def one_json(result,name,uuid):
    lists=comm.extract_text_obj(result)
    objs=[]
    for i in lists:
        obj=OCRCommon()
        obj._coordinates=i[0]
        obj._txt_result=i[1]
        obj._name=name
        obj._txt_rate=i[2]
        obj._uuid = uuid
        objs.append(obj.__dict__())
    return objs