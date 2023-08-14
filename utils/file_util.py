import os
import shutil
import base64
from config.file_config import FileConfig

file_config=FileConfig()

def save_image(base64_data, save_path):
        """
        将Base64编码的图片数据保存为图片文件
        """
        # 将Base64编码的图片数据解码为二进制数据
        image_data = base64.b64decode(base64_data)
        # 创建保存图片的文件夹
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        # 将二进制数据保存为图片文件
        try:
            with open(save_path, 'wb') as f:
                f.write(image_data)
            return True
        except Exception as e:
            print(e)
            return False
    
def extract_first_element(data):
    result = ""
    for item in data:
        if len(item) > 0:
            result += str(item[0])+"  "+str(item[1]) + "\n"
    return result

def dir_delete(dir):
    if os.path.isdir(dir):
        files=os.listdir(dir)
        os.chdir(dir)#进入指定目录
        # #删除目录下的文件
        # for file in files:
        #     os.remove(file)
        #     # print(file,"删除成功")
        os.chdir("..")#切换到外部目录
        shutil.rmtree(dir)
        print(dir,"删除成功")

def listdir(path, list_name):  # 传入存储的list
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            listdir(file_path, list_name)
        else:
            list_name.append(file_path)
            
def list_one_dir(path, list_name):  # 传入存储的list
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            continue
        else:
            list_name.append(file_path)
            
def get_file_name(list_name):
    txt_names=[]
    for name in list_name:
        filename = os.path.basename(name)
        s=filename.split('.')[0]
        txt_names.append(s)
    return txt_names

def uuid_save_mkdirs(path,uuid):
    root=path+"/"+file_config.save_path+"/"+uuid
    coord=root+"/"+file_config.coord
    main=root+"/"+file_config.main
    other=root+"/"+file_config.other
    txt_result=root+"/"+file_config.txt_result
    os.makedirs(root, exist_ok=True)
    os.makedirs(coord, exist_ok=True)
    os.makedirs(main, exist_ok=True)
    os.makedirs(other, exist_ok=True)
    os.makedirs(txt_result, exist_ok=True)
    return root,coord,main,other,txt_result

def uuid_save_mkdirs(uuid):
    root=uuid_save_root(uuid)
    coord=root+"/"+file_config.coord
    main=root+"/"+file_config.main
    other=root+"/"+file_config.other
    txt_result=root+"/"+file_config.txt_result
    os.makedirs(coord, exist_ok=True)
    os.makedirs(main, exist_ok=True)
    os.makedirs(other, exist_ok=True)
    os.makedirs(txt_result, exist_ok=True)
    return root,coord,main,other,txt_result

def uuid_save_img(uuid,name):
    root=uuid_save_root(uuid)+"/"+name
    return root

def uuid_save_root(uuid):
    path=parent_path()
    root=path+"/"+file_config.save_path+"/"+uuid
    return root

def uuid_cache_root(uuid):
    path=parent_path()
    root=path+"/"+file_config.img_cache+"/"+uuid
    return root

def uuid_cache_img(uuid):
    root=uuid_cache_root(uuid)+"/"
    di=root+file_config.cv_img
    os.makedirs(os.path.dirname(root), exist_ok=True)
    return di

def uuid_cache_split(uuid,name):
    root=uuid_cache_root(uuid)
    root=root+'/'+name
    os.makedirs(root,exist_ok=True)
    return root

def uuid_cache_write(uuid):
    root=uuid_cache_root(uuid)
    root=root+'/'+file_config.split_write
    os.makedirs(root,exist_ok=True)
    return root

def uuid_cache_spilt_path(uuid,name):
    root=uuid_cache_split(uuid,name)
    root=root+'/'+file_config.split_path
    os.makedirs(root,exist_ok=True)
    return root

def uuid_cache_split_write(uuid,name):
    root=uuid_cache_split(uuid,name)
    root=root+'/'+file_config.split_write
    os.makedirs(root,exist_ok=True)
    return root

def write_result(result_text,output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result_text)

    
def current_path():
    s=os.path.abspath(__file__)
    return s

def parent_path ():
    s=os.path.dirname(os.path.dirname(current_path()))
    return s

def get_one_name(path):
    filename = os.path.basename(path)
    s=filename.split('.')[0]
    return s
