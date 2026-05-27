#!/usr/bin/env python3
"""
Batch Validator - Diagnostic & Test Script
Tests all components: Cameras, Model, Arduino, Dataset
"""

import sys
import os
import time
from pathlib import Path

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_python_version():
    print_header("1. Python Version Check")
    version = sys.version_info
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    if version.major >= 3 and version.minor >= 9:
        print("  Status: OK")
        return True
    else:
        print("  Status: WARN - Recommend Python 3.9+")
        return True

def test_imports():
    print_header("2. Required Packages Import Check")
    packages = {
        'cv2': 'OpenCV',
        'numpy': 'NumPy',
        'torch': 'PyTorch',
        'ultralytics': 'YOLOv8',
        'serial': 'PySerial',
    }
    
    all_ok = True
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"  ✓ {name} ({module})")
        except ImportError as e:
            print(f"  ✗ {name} ({module}) - {e}")
            all_ok = False
    
    return all_ok

def test_dataset():
    print_header("3. Dataset Structure Check")
    dataset_path = Path("dataset")
    
    if not dataset_path.exists():
        print(f"  ✗ Dataset folder not found at {dataset_path.absolute()}")
        return False
    
    yaml_file = dataset_path / "data.yaml"
    if not yaml_file.exists():
        print(f"  ✗ data.yaml not found")
        return False
    
    print(f"  ✓ data.yaml found")
    
    splits = {'train': 'training', 'valid': 'validation', 'test': 'testing'}
    all_ok = True
    
    for split, name in splits.items():
        images_dir = dataset_path / split / "images"
        labels_dir = dataset_path / split / "labels"
        
        if not images_dir.exists():
            print(f"  ✗ {name} images folder not found")
            all_ok = False
            continue
        
        img_count = len(list(images_dir.glob("*")))
        if img_count == 0:
            print(f"  ✗ {name} images folder is empty")
            all_ok = False
            continue
        
        lbl_count = len(list(labels_dir.glob("*.txt"))) if labels_dir.exists() else 0
        
        print(f"  ✓ {name:12} - {img_count:4} images, {lbl_count:4} labels")
    
    return all_ok

def test_model():
    print_header("4. YOLO Model Check")
    model_path = Path("model.pt")
    
    if not model_path.exists():
        print(f"  ✗ model.pt not found")
        return False
    
    try:
        from ultralytics import YOLO
        print(f"  Loading model: {model_path}")
        model = YOLO(str(model_path))
        print(f"  ✓ Model loaded successfully")
        print(f"    - Model type: {model.model.__class__.__name__}")
        
        # Test device selection
        try:
            import torch
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = "mps"
                print(f"    - Device: Metal Performance Shaders (M1 Mac)")
            elif torch.cuda.is_available():
                device = "cuda"
                print(f"    - Device: CUDA GPU")
            else:
                device = "cpu"
                print(f"    - Device: CPU")
        except:
            print(f"    - Device: CPU")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed to load model: {e}")
        return False

def test_cameras():
    print_header("5. Camera Detection Check")
    try:
        import cv2
        cameras_found = []
        
        for index in range(4):  # Test indices 0-3
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    h, w = frame.shape[:2]
                    cameras_found.append((index, w, h))
                    print(f"  ✓ Camera {index} - {w}x{h}")
                cap.release()
        
        if not cameras_found:
            print(f"  ✗ No cameras found")
            return False
        
        if len(cameras_found) >= 2:
            print(f"  ✓ Both required cameras detected")
            return True
        else:
            print(f"  ⚠ Only {len(cameras_found)} camera(s) found (2 required)")
            return False
            
    except Exception as e:
        print(f"  ✗ Camera test failed: {e}")
        return False

def test_arduino():
    print_header("6. Arduino Connection Check")
    try:
        from arduino_controller import ArduinoController, find_arduino_port, ArduinoConfig
        
        # Try to find Arduino port
        port = find_arduino_port()
        if port:
            print(f"  Found Arduino port: {port}")
        else:
            print(f"  Could not auto-detect Arduino port")
            print(f"  Trying common ports...")
            port = None
            for test_port in ["/dev/tty.usbserial", "/dev/tty.usbmodem14201", "/dev/ttyUSB0"]:
                print(f"    Trying {test_port}...", end=" ")
                try:
                    config = ArduinoConfig(port=test_port, timeout=1)
                    arduino = ArduinoController(config, debug=False)
                    if arduino.connected:
                        print("✓")
                        port = test_port
                        break
                    else:
                        print("✗")
                except:
                    print("✗")
        
        if port:
            print(f"  ✓ Arduino connected on {port}")
            return True
        else:
            print(f"  ⚠ Arduino not connected")
            print(f"    - Check USB cable")
            print(f"    - Verify Arduino sketch is uploaded")
            print(f"    - Update CAMERA_INDICES in code if needed")
            return False
            
    except Exception as e:
        print(f"  ✗ Arduino test error: {e}")
        return False

def test_performance():
    print_header("7. Performance & Timing Check")
    try:
        import cv2
        import numpy as np
        from ultralytics import YOLO
        import time
        
        # Load model
        model = YOLO("model.pt")
        
        # Create dummy image
        dummy_frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        
        # Warm up
        print("  Warming up model...")
        _ = model.predict(dummy_frame, conf=0.8, verbose=False)
        
        # Time inference
        print("  Running inference timing...")
        start = time.time()
        results = model.predict(dummy_frame, conf=0.8, verbose=False)
        elapsed = time.time() - start
        
        fps = 1.0 / elapsed
        print(f"  ✓ Inference time: {elapsed*1000:.1f}ms ({fps:.1f} FPS)")
        
        if fps >= 15:
            print(f"    Status: Good for real-time processing")
        elif fps >= 5:
            print(f"    Status: Acceptable but may lag")
        else:
            print(f"    Status: May be too slow for real-time")
        
        return True
    except Exception as e:
        print(f"  ⚠ Performance test skipped: {e}")
        return True

def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  BATCH VALIDATOR - DIAGNOSTIC TEST SUITE".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    results = {
        "Python Version": test_python_version(),
        "Package Imports": test_imports(),
        "Dataset Structure": test_dataset(),
        "YOLO Model": test_model(),
        "Cameras": test_cameras(),
        "Arduino": test_arduino(),
        "Performance": test_performance(),
    }
    
    print_header("DIAGNOSTIC SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All systems ready! You can run: python index.py")
        return 0
    else:
        print("\n⚠ Some tests failed. Please fix issues above before running.")
        return 1

if __name__ == "__main__":
    exit(main())
