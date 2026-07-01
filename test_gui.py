import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import threading
import time

class RomerCalypsoTester(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Romer Calypso Control Interface")
        self.geometry("900x700")
        self.configure(bg="#0f172a") # Dark Slate Theme
        
        # State Variables
        self.serial_port = None
        self.read_thread = None
        self.is_connected = False
        
        # Force Dry mode on by default (True means Wet, so False means Dry)
        self.is_wet = tk.BooleanVar(value=False)
        self.voltage_val = tk.DoubleVar(value=12.0)
        self.joystick_x = 0
        self.joystick_y = 0
        self.max_power = 100
        self.dry_power_limit = 30
        
        self.setup_ui()
        self.send_loop()

    def setup_ui(self):
        # Header
        header = tk.Frame(self, bg="#1e293b", height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        lbl_title = tk.Label(header, text="Romer Calypso - Master Interface", font=("Segoe UI", 18, "bold"), bg="#1e293b", fg="#e2e8f0")
        lbl_title.pack(side=tk.LEFT, padx=20, pady=10)

        # Connection Bar
        conn_frame = tk.Frame(self, bg="#0f172a")
        conn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(conn_frame, text="COM Port:", font=("Segoe UI", 12), bg="#0f172a", fg="#cbd5e1").pack(side=tk.LEFT, padx=(0,10))
        
        self.cb_ports = ttk.Combobox(conn_frame, font=("Segoe UI", 10), width=15, state="readonly")
        self.cb_ports.pack(side=tk.LEFT, padx=(0,10))
        
        btn_refresh = tk.Button(conn_frame, text="Refresh", font=("Segoe UI", 10), bg="#334155", fg="#f8fafc", relief=tk.FLAT, command=self.refresh_ports)
        btn_refresh.pack(side=tk.LEFT, padx=(0,10))
        
        self.btn_connect = tk.Button(conn_frame, text="Connect", font=("Segoe UI", 10, "bold"), bg="#10b981", fg="#ffffff", relief=tk.FLAT, width=12, command=self.toggle_connection)
        self.btn_connect.pack(side=tk.LEFT)
        
        self.lbl_status = tk.Label(conn_frame, text="Disconnected", font=("Segoe UI", 12, "bold"), bg="#0f172a", fg="#ef4444")
        self.lbl_status.pack(side=tk.RIGHT, padx=10)
        
        # Populate ports
        self.refresh_ports()

        # Main Content Layout
        main_frame = tk.Frame(self, bg="#0f172a")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left Panel (Controls)
        left_panel = tk.Frame(main_frame, bg="#1e293b", padx=20, pady=20)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, expand=False, ipadx=20)

        # Environment Limits
        tk.Label(left_panel, text="Environment Limits", font=("Segoe UI", 14, "bold"), bg="#1e293b", fg="#e2e8f0").pack(anchor=tk.W, pady=(0, 10))
        
        chk_wet = tk.Checkbutton(left_panel, text="WET Mode (Full Power Allowed)", 
                                 variable=self.is_wet, font=("Segoe UI", 11), bg="#1e293b", fg="#38bdf8", 
                                 selectcolor="#0f172a", activebackground="#1e293b", activeforeground="#38bdf8")
        chk_wet.pack(anchor=tk.W, pady=5)
        
        tk.Label(left_panel, text="⚠️ Note: Keep unchecked to enforce 30% dry limit", font=("Segoe UI", 9, "italic"), bg="#1e293b", fg="#94a3b8").pack(anchor=tk.W, pady=(0, 15))

        # Voltage Input
        tk.Label(left_panel, text="Simulated Supply Voltage (V)", font=("Segoe UI", 14, "bold"), bg="#1e293b", fg="#e2e8f0").pack(anchor=tk.W, pady=(10, 5))
        scale_volt = tk.Scale(left_panel, from_=9.0, to=16.0, resolution=0.1, orient=tk.HORIZONTAL, 
                              variable=self.voltage_val, bg="#1e293b", fg="#34d399", highlightthickness=0, length=250)
        scale_volt.pack(anchor=tk.W, pady=5)

        # Emergency Stop
        btn_stop = tk.Button(left_panel, text="EMERGENCY STOP", font=("Segoe UI", 16, "bold"), bg="#ef4444", fg="white",
                             activebackground="#dc2626", relief=tk.FLAT, command=self.send_stop, height=2)
        btn_stop.pack(fill=tk.X, pady=(40, 10))
        
        # Power telemetry bars
        bars_frame = tk.Frame(left_panel, bg="#1e293b")
        bars_frame.pack(fill=tk.X, pady=20)
        
        tk.Label(bars_frame, text="L Thruster", font=("Segoe UI", 10), bg="#1e293b", fg="#cbd5e1").pack(side=tk.LEFT, padx=10)
        tk.Label(bars_frame, text="R Thruster", font=("Segoe UI", 10), bg="#1e293b", fg="#cbd5e1").pack(side=tk.RIGHT, padx=10)
        
        self.canvas_bars = tk.Canvas(left_panel, width=250, height=30, bg="#0f172a", highlightthickness=0)
        self.canvas_bars.pack()
        
        # Center Panel (Joystick)
        center_panel = tk.Frame(main_frame, bg="#0f172a")
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20)
        
        tk.Label(center_panel, text="Thrust Vector Control", font=("Segoe UI", 14, "bold"), bg="#0f172a", fg="#e2e8f0").pack(pady=(0, 10))

        self.canvas_size = 300
        self.center = self.canvas_size / 2
        self.canvas = tk.Canvas(center_panel, width=self.canvas_size, height=self.canvas_size, bg="#1e293b", highlightthickness=0)
        self.canvas.pack(pady=20)
        
        # Draw joystick area
        self.canvas.create_oval(10, 10, self.canvas_size-10, self.canvas_size-10, outline="#334155", width=2)
        self.canvas.create_line(self.center, 0, self.center, self.canvas_size, fill="#334155", width=2)
        self.canvas.create_line(0, self.center, self.canvas_size, self.center, fill="#334155", width=2)
        
        # Joystick knob
        self.knob_r = 25
        self.knob = self.canvas.create_oval(self.center-self.knob_r, self.center-self.knob_r, 
                                            self.center+self.knob_r, self.center+self.knob_r, 
                                            fill="#3b82f6", outline="#60a5fa", width=2)

        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        self.lbl_telemetry = tk.Label(center_panel, text="L: 0% | R: 0%", font=("Consolas", 14), bg="#0f172a", fg="#94a3b8")
        self.lbl_telemetry.pack(pady=10)
        
        # Right Panel (Terminal Log)
        right_panel = tk.Frame(main_frame, bg="#0f172a")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(right_panel, text="Live Telemetry Log", font=("Segoe UI", 14, "bold"), bg="#0f172a", fg="#e2e8f0").pack(anchor=tk.W, pady=(0, 10))
        
        self.txt_log = tk.Text(right_panel, font=("Consolas", 9), bg="#020617", fg="#34d399", state=tk.DISABLED, wrap=tk.WORD)
        self.txt_log.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(self.txt_log, command=self.txt_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.config(yscrollcommand=scrollbar.set)
        
        self.log_message("System Initialized. Awaiting Connection...")

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.cb_ports['values'] = port_list
        if port_list:
            self.cb_ports.current(0)
        else:
            self.cb_ports.set("No COM Ports Found")

    def toggle_connection(self):
        if self.is_connected:
            # Disconnect
            self.is_connected = False
            if self.serial_port and self.serial_port.is_open:
                self.send_stop()
                self.serial_port.close()
            self.btn_connect.config(text="Connect", bg="#10b981")
            self.lbl_status.config(text="Disconnected", fg="#ef4444")
            self.log_message("Disconnected from serial port.")
        else:
            # Connect
            port = self.cb_ports.get()
            if not port or port == "No COM Ports Found":
                self.log_message("Error: Select a valid COM port.")
                return
            
            try:
                self.serial_port = serial.Serial(port, 115200, timeout=1)
                self.is_connected = True
                self.btn_connect.config(text="Disconnect", bg="#ef4444")
                self.lbl_status.config(text=f"Connected ({port})", fg="#10b981")
                self.log_message(f"Successfully connected to {port} at 115200 baud.")
                
                # Start reader thread
                self.read_thread = threading.Thread(target=self.serial_read_loop, daemon=True)
                self.read_thread.start()
                
            except Exception as e:
                self.log_message(f"Connection Failed: {e}")

    def serial_read_loop(self):
        while self.is_connected and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line:
                        self.log_message(f"RX: {line}")
            except Exception:
                pass
            time.sleep(0.01)

    def log_message(self, msg):
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def on_drag(self, event):
        x = max(0, min(event.x, self.canvas_size))
        y = max(0, min(event.y, self.canvas_size))
        self.canvas.coords(self.knob, x-self.knob_r, y-self.knob_r, x+self.knob_r, y+self.knob_r)
        
        # Normalize to -1.0 to 1.0 (Y is inverted for visual up=forward)
        self.joystick_x = (x - self.center) / self.center
        self.joystick_y = -(y - self.center) / self.center

    def on_release(self, event):
        # Snap back to center
        self.canvas.coords(self.knob, self.center-self.knob_r, self.center-self.knob_r, self.center+self.knob_r, self.center+self.knob_r)
        self.joystick_x = 0
        self.joystick_y = 0
        self.send_stop()
        self.update_bars(0, 0, 'F', 'F')

    def send_stop(self):
        if self.is_connected and self.serial_port and self.serial_port.is_open:
            self.serial_port.write(b"STOP\n")
            self.log_message("TX: STOP")
        
        self.canvas.coords(self.knob, self.center-self.knob_r, self.center-self.knob_r, self.center+self.knob_r, self.center+self.knob_r)
        self.joystick_x = 0
        self.joystick_y = 0
        self.lbl_telemetry.config(text="L: 0% (STOP) | R: 0% (STOP)")
        self.update_bars(0, 0, 'F', 'F')

    def update_bars(self, l_pow, r_pow, l_dir, r_dir):
        self.canvas_bars.delete("all")
        
        # Max width 100 per bar
        l_color = "#10b981" if l_dir == 'F' else "#3b82f6"
        r_color = "#10b981" if r_dir == 'F' else "#3b82f6"
        if l_pow == 0: l_color = "#475569"
        if r_pow == 0: r_color = "#475569"
        
        # Draw Left
        self.canvas_bars.create_rectangle(10, 5, 110, 25, fill="#1e293b", outline="#334155")
        self.canvas_bars.create_rectangle(10, 5, 10 + l_pow, 25, fill=l_color, outline="")
        
        # Draw Right
        self.canvas_bars.create_rectangle(140, 5, 240, 25, fill="#1e293b", outline="#334155")
        self.canvas_bars.create_rectangle(140, 5, 140 + r_pow, 25, fill=r_color, outline="")

    def send_loop(self):
        forward = self.joystick_y
        turn = self.joystick_x
        
        left_mix = forward + turn
        right_mix = forward - turn
        
        # Normalize mix
        max_mix = max(abs(left_mix), abs(right_mix), 1.0)
        left_mix /= max_mix
        right_mix /= max_mix
        
        left_power = abs(left_mix * 100)
        right_power = abs(right_mix * 100)
        
        # Apply Dry/Wet Limit
        current_max = self.max_power if self.is_wet.get() else self.dry_power_limit
        left_power = min(left_power, current_max)
        right_power = min(right_power, current_max)
        
        left_dir = 'F' if left_mix >= 0 else 'R'
        right_dir = 'F' if right_mix >= 0 else 'R'

        if self.joystick_x != 0 or self.joystick_y != 0:
            cmd_l = f"M,L,{left_dir},{int(left_power)},500\n"
            cmd_r = f"M,R,{right_dir},{int(right_power)},500\n"
            
            if self.is_connected and self.serial_port and self.serial_port.is_open:
                self.serial_port.write(cmd_l.encode())
                time.sleep(0.01) # Small delay for Arduino parsing
                self.serial_port.write(cmd_r.encode())
                
                # Optional: log outgoing commands (can get spammy, so maybe comment out if too much)
                # self.log_message(f"TX: {cmd_l.strip()} | {cmd_r.strip()}")
            
            self.lbl_telemetry.config(text=f"L: {int(left_power)}% {left_dir} | R: {int(right_power)}% {right_dir} | Volt: {self.voltage_val.get():.1f}V")
            self.update_bars(int(left_power), int(right_power), left_dir, right_dir)
            
        self.after(200, self.send_loop)

if __name__ == "__main__":
    app = RomerCalypsoTester()
    app.mainloop()
