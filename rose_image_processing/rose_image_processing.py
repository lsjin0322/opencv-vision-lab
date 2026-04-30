import cv2
import numpy as np

path = 'ch3/rose.png'
img_load = cv2.imread(path)

if img_load is None:
    print(f"이미지를 불러올 수 없습니다. 경로를 확인해주세요: {path}")
else:
    img_original = cv2.resize(img_load, dsize=(400, 300))
    cv2.imshow('1. Original (400x300)', img_original)

    
    # 원본(400x300)의 절반인 (200, 150)으로 설정
    img_resized = cv2.resize(img_original, dsize=(200, 150))
    cv2.imshow('2. Resized (200x150)', img_resized)

    
    # 축소된 이미지(200x150)를 기준으로 회전시킵니다.
    (h, w) = img_resized.shape[:2]
    center = (w // 2, h // 2)
    
    # 시계방향 회전 (-30도)
    matrix = cv2.getRotationMatrix2D(center, -30, 1.0)
    img_rotated = cv2.warpAffine(img_resized, matrix, (w, h))
    cv2.imshow('3. Rotated Image (30 deg)', img_rotated)


    print("화면에 뜬 창을 클릭하고 아무 키나 누르면 종료됩니다.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    