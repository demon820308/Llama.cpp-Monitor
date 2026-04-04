import ctypes
from ctypes import wintypes
import json
import os
import socket
import subprocess
import sys
import threading

import customtkinter as ctk
import psutil
import pystray
from PIL import Image

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

EXE_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
RESOURCE_DIR = getattr(sys, "_MEIPASS", EXE_DIR)
CONFIG_FILE = os.path.join(EXE_DIR, "Llama Monitor-config.json")
WINDOW_WIDTH = 620
WINDOW_HEIGHT = 780

try:
    import pynvml
    pynvml.nvmlInit()
    HAS_NVML = True
except Exception:
    HAS_NVML = False


class MimoLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Llama Monitor")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.process = None
        self.is_running = False
        self.server_pid = None
        self.gpu_handle = None
        self.tray_icon = None
        self.is_minimized_to_tray = False

        self.load_config()

        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.pack(fill="both", expand=True, padx=12, pady=20)

        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Llama Monitor",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.title_label.pack(pady=(10, 15))

        self.form_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.form_frame.pack(fill="x", pady=(2, 8))

        # standard column widths for perfect alignment
        label_w = 95
        check_w = 34

        self.server_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.server_frame.pack(fill="x", pady=4)
        self.server_frame.grid_columnconfigure(0, minsize=label_w)
        self.server_frame.grid_columnconfigure(1, weight=1)
        self.server_frame.grid_columnconfigure(2, minsize=check_w)
        self.server_frame.grid_columnconfigure(3, minsize=label_w)
        self.server_frame.grid_columnconfigure(4, weight=1)
        self.server_frame.grid_columnconfigure(5, minsize=check_w)

        ctk.CTkLabel(self.server_frame, text="Server Path:", anchor="w").grid(row=0, column=0, sticky="w", padx=(10, 6))
        self.server_path = ctk.CTkEntry(self.server_frame, placeholder_text="llama-server.exe")
        self.server_path.insert(0, self.config.get("server_path", "llama-server.exe"))
        self.server_path.grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(self.server_frame, text="Working Dir:", anchor="w").grid(row=0, column=3, sticky="w", padx=(10, 6))
        self.workdir = ctk.CTkEntry(self.server_frame, placeholder_text="Current directory")
        self.workdir.insert(0, EXE_DIR)
        self.workdir.grid(row=0, column=4, sticky="ew")

        self.model_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.model_frame.pack(fill="x", pady=4)
        self.model_frame.grid_columnconfigure(0, minsize=label_w)
        self.model_frame.grid_columnconfigure(1, weight=1)
        self.model_frame.grid_columnconfigure(2, minsize=check_w)

        ctk.CTkLabel(self.model_frame, text="Model File:", anchor="w").grid(row=0, column=0, sticky="w", padx=(10, 6))
        self.model_options = self.get_model_files()
        self.model_var = ctk.StringVar(value=self.config.get("model_file", self.model_options[0] if self.model_options else ""))
        self.model_dropdown = ctk.CTkOptionMenu(
            self.model_frame,
            variable=self.model_var,
            values=self.model_options,
        )
        self.model_dropdown.grid(row=0, column=1, sticky="ew")

        self.mmproj_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.mmproj_frame.pack(fill="x", pady=4)
        self.mmproj_frame.grid_columnconfigure(0, minsize=label_w)
        self.mmproj_frame.grid_columnconfigure(1, weight=1)
        self.mmproj_frame.grid_columnconfigure(2, minsize=check_w)

        ctk.CTkLabel(self.mmproj_frame, text="MMProj File:", anchor="w").grid(row=0, column=0, sticky="w", padx=(10, 6))
        self.mmproj_options = self.get_mmproj_files()
        self.mmproj_var = ctk.StringVar(value=self.config.get("mmproj_file", self.mmproj_options[0] if self.mmproj_options else ""))
        self.use_mmproj_var = ctk.BooleanVar(value=self.config.get("use_mmproj", True))
        self.mmproj_dropdown = ctk.CTkOptionMenu(
            self.mmproj_frame,
            variable=self.mmproj_var,
            values=self.mmproj_options,
        )
        self.mmproj_dropdown.grid(row=0, column=1, sticky="ew")
        self.mmproj_checkbox = ctk.CTkCheckBox(self.mmproj_frame, text="", variable=self.use_mmproj_var, width=24)
        self.mmproj_checkbox.grid(row=0, column=2, sticky="e", padx=(0, 10))

        self.ctx_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.ctx_frame.pack(fill="x", pady=4)
        self.ctx_frame.grid_columnconfigure(0, minsize=label_w)
        self.ctx_frame.grid_columnconfigure(1, weight=1)
        self.ctx_frame.grid_columnconfigure(2, minsize=check_w)
        self.ctx_frame.grid_columnconfigure(3, minsize=label_w)
        self.ctx_frame.grid_columnconfigure(4, weight=1)
        self.ctx_frame.grid_columnconfigure(5, minsize=check_w)

        ctk.CTkLabel(self.ctx_frame, text="Context Size:", anchor="w").grid(row=0, column=0, sticky="w", padx=(10, 6))
        self.ctx_size = ctk.CTkEntry(self.ctx_frame, placeholder_text="8192")
        self.ctx_size.insert(0, self.config.get("ctx_size", "8192"))
        self.ctx_size.grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(self.ctx_frame, text="GPU Layers:", anchor="w").grid(row=0, column=3, sticky="w", padx=(10, 6))
        self.gpu_layers = ctk.CTkEntry(self.ctx_frame, placeholder_text="60")
        self.gpu_layers.insert(0, self.config.get("gpu_layers", "60"))
        self.gpu_layers.grid(row=0, column=4, sticky="ew")

        self.net_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.net_frame.pack(fill="x", pady=4)
        self.net_frame.grid_columnconfigure(0, minsize=label_w)
        self.net_frame.grid_columnconfigure(1, weight=1)
        self.net_frame.grid_columnconfigure(2, minsize=check_w)
        self.net_frame.grid_columnconfigure(3, minsize=label_w)
        self.net_frame.grid_columnconfigure(4, weight=1)
        self.net_frame.grid_columnconfigure(5, minsize=check_w)

        ctk.CTkLabel(self.net_frame, text="Host:", anchor="w").grid(row=0, column=0, sticky="w", padx=(10, 6))
        self.host = ctk.CTkEntry(self.net_frame, placeholder_text="0.0.0.0")
        self.host.insert(0, self.config.get("host", "0.0.0.0"))
        self.host.grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(self.net_frame, text="Port:", anchor="w").grid(row=0, column=3, sticky="w", padx=(10, 6))
        self.port = ctk.CTkEntry(self.net_frame, placeholder_text="8080")
        self.port.insert(0, self.config.get("port", "8080"))
        self.port.grid(row=0, column=4, sticky="ew")

        self.perf_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.perf_frame.pack(fill="x", pady=4)
        self.perf_frame.grid_columnconfigure(0, minsize=label_w)
        self.perf_frame.grid_columnconfigure(1, weight=1)
        self.perf_frame.grid_columnconfigure(2, minsize=check_w)
        self.perf_frame.grid_columnconfigure(3, minsize=label_w)
        self.perf_frame.grid_columnconfigure(4, weight=1)
        self.perf_frame.grid_columnconfigure(5, minsize=check_w)

        ctk.CTkLabel(self.perf_frame, text="Threads:", anchor="w").grid(row=0, column=0, sticky="w", padx=(10, 6))
        self.threads = ctk.CTkEntry(self.perf_frame, placeholder_text="8")
        self.threads.insert(0, self.config.get("threads", "8"))
        self.threads.grid(row=0, column=1, sticky="ew")
        self.use_threads_var = ctk.BooleanVar(value=self.config.get("use_threads", True))
        self.threads_checkbox = ctk.CTkCheckBox(self.perf_frame, text="", variable=self.use_threads_var, width=24)
        self.threads_checkbox.grid(row=0, column=2, sticky="e", padx=(4, 10))

        ctk.CTkLabel(self.perf_frame, text="N Predict:", anchor="w").grid(row=0, column=3, sticky="w", padx=(10, 6))
        self.n_predict = ctk.CTkEntry(self.perf_frame, placeholder_text="-1")
        self.n_predict.insert(0, self.config.get("n_predict", "-1"))
        self.n_predict.grid(row=0, column=4, sticky="ew")
        self.use_n_predict_var = ctk.BooleanVar(value=self.config.get("use_n_predict", True))
        self.n_predict_checkbox = ctk.CTkCheckBox(self.perf_frame, text="", variable=self.use_n_predict_var, width=24)
        self.n_predict_checkbox.grid(row=0, column=5, sticky="e", padx=(4, 10))

        self.sample_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.sample_frame.pack(fill="x", pady=4)
        self.sample_frame.grid_columnconfigure(0, minsize=label_w)
        self.sample_frame.grid_columnconfigure(1, weight=1)
        self.sample_frame.grid_columnconfigure(2, minsize=check_w)
        self.sample_frame.grid_columnconfigure(3, minsize=55)
        self.sample_frame.grid_columnconfigure(4, weight=1)
        self.sample_frame.grid_columnconfigure(5, minsize=check_w)
        self.sample_frame.grid_columnconfigure(6, minsize=55)
        self.sample_frame.grid_columnconfigure(7, weight=1)
        self.sample_frame.grid_columnconfigure(8, minsize=check_w)

        ctk.CTkLabel(self.sample_frame, text="Temp:", anchor="w").grid(row=0, column=0, sticky="w", padx=(10, 6))
        self.temp = ctk.CTkEntry(self.sample_frame, placeholder_text="0.8")
        self.temp.insert(0, self.config.get("temp", "0.8"))
        self.temp.grid(row=0, column=1, sticky="ew")
        self.use_temp_var = ctk.BooleanVar(value=self.config.get("use_temp", True))
        self.temp_checkbox = ctk.CTkCheckBox(self.sample_frame, text="", variable=self.use_temp_var, width=24)
        self.temp_checkbox.grid(row=0, column=2, sticky="e", padx=(4, 0))

        ctk.CTkLabel(self.sample_frame, text="Top P:", anchor="w").grid(row=0, column=3, sticky="w", padx=(6, 6))
        self.top_p = ctk.CTkEntry(self.sample_frame, placeholder_text="0.95")
        self.top_p.insert(0, self.config.get("top_p", "0.95"))
        self.top_p.grid(row=0, column=4, sticky="ew")
        self.use_top_p_var = ctk.BooleanVar(value=self.config.get("use_top_p", True))
        self.top_p_checkbox = ctk.CTkCheckBox(self.sample_frame, text="", variable=self.use_top_p_var, width=24)
        self.top_p_checkbox.grid(row=0, column=5, sticky="e", padx=(4, 0))

        ctk.CTkLabel(self.sample_frame, text="Batch:", anchor="w").grid(row=0, column=6, sticky="w", padx=(6, 6))
        self.batch_size = ctk.CTkEntry(self.sample_frame, placeholder_text="2048")
        self.batch_size.insert(0, self.config.get("batch_size", "2048"))
        self.batch_size.grid(row=0, column=7, sticky="ew")
        self.use_batch_size_var = ctk.BooleanVar(value=self.config.get("use_batch_size", True))
        self.batch_checkbox = ctk.CTkCheckBox(self.sample_frame, text="", variable=self.use_batch_size_var, width=24)
        self.batch_checkbox.grid(row=0, column=8, sticky="e", padx=(4, 10))



        self.btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.btn_frame.pack(fill="x", pady=10)
        self.btn_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.start_btn = ctk.CTkButton(
            self.btn_frame,
            text="Start Server",
            command=self.start_server,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.start_btn.grid(row=0, column=0, padx=(10, 5), sticky="ew")

        self.stop_btn = ctk.CTkButton(
            self.btn_frame,
            text="Stop Server",
            command=self.stop_server,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
        )
        self.stop_btn.grid(row=0, column=1, padx=(5, 5), sticky="ew")

        self.open_web_btn = ctk.CTkButton(
            self.btn_frame,
            text="Open Web",
            command=self.open_web,
            height=36,
            corner_radius=8,
        )
        self.open_web_btn.grid(row=0, column=2, padx=(5, 5), sticky="ew")

        self.save_btn = ctk.CTkButton(
            self.btn_frame,
            text="Save",
            command=self.save_config,
            height=36,
            corner_radius=8,
        )
        self.save_btn.grid(row=0, column=3, padx=(5, 10), sticky="ew")

        self.monitor_frame = ctk.CTkFrame(self.main_frame, corner_radius=8)
        self.monitor_frame.pack(fill="x", pady=8)

        ctk.CTkLabel(self.monitor_frame, text="System Monitor", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))

        self.cpu_frame = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        self.cpu_frame.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(self.cpu_frame, text="CPU:", width=80, anchor="w").pack(side="left")
        self.cpu_progress = ctk.CTkProgressBar(self.cpu_frame, width=200, height=12)
        self.cpu_progress.pack(side="left", padx=5)
        self.cpu_progress.set(0)
        self.cpu_label = ctk.CTkLabel(self.cpu_frame, text="0%", width=60, anchor="e")
        self.cpu_label.pack(side="left")

        self.mem_frame = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        self.mem_frame.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(self.mem_frame, text="Memory:", width=80, anchor="w").pack(side="left")
        self.mem_progress = ctk.CTkProgressBar(self.mem_frame, width=200, height=12)
        self.mem_progress.pack(side="left", padx=5)
        self.mem_progress.set(0)
        self.mem_label = ctk.CTkLabel(self.mem_frame, text="0% / 0GB", width=110, anchor="e")
        self.mem_label.pack(side="left")

        self.gpu_frame = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        self.gpu_frame.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(self.gpu_frame, text="GPU:", width=80, anchor="w").pack(side="left")
        self.gpu_progress = ctk.CTkProgressBar(self.gpu_frame, width=200, height=12)
        self.gpu_progress.pack(side="left", padx=5)
        self.gpu_progress.set(0)
        self.gpu_label = ctk.CTkLabel(self.gpu_frame, text="N/A", width=110, anchor="e")
        self.gpu_label.pack(side="left")

        self.status_frame = ctk.CTkFrame(self.main_frame, corner_radius=8)
        self.status_frame.pack(fill="x", pady=8)

        ctk.CTkLabel(self.status_frame, text="Status:", anchor="w").pack(side="left", padx=10)
        self.status_label = ctk.CTkLabel(self.status_frame, text="Ready", anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True, padx=5)
        self.port_label = ctk.CTkLabel(self.status_frame, text="Port: --", anchor="e")
        self.port_label.pack(side="right", padx=10)

        self.log_frame = ctk.CTkFrame(self.main_frame, corner_radius=8)
        self.log_frame.pack(fill="both", expand=True, pady=8)

        ctk.CTkLabel(self.log_frame, text="Log:", anchor="w").pack(side="top", anchor="w", padx=10, pady=(5, 0))
        self.log_text = ctk.CTkTextbox(self.log_frame, height=140, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)

        if HAS_NVML:
            try:
                self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            except Exception:
                self.gpu_handle = None

        self.start_monitoring()
        self.setup_tray()
        self.bind("<Unmap>", self.on_unmap)

    def on_unmap(self, event=None):
        if self.state() != "iconic":
            return
        self.withdraw()
        self.is_minimized_to_tray = True
        if self.tray_icon is None:
            self.setup_tray()

    def center_window(self):
        self.update_idletasks()
        width = WINDOW_WIDTH
        height = WINDOW_HEIGHT

        # Center against the Windows work area so the taskbar does not skew the position.
        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            work_width = rect.right - rect.left
            work_height = rect.bottom - rect.top
            x = rect.left + max((work_width - width) // 2, 0)
            y = rect.top + max((work_height - height) // 2, 0)
        else:
            x = max((self.winfo_screenwidth() - width) // 2, 0)
            y = max((self.winfo_screenheight() - height) // 2, 0)

        self.geometry(f"{width}x{height}+{x}+{y}")

    def get_asset_path(self, filename):
        for base_dir in (RESOURCE_DIR, EXE_DIR):
            candidate = os.path.join(base_dir, filename)
            if os.path.exists(candidate):
                return candidate
        return None

    def setup_tray(self):
        icon_image = None

        ico_path = self.get_asset_path("logo.ico")
        if ico_path:
            try:
                ico = Image.open(ico_path)
                if ico.mode != "RGBA":
                    ico = ico.convert("RGBA")
                icon_image = ico.resize((64, 64), Image.LANCZOS)
            except Exception as exc:
                print(f"Failed to load ico: {exc}")
                icon_image = None

        if icon_image is None:
            png_path = self.get_asset_path("logo_tray.png")
            if png_path:
                try:
                    icon_image = Image.open(png_path)
                    if icon_image.mode != "RGBA":
                        icon_image = icon_image.convert("RGBA")
                    icon_image = icon_image.resize((64, 64), Image.LANCZOS)
                except Exception as exc:
                    print(f"Failed to load png: {exc}")
                    icon_image = None

        if icon_image is None:
            icon_image = Image.new("RGBA", (64, 64), (70, 130, 180, 255))

        def on_tray_click(icon, event):
            if event == "left":
                self.after(0, self.show_from_tray)

        menu = pystray.Menu(
            pystray.MenuItem("Open Monitor", self.show_window, default=True),
            pystray.MenuItem("Quit Monitor", self.quit_app),
        )

        self.tray_icon = pystray.Icon(
            "LlamaMonitor",
            icon_image,
            "Llama Monitor",
            menu,
        )
        self.tray_icon.on_click = on_tray_click

        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon=None, item=None):
        self.after(0, self.deiconify)
        self.is_minimized_to_tray = False
        self.focus_force()
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def show_from_tray(self):
        self.deiconify()
        self.is_minimized_to_tray = False
        self.focus_force()
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def quit_app(self, icon=None, item=None):
        self.is_minimized_to_tray = False
        if self.is_running:
            self.stop_server()
        if self.tray_icon:
            self.tray_icon.stop()
        if HAS_NVML:
            pynvml.nvmlShutdown()
        self.destroy()

    def get_model_files(self):
        files = []
        model_dir = os.path.join(EXE_DIR, "models")
        if os.path.exists(model_dir):
            for filename in os.listdir(model_dir):
                if filename.endswith(".gguf") and "mmproj" not in filename.lower():
                    files.append(os.path.join("models", filename))
        for filename in os.listdir(EXE_DIR):
            if filename.endswith(".gguf") and "mmproj" not in filename.lower():
                files.append(filename)
        return sorted(set(files)) if files else ["璇锋妸model鏀惧湪models鐨勭洰褰曚笅"]

    def get_mmproj_files(self):
        files = []
        model_dir = os.path.join(EXE_DIR, "models")
        if os.path.exists(model_dir):
            for filename in os.listdir(model_dir):
                if filename.endswith(".gguf") and "mmproj" in filename.lower():
                    files.append(os.path.join("models", filename))
        for filename in os.listdir(EXE_DIR):
            if filename.endswith(".gguf") and "mmproj" in filename.lower():
                files.append(filename)
        return sorted(set(files)) if files else ["璇锋妸model鏀惧湪models鐨勭洰褰曚笅"]

    def start_monitoring(self):
        def monitor():
            while True:
                cpu = psutil.cpu_percent(interval=1)
                self.after(0, self.cpu_progress.set, cpu / 100)
                self.after(0, self.cpu_label.configure, text=f"{cpu:.1f}%")

                mem = psutil.virtual_memory()
                mem_used = mem.used / (1024 ** 3)
                mem_total = mem.total / (1024 ** 3)
                self.after(0, self.mem_progress.set, mem.percent / 100)
                self.after(0, self.mem_label.configure, text=f"{mem_used:.1f}GB / {mem_total:.1f}GB")

                if HAS_NVML and self.gpu_handle:
                    try:
                        gpu_info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
                        gpu_util = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
                        gpu_used = gpu_info.used / (1024 ** 3)
                        gpu_total = gpu_info.total / (1024 ** 3)
                        self.after(0, self.gpu_progress.set, gpu_util.gpu / 100)
                        self.after(0, self.gpu_label.configure, text=f"{gpu_used:.1f}GB / {gpu_total:.1f}GB")
                    except Exception:
                        self.after(0, self.gpu_label.configure, text="Error")
                else:
                    self.after(0, self.gpu_label.configure, text="N/A (no NVIDIA)")

                port = self.port.get()
                if self.is_port_open(port):
                    self.after(0, self.port_label.configure, text=f"Port {port}: Listening", text_color="green")
                    self.after(0, self.status_label.configure, text="Running", text_color="green")
                else:
                    self.after(0, self.port_label.configure, text=f"Port {port}: Closed", text_color="orange")

        threading.Thread(target=monitor, daemon=True).start()

    def is_port_open(self, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", int(port)))
            sock.close()
            return result == 0
        except Exception:
            return False

    def log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def load_config(self):
        self.config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                    self.config = json.load(file)
            except Exception:
                self.config = {}

    def save_config(self):
        self.config = {
            "server_path": self.server_path.get(),
            "model_file": self.model_var.get(),
            "mmproj_file": self.mmproj_var.get(),
            "use_mmproj": self.use_mmproj_var.get(),
            "ctx_size": self.ctx_size.get(),
            "gpu_layers": self.gpu_layers.get(),
            "host": self.host.get(),
            "port": self.port.get(),
            "threads": self.threads.get(),
            "use_threads": self.use_threads_var.get(),
            "n_predict": self.n_predict.get(),
            "use_n_predict": self.use_n_predict_var.get(),
            "batch_size": self.batch_size.get(),
            "use_batch_size": self.use_batch_size_var.get(),
            "temp": self.temp.get(),
            "use_temp": self.use_temp_var.get(),
            "top_p": self.top_p.get(),
            "use_top_p": self.use_top_p_var.get(),
            "workdir": self.workdir.get(),
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(self.config, file, indent=2, ensure_ascii=False)
        self.log("[INFO] Settings saved")

    def open_web(self):
        port = self.port.get()
        subprocess.run(["start", f"http://localhost:{port}"], shell=True)

    def start_server(self):
        if self.is_running:
            return

        if not self.server_path.get():
            self.log("[ERROR] Server path is required")
            return

        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text="Running...", text_color="green")

        cmd = [
            self.server_path.get(),
            "-m",
            self.model_var.get(),
            "-c",
            self.ctx_size.get(),
            "-ngl",
            self.gpu_layers.get(),
            "--host",
            self.host.get(),
            "--port",
            self.port.get(),
        ]
        if self.use_mmproj_var.get() and self.mmproj_var.get() != "璇锋妸model鏀惧湪models鐨勭洰褰曚笅":
            cmd[3:3] = ["--mmproj", self.mmproj_var.get()]
        if self.use_threads_var.get() and self.threads.get().strip():
            cmd.extend(["-t", self.threads.get().strip()])
        if self.use_n_predict_var.get() and self.n_predict.get().strip():
            cmd.extend(["-n", self.n_predict.get().strip()])
        if self.use_batch_size_var.get() and self.batch_size.get().strip():
            cmd.extend(["-b", self.batch_size.get().strip()])
        if self.use_temp_var.get() and self.temp.get().strip():
            cmd.extend(["--temp", self.temp.get().strip()])
        if self.use_top_p_var.get() and self.top_p.get().strip():
            cmd.extend(["--top-p", self.top_p.get().strip()])

        self.log("[INFO] Starting server...")
        self.log(f"[CMD] {' '.join(cmd)}")

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            self.process = subprocess.Popen(
                cmd,
                cwd=self.workdir.get(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                startupinfo=startupinfo,
            )
            self.server_pid = self.process.pid

            def read_output():
                for line in self.process.stdout:
                    self.after(0, self.log, line.rstrip())

            threading.Thread(target=read_output, daemon=True).start()

        except Exception as exc:
            self.log(f"[ERROR] Failed to start: {exc}")
            self.is_running = False
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.status_label.configure(text="Error", text_color="red")

    def stop_server(self):
        if not self.is_running:
            return

        self.log("[INFO] Stopping server...")
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="Stopped", text_color="orange")

    def on_closing(self):
        if self.is_running:
            self.stop_server()
        if self.tray_icon:
            self.tray_icon.stop()
        if HAS_NVML:
            pynvml.nvmlShutdown()
        self.destroy()


if __name__ == "__main__":
    app = MimoLauncher()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()























