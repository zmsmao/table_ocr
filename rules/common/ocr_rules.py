import utils.common_util as comm
from domain.ocr_rules_result import OCRRulesResult
import utils.cv_util as cvut

interval = 16

def get_txt_from_index(rect_ls,all_txt):
    res = []
    for i in rect_ls:
        if len(all_txt[i[1]])>0:
            res.append(all_txt[i[1]])
    return res


def optimization_head(img_name,coord_img_path,table_engine):
    '''
    优化head,主要用于判断表格是否分割失误
    '''
    ocr_result= option_res([coord_img_path],[img_name],table_engine)
    if len(ocr_result.list_txt_filter_pj[0])>0 and len(ocr_result.list_txt_no_filter_pj[0])<=100:
        return False
    return True

def name_cover_rect(img_name):
    #0,1,2,3 4,5 y y+h x x+w 大小 后缀
    all_index=[]
    if len(img_name)>0:
        for i in range(len(img_name)):
            s_index=str(img_name[i]).split("_")
            all_index.append(s_index)
    return all_index


def find_cover_rect(src_index,all_index):
    '''
    查找合并单元格数据和垂直向下单元格
    返回坐标和索引
    '''
    y_start=int(src_index[0])
    yh_end=int(src_index[1])
    x_start=int(src_index[2])
    xw_end=int(src_index[3])
    results=[]
    hx=[]
    hy=[]
    h=abs(int(y_start)-int(yh_end))
    w=abs(int(x_start)-int(xw_end))
    for i in range(len(all_index)):
        x=int(all_index[i][2])
        xw=int(all_index[i][3])
        y=int(all_index[i][0])
        yh=int(all_index[i][1])
        if h>w:
            if xw_end-interval<=x:
                if y_start-interval<=y and yh_end+interval>=yh:
                        hx.append((y,all_index[i],i))
        if h<w:
            if abs(x_start-x)<=interval:
                if abs(xw_end-xw)<=interval:
                    if yh_end<=y+interval:
                        hy.append((y,all_index[i],i))
    if len(hx)>0:
        hx = sorted(hx, key=lambda x: x[0])
        for i in hx:
            results.append((i[1],i[2]))
    if len(hy)>0:
        hy = sorted(hy, key=lambda x: x[0])
        for i in hy:
            results.append((i[1],i[2]))
    return results

def find_adjacent_rect(src_index,all_index,direction,same_match=True):
    '''
    查找相邻坐标和索引
    direction:上下左右 1,2,3,4
    same_match: 是否相同匹配,返回的结果不同。true返回元组,false返回list
    返回坐标和索引
    '''
    res=[]
    y_start=int(src_index[0])
    yh_end=int(src_index[1])
    x_start=int(src_index[2])
    xw_end=int(src_index[3])
    h=abs(int(y_start)-int(yh_end))
    w=abs(int(x_start)-int(xw_end))
    for i in range(len(all_index)):
        x=int(all_index[i][2])
        xw=int(all_index[i][3])
        y=int(all_index[i][0])
        yh=int(all_index[i][1])
        if direction==3:
            if same_match:
                if abs(y_start-y)<interval and abs(yh_end-yh)<interval:
                    if abs(x_start-xw)<interval:
                        return all_index[i],i
            else:
                if abs(x_start-xw)<interval:
                    if (abs(y_start-y)<interval and abs(yh_end-yh)<interval) or (y_start-interval<=y and yh_end+interval>=yh):
                        res.append((y,all_index[i],i))
        elif direction==4:
            if same_match:
                if abs(y_start-y)<interval and abs(yh_end-yh)<interval:
                    if abs(xw_end-x)<interval:
                        return all_index[i],i
            else:
                if abs(xw_end-x)<interval:
                    if (abs(y_start-y)<interval and abs(yh_end-yh)<interval) or (y_start-interval<=y and yh_end+interval>=yh):
                        res.append((y,all_index[i],i))
        elif direction==1:
            if same_match:
                if abs(x_start-x)<interval and abs(xw_end-xw)<interval:
                    if abs(y_start-yh)<interval:
                        return all_index[i],i
            else:
                if abs(y_start-yh)<interval:
                    if (abs(x_start-x)<interval and abs(xw_end-xw)<interval)  or (x_start-interval<=x and xw_end+interval>=xw): 
                        res.append((x,all_index[i],i))
        elif direction==2:
            if same_match:
                if abs(x_start-x)<interval and abs(xw_end-xw)<interval:
                    if abs(yh_end-y)<interval:
                        return all_index[i],i
            else:
                if abs(yh_end-y)<interval:
                    if (abs(x_start-x)<interval and abs(xw_end-xw)<interval) or (x_start-interval<=x and xw_end+interval>=xw): 
                        res.append((x,all_index[i],i))
    tmp = []
    if not same_match:
        res = sorted(res,key=lambda x:x[0])
        for i in res:
            tmp.append((i[1],i[2]))
    res = tmp
    return res


def option_res(coord_img_path,img_name,table_engine,is_expand = True,is_sharpening = False):
    #识别结果
    listsr=[]
    #0,1,2,3 4,5 y y+h x x+w 大小 后缀
    index_=[]
    #拼接
    list_txt_filter_pj=[]
    list_txt_no_filter_pj=[]
    #不拼接
    list_filter=[]
    list_no_filter=[]
    for i in range(len(coord_img_path)):
        expand_img = coord_img_path[i]
        if is_expand:
            expand_img = cvut.expand_cv_img(expand_img)
        if is_sharpening:
            expand_img = cvut.cv_sharpening(expand_img)
        result=table_engine.ocr(expand_img)
        lists=comm.extract_text_obj(result)
        listsr.append(lists)
        if len(img_name)>0:
            s_index=str(img_name[i]).split("_")
            index_.append(s_index)
        txt_filter_pj=''
        txt_no_filter_pj=''
        tmps_filter=[]
        tmps_no_filter=[]
        for j in range(len(lists)):
            no_filter_pj=lists[j][1]
            filter_pj=comm.filter_text(no_filter_pj)
            txt_filter_pj+=filter_pj
            txt_no_filter_pj+=no_filter_pj
            tmps_filter.append(filter_pj)
            tmps_no_filter.append(no_filter_pj)
        list_txt_filter_pj.append(txt_filter_pj)
        list_txt_no_filter_pj.append(txt_no_filter_pj)
        list_filter.append(tmps_filter)
        list_no_filter.append(tmps_no_filter)
    obj=OCRRulesResult(listsr,index_,list_txt_filter_pj,list_txt_no_filter_pj,list_filter,list_no_filter)
    return obj