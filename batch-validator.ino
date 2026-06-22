/*
 * Batch Validator — Arduino UNO Gate Controller
 *
 * Pin Map (per CLAUDE.md):
 *   PIN  9  → Servo SG90 (gate)
 *   PIN 12  → Red LED  + 220Ω resistor
 *   PIN 13  → Green LED + 220Ω resistor
 *
 * Serial commands (9600 baud, newline-terminated):
 *   GATE_OPEN   → servo 90°, green ON,  red OFF  → replies "OK:GATE_OPENED"
 *   GATE_CLOSE  → servo  0°, green OFF, red ON   → replies "OK:GATE_CLOSED"
 *   IDLE        → both LEDs OFF, servo stays      → replies "OK:IDLE"
 *   STATUS      → health check                    → replies "OK:READY"
 */

#include <Servo.h>

// ── Pin definitions ────────────────────────────────────────────────────────
#define PIN_SERVO  9
#define PIN_GREEN 13
#define PIN_RED   12   // NOTE: never use PIN 0/1 — those are RX/TX (breaks serial)

// ── Servo positions ────────────────────────────────────────────────────────
#define SERVO_OPEN  -90
#define SERVO_CLOSED  0

// ── Safety timeout ─────────────────────────────────────────────────────────
// If no command arrives within this window, LEDs are turned off automatically.
#define IDLE_TIMEOUT_MS 5000

// ── Globals ────────────────────────────────────────────────────────────────
Servo gateServo;
String inputBuffer        = "";
unsigned long lastCmdTime = 0;

// ── Setup ──────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(9600);

  pinMode(PIN_GREEN, OUTPUT);
  pinMode(PIN_RED,   OUTPUT);

  digitalWrite(PIN_GREEN, LOW);
  digitalWrite(PIN_RED,   LOW);

  gateServo.attach(PIN_SERVO);
  gateServo.write(SERVO_CLOSED);

  delay(200);
  lastCmdTime = millis();
  Serial.println("OK:READY");
}

// ── Main loop ──────────────────────────────────────────────────────────────
void loop() {
  // Read serial into buffer, process on newline
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (inputBuffer.length() > 0) {
        processCommand(inputBuffer);
        inputBuffer  = "";
        lastCmdTime  = millis();
      }
    } else {
      inputBuffer += c;
    }
  }

  // Safety timeout — turn off both LEDs if host goes silent
  if (millis() - lastCmdTime > IDLE_TIMEOUT_MS) {
    digitalWrite(PIN_GREEN, LOW);
    digitalWrite(PIN_RED,   LOW);
    lastCmdTime = millis();
  }
}

// ── Command dispatcher ─────────────────────────────────────────────────────
void processCommand(String cmd) {
  cmd.trim();

  if      (cmd == "GATE_OPEN")  { openGate();  }
  else if (cmd == "GATE_CLOSE") { closeGate(); }
  else if (cmd == "IDLE")       { setIdle();   }
  else if (cmd == "STATUS")     { Serial.println("OK:READY"); }
  else                          { Serial.println("ERROR:UNKNOWN_CMD"); }
}

// ── Actions ────────────────────────────────────────────────────────────────
void openGate() {
  gateServo.write(SERVO_OPEN);
  delay(200);
  digitalWrite(PIN_RED,   LOW);
  digitalWrite(PIN_GREEN, HIGH);
  Serial.println("OK:GATE_OPENED");
}

void closeGate() {
  gateServo.write(SERVO_CLOSED);
  delay(200);
  digitalWrite(PIN_GREEN, LOW);
  digitalWrite(PIN_RED,   HIGH);
  Serial.println("OK:GATE_CLOSED");
}

void setIdle() {
  digitalWrite(PIN_GREEN, LOW);
  digitalWrite(PIN_RED,   LOW);
  Serial.println("OK:IDLE");
}
