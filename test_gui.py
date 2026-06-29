import tkinter as tk
import serial
import threading
import time
import math

class RomerCalypsoTester(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Romer Calypso Motor Tester")
        self.geometry("600x500")
        self.configure(bg="#1e293b")
        
        # Serial connection (Dummy by default, user can change port in code)
        self.serial_port = None
        self.port_name = "/dev/ttyUSB0"  # Updated Arduino port
        self.try_connect_serial()

        # State Variables
        self.is_wet = tk.BooleanVar(value=False) # Dry by default (30% limit)
        self.voltage_val = tk.DoubleVar(value=12.0)
        self.joystick_x = 0
        self.joystick_y = 0
        self.max_power = 100
        self.dry_power_limit = 30
        
        self.setup_ui()
        self.send_loop()

    def try_connect_serial(self):
        try:
            self.serial_port = serial.Serial(self.port_name, 115200, timeout=1)
            print(f"Connected to {self.port_name}")
        except Exception as e:
            print(f"Serial not connected ({self.port_name}): {e}")

    def setup_ui(self):
        # Header
        lbl_title = tk.Label(self, text="Control Interface (Master)", font=("Arial", 16, "bold"), bg="#1e293b", fg="#f8fafc")
        lbl_title.pack(pady=10)

        # Controls Frame
        ctrl_frame = tk.Frame(self, bg="#1e293b")
        ctrl_frame.pack(fill=tk.X, padx=20)

        # Dry/Wet Toggle
        chk_wet = tk.Checkbutton(ctrl_frame, text="Environment: WET (Uncheck for Dry / 30% Limit)", 
                                 variable=self.is_wet, bg="#1e293b", fg="#38bdf8", selectcolor="#0f172a")
        chk_wet.pack(side=tk.TOP, pady=5)

        # Voltage Slider
        volt_frame = tk.Frame(ctrl_frame, bg="#1e293b")
        volt_frame.pack(side=tk.TOP, pady=10)
        lbl_volt = tk.Label(volt_frame, text="Simulated Voltage (V):", bg="#1e293b", fg="#f8fafc")
        lbl_volt.pack(side=tk.LEFT)
        scale_volt = tk.Scale(volt_frame, from_=9.0, to=16.0, resolution=0.1, orient=tk.HORIZONTAL, 
                              variable=self.voltage_val, bg="#1e293b", fg="#34d399", length=200)
        scale_volt.pack(side=tk.LEFT, padx=10)

        # Joystick Canvas
        self.canvas_size = 200
        self.center = self.canvas_size / 2
        self.canvas = tk.Canvas(self, width=self.canvas_size, height=self.canvas_size, bg="#334155", highlightthickness=0)
        self.canvas.pack(pady=20)
        
        # Draw crosshair
        self.canvas.create_line(self.center, 0, self.center, self.canvas_size, fill="#64748b")
        self.canvas.create_line(0, self.center, self.canvas_size, self.center, fill="#64748b")
        
        # Joystick knob
        self.knob = self.canvas.create_oval(self.center-15, self.center-15, self.center+15, self.center+15, fill="#ef4444")

        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # Stop Button
        btn_stop = tk.Button(self, text="EMERGENCY STOP", font=("Arial", 14, "bold"), bg="#ef4444", fg="white",
                             activebackground="#dc2626", command=self.send_stop)
        btn_stop.pack(pady=10)

        # Telemetry Text
        self.lbl_telemetry = tk.Label(self, text="L: 0% | R: 0%", font=("Courier", 12), bg="#1e293b", fg="#94a3b8")
        self.lbl_telemetry.pack(pady=5)

    def on_drag(self, event):
        x = max(0, min(event.x, self.canvas_size))
        y = max(0, min(event.y, self.canvas_size))
        self.canvas.coords(self.knob, x-15, y-15, x+15, y+15)
        
        # Normalize to -1.0 to 1.0 (Y is inverted for visual up=forward)
        self.joystick_x = (x - self.center) / self.center
        self.joystick_y = -(y - self.center) / self.center

    def on_release(self, event):
        # Snap back to center
        self.canvas.coords(self.knob, self.center-15, self.center-15, self.center+15, self.center+15)
        self.joystick_x = 0
        self.joystick_y = 0
        self.send_stop()

    def send_stop(self):
        print("Sending STOP command")
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write(b"STOP\n")
        
        # Reset joystick visually and logically if stopped via button
        self.canvas.coords(self.knob, self.center-15, self.center-15, self.center+15, self.center+15)
        self.joystick_x = 0
        self.joystick_y = 0
        self.lbl_telemetry.config(text="L: 0% (STOP) | R: 0% (STOP)")

    def send_loop(self):
        # Differential drive mix
        forward = self.joystick_y
        turn = self.joystick_x
        
        left_mix = forward + turn
        right_mix = forward - turn
        
        # Normalize mix to -1.0 to 1.0
        max_mix = max(abs(left_mix), abs(right_mix), 1.0)
        left_mix /= max_mix
        right_mix /= max_mix
        
        # Calculate power
        left_power = abs(left_mix * 100)
        right_power = abs(right_mix * 100)
        
        # Apply Dry/Wet Limit
        current_max = self.max_power if self.is_wet.get() else self.dry_power_limit
        left_power = min(left_power, current_max)
        right_power = min(right_power, current_max)
        
        left_dir = 'F' if left_mix >= 0 else 'R'
        right_dir = 'F' if right_mix >= 0 else 'R'

        if self.joystick_x != 0 or self.joystick_y != 0:
            # Send Motor commands (e.g. M,L,F,50,200  => Motor Left, Forward, 50%, 200ms)
            cmd_l = f"M,L,{left_dir},{int(left_power)},500\n"
            cmd_r = f"M,R,{right_dir},{int(right_power)},500\n"
            
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(cmd_l.encode())
                time.sleep(0.01)
                self.serial_port.write(cmd_r.encode())
            
            self.lbl_telemetry.config(text=f"L: {int(left_power)}% {left_dir} | R: {int(right_power)}% {right_dir} | Volt: {self.voltage_val.get()}V")
            
        self.after(200, self.send_loop) # Send commands every 200ms while holding

if __name__ == "__main__":
    app = RomerCalypsoTester()
    app.mainloop()
