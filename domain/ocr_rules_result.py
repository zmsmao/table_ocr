from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

@dataclass
class OCRRulesHead:
    """
    工作票/表格头部规则提取结果实体类。
    用于结构化存储从表头提取的关键业务字段。
    """
    guardian: Optional[str] = None     # 监护人
    telephone: Optional[str] = None    # 联系电话
    dept: Optional[str] = None         # 部门名称
    duty_number: Optional[str] = None  # 职务/值班编号
    start_time: Optional[str] = None   # 任务开始时间
    end_time: Optional[str] = None     # 任务结束时间
    number: Optional[str] = None       # 表单编号
    head: Optional[str] = None         # 负责人/表头标识

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class OCRRulesBody:
    """
    工作票/表格主体规则提取结果实体类。
    用于结构化存储具体作业任务及安全措施等核心字段。
    """
    work_task: Optional[str] = None      # 工作任务描述
    measure_main: Optional[str] = None   # 主要安全措施
    measure_other: Optional[str] = None  # 其他安全措施
    responsible: Optional[str] = None    # 责任人
    other: Optional[str] = None          # 补充/其他信息
    
    # 原变量名为 all，会遮蔽 Python 内置的 all() 函数，此处重构为 all_content
    all_content: Optional[Any] = None    # 兜底或全量文本信息

    def to_dict(self) -> Dict[str, Any]:
        """
        将对象序列化为字典格式。
        在序列化时，将内部安全的变量名 'all_content' 映射回业务需要的 'all' 键，
        以保证下游 JSON 结构的兼容性。
        """
        d = asdict(self)
        d['all'] = d.pop('all_content')
        return d
        
@dataclass
class OCRRulesResult:
    """
    规则匹配过程中的中间态数据存储类。
    用于暂存过滤前后的文本片段及索引信息。
    """
    listsr: Optional[Any] = None                     # 原始识别结果列表
    index_: Optional[Any] = None                     # 提取的关键字段索引集合
    list_txt_filter_pj: Optional[List[str]] = None   # 过滤特殊字符并拼接后的文本列表
    list_txt_no_filter_pj: Optional[List[str]] = None# 未过滤的原始拼接文本列表
    list_filter: Optional[List[str]] = None          # 过滤特殊字符后的单条文本列表
    list_no_filter: Optional[List[str]] = None       # 未过滤的单条文本列表
                
@dataclass
class OCRBuildResult:
    """
    最终业务层返回的整合结果装配类。
    将表头、表体、基础信息组装为前端/调用方需要的标准结构。
    """
    name: Optional[str] = None                # 原始图像名称
    uuid: Optional[str] = None                # 任务唯一标识符
    table_head: Optional[Any] = None          # 表格原始头部信息
    table_type: Optional[str] = None          # 表格类型/模板标识
    ocr_head: Optional[OCRRulesHead] = None   # 结构化提取后的头部对象
    ocr_body: Optional[OCRRulesBody] = None   # 结构化提取后的主体对象

    def to_dict(self) -> Dict[str, Any]:
        """
        装配最终的层级化字典结果。
        严格保持原有的嵌套结构，自动处理路径拼接与嵌套对象的序列化。
        """
        return {
            'img_name': str(self.name) if self.name else None,
            'uuid_path': f'io/save_path/{self.uuid}' if self.uuid else None,
            'table_head': self.table_head,
            'table_type': self.table_type,
            'table_body': {
                'head': self.ocr_head.to_dict() if self.ocr_head else None,
                'body': self.ocr_body.to_dict() if self.ocr_body else None
            }
        }