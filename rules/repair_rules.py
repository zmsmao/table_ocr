from rules.common import comm_rules 
from rules.common import ocr_rules 
from domain.ocr_rules_result import OCRRulesHead,OCRRulesBody,OCRRulesResult,OCRBuildResult
import utils.file_util as filu
def rules(coord_img_path,table_engine,uuid,name):
    '''
    抢修类工作票
    '''
    coord_img_path = filu.sort_file_path(coord_img_path)
    img_name = filu.get_file_name(coord_img_path)
    all_index = ocr_rules.name_cover_rect(img_name)
    ocr_body=OCRRulesBody()
    ocr_head=OCRRulesHead()
    build_res = OCRBuildResult()
    repair_key = '工作票'
    repair_value ='抢修'
    k_error =  "图片质量不佳，或者图片不符合规范，或者图片缺失表头，保证图片要清晰，表格平整。"
    
    #初始坐标 没有找到head返回
    first_suffix =  all_index[0][-1]
    if first_suffix!='head':
        raise RuntimeError(k_error)
    #检测 表头不符合规则
    table_first=ocr_rules.find_adjacent_rect(all_index[0],all_index,2,False)
    if len(table_first)!=2:
        raise RuntimeError(k_error)
    #其他坐标
    four_list = ocr_rules.find_cover_rect(table_first[0],all_index)
    if len(four_list)!=4:
        raise RuntimeError(k_error)
    #检测 找到head，但是过长返回
    flag = ocr_rules.optimization_head(img_name[0],coord_img_path[0],table_engine)
    if flag:
        raise RuntimeError(k_error)
    #识别结果
    ocr_result=ocr_rules.option_res(coord_img_path,img_name,table_engine)
    head_ls = ocr_result.list_filter[0]
    #初始化
    build_res.table_type = repair_key
    build_res.name = name
    build_res.uuid = uuid
    build_res.table_head = comm_rules.get_head_txt(repair_value,head_ls)
    all_index = ocr_result.index_
    all_txt = ocr_result.list_no_filter
    #开始匹配
    s1,s2,s3,s6=comm_rules.get_merge_lattice_txt(ocr_rules.get_txt_from_index([four_list[0]],all_txt))
    ocr_body.work_task = ocr_rules.get_txt_from_index([four_list[1]],all_txt)
    ocr_body.measure_other= ocr_rules.get_txt_from_index([four_list[2]],all_txt)
    ocr_head = OCRRulesHead(guardian=s1,telephone=s2,dept=s3,duty_number=s6)
    
    build_res.ocr_body = ocr_body
    build_res.ocr_head = ocr_head
    return build_res.__dict__()




