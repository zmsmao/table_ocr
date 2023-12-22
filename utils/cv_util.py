import cv2
from config.cv_config import CVConfig
import utils.file_util as fiul 
import numpy as np
import collections
import math
import os

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
            if j==0 and counterls[0][2]>0 and counterls[1][2]==0:
                continue
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
        
        # # 二次过滤：
        # if len(x_y_list)>1:
        #     x_y_remove=[]
        #     for j in range(len(x_y_list)):
        #         x1=x_dict.get(x_y_list[j][1])
        #         xw=x_dict.get(x_y_list[j][3])
        #         y1=y_dict.get(x_y_list[j][4])
        #         yh=y_dict.get(x_y_list[j][5])
        #         if (x1==1 or xw==1) and (y1==1 or yh ==1):
        #             x_y_remove.append(j)
        #     x_y_list=rm_list(x_y_list,x_y_remove)
    print({'x_y_list':x_y_list})
    return x_y_list


def get_correct(path,save_path):
    gray,image = cv_gray_path(path)
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
    cv_spilt_save(x_y_list,image,coord)
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

def cache_save_cv_gray(cache,path):
    gray,image=cv_gray_path(path)
    cv2.imwrite(cache,gray)
    img=cv2.imread(cache,1)
    return img
        

def cv_build(uuid,name):
    root,coord,main,other,txt_result=fiul.uuid_save_mkdirs(uuid)
    save_rotate=fiul.uuid_save_rotate_img(uuid)
    target_path = root+"/"+name
    #初始化
    target_path = cv_init_img(target_path,uuid)
    #调整图片
    flag_rotate = get_correct(target_path,save_rotate)
    if flag_rotate:
        target_path = save_rotate
    gray,image = cv_gray_path(target_path)
    binary=cv_adaptiveThreshold(gray)
    dilatedcol,dilatedrow=cv_x_y(other,binary)
    merge=cv_table(other,dilatedcol,dilatedrow)
    x_y_list=cv_core(merge)
    # #情空表格线
    # image = clear_border_lines(image,contours,save_line)
    cv_end_save(x_y_list,image,coord,main)
    return coord,txt_result


def cv_two_split_build(uuid,path,x_e=10,y_e=1):
    pp=fiul.uuid_cache_root(uuid)
    img_name=fiul.get_one_name(path)
    split=fiul.uuid_cache_spilt_path(uuid,img_name)
    wirte =fiul. uuid_cache_split_write(uuid,img_name)
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


def get_transform(input_path, output_path):
    # 读取原始图片
    gray,image=cv_gray_path(input_path)
    gray = cv_adaptiveThreshold(gray)
    #高斯模糊
    # gray = cv2.GaussianBlur(gray, (5, 5), 0)
    # 执行轮廓检测
    contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # 筛选最大的封闭边框
    max_contour = max(contours, key=cv2.contourArea)
    # cv2.drawContours(src, [max_contour], -1, (0, 255, 0), thickness=2)
    # 获取轮廓的外接矩形
    x, y, w, h = cv2.boundingRect(max_contour)
    # 提取四个角点
    top_left = (x, y)
    bottom_left = (w+x,y)
    top_right = (x, h+y)
    bottom_right = (x+w, h + y)
    box = np.int0([top_left,top_right,bottom_left,bottom_right])
    # 寻找最小面积矩形
    # rect = cv2.minAreaRect(max_contour)
    # box = np.int0(cv2.boxPoints(rect))
    # cv2.drawContours(src, [box], -1, (255, 255, 0), thickness=2)
    # 获取轮廓的坐标点
    # 近似轮廓为四边形
    epsilon = 0.02 * cv2.arcLength(max_contour, True)
    approx = cv2.approxPolyDP(max_contour, epsilon, True)
    #多次近似
    approx = mush_approx(approx)
    # 获取轮廓的四个端点坐标
    points = approx.squeeze().tolist()
    # 定义排序规则函数
    def contour_sort_rule(point):
        x, y = point
        # 根据越上越左、越上越右、越下越左、越下越右的顺序进行排序
        if x <= image.shape[0] // 2 and y <= image.shape[1] // 2:
            return 1  # 越左越上
        elif x > image.shape[0] // 2 and y <= image.shape[1] // 2:
            return 2  # 越右越上
        elif x <= image.shape[0] // 2 and y > image.shape[1] // 2:
            return 3  # 越左越下
        else:
            return 4  # 越右越下
    #无法近似四边形则停止变换，直接返回
    if len(points)>4:
        return False
    # 根据排序规则对坐标点进行排序
    sorted_points = sorted(points, key=contour_sort_rule)
    sorted_box = sorted(box, key=contour_sort_rule)
    # 打印排序后的坐标点
    print("透视变换----")
    x_set,y_set = get_x_y_set(sorted_points)
    if len(set(x_set))==2 and len(set(y_set))==2:
        return False
    
    # 组合角点
    res = np.float32([sorted_points[0], sorted_points[1], sorted_points[2], sorted_points[3]])
    img_size = (image.shape[1],image.shape[0])
    dst = np.float32([sorted_box[0],sorted_box[1],sorted_box[2],sorted_box[3]])
    # dst = np.float32([[0, 0], [5000 ,0], [0, 5000], [5000, 5000]])
    # 获取透视变换矩阵，进行转换
    M = cv2.getPerspectiveTransform(res, dst)
    src = cv2.warpPerspective(image, M,img_size)
    
    if check_trf_success(src):
        cv2.imwrite(output_path,src)
        return True
    return False

def get_compress(input_path, output_path,target_max_size):
    # 读取原始图片
    image = cv2.imread(input_path)

    # 获取原始图片的宽度和高度
    width = image.shape[1]
    height = image.shape[0]
    
    original_size = os.path.getsize(input_path)

    # 如果原始图片已经小于等于目标大小，则直接保存原始图片
    if original_size < target_max_size:
        return False
    
    # 计算原始图片的大小
    original_size = width * height
    # 计算压缩比例
    compression_ratio = (target_max_size*1.75 / original_size) ** 0.5
    
    if compression_ratio>=1:
        return False

    # 计算压缩后的宽度和高度
    compressed_width = int(width * compression_ratio)
    compressed_height = int(height * compression_ratio)

    # 使用二三插值法进行压缩
    compressed_image = cv2.resize(image, (compressed_width, compressed_height), interpolation=cv2.INTER_CUBIC)

    # 保存压缩后的图片
    cv2.imwrite(output_path, compressed_image)
    
    return True

def expand_cv_img(src_path):
    '''
    扩展像素,ocr提高识别度
    '''
    file_dir =os.path.dirname(src_path)
    filename = os.path.basename(src_path)
    s=filename.split('.')[0]
    fx = filename.split('.')[1]
    # # 读取原始图像
    # img = cv2.imread(src_path)
    # # 获取原始图像的宽度和高度
    # original_height, original_width = img.shape[:2]
    # # 扩展后的边框大小
    # border_size = 10
    # # 计算扩展后的宽度和高度
    # expanded_width = original_width + 2 * border_size
    # expanded_height = original_height + 2 * border_size
    # # 创建扩展后的图像
    # expanded_img = cv2.resize(img, (expanded_width, expanded_height))
    
    # # 读取原始图像
    # expansion_factor = 1.21
    # original_image = cv2.imread(src_path)

    # # 获取原始图像的宽度和高度
    # original_height, original_width = original_image.shape[:2]

    # # 计算扩展后的图像的目标宽度和高度
    # target_width = int(original_width * expansion_factor)
    # target_height = int(original_height * expansion_factor)

    # # 计算水平和垂直的填充量
    # horizontal_padding = int((target_width - original_width) / 2)
    # vertical_padding = int((target_height - original_height) / 2)

    # 创建一个新的扩展后大小的空白图像
    # expanded_img = cv2.copyMakeBorder(original_image, vertical_padding, vertical_padding,
    #                                     horizontal_padding, horizontal_padding, cv2.BORDER_CONSTANT,value=[255,255,255])
    img = cv2.imread(src_path)
    # height, width, channels = img.shape
    # img=img[1:height-1,1:width-1]
    top = 6  # 顶部边框大小
    bottom = 14  # 底部边框大小
    left = 10 # 左侧边框大小
    right = 10  # 右侧边框大小
    # 使用cv2.copyMakeBorder()函数扩展图像
    expanded_img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    tmp = file_dir+"\_tmp."+fx
    cv2.imwrite(tmp,expanded_img)
    return tmp

def check_trf_success(gray):
    #再次检测
    #执行轮廓检测
    gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    gray = cv_adaptiveThreshold(gray)
    # try:
    contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # except:
    #     return False
    # 筛选最大的封闭边框
    max_contour = max(contours, key=cv2.contourArea)
    epsilon = 0.02 * cv2.arcLength(max_contour, True)
    approx = cv2.approxPolyDP(max_contour, epsilon, True)
    #多次近似
    approx = mush_approx(approx)
    # 获取轮廓的四个端点坐标
    points = approx.squeeze().tolist()
    #无法近似四边形则停止变换，直接返回
    if len(points)>4:
        return False
    print("透视变换check----")
    x_set,y_set = get_x_y_set(points)
    if len(set(x_set))!=2 and len(set(y_set))!=2:
        return False
    return True

def mush_approx(approx):
    #多次近似
    if len(approx) > 4:
    # 寻找最小面积的四边形
        hull = cv2.convexHull(approx)
        if len(hull) == 4:
            approx = hull
        else:
            hull = cv2.convexHull(hull)
            approx = hull
    if len(approx) >4:
        hull = cv2.convexHull(approx)
        if len(hull) == 4:
            approx = hull
        else:
            hull = cv2.convexHull(hull)
            approx = hull
    return approx
            
def get_x_y_set(points):
    x_set=[]
    y_set=[]
    for point in points:
        x, y = point
        print(f"Point: ({x}, {y})")
        temp_index=0
        y1=y
        for index in range(len(y_set)):
            if abs(y1-y_set[index])<=CVConfig.pixel_fault_tolerance:
                temp_index=index
                y1=y_set[index]
        if temp_index==0 :
            y_set.append(y1)
        temp_index=0
        x1=x
        for index in range(len(x_set)):
            if abs(x1-x_set[index])<=CVConfig.pixel_fault_tolerance:
                temp_index=index
                x1=x_set[index]
        if temp_index==0 :
            x_set.append(x1)
    return x_set,y_set

def clear_border_lines(image,contours,save_line):
    for i in contours:
        cv2.drawContours(image, [i], 0, (255, 255, 255), 2)
    cv2.imwrite(save_line,image)
    gray,image = cv_gray_path(save_line)
    return image

def cv_init_img(src_path,uuid):
    '''
    初始化优化图片，使用压缩和透视变换
    '''
    save_compress=fiul.uuid_save_compress_img(uuid)
    save_transform = fiul.uuid_save_transform_img(uuid)
    target = src_path
    #压缩图片
    flag_compress = get_compress(target,save_compress,CVConfig.cv_compress)
    if flag_compress:
        target = save_compress
    #透视转化
    flag_transform=get_transform(target,save_transform)
    if flag_transform:
        target = save_transform
    return target
    