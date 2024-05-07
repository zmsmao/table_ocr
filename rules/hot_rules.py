from rules.common import comm_rules 
from rules.common import ocr_rules 
from domain.ocr_rules_result import OCRRulesHead,OCRRulesBody,OCRRulesResult,OCRBuildResult
import utils.file_util as filu
def rules(coord_img_path,table_engine,uuid,name):
    '''
    动火类工作票
    '''
    coord_img_path = filu.sort_file_path(coord_img_path)
    img_name = filu.get_file_name(coord_img_path)
    ocr_body=OCRRulesBody()
    ocr_head=OCRRulesHead()
    build_res = OCRBuildResult()
    build_res.ocr_body = ocr_body
    build_res.ocr_head = ocr_head
    hot_key = '工作票'
    hot_value ='动火'
    
    all_index = ocr_rules.name_cover_rect(img_name)
    #初始坐标 没有找到head返回
    first_suffix =  all_index[0][-1]
    if first_suffix!='head':
        return build_res
    #检测 找到head，但是过长返回
    flag = ocr_rules.optimization_head(img_name,coord_img_path,table_engine)
    if flag:
        return build_res
    #识别结果
    ocr_result=ocr_rules.option_res(coord_img_path,img_name,table_engine)
    head_ls = ocr_result.list_filter[0]
    #初始化
    build_res.table_type = hot_key
    build_res.name = name
    build_res.uuid = uuid
    build_res.table_head = comm_rules.get_head_txt(hot_value,head_ls)
    all_index = ocr_result.index_
    all_txt = ocr_result.list_no_filter
    #开始匹配头部
    #其他内容
    table_first=ocr_rules.find_adjacent_rect(all_index[0],all_index,2,False)
    first_txt_list=ocr_rules.get_txt_from_index(table_first,ocr_result.list_txt_filter_pj)
    #检测 表头不符合规则
    if len(first_txt_list)!=3:
        return build_res
    ocr_head = comm_rules.build_merge_table_head(first_txt_list[0],first_txt_list[2])
    #编号
    number_str = ocr_result.list_txt_no_filter_pj[0]
    ocr_head.number=comm_rules.get_number_txt(number_str)
    #内容
    for i in range(len(ocr_result.index_)):
        #0,1,2,3 4,5 y y+h x x+w 大小 后缀
        s_index=ocr_result.index_[i]
        txt_filter_pj=str(ocr_result.list_txt_filter_pj[i])
        tmps_no_filter=ocr_result.list_no_filter[i]
        if s_index[-1]=='head':
            continue
        if s_index[-1]=='end':
            continue
        # 工作任务
        if len(txt_filter_pj)>4:
            if txt_filter_pj[:4]=='工作任务'  or txt_filter_pj[:4].find('作任务')!=-1:
                ocr_body.work_task=tmps_no_filter
        if len(txt_filter_pj)==4 and txt_filter_pj[:4]=='工作任务':
            res=ocr_rules.get_txt_from_index(ocr_rules.find_cover_rect(s_index,all_index),all_txt)
            ocr_body.work_task=res
        # 工作要求的安全措施
        if len(txt_filter_pj)>=4 and txt_filter_pj[:9].find('工作要求的安全措')!=-1:
            res=ocr_rules.get_txt_from_index(ocr_rules.find_cover_rect(s_index,all_index),all_txt)
            ocr_body.measure_main=res
        # 其他安全措施和注意事项
        if (txt_filter_pj.find('其他安全措施和注意事项')!=-1 or txt_filter_pj.find('他安全措施和注')!=-1)and len(txt_filter_pj)<=11:
            res=ocr_rules.get_txt_from_index(ocr_rules.find_cover_rect(s_index,all_index),all_txt)
            ocr_body.measure_other=res
        # 安全措施或注意事项
        if txt_filter_pj.find('安全措施或注意事项')!=-1 and len(txt_filter_pj)==9:
            res=ocr_rules.get_txt_from_index(ocr_rules.find_cover_rect(s_index,all_index),all_txt)
            ocr_body.measure_other=res
        # 安全措施或注意事项
        if len(txt_filter_pj)>10:
            if txt_filter_pj[:10]=='安全措施或注意事项' or txt_filter_pj[:10].find('安全措施或注意事项')!=-1:
                ocr_body.measure_other=tmps_no_filter
        #调度或设备运维单位负责的安全措施
        if txt_filter_pj[:16].find('调度')!=-1 :
            if  txt_filter_pj[:16].find('措施')!=-1:
                res=ocr_rules.get_txt_from_index(ocr_rules.find_cover_rect(s_index,all_index),all_txt)
                ocr_body.responsible=res
    build_res.ocr_body = ocr_body
    build_res.ocr_head = ocr_head
    return build_res.__dict__()

    
    
    



