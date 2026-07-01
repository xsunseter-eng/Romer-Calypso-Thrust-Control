/*
 * Romer Calypso Motor Driver - Main Board Firmware
 * Board: Arduino Uno R3
 * Protocol: USB Serial (115200 baud)
 */

#include <Servo.h>

// ESC Control Pins
const int ESC_LEFT_PIN = 9;
const int ESC_RIGHT_PIN = 10;

Servo escLeft;
Servo escRight;

// Motor Control State
bool isCommandActive = false;
unsigned long commandEndTime = 0;

// Serial parsing buffer
String serialBuffer = "";

void setup() {
  Serial.begin(115200);
  
  // Initialize ESCs (send neutral signal)
  escLeft.attach(ESC_LEFT_PIN);
  escRight.attach(ESC_RIGHT_PIN);
  stopEngines();
  
  Serial.println("Romer Calypso Driver Initialized.");
}

void loop() {
  // Check if current duration command has expired
  if (isCommandActive && millis() >= commandEndTime) {
    stopEngines();
    isCommandActive = false;
    Serial.println("Command duration expired. Engines stopped.");
  }
  
  // Non-blocking serial read
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      serialBuffer.trim();
      if (serialBuffer.length() > 0) {
        processCommand(serialBuffer);
      }
      serialBuffer = ""; // Reset buffer
    } else {
      serialBuffer += c;
    }
  }
}

void processCommand(String cmd) {
  // Emergency Stop / Cancel
  if (cmd == "STOP" || cmd == "CANCEL") {
    stopEngines();
    isCommandActive = false;
    Serial.println("EMERGENCY STOP executed.");
    return;
  }
  
  // Motor Control command
  // Expected Format: M,<L/R>,<Direction(F/R)>,<Power(0-100)>,<Duration_ms>
  if (cmd.startsWith("M,")) {
    int comma1 = cmd.indexOf(',');
    int comma2 = cmd.indexOf(',', comma1 + 1);
    int comma3 = cmd.indexOf(',', comma2 + 1);
    int comma4 = cmd.indexOf(',', comma3 + 1);

    if (comma1 > 0 && comma2 > 0 && comma3 > 0 && comma4 > 0) {
      String motor = cmd.substring(comma1 + 1, comma2);
      String dir = cmd.substring(comma2 + 1, comma3);
      int power = cmd.substring(comma3 + 1, comma4).toInt();
      unsigned long duration = cmd.substring(comma4 + 1).toInt();

      power = constrain(power, 0, 100);
      
      // Calculate PWM signal: 1500 is neutral. 
      // Basic ESC limits: 1100 (full reverse) to 1900 (full forward).
      // power (0-100) * 4 maps to (0-400), fitting safely within limits.
      int signal = 1500;
      if (dir == "F") signal = 1500 + (power * 4);
      else if (dir == "R") signal = 1500 - (power * 4);

      if (motor == "L") escLeft.writeMicroseconds(signal);
      else if (motor == "R") escRight.writeMicroseconds(signal);

      Serial.println("ACK: " + cmd);
      isCommandActive = true;
      commandEndTime = millis() + duration;
    }
  }
}

void stopEngines() {
  // 1500us is typically neutral/stop for bi-directional marine ESCs
  escLeft.writeMicroseconds(1500);
  escRight.writeMicroseconds(1500);
}
