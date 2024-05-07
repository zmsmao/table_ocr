class FileConfig:
    # 存储主图
    main='main'
    # 存储cv优化图
    other='other'
    #存储视频帧
    frame='frame'
    # 存储分隔图
    coord='coord'
    # 存储识别结果
    txt_result='txt_result'
    # 存储路径
    save_path='io/save_path'
    # 缓存图像
    img_cache='cache'
    # 缓存图像名称
    cv_img='cv.jpg'
    #前缀
    suffix_jpg='.jpg'
    #二次分隔
    split_path='split'
    #二次分隔存储位置
    split_write='write'
    #是否删除源图片和分隔图片
    is_delete_file=False
    
    cv_rotate_img='rotate_cv.jpg'
    
    cv_compress_img = 'compress_cv.jpg'
    
    cv_transform_img = 'transform_cv.jpg'
    
    cv_intelligence_img = 'intelligence_cv.jpg'
    
    cv_border_lines_img = 'lines_cv.jpg'
    
    cv_border_lines_img = 'lines_cv.jpg'
    
    cv_accept_name = ' accept_cv'
    
    cv_draw_max_rect = 'draw_cv.jpg'

    cv_video_img_name = 'video_img_cv'