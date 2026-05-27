/*
  Test remaining untested pins: 0, 1, A1, A2, A3
*/

#define PIN_13 13
#define PIN_0 0
#define PIN_1 1
#define PIN_A1 A1
#define PIN_A2 A2

void setup() {
  Serial.begin(9600);
  pinMode(PIN_13, OUTPUT);
  pinMode(PIN_0, OUTPUT);
  pinMode(PIN_1, OUTPUT);
  pinMode(PIN_A1, OUTPUT);
  pinMode(PIN_A2, OUTPUT);
  
  // Turn all off
  digitalWrite(PIN_13, LOW);
  digitalWrite(PIN_0, LOW);
  digitalWrite(PIN_1, LOW);
  digitalWrite(PIN_A1, LOW);
  digitalWrite(PIN_A2, LOW);
  
  delay(1000);
}

void loop() {
  // Test Pin 0
  Serial.println("Pin 0 ON");
  digitalWrite(PIN_0, HIGH);
  delay(2000);
  digitalWrite(PIN_0, LOW);
  delay(1000);
  
  // Test Pin 1
  Serial.println("Pin 1 ON");
  digitalWrite(PIN_1, HIGH);
  delay(2000);
  digitalWrite(PIN_1, LOW);
  delay(1000);
  
  // Test A1
  Serial.println("A1 ON");
  digitalWrite(PIN_A1, HIGH);
  delay(2000);
  digitalWrite(PIN_A1, LOW);
  delay(1000);
  
  // Test A2
  Serial.println("A2 ON");
  digitalWrite(PIN_A2, HIGH);
  delay(2000);
  digitalWrite(PIN_A2, LOW);
  delay(1000);
  
  // Control pin
  Serial.println("Pin 13 ON (control)");
  digitalWrite(PIN_13, HIGH);
  delay(2000);
  digitalWrite(PIN_13, LOW);
  delay(2000);
}
