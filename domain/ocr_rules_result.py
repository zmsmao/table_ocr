class OCRRulesHead:
        def __init__(self, guardian=None,telephone=None
                , dept=None,duty_number=None,start_time=None,end_time=None,number=None,head=None):
                self.guardian = guardian
                self.telephone = telephone
                self.dept=dept
                self.duty_number=duty_number
                self.start_time=start_time
                self.end_time=end_time
                self.number=number
                self.head=head
                
        def __dict__(self):
                return {
                "guardian": self.guardian,
                "telephone": self.telephone,
                "dept": self.dept,
                "duty_number": self.duty_number,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "number": self.number,
                "head": self.head
                }
class OCRRulesBody:
        def __init__(self, work_task=None,measure_main=None,measure_other=None,responsible=None
        ,other=None,all=None):
                self.work_task = work_task
                self.measure_main = measure_main
                self.measure_other = measure_other
                self.other=other
                self.all=all
                self.responsible=responsible
        def __dict__(self):
                return {
                "work_task": self.work_task,
                "measure_main": self.measure_main,
                "measure_other": self.measure_other,
                "other": self.other,
                "all": self.all,
                "responsible": self.responsible
                }
        
class OCRRulesResult:
        # (listsr,index_,list_txt_filter_pj,list_txt_no_filter_pj,list_filter,list_no_filter)
        def __init__(self,listsr=None,index_=None,list_txt_filter_pj=None,list_txt_no_filter_pj=None,list_filter=None,list_no_filter=None):
                self.listsr=listsr
                self.index_=index_
                self.list_txt_filter_pj=list_txt_filter_pj
                self.list_txt_no_filter_pj=list_txt_no_filter_pj
                self.list_filter=list_filter
                self.list_no_filter=list_no_filter