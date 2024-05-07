import os
import shutil
import base64
from config.file_config import FileConfig

file_config=FileConfig()

# 获取文件扩展名
def get_extension_file(file_name):
    file_extension = os.path.splitext(file_name)[1]
    return file_extension

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
        

def encode_image(file):
    with open(file,'rb') as f:
        img_data = f.read()
        base64_data = base64.b64encode(img_data)
        #print(base64_data)
        # 如果想要在浏览器上访问base64格式图片，需要在前面加上：data:image/jpeg;base64,
        return base64_data

    
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

def list_dir(dir_path):
    '''
        通过 listdir 得到的是仅当前路径下的文件名，不包括子目录中的文件，如果需要得到所有文件需要递归
    '''
    res=[]
    for i in os.listdir(dir_path):
        file_path = os.path.join(dir_path, i)
        if os.path.isdir(file_path):
            res.append(file_path)
    return res
def listdir(path, coord_img_path):  # 传入存储的list
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            listdir(file_path, coord_img_path)
        else:
            coord_img_path.append(file_path)
            
def list_one_dir(path, coord_img_path):  # 传入存储的list
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            continue
        else:
            coord_img_path.append(file_path)
            
def get_file_name(coord_img_path):
    img_name=[]
    for name in coord_img_path:
        filename = os.path.basename(name)
        s=filename.split('.')[0]
        img_name.append(s)
    return img_name

def sort_file_path(coord_img_path):
    res = []
    for i in coord_img_path:
        filename = os.path.basename(i)
        s=filename.split('.')[0].split('_')[0]
        res.append((int(s),i))
    tmp=[]
    res = sorted(res,key=lambda x:x[0])
    for i in  res:
        tmp.append(i[1])
    return tmp
    

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

def uuid_save_video_img(uuid,suffix):
    root=uuid_save_root(uuid)+"/"
    di=root+file_config.cv_video_img_name+suffix
    os.makedirs(os.path.dirname(root), exist_ok=True)
    return di

def uuid_save_mkdir_video_frame(uuid):
    root=uuid_save_root(uuid)
    frame=root+"/"+file_config.frame
    os.makedirs(frame, exist_ok=True)
    return frame

def uuid_save_web_file(file,uuid):
    suffix=get_extension_file(file_name=file.filename)
    di = uuid_save_video_img(uuid,suffix)
    file.save(di)
    return di

def uuid_save_img(uuid,name):
    root=uuid_save_root(uuid)+"/"+name
    return root

def uuid_save_root(uuid):
    path=parent_path()
    root=path+"/"+file_config.save_path+"/"+uuid
    os.makedirs(root, exist_ok=True)
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

def uuid_save_rotate_img(uuid):
    root=uuid_save_root(uuid)+"/"
    di=root+file_config.cv_rotate_img
    os.makedirs(os.path.dirname(root), exist_ok=True)
    return di

def uuid_save_compress_img(uuid):
    root=uuid_save_root(uuid)+"/"
    di=root+file_config.cv_compress_img
    os.makedirs(os.path.dirname(root), exist_ok=True)
    return di

def uuid_save_draw_rect_img(uuid):
    root=uuid_save_root(uuid)+"/"
    di=root+file_config.cv_draw_max_rect
    os.makedirs(os.path.dirname(root), exist_ok=True)
    return di

def uuid_save_transform_img(uuid):
    root=uuid_save_root(uuid)+"/"
    di=root+file_config.cv_transform_img
    os.makedirs(os.path.dirname(root), exist_ok=True)
    return di


def uuid_save_line_img(uuid):
    root=uuid_save_root(uuid)+"/"
    di=root+file_config.cv_border_lines_img
    os.makedirs(os.path.dirname(root), exist_ok=True)
    return di


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
