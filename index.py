import sys
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from arduino_controller import ArduinoController, ArduinoConfig, find_arduino_port

CONFIG = {
    "model_path": "./model.pt",
    "conf_threshold": 0.80, 
    "img_size": 640,
    "class_pallet": "pallet",
    "class_box": "box",
    "camera_indices": (0, 1),
    "camera_width": 1280,
    "camera_height": 720,
    "local_iou_threshold": 0.25,
    "track_ttl_seconds": 1.5,
    "min_confirmations_to_count": 2,
    "match_x_threshold": 0.12,
    "match_y_threshold": 0.14,
    "match_area_ratio_threshold": 1.5,
    "match_aspect_ratio_threshold": 1.4,
    "panel_width": 960,
    "panel_height": 1080,
    "window_name": "Batch Validator",
    "bg_color": (30, 30, 30),
}

def setup_logger(name: str = "batch_validator") -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger

log = setup_logger()

def select_device() -> str:
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        log.info("Device: Apple MPS (M1)")
        return "mps"
    
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)

        log.info(f"Device: CUDA — {name}")
        return "cuda"
    
    log.info("Device: CPU")
    return "cpu"


BBox = Tuple[int, int, int, int] # (x1, y1, x2, y2)

def box_iou(a: BBox, b: BBox) -> float:
    ix1 = max(a[0], b[0]);  iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2]);  iy2 = min(a[3], b[3])

    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)

    if inter == 0:
        return 0.0
    
    area_a = max(1, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(1, (b[2] - b[0]) * (b[3] - b[1]))

    return inter / float(area_a + area_b - inter)


def normalize_box(bbox: BBox, frame_w: int, frame_h: int):
    x1, y1, x2, y2 = bbox

    w = max(1, x2 - x1);  h = max(1, y2 - y1)

    cx = (x1 + w / 2.0) / max(1, frame_w)
    cy = (y1 + h / 2.0) / max(1, frame_h)

    area = (w * h) / max(1, frame_w * frame_h)

    return (cx, cy), area, w / float(h)


def boxes_overlap(box_bbox: BBox, pallet_bbox: BBox) -> bool:
    return box_iou(box_bbox, pallet_bbox) > 0.0


class CameraStream:
    def __init__(self, index: int, width: int, height: int):
        self.index = index
        self.cap = cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.running = self.cap.isOpened()
        self._lock = threading.Lock()
        self._frame = None
        self._ok = False
        self._thread = threading.Thread(target = self._reader, daemon = True)

        self._thread.start()

    def _reader(self) -> None:
        while self.running:
            ok, frame = self.cap.read()
            with self._lock:
                self._ok = ok
                self._frame = frame if ok else self._frame
            if not ok:
                time.sleep(0.01)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self._lock:
            if not self._ok or self._frame is None:
                return False, None
            
            return True, self._frame.copy()

    def release(self) -> None:
        self.running = False
        self._thread.join(timeout=1.0)

        self.cap.release()

@dataclass
class LocalTrack:
    track_id: int
    bbox: BBox
    conf: float
    last_seen: float
    hits: int = 1


class SimpleTracker:
    def __init__(self, name: str, iou_threshold: float, ttl: float):
        self.name = name
        self.iou_threshold = iou_threshold
        self.ttl = ttl
        self._next_id = 1
        self.tracks: Dict[int, LocalTrack] = {}

    def update(self, detections: List[Tuple[BBox, float]], now: float) -> List[LocalTrack]:
        candidates = []

        for tid, track in self.tracks.items():
            for di, (bbox, conf) in enumerate(detections):
                iou = box_iou(track.bbox, bbox)
                if iou >= self.iou_threshold:
                    candidates.append((iou, tid, di, bbox, conf))

        candidates.sort(reverse=True, key=lambda x: x[0])

        matched_t, matched_d = set(), set()
        for _, tid, di, bbox, conf in candidates:
            if tid in matched_t or di in matched_d:
                continue

            self.tracks[tid].bbox = bbox
            self.tracks[tid].conf = conf
            self.tracks[tid].last_seen = now
            self.tracks[tid].hits += 1

            matched_t.add(tid); matched_d.add(di)

        for di, (bbox, conf) in enumerate(detections):
            if di in matched_d:
                continue

            tid = self._next_id;  self._next_id += 1
            self.tracks[tid] = LocalTrack(tid, bbox, conf, now)

        for tid in [t for t, tr in self.tracks.items() if now - tr.last_seen > self.ttl]:
            del self.tracks[tid]

        return list(self.tracks.values())


@dataclass
class GlobalObject:
    global_id: int
    camera_name: str
    local_id: int
    bbox: BBox
    conf: float
    frame_w: int
    frame_h: int
    last_seen: float
    observations: int = 0
    seen_cameras: set = field(default_factory = set)
    counted: bool = False


class GlobalFusionCounter:
    def __init__(self, cfg: dict):
        self.min_confirmations = cfg["min_confirmations_to_count"]
        self.ttl = cfg["track_ttl_seconds"]
        self.match_x = cfg["match_x_threshold"]
        self.match_y = cfg["match_y_threshold"]
        self.match_area = cfg["match_area_ratio_threshold"]
        self.match_aspect = cfg["match_aspect_ratio_threshold"]
        self._next_id = 1
        self.objects: Dict[int, GlobalObject] = {}
        self._local_to_global: Dict[Tuple[str, int], int] = {}
        self.total_count = 0

    def _find_match(self, cam: str, lid: int, bbox: BBox, fw: int, fh: int, now: float) -> Optional[int]:
        key = (cam, lid)

        if key in self._local_to_global:
            gid = self._local_to_global[key]

            if gid in self.objects:
                return gid

        (cx, cy), area, aspect = normalize_box(bbox, fw, fh)
        best_gid, best_score = None, float("inf")

        for gid, obj in self.objects.items():
            if now - obj.last_seen > self.ttl * 2:
                continue

            (ex, ey), earea, easpect = normalize_box(obj.bbox, obj.frame_w, obj.frame_h)

            if abs(cx - ex) > self.match_x:
                continue

            if abs(cy - ey) > self.match_y:
                continue

            area_r   = max(area, earea)   / max(1e-9, min(area, earea))
            aspect_r = max(aspect, easpect) / max(1e-9, min(aspect, easpect))

            if area_r > self.match_area: continue
            if aspect_r > self.match_aspect: continue

            score = abs(cx - ex) * 0.25 + abs(cy - ey) * 0.75 + (area_r - 1) + (aspect_r - 1) * 0.5
            if score < best_score:
                best_score = score; best_gid = gid

        return best_gid

    def update(self, observations: List[dict], now: float) -> None:
        used = set()

        for obs in sorted(observations, key=lambda o: o["conf"], reverse=True):
            cam = obs["camera_name"]
            lid = obs["local_id"]
            bbox = obs["bbox"]
            fw, fh = obs["frame_w"], obs["frame_h"]
            conf = obs["conf"]

            gid = self._find_match(cam, lid, bbox, fw, fh, now)
            if gid in used:
                gid = None

            if gid is None:
                gid = self._next_id;  self._next_id += 1

                self.objects[gid] = GlobalObject(
                    global_id=gid, camera_name=cam, local_id=lid,
                    bbox=bbox, conf=conf, frame_w=fw, frame_h=fh, last_seen=now,
                )
            else:
                obj = self.objects[gid]
                obj.camera_name = cam; obj.local_id = lid
                obj.bbox = bbox; obj.conf = conf
                obj.frame_w = fw; obj.frame_h = fh
                obj.last_seen = now

            obj = self.objects[gid]
            obj.observations += 1
            obj.seen_cameras.add(cam)
            used.add(gid)

            if (not obj.counted and obj.observations >= self.min_confirmations):
                obj.counted = True
                log.info(f"Box confirmed (global_id={gid})")

            self._local_to_global[(cam, lid)] = gid

        stale = [gid for gid, obj in self.objects.items() if now - obj.last_seen > self.ttl * 4]
        for gid in stale:
            del self.objects[gid]

        for key in [k for k, v in self._local_to_global.items() if v not in self.objects]:
            del self._local_to_global[key]

        prev = self.total_count
        self.total_count = sum(1 for obj in self.objects.values() if obj.counted)
        if self.total_count != prev:
            log.info(f"Count changed: {prev} -> {self.total_count}")

    def reset(self) -> None:
        self.objects.clear()
        self._local_to_global.clear()
        self.total_count = 0
        self._next_id    = 1

def run_inference(model: YOLO, frame: np.ndarray, device: str, cfg: dict) -> Tuple[List[Tuple[BBox, float]], List[BBox], List[Tuple[BBox, float]]]:
    results = model.predict(
        source = frame,
        conf = cfg["conf_threshold"],
        imgsz = cfg["img_size"],
        device = device,
        half = False,
        verbose = False,
    )

    pallet_boxes: List[BBox] = []
    raw_boxes: List[Tuple[BBox, float]] = []

    if not results or results[0].boxes is None:
        return [], [], []

    result = results[0]
    names  = result.names

    for det in result.boxes:
        cls_name = names[int(det.cls[0])]
        bbox     = tuple(map(int, det.xyxy[0]))
        conf     = float(det.conf[0])

        if cls_name == cfg["class_pallet"]:
            pallet_boxes.append(bbox)
        elif cls_name == cfg["class_box"]:
            raw_boxes.append((bbox, conf))

    if pallet_boxes:
        countable_boxes = [
            (bbox, conf)
            for bbox, conf in raw_boxes
            if any(boxes_overlap(bbox, p) for p in pallet_boxes)
        ]
    else:
        countable_boxes = []

    return raw_boxes, pallet_boxes, countable_boxes


def draw_frame(frame: np.ndarray, box_tracks: List[LocalTrack], pallet_boxes: List[BBox], cam_label: str, cfg: dict) -> np.ndarray:
    out = frame.copy()

    for p in pallet_boxes:
        cv2.rectangle(out, (p[0], p[1]), (p[2], p[3]), (200, 120, 0), 2)
        cv2.putText(out, "pallet", (p[0], max(16, p[1] - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 120, 0), 2)

    for t in box_tracks:
        x1, y1, x2, y2 = t.bbox
        color = (0, 255, 0) if t.conf >= cfg["conf_threshold"] else (0, 220, 220)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        cv2.putText(out, f"box {t.conf:.0%}",
                    (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
    return out


def fit_frame(frame: Optional[np.ndarray], w: int, h: int, bg: tuple) -> np.ndarray:
    canvas = np.full((h, w, 3), bg, dtype=np.uint8)

    if frame is None:
        return canvas
    
    sh, sw = frame.shape[:2]
    scale  = min(w / max(1, sw), h / max(1, sh))
    rw, rh = max(1, int(sw * scale)), max(1, int(sh * scale))
    resized = cv2.resize(frame, (rw, rh))
    ox, oy  = (w - rw) // 2, (h - rh) // 2
    canvas[oy:oy + rh, ox:ox + rw] = resized

    return canvas


def draw_hud(canvas: np.ndarray, fps: float, total: int,
             expected: Optional[int], typing_buf: str,
             arduino_ok: bool) -> None:
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 110), (0, 0, 0), -1)

    if expected is None:
        status_text  = "Awaiting expected qty"
        status_color = (200, 200, 200)
    elif total == expected:
        status_text  = "MATCH"
        status_color = (0, 220, 0)
    else:
        status_text  = "NOT MATCH"
        status_color = (0, 0, 255)

    ard_color = (0, 255, 0) if arduino_ok else (80, 80, 255)
    ard_label = "Arduino: CONNECTED" if arduino_ok else "Arduino: OFFLINE"

    cv2.putText(canvas, f"FPS: {fps:.1f}", (20,  40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(canvas, f"Boxes: {total}", (20,  80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0),     2)
    cv2.putText(canvas, f"Expected: {expected or '—'}", (400, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(canvas, f"Status: {status_text}", (400, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, status_color,    2)
    cv2.putText(canvas, ard_label, (900, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, ard_color,       2)
    cv2.putText(canvas, f"Input: {typing_buf or '_'} [digits+Enter | Backspace | r=reset | q=quit]", (900, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)


def handle_arduino(arduino: Optional[ArduinoController], total: int, expected: Optional[int]) -> None:
    if arduino is None or not arduino.connected:
        return
    
    if expected is None:
        arduino.idle()
    elif total == expected:
        arduino.open_gate()
    else:
        arduino.close_gate()

def main() -> None:
    log.info("=" * 60)
    log.info("  Batch Validator — starting up")
    log.info("=" * 60)

    device = select_device()
    log.info(f"Loading model: {CONFIG['model_path']}")
    model = YOLO(CONFIG["model_path"])
    if device != "cpu":
        model.to(device)

    arduino: Optional[ArduinoController] = None
    port = find_arduino_port()
    if port:
        arduino = ArduinoController(ArduinoConfig(port=port))
    else:
        log.warning("Arduino not found — continuing without hardware.")

    cameras = [
        CameraStream(idx, CONFIG["camera_width"], CONFIG["camera_height"])
        for idx in CONFIG["camera_indices"]
    ]

    if not all(cam.running for cam in cameras):
        log.error("Could not open both cameras. Check USB connections and indices.")
        for cam in cameras: cam.release()

        if arduino: arduino.disconnect()
        return

    trackers = [
        SimpleTracker(
            name = f"cam{i}",
            iou_threshold = CONFIG["local_iou_threshold"],
            ttl = CONFIG["track_ttl_seconds"],
        )

        for i in range(len(cameras))
    ]

    fusion = GlobalFusionCounter(CONFIG)
    expected_qty: Optional[int] = None
    typing_buf = ""
    last_status = None
    last_t = time.time()

    cv2.namedWindow(CONFIG["window_name"], cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(CONFIG["window_name"], cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    log.info("Running. Press 'q' to quit.")

    try:
        while True:
            now = time.time()
            fps = 1.0 / max(1e-9, now - last_t);  last_t = now

            panels = []
            observations = []

            for i, cam in enumerate(cameras):
                ok, frame = cam.read()

                if not ok or frame is None:
                    placeholder = np.full(
                        (CONFIG["camera_height"], CONFIG["camera_width"], 3),
                        CONFIG["bg_color"], dtype=np.uint8,
                    )

                    cv2.putText(placeholder, f"Camera {i+1} offline", (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                    panels.append(placeholder)

                    continue

                trackable_boxes, pallet_boxes, countable_boxes = run_inference(model, frame, device, CONFIG)
                tracks = trackers[i].update(trackable_boxes, now)

                countable_ids = {bbox for bbox, _ in countable_boxes}
                observations.extend({
                    "camera_name": trackers[i].name,
                    "local_id": t.track_id,
                    "bbox": t.bbox,
                    "conf": t.conf,
                    "frame_w": frame.shape[1],
                    "frame_h": frame.shape[0],
                } for t in tracks if t.bbox in countable_ids)

                annotated = draw_frame(frame, tracks, pallet_boxes, f"Cam {i+1}", CONFIG)

                cv2.rectangle(annotated, (0, 0), (380, 80), (0, 0, 0), -1)
                cv2.putText(annotated, f"Cam {i+1}  tracks: {len(tracks)}", (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(annotated, f"Pallets: {len(pallet_boxes)}", (12, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 120, 0), 2)

                panels.append(annotated)

            fusion.update(observations, now)
            total = fusion.total_count

            current_status = (total, expected_qty)
            if current_status != last_status:
                handle_arduino(arduino, total, expected_qty)

                log.info(f"Count={total}  Expected={expected_qty}  "f"Status={'MATCH' if expected_qty is not None and total == expected_qty else 'NO MATCH' if expected_qty is not None else 'AWAITING'}")
                last_status = current_status

            pw, ph = CONFIG["panel_width"], CONFIG["panel_height"]
            bg = CONFIG["bg_color"]
            left = fit_frame(panels[0] if len(panels) > 0 else None, pw, ph, bg)
            right = fit_frame(panels[1] if len(panels) > 1 else None, pw, ph, bg)
            canvas = np.hstack([left, right])

            draw_hud(canvas, fps, total, expected_qty, typing_buf, arduino is not None and arduino.connected)
            cv2.imshow(CONFIG["window_name"], canvas)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif ord("0") <= key <= ord("9"):
                typing_buf += chr(key)
            elif key in (8, 127):
                typing_buf = typing_buf[:-1]
            elif key in (13, 10):
                if typing_buf:
                    expected_qty = int(typing_buf)
                    typing_buf = ""
                    
                    handle_arduino(arduino, total, expected_qty)
                    last_status = None
            elif key == ord("r"):
                fusion.reset()

                for t in trackers:
                    t.tracks.clear();  t._next_id = 1

                expected_qty = None
                typing_buf = ""
                last_status = None

                if arduino:
                    arduino.idle()

                log.info("Reset: all counts cleared.")

    finally:
        for cam in cameras:
            cam.release()
            
        if arduino:
            arduino.idle()
            arduino.disconnect()

        cv2.destroyAllWindows()
        log.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Interrupted by user.")
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        sys.exit(1)