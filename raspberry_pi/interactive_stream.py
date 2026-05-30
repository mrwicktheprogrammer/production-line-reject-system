# Import the tools we need
import cv2              # For camera and image processing
import numpy as np      # For handling arrays and math
import serial           # For talking to Arduino
import glob             # For finding device ports
import time             # For delays
import threading        # For running tasks at the same time
from flask import Flask, Response  # For making a simple web server

# Start a web app
app = Flask(__name__)

# -------------------------------
# 1. Connect to Arduino
# -------------------------------
arduino = None
# Look for Arduino ports
ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
for port in ports:
    try:
        # Try to open the port
        arduino = serial.Serial(port, 115200, timeout=1)
        time.sleep(2)  # Wait for Arduino to reset
        print(f"[+] Connected to Arduino at {port}")
        break
    except Exception:
        continue

# Stop if Arduino not found
if not arduino:
    print("[-] No Arduino found. Exiting.")
    exit()

# -------------------------------
# 2. Connect to Camera
# -------------------------------
cap = None
# Try different camera numbers
for idx in [0, 2, 1]:
    cap = cv2.VideoCapture(idx)
    if cap.isOpened():
        ret, test_frame = cap.read()
        if ret:
            print(f"[+] Camera found at index {idx}")
            break
        cap.release()

# Stop if no camera found
if not cap or not cap.isOpened():
    print("[-] No camera found. Exiting.")
    exit()

# Set camera to low‑lag mode
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

# -------------------------------
# Shared variables
# -------------------------------
output_frame = None
frame_lock = threading.Lock()  # To keep frames safe between threads
is_rejecting = False           # Flag so we don’t trigger twice

# -------------------------------
# 3. Vision Reject Engine
# -------------------------------
def vision_reject_engine():
    global output_frame, is_rejecting
    
    TRIPWIRE_Y = 160  # Line across the screen

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # Draw the tripwire line
        cv2.line(frame, (0, TRIPWIRE_Y), (320, TRIPWIRE_Y), (0, 255, 255), 2)
        cv2.putText(frame, "TRIPWIRE", (10, TRIPWIRE_Y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

        # Only check if not already rejecting
        if not is_rejecting:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Red color range
            lower_red = np.array([0, 120, 70])
            upper_red = np.array([10, 255, 255])

            # Find red areas
            mask = cv2.inRange(hsv, lower_red, upper_red)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                # Biggest red shape
                largest_contour = max(contours, key=cv2.contourArea)
                if cv2.contourArea(largest_contour) > 200:
                    M = cv2.moments(largest_contour)
                    if M["m00"] != 0:
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])

                        # Draw box and dot
                        x, y, w, h = cv2.boundingRect(largest_contour)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                        cv2.circle(frame, (cX, cY), 4, (0, 255, 0), -1)
                        cv2.putText(frame, f"Y: {cY}", (x, y - 5), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

                        # If defect crosses the line
                        if cY > TRIPWIRE_Y:
                            is_rejecting = True
                            cv2.putText(frame, "REJECT!", (50, 40), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                            print(f"[!] Defect crossed line at Y={cY}. Rejecting!")
                            arduino.write(b"REJECT\n")  # Tell Arduino to reject
                            time.sleep(2.0)             # Wait for arm to move
                            is_rejecting = False

        # Save frame for web stream
        with frame_lock:
            output_frame = frame.copy()
        time.sleep(0.01)

# -------------------------------
# 4. Web Server for Video
# -------------------------------
def stream_generator():
    global output_frame
    while True:
        with frame_lock:
            if output_frame is None:
                continue
            ret, encoded_img = cv2.imencode('.jpg', output_frame)
            if not ret:
                continue
            img_bytes = encoded_img.tobytes()
            
        # Send frame as part of video stream
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + img_bytes + b'\r\n')

# Home page
@app.route('/')
def home():
    return "<h1>Production Dashboard</h1><hr><img src='/video_feed' width='320' height='240'>"

# Video feed page
@app.route('/video_feed')
def video_feed():
    return Response(stream_generator(), mimetype='multipart/x-mixed-replace; boundary=frame')

# -------------------------------
# MAIN PROGRAM
# -------------------------------
if __name__ == '__main__':
    # Start vision engine in background
    t = threading.Thread(target=vision_reject_engine, daemon=True)
    t.start()
    # Start web server
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
