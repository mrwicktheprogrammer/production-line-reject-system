#include <Servo.h>

Servo baseServo;
Servo shoulderServo;
Servo elbowServo;

String command = "";

// High-speed static positions
int homeBase = 140;      // Tucked safely completely away from the track
int strikeBase = 70;     // Fast forward arc angle to swipe across the lane

void setup() {
    Serial.begin(115200);

    baseServo.attach(9);      
    shoulderServo.attach(6);  
    elbowServo.attach(5);     

    // Lock the structural joints to a rigid, flat height over the track surface
    shoulderServo.write(100); 
    elbowServo.write(90);     
    
    // Move base to ready position
    baseServo.write(homeBase);
    
    Serial.println("[+] Industrial Reject System Online.");
}

void loop() {
    while(Serial.available() > 0) {
        char c = Serial.read();
        if(c == '\n') {
            processCommand(command);
            command = ""; 
        } else {
            command += c;
        }
    }
}

void processCommand(String cmd) {
    if(cmd.startsWith("REJECT")) {
        executeHighSpeedSwipe();
    }
}

void executeHighSpeedSwipe() {
    Serial.println("[!] SWIPE DEPLOYED!");
    
    // 1. Instantly snap the base servo across the lane (no smooth damping, purely max speed)
    baseServo.write(strikeBase);
    delay(350); // Small pause at peak extension to guarantee contact
    
    // 2. Snap immediately back to the home dock position to let the line keep running
    baseServo.write(homeBase);
    delay(300); 
}
