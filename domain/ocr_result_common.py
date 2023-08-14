class OCRCommon:
    def __init__(self, name=None, coordinates=None, txt_result=None,txt_rate=None,uuid=None):
        self._name = name
        self._coordinates = coordinates
        self._txt_result = txt_result
        self._txt_rate=txt_rate
        self._uuid = uuid

    # 原始名称属性的set/get方法
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    # bbox属性的set/get方法
    @property
    def coordinates(self):
        return self._coordinates

    @coordinates.setter
    def coordinates(self, value):
        self._coordinates = value

    # txt_result属性的set/get方法
    @property
    def txt_result(self):
        return self._txt_result

    @txt_result.setter
    def txt_result(self, value):
        self._txt_result = value
        
    
    # txt_rate属性的set/get方法
    @property
    def txt_rate(self):
        return self.txt_rate

    @txt_rate.setter
    def txt_result(self, value):
        self._txt_rate = value
    
    # uuid属性的set/get方法
    @property
    def uuid(self):
        return self.uuid

    @uuid.setter
    def txt_result(self, value):
        self._uuid = value
        
        
    def __dict__(self):
        return {
            "coordinates": self._coordinates,
            "txt_result": self._txt_result,
            "name": self._name,
            "txt_rate": self._txt_rate,
            "uuid":self._uuid
        }

class OCRAll:
    def __init__(self, name=None, bbox=None, result=None,suffix=None,bbox_path=None):
        self._name = name
        self._bbox = bbox
        self._result = result
        self._suffix=suffix
        self._bbox_path = bbox_path
        
    def __dict__(self):
        return {
            "bbox": self._bbox,
            "result": self._result,
            "name": self._name,
            "suffix": self._suffix,
            "bbox_path":self._bbox_path
        }
    
    # 原始名称属性的set/get方法
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    # bbox属性的set/get方法
    @property
    def bbox(self):
        return self._bbox

    @bbox.setter
    def bbox(self, value):
        self._bbox = value

    # txt_result属性的set/get方法
    @property
    def result(self):
        return self._result

    @result.setter
    def txt_result(self, value):
        self._result = value
        
    @property
    def suffix(self):
        return self._suffix

    @suffix.setter
    def suffix(self, value):
        self._suffix = value
        
    
    @property
    def bbox_path(self):
        return self._suffix

    @bbox_path.setter
    def bbox_path(self, value):
        self._bbox_path = value