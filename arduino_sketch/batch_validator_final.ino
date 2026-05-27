#include <Servo.h>

#define GREEN_PIN 13
#define RED_PIN 1       // Only working non-interfering pins: 0 (breaks serial), 1, 9 (servo), 13
#define SERVO_PIN 9

Servo gateServo;
String inputBuffer = "";
unsigned long lastCommandTime = 0;

void setup() {
  Serial.begin(9600);
  
  // Force explicit initialization
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(RED_PIN, OUTPUT);
  pinMode(SERVO_PIN, OUTPUT);
  
  // Set BOTH LEDs to OFF at startup
  digitalWrite(GREEN_PIN, LOW);
  digitalWrite(RED_PIN, LOW);
  
  delay(100);
  
  gateServo.attach(SERVO_PIN);
  gateServo.write(0);  // Start closed
  
  delay(200);
  Serial.println("Arduino Ready");
}

void loop() {
  // Read serial commands
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (inputBuffer.length() > 0) {
        processCommand(inputBuffer);
        inputBuffer = "";
        lastCommandTime = millis();
      }
    } else {
      inputBuffer += c;
    }
  }
  
  // Safety: If no command for 5 seconds, reset LEDs to OFF
  if (millis() - lastCommandTime > 5000) {
    digitalWrite(GREEN_PIN, LOW);
    digitalWrite(RED_PIN, LOW);
    lastCommandTime = millis();
  }
}

void processCommand(String cmd) {
  cmd.trim();
  
  if (cmd == "GATE_OPEN") {
    openGate();
  } 
  else if (cmd == "GATE_CLOSE") {
    closeGate();
  }
  else if (cmd == "STATUS") {
    Serial.println("OK:READY");
  }
  else if (cmd == "IDLE") {
    // Explicitly turn OFF both LEDs
    digitalWrite(GREEN_PIN, LOW);
    digitalWrite(RED_PIN, LOW);
    Serial.println("OK:IDLE");
  }
  else {
    Serial.println("ERROR:UNKNOWN");
  }
}

void openGate() {
  // Match condition: Green ON, Red OFF, gate opens
  gateServo.write(90);
  delay(200);
  
  // Explicit state setting with delays
  digitalWrite(GREEN_PIN, HIGH);
  delay(50);
  digitalWrite(RED_PIN, LOW);
  delay(50);
  
  Serial.println("OK:GATE_OPENED");
}

void closeGate() {
  // Mismatch condition: Green OFF, Red ON, gate closes
  gateServo.write(0);
  delay(200);
  
  // Explicit state setting with delays
  digitalWrite(GREEN_PIN, LOW);
  delay(50);
  digitalWrite(RED_PIN, HIGH);
  delay(50);
  
  Serial.println("OK:GATE_CLOSED");
}
