import sys
import cv2 as cv
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer

class TrafficWeak(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('교통약자 보호: 실시간 매칭')
        self.setGeometry(100, 100, 1600, 900)

        self.signButton = QPushButton('표지판 등록', self)
        self.roadButton = QPushButton('도로 영상 불러오기', self)
        self.recognitionButton = QPushButton('인식', self)
        self.quitButton = QPushButton('나가기', self)

        self.infoLabel = QLabel('환영합니다!', self)
        self.rightLabel = QLabel(self)
        self.rightLabel.setStyleSheet("background-color: #111;")

        self.signButton.setGeometry(10, 10, 100, 30)
        self.roadButton.setGeometry(120, 10, 130, 30)
        self.recognitionButton.setGeometry(260, 10, 100, 30)
        self.quitButton.setGeometry(1480, 10, 100, 30)
        self.infoLabel.setGeometry(10, 45, 1580, 30)
        self.rightLabel.setGeometry(10, 80, 1580, 800)

        self.signButton.clicked.connect(self.signFunction)
        self.roadButton.clicked.connect(self.roadFunction)
        self.recognitionButton.clicked.connect(self.recognitionFunction)
        self.quitButton.clicked.connect(self.quitFunction)

        self.signFiles = [['ch6/SpeedLimit.png', '단속구간'], ['ch6/SchoolZone.png', '어린이보호구역']]
        self.signImgs = []
        self.roadCap = None
        self.signData = []
        self.recognizing = False
        self.lastResult = None  # ✅ 마지막 인식 결과 저장

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.processFrame)

    def showOnLabel(self, img, label):
        rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg).scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(pix)

    def signFunction(self):
        self.signImgs = [cv.imread(f[0]) for f in self.signFiles]
        self.signData = []

        sift = cv.SIFT_create(nfeatures=5000, nOctaveLayers=5,
                              contrastThreshold=0.02, edgeThreshold=20, sigma=1.4)
        for img in self.signImgs:
            gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
            gray = cv.equalizeHist(gray)
            gray = cv.GaussianBlur(gray, (3, 3), 0)
            kp, des = sift.detectAndCompute(gray, None)
            self.signData.append((img, kp, des))

        self.infoLabel.setText('표지판 등록 완료')

    def roadFunction(self):
        fname, _ = QFileDialog.getOpenFileName(self, '영상 선택', './', 'Video Files (*.mov *.mp4)')
        if fname:
            self.roadCap = cv.VideoCapture(fname)
            ret, frame = self.roadCap.read()
            if ret:
                self.currentFrame = frame
                self.showOnLabel(frame, self.rightLabel)
            self.infoLabel.setText('영상 불러오기 완료 - 인식 버튼을 누르세요')

    def processFrame(self):
        if self.roadCap is None:
            return

        fps = self.roadCap.get(cv.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        skip = int(fps * 5)
        for _ in range(skip - 1):
            self.roadCap.grab()

        ret, frame = self.roadCap.read()
        if not ret:
            self.timer.stop()
            self.recognizing = False
            self.infoLabel.setText('영상 재생 완료')
            return

        self.currentFrame = frame

        if self.recognizing:
            self.doRecognition()
        else:
            self.showOnLabel(frame, self.rightLabel)

    def recognitionFunction(self):
        if not self.timer.isActive():
            if self.roadCap is None:
                self.infoLabel.setText('먼저 영상을 불러오세요')
                return
            self.recognizing = True
            self.timer.start(30)

    def doRecognition(self):
        if not hasattr(self, 'currentFrame') or len(self.signData) == 0:
            return

        sift = cv.SIFT_create(nfeatures=5000, nOctaveLayers=5,
                              contrastThreshold=0.02, edgeThreshold=20, sigma=1.4)

        gray_road = cv.cvtColor(self.currentFrame, cv.COLOR_BGR2GRAY)
        gray_road = cv.equalizeHist(gray_road)
        gray_road = cv.GaussianBlur(gray_road, (3, 3), 0)
        road_kp, road_des = sift.detectAndCompute(gray_road, None)

        matcher = cv.FlannBasedMatcher(dict(algorithm=1, trees=8), dict(checks=200))

        # ✅ 형광색으로 변경
        box_colors = [(0, 255, 0), (0, 255, 255)]   # 형광 초록, 형광 노랑
        label_texts = ['SpeedLimit', 'SchoolZone']
        road_with_boxes = self.currentFrame.copy()
        results = []
        match_rows = []
        found_boxes = []  # ✅ 박스 좌표 저장 (크롭용)

        for i, (sign_img, sign_kp, sign_des) in enumerate(self.signData):
            if sign_des is None or road_des is None:
                continue

            knn_match = matcher.knnMatch(sign_des, road_des, 2)
            good_match = [m for m, n in knn_match if m.distance < 0.75 * n.distance]

            if len(good_match) < 6:
                continue

            pts1 = np.float32([sign_kp[m.queryIdx].pt for m in good_match]).reshape(-1, 1, 2)
            pts2 = np.float32([road_kp[m.trainIdx].pt for m in good_match]).reshape(-1, 1, 2)
            H, mask = cv.findHomography(pts1, pts2, cv.RANSAC, 3.0, maxIters=3000, confidence=0.995)

            if H is None or mask.sum() < 5:
                continue

            det = np.linalg.det(H[:2, :2])
            if not (0.005 < abs(det) < 200):
                continue

            h, w = sign_img.shape[:2]
            box = cv.perspectiveTransform(
                np.float32([[0,0],[0,h-1],[w-1,h-1],[w-1,0]]).reshape(-1,1,2), H
            )

            box_area = cv.contourArea(np.int32(box))
            frame_area = self.currentFrame.shape[0] * self.currentFrame.shape[1]
            if not (0.0005 * frame_area < box_area < 0.6 * frame_area):
                continue

            # ✅ 박스를 bounding rect 기준 정사각 네모로 깔끔하게 표시
            pts = np.int32(box).reshape(-1, 2)
            x, y, bw, bh = cv.boundingRect(pts)
            cv.rectangle(road_with_boxes, (x, y), (x + bw, y + bh), box_colors[i], 3)
            cv.putText(road_with_boxes, label_texts[i], (x, y - 10),
                       cv.FONT_HERSHEY_SIMPLEX, 1.0, box_colors[i], 2)

            results.append(self.signFiles[i][1])
            found_boxes.append((i, sign_img, sign_kp, good_match, x, y, bw, bh))

        # ✅ 매칭선 + 크롭 확대 구성
        for (i, sign_img, sign_kp, good_match, x, y, bw, bh) in found_boxes:
            sign_h = 300
            scale = sign_h / sign_img.shape[0]
            sign_large = cv.resize(sign_img, (int(sign_img.shape[1] * scale), sign_h))
            sign_kp_large = [cv.KeyPoint(kp.pt[0]*scale, kp.pt[1]*scale,
                                         kp.size*scale, kp.angle,
                                         kp.response, kp.octave, kp.class_id)
                             for kp in sign_kp]

            pad = 20
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(self.currentFrame.shape[1], x + bw + pad)
            y2 = min(self.currentFrame.shape[0], y + bh + pad)
            crop = road_with_boxes[y1:y2, x1:x2]

            if crop.shape[0] > 0 and crop.shape[1] > 0:
                crop_scale = sign_h / crop.shape[0]
                road_crop_large = cv.resize(crop, (int(crop.shape[1] * crop_scale), sign_h))
            else:
                road_crop_large = np.zeros((sign_h, sign_h, 3), dtype=np.uint8)
                crop_scale = 1.0

            road_kp_crop = []
            road_kp_crop_idx = []
            for idx, kp in enumerate(road_kp):
                nx = (kp.pt[0] - x1) * crop_scale
                ny = (kp.pt[1] - y1) * crop_scale
                if 0 <= nx < road_crop_large.shape[1] and 0 <= ny < road_crop_large.shape[0]:
                    road_kp_crop.append(cv.KeyPoint(nx, ny, kp.size, kp.angle,
                                                    kp.response, kp.octave, kp.class_id))
                    road_kp_crop_idx.append(idx)

            idx_map = {orig: new for new, orig in enumerate(road_kp_crop_idx)}
            good_match_crop = []
            for m in good_match:
                if m.trainIdx in idx_map:
                    good_match_crop.append(cv.DMatch(m.queryIdx, idx_map[m.trainIdx], m.distance))

            if good_match_crop:
                row = cv.drawMatches(
                    sign_large, sign_kp_large,
                    road_crop_large, road_kp_crop,
                    good_match_crop, None,
                    matchColor=None,
                    singlePointColor=None,
                    flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
                )
            else:
                row = np.hstack([sign_large, road_crop_large])

            match_rows.append(row)

        if match_rows:
            max_w = max(r.shape[1] for r in match_rows)
            padded = []
            for r in match_rows:
                if r.shape[1] < max_w:
                    pad_img = np.zeros((r.shape[0], max_w - r.shape[1], 3), dtype=np.uint8)
                    r = np.hstack([r, pad_img])
                padded.append(r)

            match_combined = np.vstack(padded)

            road_scale = max_w / road_with_boxes.shape[1]
            road_resized = cv.resize(road_with_boxes,
                                     (max_w, int(road_with_boxes.shape[0] * road_scale)))

            # ✅ 구분선 추가
            divider = np.full((4, max_w, 3), 80, dtype=np.uint8)
            final = np.vstack([match_combined, divider, road_resized])

            self.showOnLabel(final, self.rightLabel)

            # ✅ 결과는 한 번만, 두 표지판 모두 표시
            result_text = ' / '.join(results)
            if result_text != self.lastResult:
                self.lastResult = result_text
                self.infoLabel.setText('인식됨: ' + result_text)
        else:
            self.showOnLabel(road_with_boxes, self.rightLabel)
            if self.lastResult is not None:
                self.lastResult = None
                self.infoLabel.setText('인식된 표지판 없음')

    def quitFunction(self):
        self.close()

app = QApplication(sys.argv)
win = TrafficWeak()
win.show()
app.exec_()
