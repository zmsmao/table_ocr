from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

@dataclass
class OCRCommon:
    """
    通用 OCR 识别结果基础实体类。
    使用 @dataclass 自动生成 __init__ 和基础属性绑定，替代原有的冗长 getter/setter。
    """
    name: Optional[str] = None         # 图像或任务名称
    coordinates: Optional[Any] = None  # 文本框坐标信息，通常格式为 [ [x1,y1], [x2,y2], ... ]
    txt_result: Optional[str] = None   # 识别出的具体文本内容
    txt_rate: Optional[float] = None   # 文本识别置信度/准确率
    uuid: Optional[str] = None         # 任务唯一标识符

    def to_dict(self) -> Dict[str, Any]:
        """
        将对象序列化为字典格式。
        注：原代码重写了 __dict__() 方法，这在 Python 中会引发内置属性冲突，
        此处统一重构为标准的 to_dict() 实例方法。
        """
        return asdict(self)

@dataclass
class OCRAll:
    """
    全量表格/图像切片 OCR 识别结果实体类。
    """
    name: Optional[str] = None         # 图像或任务名称
    bbox: Optional[Any] = None         # 切片的全局边界框坐标
    result: Optional[Any] = None       # 该切片内的具体 OCR 识别结果（通常包含多个 OCRCommon 对象）
    suffix: Optional[str] = None       # 图像文件后缀名
    bbox_path: Optional[str] = None    # 对应切片图像的物理存储路径

    def to_dict(self) -> Dict[str, Any]:
        """将全量识别结果对象序列化为字典格式"""
        return asdict(self)