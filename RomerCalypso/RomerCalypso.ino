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
  
  // Parse incoming commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command.length() > 0) {
      processCommand(command);
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
      int signal = 1500;
      if (dir == "F") signal = 1500 + (power * 5);
      else if (dir == "R") signal = 1500 - (power * 5);

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
