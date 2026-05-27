/*
  Batch Validator - Clean Version
  Servo + Dual LED Control
*/

#include <Servo.h>

#define SERVO_PIN 9
#define GREEN_PIN 13
#define RED_PIN A1  // Changed to A1 (safer than serial Pin 1)

Servo gateServo;
String buffer = "";

void setup() {
  Serial.begin(9600);
  
  // Setup pins
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(RED_PIN, OUTPUT);
  
  // Ensure both LEDs OFF initially
  digitalWrite(GREEN_PIN, LOW);
  digitalWrite(RED_PIN, LOW);
  delay(200);
  digitalWrite(GREEN_PIN, LOW);
  digitalWrite(RED_PIN, LOW);
  
  // Setup servo
  gateServo.attach(SERVO_PIN);
  gateServo.write(0);  // Gate closed
  delay(500);
  
  Serial.println("Arduino Ready - Batch Validator System");
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      handleCommand(buffer);
      buffer = "";
    } else {
      buffer += c;
    }
  }
}

void handleCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();
  
  if (cmd == "GATE_OPEN") {
    // MATCH: Gate open, Green ON, Red OFF
    gateServo.write(90);
    delay(200);
    
    digitalWrite(GREEN_PIN, HIGH);
    delay(50);
    digitalWrite(RED_PIN, LOW);
    delay(50);
    
    Serial.println("OK:GATE_OPENED");
  }
  else if (cmd == "GATE_CLOSE") {
    // MISMATCH: Gate close, Green OFF, Red ON
    gateServo.write(0);
    delay(200);
    
    digitalWrite(GREEN_PIN, LOW);
    delay(50);
    digitalWrite(RED_PIN, HIGH);
    delay(50);
    
    Serial.println("OK:GATE_CLOSED");
  }
  else if (cmd == "STATUS") {
    Serial.println("OK:READY");
  }
  else if (cmd == "TEST") {
    Serial.println("TEST:STARTING");
    gateServo.write(90);
    delay(1000);
    gateServo.write(0);
    delay(1000);
    Serial.println("TEST:COMPLETE");
  }
  else {
    Serial.println("ERROR:UNKNOWN");
  }
}
