import utils.common_util as comm
import utils.file_util as fiut
import utils.cv_util as cvut
import json
from domain.ocr_rules_result import OCRRulesHead,OCRRulesBody,OCRRulesResult
def rules(list_name,txt_name,table_engine,uuid,name,txt_result=[]):
    ocr_body=OCRRulesBody()
    ocr_head=OCRRulesHead()
    #优化head
    is_interrupt=True
    for i in range(len(txt_name)):
        s_index=str(txt_name[i]).split("_")
        if s_index[0] == '0':
            ocr_result= option_res([list_name[i]],[txt_name[i]],table_engine)
            if len(ocr_result.list_txt_filter_pj[0])>0 and len(ocr_result.list_txt_no_filter_pj[0])<=45:
                is_interrupt = False
                break
    if is_interrupt:
        dicts={
            'img_name':str(name),
            'uuid_path':'io/save_path/'+uuid,
            'table_head':ocr_head.head,
            'table_body':{
            'head':ocr_head.__dict__(),
            'body':ocr_body.__dict__()
            }
        }
        return dicts
    ocr_result=option_res(list_name,txt_name,table_engine)
        # s_result_path = txt_result+'/'+txt_name[i]+'_result.txt'
        # s_result=tmps_pj+'\n'+tmps_no_pj+'\n'
        # fiut.write_result(s_result,s_result_path)
    #结果匹配
    head=''
    for i in range(len(ocr_result.index_)):
        txt_filter_pj=ocr_result.list_txt_filter_pj[i]
        txt_no_filter_pj= ocr_result.list_txt_no_filter_pj[i]
        if ocr_result.index_[i][-1]=='head':
            head=ocr_result.list_txt_filter_pj[i]
            break
    #表头
    if head.find("种")!=-1 or txt_filter_pj.find('记录')!=-1:
        result_paths=find_split_head(list_name,txt_name,ocr_result.index_)
        s1=two_spilt(result_paths,uuid,table_engine)
        ocr_head=normal_head(s1)
        ocr_head.head='工作票'
        
        if txt_filter_pj.find("编号") != -1:
            chinese_pj=comm.filter_chinese_punctuation(txt_no_filter_pj)
            _,end=comm.find_substring_positions(chinese_pj,'编号')
            ors=chinese_pj[end+1:len(chinese_pj)]
            ocr_head.number=ors
    #内容
    for i in range(len(ocr_result.index_)):
        #0,1,2,3 4,5 y y+h x x+w 大小 后缀
        s_index=ocr_result.index_[i]
        txt_filter_pj=str(ocr_result.list_txt_filter_pj[i])
        txt_no_filter_pj=ocr_result.list_txt_no_filter_pj[i]
        tmps_filter=ocr_result.list_filter[i]
        tmps_no_filter=ocr_result.list_no_filter[i]
        if head.find("附页") != -1:
            ocr_head.head='附页'
            if s_index[-1]=='head':
                continue
            if s_index[-1]=='end':
                continue
            if len(ocr_result.index_)==3:
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
            if len(ocr_result.index_)>3:
                if len(txt_filter_pj)==4 and txt_filter_pj[:4]=='工作任务':
                    res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                        ,ocr_result.index_,ocr_result.list_no_filter)
                    ocr_body.work_task=res
        elif head.find("种")!=-1 or head.find('记录')!=-1:
            # 工作任务
            if len(txt_filter_pj)>4:
                if txt_filter_pj[:4]=='工作任务'  or txt_filter_pj[:4].find('作任务')!=-1:
                    ocr_body.work_task=tmps_no_filter
            if len(txt_filter_pj)==4 and txt_filter_pj[:4]=='工作任务':
                res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                    ,ocr_result.index_,ocr_result.list_no_filter)
                ocr_body.work_task=res
            # 工作要求的安全措施
            if len(txt_filter_pj)>=4 and txt_filter_pj[:9].find('工作要求的安全措')!=-1:
                res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                    ,ocr_result.index_,ocr_result.list_no_filter)
                ocr_body.measure_main=res
            # 其他安全措施和注意事项
            if (txt_filter_pj.find('其他安全措施和注意事项')!=-1 or txt_filter_pj.find('他安全措施和注')!=-1)and len(txt_filter_pj)<=11:
                res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                    ,ocr_result.index_,ocr_result.list_no_filter)
                ocr_body.measure_other=res
            # 安全措施或注意事项
            if txt_filter_pj.find('安全措施或注意事项')!=-1 and len(txt_filter_pj)==9:
                res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                    ,ocr_result.index_,ocr_result.list_no_filter)
                ocr_body.measure_other=res
            # 安全措施或注意事项
            if len(txt_filter_pj)>10:
                if txt_filter_pj[:10]=='安全措施或注意事项' or txt_filter_pj[:10].find('安全措施或注意事项')!=-1:
                    ocr_body.measure_other=tmps_no_filter
            #调度或设备运维单位负责的安全措施
            if len(txt_filter_pj)==16 :
                if txt_filter_pj.find('调度')!=-1 :
                    if txt_filter_pj.find('措施')!=-1:
                        res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                            ,ocr_result.index_,ocr_result.list_no_filter)
                        ocr_body.responsible=res
        else:
            if len(txt_filter_pj)==4 and txt_filter_pj[:4]=='工作任务':
                    res=find_x_y_range(s_index[0],s_index[1],s_index[2],s_index[3]
                                        ,ocr_result.index_,ocr_result.list_no_filter)
                    ocr_body.work_task=res
                    ocr_head.head='附页'
    dicts={
        'img_name':str(name),
        'uuid_path':'io/save_path/'+uuid,
        'table_head':ocr_head.head,
        'table_body':{
            'head':ocr_head.__dict__(),
            'body':ocr_body.__dict__()
        }
    }
    print('io/save_path/'+uuid)
    # ts = fiut.parent_path()+'/cache/'+str(name).split('.')[0]+"_result.txt"
    # fiut.write_result(json.dumps(dicts, ensure_ascii=False, indent=2),ts)
    return dicts


def find_split_head(list_name,txt_name,list_s_index):
    result_paths=[]
    head_y,flag=find_head(txt_name)
    if flag:
        result_paths=find_y(head_y,list_s_index,list_name)
    return result_paths

def two_spilt(result_paths,uuid,table_engine):
    ts=[]
    tss=''
    if len(result_paths) == 1:
        list_names=[]
        root,write_path=cvut.cv_two_split_build(uuid,result_paths[0])
        fiut.listdir(root,list_names)
        obj=option_res(list_name=list_names,txt_name=[],table_engine=table_engine)
            # s_result_path = write_path+'/'+txt_name_split[i]+'_result.txt'
            # s_result=tmps_pj+'\n'+tmps_no_pj+'\n'
            # fiut.write_result(s_result,s_result_path)
        ts=obj.list_txt_filter_pj
    if len(result_paths) >=3:
        obj=option_res(list_name=result_paths,txt_name=[],table_engine=table_engine)
        ts=obj.list_txt_filter_pj
    return ts
            
def normal_head(f):
    s1='' 
    s2='' 
    s3=''
    s4=''
    s5=''
    s6=''
    for line in f:
        line=line.replace("\n", "")
        if line.find('人')!=-1:
            sk = comm.extract_numbers(line)
            if len(sk)==2:
                s2=sk[0]
                s6=sk[1]
            if len(sk)==1:
                s6=sk[0]
            no_sk = comm.filter_numbers(line)
            tp=no_sk.find('和')
            index=tp-2
            start,end=comm.find_substring_positions(no_sk,'监护人')
            s1=no_sk[end+1:index].replace('电话',',')
            index_s = no_sk.find('组')
            ts = no_sk[index_s+1:len(line)]
            start,end=comm.find_substring_positions(ts,'负')
            s3=ts[:start-2]
        if line.find('年')!=-1:
            start,end=comm.find_substring_positions(line,'至')
            s4 = line[1:start]
            s5= line[start+1:len(line)]                   
    result = OCRRulesHead(guardian=s1,telephone=s2,dept=s3,duty_number=s6,start_time=s4,end_time=s5)
    return result


def find_y(des_y,list_s_index,list_name):
    result_path=[]
    for i in range(len(list_s_index)):
        if abs(des_y-int(list_s_index[i][0]))<=10 :
            result_path.append(list_name[i])
    return result_path

def find_x_y_range(y_start,yh_end,x_start,xw_end,list_s_index,listss):
    results=[]
    h=abs(int(y_start)-int(yh_end))
    w=abs(int(x_start)-int(xw_end))
    for i in range(len(list_s_index)):
        x=int(list_s_index[i][2])
        xw=int(list_s_index[i][3])
        y=int(list_s_index[i][0])
        yh=int(list_s_index[i][1])
        if h>w:
            if abs(int(xw_end)-x)<=10:
                if int(y_start)<=y: 
                    if int(yh_end)>=yh:
                        results.append(listss[i])
        if h<w:
            if abs(int(yh_end)-y)<=10: 
                if int(x_start)<=x:
                    if int(xw_end)>=xw:
                        results.append(listss[i])
    return results

def find_head(txt_name):
    flag= False
    head_y=0
    for k in txt_name:
        s_index=str(k).split("_")
        if int(s_index[0])==0 and s_index[-1]=='head':
            head_y=int(s_index[1])
            break
    if head_y>0:
        flag=True
    return head_y,flag

def option_res(list_name,txt_name,table_engine):
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
    for i in range(len(list_name)):
        result=table_engine.ocr(list_name[i])
        lists=comm.extract_text_obj(result)
        listsr.append(lists)
        if len(txt_name)>0:
            s_index=str(txt_name[i]).split("_")
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