import utils.common_util as comm
import utils.file_util as fiut
import utils.cv_util as cvut
import json
from domain.ocr_rules_result import OCRRulesHead,OCRRulesBody,OCRRulesResult
import re
interval = 16
def rules(coord_img_path,table_engine,uuid,name):
    coord_img_path = fiut.sort_file_path(coord_img_path)
    img_name = fiut.get_file_name(coord_img_path)
    all_index = name_cover_rect(img_name)
    ocr_body=OCRRulesBody()
    ocr_head=OCRRulesHead()
    ocr_result=OCRRulesResult()
    table_type=''
    # k_error =  "图片质量不佳，或者图片不符合规范，或者图片缺失表头，保证图片要清晰，表格平整。"
    k_error = '''1.不支持双面识别和伪双面识别。2.图片质量差，图片不符合模板标准。3.表格不完整（logo遮挡表格线，表格线部分缺失，表格线模糊）。4.表格不平整（中间凹陷和表格线弯曲）。5.存在多表格干扰，无法定位主表格。6.生僻字识别模型不支持。7.任何模型识别率不可能达到100%的效果，肯定会有损失文本和错误文本的情况。
'''
    #优化head
    first_suffix =  all_index[0][-1]
    if first_suffix!='head':
        raise RuntimeError(k_error)
    is_interrupt=True
    ocr_result= option_res([coord_img_path[0]],[img_name[0]],table_engine)
    if len(ocr_result.list_txt_filter_pj[0])>0 and len(ocr_result.list_txt_no_filter_pj[0])<=100:
        is_interrupt = False
    if is_interrupt:
        raise RuntimeError(k_error)
    result_paths = []
    #结果匹配
    # 补充提出表头 2023-10-26
    head=ocr_result.list_txt_filter_pj[0]
    head_ls = ocr_result.list_filter[0]
    head_no = ocr_result.list_txt_no_filter_pj[0]
    #表头
    if head.find("附页")==-1:
        result_paths=find_split_head(coord_img_path,int(all_index[0][1]),all_index)
        if len(result_paths)!=3:
            raise RuntimeError(k_error)
    if head.find("种")!=-1 or head.find('记录')!=-1 or head.find("带电")!=-1:
        ex_txt,src_txt,ex_time_txt,src_time_txt=two_spilt(result_paths,uuid,table_engine)
        find_ops_time_txt(ex_time_txt,src_time_txt,ocr_head)
        find_ops_head_txt(ex_txt,src_txt,ocr_head)
        table_type = '工作票'
    if head.find("附页")!=-1:
        table_type='附页'
    for i in head_ls:
        if i.find("种")!=-1 or i.find('记录')!=-1 or i.find("带电")!=-1 or  i.find("附页") != -1:
            ocr_head.head = i
            break
    if head.find("编号") != -1 and head.find("附页")==-1:
        chinese_pj=comm.filter_chinese_punctuation(head_no)
        _,end=comm.find_substring_positions(chinese_pj,'编号')
        ors=chinese_pj[end+1:len(chinese_pj)]
        ocr_head.number=ors
    
    #移除已识别的head
    tmp1=[]
    tmp2=[]
    del coord_img_path[0]
    del img_name[0]
    for i in range(len(coord_img_path)):
        if coord_img_path[i] not in result_paths:
            tmp1.append(coord_img_path[i])
            tmp2.append(img_name[i])
    coord_img_path = tmp1
    img_name = tmp2
    
    ocr_result=option_res(coord_img_path,img_name,table_engine)
    
    #内容
    for i in range(len(ocr_result.index_)):
        #0,1,2,3 4,5 y y+h x x+w 大小 后缀
        s_index=ocr_result.index_[i]
        txt_filter_pj=str(ocr_result.list_txt_filter_pj[i])
        tmps_filter=ocr_result.list_filter[i]
        tmps_no_filter=ocr_result.list_no_filter[i]
        if s_index[-1]=='head':
            continue
        if s_index[-1]=='end':
            continue
        if head.find("附页") != -1:
            if len(ocr_result.index_)<=2:
                # 其他安全措施和注意事项
                measure_other=[]
                # 之前的数据
                other=[]
                #工作任务
                work_task=[]
                j=0
                while(j<len(tmps_filter)):
                    if tmps_filter[j].find('其他安全措施和注意事项')!=-1 or (
                        len(tmps_filter[j])<=11 and tmps_filter[j].find('其他安全')!=-1):
                        for k in range(j,len(tmps_filter)):
                            if str(tmps_filter[k])[:4].find('备注')!=-1:
                                break
                            else:
                                measure_other.append(tmps_no_filter[k])
                        break
                    elif tmps_filter[j].find('安全措施')!=-1 and tmps_filter[j].find('注意事项')!=-1:
                        for k in range(j,len(tmps_filter)):
                            if str(tmps_filter[k])[:4].find('备注')!=-1:
                                break
                            else:
                                measure_other.append(tmps_no_filter[k])
                        break
                    elif len(tmps_filter[j])<=4 and tmps_filter[j].find('工作任务')!=-1:
                        for k in range(j+1,len(tmps_filter)):
                            if str(tmps_filter[k])[:4].find('工作')!=-1 or str(tmps_filter[k])[:4].find('安全')!=-1:
                                break
                            else:
                                work_task.append(tmps_no_filter[k])
                        j=k-1
                    else:
                        if str(tmps_filter[j][:4]).find('备注')!=-1:
                            break
                        else:
                            other.append(tmps_no_filter[j])
                    j+=1
                ocr_body.measure_other=measure_other
                ocr_body.other=other
                ocr_body.work_task=work_task
            if len(ocr_result.index_)>2:
                if len(txt_filter_pj)==4 and txt_filter_pj[:4]=='工作任务':
                    res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                        ,ocr_result.index_,ocr_result.list_no_filter)
                    ocr_body.work_task=res
        elif head.find("种")!=-1 or head.find('记录')!=-1 or head.find("带电")!=-1:
            # 工作任务
            if len(txt_filter_pj)>4:
                if txt_filter_pj[:4]=='工作任务'  or txt_filter_pj[:4].find('作任务')!=-1:
                    ocr_body.work_task=tmps_no_filter
                    continue
            if len(txt_filter_pj)==4 and txt_filter_pj[:4]=='工作任务':
                res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                    ,ocr_result.index_,ocr_result.list_no_filter)
                ocr_body.work_task=res
                continue
            # 工作要求的安全措施
            if len(txt_filter_pj)>=4 and txt_filter_pj[:9].find('工作要求的安全措')!=-1:
                res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                    ,ocr_result.index_,ocr_result.list_no_filter)
                ocr_body.measure_main=res
                continue
            # 其他安全措施和注意事项
            if (txt_filter_pj.find('其他安全措施和注意事项')!=-1 or txt_filter_pj.find('他安全措施和注')!=-1)and len(txt_filter_pj)<=11:
                res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                    ,ocr_result.index_,ocr_result.list_no_filter)
                ocr_body.measure_other=res
                continue
            # 安全措施或注意事项
            if txt_filter_pj.find('安全措施或注意事项')!=-1 and len(txt_filter_pj)==9:
                res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                    ,ocr_result.index_,ocr_result.list_no_filter)
                ocr_body.measure_other=res
                continue
            # 安全措施或注意事项
            if len(txt_filter_pj)>10:
                if txt_filter_pj[:10]=='安全措施或注意事项' or txt_filter_pj[:10].find('安全措施或注意事项')!=-1:
                    ocr_body.measure_other=tmps_no_filter
                    continue
            #调度或设备运维单位负责的安全措施
            if len(txt_filter_pj)>10 :
                if txt_filter_pj.find('调度')!=-1 or txt_filter_pj.find('调或')!=-1 :
                    if txt_filter_pj.find('措施')!=-1 or txt_filter_pj.find('安措')!=-1:
                        res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                            ,ocr_result.index_,ocr_result.list_no_filter)
                        ocr_body.responsible=res
                        continue
        else:
            if len(txt_filter_pj)==4 and txt_filter_pj[:4]=='工作任务':
                    res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                        ,ocr_result.index_,ocr_result.list_no_filter)
                    ocr_body.work_task=res
                    ocr_head.head='附页'

    if head.find("附页") != -1:
        if ocr_body.work_task==None and len(ocr_result.index_)>2:
                    raise RuntimeError(k_error)
    dicts={
        'img_name':str(name),
        'uuid_path':'io/save_path/'+uuid,
        'table_head':ocr_head.head,
        'table_type': table_type,
        'table_body':{
            'head':ocr_head.__dict__(),
            'body':ocr_body.__dict__()
        }
    }
    print('io/save_path/'+uuid)
    # ts = fiut.parent_path()+'/cache/'+str(name).split('.')[0]+"_result.txt"
    # fiut.write_result(json.dumps(dicts, ensure_ascii=False, indent=2),ts)
    return dicts


def find_split_head(coord_img_path,head_y,list_s_index):
    result_paths=find_y(head_y,list_s_index,coord_img_path)
    return result_paths

def two_spilt(result_paths,uuid,table_engine):
    ts=[]
    obj=option_res(coord_img_path=result_paths,img_name=[],table_engine=table_engine)
    ts = obj.list_txt_filter_pj
    ex_txt=''
    src_txt=''
    ex_time_txt=''
    src_time_txt=''
    for i in range(len(ts)):
        if ts[i].find('年')!=-1:
            ex_time_txt = ts[i]
            src_time_txt =  obj=option_res(coord_img_path=[result_paths[i]],img_name=[],table_engine=table_engine,is_expand=False).list_txt_filter_pj[0]
        if ts[i].find('人')!=-1:
            src_txt = obj=option_res(coord_img_path=[result_paths[i]],img_name=[],table_engine=table_engine,is_expand=False).list_txt_filter_pj[0]
            ex_txt = ts[i]
    return ex_txt,src_txt,ex_time_txt,src_time_txt

def find_y(des_y,list_s_index,coord_img_path):
    result_path=[]
    for i in range(len(list_s_index)):
        if abs(des_y-int(list_s_index[i][0]))<=interval :
            result_path.append(coord_img_path[i])
    return result_path

def find_x_y_range(y_start,yh_end,x_start,xw_end,list_s_index,listss):
    results=[]
    hx=[]
    hy=[]
    y_start=int(y_start)
    yh_end=int(yh_end)
    x_start=int(x_start)
    xw_end=int(xw_end)
    h=abs(int(y_start)-int(yh_end))
    w=abs(int(x_start)-int(xw_end))
    for i in range(len(list_s_index)):
        x=int(list_s_index[i][2])
        xw=int(list_s_index[i][3])
        y=int(list_s_index[i][0])
        yh=int(list_s_index[i][1])
        if h>w:
            if xw_end-interval<=x:
                if y_start-interval<=y and yh_end+interval>=yh:
                        hx.append((x,listss[i]))
        if h<w:
            if abs(x_start-x)<=interval:
                if abs(xw_end-xw)<=interval:
                    if yh_end<=y+interval and len(listss[i])>0:
                        hy.append((x,listss[i]))
                        
    if len(hx)>0:
        hx = sorted(hx, key=lambda x: x[0])
        for i in hx:
            results.append(i[1])
    if len(hy)>0:
        hy = sorted(hy, key=lambda x: x[0])
        for i in hy:
            results.append(i[1])
    return results

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

def name_cover_rect(img_name):
    #0,1,2,3 4,5 y y+h x x+w 大小 后缀
    all_index=[]
    if len(img_name)>0:
        for i in range(len(img_name)):
            s_index=str(img_name[i]).split("_")
            all_index.append(s_index)
    return all_index

def find_head_rules(ex_txt):
    s1='' 
    s2='' 
    s3=''
    s6=''
    sk = comm.extract_numbers(ex_txt)
    if len(sk)==2:
        s2=sk[0]
        s6=sk[1]
    if len(sk)==1:
        if len(sk[0])>4:
            s2=sk[0]
        else:
            s6=sk[0]
    no_sk = comm.filter_numbers(ex_txt)
    tp=no_sk.find('和')
    index=tp-2
    start,end=comm.find_substring_positions(no_sk,'监护人')
    s1=no_sk[end+1:index].replace('电话',',')
    index_s = no_sk.find('组')
    ts = no_sk[index_s+1:len(ex_txt)]
    start,end=comm.find_substring_positions(ts,'负')
    s3=ts[:start-2]
    return  s1,s2,s3,s6

def find_ops_head_txt(ex_txt,src_txt,ocr_head:OCRRulesHead):
    # guardian=s1,telephone=s2,dept=s3,duty_number=s6,
    s1,s2,s3,s6=find_head_rules(ex_txt)
    s11,s22,s33,s66=find_head_rules(src_txt)
    ocr_head.guardian = s1
    ocr_head.telephone = s2
    if len(s33)>len(s3):
        s3=s33
    ocr_head.dept = s3
    if len(str(s66))==0:
        s66 = s6
    ocr_head.duty_number=s66

def  find_head_time(line):
    s4=''
    s5=''
    start,end=comm.find_substring_positions(line,'至')
    s4 = line[1:start]
    s5= line[start+1:len(line)]
    if start == 1:
        start_min,end_min=comm.find_substring_positions(line,'分')
        s4 = line[start+1:start_min]
        s5= line[start_min+1:len(line)]
    elif line[0].isdigit():
        s4 = line[:start]
        s5= line[start+1:len(line)]
    if s4[0].isdigit() and int(s4[0])!=2:
        s4=s4[1:]
    return s4,s5

def find_ops_time_txt(ex_time_txt,src_time_txt,ocr_head:OCRRulesHead):
    s4,s5=find_head_time(ex_time_txt)
    s44,s55=find_head_time(src_time_txt)
    if check_time_format(s4):
        s44=s4
    if check_time_format(s5):
        s55=s5
    ocr_head.start_time = s44
    ocr_head.end_time = s55
    
def check_time_format(text):
    pattern = r"\d{4}年\d{1,2}月\d{1,2}日\d{1,2}时\d{1,2}分"
    match = re.fullmatch(pattern, text)
    if match:
        return True
    else:
        return False