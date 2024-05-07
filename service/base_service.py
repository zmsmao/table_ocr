import cv2
import utils.common_util as comm
import utils.file_util as fiul
import utils.cv_util as cvut
import utils.speck_util as spul
from domain.ocr_result_common import OCRCommon,OCRAll
from config.file_config import FileConfig
from config.model_config import ModelConfig
from paddleocr import PaddleOCR
from rules.base_rules import rules
from config.cv_config import CVConfig
# import adapter.adapter_route as adp_ru


def com_video_img(type:int,uuid:str,di:str):
    print("UuidPath:  io/save_path/"+uuid)
    table_engine = PaddleOCR(det_model_dir=ModelConfig.model_det_path,
                    rec_model_dir=ModelConfig.model_rec_path,
                    use_gpu= ModelConfig.is_use_gpu,
                    cls_model_dir=ModelConfig.cls_model_dir,
                    lang=ModelConfig.lang,use_angle_cls=True)
    if type==1:
        #压缩图片
        save_compress=fiul.uuid_save_compress_img(uuid)
        target = di
        flag_compress = cvut.get_compress(target,save_compress,CVConfig.cv_compress)
        if flag_compress:
            target = save_compress
        print("UuidPath:  io/save_path/"+uuid)
        result=table_engine.ocr(target,rec=True)
        result=comm.extract_text_obj(result)
        res = []
        for i  in result:
            res.append(i[1])
        return res
    if type==2:
        frame=fiul.uuid_save_mkdir_video_frame(uuid)
        img_list = cvut.cv_init_video(di,frame)
        list_txt_no_filter_pj=[]
        list_txt_filter_pj=[]
        for i in range(len(img_list)):
            result=table_engine.ocr(img_list[i])
            lists=comm.extract_text_obj(result)
            txt_no_filter_pj=''
            txt_filter_pj=''
            for j in range(len(lists)):
                no_filter_pj=lists[j][1]
                filter_pj=comm.filter_text(no_filter_pj)
                txt_filter_pj+=filter_pj
                txt_no_filter_pj+=no_filter_pj
            if len(txt_filter_pj)>0:
                list_txt_no_filter_pj.append(txt_no_filter_pj)
                list_txt_filter_pj.append(txt_filter_pj)
        res=[]
        res.append(list_txt_no_filter_pj[0])
        for i in range(0,len(list_txt_no_filter_pj)-1):
            if list_txt_filter_pj[i].find(list_txt_filter_pj[i+1])==-1:
                res.append(list_txt_no_filter_pj[i+1])
        return res

def common(data,uuid):
    table_engine = PaddleOCR(det_model_dir=ModelConfig.model_det_path,
                            rec_model_dir=ModelConfig.model_rec_path,
                            use_gpu= ModelConfig.is_use_gpu,
                            cls_model_dir=ModelConfig.cls_model_dir,
                            lang=ModelConfig.lang,use_angle_cls=True)
    print("UuidPath:  io/save_path/"+uuid)
    root_dir,name=com_path(data=data,uuid=uuid)
    return table_engine.ocr(root_dir+"/"+name,det=False)
    # return comm_ocr(root_dir+"/"+name,name,uuid,table_engine)

def res(data,uuid,executor):
    coord_img_path=[]
    table_engine = PaddleOCR(det_model_dir=ModelConfig.model_det_path,
                            rec_model_dir=ModelConfig.model_rec_path,
                            use_gpu= ModelConfig.is_use_gpu,
                            cls_model_dir=ModelConfig.cls_model_dir,
                            lang=ModelConfig.lang,use_angle_cls=True)
    print("UuidPath:  io/save_path/"+uuid)
    # 普通识别
    # coord,txt_result,name=cv_path(data,uuid)
    # fiul.list_one_dir(coord,coord_img_path)
    # 智能识别
    key_word = ["种","记录","带电","附页"]
    name=intelligence_splie(data,uuid,table_engine,coord_img_path,False,key_word=key_word)
    # result= adp_ru.adapter_rules_route(coord_img_path,table_engine,uuid,name,route)
    result=rules(coord_img_path=coord_img_path,table_engine=table_engine,uuid=uuid,name=name)
    return result

def all(data,uuid,executor):
    # 第一种方案 先分割再识别
    table_engine = PaddleOCR(det_model_dir=ModelConfig.model_det_path,
                            rec_model_dir=ModelConfig.model_rec_path,
                            use_gpu= ModelConfig.is_use_gpu,
                            cls_model_dir=ModelConfig.cls_model_dir,
                            lang=ModelConfig.lang,use_angle_cls=True)
    print("UuidPath:  io/save_path/"+uuid)
    coord_img_path=[]
    img_name=[]
    #普通分隔
    # coord,txt_result,name=cv_path(data,uuid)
    # fiul.list_one_dir(coord,coord_img_path)
    # 智能识别
    name=intelligence_splie(data,uuid,table_engine,coord_img_path,is_check_word=False)
    # img_name=fiul.get_file_name(coord_img_path)
    objs=[]
    for i in range(len(coord_img_path)):
        result=table_engine.ocr(coord_img_path[i])
        one=one_json(result,name,uuid)
        #0,1,2,3 y y+h x x+w 后缀
        s_index=str(img_name[i]).split("_")
        obj=OCRAll()
        obj._bbox=[[s_index[2],s_index[0]],[s_index[2],s_index[1]]
                ,[s_index[3],s_index[0]],[s_index[3],s_index[1]]]
        obj._name=name
        obj._result=one
        obj._suffix=s_index[-1]
        obj._bbox_path = FileConfig.save_path+"/"+uuid+"/"+FileConfig.coord+"/"+img_name[i]
        objs.append(obj.__dict__())
    return objs
    #第二种方案 再识别在分割
    # ans = common(data=data,uuid=uuid)
    # index_ = []
    # name = ans[0]['name']
    # for i in range(len(ans)):
    #     index_.append(ans[i]['coordinates'])
    # root = fiul.uuid_save_root(uuid)
    # image = cv2.imread(root+"/"+name)
    # height, width, channels = image.shape
    # rectangle = spul.expand_coordinates(spul.calculate_bounding_box(index_),width,height,40,10)
    # x1, y1 = map(int, rectangle[0])
    # x2, y2 = map(int, rectangle[1])
    # roi = image[y1:y2, x1:x2]
    # image_name = root+"/"+uuid+name
    # cv2.imwrite(image_name,roi)
    # coord,txt_result = cvut.cv_build(uuid,uuid+name)
    # fiul.list_one_dir(coord,coord_img_path)
    # img_name=fiul.get_file_name(coord_img_path)
    # index_s=[]
    # x_t = x1
    # y_t = y1
    # for i in img_name:
    #     s_index=str(i).split("_")
    #     tmp = [[int(s_index[2]),int(s_index[0])],[int(s_index[2]),int(s_index[1])]
    #                 ,[int(s_index[3]),int(s_index[0])],[int(s_index[3]),int(s_index[1])]]
    #     index_s.append(tmp)
    
    # objs=[]
    # for i in index_s:
    #     obj=OCRAll()
    #     obj._result = []
    #     for j in ans:
    #         ts = [[int(point[0])-x_t, int(point[1])-y_t] for point in j['coordinates']]
    #         if cvut.is_inside(i,ts):
    #             obj._result.append(j)
    #     objs.append(obj.__dict__())
    # print()
    # return objs
                
def com_path(data,uuid):
    image = data['image']
    suffix = data['suffix']
    name = data['name']
    name=FileConfig.cv_accept_name+suffix
    root_dir = fiul.uuid_save_root(uuid)
    fiul.save_image(image,root_dir+"/"+name)
    return root_dir,name

def cv_path(data,uuid):
    root_dir,name=com_path(data,uuid)
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

def comm_ocr(path,name,uuid,table_engine):
    result=table_engine.ocr(path)
    return one_json(result,name,uuid)


def intelligence_splie( data,uuid
    ,table_engine:PaddleOCR
    ,coord_img_path:list
    ,is_check_word=False
    ,key_word:list=[]):
    '''
    通过一次先识别整体轮廓即可，无需识别文字。
    is_check_word : 检测文字
    key_word: 先开启is_check_word，再使用
    '''
    root_dir,name=com_path(data,uuid)
    root_image = root_dir+"/"+name
    target_path = cvut.cv_init_img(root_image,uuid)
    image = cv2.imread(target_path)
    height, width, channels = image.shape
    index_ = []
    if is_check_word:
        check_index = 0
        ans = comm_ocr(path=target_path,name=name,uuid=uuid,table_engine=table_engine)
        for i in range(len(ans)):
            res_=ans[i]['txt_result']
            # if  res_.find("种")!=-1 or res_.find('记录')!=-1 or res_.find("带电")!=-1 or  res_.find("附页") != -1:
            if res_ in key_word:
                check_index = i
                break
        #判断是否在这个表格框里。
        tmp = ans[check_index]['coordinates']
        if int(tmp[0][0])>height/2:
            check_index = 0
        for i in range(check_index,len(ans)):
            index_.append(ans[i]['coordinates'])
    else:
        ans = table_engine.ocr(target_path,rec=False)
        coordinates = ans[0]
        for i in coordinates:
            integer_list = [[int(num) for num in sublist] for sublist in i]
            index_.append(integer_list)
    #左，右，上，下
    rectangle = spul.expand_coordinates(spul.calculate_bounding_box(index_),width,height,30,120,30,80)
    x1, y1 = map(int, rectangle[0])
    x2, y2 = map(int, rectangle[1])
    roi = image[y1:y2, x1:x2]
    image_name = root_dir+"/"+FileConfig.cv_intelligence_img
    cv2.imwrite(image_name,roi)
    # route = adp_ru.adapter_key(ans,target_path,root_dir)
    # save_compress=fiul.uuid_save_compress_img(uuid)
    # flag_compress = cvut.get_compress(image_name,save_compress,CVConfig.cv_compress)
    # if flag_compress:
    #     coord,txt_result = cvut.cv_build(uuid,CVConfig.cv_compress)
    # else:
    #     coord,txt_result = cvut.cv_build(uuid,FileConfig.cv_intelligence_img)
    coord,txt_result = cvut.cv_build(uuid,FileConfig.cv_intelligence_img)
    fiul.list_one_dir(coord,coord_img_path)
    return name