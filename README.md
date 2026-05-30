# Automated Production Line Reject System

An industrial-inspired automation project utilizing a Raspberry Pi, an Arduino-controlled robotic arm, and computer vision (OpenCV) to identify and sort defective items on a simulated manufacturing line.

## How It Works
1. **Vision Inspection:** A USB webcam captures a real-time frame buffer at 320x240 resolution with minimal latency.
2. **Tripwire Detection:** The Python application tracks specific color profiles (e.g., Red for defects) using HSV color space thresholds. 
3. **High-Speed Actuation:** The moment a defect crosses a virtual screen "tripwire", an instantaneous command is sent via a `115200` baud serial link (`/dev/ttyUSB0`) to an Arduino Uno, deploying a rapid mechanical sweep profile to clear the line.

## Repository Structure
* `/raspberry_pi`: Contains the Flask web dashboard and high-speed OpenCV tracking logic.
* `/arduino`: Contains the synchronized high-speed servo swipe routines.
