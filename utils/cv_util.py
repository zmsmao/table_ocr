import cv2
from config.cv_config import CVConfig
from utils.file_util import uuid_save_mkdirs,uuid_save_rotate_img,uuid_cache_root,get_one_name,uuid_cache_spilt_path,uuid_cache_split_write
import numpy as np
import collections
import math

def analyze_data(data):
    data_ = [x for x in data if x != 0]
    data_not = [x for x in data if x == 0]
    if  len(data_not)>len(data_)*2:
        return 0.0
    data = data_
    # 区分正负两部分
    positive = [x for x in data if x > 0]
    negative = [x for x in data if x < 0]
    # 选择数据量较多部分
    if len(positive) > len(negative):
        selected_data = positive
    else:
        selected_data = negative
    selected_data = list(map(float, selected_data))
        
    # 计算统计量      
    median = np.median(selected_data)
    return median

def rotate(image,angle,center=None,scale=1.0):
    (w,h) = image.shape[0:2]
    if center is None:
        center = (w//2,h//2)   
    wrapMat = cv2.getRotationMatrix2D(center,angle,scale)    
    return cv2.warpAffine(image,wrapMat,(h,w))

def is_inside(src, dst):
    src_x = [p[0] for p in src]
    src_y = [p[1] for p in src]

    dst_x = [p[0] for p in dst]
    dst_y = [p[1] for p in dst]

    return (max(dst_x) <= max(src_x) and min(dst_x) >= min(src_x) and
            max(dst_y) <= max(src_y) and min(dst_y) >= min(src_y))
    
def rm_list(x_y_list,x_y_remove):
    x_y_result=[]
    for k in range(len(x_y_list)):
        if k not in x_y_remove:
            x_y_result.append(x_y_list[k])
    return x_y_result

#灰度化
def cv_gray(root,name):
    image = cv2.imread(root+"/"+name)
    # 裁剪图片
    if CVConfig.cv_is_split:
        height, width, channels = image.shape
        roi=image[CVConfig.cv_y_head_split:height-CVConfig.cv_y_end_split
                    ,CVConfig.cv_x_right_split:width-CVConfig.cv_x_left_split]
        cv2.imwrite(root+"/"+name,roi)
        img=cv2.imread(root+"/"+name,1)
        image=img
    #灰度图片
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray,image

def cv_gray_path(path):
    image = cv2.imread(path, 1)
    #灰度图片
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray,image

#二值化
def cv_adaptiveThreshold(gray):
    binary = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,35, -7)
    return binary

#识别横竖线
def cv_x_y(other,binary,x_eroded=1,y_eroded=1):
    rows,cols=binary.shape
    scale = 40
    #识别横线
    kernel  = cv2.getStructuringElement(cv2.MORPH_RECT,(cols//scale,1))
    eroded = cv2.erode(binary,kernel,iterations = y_eroded)
    dilatedcol = cv2.dilate(eroded,kernel,iterations = 1)
    cv2.imwrite(other+"cvX.jpg",dilatedcol)

    scale = 40
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT,(1,rows//scale))
    eroded = cv2.erode(binary,kernel,iterations = x_eroded)
    dilatedrow = cv2.dilate(eroded,kernel,iterations = 1)
    cv2.imwrite(other+"cvY.jpg",dilatedrow)

    return dilatedcol,dilatedrow

#识别表格
def cv_table(other,dilatedcol,dilatedrow):
    #标识交点
    bitwiseAnd = cv2.bitwise_and(dilatedcol,dilatedrow)
    cv2.imwrite(other+CVConfig.cv_point,bitwiseAnd) #将二值像素点生成图片保存
    #标识表格
    merge = cv2.add(dilatedcol,dilatedrow)
    # cv2.imshow("表格整体展示：",merge)
    # cv2.waitKey(0)
    cv2.imwrite(other+CVConfig.cv_table,merge)
    
    return merge

def cv_core(merge):
    # 对二值化图像进行轮廓检测，得到每一个表格的轮廓
    contours, _ = cv2.findContours(merge, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # 得到原始过滤坐标
    list_result=[]
    # 统一化x,y
    x_set=[]
    y_set=[]
    x_set.append(0)
    y_set.append(0)
    # 记录x，y坐标
    x_result=[]
    y_result=[]
    # 过滤坐标
    x_y_set=set()
    # 排序过滤之后的最终坐标
    x_y_list=[]
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        i=h*w
        # 过滤像素过小的图像
        temp_index = 0
        x1=0 
        y1=0
        xw=0
        yh=0
        x1=x
        for index in range(len(x_set)):
            if abs(x-x_set[index])<=CVConfig.pixel_fault_tolerance:
                temp_index=index
                x1=x_set[index]
        if temp_index==0 :
            x_set.append(x)
        temp_index=0 
        xw=x+w
        for index in range(len(x_set)):
            if abs(xw-x_set[index])<=CVConfig.pixel_fault_tolerance:
                temp_index=index
                xw=x_set[index]
        if temp_index==0 :
            x_set.append(xw)
        temp_index=0
            
        y1=y
        for index in range(len(y_set)):
            if abs(y1-y_set[index])<=CVConfig.pixel_fault_tolerance:
                temp_index=index
                y1=y_set[index]
        if temp_index==0 :
            y_set.append(y1)
        temp_index=0
        yh=y+h
        for index in range(len(y_set)):
            if abs(yh-y_set[index])<=CVConfig.pixel_fault_tolerance:
                temp_index=index
                yh=y_set[index]
        if temp_index==0 :
            y_set.append(yh)
        temp_index=0
        # 构建坐标
        temp=[(x1,y1),(x1,yh),(xw,y1),(xw,yh)]
        # 构建set可识别的坐标
        temp_boo=(x1,y1,xw,yh)
        if  temp_boo not in x_y_set:
            i=abs(y1-yh)*abs(x1-xw)
            if i>CVConfig.min_size:
                x_y_set.add(temp_boo)
                # 构建可排序的坐标
                x_y_list.append((i,x1,temp,xw,y1,yh))
                list_result.append(temp)
                x_result.append(x1)
                x_result.append(xw)
                y_result.append(y1)
                y_result.append(yh)
    #统计x出现的次数
    x_dict=collections.Counter(x_result)
    y_dict=collections.Counter(y_result)
    x_y_list=sorted(x_y_list,key=lambda x:(x[0],x[2][0]),reverse=True)
    x_set=set(x_set)
    y_set=set(y_set)
    #统计节点
    def new_ps(x_y_list):
        counterls=[]
        for i in range(len(x_y_list)):
            number=0
            for u in range(i+1,len(x_y_list)):
                if is_inside(x_y_list[i][2],x_y_list[u][2]):
                    number+=1
            counterls.append((x_y_list[i][0],x_y_list[i][2],number))
        return counterls
    counterls=new_ps(x_y_list)
    print({'counterls':counterls})
    # 中间变量
    x_y_remove=[]
    x_y_list_rm=[]
    if len(x_y_list)>1:
        for j in range(len(x_y_list)):
            x1=x_dict.get(x_y_list[j][1])
            xw=x_dict.get(x_y_list[j][3])
            y1=y_dict.get(x_y_list[j][4])
            yh=y_dict.get(x_y_list[j][5])
            if (x1==1 or xw==1) and (y1==1 or yh ==1):
                x_y_remove.append(j)
        #散列式表单情况
        if len(x_y_remove)<len(x_y_list):
            x_y_list=rm_list(x_y_list,x_y_remove)
        else:
            x_y_remove=[]
            lens=len(x_y_list)-1
            for u in range(0,len(x_y_list)-1):
                if is_inside(x_y_list[u][2],x_y_list[u+1][2]):
                    continue
                else:
                    lens=u
                    break
            x_y_list = [x_y_list[lens]]
        # 计算小表格是否在主表格里或者是已存在于原表格
        if len(x_y_list)>1:
            x_y_remove=[]
            for j in range(len(x_y_list)):
                if is_inside(x_y_list[0][2],x_y_list[j][2]):
                    continue
                else:
                    x_y_remove.append(j)
            x_y_list=rm_list(x_y_list,x_y_remove)
        
        # 二次过滤：
        if len(x_y_list)>1:
            x_y_remove=[]
            for j in range(len(x_y_list)):
                x1=x_dict.get(x_y_list[j][1])
                xw=x_dict.get(x_y_list[j][3])
                y1=y_dict.get(x_y_list[j][4])
                yh=y_dict.get(x_y_list[j][5])
                if (x1==1 or xw==1) and (y1==1 or yh ==1):
                    x_y_remove.append(j)
            x_y_list=rm_list(x_y_list,x_y_remove)
    print({'x_y_list':x_y_list})
    return x_y_list


def get_correct(root,name,save_path):
    gray,image = cv_gray(root,name)
    #腐蚀、膨胀
    kernel = np.ones((5,5),np.uint8)
    erode_Img = cv2.erode(gray,kernel)
    eroDil = cv2.dilate(erode_Img,kernel)
    # showAndWaitKey("eroDil",eroDil)
    #边缘检测
    canny = cv2.Canny(eroDil,50,150)
    # showAndWaitKey("canny",canny)
    #霍夫变换得到线条
    lines = cv2.HoughLinesP(canny, 0.8, np.pi / 180, 90,minLineLength=100,maxLineGap=10)
    #画出线条
    ls=[]
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if(x1!=x2):
            k = float((y1-y2)/(x1-x2))
            ls.append(k)
    # 斜率
    """
    计算角度,因为x轴向右，y轴向下，所有计算的斜率是常规下斜率的相反数，我们就用这个斜率（旋转角度）进行旋转
    """
    median=analyze_data(ls)
    if median!=0.0:
        k = median
        angle = np.degrees(math.atan(k))
        print('旋转的角度为：'+str(angle))
        """
        旋转角度大于0，则逆时针旋转，否则顺时针旋转
        """
        rotateImg = rotate(image,angle)
        cv2.imwrite(save_path,rotateImg)
        return True
    return False
        
def cv_end_save(x_y_list,image,coord,main):
    size_i=cv_spilt_save(x_y_list,image,coord)
    x, y, w, h = cv2.boundingRect(np.array(x_y_list[0][2]))
    roi = image[y:y+h, x:x+w]
    cv2.imwrite(main+'/'+"_"+
                    str(y)+"_"+str(y+h)+"_"+
                    str(x)+"_"+str(x+w)+"_main.jpg",roi)
    # 创建一个与原始图像大小相同的掩膜
    mask = np.zeros_like(image)
    # 在掩膜上绘制矩形
    cv2.rectangle(mask, (x, y), (x + w, y + h), (255, 255, 255), -1)
    # 对掩膜进行反转
    mask = cv2.bitwise_not(mask)
    # 获取除给定坐标以外的图像
    roi_not = cv2.bitwise_and(image, mask)
    cv2.imwrite(main+'/'+"_other_coordinate_not.jpg",roi_not)

    height, width, channels = image.shape
    if y>0:
        roiH=image[0:y,0:width]
        i=(y-0)*width
        if i>CVConfig.min_size/2:
            cv2.imwrite(coord+'/'+
                            str(0)+"_"+str(y)+"_"+
                            str(x)+"_"+str(x+w)+"_"+str(i)+"_head.jpg",roiH)
    if (height-y-h)>0:
        roiE=image[y+h:height,0:width]
        i=(height-y-h)*width
        if i>CVConfig.min_size/2:
            cv2.imwrite(coord+'/'+
                            str(y+h)+"_"+str(height)+"_"+
                            str(x)+"_"+str(x+w)+"_"+str(i)+"_end.jpg",roiE)


def cv_spilt_save(x_y_list,image,path):
    size_i=[]
    if len(x_y_list)==0:
        print()
    elif len(x_y_list)==1:
        x, y, w, h = cv2.boundingRect(np.array(x_y_list[0][2]))
        roi = image[y:y+h, x:x+w]
        i=h*w
        cv2.imwrite(path+'/'+
                    str(y)+"_"+str(y+h)+"_"+
                    str(x)+"_"+str(x+w)+"_"+str(i)+"_coordinate.jpg",roi)
    else:
        for j in range(1,len(x_y_list)):
            xt=x_y_list[j][2][0][0]
            yt=x_y_list[j][2][0][1]
            xwt=x_y_list[j][2][3][0]
            yht=x_y_list[j][2][3][1]
            x, y, w, h = cv2.boundingRect(np.array(x_y_list[j][2]))
            roi = image[y:y+h, x:x+w]
            i=h*w
            if i>CVConfig.min_size:
                cv2.imwrite(path+'/'+
                                str(yt)+"_"+str(yht)+"_"+
                                str(xt)+"_"+str(xwt)+"_"+str(i)+"_coordinate.jpg",roi)
                size_i.append(i)
    return size_i

def cache_save_cv_gray(cache,path):
    gray,image=cv_gray_path(path)
    cv2.imwrite(cache,gray)
    img=cv2.imread(cache,1)
    return img
        

def cv_build(uuid,name):
    root,coord,main,other,txt_result=uuid_save_mkdirs(uuid)
    gray,image=cv_gray(root,name)
    save_rotate=uuid_save_rotate_img(uuid)
    #调整图片
    flag = get_correct(root,name,save_rotate)
    if flag:
        gray,image=cv_gray_path(save_rotate)
    binary=cv_adaptiveThreshold(gray)
    dilatedcol,dilatedrow=cv_x_y(other,binary)
    merge=cv_table(other,dilatedcol,dilatedrow)
    x_y_list=cv_core(merge)
    cv_end_save(x_y_list,image,coord,main)
    return coord,txt_result


def cv_two_split_build(uuid,path,x_e=10,y_e=1):
    pp=uuid_cache_root(uuid)
    img_name=get_one_name(path)
    split=uuid_cache_spilt_path(uuid,img_name)
    wirte = uuid_cache_split_write(uuid,img_name)
    image=cv2.imread(path,1)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary=cv_adaptiveThreshold(gray)
    dilatedcol,dilatedrow=cv_x_y(pp+"/",binary,x_eroded=x_e,y_eroded=y_e)
    x_set=[0]
    ys,xs=np.where(dilatedrow>0)
    for i in xs:
        temp_index=0
        for index in range(len(x_set)):
            if abs(i-x_set[index])<=CVConfig.pixel_fault_tolerance:
                temp_index=index
        if temp_index==0 :
                x_set.append(i)
    x_set=sorted(list(set(x_set)))
    x_set=x_set[1:len(x_set)-1]
    height, width, channels = image.shape
    roiH = image[0:height,0:x_set[0]]
    i=height*x_set[0]
    cv2.imwrite(split+'/'+
                                str(0)+"_"+str(height)+"_"+
                                str(0)+"_"+str(x_set[0])+"_"+str(i)+"_coordinate.jpg",roiH)
    roiE = image[0:height,x_set[len(x_set)-1]:width]
    ed=width-x_set[len(x_set)-1]
    i=height*ed
    cv2.imwrite(split+'/'+
                                str(0)+"_"+str(height)+"_"+
                                str(x_set[len(x_set)-1])+"_"+str(width)+"_"+str(i)+"_coordinate.jpg",roiE)
    for i in range(len(x_set)-1):
        roi = image[0:height,x_set[i]:x_set[i+1]]
        ed=x_set[i+1]-x_set[i]
        cv2.imwrite(split+'/'+
                                    str(0)+"_"+str(height)+"_"+
                                    str(x_set[i])+"_"+str(x_set[i+1])+"_"+str(ed)+"_coordinate.jpg",roi)
    return split,wirte


