from rules.common import comm_rules 
from rules.common import ocr_rules 
from domain.ocr_rules_result import OCRRulesHead,OCRRulesBody,OCRRulesResult,OCRBuildResult
import utils.file_util as filu
def rules(coord_img_path,table_engine,uuid,name):
    '''
    附页
    '''
    #路径排序
    coord_img_path = filu.sort_file_path(coord_img_path)
    img_name = filu.get_file_name(coord_img_path)
    ocr_body=OCRRulesBody()
    ocr_head=OCRRulesHead()
    build_res = OCRBuildResult()
    attached_key = '附页'
    k_error =  "图片质量不佳，或者图片不符合规范，或者图片缺失表头，保证图片要清晰，表格平整。"
    all_index = ocr_rules.name_cover_rect(img_name)
    #初始坐标 没有找到head返回
    first_suffix =  all_index[0][-1]
    if first_suffix!='head':
        raise RuntimeError(k_error)
    #检测 找到head，但是过长返回
    flag = ocr_rules.optimization_head(img_name[0],coord_img_path[0],table_engine)
    if flag:
        raise RuntimeError(k_error)
    #识别结果
    ocr_result=ocr_rules.option_res(coord_img_path,img_name,table_engine)
    head_ls = ocr_result.list_filter[0]
    #初始化
    build_res.table_type = attached_key
    build_res.name = name
    build_res.uuid = uuid
    build_res.table_head = comm_rules.get_head_txt(attached_key,head_ls)
    all_index = ocr_result.index_
    all_txt = ocr_result.list_no_filter
    #开始匹配头部
    number_str = ocr_result.list_txt_no_filter_pj[0]
    #编号
    ocr_head.number=comm_rules.get_number_txt(number_str)
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
                res=ocr_rules.get_txt_from_index(ocr_rules.find_cover_rect(s_index,all_index),all_txt)
                ocr_body.work_task=res
    build_res.ocr_body = ocr_body
    build_res.ocr_head = ocr_head
    return build_res.__dict__()