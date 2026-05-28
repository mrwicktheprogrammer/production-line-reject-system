import cv2
import numpy as np
import serial
import glob
import time
import threading
from flask import Flask, Response

app = Flask(__name__)

# 1. AUTOMATIC SERIAL LINK FALLBACK
arduino = None
ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
for port in ports:
    try:
        arduino = serial.Serial(port, 115200, timeout=1)
        time.sleep(2)  
        print(f"[+] Production Serial Link Active: {port}")
        break
    except Exception:
        continue

if not arduino:
    print("[-] CRITICAL: Arduino link dropped out. Exiting.")
    exit()

# 2. DEVICE INDEX AUTO-SCANNER
cap = None
for idx in [0, 2, 1]:  
    cap = cv2.VideoCapture(idx)
    if cap.isOpened():
        ret, test_frame = cap.read()
        if ret:
            print(f"[+] Camera Eye locked onto Index {idx}")
            break
        cap.release()

if not cap or not cap.isOpened():
    print("[-] CRITICAL: Camera unreadable. Exiting.")
    exit()

# Optimize camera parameters for zero network latency
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)     
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)  
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

output_frame = None
frame_lock = threading.Lock()
is_rejecting = False

# 3. HIGH-SPEED REJECT ENGINE
def vision_reject_engine():
    global output_frame, is_rejecting
    
    # Define our virtual tripwire line on the screen (Y-coordinate 160 out of 240)
    TRIPWIRE_Y = 160 

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # Draw the physical tripwire line overlay onto the video (Yellow line)
        cv2.line(frame, (0, TRIPWIRE_Y), (320, TRIPWIRE_Y), (0, 255, 255), 2)
        cv2.putText(frame, "REJECT TRIPWIRE LINE", (10, TRIPWIRE_Y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

        if not is_rejecting:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Target color boundaries (Tracking RED objects as the "Defective" items)
            lower_red = np.array([0, 120, 70])
            upper_red = np.array([10, 255, 255])
            
            mask = cv2.inRange(hsv, lower_red, upper_red)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                if cv2.contourArea(largest_contour) > 200: 
                    M = cv2.moments(largest_contour)
                    if M["m00"] != 0:
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])

                        # UI bounding box around detected item
                        x, y, w, h = cv2.boundingRect(largest_contour)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                        cv2.circle(frame, (cX, cY), 4, (0, 255, 0), -1)
                        cv2.putText(frame, f"Defect Y: {cY}", (x, y - 5), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

                        # ACTION CONDITION: Triggered when defect crosses the tripwire line
                        if cY > TRIPWIRE_Y:
                            is_rejecting = True
                            cv2.putText(frame, "!!! REJECT ACTIVATED !!!", (50, 40), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                            
                            print(f"[!] Defect crossed tripwire at Y={cY}. Deploying reject arm!")
                            arduino.write(b"REJECT\n")
                            
                            # Pause processing loop briefly to let the mechanical swing execute safely
                            time.sleep(2.0) 
                            is_rejecting = False

        with frame_lock:
            output_frame = frame.copy()
            
        time.sleep(0.01)

# 4. LIGHTWEIGHT WEB HOSTING 
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
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + img_bytes + b'\r\n')

@app.route('/')
def home():
    return "<h1>🏭 Production Reject Dashboard</h1><hr><img src='/video_feed' width='320' height='240'>"

@app.route('/video_feed')
def video_feed():
    return Response(stream_generator(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    t = threading.Thread(target=vision_reject_engine, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
