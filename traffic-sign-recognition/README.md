# 교통약자 보호 - 실시간 표지판 인식 시스템

실시간 도로 영상에서 **속도제한 표지판**과 **어린이보호구역 표지판**을 자동으로 탐지하고 매칭하는 컴퓨터 비전 프로그램입니다.

<br>

## 프로젝트 개요

미리 등록된 교통 표지판 이미지와 도로 주행 영상을 입력받아, SIFT 특징점 추출 및 FLANN 기반 매칭으로 표지판을 실시간으로 인식합니다.
속도단속 구간과 어린이보호구역을 자동 감지하여 교통약자 보호에 기여하는 것을 목표로 합니다.

<br>

## 실행 화면

### 1. 원거리 표지판 인식 — SpeedLimit + SchoolZone 동시 감지

멀리서 촬영된 도로 영상에서 두 표지판을 동시에 탐지하고 매칭선과 함께 결과를 표시합니다.

<img width="834" height="913" alt="스크린샷 2026-04-29 124713" src="https://github.com/user-attachments/assets/5a3dba5d-3288-4803-ac21-b6668f47e2e2" />


<br>

### 2. 근거리 복합 인식 — 확대 프레임에서의 정밀 매칭

표지판이 가까이 찍힌 프레임에서 SpeedLimit과 SchoolZone을 각각 탐지하여 초록/노랑 박스로 구분합니다.

<img width="910" height="929" alt="스크린샷 2026-04-29 124723" src="https://github.com/user-attachments/assets/25c006eb-4ca5-410e-aca8-b46584a757de" />


<br>

### 3. 단일 표지판 클로즈업 — SIFT 키포인트 매칭 시각화

등록된 표지판 이미지와 도로 영상 프레임 간의 특징점 매칭 라인을 직접 확인할 수 있습니다.

<img width="780" height="931" alt="스크린샷 2026-04-29 124757" src="https://github.com/user-attachments/assets/70d9b8bd-1458-4512-8819-a701cb5a3e24" />



<br>

## 기술 스택

| 항목 | 내용 |
|:------|:------|
| Language | Python 3 |
| GUI | PyQt5 |
| Computer Vision | OpenCV (cv2) |
| 특징점 추출 | SIFT (Scale-Invariant Feature Transform) |
| 매칭 알고리즘 | FLANN-based Matcher + KNN (k=2) |
| 호모그래피 추정 | RANSAC 기반 cv2.findHomography |

<br>

## 동작 원리

### 1단계 — 표지판 등록

`표지판 등록` 버튼을 누르면 아래 두 이미지를 고정 경로에서 불러와 SIFT 분석을 수행합니다.

각 이미지에 대해 아래 전처리 후 키포인트와 디스크립터를 추출합니다.

```python
gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
gray = cv.equalizeHist(gray)             # 히스토그램 평활화
gray = cv.GaussianBlur(gray, (3, 3), 0)  # 가우시안 블러
kp, des = sift.detectAndCompute(gray, None)
```

SIFT 파라미터는 다음과 같습니다.

```python
cv.SIFT_create(
    nfeatures=5000,
    nOctaveLayers=5,
    contrastThreshold=0.02,
    edgeThreshold=20,
    sigma=1.4
)
```

<br>

### 2단계 — 도로 영상 불러오기

파일 다이얼로그로 `.mov` 또는 `.mp4` 영상을 선택하면 첫 프레임을 미리보기로 표시합니다.

<br>

### 3단계 — 실시간 인식

`인식` 버튼을 누르면 QTimer가 **30ms 간격**으로 프레임 처리를 호출합니다.
매 호출마다 영상의 FPS를 기준으로 **5초치 프레임을 grab()으로 스킵**한 뒤 다음 프레임을 분석합니다.

```python
fps = self.roadCap.get(cv.CAP_PROP_FPS)  # fps가 0 이하이면 30으로 대체
skip = int(fps * 5)
for _ in range(skip - 1):
    self.roadCap.grab()
ret, frame = self.roadCap.read()
```

각 프레임에 동일한 전처리(equalizeHist + GaussianBlur) 후 SIFT 특징점을 추출하고 FLANN으로 매칭합니다.

```python
cv.FlannBasedMatcher(
    dict(algorithm=1, trees=8),
    dict(checks=200)
)
```

매칭 필터링 및 검증은 아래 순서로 진행됩니다.

<br>

### 4단계 — 결과 시각화

검출된 표지판마다 boundingRect 기준 사각형 박스와 레이블을 그립니다.

- 초록 박스 `(0, 255, 0)` — SpeedLimit (단속구간)
- 노랑 박스 `(0, 255, 255)` — SchoolZone (어린이보호구역)

화면은 아래 구조로 구성됩니다.

- 상단: 표지판 원본 이미지와 도로 크롭 간의 매칭선 시각화 (sign_h=300px 기준 리사이즈, pad=20px)
- 중간: 구분선 (4px, gray=80)
- 하단: 전체 도로 프레임 + 바운딩 박스

인식 결과는 직전 결과(lastResult)와 달라졌을 때만 상단 infoLabel에 업데이트됩니다.
두 표지판이 동시에 검출되면 `단속구간 / 어린이보호구역` 형태로 표시됩니다.

<br>

## 실행 방법

### 1. 의존성 설치

```bash
pip install opencv-python opencv-contrib-python PyQt5 numpy
```

> SIFT는 `opencv-contrib-python`에 포함되어 있습니다. `opencv-python`만 설치하면 오류가 발생합니다.

<br>

### 2. 표지판 이미지 준비

실행 파일과 같은 위치에 `ch6/` 폴더를 생성하고 아래 이미지를 넣어주세요.

> 표지판 이미지 경로는 코드 내 `self.signFiles`에 하드코딩되어 있습니다. 변경 시 해당 리스트를 수정하세요.

<br>

### 3. 실행

```bash
python traffic_weak.py
```

<br>

## 사용 순서

| 순서 | 버튼 | 동작 |
|:---:|:------|:------|
| 1 | 표지판 등록 | ch6/ 폴더의 표지판 이미지를 SIFT로 분석하여 메모리에 등록 |
| 2 | 도로 영상 불러오기 | .mov / .mp4 파일 선택, 첫 프레임 미리보기 표시 |
| 3 | 인식 | QTimer 시작 (30ms), 5초 단위 프레임 분석 및 표지판 탐지 |
| 4 | 나가기 | 프로그램 종료 |

> 인식 버튼은 영상을 불러온 상태에서만 동작합니다. 영상이 끝나면 타이머가 자동 정지되고 "영상 재생 완료"가 표시됩니다.

<br>

## 프로젝트 구조
<br>

## 주요 파라미터

| 파라미터 | 값 | 설명 |
|:------|:---:|:------|
| nfeatures | 5000 | SIFT 최대 검출 키포인트 수 |
| nOctaveLayers | 5 | 옥타브당 레이어 수 |
| contrastThreshold | 0.02 | 낮은 대비 키포인트 필터 임계값 |
| edgeThreshold | 20 | 엣지 필터 임계값 |
| sigma | 1.4 | 가우시안 시그마 |
| trees | 8 | FLANN KD-tree 수 |
| checks | 200 | FLANN 탐색 횟수 |
| ratio threshold | 0.75 | Lowe's ratio test 임계값 |
| min_good_matches | 6 | 최소 유효 매칭 수 |
| RANSAC threshold | 3.0 px | 호모그래피 추정 오차 허용값 |
| min_inliers | 5 | 최소 inlier 수 |
| maxIters | 3000 | RANSAC 최대 반복 횟수 |
| confidence | 0.995 | RANSAC 신뢰도 |
| det 범위 | 0.005 ~ 200 | 호모그래피 행렬식 유효 범위 |
| 면적 비율 | 0.05% ~ 60% | 탐지 박스의 프레임 대비 면적 범위 |
| timer interval | 30 ms | QTimer 호출 간격 |
| frame skip | fps x 5 | 매 호출마다 스킵할 프레임 수 |
| sign_h | 300 px | 매칭 시각화 표지판 높이 기준 |
| crop pad | 20 px | 크롭 영역 여백 |

