import cv2 as cv
import numpy as np


img = cv.imread('apples.jpg')


gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

blur_std = cv.GaussianBlur(gray, (3, 3), 0)

blur_for_contour = cv.GaussianBlur(gray, (7, 7), 0)


grad_x = cv.Sobel(blur_std, cv.CV_16S, 1, 0, ksize=3)
grad_y = cv.Sobel(blur_std, cv.CV_16S, 0, 1, ksize=3)
abs_x = cv.convertScaleAbs(grad_x)
abs_y = cv.convertScaleAbs(grad_y)
sobel_res = cv.addWeighted(abs_x, 0.5, abs_y, 0.5, 0)


canny_res = cv.Canny(blur_std, 50, 150)


contour_base = cv.Canny(blur_for_contour, 30, 100)


kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5))
morphed = cv.morphologyEx(contour_base, cv.MORPH_CLOSE, kernel, iterations=2)


contours, _ = cv.findContours(morphed, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

contour_img = img.copy()
for cnt in contours:

    if cv.contourArea(cnt) > 200:

        cv.drawContours(contour_img, [cnt], -1, (0, 255, 0), 2)


cv.imshow('1. Sobel Magnitude', sobel_res)
cv.imshow('2. Canny Edge', canny_res)
cv.imshow('3. Final Smooth Boundary', contour_img)

cv.imwrite('result_1_sobel.jpg', sobel_res)
cv.imwrite('result_2_canny.jpg', canny_res)
cv.imwrite('result_3_contour.jpg', contour_img)


cv.waitKey(0)
cv.destroyAllWindows()