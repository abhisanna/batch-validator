# 🔴 Arduino Power Troubleshooting Guide

## Issue: No lights on Arduino + Not detected by macOS

This guide helps you fix the Arduino power/detection issue step by step.

---

## 🔍 Quick Diagnosis

| Symptom | Likely Cause |
|---------|-------------|
| ❌ No lights on Arduino | Power not reaching Arduino |
| ❌ Not detected in USB list | Could be power or damaged |
| ❌ No `/dev/tty.*` ports | Either power issue OR driver missing |

---

## 🛠️ Step-by-Step Troubleshooting

### **STEP 1: Check Physical Connection (2 min)**

```bash
# Look at your Arduino right now:
✓ Is USB cable plugged into Mac?
✓ Is USB cable plugged into Arduino?
✓ Are there any lights on the Arduino?
  (Usually a red LED that should always be on)
✓ Is the cable bent/damaged?
✓ Is the connector loose?
```

**If no lights:**
- Try a **different USB cable** (current one might be data-only or broken)
- Try a **different USB port** on your Mac
- Try **different USB hub** if using one
- Check if cable end is damaged/bent

### **STEP 2: Verify USB Detection on Mac (2 min)**

```bash
# Method 1: Use System Report
Open System Report:
1. Apple menu → About This Mac
2. Click "System Report..." button
3. Left sidebar → "USB"
4. Look for "Arduino" or "CH340" or "FTDI"
5. If you see it listed, driver is working!
6. If NOT listed, power is not reaching Arduino

# Method 2: Check terminal
system_profiler SPUSBDataType | grep -i arduino
```

**Expected output if connected:** Should show Arduino device

### **STEP 3: Check if LED Lights Up (1 min)**

Get close to your Arduino and look for:
- **Red LED** (usually labeled "PWR" or "ON")
- This should be **always on** when connected to USB
- If you see it: Power is good, driver might be missing
- If you DON'T see it: **Power is NOT reaching Arduino**

### **STEP 4: Check Serial Ports (1 min)**

```bash
# List all available serial ports
ls -la /dev/tty.* | grep -v Bluetooth

# Look for one of these:
# /dev/tty.usbserial*      (if using FTDI chip)
# /dev/tty.usbmodem*       (if using native USB)
# /dev/tty.SLAB_USBtoUART  (if using CH340)
```

**If you see one:** Driver is installed, try using that port
**If you see NONE:** Either power issue OR driver missing

---

## 🚨 Most Likely Scenarios & Fixes

### **Scenario 1: No lights on Arduino (MOST LIKELY)**

**Problem:** USB cable is not powering Arduino

**Fix:**
1. Try a **different USB cable** (essential!)
2. Make sure it's a **USB-A to USB-C cable** (not just any cable)
3. Use cable that comes with other devices (iPhone, etc.)
4. Test on **different Mac USB port**

**How to verify:** 
```bash
# After trying different cable, run:
system_profiler SPUSBDataType | grep -i arduino
```

---

### **Scenario 2: USB cable works but still not detected**

**Problem:** Driver not installed

**Solution:**

**If your Arduino has a CH340 chip** (common clone boards):
```bash
# Download driver from:
# https://github.com/WCHSoftware/ch34x_install_macos

# Or use Homebrew (easiest):
brew install wch-ch34x-usb-serial-driver
# Then restart Mac
```

**If your Arduino has FTDI chip:**
```bash
# Download from:
# https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers

# Or use Homebrew:
brew install ftdi-vcp-driver
# Then restart Mac
```

**If Arduino Uno (official):**
- Usually has built-in USB, should work without extra driver
- But some clones use CH340 instead

---

### **Scenario 3: Arduino appears in USB but no serial ports**

**Problem:** Driver installed but not completely

**Fix:**
```bash
# Reinstall driver
brew uninstall wch-ch34x-usb-serial-driver
brew install wch-ch34x-usb-serial-driver

# Or reinstall FTDI
brew uninstall ftdi-vcp-driver
brew install ftdi-vcp-driver

# Restart Mac
```

---

## 🔧 Complete Troubleshooting Checklist

- [ ] **Cable Check 1**: Try different USB cable
- [ ] **Cable Check 2**: Try different USB port on Mac
- [ ] **Power Check**: Look for red LED on Arduino (any lights?)
- [ ] **Detection Check**: Run `system_profiler SPUSBDataType | grep -i arduino`
- [ ] **Port Check**: Run `ls -la /dev/tty.* | grep -v Bluetooth`
- [ ] **Driver Check**: Arduino IDE can detect port (Tools → Port)
- [ ] **Reboot**: Restart Mac if you installed driver
- [ ] **Test**: Re-run `python test_arduino.py`

---

## 📱 Determine Your Arduino Type

Need to know which driver to install? Check:

```bash
# Connect Arduino and run:
system_profiler SPUSBDataType

# Look for one of these in output:
"Silicon Labs CP210x USB to UART Bridge"  → Install FTDI driver
"WinChiphead CH340"                       → Install CH340 driver
"Arduino LLC"                             → Likely built-in USB (no driver needed)
"Arduino Srl"                             → Official Arduino (no driver needed)
```

---

## 💡 Quick Test After Fix

Once Arduino shows up in USB:

```bash
# 1. Check if port appears
ls /dev/tty.*

# 2. Run Python test
cd /Users/abhisanna/Documents/batch-validator
source .venv/bin/activate
python test_arduino.py

# 3. OR open Arduino IDE to test
# Tools → Port → Select your Arduino
# Upload → Blink example
# If LED blinks: Arduino works!
```

---

## 🆘 If Nothing Works

### **Possible hardware damage:**
- Arduino might be defective
- USB connector might be broken
- Power supply circuit damaged

### **How to verify:**
1. Do you have access to another Mac or Linux PC?
   - Try connecting Arduino there
   - If detected elsewhere: issue is with your Mac USB
   - If not detected anywhere: Arduino might be damaged

2. Try **Arduino-as-ISP** method:
   - Use another Arduino to reprogram the bootloader
   - Indicates Arduino can be recovered

3. Visual inspection:
   - Look for burned components on board
   - Check for solder bridges or cracks
   - Look at USB connector for damage

---

## 📞 What to Tell Arduino Support

If contacting seller/support, provide:
- **Model**: Arduino UNO R3 ATmega328p
- **Issue**: No power indicator LED + not detected
- **Tests run**:
  - Different USB cables: ✓ Tried
  - Different Mac USB ports: ✓ Tried
  - System report shows: ✓ Not detected
  - Drivers installed: ✓ Yes/No

---

## ✅ Success Checklist

When Arduino is working properly:
- ✅ Red LED lights up immediately when connected
- ✅ Appears in `system_profiler SPUSBDataType`
- ✅ Port shows up in `ls /dev/tty.*`
- ✅ Arduino IDE detects it (Tools → Port)
- ✅ `python test_arduino.py` finds it
- ✅ Serial communication works

---

## 📋 Next Steps After Fixing

Once Arduino is detected:

```bash
# 1. Upload sketch
# In Arduino IDE:
# File → Open → arduino_sketch.ino
# Tools → Board → Arduino Uno
# Tools → Port → /dev/tty.usbserial... (or your port)
# Sketch → Upload

# 2. Test connection
python test_arduino.py

# 3. Run application
python index.py
```

---

**Most likely fix: Try a different USB cable!** ⚡
90% of "Arduino not detected" issues are cable problems.
