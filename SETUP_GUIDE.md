# Batch Validator - Complete Setup & Execution Guide

## Project Overview
YOLOv8-based object detection system with dual-camera fusion, automatic box counting, and Arduino IoT integration for gate control and LED feedback.

### System Architecture
```
Webcam1 ─────┐
             ├─→ YOLO Detection ─→ Fusion Counter ─→ Quantity Match Check ─→ Arduino Control
Webcam2 ─────┘                                              │
                                                            ├─→ Gate OPEN + Green LED
                                                            └─→ Gate CLOSED + Red LED
```

---

## 🔧 Hardware Setup

### Arduino Connections (UNO R3 ATmega328p)
```
┌─────────────────────────────────────────────┐
│        Arduino UNO R3 (ATmega328p)         │
├─────────────────────────────────────────────┤
│ Pin 9  ─→ Servo Motor SG90 (PWM signal)   │
│ Pin 12 ─→ Green LED (via 220Ω resistor)   │
│ Pin 13 ─→ Red LED (via 220Ω resistor)     │
│ GND    ─→ Common GND (Servo, LEDs)        │
│ 5V     ─→ Power (optional, for LEDs)      │
└─────────────────────────────────────────────┘
```

### Servo Motor SG90 Pinout
- Red wire → 5V
- Brown wire → GND
- Orange/Yellow wire → Pin 9

### LED Connections
- Green LED: Anode → Pin 12, Cathode → GND (via 220Ω)
- Red LED: Anode → Pin 13, Cathode → GND (via 220Ω)

---

## 📦 Installation Steps

### 1. Clone/Setup Python Environment
```bash
cd /Users/abhisanna/Documents/batch-validator
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Upload Arduino Sketch
1. Open Arduino IDE
2. Open `arduino_sketch.ino`
3. Select Board: "Arduino Uno"
4. Select Port: The USB port where your Arduino is connected
5. Click Upload button
6. Verify "Done uploading" message

To find your Arduino port on macOS:
```bash
# Method 1: List USB devices
ls -la /dev/tty.* | grep -i usb

# Method 2: Use Arduino IDE (Tools → Port)

# Method 3: Use system profiler
system_profiler SPUSBDataType | grep -A5 Arduino
```

---

## ▶️ Running the Application

### Basic Execution
```bash
python index.py
```

### With Debug Output
```bash
python index.py
```

### Command Line Controls (while running)
| Key | Action |
|-----|--------|
| `0-9` | Type expected box quantity |
| `Enter` | Submit expected quantity |
| `Backspace` | Delete last digit |
| `r` | Reset count to 0 and close gate |
| `q` | Quit application |

### Example Usage Flow
```
1. Start application: python index.py
2. Two webcam feeds appear fullscreen
3. Place boxes in front of cameras
4. Type expected quantity (e.g., "5")
5. Press Enter
6. System displays:
   - If correct count → "MATCH" (Green LED on, gate opens)
   - If wrong count → "NOT MATCH" (Red LED on, gate closed)
7. Press 'r' to reset and try again
8. Press 'q' to quit
```

---

## 🤖 Model Training (Optional)

If you want to retrain the YOLOv8 model on your dataset:

```bash
python train.py
```

This will:
- Train on 150 epochs with early stopping at patience=20
- Use 640x640 resolution images
- Apply augmentations via Roboflow
- Save best weights to `runs/detect/batch-validator-res/weights/best.pt`
- Generate performance metrics (mAP, Precision, Recall, Accuracy)

### Expected Training Metrics
- **mAP (mean Average Precision)**: ≥ 85%
- **Precision**: ≥ 90%
- **Recall**: ≥ 85%
- **Training Time**: ~2-4 hours on M1 Mac

---

## 🔍 Expected Output

### Console Output (Running Application)
```
Initializing Arduino connection...
  Found Arduino port: /dev/tty.usbserial-1410
✓ Arduino connected on /dev/tty.usbserial-1410
→ Sent: STATUS
← Received: OK:READY
[count] total=0 expected=unset status=awaiting input
[count] total=1 expected=3 status=NOT MATCH
[count] total=2 expected=3 status=NOT MATCH
[count] total=3 expected=3 status=MATCH
→ Arduino: Opening gate (GREEN LED)
→ Sent: GATE_OPEN
← Received: OK:GATE_OPENED
```

### GUI Display
- Top-left panel: Camera 1 feed with detected boxes
- Top-right panel: Camera 2 feed with detected boxes
- Top bar: FPS, total count, expected count, status, Arduino connection
- Status colors:
  - Green text: "MATCH" ✓
  - Red text: "NOT MATCH" ✗
  - White text: "Awaiting expected qty"

---

## 🐛 Troubleshooting

### Arduino Connection Issues
```bash
# Check if Arduino port is recognized
ls /dev/tty.*

# If not found, try:
# 1. Unplug USB cable
# 2. Wait 5 seconds
# 3. Plug back in
# 4. Check Arduino IDE Tools → Port
```

### Camera Not Opening
```bash
# Test camera indices
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera 0:', cap.isOpened())"
python -c "import cv2; cap = cv2.VideoCapture(1); print('Camera 1:', cap.isOpened())"

# If needed, modify CAMERA_INDICES in index.py
```

### Model Not Detecting Boxes
- Ensure adequate lighting
- Check confidence threshold (CONF_THRESHOLD=0.8 in index.py)
- Verify model.pt file exists
- Test with `python -c "from ultralytics import YOLO; m = YOLO('model.pt'); print('Model loaded')`

### PySerial Import Error
```bash
pip install --upgrade pyserial
```

---

## 📊 Dataset Information

- **Source**: Roboflow (miniature boxes and pallets)
- **Classes**: 1 (box)
- **Total Images**: 2,167 (80% train, 10% val, 10% test)
- **Preprocessing**: Brightness, noise, blur augmentation
- **Training/Validation Split**: 80/10/10

---

## 🎯 Key Features Implemented

✅ Dual-camera real-time detection with fusion counter
✅ Box deduplication using tag IDs (avoids double-counting)
✅ Quantity comparison logic
✅ Arduino servo motor control
✅ LED feedback (Green=Match, Red=Mismatch)
✅ Multi-threaded camera streaming
✅ FPS monitoring
✅ Configurable detection threshold
✅ Graceful cleanup and disconnection

---

## 📝 Notes

- The application runs in fullscreen on Mac
- Fusion timeout: 1.5 seconds (objects older than this are dropped)
- Servo angles: 0° (closed), 90° (open)
- LED blink count: 3 blinks on status change
- Baud rate: 9600 (Arduino ↔ Python)

---

## 🤝 Support

For issues or questions:
1. Check troubleshooting section
2. Verify Arduino sketch uploaded correctly
3. Test Arduino connection independently
4. Review console output for error messages
5. Ensure dataset is properly structured

---

**Last Updated**: 2026-05-19
**Project**: Batch Validator - IoT Object Detection System
