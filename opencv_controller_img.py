import cv2
import numpy as np
from matplotlib import pyplot as plt
import collections 
import os

# 读取原始图像

def create_folder_if_not_exists(path):
    # 如果路径不存在，则创建路径
    if not os.path.exists(path):
        os.makedirs(path)

pixel_fault_tolerance=7

image_number='0006'

min_size = 2000

save_pp_head = './save_path/'+image_number+'/'

image = cv2.imread('./input_path/'+image_number+'.jpg', 1)

#灰度图片
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#二值化
binary = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,35, -7)
# cv2.imshow("Eroded Image",binary)
# cv2.waitKey(0)


rows,cols=binary.shape
scale = 40
#识别横线
kernel  = cv2.getStructuringElement(cv2.MORPH_RECT,(cols//scale,1))
eroded = cv2.erode(binary,kernel,iterations = 1)
#cv2.imshow("Eroded Image",eroded)
dilatedcol = cv2.dilate(eroded,kernel,iterations = 1)
cv2.imwrite(save_pp_head+"cvX.jpg",dilatedcol)

save_pp=save_pp_head+'index/'

scale = 20
kernel = cv2.getStructuringElement(cv2.MORPH_RECT,(1,rows//scale))
eroded = cv2.erode(binary,kernel,iterations = 1)
dilatedrow = cv2.dilate(eroded,kernel,iterations = 1)
cv2.imwrite(save_pp_head+"cvY.jpg",dilatedrow)

#标识交点
bitwiseAnd = cv2.bitwise_and(dilatedcol,dilatedrow)
cv2.imwrite(save_pp+"point.jpg",bitwiseAnd) #将二值像素点生成图片保存
#标识表格
merge = cv2.add(dilatedcol,dilatedrow)
# cv2.imshow("表格整体展示：",merge)
# cv2.waitKey(0)
cv2.imwrite(save_pp+"table.jpg",merge)

# 对二值化图像进行轮廓检测，得到每一个表格的轮廓
contours, _ = cv2.findContours(merge, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

# #排序
# contours=sorted(contours,key=lambda x :x[0])
# 针对每一个表格轮廓，对原图像进行裁剪，得到每个单独的单元格或表格
list_result=[]
x_set=[]
y_set=[]
x_set.append(0)
y_set.append(0)
x_result=[]
xw_result=[]
x_y_set=set()
x_y_list=[]
x_y_result=[]
for contour in contours:
    x, y, w, h = cv2.boundingRect(contour)
    i=h*w
    if i<=min_size:
        continue
    temp_index = 0
    x1=0 
    y1=0
    xw=0
    yh=0
    x1=x
    for index in range(len(x_set)):
        if abs(x-x_set[index])<=pixel_fault_tolerance:
            temp_index=index
            x1=x_set[index]
    if temp_index==0 :
        x_set.append(x)
    temp_index=0 
    xw=x+w
    for index in range(len(x_set)):
        if abs(xw-x_set[index])<=pixel_fault_tolerance:
            temp_index=index
            xw=x_set[index]
    if temp_index==0 :
        x_set.append(xw)
    temp_index=0
        
    y1=y
    for index in range(len(y_set)):
        if abs(y1-y_set[index])<=pixel_fault_tolerance:
            temp_index=index
            y1=y_set[index]
    if temp_index==0 :
        y_set.append(y1)
    temp_index=0
    yh=y+h
    for index in range(len(y_set)):
        if abs(yh-y_set[index])<=pixel_fault_tolerance:
            temp_index=index
            yh=y_set[index]
    if temp_index==0 :
        y_set.append(yh)
    temp_index=0
    temp=[(x1,y1),(x1,yh),(xw,y1),(xw,yh)]
    temp_boo=(x1,y1,xw,yh)
    if  temp_boo not in x_y_set:
        x_y_set.add(temp_boo)
        x_y_list.append((i,x1,temp,xw))
        list_result.append(temp)
        x_result.append(x1)
        x_result.append(xw)
print(list_result)

x_dict=collections.Counter(x_result)
# ys,xs = np.where(bitwiseAnd>0)
# sorted_data=test.index_(x_set,y_set,xs,ys,pixel_fault_tolerance)
# group=test.group_coordinates(sorted_data)

# if len(group[0][1])==1 and len(list_result)!=1:
#     for i in range (len(list_result)):
#         tem=group[0][1][0][0]
#         ls=list_result[i][0][0]
#         if tem==ls:
#             del list_result[i]
x_y_list=sorted(x_y_list,key=lambda x:(x[0],x[2][0]),reverse=True)
x_set=set(x_set)
y_set=set(y_set)
print(x_y_list)

x_y_remove=[]
if len(x_y_list)>1:
    for j in range(len(x_y_list)):
        if j == len(x_y_list)-1:
            continue
        x1=x_dict.get(x_y_list[j][1])
        xw=x_dict.get(x_y_list[j][3])
        if x1==1 or xw==1:
            x_y_remove.append(j)

    for k in range(len(x_y_list)):
        if k not in x_y_remove:
            x_y_result.append(x_y_list[k])
    x_y_list=x_y_result
    
if len(x_y_list)==0:
    print()
elif len(x_y_list)==1:
    x, y, w, h = cv2.boundingRect(np.array(x_y_list[0][2]))
    roi = image[y:y+h, x:x+w]
    i=h*w
    cv2.imwrite(save_pp_head+'/coordinate/'+"_"+
                str(y)+"_"+str(y+h)+"_"+
                str(x)+"_"+str(x+w)+"_coordinate.jpg",roi)
else:
    print(x_y_list)
    for j in range(1,len(x_y_list)):
        x, y, w, h = cv2.boundingRect(np.array(x_y_list[j][2]))
        roi = image[y:y+h, x:x+w]
        i=h*w
        if i>min_size:
            cv2.imwrite(save_pp_head+'/coordinate/'+"_"+str(i)+"_"+
                            str(y)+"_"+str(y+h)+"_"+
                            str(x)+"_"+str(x+w)+"_coordinate.jpg",roi)

x, y, w, h = cv2.boundingRect(np.array(x_y_list[0][2]))
roi = image[y:y+h, x:x+w]
cv2.imwrite(save_pp_head+'/main/'+"_"+
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
cv2.imwrite(save_pp_head+'/main/'+"_other_coordinate_not.jpg",roi_not)

height, width, channels = image.shape
roiH=image[0:y,0:width]
cv2.imwrite(save_pp_head+'/coordinate/'+"_"+
                str(0)+"_"+str(y)+"_"+
                str(x)+"_"+str(x+w)+"_head.jpg",roiH)
roiE=image[y+h:height,0:width]
cv2.imwrite(save_pp_head+'/coordinate/'+"_"+
                str(y+h)+"_"+str(height)+"_"+
                str(x)+"_"+str(x+w)+"_end.jpg",roiE)
print(height,width,channels)



