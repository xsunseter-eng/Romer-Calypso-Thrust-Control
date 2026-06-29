# Romer Calypso Motor Driver - Main Board

This repository contains the foundational software architecture and firmware for the **Romer Calypso Motor Driver**. The system acts as a hardware-agnostic control layer that safely translates high-level commands into precise physical actuation for marine/sea vehicle engines.

## Overview

The core philosophy of the system is to maintain a robust, decoupled interface between the high-level decision-making software (the "Master") and the physical hardware. The Arduino Uno R3 serves as the bridge between the Master control interface and the Electronic Speed Controllers (ESCs).

### Key Features
*   **Decoupled Control:** The Arduino handles the lower-level PWM signals, while the Master handles environmental logic (e.g., wet/dry limits).
*   **Optimized Communication:** Commands utilize a *Duration* parameter to prevent USB Serial communication overload, allowing the Master to sleep or focus on heavy processing.
*   **Built-in Safety:** Includes an immediate Emergency Stop command and hardcoded environmental limits (e.g., 30% power cap in dry conditions enforced by the Master).

## Repository Contents

*   **`RomerCalypso/RomerCalypso.ino`**: The main Arduino firmware. Parses CSV-formatted commands (e.g., `M,L,F,50,500`) and translates them to ESC PWM signals.
*   **`test_gui.py`**: A Python Tkinter-based Graphical User Interface for testing the motors. Features a virtual joystick with differential mixing, dry/wet simulation toggle, and an emergency stop button.
*   **`romer_calypso_whitepaper.pdf` & `.tex`**: The formal LaTeX technical whitepaper detailing the system architecture, hardware connections, and signal protocol.

## Getting Started

### Hardware Connections (Arduino Uno R3)
1.  **Left ESC Signal:** Pin 9
2.  **Right ESC Signal:** Pin 10
3.  **Ground:** Connect the ESC signal grounds to the Arduino GND pins.

### Running the Test GUI
```bash
python3 -m venv venv
source venv/bin/activate
pip install pyserial
python test_gui.py
```
*Note: Make sure to check the COM port setting in the python script (`/dev/ttyUSB0` or similar) to match your Arduino connection.*
