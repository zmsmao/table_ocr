import utils.common_util as comm
from domain.ocr_rules_result import OCRRulesHead
import rules.common.ocr_rules as ocr_rules

def get_number_txt(txt):
    chinese_pj=comm.filter_chinese_punctuation(txt)
    _,end=comm.find_substring_positions(chinese_pj,'编号')
    ors=chinese_pj[end+1:len(chinese_pj)]
    return ors

def get_head_txt(src_txt,head_ls):
    for i in head_ls:
        if i.find(src_txt)!=-1:
            return i

def get_merge_time_txt(txt):
    s4=''
    s5=''
    if txt.find('年')!=-1:
        start,end=comm.find_substring_positions(txt,'至')
        s4 = txt[1:start]
        s5= txt[start+1:len(txt)] 
        if start == 1:
            start_min,end_min=comm.find_substring_positions(txt,'分')
            s4 = txt[start+1:start_min]
            s5= txt[start_min+1:len(txt)] 
        elif txt[0].isdigit():
            s4 = txt[:start]
            s5= txt[start+1:len(txt)] 
        if s4[0].isdigit() and int(s4[0])!=2:
                s4=s4[1:]
    return s4,s5

def get_merge_lattice_txt(txt):
    s1='' 
    s2='' 
    s3=''
    s6=''
    if txt.find('人')!=-1:
        sk = comm.extract_numbers(txt)
        if len(sk)==2:
                s2=sk[0]
                s6=sk[1]
        if len(sk)==1:
            if len(sk[0])>4:
                s2=sk[0]
            else:
                s6=sk[0]
        no_sk = comm.filter_numbers(txt)
        tp=no_sk.find('和')
        index=tp-2
        start,end=comm.find_substring_positions(no_sk,'监护人')
        s1=no_sk[end+1:index].replace('电话',',')
        index_s = no_sk.find('组')
        ts = no_sk[index_s+1:len(txt)]
        start,end=comm.find_substring_positions(ts,'负')
        s3=ts[:start-2]
    return s1,s2,s3,s6

def get_dispersed_lattice_txt(src_list,all_txt):
    s1='' 
    s2='' 
    s3=''
    s6=''
    first=all_txt[src_list[0]]
    second = all_txt[src_list[1]]
    third = all_txt[src_list[2]]
    fourth= all_txt[src_list[3]]
    start,end=comm.find_substring_positions(first,'人')
    s1 = first[end+1,len(first)]
    s2 = comm.extract_numbers(second)[0]
    start,end=comm.find_substring_positions(third,'组')
    s3 = third[end+1,len(third)]
    s6 = comm.extract_numbers(fourth)[0]
    return s1,s2,s3,s6

def get_dispersed_time(src_list,all_txt):
    s4=''
    s5=''
    res=[]
    for i in src_list:
        tmp = all_txt[i]
        if len(tmp)>0:
            res.append(i)
    first=all_txt[res[0]]
    second = all_txt[res[1]]
    s4 = first[1:len(first)]
    s5 = second[1:len(second)]
    return s4,s5

def build_merge_table_head(lattice_txt,time_txt):
    s1,s2,s3,s6 = get_merge_lattice_txt(lattice_txt)
    s4,s5 = get_merge_time_txt(time_txt)
    result = OCRRulesHead(guardian=s1,telephone=s2,dept=s3,duty_number=s6,start_time=s4,end_time=s5)
    return result

def build_dispersed_table_head(lattice_index,time_index,all_txt):
    s1,s2,s3,s6 = get_dispersed_lattice_txt(lattice_index,all_txt)
    s4,s5 = get_dispersed_time(time_index,all_txt)
    result = OCRRulesHead(guardian=s1,telephone=s2,dept=s3,duty_number=s6,start_time=s4,end_time=s5)
    return result

def find_time_lattice(mid_index,all_index):
    lattice_index = []
    time_index = []
    lattice_list=ocr_rules.find_adjacent_rect(mid_index,all_index,3,False)
    time_list = ocr_rules.find_adjacent_rect(mid_index,all_index,4,False)
    
    for i in range(len(lattice_list)):
        lattice_index.append(lattice_list[i][1])
    
    for i in range(len(time_list)):
        time_index.append(time_list[i][1])
        
    return lattice_index,time_index