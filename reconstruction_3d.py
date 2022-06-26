from GUI import GUI
from HAL import HAL
import cv2
import numpy as np
import random as rdm
# Enter sequential code!

def getProjectionLine(camera_optical_center, pxl, side):
    new_pxl = [pxl[1], pxl[0], 1]
    cam_2d_point = HAL.graficToOptical(side, new_pxl)

    pt_3d = HAL.backproject(side, cam_2d_point)
    projection_vector = pt_3d[:3] - camera_optical_center

    return projection_vector
    

def drawPoint(pxl, match, l_cam_pos, r_cam_pos, l_img, r_img, l_projection_vector):
    r_projection_vector = getProjectionLine(r_cam_pos, match, "right")
    
    n = np.cross(l_projection_vector, r_projection_vector)
    A = np.array([l_projection_vector, n, - r_projection_vector])
    b = r_cam_pos - l_cam_pos

    m, c, _ = np.linalg.lstsq(A.T, b)[0]

    pt_3d = (m * l_projection_vector) + ((c / 2) * n)
    pt_3d_scene = HAL.project3DScene(pt_3d).tolist()

    l_pxl_color = l_img[pxl[0], pxl[1]]
    r_pxl_color = r_img[match[0], match[1]].tolist()
    color_sum = (l_pxl_color + r_pxl_color) // 2

    return pt_3d_scene + color_sum.tolist()[::-1]
    

def getMatching(l_img, croped, pxl):
    space = 4
    template = l_img[pxl[0] - space:pxl[0] + space + 1, pxl[1] - space:pxl[1] + space + 1]
    
    try:
        match = cv2.matchTemplate(croped, template, cv2.TM_CCOEFF_NORMED)
    except:
        return [], 0
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)

    match_point = np.array(max_loc)[::-1] + space
    return match_point, max_val


def getRectangle(u, p1, p2):
    v = p2 - p1
    return (v[1] * (u - p1[0]) / v[0]) + p1[1]


def drawStaightLine(camera_optical_center, projecion_vector, l_img, r_img, pxl):
    height = l_img.shape[0]
    width = l_img.shape[1]
    
    cv2.line(l_img, (0, pxl[1]), [width, pxl[1]], (0, 0, 255), 5, cv2.LINE_AA);
    cv2.line(r_img, (0, pxl[1]), [width, pxl[1]], (0, 255, 0), 5, cv2.LINE_AA);
    cv2.circle(l_img, (pxl[0], pxl[1]), radius=5, color=(255, 0, 0), thickness=36)
    
    
def cropImg(img_pt_1, img_pt_2, l_img, r_img):
    
    vect = img_pt_2 - img_pt_1

    rect_y = lambda x, v: (v[1] * (x - img_pt_1[0]) / v[0]) + img_pt_1[1]

    img_pt_1 = np.array([0, rect_y(0, vect)]).astype(np.int)
    img_pt_2 = np.array([l_img.shape[1], rect_y(l_img.shape[1], vect)]).astype(np.int)
    
    croped = np.zeros(l_img.shape)
    cv2.line(croped, tuple(img_pt_1), tuple(img_pt_2), (1, 1, 1), 11)
    croped = r_img * croped.astype(bool)
    return croped
    
    
def getEpipolarLine(l_camera_optical_center, r_camera_optical_center, l_projection_vector, l_img):

    
    l_projection_vector = np.append(l_projection_vector, [1])
    l_camera_optical_center = np.append(l_camera_optical_center, [1])
    r_camera_optical_center = np.append(r_camera_optical_center, [1])
    
    r_2d_projection_vector = HAL.project("right",  l_projection_vector + l_camera_optical_center)

    r_2d_projection_vector_2 = HAL.project("right",  (l_projection_vector * 10) + l_camera_optical_center)

    img_pt_1 = HAL.opticalToGrafic("right", r_2d_projection_vector)
    img_pt_2 = HAL.opticalToGrafic("right", r_2d_projection_vector_2)
    
    return img_pt_1, img_pt_2 


def reduceNumberOfPoints(l_img, selected_pxls):
    img = cv2.Canny(l_img, 100, 200)
    sum_pxl = np.sum(img == 255)
    print(f"There are {sum_pxl} white pixels on the left image")
    
    if sum_pxl < selected_pxls:
        selected_pxls = sum_pxl
    
    new_img = img.copy()
    new_img[:] = 0
    
    white_pixels = []
    
    height = img.shape[0]
    width = img.shape[1]

    for x in range(width):
        for y in range(height):
            if img[y][x] == 255:
                white_pixels.append([x, y])
                
    white_pixels = rdm.sample(white_pixels, selected_pxls)
    
    for w_pxl in white_pixels:
        new_img[w_pxl[1]][w_pxl[0]] = 255
        
    # print(f"Number of pixels choosen : {len(white_pixels)}")
    return new_img, white_pixels
    
loop = True
while True:

    if loop == True:
        loop = False
        
        l_img = HAL.getImage('left')
        r_img = HAL.getImage('right')
    
        l_cam_pos = HAL.getCameraPosition('left')
        r_cam_pos = HAL.getCameraPosition('right')
    
        print(f"Left pos : {l_cam_pos}")
        print(f"Right pos : {r_cam_pos}")
    
        reduced_img, white_pixels = reduceNumberOfPoints(l_img, 400000)
        all_results_pt = []
        
        a = 0
        for i, pxl_i in enumerate(white_pixels):
            pxl = [pxl_i[1], pxl_i[0]]
            l_projection_vector = getProjectionLine(l_cam_pos, pxl, "left")
            # drawStaightLine(r_cam_pos, l_projection_vector, l_img, r_img, pxl)
            img_pt_1, img_pt_2 = getEpipolarLine(l_cam_pos, r_cam_pos, l_projection_vector, r_img)
            croped = cropImg(img_pt_1, img_pt_2, l_img, r_img)
            match, confidence = getMatching(l_img, croped, pxl)
            # print(f"pixel number {i + 1}, conf = {confidence}")
            if confidence > 0.8:
                try:
                    a += 1
                    point = drawPoint(pxl, match, l_cam_pos, r_cam_pos, l_img, r_img, l_projection_vector)
                    # print("RESULT",pxl, " - ", point)
                    all_results_pt.append(point)
                    print(f"We have done {i + 1} points ! {a} already painted")
                except:
                    pass
        GUI.ShowAllPoints(all_results_pt)
        # GUI.showImages(l_canny, reduced_img, True)
        # GUI.showImages(croped,r_img, True)
        # GUI.showImages(l_img, mask, True)
