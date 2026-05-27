# Quick Reference Card

## Application Keyboard Controls (while running)

| Key | Action | Notes |
|-----|--------|-------|
| `0-9` | Type expected quantity | Build up the number digit by digit |
| `Enter/Return` | Submit expected quantity | Triggers comparison and Arduino action |
| `Backspace/Delete` | Remove last digit | Use to correct input |
| `r` | Reset system | Clears count, closes gate, resets trackers |
| `q` | Quit application | Safely disconnects Arduino and closes cameras |

## Example Usage Sequence

```
1. python index.py
   ├─ Wait for cameras to initialize
   ├─ Wait for Arduino to connect (if attached)
   └─ See fullscreen display with 2 camera feeds

2. Place 5 boxes in front of cameras
   └─ System displays: "Total unique boxes: 3"

3. Type: 5
   └─ Buffer shows: "5_"

4. Press Enter
   └─ System compares 3 vs 5
   └─ Display shows: "NOT MATCH" (red text)
   └─ Arduino: Close gate + Red LED blinks
   └─ Console: "[count] total=3 expected=5 status=NOT MATCH"

5. Add 2 more boxes
   └─ System updates: "Total unique boxes: 5"
   └─ Display automatically shows: "MATCH" (green text)
   └─ Arduino: Open gate + Green LED blinks

6. Press r to reset
   └─ Count reset to 0
   └─ Gate closes
   └─ Ready for next batch

7. Press q to quit
   └─ Arduino disconnects safely
   └─ Cameras release
   └─ Application exits
```

---

## Display Information

### Top-Left Corner (Camera 1)
- Live feed from USB Camera 0
- Detected boxes with bounding boxes (green rectangles)
- Local track IDs for each detection
- Confidence scores

### Top-Right Corner (Camera 2)
- Live feed from USB Camera 1
- Same detection overlay as Camera 1

### Top Bar Information
```
[Left]                        [Center]                    [Right]
FPS: 12.3                     Expected: unset             Typing buffer: 5_
Total unique boxes: 3         Status: AWAITING INPUT      Arduino: CONNECTED
```

**Status Colors:**
- **Green**: "MATCH" ✓ (detected count = expected count)
- **Red**: "NOT MATCH" ✗ (detected count ≠ expected count)
- **White**: "AWAITING INPUT" (expected count not set yet)

---

## Arduino Serial Commands

### From Python to Arduino
```
STATUS      → Check if Arduino is ready
             ← Response: "OK:READY"

GATE_OPEN   → Open gate + blink Green LED 3x
             ← Response: "OK:GATE_OPENED"

GATE_CLOSE  → Close gate + blink Red LED 3x
             ← Response: "OK:GATE_CLOSED"

TEST        → Run Arduino self-test
             ← Response: "TEST:COMPLETE"
```

### Communication Details
- **Baud Rate**: 9600
- **Data Bits**: 8
- **Stop Bits**: 1
- **Parity**: None
- **Handshake**: None
- **Line Ending**: \n (newline)

---

## Console Output Examples

### Startup
```
Initializing Arduino connection...
  Found Arduino port: /dev/tty.usbserial-1410
✓ Arduino connected on /dev/tty.usbserial-1410
→ Sent: STATUS
← Received: OK:READY
```

### Detection Running
```
[count] total=0 expected=unset status=awaiting input
[count] total=1 expected=3 status=NOT MATCH
[count] total=2 expected=3 status=NOT MATCH
[count] total=3 expected=3 status=MATCH
→ Arduino: Opening gate (GREEN LED)
→ Sent: GATE_OPEN
← Received: OK:GATE_OPENED
```

### Shutdown
```
✓ Arduino disconnected
```

---

## Configuration Quick Edits

### To change camera indices (if using different cameras)
**File**: `index.py`, Line ~15
```python
CAMERA_INDICES = (0, 1)  # Change to (1, 2) or others as needed
```

### To change detection confidence threshold
**File**: `index.py`, Line ~16
```python
CONF_THRESHOLD = 0.8  # Lower = more detections, Higher = fewer
```

### To change Arduino port manually
**File**: `index.py`, Line ~407 (in main() function)
```python
config = ArduinoConfig(port="/dev/tty.YOUR_PORT")
```

### To enable debug logging
**File**: `index.py`, Line ~410
```python
arduino = ArduinoController(config, debug=True)  # Change False → True
```

---

## Hardware Pin Reference

### Arduino UNO Pins Used
- **Pin 9**: PWM - Servo Motor Signal
- **Pin 12**: Digital Out - Green LED (via 220Ω)
- **Pin 13**: Digital Out - Red LED (via 220Ω)
- **GND**: Common Ground

### Servo Motor Angles
- **0°**: Gate CLOSED
- **90°**: Gate OPEN

### LED Timing
- **On Duration**: 500ms per blink
- **Number of Blinks**: 3 blinks per status change

---

## Keyboard Shortcuts Summary

```
Type digit(s)      Add to input buffer
Enter              Submit and compare
Backspace          Correct input
r                  Reset everything
q                  Quit (shutdown)
```

---

## File Locations

| Purpose | File |
|---------|------|
| Main app | `index.py` |
| Arduino firmware | `arduino_sketch.ino` |
| Arduino Python lib | `arduino_controller.py` |
| Run diagnostics | `python test_diagnostic.py` |
| Test Arduino only | `python test_arduino.py` |
| Setup docs | `SETUP_GUIDE.md` |
| This file | `QUICK_REFERENCE.md` |

---

## Common Issues & Quick Fixes

| Problem | Fix |
|---------|-----|
| Arduino won't connect | Unplug USB, wait 2 sec, reconnect |
| No cameras detected | Check USB cables, try different indices |
| Application freezes | Check Arduino is responding, restart app |
| LED not blinking | Check 220Ω resistors, pin connections |
| Wrong count detected | Adjust `CONF_THRESHOLD`, check lighting |
| Servo not moving | Check Pin 9, verify sketch uploaded |

---

## Performance Tips

1. **Faster inference**: Lower `IMG_SIZE` to 416
2. **Better accuracy**: Keep `IMG_SIZE` at 640
3. **Fewer false detections**: Increase `CONF_THRESHOLD` to 0.85+
4. **Detect more boxes**: Decrease `CONF_THRESHOLD` to 0.7
5. **Smoother tracking**: Decrease `TRACK_TTL_SECONDS`
6. **More stable counting**: Increase `MIN_CONFIRMATIONS_TO_COUNT`

---

**Print this card and keep it nearby while running the application!**

Last Updated: 2026-05-19
