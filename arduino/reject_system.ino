#include <Servo.h>   // Library to control servo motors

// Create servo objects
Servo baseServo;
Servo shoulderServo;
Servo elbowServo;

String command = "";  // Store incoming text commands

// Pre-set positions for the base servo
int homeBase = 140;   // Safe position (arm tucked away)
int strikeBase = 70;  // Position to swipe across the track

void setup() {
    Serial.begin(115200);  // Start serial communication with computer

    // Attach servos to pins
    baseServo.attach(9);      
    shoulderServo.attach(6);  
    elbowServo.attach(5);     

    // Fix shoulder and elbow at a flat height above the track
    shoulderServo.write(100); 
    elbowServo.write(90);     
    
    // Move base servo to home position
    baseServo.write(homeBase);
    
    Serial.println("[+] Industrial Reject System Online.");
}

void loop() {
    // Check if there is data coming from computer
    while(Serial.available() > 0) {
        char c = Serial.read();  // Read one character
        if(c == '\n') {          // End of command
            processCommand(command);  // Handle the command
            command = "";             // Reset command string
        } else {
            command += c;             // Add character to command
        }
    }
}

void processCommand(String cmd) {
    // If the command starts with "REJECT"
    if(cmd.startsWith("REJECT")) {
        executeHighSpeedSwipe();  // Run the swipe function
    }
}

void executeHighSpeedSwipe() {
    Serial.println("[!] SWIPE DEPLOYED!");
    
    // Move base servo quickly to strike position
    baseServo.write(strikeBase);
    delay(350);  // Wait a short time to make sure it hits
    
    // Move base servo back to home position
    baseServo.write(homeBase);
    delay(300);  // Wait before ready again
}
