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
