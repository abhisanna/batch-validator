import time
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from ultralytics import YOLO
from arduino_controller import ArduinoController, ArduinoConfig, find_arduino_port

try:
    import torch
except Exception:  # pragma: no cover - torch is expected through ultralytics
    torch = None


MODEL_PATH = "./model.pt"
CAMERA_INDICES = (0, 1)
CONF_THRESHOLD = 0.8
IMG_SIZE = 640
WINDOW_NAME = "Batch Validator"
FRAME_PLACEHOLDER = (30, 30, 30)
FUSION_CENTER_THRESHOLD = 0.18
FUSION_AREA_RATIO_THRESHOLD = 1.8
LOCAL_IOU_THRESHOLD = 0.25
TRACK_TTL_SECONDS = 1.5
MIN_CONFIRMATIONS_TO_COUNT = 2
MATCH_Y_THRESHOLD = 0.14
MATCH_X_THRESHOLD = 0.12
MATCH_AREA_RATIO_THRESHOLD = 1.5
MATCH_ASPECT_RATIO_THRESHOLD = 1.4


def select_device() -> str:
    if torch is None:
        return "cpu"

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"

    if torch.cuda.is_available():
        return "cuda"

    return "cpu"


DEVICE = select_device()
MODEL = YOLO(MODEL_PATH)
if DEVICE != "cpu":
    MODEL.to(DEVICE)


def box_iou(box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    if inter_area == 0:
        return 0.0

    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    return inter_area / float(area_a + area_b - inter_area)


def center_and_area(box: Tuple[int, int, int, int]) -> Tuple[Tuple[float, float], float, float]:
    x1, y1, x2, y2 = box
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    center = (x1 + width / 2.0, y1 + height / 2.0)
    aspect_ratio = width / float(height)
    return center, float(width * height), float(aspect_ratio)


def normalize_box(box: Tuple[int, int, int, int], frame_size: Tuple[int, int]) -> Tuple[Tuple[float, float], float, float]:
    frame_width, frame_height = frame_size
    center, area, aspect_ratio = center_and_area(box)
    normalized_center = (center[0] / max(1, frame_width), center[1] / max(1, frame_height))
    normalized_area = area / float(max(1, frame_width * frame_height))
    return normalized_center, normalized_area, aspect_ratio


def fit_frame(frame: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
    target_width, target_height = target_size
    if frame is None:
        return np.full((target_height, target_width, 3), FRAME_PLACEHOLDER, dtype=np.uint8)

    source_height, source_width = frame.shape[:2]
    scale = min(target_width / float(max(1, source_width)), target_height / float(max(1, source_height)))
    resized_width = max(1, int(source_width * scale))
    resized_height = max(1, int(source_height * scale))
    resized = cv2.resize(frame, (resized_width, resized_height))

    canvas = np.full((target_height, target_width, 3), FRAME_PLACEHOLDER, dtype=np.uint8)
    x_offset = (target_width - resized_width) // 2
    y_offset = (target_height - resized_height) // 2
    canvas[y_offset:y_offset + resized_height, x_offset:x_offset + resized_width] = resized
    return canvas


class CameraStream:
    def __init__(self, index: int):
        self.index = index
        self.capture = cv2.VideoCapture(index)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.running = self.capture.isOpened()
        self.lock = threading.Lock()
        self.frame = None
        self.success = False
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self) -> None:
        while self.running:
            success, frame = self.capture.read()
            with self.lock:
                self.success = success
                if success:
                    self.frame = frame
            if not success:
                time.sleep(0.01)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self.lock:
            if not self.success or self.frame is None:
                return False, None
            return True, self.frame.copy()

    def release(self) -> None:
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.capture.release()


@dataclass
class LocalTrack:
    track_id: int
    bbox: Tuple[int, int, int, int]
    conf: float
    last_seen: float
    hits: int = 1


class SimpleTracker:
    def __init__(self, camera_name: str):
        self.camera_name = camera_name
        self.next_track_id = 1
        self.tracks: Dict[int, LocalTrack] = {}

    def update(self, detections: List[Tuple[Tuple[int, int, int, int], float]], now: float) -> List[LocalTrack]:
        matched_tracks = set()
        matched_detections = set()
        track_ids = list(self.tracks.keys())

        candidates = []
        for track_id in track_ids:
            track = self.tracks[track_id]
            for detection_index, (bbox, confidence) in enumerate(detections):
                iou_score = box_iou(track.bbox, bbox)
                if iou_score < LOCAL_IOU_THRESHOLD:
                    continue
                candidates.append((iou_score, track_id, detection_index, bbox, confidence))

        candidates.sort(reverse=True, key=lambda item: item[0])

        for _, track_id, detection_index, bbox, confidence in candidates:
            if track_id in matched_tracks or detection_index in matched_detections:
                continue
            self.tracks[track_id].bbox = bbox
            self.tracks[track_id].conf = confidence
            self.tracks[track_id].last_seen = now
            self.tracks[track_id].hits += 1
            matched_tracks.add(track_id)
            matched_detections.add(detection_index)

        for detection_index, (bbox, confidence) in enumerate(detections):
            if detection_index in matched_detections:
                continue
            track_id = self.next_track_id
            self.next_track_id += 1
            self.tracks[track_id] = LocalTrack(
                track_id=track_id,
                bbox=bbox,
                conf=confidence,
                last_seen=now,
            )

        stale_ids = [track_id for track_id, track in self.tracks.items() if now - track.last_seen > TRACK_TTL_SECONDS]
        for track_id in stale_ids:
            del self.tracks[track_id]

        return list(self.tracks.values())


@dataclass
class GlobalObject:
    global_id: int
    camera_name: str
    local_track_id: int
    bbox: Tuple[int, int, int, int]
    conf: float
    frame_size: Tuple[int, int]
    last_seen: float
    observations_seen: int = 0
    seen_cameras: set[str] = None
    counted: bool = False

    def __post_init__(self) -> None:
        if self.seen_cameras is None:
            self.seen_cameras = {self.camera_name}


class GlobalFusionCounter:
    def __init__(self):
        self.next_global_id = 1
        self.global_objects: Dict[int, GlobalObject] = {}
        self.local_to_global: Dict[Tuple[str, int], int] = {}
        self.total_count = 0

    def _match_existing(self, camera_name: str, local_track_id: int, bbox: Tuple[int, int, int, int], frame_size: Tuple[int, int], now: float) -> Optional[int]:
        direct_key = (camera_name, local_track_id)
        if direct_key in self.local_to_global:
            global_id = self.local_to_global[direct_key]
            if global_id in self.global_objects:
                return global_id

        normalized_center, normalized_area, normalized_aspect = normalize_box(bbox, frame_size)
        best_global_id = None
        best_score = float("inf")

        for global_id, global_object in self.global_objects.items():
            if now - global_object.last_seen > TRACK_TTL_SECONDS * 2:
                continue

            if global_object.camera_name == camera_name and global_object.local_track_id == local_track_id:
                return global_id

            existing_center, existing_area, existing_aspect = normalize_box(global_object.bbox, global_object.frame_size)
            center_x_distance = abs(normalized_center[0] - existing_center[0])
            center_y_distance = abs(normalized_center[1] - existing_center[1])
            area_ratio = max(normalized_area, existing_area) / max(1e-6, min(normalized_area, existing_area))
            aspect_ratio = max(normalized_aspect, existing_aspect) / max(1e-6, min(normalized_aspect, existing_aspect))

            if center_x_distance > MATCH_X_THRESHOLD:
                continue
            if center_y_distance > MATCH_Y_THRESHOLD:
                continue
            if area_ratio > MATCH_AREA_RATIO_THRESHOLD:
                continue
            if aspect_ratio > MATCH_ASPECT_RATIO_THRESHOLD:
                continue

            score = (center_x_distance * 0.25) + (center_y_distance * 0.75) + (area_ratio - 1.0) + ((aspect_ratio - 1.0) * 0.5)
            if score < best_score:
                best_score = score
                best_global_id = global_id

        return best_global_id

    def update(self, observations: List[Dict[str, object]], now: float) -> Dict[int, int]:
        assigned: Dict[int, int] = {}
        used_global_ids = set()

        ordered_observations = sorted(
            observations,
            key=lambda item: float(item["conf"]),
            reverse=True,
        )

        for observation in ordered_observations:
            camera_name = str(observation["camera_name"])
            local_track_id = int(observation["local_track_id"])
            bbox = observation["bbox"]
            frame_size = observation["frame_size"]
            confidence = float(observation["conf"])

            matched_global_id = self._match_existing(camera_name, local_track_id, bbox, frame_size, now)
            if matched_global_id in used_global_ids:
                matched_global_id = None

            if matched_global_id is None:
                matched_global_id = self.next_global_id
                self.next_global_id += 1
                self.global_objects[matched_global_id] = GlobalObject(
                    global_id=matched_global_id,
                    camera_name=camera_name,
                    local_track_id=local_track_id,
                    bbox=bbox,
                    conf=confidence,
                    frame_size=frame_size,
                    last_seen=now,
                )
            else:
                global_object = self.global_objects[matched_global_id]
                global_object.camera_name = camera_name
                global_object.local_track_id = local_track_id
                global_object.bbox = bbox
                global_object.conf = confidence
                global_object.frame_size = frame_size
                global_object.last_seen = now
            global_object = self.global_objects[matched_global_id]
            global_object.observations_seen += 1
            global_object.seen_cameras.add(camera_name)
            used_global_ids.add(matched_global_id)

            if not global_object.counted and len(global_object.seen_cameras) >= MIN_CONFIRMATIONS_TO_COUNT and global_object.observations_seen >= MIN_CONFIRMATIONS_TO_COUNT:
                global_object.counted = True
                self.total_count += 1

            self.local_to_global[(camera_name, local_track_id)] = matched_global_id
            assigned[local_track_id] = matched_global_id

        stale_global_ids = [
            global_id
            for global_id, global_object in self.global_objects.items()
            if now - global_object.last_seen > TRACK_TTL_SECONDS * 4
        ]
        for global_id in stale_global_ids:
            del self.global_objects[global_id]

        stale_local_keys = [
            key
            for key, global_id in self.local_to_global.items()
            if global_id not in self.global_objects
        ]
        for key in stale_local_keys:
            del self.local_to_global[key]

        return assigned


def infer_detections(frame: np.ndarray) -> List[Tuple[Tuple[int, int, int, int], float]]:
    results = MODEL.predict(
        source=frame,
        conf=CONF_THRESHOLD,
        imgsz=IMG_SIZE,
        device=DEVICE,
        half=False,
        verbose=False,
    )

    detections: List[Tuple[Tuple[int, int, int, int], float]] = []
    if not results:
        return detections

    result = results[0]
    if result.boxes is None:
        return detections

    for detection in result.boxes:
        x1, y1, x2, y2 = map(int, detection.xyxy[0])
        confidence = float(detection.conf[0])
        detections.append(((x1, y1, x2, y2), confidence))

    return detections


def draw_detections(frame: np.ndarray, tracks: List[LocalTrack], camera_label: str) -> np.ndarray:
    annotated = frame.copy()
    for track in tracks:
        x1, y1, x2, y2 = track.bbox
        color = (0, 255, 0) if track.conf >= CONF_THRESHOLD else (0, 255, 255)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            annotated,
            f"{camera_label} ID {track.track_id} {track.conf:.0%}",
            (x1, max(20, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
        )
    return annotated


def print_status(total_count: int, expected_qty: Optional[int], arduino: Optional[ArduinoController] = None) -> None:
    if expected_qty is None:
        print(f"[count] total={total_count} expected=unset status=awaiting input")
        return

    status = "MATCH" if total_count == expected_qty else "NOT MATCH"
    print(f"[count] total={total_count} expected={expected_qty} status={status}")
    
    # Send command to Arduino
    if arduino and arduino.connected:
        if total_count == expected_qty:
            print("→ Arduino: Opening gate (GREEN LED)")
            arduino.open_gate()
        else:
            print("→ Arduino: Closing gate (RED LED)")
            arduino.close_gate()


def main() -> None:
    # Initialize Arduino
    print("Initializing Arduino connection...")
    arduino_port = find_arduino_port()
    arduino = None
    arduino_status = "NOT CONNECTED"
    
    if arduino_port:
        print(f"  Found Arduino port: {arduino_port}")
        config = ArduinoConfig(port=arduino_port)
        arduino = ArduinoController(config, debug=True)
        if arduino.connected:
            arduino_status = "CONNECTED"
    else:
        print("  ⚠ Arduino port not auto-detected. Trying common ports...")
        for port in ["/dev/cu.usbserial-A5069RR4", "/dev/tty.usbserial-A5069RR4",
                     "/dev/cu.usbserial", "/dev/tty.usbserial",
                     "/dev/cu.usbmodem14201", "/dev/tty.usbmodem14201", 
                     "/dev/ttyUSB0"]:
            try:
                config = ArduinoConfig(port=port)
                arduino = ArduinoController(config, debug=False)
                if arduino.connected:
                    arduino_status = "CONNECTED"
                    print(f"  ✓ Connected on {port}")
                    break
            except:
                pass
    
    if not arduino or not arduino.connected:
        print("  ⚠ Arduino not available - running in camera-only mode")
        arduino = None
    
    cameras = [CameraStream(index) for index in CAMERA_INDICES]
    if not all(camera.running for camera in cameras):
        print("Unable to open both cameras. Check the USB webcam indices.")
        for camera in cameras:
            camera.release()
        if arduino:
            arduino.disconnect()
        return

    trackers = [SimpleTracker(f"cam{index}") for index in range(len(cameras))]
    fusion_counter = GlobalFusionCounter()

    expected_input = ""
    expected_qty: Optional[int] = None
    last_status: Optional[Tuple[int, Optional[int]]] = None
    last_frame_time = time.time()

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    try:
        while True:
            now = time.time()
            fps = 1.0 / max(1e-6, now - last_frame_time)
            last_frame_time = now

            display_frames = []
            combined_observations = []

            for camera_index, camera in enumerate(cameras):
                success, frame = camera.read()
                if not success or frame is None:
                    placeholder = np.full((720, 1280, 3), FRAME_PLACEHOLDER, dtype=np.uint8)
                    cv2.putText(
                        placeholder,
                        f"Camera {camera_index + 1} offline",
                        (40, 80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 0, 255),
                        2,
                    )
                    display_frames.append(placeholder)
                    continue

                detections = infer_detections(frame)
                local_tracks = trackers[camera_index].update(detections, now)
                combined_observations.extend(
                    {
                        "camera_name": trackers[camera_index].camera_name,
                        "local_track_id": track.track_id,
                        "bbox": track.bbox,
                        "conf": track.conf,
                        "frame_size": (frame.shape[1], frame.shape[0]),
                    }
                    for track in local_tracks
                )

                annotated = draw_detections(frame, local_tracks, f"Cam {camera_index + 1}")
                camera_overlay = annotated.copy()
                cv2.rectangle(camera_overlay, (0, 0), (430, 90), (0, 0, 0), -1)
                cv2.putText(camera_overlay, f"Cam {camera_index + 1}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                cv2.putText(camera_overlay, f"Local tracks: {len(local_tracks)}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                display_frames.append(camera_overlay)

            fusion_counter.update(combined_observations, now)
            total_count = fusion_counter.total_count

            if last_status != (total_count, expected_qty):
                print_status(total_count, expected_qty, arduino)
                last_status = (total_count, expected_qty)

            half_width = 960
            display_height = 1080
            left_panel = fit_frame(display_frames[0], (half_width, display_height))
            right_panel = fit_frame(display_frames[1], (half_width, display_height))
            canvas = np.hstack([left_panel, right_panel])

            status_text = "Awaiting expected qty" if expected_qty is None else ("MATCH" if total_count == expected_qty else "NOT MATCH")
            status_color = (0, 220, 0) if status_text == "MATCH" else ((0, 0, 255) if status_text == "NOT MATCH" else (255, 255, 255))

            cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 120), (0, 0, 0), -1)
            cv2.putText(canvas, f"FPS: {fps:.1f}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            cv2.putText(canvas, f"Total unique boxes: {total_count}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            cv2.putText(canvas, f"Expected: {expected_qty if expected_qty is not None else 'unset'}", (520, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            cv2.putText(canvas, f"Status: {status_text}", (520, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, status_color, 2)
            cv2.putText(canvas, f"Arduino: {arduino_status}", (980, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if arduino_status == "CONNECTED" else (255, 0, 0), 2)
            cv2.putText(canvas, f"Typing buffer: {expected_input or '_'}  [digits + Enter, Backspace, r=reset, q=quit]", (980, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

            cv2.imshow(WINDOW_NAME, canvas)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if ord("0") <= key <= ord("9"):
                expected_input += chr(key)
            elif key in (8, 127):
                expected_input = expected_input[:-1]
            elif key in (13, 10):
                if expected_input:
                    expected_qty = int(expected_input)
                    expected_input = ""
                    print_status(total_count, expected_qty, arduino)
                    last_status = (total_count, expected_qty)
            elif key == ord("r"):
                fusion_counter = GlobalFusionCounter()
                for tracker in trackers:
                    tracker.tracks.clear()
                    tracker.next_track_id = 1
                total_count = 0
                expected_input = ""
                if arduino:
                    arduino.close_gate()  # Reset to closed gate
                print_status(total_count, expected_qty, arduino)
                last_status = (total_count, expected_qty)

    finally:
        for camera in cameras:
            camera.release()
        if arduino:
            arduino.disconnect()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()