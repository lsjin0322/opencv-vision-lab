import cv2
import mediapipe as mp
import numpy as np
import math
import time

# ==========================================
# 1. 초기화 및 설정
# ==========================================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils

COLORS = {
    "WHITE": (255, 255, 255),
    "RED": (0, 0, 255),
    "GREEN": (0, 255, 0),
    "BLUE": (255, 0, 0)
}
COLOR_LIST = [COLORS["WHITE"], COLORS["RED"], COLORS["GREEN"], COLORS["BLUE"]]
STYLE_LIST = ["SOLID", "NEON", "DOTTED"]

class HandState:
    def __init__(self):
        self.mode = "MOVE"
        self.current_stroke = []
        self.prev_x = 0
        self.prev_y = 0
        
        # 선 끊김 방지를 위한 히스테리시스 상태 변수
        self.is_pinching = False
        
        # 제스처 타이머
        self.middle_touching = False
        self.last_middle_tap = 0.0
        self.ring_touching = False
        self.last_style_change = 0.0

class SpaceState:
    def __init__(self):
        self.strokes = [] 
        self.rx = 0.0     
        self.ry = 0.0     
        
        self.current_color = COLORS["WHITE"]
        self.current_style = "SOLID" 
        self.current_thickness = 5
        
        self.hands = {"Left": HandState(), "Right": HandState()}

space = SpaceState()

PALETTE = [{"x1": 10 + i*70, "y1": 10, "x2": 70 + i*70, "y2": 80, "color": COLOR_LIST[i]} for i in range(4)]
STYLE_BTN = [
    {"x1": 310, "y1": 10, "x2": 410, "y2": 80, "style": "SOLID"},
    {"x1": 420, "y1": 10, "x2": 520, "y2": 80, "style": "NEON"},
    {"x1": 530, "y1": 10, "x2": 630, "y2": 80, "style": "DOTTED"}
]
TRASH_BTN = {"x1": 1100, "y1": 10, "x2": 1260, "y2": 80}
SLIDER = {"x1": 1180, "y1": 200, "x2": 1260, "y2": 500}

# ==========================================
# 2. 3D 수학 연산
# ==========================================
def project_3d_to_2d(x, y, z, rx, ry, cx, cy):
    x_rot_y = x * math.cos(ry) - z * math.sin(ry)
    z_rot_y = x * math.sin(ry) + z * math.cos(ry)
    
    y_rot_x = y * math.cos(rx) - z_rot_y * math.sin(rx)
    z_rot_x = y * math.sin(rx) + z_rot_y * math.cos(rx)
    
    fov, distance = 600.0, 600.0
    z_shifted = max(1, z_rot_x + distance)
    
    scale = fov / z_shifted
    proj_x = int(cx + (x_rot_y * scale))
    proj_y = int(cy + (y_rot_x * scale))
    return proj_x, proj_y, scale

def get_world_coords_from_screen(cam_x, cam_y, rx, ry):
    x1, y1 = cam_x, cam_y * math.cos(-rx)
    z1 = cam_y * math.sin(-rx)
    world_x = x1 * math.cos(-ry) - z1 * math.sin(-ry)
    world_z = x1 * math.sin(-ry) + z1 * math.cos(-ry)
    return world_x, y1, world_z

def get_distance(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

def get_fingers_up(hand_landmarks):
    tips, pips = [4, 8, 12, 16, 20], [2, 6, 10, 14, 18]
    fingers = [1 if hand_landmarks.landmark[tips[0]].x < hand_landmarks.landmark[pips[0]].x else 0]
    for id in range(1, 5):
        fingers.append(1 if hand_landmarks.landmark[tips[id]].y < hand_landmarks.landmark[pips[id]].y else 0)
    return fingers

# ==========================================
# 3. 메인 루프
# ==========================================
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

TOUCH_THRESHOLD = 30
ERASE_RADIUS = 30 

while True:
    success, frame = cap.read()
    if not success: break

    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape
    cx, cy = w // 2, h // 2

    render_canvas = np.zeros((h, w, 3), dtype=np.uint8)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    if results.multi_hand_landmarks and results.multi_handedness:
        for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            label = results.multi_handedness[idx].classification[0].label
            h_state = space.hands[label]

            thumb_2d = (int(hand_landmarks.landmark[4].x * w), int(hand_landmarks.landmark[4].y * h))
            index_2d = (int(hand_landmarks.landmark[8].x * w), int(hand_landmarks.landmark[8].y * h))
            middle_2d = (int(hand_landmarks.landmark[12].x * w), int(hand_landmarks.landmark[12].y * h))
            ring_2d = (int(hand_landmarks.landmark[16].x * w), int(hand_landmarks.landmark[16].y * h))
            pinky_2d = (int(hand_landmarks.landmark[20].x * w), int(hand_landmarks.landmark[20].y * h))
            
            fingers = get_fingers_up(hand_landmarks)
            dist_thumb_index = get_distance(thumb_2d, index_2d)
            dist_thumb_middle = get_distance(thumb_2d, middle_2d)
            dist_thumb_ring = get_distance(thumb_2d, ring_2d)

            now_time = time.time()

            # 색상/스타일 변경 (더블/싱글 탭)
            if dist_thumb_middle < TOUCH_THRESHOLD:
                if not h_state.middle_touching:
                    h_state.middle_touching = True
                    if now_time - h_state.last_middle_tap < 0.6: 
                        curr_idx = COLOR_LIST.index(space.current_color)
                        space.current_color = COLOR_LIST[(curr_idx + 1) % len(COLOR_LIST)]
                        h_state.last_middle_tap = 0.0 
                    else:
                        h_state.last_middle_tap = now_time
            else:
                h_state.middle_touching = False

            if dist_thumb_ring < TOUCH_THRESHOLD:
                if not h_state.ring_touching:
                    h_state.ring_touching = True
                    if now_time - h_state.last_style_change > 0.5: 
                        curr_idx = STYLE_LIST.index(space.current_style)
                        space.current_style = STYLE_LIST[(curr_idx + 1) % len(STYLE_LIST)]
                        h_state.last_style_change = now_time
            else:
                h_state.ring_touching = False

            # [핵심] 선 끊김 방지 히스테리시스 회로
            if dist_thumb_index < 35:
                h_state.is_pinching = True
            elif dist_thumb_index > 60:
                h_state.is_pinching = False

            is_fist = sum(fingers) == 0
            is_pinky_only = fingers == [0, 0, 0, 0, 1] 
            
            curr_x, curr_y = index_2d
            if is_fist: 
                curr_x = int(hand_landmarks.landmark[0].x * w)
                curr_y = int(hand_landmarks.landmark[0].y * h)

            in_trash = (TRASH_BTN["x1"] < curr_x < TRASH_BTN["x2"]) and (TRASH_BTN["y1"] < curr_y < TRASH_BTN["y2"])
            in_slider = (SLIDER["x1"] < curr_x < SLIDER["x2"]) and (SLIDER["y1"] < curr_y < SLIDER["y2"])

            # 제스처 상태 전이
            if is_fist and in_slider: h_state.mode = "SCROLL_UI"
            elif in_trash and h_state.is_pinching: h_state.mode = "DELETE_TRIGGERED"
            elif is_pinky_only: h_state.mode = "ERASE_PARTIAL"
            elif h_state.is_pinching: h_state.mode = "DRAW_3D"
            elif is_fist: h_state.mode = "ROTATE_CAMERA"
            else: h_state.mode = "MOVE"

            # 2D 좌표 스무딩 (보간율 상승으로 선을 더 매끄럽게 연결)
            if h_state.prev_x == 0 and h_state.prev_y == 0:
                h_state.prev_x, h_state.prev_y = curr_x, curr_y
            else:
                curr_x = int(h_state.prev_x * 0.4 + curr_x * 0.6)
                curr_y = int(h_state.prev_y * 0.4 + curr_y * 0.6)

            # 로직 실행
            if h_state.mode == "SCROLL_UI":
                ratio = (SLIDER["y2"] - curr_y) / (SLIDER["y2"] - SLIDER["y1"])
                space.current_thickness = max(1, min(20, int(ratio * 20)))
                cv2.circle(frame, (curr_x, curr_y), 20, (0, 255, 255), 3)

            elif h_state.mode == "DRAW_3D":
                cam_x, cam_y = curr_x - cx, curr_y - cy
                wx, wy, wz = get_world_coords_from_screen(cam_x, cam_y, space.rx, space.ry)
                h_state.current_stroke.append((wx, wy, wz))
                cv2.circle(frame, (curr_x, curr_y), 10, space.current_color, -1)
                
            elif h_state.mode == "ROTATE_CAMERA":
                space.ry += (curr_x - h_state.prev_x) * 0.01  
                space.rx += (curr_y - h_state.prev_y) * 0.01  
                cv2.circle(frame, (curr_x, curr_y), 15, (255, 0, 255), 2)

            elif h_state.mode == "ERASE_PARTIAL":
                cv2.circle(frame, pinky_2d, ERASE_RADIUS, (0, 0, 255), 2)
                new_strokes = []
                for stroke_data in space.strokes:
                    current_segment = []
                    for pt in stroke_data["points"]:
                        px, py, _ = project_3d_to_2d(pt[0], pt[1], pt[2], space.rx, space.ry, cx, cy)
                        if get_distance(pinky_2d, (px, py)) > ERASE_RADIUS:
                            current_segment.append(pt)
                        else:
                            if len(current_segment) > 1:
                                new_strokes.append({
                                    "points": current_segment, "color": stroke_data["color"],
                                    "style": stroke_data["style"], "thickness": stroke_data["thickness"]
                                })
                            current_segment = [] 
                    if len(current_segment) > 1:
                        new_strokes.append({
                            "points": current_segment, "color": stroke_data["color"],
                            "style": stroke_data["style"], "thickness": stroke_data["thickness"]
                        })
                space.strokes = new_strokes

            elif h_state.mode == "DELETE_TRIGGERED":
                space.strokes.clear()
                for l in ["Left", "Right"]: space.hands[l].current_stroke = []
                space.rx, space.ry = 0.0, 0.0 

            if h_state.mode != "DRAW_3D" and len(h_state.current_stroke) > 0:
                space.strokes.append({
                    "points": h_state.current_stroke, 
                    "color": space.current_color, 
                    "style": space.current_style,
                    "thickness": space.current_thickness
                })
                h_state.current_stroke = []

            h_state.prev_x, h_state.prev_y = curr_x, curr_y

    # ==========================================
    # 4. 3D 공간 렌더링
    # ==========================================
    all_strokes = space.strokes.copy()
    for l in ["Left", "Right"]:
        if len(space.hands[l].current_stroke) > 0:
            all_strokes.append({
                "points": space.hands[l].current_stroke, 
                "color": space.current_color, 
                "style": space.current_style,
                "thickness": space.current_thickness
            })

    for stroke_data in all_strokes:
        pts = stroke_data["points"]
        color = stroke_data["color"]
        style = stroke_data["style"]
        base_thick = stroke_data.get("thickness", 5)

        for i in range(1, len(pts)):
            p1, p2 = pts[i-1], pts[i]
            x1, y1, scale1 = project_3d_to_2d(p1[0], p1[1], p1[2], space.rx, space.ry, cx, cy)
            x2, y2, scale2 = project_3d_to_2d(p2[0], p2[1], p2[2], space.rx, space.ry, cx, cy)
            
            thickness = max(1, int(base_thick * scale1))
            
            if style == "SOLID":
                cv2.line(render_canvas, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)
            elif style == "NEON":
                cv2.line(render_canvas, (x1, y1), (x2, y2), color, thickness + 6, cv2.LINE_AA)
                cv2.line(render_canvas, (x1, y1), (x2, y2), (255, 255, 255), max(1, thickness - 2), cv2.LINE_AA)
            elif style == "DOTTED":
                if i % 3 == 0: cv2.circle(render_canvas, (x2, y2), thickness, color, -1)

    # ==========================================
    # 5. [핵심] 진짜 색상 알파 블렌딩 합성
    # ==========================================
    # 그려진 픽셀(0 초과) 위치를 찾아내어 원본 프레임의 해당 픽셀을 완전히 덮어씁니다.
    # 배경의 밝기와 무관하게 100% 진한 색상을 보장합니다.
    mask = cv2.cvtColor(render_canvas, cv2.COLOR_BGR2GRAY) > 0
    frame[mask] = render_canvas[mask]

    # UI 렌더링
    for p in PALETTE:
        cv2.rectangle(frame, (p["x1"], p["y1"]), (p["x2"], p["y2"]), p["color"], -1)
        if space.current_color == p["color"]: 
            cv2.rectangle(frame, (p["x1"], p["y1"]), (p["x2"], p["y2"]), (0, 255, 255), 4)

    for s in STYLE_BTN:
        if space.current_style == s["style"]:
            cv2.rectangle(frame, (s["x1"], s["y1"]), (s["x2"], s["y2"]), (220, 220, 220), -1)
            cv2.rectangle(frame, (s["x1"], s["y1"]), (s["x2"], s["y2"]), (0, 255, 0), 3)
            cv2.putText(frame, s["style"], (s["x1"] + 10, s["y1"] + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        else:
            cv2.rectangle(frame, (s["x1"], s["y1"]), (s["x2"], s["y2"]), (80, 80, 80), -1)
            cv2.putText(frame, s["style"], (s["x1"] + 10, s["y1"] + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    cv2.rectangle(frame, (1200, SLIDER["y1"]), (1240, SLIDER["y2"]), (50, 50, 50), -1)
    handle_y = SLIDER["y2"] - int((space.current_thickness / 20) * (SLIDER["y2"] - SLIDER["y1"]))
    cv2.circle(frame, (1220, handle_y), 15, (0, 255, 255), -1)
    cv2.putText(frame, f"Size: {space.current_thickness}", (1160, SLIDER["y1"] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.rectangle(frame, (TRASH_BTN["x1"], TRASH_BTN["y1"]), (TRASH_BTN["x2"], TRASH_BTN["y2"]), (0, 0, 150), -1)
    cv2.putText(frame, "TRASH", (TRASH_BTN["x1"] + 20, TRASH_BTN["y1"] + 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    cv2.putText(frame, "MOTION GUIDE", (20, h - 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(frame, "[PINCH] Draw 3D Line    |  [FIST] Rotate Space", (20, h - 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(frame, "[PINKY] Eraser          |  [FIST on Slider] Change Size", (20, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(frame, "[THUMB+MIDDLE x2] Color |  [THUMB+RING] Style", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    cv2.imshow("3D Air Architect Pro", frame)

    if cv2.waitKey(1) & 0xFF == 27: break

cap.release()
cv2.destroyAllWindows()