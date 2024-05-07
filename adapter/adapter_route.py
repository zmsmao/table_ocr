from rules import hot_rules 
from rules import repair_rules
from rules import attached_rules

from rules import base_rules
from rules import charge_rules
from rules import distributing_rules
from rules import factory_rules

from rules import line_rules
from rules import record_rules

from config.file_config import FileConfig
import utils.speck_util as spul
from domain.ocr_result_common import OCRCommon
import cv2

def init_key():
    key = ['线路','配电','带电','记录','附页','厂站','动火','抢修']
    return key

def adapter_rules_route(coord_img_path,table_engine,uuid,name,route:int):
    res = None
    if route == -1:
        res= base_rules.rules(coord_img_path,table_engine,uuid,name)
    elif route == 0:
        res= line_rules.rules(coord_img_path,table_engine,uuid,name)
    elif route == 1:
        res= distributing_rules.rules(coord_img_path,table_engine,uuid,name)
    elif route == 2:
        res= charge_rules.rules(coord_img_path,table_engine,uuid,name)
    elif route == 3:
        res= record_rules.rules(coord_img_path,table_engine,uuid,name)
    elif route == 4:
        res= attached_rules.rules(coord_img_path,table_engine,uuid,name)
    elif route == 5:
        res= factory_rules.rules(coord_img_path,table_engine,uuid,name)
    # elif route == 6:
    #     res= hot_rules.rules(coord_img_path,table_engine,uuid,name)
    # elif route == 7:
    #     res= repair_rules.rules(coord_img_path,table_engine,uuid,name)
    return res
        
        
def adapter_key(ans:OCRCommon,target_path,root_dir,is_check=True):
    '''
    返回route 确定走哪个规则
    '''
    index_ = []
    check_index = 0
    route = -1
    image = cv2.imread(target_path)
    height, width, channels = image.shape
    key = init_key()
    if is_check:
        for i in range(len(ans)):
            res_=ans[i]['txt_result']
            for j in range(len(key)):
                if res_.find(key[j])!=-1:
                    route = j
                    check_index = i
                    print("匹配规则为：----: >>>"+key[j]+",key值为: ----: >>>"+str(j))
                    break
            if route!=-1:
                break   
        #判断是否在这个表格框里。
        tmp = ans[check_index]['coordinates']
        if int(tmp[0][0])>height/2:
            check_index = 0
        for i in range(check_index,len(ans)):
            index_.append(ans[i]['coordinates'])
    #左，右，上，下
    rectangle = spul.expand_coordinates(spul.calculate_bounding_box(index_),width,height,45,150,30,80)
    x1, y1 = map(int, rectangle[0])
    x2, y2 = map(int, rectangle[1])
    roi = image[y1:y2, x1:x2]
    image_name = root_dir+"/"+FileConfig.cv_intelligence_img
    cv2.imwrite(image_name,roi)
    return route
    
    
