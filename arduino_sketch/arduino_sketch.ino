/*
  Batch Validator - Arduino IoT Control Sketch
  
  Hardware Setup:
  - Servo Motor SG90: Pin 9
  - Green LED: Pin 13 (via 220Ω resistor) - ON when quantities match
  - Red LED: Pin 1 (via 220Ω resistor) - ON when quantities don't match
  
  Communication Protocol:
  - Serial: 9600 baud
  - Commands: "GATE_OPEN" or "GATE_CLOSE"
  - Responses: "OK", "ERROR"
*/

#include <Servo.h>

// Pin Definitions
#define SERVO_PIN 9
#define GREEN_LED_PIN 13     // Green: Pin 13
#define RED_LED_PIN 0        // Red: Pin 0 (safer than Pin 1 for serial)

// Servo angles
#define GATE_CLOSED_ANGLE 0
#define GATE_OPEN_ANGLE 90

Servo gateServo;
String inputBuffer = "";

void setup() {
  Serial.begin(9600);
  
  // Initialize pins
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
  
  // Initialize servo
  gateServo.attach(SERVO_PIN);
  closeGate();
  
  // Explicitly turn OFF both LEDs at startup
  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, LOW);
  delay(100);
  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, LOW);
  
  Serial.println("Arduino Ready - Batch Validator System");
  delay(500);
}

void loop() {
  // Check for serial input
  if (Serial.available() > 0) {
    char inChar = Serial.read();
    
    if (inChar == '\n') {
      processCommand(inputBuffer);
      inputBuffer = "";
    } else {
      inputBuffer += inChar;
    }
  }
}

void processCommand(String command) {
  // Remove any whitespace
  command.trim();
  command.toUpperCase();
  
  if (command == "GATE_OPEN" || command == "OPEN") {
    openGate();
    // Match detected: Green ON, Red OFF
    digitalWrite(GREEN_LED_PIN, HIGH);
    digitalWrite(RED_LED_PIN, LOW);
    Serial.println("OK:GATE_OPENED");
  } 
  else if (command == "GATE_CLOSE" || command == "CLOSE") {
    closeGate();
    // Mismatch detected: Green OFF, Red ON
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, HIGH);
    Serial.println("OK:GATE_CLOSED");
  }
  else if (command == "STATUS") {
    Serial.println("OK:READY");
  }
  else if (command == "TEST") {
    Serial.println("TEST:STARTING");
    openGate();
    delay(1000);
    closeGate();
    Serial.println("TEST:COMPLETE");
  }
  else {
    Serial.println("ERROR:UNKNOWN_COMMAND");
  }
}

void openGate() {
  gateServo.write(GATE_OPEN_ANGLE);
  delay(500);  // Allow servo time to move
}

void closeGate() {
  gateServo.write(GATE_CLOSED_ANGLE);
  delay(500);  // Allow servo time to move
}
