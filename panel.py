import ctypes
from ctypes import wintypes
import csv
from difflib import SequenceMatcher
import json
import math
import os
import queue
import random
import re
import subprocess
import tempfile
import threading
import time
import tkinter as tk
import unicodedata
import xml.etree.ElementTree as ET
import sys
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
from urllib.parse import quote, urlparse
import base64

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
INSTANCE_MUTEX = None
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR)).resolve()
else:
    BASE_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = BASE_DIR

def acquire_single_instance():
    global INSTANCE_MUTEX
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.CreateMutexW(None, False, "Local\\PanelCelularesV2_MultiDispositivo")
        if not handle:
            return False
        if ctypes.get_last_error() == 183:
            kernel32.CloseHandle(handle)
            return False
        INSTANCE_MUTEX = (kernel32, handle)
        return True
    except Exception:
        return True

def release_single_instance():
    global INSTANCE_MUTEX
    if INSTANCE_MUTEX:
        try:
            kernel32, handle = INSTANCE_MUTEX
            kernel32.CloseHandle(handle)
        except Exception:
            pass
        INSTANCE_MUTEX = None

def set_windows_app_id():
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "AdministracionDeMoviles.Version1.88"
        )
    except Exception:
        pass

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


class ProfessionalPhoneController:
    SEQUENCE_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".heif", ".avif"}
    SEQUENCE_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".3gp", ".m4v", ".mpeg", ".mpg", ".wmv"}
    SEQUENCE_ACTIONS = {
        "Dar clic en la captura": "tap",
        "Presionar y deslizar": "swipe",
        "Identificar texto y pulsar": "tap_text",
        "Identificar Publicar y pulsar": "tap_publish",
        "Escribir texto": "text",
        "Ocultar teclado": "hide_keyboard",
        "Subir imagen/video al teléfono": "upload_media",
        "Cargar lista por renglones": "load_list",
        "Siguiente elemento de lista": "next_list",
        "Abrir liga / link": "open_url",
        "Calentamiento orgánico": "warmup",
        "Tiempo de espera": "wait",
        "Atrás": "back",
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Administración de móviles (移动设备管理)")
        self.root.geometry("1320x900")
        self.root.minsize(1100, 720)
        self.root.configure(bg="#eef2f7")
        self.configure_application_icon()

        self.adb = self.find_adb()
        self.scrcpy = self.find_scrcpy()
        self.ui_queue = queue.Queue()
        self.search_stop_event = threading.Event()
        self.human_stop_event = threading.Event()
        self.report_stop_event = threading.Event()
        self.advanced_stop_event = threading.Event()
        self.maintenance_stop_event = threading.Event()
        self.interaction_stop_event = threading.Event()
        self.sequence_stop_event = threading.Event()
        self.app_closing = threading.Event()
        
        self.search_running = False
        self.human_running = False
        self.report_running = False
        self.advanced_running = False
        self.maintenance_running = False
        self.interaction_running = False
        self.sequence_running = False
        self.interaction_devices = set()
        self.combined_next_action = None
        self.screen_size_cache = {}
        
        self.device_config_file = BASE_DIR / "dispositivos.json"
        self.search_record_dir = BASE_DIR / "registros_busqueda"
        self.sequence_dir = BASE_DIR / "secuencias"
        self.templates_dir = RESOURCE_DIR / "templates"
        self.templates_dir.mkdir(exist_ok=True)

        self.device_aliases = self.load_device_aliases()
        self.device_details = {}
        self.device_tasks = {}
        self.device_tasks_lock = threading.Lock()
        self.search_record_lock = threading.Lock()
        self.busy_devices = set()
        self.uiautomator_lock = threading.Lock()
        self.scrcpy_processes = {}
        self.device_log_windows = {}
        self.device_log_texts = {}
        self.device_log_status_vars = {}
        self.search_devices = []
        self.pending_search_match = None
        self.sequence_steps = []
        self.sequence_capture_size = None
        self.sequence_display_geometry = None
        self.sequence_photo = None
        self.sequence_record_mode = "tap"
        self.sequence_swipe_start = None
        self.ocr_warning_shown = False
        self.first_device_scan = True

        self.root.after(100, self._drain_ui_queue)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background="#f7f9fc")
        style.configure("TLabel", background="#f7f9fc", foreground="#25324a", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 9, "bold"), padding=(10, 7), relief="flat")
        style.configure("TEntry", padding=5)
        style.configure("TCombobox", padding=4)
        style.configure("TCheckbutton", background="#f7f9fc", foreground="#25324a", font=("Segoe UI", 9))
        style.configure("TLabelframe", background="#f7f9fc", bordercolor="#d8e0ec", relief="solid")
        style.configure("TLabelframe.Label", background="#f7f9fc", foreground="#1d2b44", font=("Segoe UI", 9, "bold"))
        style.configure("Treeview", background="white", fieldbackground="white", foreground="#25324a", rowheight=28, borderwidth=0)
        style.configure("Treeview.Heading", background="#e8edf5", foreground="#25324a", font=("Segoe UI", 9, "bold"), padding=7)
        style.map("Treeview", background=[("selected", "#dceaff")], foreground=[("selected", "#123f78")])
        style.configure("Primary.TButton", background="#1877f2", foreground="white")
        style.configure("Success.TButton", background="#42b72a", foreground="white")
        style.configure("Warning.TButton", background="#f0ad4e", foreground="white")
        style.configure("Danger.TButton", background="#d64545", foreground="white")
        style.layout("Sidebar.TNotebook", [("TNotebook.client", {"sticky": "nswe"})])
        style.layout("Sidebar.TNotebook.Tab", [])

        self.devices = []

        self.create_application_header()
        self.create_application_footer()
        self.create_console_widget()

        self.workspace = tk.Frame(self.root, bg="#eef2f7")
        self.workspace.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.sidebar = tk.Frame(self.workspace, bg="#17233a", width=228)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.content_panel = tk.Frame(self.workspace, bg="#f7f9fc", highlightthickness=1, highlightbackground="#d8e0ec")
        self.content_panel.pack(side="left", fill="both", expand=True)

        self.notebook = ttk.Notebook(self.content_panel, style="Sidebar.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_general = ttk.Frame(self.notebook)
        self.tab_interaction = ttk.Frame(self.notebook)
        self.tab_search = ttk.Frame(self.notebook)
        self.tab_sequence = ttk.Frame(self.notebook)
        self.tab_vision = ttk.Frame(self.notebook)
        self.tab_human = ttk.Frame(self.notebook)
        self.tab_report = ttk.Frame(self.notebook)
        self.tab_advanced = ttk.Frame(self.notebook)
        self.tab_maintenance = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_general, text="Dispositivos")
        self.notebook.add(self.tab_interaction, text="Interacciones")
        self.notebook.add(self.tab_search, text="Búsqueda")
        self.notebook.add(self.tab_sequence, text="Secuencias")
        self.notebook.add(self.tab_vision, text="Reacciones")
        self.notebook.add(self.tab_human, text="Modo humano")
        self.notebook.add(self.tab_report, text="Reportes")
        self.notebook.add(self.tab_advanced, text="Automatización avanzada")
        self.notebook.add(self.tab_maintenance, text="Mantenimiento")

        self.navigation_pages = [
            ("OPERACIÓN", [
                ("Dispositivos", self.tab_general),
                ("Interacciones", self.tab_interaction),
                ("Búsqueda", self.tab_search),
                ("Secuencias", self.tab_sequence),
            ]),
            ("AUTOMATIZACIÓN", [
                ("Reacciones", self.tab_vision),
                ("Modo humano", self.tab_human),
                ("Reportes", self.tab_report),
            ]),
            ("HERRAMIENTAS", [
                ("Automatización avanzada", self.tab_advanced),
                ("Mantenimiento", self.tab_maintenance),
            ]),
        ]
        self.create_sidebar_navigation()

        self.create_general_widgets()
        self.create_interaction_widgets()
        self.create_search_widgets()
        self.create_sequence_widgets()
        self.create_vision_widgets()
        self.create_human_widgets()
        self.create_report_widgets()
        self.create_advanced_widgets()
        self.create_maintenance_widgets()
        self.select_navigation_page(self.tab_general, "Dispositivos")

        self.refresh_devices_async()
        threading.Thread(target=self.auto_scan_worker, daemon=True).start()

    def configure_application_icon(self):
        icon_png = RESOURCE_DIR / "assets" / "app_icon.png"
        icon_ico = RESOURCE_DIR / "assets" / "app_icon.ico"
        try:
            if icon_png.exists():
                self.app_icon = tk.PhotoImage(file=str(icon_png))
                self.root.iconphoto(True, self.app_icon)
            if os.name == "nt" and icon_ico.exists():
                self.root.iconbitmap(default=str(icon_ico))
        except tk.TclError:
            self.app_icon = None

    def create_application_header(self):
        header = tk.Frame(self.root, bg="#0f5fb8", height=78)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_box = tk.Frame(header, bg="#0f5fb8")
        title_box.pack(side="left", fill="y", padx=20)
        tk.Label(title_box, text="Administración de móviles (移动设备管理)", bg="#0f5fb8", fg="white",
                 font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w", pady=(11, 0))
        self.current_page_var = tk.StringVar(value="Dispositivos")
        tk.Label(title_box, textvariable=self.current_page_var, bg="#0f5fb8", fg="#cfe5ff",
                 font=("Segoe UI", 9)).pack(anchor="w")

        self.header_device_var = tk.StringVar(value="0 conectados  ·  0 seleccionados")
        status = tk.Frame(header, bg="#0b4f9b", padx=14, pady=8)
        status.pack(side="right", padx=20, pady=10)
        tk.Label(status, text="ESTADO DE DISPOSITIVOS", bg="#0b4f9b", fg="#a9cff9",
                 font=("Segoe UI", 8, "bold")).pack(anchor="e")
        tk.Label(status, textvariable=self.header_device_var, bg="#0b4f9b", fg="white",
                 font=("Segoe UI", 10, "bold")).pack(anchor="e")

    def create_application_footer(self):
        footer = tk.Frame(self.root, bg="#e3e9f2", height=38)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        tk.Label(
            footer,
            text="版本 1.88",
            bg="#e3e9f2",
            fg="#52647d",
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(side="right", padx=16, pady=7)

    def create_sidebar_navigation(self):
        self.navigation_buttons = {}
        tk.Label(self.sidebar, text="NAVEGACIÓN", bg="#17233a", fg="#91a4c3",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(18, 8))
        for group, pages in self.navigation_pages:
            tk.Label(self.sidebar, text=group, bg="#17233a", fg="#7186a9",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(12, 4))
            for label, tab in pages:
                button = tk.Button(
                    self.sidebar,
                    text=label,
                    command=lambda current_tab=tab, current_label=label: self.select_navigation_page(current_tab, current_label),
                    bg="#17233a",
                    fg="#dce6f5",
                    activebackground="#23426d",
                    activeforeground="white",
                    relief="flat",
                    bd=0,
                    anchor="w",
                    padx=18,
                    pady=9,
                    font=("Segoe UI", 9, "bold"),
                    cursor="hand2",
                )
                button.pack(fill="x", padx=8, pady=1)
                self.navigation_buttons[str(tab)] = button

        footer = tk.Label(self.sidebar, text="Multi-dispositivo", bg="#17233a", fg="#7186a9",
                          font=("Segoe UI", 8))
        footer.pack(side="bottom", anchor="w", padx=18, pady=16)

    def select_navigation_page(self, tab, label):
        self.notebook.select(tab)
        self.current_page_var.set(label)
        selected_key = str(tab)
        for key, button in self.navigation_buttons.items():
            is_selected = key == selected_key
            button.configure(
                bg="#1877f2" if is_selected else "#17233a",
                fg="white" if is_selected else "#dce6f5",
            )

    def auto_scan_worker(self):
        while not self.app_closing.is_set():
            time.sleep(4)
            if not any([self.search_running, self.sequence_running, self.human_running, self.report_running, self.advanced_running, self.maintenance_running]):
                current = self.get_devices()
                if set(current) != set(self.devices):
                    self.post_ui(self.refresh_devices_async)

    def find_adb(self):
        tools_path = RESOURCE_DIR / "herramientas"
        if tools_path.exists():
            for root, dirs, files in os.walk(tools_path):
                if "adb.exe" in files:
                    return os.path.join(root, "adb.exe")
        import shutil
        sys_adb = shutil.which("adb")
        return sys_adb if sys_adb else "adb"

    def find_scrcpy(self):
        for candidate in (RESOURCE_DIR / "herramientas").glob("**/scrcpy.exe"):
            return str(candidate)
        return None

    def load_device_aliases(self):
        try:
            if self.device_config_file.exists():
                data = json.loads(self.device_config_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {str(k): str(v).strip() for k, v in data.items() if str(v).strip()}
        except Exception as e:
            self.log(f"No se pudieron cargar los alias: {e}")
        return {}

    def save_device_aliases(self):
        try:
            self.device_config_file.write_text(json.dumps(self.device_aliases, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar alias: {e}")

    def create_general_widgets(self):
        dev_frame = ttk.LabelFrame(self.tab_general, text=" Gestión de Dispositivos Conectados ", padding=10)
        dev_frame.pack(fill="x", padx=10, pady=10)

        toolbar = ttk.Frame(dev_frame)
        toolbar.pack(fill="x", pady=(0, 7))

        ttk.Button(toolbar, text="Escanear Dispositivos", command=self.refresh_devices_async, style="Success.TButton").pack(side="left")
        ttk.Button(toolbar, text="Seleccionar todos", command=self.select_all_devices).pack(side="left", padx=(7, 0))
        ttk.Button(toolbar, text="Ninguno", command=self.clear_device_selection).pack(side="left", padx=(7, 0))
        ttk.Button(toolbar, text="Asignar nombre", command=self.rename_selected_device).pack(side="left", padx=(7, 0))
        ttk.Button(toolbar, text="Ver en Pantalla", command=self.open_selected_screens, style="Primary.TButton").pack(side="left", padx=(18, 0))
        ttk.Button(toolbar, text="Ver todos", command=self.open_all_screens).pack(side="left", padx=(7, 0))
        ttk.Button(toolbar, text="Cerrar pantallas", command=self.close_selected_screens).pack(side="left", padx=(7, 0))
        ttk.Button(toolbar, text="Cerrar todas", command=self.close_all_screens).pack(side="left", padx=(7, 0))

        self.lbl_devices = ttk.Label(toolbar, text="Dispositivos detectados: 0", font=("Segoe UI", 9, "bold"))
        self.lbl_devices.pack(side="right", padx=5)

        table_frame = ttk.Frame(dev_frame)
        table_frame.pack(fill="x")
        columns = ("nombre", "modelo", "serial", "android", "estado", "tarea")
        self.device_table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended", height=4)
        headings = {"nombre": "Nombre", "modelo": "Modelo", "serial": "Serie", "android": "Android", "estado": "Estado", "tarea": "Tarea actual"}
        widths = {"nombre": 140, "modelo": 135, "serial": 135, "android": 70, "estado": 95, "tarea": 180}
        for col in columns:
            self.device_table.heading(col, text=headings[col])
            self.device_table.column(col, width=widths[col], anchor="w")
        self.device_table.pack(side="left", fill="x", expand=True)
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.device_table.yview)
        scroll.pack(side="right", fill="y")
        self.device_table.configure(yscrollcommand=scroll.set)
        self.device_table.bind("<<TreeviewSelect>>", self.update_selection_label)
        self.device_table.bind("<Double-1>", lambda e: self.rename_selected_device())

        self.lbl_selection = ttk.Label(dev_frame, text="Seleccionados: 0", foreground="#1d5f91", font=("Segoe UI", 9, "bold"))
        self.lbl_selection.pack(anchor="w", pady=(6, 0))

        act_frame = ttk.LabelFrame(self.tab_general, text=" Tareas Básicas de Sistema ", padding=10)
        act_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(act_frame, text="Abrir Facebook en seleccionados", command=self.open_facebook_all, style="Primary.TButton").pack(anchor="w", padx=5, pady=5)
        
        ttk.Label(act_frame, text="Inyectar texto directo:", font=("Segoe UI", 9)).pack(anchor="w", padx=5, pady=(10, 2))
        self.text_post_general = scrolledtext.ScrolledText(act_frame, width=80, height=3, font=("Segoe UI", 10))
        self.text_post_general.pack(fill="x", padx=5, pady=2)
        ttk.Button(act_frame, text="Inyectar Texto Simple", command=lambda: self.execute_multithreaded(lambda dev: self.inject_text_adb(dev, self.text_post_general.get("1.0", tk.END).strip()), "Inyectando Texto")).pack(anchor="w", padx=5, pady=5)

    def create_interaction_widgets(self):
        info_lbl = ttk.Label(self.tab_interaction, text="Accesibilidad + clic calculado por figura para localizar Me gusta y Comentario.", font=("Segoe UI", 9, "italic", "bold"), foreground="#1877f2")
        info_lbl.pack(anchor="w", padx=15, pady=(15, 5))

        int_frame = ttk.LabelFrame(self.tab_interaction, text=" Configuración de la Acción ", padding=15)
        int_frame.pack(fill="x", padx=15, pady=5)

        ttk.Label(int_frame, text="URL de la publicación (Post, Foto, Video):", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=2)
        self.entry_int_url = ttk.Entry(int_frame, font=("Segoe UI", 10))
        self.entry_int_url.pack(fill="x", pady=(0, 10))

        opts_frame = ttk.Frame(int_frame)
        opts_frame.pack(fill="x", pady=5)

        self.int_airplane_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts_frame, text="🛡️ Rotar IP (Activar Modo Avión 5s)", variable=self.int_airplane_var).pack(side="left")

        self.int_warmup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text="☕ Realizar Calentamiento previo en Feed", variable=self.int_warmup_var).pack(side="left", padx=(20, 0))

        vision_opts = ttk.Frame(int_frame)
        vision_opts.pack(fill="x", pady=(6, 2))
        self.int_calculated_click_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            vision_opts,
            text="🎯 Clic calculado por figura (manita / comentario)",
            variable=self.int_calculated_click_var,
        ).pack(side="left")
        self.int_reel_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            vision_opts,
            text="🎬 Reel",
            variable=self.int_reel_mode_var,
        ).pack(side="left", padx=(18, 0))
        ttk.Label(vision_opts, text="Desplazamientos máximos:").pack(side="left", padx=(18, 4))
        self.int_calculated_scrolls_var = tk.StringVar(value="8")
        ttk.Spinbox(
            vision_opts,
            from_=0,
            to=30,
            width=4,
            textvariable=self.int_calculated_scrolls_var,
        ).pack(side="left")

        ttk.Label(int_frame, text="Texto del Comentario (Usa Spintax: {Hola|Qué tal}):", font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 2))
        self.text_int_comment = scrolledtext.ScrolledText(int_frame, height=4, font=("Segoe UI", 10))
        self.text_int_comment.pack(fill="x", pady=(0, 10))

        sec_frame = ttk.LabelFrame(self.tab_interaction, text=" Parámetros de Tiempos ", padding=10)
        sec_frame.pack(fill="x", padx=15, pady=5)

        row2 = ttk.Frame(sec_frame)
        row2.pack(fill="x", pady=4)
        ttk.Label(row2, text="Espera para cargar publicación en FB Lite:").pack(side="left")
        self.int_load_min = tk.StringVar(value="6.0")
        ttk.Spinbox(row2, from_=4.0, to=30.0, increment=1.0, width=4, textvariable=self.int_load_min).pack(side="left", padx=4)
        ttk.Label(row2, text="a").pack(side="left")
        self.int_load_max = tk.StringVar(value="10.0")
        ttk.Spinbox(row2, from_=4.0, to=30.0, increment=1.0, width=4, textvariable=self.int_load_max).pack(side="left", padx=4)
        ttk.Label(row2, text="segundos").pack(side="left")

        btn_row = ttk.Frame(self.tab_interaction)
        btn_row.pack(fill="x", padx=15, pady=15)

        self.int_do_like_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            btn_row, text="👍 Me gusta", variable=self.int_do_like_var
        ).pack(side="left", padx=(0, 10))
        self.int_do_comment_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            btn_row, text="💬 Comentario", variable=self.int_do_comment_var
        ).pack(side="left", padx=(0, 14))
        self.btn_start_selected = ttk.Button(
            btn_row,
            text="▶ Ejecutar acciones seleccionadas",
            command=self.start_selected_interactions,
            style="Success.TButton",
        )
        self.btn_start_selected.pack(side="left", ipadx=8, ipady=4)
        self.btn_stop_interaction = ttk.Button(
            btn_row,
            text="⏹ Detener proceso",
            command=self.stop_interaction_process,
            style="Warning.TButton",
            state="disabled",
        )
        self.btn_stop_interaction.pack(side="left", ipadx=8, ipady=4)
        self.interaction_status_var = tk.StringVar(value="Listo")
        ttk.Label(btn_row, textvariable=self.interaction_status_var).pack(side="right", padx=8)

    def create_human_widgets(self):
        human_frame = ttk.LabelFrame(self.tab_human, text=" 🛡️ Configuración de Calentamiento y Comportamiento Humano ", padding=15)
        human_frame.pack(fill="both", expand=True, padx=15, pady=15)

        ttk.Label(human_frame, text="Simula actividad real en Facebook Lite: desplazamiento variable con pausas de lectura, visualización de videos/reels y pausas prolongadas para evitar bloqueos.", font=("Segoe UI", 9, "italic"), foreground="#1877f2").pack(anchor="w", pady=(0, 10))

        opts = ttk.Frame(human_frame)
        opts.pack(fill="x", pady=5)

        self.hum_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="📜 Scroll orgánico variable (arriba/abajo con pausas)", variable=self.hum_scroll_var).pack(anchor="w", pady=3)

        self.hum_video_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="📺 Pausar ocasionalmente en videos / reels (10-30s)", variable=self.hum_video_var).pack(anchor="w", pady=3)

        self.hum_like_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="👍 Dar Me gusta ocasional de forma aleatoria (1 de cada 10 posts)", variable=self.hum_like_var).pack(anchor="w", pady=3)

        dur_frame = ttk.LabelFrame(human_frame, text=" Duración de la Sesión de Calentamiento ", padding=10)
        dur_frame.pack(fill="x", pady=15)

        row_dur = ttk.Frame(dur_frame)
        row_dur.pack(fill="x", pady=5)
        ttk.Label(row_dur, text="Tiempo total de ejecución continua:").pack(side="left")
        self.hum_duration_var = tk.StringVar(value="30")
        ttk.Spinbox(row_dur, from_=5.0, to=240.0, increment=5.0, width=5, textvariable=self.hum_duration_var).pack(side="left", padx=8)
        ttk.Label(row_dur, text="minutos").pack(side="left")

        btn_row_hum = ttk.Frame(human_frame)
        btn_row_hum.pack(fill="x", pady=15)

        self.btn_start_human = ttk.Button(btn_row_hum, text="▶ Iniciar Modo Humano en Seleccionados", command=self.start_human_warming, style="Success.TButton")
        self.btn_start_human.pack(side="left", ipadx=10, ipady=5)

        self.btn_stop_human = ttk.Button(btn_row_hum, text="⏹ Detener Modo Humano", command=self.stop_human_warming, style="Warning.TButton", state="disabled")
        self.btn_stop_human.pack(side="left", padx=15, ipadx=10, ipady=5)

        self.hum_status_var = tk.StringVar(value="Estado: Inactivo")
        ttk.Label(human_frame, textvariable=self.hum_status_var, font=("Segoe UI", 9, "bold"), foreground="#1d5f91").pack(anchor="w", pady=10)

    def create_report_widgets(self):
        rep_frame = ttk.LabelFrame(self.tab_report, text=" 🚨 Automatización de Reportes Masivos (Publicación / Perfil) ", padding=15)
        rep_frame.pack(fill="both", expand=True, padx=15, pady=15)

        ttk.Label(rep_frame, text="Ingresa el enlace de la publicación o perfil a reportar y selecciona el motivo:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.entry_rep_url = ttk.Entry(rep_frame, font=("Segoe UI", 10))
        self.entry_rep_url.pack(fill="x", pady=(0, 10))

        m_frame = ttk.LabelFrame(rep_frame, text=" Motivo del Reporte ", padding=10)
        m_frame.pack(fill="x", pady=10)

        self.rep_reason_var = tk.StringVar(value="spam")
        ttk.Radiobutton(m_frame, text="Spam / Publicidad engañosa", variable=self.rep_reason_var, value="spam").pack(anchor="w", pady=2)
        ttk.Radiobutton(m_frame, text="Información falsa / Fake News", variable=self.rep_reason_var, value="falsa").pack(anchor="w", pady=2)
        ttk.Radiobutton(m_frame, text="Cuenta falsa / Suplantación", variable=self.rep_reason_var, value="cuenta").pack(anchor="w", pady=2)

        opts_rep = ttk.Frame(rep_frame)
        opts_rep.pack(fill="x", pady=10)
        self.rep_airplane_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_rep, text="🛡️ Rotar IP con Modo Avión antes de cada reporte (Recomendado)", variable=self.rep_airplane_var).pack(anchor="w")

        btn_row_rep = ttk.Frame(rep_frame)
        btn_row_rep.pack(fill="x", pady=15)

        self.btn_start_report = ttk.Button(btn_row_rep, text="🚀 Ejecutar Reporte Masivo en Seleccionados", command=self.start_mass_report, style="Success.TButton")
        self.btn_start_report.pack(side="left", ipadx=10, ipady=5)

        self.btn_stop_report = ttk.Button(btn_row_rep, text="⏹ Detener Reportes", command=self.stop_mass_report, style="Warning.TButton", state="disabled")
        self.btn_stop_report.pack(side="left", padx=15, ipadx=10, ipady=5)

        self.rep_status_var = tk.StringVar(value="Estado: Listo para reportar.")
        ttk.Label(rep_frame, textvariable=self.rep_status_var, font=("Segoe UI", 9, "bold"), foreground="#1d5f91").pack(anchor="w", pady=10)

    def create_advanced_widgets(self):
        adv_frame = ttk.LabelFrame(self.tab_advanced, text=" 🚀 Módulo Avanzado: Auto-Invitaciones, Scraping de Leads y Publicación en Grupos ", padding=15)
        adv_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # 1. Auto-Invitación
        inv_frame = ttk.LabelFrame(adv_frame, text="1. Auto-Invitación Masiva a Eventos / Páginas", padding=10)
        inv_frame.pack(fill="x", pady=5)
        ttk.Label(inv_frame, text="URL del Evento o Página a invitar:").pack(anchor="w")
        self.entry_inv_url = ttk.Entry(inv_frame, font=("Segoe UI", 9))
        self.entry_inv_url.pack(fill="x", pady=(2, 5))
        ttk.Button(inv_frame, text="👥 Iniciar Auto-Invitación en Seleccionados", command=self.start_auto_invite, style="Primary.TButton").pack(anchor="w", pady=2)

        # 2. Scraping de Leads / Comentarios
        scrap_frame = ttk.LabelFrame(adv_frame, text="2. Scraping y Extracción de Leads (Comentarios)", padding=10)
        scrap_frame.pack(fill="x", pady=5)
        ttk.Label(scrap_frame, text="Extrae perfiles y textos de comentarios de la publicación activa en pantalla a CSV.").pack(anchor="w")
        ttk.Button(scrap_frame, text="📥 Extraer Comentarios a CSV", command=self.start_lead_scraping, style="Success.TButton").pack(anchor="w", pady=5)

        # 3. Cross-Posting en Grupos
        group_frame = ttk.LabelFrame(adv_frame, text="3. Publicación Cruzada (Cross-Posting) en Grupos", padding=10)
        group_frame.pack(fill="x", pady=5)
        ttk.Label(group_frame, text="Texto a publicar en rotación (Soporta Spintax):").pack(anchor="w")
        self.text_group_post = scrolledtext.ScrolledText(group_frame, height=3, font=("Segoe UI", 9))
        self.text_group_post.pack(fill="x", pady=(2, 5))
        ttk.Button(group_frame, text="📢 Publicar en Grupos Masivamente", command=self.start_group_crosspost, style="Success.TButton").pack(anchor="w", pady=2)

        self.adv_status_var = tk.StringVar(value="Estado Avanzado: En espera.")
        ttk.Label(adv_frame, textvariable=self.adv_status_var, font=("Segoe UI", 9, "bold"), foreground="#1d5f91").pack(anchor="w", pady=10)

    def create_maintenance_widgets(self):
        maint_frame = ttk.LabelFrame(self.tab_maintenance, text=" 🧹 Mantenimiento de Cuentas y Live Streaming Booster ", padding=15)
        maint_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # 1. Limpieza de notificaciones y solicitudes
        clean_frame = ttk.LabelFrame(maint_frame, text="1. Limpieza de Notificaciones y Solicitudes de Amistad", padding=10)
        clean_frame.pack(fill="x", pady=5)
        ttk.Label(clean_frame, text="Simula mantenimiento automático para limpiar alertas acumuladas y aceptar/rechazar pendientes.").pack(anchor="w", pady=2)
        ttk.Button(clean_frame, text="🧹 Ejecutar Mantenimiento de Cuentas", command=self.start_account_maintenance, style="Warning.TButton").pack(anchor="w", pady=5)

        # 2. Live Streaming Booster
        live_frame = ttk.LabelFrame(maint_frame, text="2. Live Streaming Booster (Tracción en En Vivos)", padding=10)
        live_frame.pack(fill="x", pady=5)
        ttk.Label(live_frame, text="URL de la Transmisión en Vivo:").pack(anchor="w")
        self.entry_live_url = ttk.Entry(live_frame, font=("Segoe UI", 9))
        self.entry_live_url.pack(fill="x", pady=(2, 5))
        ttk.Button(live_frame, text="📺 Iniciar Booster de Transmisión", command=self.start_live_booster, style="Primary.TButton").pack(anchor="w", pady=2)

        self.maint_status_var = tk.StringVar(value="Estado de Mantenimiento: En espera.")
        ttk.Label(maint_frame, textvariable=self.maint_status_var, font=("Segoe UI", 9, "bold"), foreground="#1d5f91").pack(anchor="w", pady=10)

    # --- LÓGICA DE LAS NUEVAS 5 ACTIVIDADES ---

    def start_auto_invite(self):
        url = self.entry_inv_url.get().strip()
        devs = self.get_selected_devices()
        if not devs or not url: return messagebox.showwarning("Aviso", "Selecciona dispositivos e ingresa una URL.")
        self.log("🚀 Iniciando Auto-Invitación masiva...")
        def task(d):
            self.run_on_device(d, ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url, "com.facebook.lite"])
            time.sleep(6)
            size = self.screen_size_cache.get(d, (1080, 1920))
            for _ in range(5): # Scroll por la lista de amigos y toque en invitar
                self.find_node_and_tap(d, ["invitar", "invite"], size)
                self.run_on_device(d, ["shell", "input", "swipe", str(size[0]//2), str(int(size[1]*0.7)), str(size[0]//2), str(int(size[1]*0.3)), "400"])
                time.sleep(2)
        self.execute_multithreaded(task, "Auto-Invitación")

    def start_lead_scraping(self):
        devs = self.get_selected_devices()
        if not devs: return messagebox.showwarning("Aviso", "Selecciona al menos un celular.")
        self.log("📥 Extrayendo comentarios y leads de la pantalla actual...")
        def task(d):
            hierarchy = self.get_android_hierarchy(d)
            if not hierarchy: return
            records = []
            for node in hierarchy.iter("node"):
                txt = node.attrib.get("text", "").strip()
                if txt and len(txt) > 3:
                    records.append([time.strftime("%Y-%m-%d %H:%M:%S"), d, txt])
            if records:
                os.makedirs(self.search_record_dir, exist_ok=True)
                csv_path = self.search_record_dir / f"leads_{time.strftime('%Y-%m-%d')}.csv"
                with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerows(records)
                self.log(f"[{d}] ✓ {len(records)} elementos extraídos y guardados en CSV.")
        self.execute_multithreaded(task, "Scraping de Leads")

    def start_group_crosspost(self):
        text = self.text_group_post.get("1.0", tk.END).strip()
        devs = self.get_selected_devices()
        if not devs or not text: return messagebox.showwarning("Aviso", "Selecciona dispositivos y escribe contenido.")
        self.log("📢 Iniciando publicación cruzada en grupos...")
        def task(d):
            final_txt = self.parse_spintax(text)
            self.run_on_device(d, ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "https://m.facebook.com/groups", "com.facebook.lite"])
            time.sleep(6)
            size = self.screen_size_cache.get(d, (1080, 1920))
            self.find_node_and_tap(d, ["escribe algo", "write something", "publicar"], size)
            time.sleep(2)
            self.inject_text_adb(d, final_txt)
            time.sleep(2)
            self.find_node_and_tap(d, ["publicar", "post"], size)
            self.log(f"[{d}] ✓ Publicación en grupo enviada.")
        self.execute_multithreaded(task, "Cross-Posting")

    def start_account_maintenance(self):
        devs = self.get_selected_devices()
        if not devs: return messagebox.showwarning("Aviso", "Selecciona al menos un celular.")
        self.log("🧹 Ejecutando mantenimiento y limpieza de cuentas...")
        def task(d):
            self.run_on_device(d, ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "https://m.facebook.com/notifications", "com.facebook.lite"])
            time.sleep(5)
            size = self.screen_size_cache.get(d, (1080, 1920))
            self.find_node_and_tap(d, ["marcar como leídas", "mark all as read", "aceptar", "confirmar"], size)
            self.log(f"[{d}] ✓ Mantenimiento completado.")
        self.execute_multithreaded(task, "Mantenimiento")

    def start_live_booster(self):
        url = self.entry_live_url.get().strip()
        devs = self.get_selected_devices()
        if not devs or not url: return messagebox.showwarning("Aviso", "Selecciona dispositivos e ingresa la URL del Live.")
        self.log("📺 Iniciando Live Streaming Booster...")
        def task(d):
            self.run_on_device(d, ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url, "com.facebook.lite"])
            time.sleep(10)
            size = self.screen_size_cache.get(d, (1080, 1920))
            end_t = time.time() + 600 # Mantener por 10 minutos mandando interacciones periódicas
            while time.time() < end_t and not self.app_closing.is_set():
                if OPENCV_AVAILABLE:
                    self.tap_image_template(d, "love.png")
                else:
                    self.run_on_device(d, ["shell", "input", "tap", str(int(size[0]*0.9)), str(int(size[1]*0.8))])
                time.sleep(30)
            self.log(f"[{d}] ✓ Sesión de Booster en vivo finalizada.")
        self.execute_multithreaded(task, "Live Booster")

    def create_vision_widgets(self):
        vision_frame = ttk.LabelFrame(self.tab_vision, text=" Reacciones OpenCV ", padding=15)
        vision_frame.pack(fill="both", expand=True, padx=10, pady=10)
        if not OPENCV_AVAILABLE:
            ttk.Label(vision_frame, text="⚠️ OpenCV y NumPy no están instaladas.", foreground="red", font=("Segoe UI", 10, "bold")).pack(pady=20)
            return
        ttk.Label(vision_frame, text="Selecciona la reacción:").pack(anchor="w", pady=5)
        btn_container = ttk.Frame(vision_frame)
        btn_container.pack(pady=20)
        reactions = [("👍 'Me gusta'", "like.png"), ("❤️ 'Me encanta'", "love.png"), ("😆 'Me divierte'", "haha.png"), ("😢 'Me entristece'", "sad.png"), ("😡 'Me enoja'", "angry.png")]
        for lbl, fn in reactions: ttk.Button(btn_container, text=lbl, command=lambda f=fn: self.execute_vision_reaction(f)).pack(fill="x", pady=6, ipadx=10, ipady=3)

    def create_search_widgets(self):
        search_frame = ttk.LabelFrame(self.tab_search, text=" Búsqueda asistida ", padding=12)
        search_frame.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Label(search_frame, text="Palabras clave (separadas por comas):").pack(anchor="w")
        self.search_keywords = scrolledtext.ScrolledText(search_frame, height=3, font=("Segoe UI", 10))
        self.search_keywords.pack(fill="x", pady=(3, 9))

        action_row = ttk.LabelFrame(search_frame, text=" Acción al encontrar palabras ", padding=8)
        action_row.pack(fill="x", pady=(2, 7))
        ttk.Label(
            action_row,
            text="La coincidencia abre la publicación pulsando su fecha/hora antes de ejecutar acciones.",
            foreground="#1d5f91",
        ).pack(anchor="w", pady=(0, 4))
        action_checks = ttk.Frame(action_row)
        action_checks.pack(fill="x")
        self.search_like_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            action_checks,
            text='👍 Me gusta',
            variable=self.search_like_var,
        ).pack(side="left")
        self.search_save_link_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            action_checks,
            text='Guardar enlace',
            variable=self.search_save_link_var,
        ).pack(side="left", padx=(18, 0))
        self.search_comment_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            action_checks,
            text='💬 Comentario',
            variable=self.search_comment_var,
        ).pack(side="left", padx=(18, 0))
        comment_row = ttk.Frame(action_row)
        comment_row.pack(fill="x", padx=(24, 0), pady=(4, 1))
        ttk.Label(comment_row, text="Texto del comentario:").pack(side="left")
        self.search_comment_text_var = tk.StringVar()
        ttk.Entry(comment_row, textvariable=self.search_comment_text_var).pack(side="left", fill="x", expand=True, padx=5)
        wait_row = ttk.Frame(action_row)
        wait_row.pack(fill="x", padx=(24, 0), pady=(4, 1))
        ttk.Label(wait_row, text="Espera antes de las acciones — mínimo:").pack(side="left")
        self.search_like_min_var = tk.StringVar(value="3")
        ttk.Spinbox(wait_row, from_=1, to=60, width=5, textvariable=self.search_like_min_var).pack(side="left", padx=5)
        ttk.Label(wait_row, text="máximo:").pack(side="left")
        self.search_like_max_var = tk.StringVar(value="8")
        ttk.Spinbox(wait_row, from_=1, to=60, width=5, textvariable=self.search_like_max_var).pack(side="left", padx=5)
        ttk.Label(wait_row, text="segundos").pack(side="left")
        self.search_continuous_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            action_row,
            text="Continuar buscando hasta pulsar Detener",
            variable=self.search_continuous_var,
        ).pack(anchor="w", pady=(3, 0))
        
        button_row = ttk.Frame(search_frame)
        button_row.pack(fill="x", pady=(10, 6))
        self.btn_start_search = ttk.Button(button_row, text="Iniciar búsqueda", command=self.start_keyword_search, style="Success.TButton")
        self.btn_start_search.pack(side="left")
        self.btn_stop_search = ttk.Button(button_row, text="Detener", command=self.stop_keyword_search, state="disabled")
        self.btn_stop_search.pack(side="left", padx=7)
        
        self.search_status_var = tk.StringVar(value="Listo para buscar.")
        ttk.Label(search_frame, textvariable=self.search_status_var, foreground="#1d5f91", font=("Segoe UI", 9, "bold")).pack(fill="x", pady=(2, 7))
        self.search_results = scrolledtext.ScrolledText(search_frame, height=5, font=("Consolas", 9), state="disabled")
        self.search_results.pack(fill="both", expand=True, pady=(3, 9))

    def create_sequence_widgets(self):
        sequence_frame = ttk.LabelFrame(
            self.tab_sequence,
            text=" Constructor visual de procedimientos ",
            padding=10,
        )
        sequence_frame.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Label(
            sequence_frame,
            text=(
                "Selecciona un teléfono, captura su pantalla y pulsa sobre la imagen para registrar un toque. "
                "La ejecución siempre puede detenerse."
            ),
            foreground="#1d5f91",
        ).pack(fill="x", pady=(0, 7))

        toolbar = ttk.Frame(sequence_frame)
        toolbar.pack(fill="x", pady=(0, 7))
        ttk.Button(toolbar, text="Capturar teléfono seleccionado", command=self.capture_sequence_screen).pack(side="left")
        ttk.Button(toolbar, text="Guardar", command=self.save_sequence_file).pack(side="right", padx=(7, 0))
        ttk.Button(toolbar, text="Cargar", command=self.load_sequence_file).pack(side="right")

        action_builder = ttk.LabelFrame(sequence_frame, text=" Agregar una acción al proceso ", padding=7)
        action_builder.pack(fill="x", pady=(0, 7))
        selector_row = ttk.Frame(action_builder)
        selector_row.pack(fill="x")
        ttk.Label(selector_row, text="Acción:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.sequence_action_var = tk.StringVar(value="Escribir texto")
        self.sequence_action_combo = ttk.Combobox(
            selector_row,
            textvariable=self.sequence_action_var,
            values=list(self.SEQUENCE_ACTIONS),
            state="readonly",
            width=29,
        )
        self.sequence_action_combo.pack(side="left", padx=(6, 8))
        self.sequence_action_combo.bind("<<ComboboxSelected>>", lambda _event: self.render_sequence_action_fields())
        ttk.Button(
            selector_row,
            text="Agregar acción",
            command=self.add_configured_sequence_action,
            style="Primary.TButton",
        ).pack(side="left")
        ttk.Label(
            selector_row,
            text="Los valores iniciales reutilizan los tiempos ya establecidos en el panel.",
            foreground="#1d5f91",
        ).pack(side="left", padx=(12, 0))
        self.sequence_action_fields = ttk.Frame(action_builder)
        self.sequence_action_fields.pack(fill="x", pady=(6, 0))
        self.render_sequence_action_fields()

        content = ttk.Panedwindow(sequence_frame, orient="horizontal")
        content.pack(fill="both", expand=True)
        preview_frame = ttk.LabelFrame(content, text=" Pantalla del teléfono ", padding=5)
        steps_frame = ttk.LabelFrame(content, text=" Pasos registrados ", padding=5)
        content.add(preview_frame, weight=3)
        content.add(steps_frame, weight=2)

        self.sequence_canvas = tk.Canvas(
            preview_frame,
            width=430,
            height=350,
            bg="#202020",
            highlightthickness=1,
            highlightbackground="#606060",
            cursor="crosshair",
        )
        self.sequence_canvas.pack(fill="both", expand=True)
        self.sequence_canvas.bind("<Button-1>", self.record_sequence_tap)

        self.sequence_tree = ttk.Treeview(
            steps_frame,
            columns=("step", "type", "detail"),
            show="headings",
            height=11,
            selectmode="browse",
        )
        self.sequence_tree.heading("step", text="#")
        self.sequence_tree.heading("type", text="Acción")
        self.sequence_tree.heading("detail", text="Detalle")
        self.sequence_tree.column("step", width=40, anchor="center", stretch=False)
        self.sequence_tree.column("type", width=85, anchor="w", stretch=False)
        self.sequence_tree.column("detail", width=220, anchor="w")
        self.sequence_tree.pack(fill="both", expand=True)

        edit_row = ttk.Frame(steps_frame)
        edit_row.pack(fill="x", pady=(6, 0))
        ttk.Button(edit_row, text="Subir", command=lambda: self.move_sequence_step(-1)).pack(side="left")
        ttk.Button(edit_row, text="Bajar", command=lambda: self.move_sequence_step(1)).pack(side="left", padx=(5, 0))
        ttk.Button(edit_row, text="Eliminar", command=self.delete_sequence_step).pack(side="left", padx=(5, 0))
        ttk.Button(edit_row, text="Limpiar", command=self.clear_sequence_steps).pack(side="right")

        execution_row = ttk.Frame(sequence_frame)
        execution_row.pack(fill="x", pady=(8, 4))
        self.btn_sequence_step = ttk.Button(
            execution_row,
            text="Ejecutar paso seleccionado",
            command=lambda: self.start_sequence_execution(single_step=True),
            style="Primary.TButton",
        )
        self.btn_sequence_step.pack(side="left")
        self.btn_sequence_all = ttk.Button(
            execution_row,
            text="Ejecutar secuencia completa",
            command=lambda: self.start_sequence_execution(single_step=False),
            style="Success.TButton",
        )
        self.btn_sequence_all.pack(side="left", padx=(7, 0))
        self.btn_sequence_stop = ttk.Button(
            execution_row,
            text="Detener",
            command=self.stop_sequence_execution,
            style="Warning.TButton",
            state="disabled",
        )
        self.btn_sequence_stop.pack(side="left", padx=(7, 0))
        self.sequence_status_var = tk.StringVar(value="Secuencia lista. No hay pasos registrados.")
        ttk.Label(
            sequence_frame,
            textvariable=self.sequence_status_var,
            foreground="#1d5f91",
            font=("Segoe UI", 9, "bold"),
        ).pack(fill="x", pady=(2, 0))

    def render_sequence_action_fields(self):
        if not hasattr(self, "sequence_action_fields"):
            return
        for child in self.sequence_action_fields.winfo_children():
            child.destroy()
        action_type = self.SEQUENCE_ACTIONS.get(self.sequence_action_var.get(), "text")
        self.sequence_action_text_widget = None
        self.sequence_action_list_widget = None
        self.sequence_action_url_var = None
        self.sequence_action_use_list_var = None
        self.sequence_action_min_var = None
        self.sequence_action_max_var = None
        self.sequence_action_duration_var = None
        self.sequence_action_target_text_var = None
        self.sequence_action_media_path_var = None

        if action_type == "tap":
            ttk.Label(
                self.sequence_action_fields,
                text=(
                    "Captura el teléfono y pulsa Agregar acción; después haz clic sobre la imagen. "
                    "La cruz numerada y sus coordenadas proporcionales se agregarán a Pasos registrados."
                ),
                foreground="#1d5f91",
            ).pack(anchor="w")
            return

        if action_type == "swipe":
            row = ttk.Frame(self.sequence_action_fields)
            row.pack(fill="x")
            ttk.Label(
                row,
                text="Duración de la presión y el desplazamiento:",
            ).pack(side="left")
            self.sequence_action_duration_var = tk.StringVar(value="800")
            ttk.Entry(row, textvariable=self.sequence_action_duration_var, width=8).pack(side="left", padx=(6, 4))
            ttk.Label(row, text="milisegundos (100 a 10000)").pack(side="left")
            ttk.Label(
                self.sequence_action_fields,
                text=(
                    "Pulsa Agregar acción y marca dos puntos sobre la captura: primero el inicio sostenido "
                    "y después el destino del deslizamiento."
                ),
                foreground="#1d5f91",
            ).pack(anchor="w", pady=(4, 0))
            return

        if action_type == "tap_text":
            row = ttk.Frame(self.sequence_action_fields)
            row.pack(fill="x")
            ttk.Label(row, text="Texto que debe aparecer:").pack(side="left")
            self.sequence_action_target_text_var = tk.StringVar(value="Escribe algo...")
            ttk.Entry(row, textvariable=self.sequence_action_target_text_var).pack(
                side="left", fill="x", expand=True, padx=(6, 0)
            )
            ttk.Label(
                self.sequence_action_fields,
                text=(
                    "Busca la frase completa en la pantalla y pulsa su centro. "
                    "Primero usa la información de Android y después el reconocimiento visual local."
                ),
                foreground="#1d5f91",
            ).pack(anchor="w", pady=(4, 0))
            return

        if action_type == "tap_publish":
            ttk.Label(
                self.sequence_action_fields,
                text=(
                    "Localiza el texto exacto Publicar y pulsa la coincidencia superior. "
                    "Usa accesibilidad y OCR; no depende de coordenadas fijas."
                ),
                foreground="#1d5f91",
            ).pack(anchor="w")
            return

        if action_type == "hide_keyboard":
            ttk.Label(
                self.sequence_action_fields,
                text=(
                    "Comprueba si el teclado está visible y sólo entonces lo oculta. "
                    "Si ya está cerrado, no pulsa Atrás ni cambia de pantalla."
                ),
                foreground="#1d5f91",
            ).pack(anchor="w")
            return

        if action_type == "upload_media":
            row = ttk.Frame(self.sequence_action_fields)
            row.pack(fill="x")
            ttk.Label(row, text="Imagen o video:").pack(side="left")
            self.sequence_action_media_path_var = tk.StringVar()
            ttk.Entry(
                row,
                textvariable=self.sequence_action_media_path_var,
                state="readonly",
            ).pack(side="left", fill="x", expand=True, padx=(6, 6))
            ttk.Button(row, text="Seleccionar archivo", command=self.choose_sequence_media).pack(side="left")
            ttk.Label(
                self.sequence_action_fields,
                text=(
                    "Al ejecutar el paso, las imágenes se copian a Pictures/PanelCelulares y los videos a "
                    "Movies/PanelCelulares; Android los registra para Galería y Archivos."
                ),
                foreground="#1d5f91",
            ).pack(anchor="w", pady=(4, 0))
            return

        if action_type == "text":
            row = ttk.Frame(self.sequence_action_fields)
            row.pack(fill="x")
            self.sequence_action_use_list_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(
                row,
                text="Usar el elemento actual de la lista",
                variable=self.sequence_action_use_list_var,
            ).pack(side="left")
            ttk.Label(row, text="Intervalo entre letras — mínimo:").pack(side="left", padx=(18, 4))
            self.sequence_action_min_var = tk.StringVar(value="0.05")
            self.sequence_action_max_var = tk.StringVar(value="0.15")
            ttk.Entry(row, textvariable=self.sequence_action_min_var, width=7).pack(side="left")
            ttk.Label(row, text="máximo:").pack(side="left", padx=(7, 4))
            ttk.Entry(row, textvariable=self.sequence_action_max_var, width=7).pack(side="left")
            ttk.Label(row, text="segundos").pack(side="left", padx=(4, 0))
            self.sequence_action_text_widget = scrolledtext.ScrolledText(
                self.sequence_action_fields, height=2, font=("Segoe UI", 9)
            )
            self.sequence_action_text_widget.pack(fill="x", pady=(5, 0))
            return

        if action_type == "load_list":
            ttk.Label(
                self.sequence_action_fields,
                text="Pega la lista: cada renglón será un elemento independiente del proceso.",
            ).pack(anchor="w")
            self.sequence_action_list_widget = scrolledtext.ScrolledText(
                self.sequence_action_fields, height=3, font=("Segoe UI", 9)
            )
            self.sequence_action_list_widget.pack(fill="x", pady=(4, 0))
            return

        if action_type == "next_list":
            ttk.Label(
                self.sequence_action_fields,
                text="Avanza al siguiente renglón de la lista cargada. Si ya terminó, el proceso lo informa sin reiniciar la lista.",
                foreground="#1d5f91",
            ).pack(anchor="w")
            return

        if action_type == "open_url":
            row = ttk.Frame(self.sequence_action_fields)
            row.pack(fill="x")
            self.sequence_action_use_list_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(
                row,
                text="Usar el elemento actual de la lista como URL",
                variable=self.sequence_action_use_list_var,
            ).pack(side="left")
            ttk.Label(row, text="Liga / link:").pack(side="left", padx=(18, 4))
            self.sequence_action_url_var = tk.StringVar()
            ttk.Entry(row, textvariable=self.sequence_action_url_var).pack(side="left", fill="x", expand=True)
            return

        if action_type in {"warmup", "wait"}:
            row = ttk.Frame(self.sequence_action_fields)
            row.pack(fill="x")
            if action_type == "warmup":
                label = "Duración del calentamiento — mínimo:"
                minimum_default, maximum_default = "5", "15"
            else:
                label = "Tiempo de espera aleatorio — mínimo:"
                minimum_default, maximum_default = "1", "4"
            ttk.Label(row, text=label).pack(side="left")
            self.sequence_action_min_var = tk.StringVar(value=minimum_default)
            self.sequence_action_max_var = tk.StringVar(value=maximum_default)
            ttk.Entry(row, textvariable=self.sequence_action_min_var, width=8).pack(side="left", padx=(5, 0))
            ttk.Label(row, text="máximo:").pack(side="left", padx=(8, 4))
            ttk.Entry(row, textvariable=self.sequence_action_max_var, width=8).pack(side="left")
            ttk.Label(row, text="segundos").pack(side="left", padx=(4, 0))
            if action_type == "warmup":
                ttk.Label(
                    row,
                    text="Reutiliza el calentamiento orgánico actual con sus pausas internas.",
                    foreground="#1d5f91",
                ).pack(side="left", padx=(12, 0))
            else:
                ttk.Label(
                    row,
                    text="Valores disponibles cada 0.5 s (500 ms).",
                    foreground="#1d5f91",
                ).pack(side="left", padx=(12, 0))
            return

        ttk.Label(
            self.sequence_action_fields,
            text="Registra el botón Atrás de Android.",
            foreground="#1d5f91",
        ).pack(anchor="w")

    def read_sequence_interval(self, minimum_var, maximum_var, minimum_allowed, maximum_allowed, label):
        try:
            minimum = float(minimum_var.get())
            maximum = float(maximum_var.get())
        except (AttributeError, TypeError, ValueError):
            messagebox.showwarning("Intervalo no válido", f"{label}: escribe mínimo y máximo numéricos.", parent=self.root)
            return None
        if not minimum_allowed <= minimum <= maximum_allowed or not minimum_allowed <= maximum <= maximum_allowed:
            messagebox.showwarning(
                "Intervalo no válido",
                f"{label}: ambos valores deben estar entre {minimum_allowed:g} y {maximum_allowed:g}.",
                parent=self.root,
            )
            return None
        if minimum > maximum:
            messagebox.showwarning("Intervalo no válido", f"{label}: el mínimo no puede superar al máximo.", parent=self.root)
            return None
        return round(minimum, 3), round(maximum, 3)

    def choose_sequence_media(self):
        path = filedialog.askopenfilename(
            title="Seleccionar imagen o video",
            parent=self.root,
            filetypes=(
                ("Imágenes y videos", "*.jpg *.jpeg *.png *.gif *.webp *.bmp *.heic *.heif *.avif *.mp4 *.mov *.mkv *.avi *.webm *.3gp *.m4v *.mpeg *.mpg *.wmv"),
                ("Todos los archivos", "*.*"),
            ),
        )
        if path and self.sequence_action_media_path_var is not None:
            self.sequence_action_media_path_var.set(str(Path(path).resolve()))

    def add_configured_sequence_action(self):
        if self.sequence_running:
            return
        action_type = self.SEQUENCE_ACTIONS.get(self.sequence_action_var.get(), "text")
        step = {"type": action_type}

        if action_type == "tap":
            if not self.sequence_capture_size or not self.sequence_display_geometry:
                return messagebox.showwarning(
                    "Captura requerida",
                    "Primero selecciona un teléfono y pulsa Capturar teléfono seleccionado.",
                    parent=self.root,
                )
            self.sequence_status_var.set(
                "Dar clic está activo: pulsa el punto deseado sobre la captura para registrar la cruz y sus coordenadas."
            )
            self.sequence_record_mode = "tap"
            self.sequence_swipe_start = None
            self.draw_sequence_markers()
            return
        if action_type == "swipe":
            if not self.sequence_capture_size or not self.sequence_display_geometry:
                return messagebox.showwarning(
                    "Captura requerida",
                    "Primero selecciona un teléfono y pulsa Capturar teléfono seleccionado.",
                    parent=self.root,
                )
            try:
                duration_ms = int(self.sequence_action_duration_var.get())
            except (AttributeError, TypeError, ValueError):
                return messagebox.showwarning(
                    "Duración no válida",
                    "Escribe la duración sostenida en milisegundos.",
                    parent=self.root,
                )
            if not 100 <= duration_ms <= 10000:
                return messagebox.showwarning(
                    "Duración no válida",
                    "La duración debe estar entre 100 y 10000 milisegundos.",
                    parent=self.root,
                )
            self.sequence_record_mode = "swipe"
            self.sequence_swipe_start = {"duration_ms": duration_ms}
            self.draw_sequence_markers()
            self.sequence_status_var.set(
                "Deslizamiento activo: marca primero dónde se mantendrá presionado y después el punto de destino."
            )
            return
        if action_type == "tap_text":
            target_text = self.sequence_action_target_text_var.get().strip()
            if not target_text:
                return messagebox.showwarning(
                    "Texto requerido",
                    "Escribe el texto que debe identificarse en la pantalla.",
                    parent=self.root,
                )
            step["target_text"] = target_text
        if action_type == "upload_media":
            media_path = Path(self.sequence_action_media_path_var.get().strip())
            media_type = self.sequence_media_type(media_path)
            if not media_path.is_file() or media_type is None:
                return messagebox.showwarning(
                    "Archivo no válido",
                    "Selecciona una imagen o video compatible que todavía exista en el equipo.",
                    parent=self.root,
                )
            step.update({"local_path": str(media_path.resolve()), "media_type": media_type})
        if action_type == "text":
            use_list = bool(self.sequence_action_use_list_var.get())
            text_value = self.sequence_action_text_widget.get("1.0", tk.END).rstrip("\r\n")
            if not use_list and not text_value:
                return messagebox.showwarning("Texto requerido", "Escribe el texto o activa el elemento actual de la lista.")
            interval = self.read_sequence_interval(
                self.sequence_action_min_var, self.sequence_action_max_var, 0.01, 10.0, "Intervalo entre letras"
            )
            if not interval:
                return
            step.update({
                "source": "list" if use_list else "literal",
                "text": "" if use_list else text_value,
                "char_min_seconds": interval[0],
                "char_max_seconds": interval[1],
            })
        elif action_type == "load_list":
            raw_value = self.sequence_action_list_widget.get("1.0", tk.END)
            items = [line.strip() for line in raw_value.splitlines() if line.strip()]
            if not items:
                return messagebox.showwarning("Lista vacía", "Agrega al menos un renglón a la lista.")
            step["items"] = items
        elif action_type == "open_url":
            use_list = bool(self.sequence_action_use_list_var.get())
            url_value = self.sequence_action_url_var.get().strip()
            if not use_list and not url_value:
                return messagebox.showwarning("URL requerida", "Escribe una liga o activa el elemento actual de la lista.")
            step.update({"source": "list" if use_list else "literal", "url": "" if use_list else url_value})
        elif action_type in {"warmup", "wait"}:
            minimum_allowed = 1.0 if action_type == "warmup" else 0.5
            interval = self.read_sequence_interval(
                self.sequence_action_min_var,
                self.sequence_action_max_var,
                minimum_allowed,
                3600.0,
                "Calentamiento" if action_type == "warmup" else "Espera",
            )
            if not interval:
                return
            step.update({"min_seconds": interval[0], "max_seconds": interval[1]})
            if action_type == "wait":
                if any(abs(value * 2 - round(value * 2)) > 1e-9 for value in interval):
                    return messagebox.showwarning(
                        "Intervalo no válido",
                        "El mínimo y el máximo deben avanzar de 0.5 en 0.5 segundos.",
                        parent=self.root,
                    )
                step["interval_step"] = 0.5
        self.add_sequence_step(step)

    def capture_sequence_screen(self):
        if self.sequence_running:
            return messagebox.showwarning("Secuencia activa", "Detén la ejecución antes de capturar otra pantalla.")
        devices = self.get_selected_devices()
        if len(devices) != 1:
            return messagebox.showwarning("Selección", "Selecciona exactamente un teléfono para capturar su pantalla.")
        device = devices[0]
        self.sequence_status_var.set(f"Capturando pantalla de {self.display_device_name(device)}...")

        def worker():
            screen = self.capture_device_screen(device)
            if screen is None:
                self.post_ui(lambda: self.sequence_status_var.set("No se pudo capturar la pantalla."))
                return
            self.post_ui(lambda img=screen, dev=device: self.show_sequence_screen(dev, img))

        threading.Thread(target=worker, daemon=True).start()

    def show_sequence_screen(self, device, screen):
        if screen is None or not OPENCV_AVAILABLE:
            self.sequence_status_var.set("La vista previa requiere OpenCV.")
            return
        source_height, source_width = screen.shape[:2]
        canvas_width = max(320, self.sequence_canvas.winfo_width())
        canvas_height = max(300, self.sequence_canvas.winfo_height())
        scale = min(canvas_width / source_width, canvas_height / source_height)
        display_width = max(1, int(source_width * scale))
        display_height = max(1, int(source_height * scale))
        resized = cv2.resize(screen, (display_width, display_height), interpolation=cv2.INTER_AREA)
        ok, encoded = cv2.imencode(".png", resized)
        if not ok:
            self.sequence_status_var.set("No se pudo preparar la vista previa.")
            return
        self.sequence_photo = tk.PhotoImage(data=base64.b64encode(encoded.tobytes()).decode("ascii"))
        offset_x = (canvas_width - display_width) // 2
        offset_y = (canvas_height - display_height) // 2
        self.sequence_canvas.delete("all")
        self.sequence_canvas.create_image(offset_x, offset_y, anchor="nw", image=self.sequence_photo)
        self.sequence_capture_size = (source_width, source_height)
        self.sequence_display_geometry = (offset_x, offset_y, display_width, display_height)
        self.sequence_swipe_start = None
        self.draw_sequence_markers()
        self.sequence_status_var.set(
            f"Captura de {self.display_device_name(device)}: {source_width} × {source_height}. Pulsa sobre la imagen para agregar un toque."
        )

    def record_sequence_tap(self, event):
        if self.sequence_running or not self.sequence_capture_size or not self.sequence_display_geometry:
            return
        offset_x, offset_y, display_width, display_height = self.sequence_display_geometry
        local_x, local_y = event.x - offset_x, event.y - offset_y
        if not (0 <= local_x <= display_width and 0 <= local_y <= display_height):
            return
        source_width, source_height = self.sequence_capture_size
        x_ratio = min(1.0, max(0.0, local_x / display_width))
        y_ratio = min(1.0, max(0.0, local_y / display_height))
        if self.sequence_record_mode == "swipe":
            pending = self.sequence_swipe_start or {"duration_ms": 800}
            if "x_ratio" not in pending:
                pending.update({
                    "x_ratio": round(x_ratio, 6),
                    "y_ratio": round(y_ratio, 6),
                    "recorded_width": source_width,
                    "recorded_height": source_height,
                })
                self.sequence_swipe_start = pending
                self.draw_sequence_markers()
                self.sequence_status_var.set(
                    f"Inicio sostenido: X {x_ratio * 100:.1f}% · Y {y_ratio * 100:.1f}%. Ahora marca el destino."
                )
                return
            self.add_sequence_step({
                "type": "swipe",
                "start_x_ratio": pending["x_ratio"],
                "start_y_ratio": pending["y_ratio"],
                "end_x_ratio": round(x_ratio, 6),
                "end_y_ratio": round(y_ratio, 6),
                "duration_ms": pending["duration_ms"],
                "recorded_width": source_width,
                "recorded_height": source_height,
            })
            self.sequence_swipe_start = {"duration_ms": pending["duration_ms"]}
            self.sequence_status_var.set(
                f"Deslizamiento agregado: X {pending['x_ratio'] * 100:.1f}%, Y {pending['y_ratio'] * 100:.1f}% "
                f"→ X {x_ratio * 100:.1f}%, Y {y_ratio * 100:.1f}%."
            )
            return
        self.add_sequence_step({
            "type": "tap",
            "x_ratio": round(x_ratio, 6),
            "y_ratio": round(y_ratio, 6),
            "recorded_width": source_width,
            "recorded_height": source_height,
        })
        self.sequence_status_var.set(
            f"Dar clic agregado: X {x_ratio * 100:.1f}% · Y {y_ratio * 100:.1f}%."
        )

    def add_sequence_step(self, step):
        if self.sequence_running:
            return
        validated = self.validate_sequence_step(step)
        if not validated:
            return messagebox.showwarning("Paso no válido", "El paso no contiene una acción admitida.")
        self.sequence_steps.append(validated)
        self.refresh_sequence_tree(select_index=len(self.sequence_steps) - 1)
        self.draw_sequence_markers()

    def validate_sequence_step(self, step):
        if not isinstance(step, dict):
            return None
        step_type = str(step.get("type", "")).strip().casefold()
        if step_type == "tap":
            try:
                x_ratio = float(step["x_ratio"])
                y_ratio = float(step["y_ratio"])
            except (KeyError, TypeError, ValueError):
                return None
            if not (0.0 <= x_ratio <= 1.0 and 0.0 <= y_ratio <= 1.0):
                return None
            return {
                "type": "tap",
                "x_ratio": round(x_ratio, 6),
                "y_ratio": round(y_ratio, 6),
                "recorded_width": max(1, int(step.get("recorded_width", 1))),
                "recorded_height": max(1, int(step.get("recorded_height", 1))),
            }
        if step_type == "swipe":
            try:
                start_x = float(step["start_x_ratio"])
                start_y = float(step["start_y_ratio"])
                end_x = float(step["end_x_ratio"])
                end_y = float(step["end_y_ratio"])
                duration_ms = int(step["duration_ms"])
            except (KeyError, TypeError, ValueError):
                return None
            if not all(0.0 <= value <= 1.0 for value in (start_x, start_y, end_x, end_y)):
                return None
            if not 100 <= duration_ms <= 10000:
                return None
            return {
                "type": "swipe",
                "start_x_ratio": round(start_x, 6),
                "start_y_ratio": round(start_y, 6),
                "end_x_ratio": round(end_x, 6),
                "end_y_ratio": round(end_y, 6),
                "duration_ms": duration_ms,
                "recorded_width": max(1, int(step.get("recorded_width", 1))),
                "recorded_height": max(1, int(step.get("recorded_height", 1))),
            }
        if step_type == "tap_text":
            target_text = str(step.get("target_text", "")).strip()
            if not target_text or len(target_text) > 500:
                return None
            return {"type": "tap_text", "target_text": target_text}
        if step_type == "tap_publish":
            return {"type": "tap_publish"}
        if step_type == "hide_keyboard":
            return {"type": "hide_keyboard"}
        if step_type == "upload_media":
            local_path = str(step.get("local_path", "")).strip()
            media_type = str(step.get("media_type", "")).strip().casefold()
            detected_type = self.sequence_media_type(Path(local_path)) if local_path else None
            if not local_path or len(local_path) > 32767 or media_type not in {"image", "video"}:
                return None
            if detected_type != media_type:
                return None
            return {"type": "upload_media", "local_path": local_path, "media_type": media_type}
        if step_type == "wait":
            try:
                if "min_seconds" in step or "max_seconds" in step:
                    minimum = float(step["min_seconds"])
                    maximum = float(step["max_seconds"])
                else:
                    # Compatibilidad con los JSON versión 1 de espera fija.
                    minimum = maximum = float(step["seconds"])
            except (KeyError, TypeError, ValueError):
                return None
            interval_step = step.get("interval_step")
            if interval_step is not None:
                try:
                    interval_step = float(interval_step)
                except (TypeError, ValueError):
                    return None
                if interval_step != 0.5:
                    return None
                if minimum < 0.5 or any(abs(value * 2 - round(value * 2)) > 1e-9 for value in (minimum, maximum)):
                    return None
            if not 0.1 <= minimum <= 3600.0 or not 0.1 <= maximum <= 3600.0 or minimum > maximum:
                return None
            validated_wait = {
                "type": "wait",
                "min_seconds": round(minimum, 3),
                "max_seconds": round(maximum, 3),
            }
            if interval_step is not None:
                validated_wait["interval_step"] = interval_step
            return validated_wait
        if step_type == "warmup":
            try:
                minimum = float(step["min_seconds"])
                maximum = float(step["max_seconds"])
            except (KeyError, TypeError, ValueError):
                return None
            if not 1.0 <= minimum <= 3600.0 or not 1.0 <= maximum <= 3600.0 or minimum > maximum:
                return None
            return {
                "type": "warmup",
                "min_seconds": round(minimum, 3),
                "max_seconds": round(maximum, 3),
            }
        if step_type == "load_list":
            items = step.get("items")
            if not isinstance(items, list) or not 1 <= len(items) <= 1000:
                return None
            cleaned = []
            for item in items:
                if not isinstance(item, str):
                    return None
                value = item.strip()
                if not value or len(value) > 10000:
                    return None
                cleaned.append(value)
            return {"type": "load_list", "items": cleaned}
        if step_type == "next_list":
            return {"type": "next_list"}
        if step_type == "text":
            source = str(step.get("source", "literal")).strip().casefold()
            text_value = str(step.get("text", ""))
            try:
                minimum = float(step["char_min_seconds"])
                maximum = float(step["char_max_seconds"])
            except (KeyError, TypeError, ValueError):
                return None
            if source not in {"literal", "list"}:
                return None
            if source == "literal" and (not text_value or len(text_value) > 20000):
                return None
            if source == "list":
                text_value = ""
            if not 0.01 <= minimum <= 10.0 or not 0.01 <= maximum <= 10.0 or minimum > maximum:
                return None
            return {
                "type": "text",
                "source": source,
                "text": text_value,
                "char_min_seconds": round(minimum, 3),
                "char_max_seconds": round(maximum, 3),
            }
        if step_type == "open_url":
            source = str(step.get("source", "literal")).strip().casefold()
            url_value = str(step.get("url", "")).strip()
            if source not in {"literal", "list"}:
                return None
            if source == "literal":
                parsed = urlparse(url_value)
                if len(url_value) > 2048 or parsed.scheme not in {"http", "https"} or not parsed.hostname:
                    return None
            else:
                url_value = ""
            return {"type": "open_url", "source": source, "url": url_value}
        if step_type == "back":
            return {"type": "back"}
        return None

    def sequence_step_description(self, step):
        if step["type"] == "tap":
            return "Toque", f"X {step['x_ratio'] * 100:.1f}% · Y {step['y_ratio'] * 100:.1f}%"
        if step["type"] == "swipe":
            return (
                "Presionar y deslizar",
                f"X {step['start_x_ratio'] * 100:.1f}%, Y {step['start_y_ratio'] * 100:.1f}% → "
                f"X {step['end_x_ratio'] * 100:.1f}%, Y {step['end_y_ratio'] * 100:.1f}% · {step['duration_ms']} ms",
            )
        if step["type"] == "tap_text":
            return "Identificar y pulsar", f'Texto exacto: "{step["target_text"][:80]}"'
        if step["type"] == "tap_publish":
            return "Identificar Publicar", "Pulsar la coincidencia exacta superior"
        if step["type"] == "hide_keyboard":
            return "Ocultar teclado", "Cerrar sólo cuando Android confirme que está visible"
        if step["type"] == "upload_media":
            media_label = "Imagen" if step["media_type"] == "image" else "Video"
            return "Subir multimedia", f"{media_label}: {Path(step['local_path']).name}"
        if step["type"] == "wait":
            minimum = step["min_seconds"]
            maximum = step["max_seconds"]
            if minimum == maximum:
                return "Espera", f"{minimum:g} segundos (fija)"
            if step.get("interval_step") == 0.5:
                return "Tiempo de espera", f"Aleatorio: {minimum:g} a {maximum:g} segundos · saltos de 0.5 s"
            return "Espera", f"Aleatoria: {minimum:g} a {maximum:g} segundos"
        if step["type"] == "warmup":
            return "Calentamiento", f"Orgánico: {step['min_seconds']:g} a {step['max_seconds']:g} segundos"
        if step["type"] == "load_list":
            return "Cargar lista", f"{len(step['items'])} renglones"
        if step["type"] == "next_list":
            return "Siguiente", "Avanzar un renglón de la lista"
        if step["type"] == "text":
            source = "elemento de lista" if step["source"] == "list" else f"texto: {step['text'][:45]}"
            return "Escribir", f"{source} · {step['char_min_seconds']:g}–{step['char_max_seconds']:g} s/letra"
        if step["type"] == "open_url":
            source = "elemento de lista" if step["source"] == "list" else step["url"][:55]
            return "Abrir URL", source
        return "Atrás", "Botón Atrás de Android"

    def refresh_sequence_tree(self, select_index=None):
        self.sequence_tree.delete(*self.sequence_tree.get_children())
        for index, step in enumerate(self.sequence_steps):
            action, detail = self.sequence_step_description(step)
            self.sequence_tree.insert("", "end", iid=str(index), values=(index + 1, action, detail))
        if select_index is not None and 0 <= select_index < len(self.sequence_steps):
            self.sequence_tree.selection_set(str(select_index))
            self.sequence_tree.focus(str(select_index))
            self.sequence_tree.see(str(select_index))
        self.sequence_status_var.set(f"Pasos registrados: {len(self.sequence_steps)}.")

    def selected_sequence_index(self):
        selection = self.sequence_tree.selection()
        if not selection:
            return None
        try:
            return int(selection[0])
        except (TypeError, ValueError):
            return None

    def delete_sequence_step(self):
        if self.sequence_running:
            return
        index = self.selected_sequence_index()
        if index is None:
            return
        self.sequence_steps.pop(index)
        self.refresh_sequence_tree(select_index=min(index, len(self.sequence_steps) - 1))
        self.draw_sequence_markers()

    def move_sequence_step(self, delta):
        if self.sequence_running:
            return
        index = self.selected_sequence_index()
        if index is None:
            return
        target = index + delta
        if not 0 <= target < len(self.sequence_steps):
            return
        self.sequence_steps[index], self.sequence_steps[target] = self.sequence_steps[target], self.sequence_steps[index]
        self.refresh_sequence_tree(select_index=target)
        self.draw_sequence_markers()

    def clear_sequence_steps(self):
        if self.sequence_running or not self.sequence_steps:
            return
        if messagebox.askyesno("Limpiar secuencia", "¿Eliminar todos los pasos registrados?", parent=self.root):
            self.sequence_steps.clear()
            self.refresh_sequence_tree()
            self.draw_sequence_markers()

    def draw_sequence_markers(self):
        if not hasattr(self, "sequence_canvas"):
            return
        self.sequence_canvas.delete("sequence_marker")
        if not self.sequence_display_geometry:
            return
        offset_x, offset_y, display_width, display_height = self.sequence_display_geometry
        for step_number, step in enumerate(self.sequence_steps, start=1):
            if step.get("type") == "tap":
                x = offset_x + step["x_ratio"] * display_width
                y = offset_y + step["y_ratio"] * display_height
                self.sequence_canvas.create_line(
                    x - 12, y, x + 12, y, fill="#ff3030", width=2, tags="sequence_marker",
                )
                self.sequence_canvas.create_line(
                    x, y - 12, x, y + 12, fill="#ff3030", width=2, tags="sequence_marker",
                )
                self.sequence_canvas.create_text(
                    x + 16, y - 12, text=str(step_number), fill="#ff3030",
                    font=("Segoe UI", 8, "bold"), tags="sequence_marker",
                )
                continue
            if step.get("type") != "swipe":
                continue
            start_x = offset_x + step["start_x_ratio"] * display_width
            start_y = offset_y + step["start_y_ratio"] * display_height
            end_x = offset_x + step["end_x_ratio"] * display_width
            end_y = offset_y + step["end_y_ratio"] * display_height
            self.sequence_canvas.create_line(
                start_x, start_y, end_x, end_y, fill="#ff8c00", width=3,
                arrow=tk.LAST, tags="sequence_marker",
            )
            for x, y, suffix in ((start_x, start_y, "I"), (end_x, end_y, "F")):
                self.sequence_canvas.create_line(
                    x - 10, y, x + 10, y, fill="#ff8c00", width=2, tags="sequence_marker",
                )
                self.sequence_canvas.create_line(
                    x, y - 10, x, y + 10, fill="#ff8c00", width=2, tags="sequence_marker",
                )
                self.sequence_canvas.create_text(
                    x + 15, y - 11, text=f"{step_number}{suffix}", fill="#ff8c00",
                    font=("Segoe UI", 8, "bold"), tags="sequence_marker",
                )
        pending = self.sequence_swipe_start or {}
        if self.sequence_record_mode == "swipe" and "x_ratio" in pending:
            x = offset_x + pending["x_ratio"] * display_width
            y = offset_y + pending["y_ratio"] * display_height
            self.sequence_canvas.create_oval(
                x - 11, y - 11, x + 11, y + 11,
                outline="#ffd400", width=2, tags="sequence_marker",
            )
            self.sequence_canvas.create_text(
                x, y, text="I", fill="#ffd400",
                font=("Segoe UI", 8, "bold"), tags="sequence_marker",
            )

    def save_sequence_file(self):
        if self.sequence_running or not self.sequence_steps:
            return messagebox.showwarning("Secuencia", "No hay pasos para guardar.")
        self.sequence_dir.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Guardar secuencia",
            initialdir=str(self.sequence_dir),
            defaultextension=".json",
            filetypes=[("Secuencia JSON", "*.json")],
        )
        if not path:
            return
        payload = {
            "format": "panel-celulares-sequence",
            "version": 1,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "steps": self.sequence_steps,
        }
        try:
            Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.sequence_status_var.set(f"Secuencia guardada: {Path(path).name}")
        except Exception as error:
            messagebox.showerror("No se pudo guardar", str(error), parent=self.root)

    def load_sequence_file(self):
        if self.sequence_running:
            return
        self.sequence_dir.mkdir(parents=True, exist_ok=True)
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Cargar secuencia",
            initialdir=str(self.sequence_dir),
            filetypes=[("Secuencia JSON", "*.json")],
        )
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("format") != "panel-celulares-sequence" or payload.get("version") != 1:
                raise ValueError("El archivo no pertenece al formato de secuencias versión 1.")
            raw_steps = payload.get("steps")
            if not isinstance(raw_steps, list) or len(raw_steps) > 500:
                raise ValueError("La lista de pasos no es válida o supera el máximo de 500.")
            validated = []
            for raw_step in raw_steps:
                step = self.validate_sequence_step(raw_step)
                if not step:
                    raise ValueError("El archivo contiene un paso no permitido.")
                validated.append(step)
            self.sequence_steps = validated
            self.refresh_sequence_tree(select_index=0 if validated else None)
            self.draw_sequence_markers()
            self.sequence_status_var.set(f"Secuencia cargada: {Path(path).name} · {len(validated)} pasos.")
        except Exception as error:
            messagebox.showerror("No se pudo cargar", str(error), parent=self.root)

    def start_sequence_execution(self, single_step=False):
        if self.sequence_running:
            return
        if not self.sequence_steps:
            return messagebox.showwarning("Secuencia", "Registra o carga al menos un paso.")
        if single_step:
            index = self.selected_sequence_index()
            if index is None:
                return messagebox.showwarning("Secuencia", "Selecciona el paso que deseas ejecutar.")
            steps = [(index, dict(self.sequence_steps[index]))]
        else:
            steps = [(index, dict(step)) for index, step in enumerate(self.sequence_steps)]
        devices, busy = self.claim_devices(self.get_selected_devices(), "Secuencia de acciones")
        if not devices:
            return messagebox.showwarning("Equipos ocupados", "Selecciona teléfonos disponibles para ejecutar la secuencia.")
        if busy:
            messagebox.showinfo("Equipos ocupados", "Se omitieron equipos que ya ejecutan otra acción.")
        previous_tasks = {device: self.device_tasks.get(device) for device in devices}
        for device in devices:
            self.set_device_task(device, "Secuencia de acciones")
        self.sequence_stop_event.clear()
        self.sequence_running = True
        self.btn_sequence_step.config(state="disabled")
        self.btn_sequence_all.config(state="disabled")
        self.btn_sequence_stop.config(state="normal")
        self.sequence_status_var.set(f"Ejecutando {len(steps)} paso(s) en {len(devices)} teléfono(s)...")
        threading.Thread(
            target=self.sequence_execution_worker,
            args=(devices, steps, previous_tasks),
            daemon=True,
        ).start()

    def sequence_list_value(self, list_context, device):
        context = list_context.get(device) or {}
        items = context.get("items") or []
        index = context.get("index", 0)
        if not 0 <= index < len(items):
            return None
        return items[index]

    @staticmethod
    def normalize_tappable_text(value):
        """Iguala espacios y las dos representaciones habituales de puntos suspensivos."""
        normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
        normalized = normalized.replace("…", "...")
        return re.sub(r"\s+", " ", normalized).strip()

    def find_visible_text_point(self, device, target_text):
        """Devuelve el centro del texto exacto, priorizando accesibilidad sobre OCR."""
        target = self.normalize_tappable_text(target_text)
        if not target:
            return None, None
        hierarchy = self.get_android_hierarchy(device)
        accessibility_matches = []
        for record in self.accessibility_text_records(hierarchy):
            if self.normalize_tappable_text(record.get("text")) != target:
                continue
            left, top, right, bottom = record["bounds"]
            if right > left and bottom > top:
                accessibility_matches.append((top, (left + right) // 2, (top + bottom) // 2))
        if accessibility_matches:
            accessibility_matches.sort()
            _, x, y = accessibility_matches[0]
            return (x, y), "accesibilidad"

        ocr_matches = []
        for record in self.windows_ocr_records(device):
            if self.normalize_tappable_text(record.get("text")) != target:
                continue
            left, top, right, bottom = record.get("bounds", (0, 0, 0, 0))
            if right > left and bottom > top:
                ocr_matches.append((top, (left + right) // 2, (top + bottom) // 2))
        if ocr_matches:
            ocr_matches.sort()
            _, x, y = ocr_matches[0]
            return (x, y), "OCR local"
        return None, None

    def tap_visible_text(self, device, target_text):
        point, source = self.find_visible_text_point(device, target_text)
        if point is None:
            self.log(f'[{device}] Secuencia: no se encontró el texto exacto "{target_text}".')
            return False
        x, y = point
        ok, detail = self.run_on_device(device, ["shell", "input", "tap", str(x), str(y)], timeout=15)
        if ok:
            self.log(f'[{device}] Secuencia: texto "{target_text}" pulsado en ({x}, {y}) mediante {source}.')
        else:
            self.log(f'[{device}] Secuencia: se encontró "{target_text}", pero el toque falló: {detail}')
        return ok

    @staticmethod
    def keyboard_visible_from_diagnostics(output):
        """Interpreta los indicadores habituales de teclado visible entre versiones de Android."""
        value = str(output or "")
        true_markers = (
            r"\bmInputShown\s*=\s*true\b",
            r"\bisInputViewShown\s*=\s*true\b",
            r"\bmInputMethodWindowVisible\s*=\s*true\b",
            r"\bmImeShowing\s*=\s*true\b",
            r"\bmImeWindowVis\s*=\s*0x(?:2|3)\b",
        )
        return any(re.search(pattern, value, re.IGNORECASE) for pattern in true_markers)

    def is_keyboard_visible(self, device):
        ok, diagnostics = self.run_on_device(device, ["shell", "dumpsys", "input_method"], timeout=15)
        if ok and self.keyboard_visible_from_diagnostics(diagnostics):
            return True
        try:
            hierarchy = self.get_android_hierarchy(device)
            if hierarchy is not None:
                for node in hierarchy.iter("node"):
                    package = node.attrib.get("package", "").casefold()
                    if any(marker in package for marker in ("inputmethod", "keyboard", ".ime")):
                        return True
        except Exception as error:
            self.log(f"[{device}] Secuencia: no se pudo verificar el teclado por accesibilidad: {error}")
        return False

    def hide_keyboard_if_visible(self, device):
        if not self.is_keyboard_visible(device):
            self.log(f"[{device}] Secuencia: el teclado ya está oculto; no se pulsó Atrás.")
            return True
        ok, detail = self.run_on_device(device, ["shell", "input", "keyevent", "4"], timeout=15)
        if ok:
            self.log(f"[{device}] Secuencia: teclado ocultado.")
        else:
            self.log(f"[{device}] Secuencia: no se pudo ocultar el teclado: {detail}")
        return ok

    @classmethod
    def sequence_media_type(cls, path):
        suffix = Path(path).suffix.casefold()
        if suffix in cls.SEQUENCE_IMAGE_EXTENSIONS:
            return "image"
        if suffix in cls.SEQUENCE_VIDEO_EXTENSIONS:
            return "video"
        return None

    def upload_media_to_device(self, device, local_path, media_type, stop_event):
        source = Path(local_path)
        if not source.is_file():
            self.log(f"[{device}] Secuencia: el archivo multimedia ya no existe: {source}")
            return "failed"
        detected_type = self.sequence_media_type(source)
        if detected_type != media_type:
            self.log(f"[{device}] Secuencia: el tipo del archivo multimedia no coincide; transferencia omitida.")
            return "failed"
        remote_directory = "/sdcard/Pictures/PanelCelulares" if media_type == "image" else "/sdcard/Movies/PanelCelulares"
        remote_path = f"{remote_directory}/{source.name}"
        ok, detail = self.run_on_device(device, ["shell", "mkdir", "-p", remote_directory], timeout=20)
        if not ok:
            self.log(f"[{device}] Secuencia: no se pudo preparar la carpeta multimedia: {detail}")
            return "failed"
        command = [self.adb, "-s", device, "push", str(source), remote_path]
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                creationflags=NO_WINDOW,
            )
            started = time.monotonic()
            while process.poll() is None:
                if self.app_closing.is_set() or stop_event.is_set():
                    process.terminate()
                    process.communicate(timeout=5)
                    self.log(f"[{device}] Secuencia: transferencia multimedia detenida.")
                    return "cancelled"
                if time.monotonic() - started > 600:
                    process.kill()
                    process.communicate(timeout=5)
                    self.log(f"[{device}] Secuencia: la transferencia multimedia excedió 10 minutos.")
                    return "failed"
                time.sleep(0.2)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                self.log(f"[{device}] Secuencia: no se pudo subir {source.name}: {(stderr or stdout).strip()}")
                return "failed"
        except Exception as error:
            self.log(f"[{device}] Secuencia: error al subir {source.name}: {error}")
            return "failed"
        scan_uri = "file://" + quote(remote_path, safe="/")
        scan_ok, scan_detail = self.run_on_device(
            device,
            ["shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", scan_uri],
            timeout=20,
        )
        if scan_ok:
            self.log(f"[{device}] Secuencia: {source.name} disponible en {remote_directory}.")
        else:
            self.log(
                f"[{device}] Secuencia: {source.name} fue copiado, pero Android no confirmó el registro multimedia: {scan_detail}"
            )
        return "sent"

    def open_url_on_device(self, device, url):
        """Reutiliza únicamente la apertura de liga empleada por Interacciones."""
        value = str(url or "").strip()
        parsed = urlparse(value)
        if len(value) > 2048 or parsed.scheme not in {"http", "https"} or not parsed.hostname:
            self.log(f"[{device}] Secuencia: la liga no es un URL HTTP/HTTPS válido; paso omitido.")
            return False
        ok, detail = self.run_on_device(
            device,
            ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", value, "com.facebook.lite"],
            timeout=20,
        )
        self.log(f"[{device}] Secuencia: liga abierta." if ok else f"[{device}] Secuencia: no se pudo abrir la liga: {detail}")
        return ok

    def inject_text_with_interval(self, device, text, minimum, maximum, stop_event):
        """Escribe carácter por carácter y permite cancelar entre cada entrada."""
        if not text:
            self.log(f"[{device}] Secuencia: el texto está vacío; paso omitido.")
            return "failed"
        needs_unicode = any(ord(character) > 127 for character in text)
        previous_ime = None
        adb_ime = None
        if needs_unicode:
            ok, ime_list = self.run_on_device(device, ["shell", "ime", "list", "-s"], timeout=15)
            if not ok:
                self.log(f"[{device}] Secuencia: no se pudo consultar el teclado Android: {ime_list}")
                return "failed"
            adb_ime = next(
                (line.strip() for line in ime_list.splitlines() if "com.android.adbkeyboard" in line.casefold()),
                None,
            )
            if not adb_ime:
                self.log(f"[{device}] Secuencia: ADB Keyboard es necesario para escribir Unicode letra por letra.")
                return "failed"
            ok, current_ime = self.run_on_device(
                device, ["shell", "settings", "get", "secure", "default_input_method"], timeout=15
            )
            if not ok:
                self.log(f"[{device}] Secuencia: no se pudo leer el teclado actual: {current_ime}")
                return "failed"
            previous_ime = current_ime.strip()
            ok, detail = self.run_on_device(device, ["shell", "ime", "set", adb_ime], timeout=15)
            if not ok:
                self.log(f"[{device}] Secuencia: no se pudo activar ADB Keyboard: {detail}")
                return "failed"
        try:
            for index, character in enumerate(text):
                if self.app_closing.is_set() or stop_event.is_set():
                    return "cancelled"
                if character in {"\r", "\n"}:
                    if character == "\r" and index + 1 < len(text) and text[index + 1] == "\n":
                        continue
                    ok, detail = self.run_on_device(device, ["shell", "input", "keyevent", "66"], timeout=15)
                elif needs_unicode:
                    payload = base64.b64encode(character.encode("utf-8")).decode("ascii")
                    ok, detail = self.run_on_device(
                        device, ["shell", "am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", payload], timeout=15
                    )
                else:
                    escaped = character.replace("\\", "\\\\").replace("%", "\\%").replace(" ", "%s")
                    if character in ('"', "'", "&", "<", ">", ";", "|", "(", ")", "$", "`", "!", "*", "?", "[", "]", "{", "}"):
                        escaped = "\\" + escaped
                    ok, detail = self.run_on_device(device, ["shell", "input", "text", escaped], timeout=15)
                if not ok:
                    self.log(f"[{device}] Secuencia: falló la escritura: {detail}")
                    return "failed"
                if index < len(text) - 1:
                    if self.wait_or_cancel(random.uniform(minimum, maximum), stop_event):
                        return "cancelled"
            self.log(f"[{device}] Secuencia: texto escrito ({len(text)} caracteres).")
            return "sent"
        finally:
            if needs_unicode and previous_ime and previous_ime != "null":
                self.run_on_device(device, ["shell", "ime", "set", previous_ime], timeout=15)

    def choose_sequence_wait_seconds(self, step):
        minimum = step["min_seconds"]
        maximum = step["max_seconds"]
        if minimum == maximum:
            return minimum
        if step.get("interval_step") == 0.5:
            minimum_tick = round(minimum * 2)
            maximum_tick = round(maximum * 2)
            return random.randint(minimum_tick, maximum_tick) / 2.0
        # Compatibilidad con secuencias guardadas antes de los saltos de 500 ms.
        return random.uniform(minimum, maximum)

    def sequence_execution_worker(self, devices, indexed_steps, previous_tasks):
        results = {}
        results_lock = threading.Lock()

        def run_device(device):
            try:
                device_result = self.sequence_device_worker(device, indexed_steps)
            except Exception as error:
                device_result = "con error"
                self.log(f"[{device}] Secuencia: el trabajador terminó con error: {error}")
            with results_lock:
                results[device] = device_result

        threads = [
            threading.Thread(target=run_device, args=(device,), daemon=True)
            for device in devices
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        if any(value == "con error" for value in results.values()):
            result = "con error"
        elif any(value == "detenida" for value in results.values()):
            result = "detenida"
        else:
            result = "completada"
        self.post_ui(
            lambda r=result, devs=list(devices), prev=previous_tasks: self.finish_sequence_execution(r, devs, prev)
        )

    def sequence_device_worker(self, device, indexed_steps):
        result = "completada"
        devices = [device]
        list_context = {device: {"items": [], "index": 0} for device in devices}
        try:
            for position, (original_index, step) in enumerate(indexed_steps, start=1):
                if self.sequence_stop_event.is_set() or self.app_closing.is_set():
                    result = "detenida"
                    break
                action, detail = self.sequence_step_description(step)
                self.post_ui(
                    lambda pos=position, total=len(indexed_steps), act=action: self.sequence_status_var.set(
                        f"Paso {pos} de {total}: {act}."
                    )
                )
                self.log(f"Secuencia · paso {original_index + 1}: {action} · {detail}")
                if step["type"] == "load_list":
                    for device in devices:
                        list_context[device] = {"items": list(step["items"]), "index": 0}
                    self.log(f"Secuencia: lista cargada con {len(step['items'])} renglones; elemento actual 1.")
                    continue
                if step["type"] == "next_list":
                    for device in devices:
                        context = list_context[device]
                        if not context["items"]:
                            self.log(f"[{device}] Secuencia: no hay una lista cargada; no se avanzó.")
                        elif context["index"] + 1 < len(context["items"]):
                            context["index"] += 1
                            self.log(
                                f"[{device}] Secuencia: lista avanzada al elemento "
                                f"{context['index'] + 1} de {len(context['items'])}."
                            )
                        else:
                            context["index"] = len(context["items"])
                            self.log(f"[{device}] Secuencia: se alcanzó el final de la lista.")
                    continue
                if step["type"] == "wait":
                    chosen_seconds = self.choose_sequence_wait_seconds(step)
                    self.log(
                        f"[{device}] Secuencia · paso {original_index + 1}: espera elegida {chosen_seconds:g} s "
                        f"dentro de {step['min_seconds']:g}–{step['max_seconds']:g} s."
                    )
                    self.post_ui(
                        lambda dev=device, pos=position, total=len(indexed_steps), chosen=chosen_seconds: self.sequence_status_var.set(
                            f"{self.display_device_name(dev)} · paso {pos} de {total}: espera de {chosen:g} s."
                        )
                    )
                    if self.wait_or_cancel(chosen_seconds, self.sequence_stop_event):
                        result = "detenida"
                        break
                    continue
                for device in devices:
                    if self.sequence_stop_event.is_set() or self.app_closing.is_set():
                        result = "detenida"
                        break
                    if step["type"] == "tap":
                        size = self.get_device_screen_size(device)
                        if not size:
                            self.log(f"[{device}] Secuencia: no se pudo leer la resolución; paso omitido.")
                            continue
                        x = min(size[0] - 1, max(0, round(step["x_ratio"] * size[0])))
                        y = min(size[1] - 1, max(0, round(step["y_ratio"] * size[1])))
                        ok, detail_result = self.run_on_device(
                            device, ["shell", "input", "tap", str(x), str(y)], timeout=15
                        )
                        self.log(
                            f"[{device}] Secuencia: toque ({x}, {y}) "
                            + ("ejecutado." if ok else f"falló: {detail_result}")
                        )
                    elif step["type"] == "swipe":
                        size = self.get_device_screen_size(device)
                        if not size:
                            self.log(f"[{device}] Secuencia: no se pudo leer la resolución; deslizamiento omitido.")
                            continue
                        start_x = min(size[0] - 1, max(0, round(step["start_x_ratio"] * size[0])))
                        start_y = min(size[1] - 1, max(0, round(step["start_y_ratio"] * size[1])))
                        end_x = min(size[0] - 1, max(0, round(step["end_x_ratio"] * size[0])))
                        end_y = min(size[1] - 1, max(0, round(step["end_y_ratio"] * size[1])))
                        ok, detail_result = self.run_on_device(
                            device,
                            [
                                "shell", "input", "touchscreen", "swipe",
                                str(start_x), str(start_y), str(end_x), str(end_y), str(step["duration_ms"]),
                            ],
                            timeout=15,
                        )
                        self.log(
                            f"[{device}] Secuencia: presión y deslizamiento "
                            f"({start_x}, {start_y}) → ({end_x}, {end_y}) "
                            + ("ejecutado." if ok else f"falló: {detail_result}")
                        )
                    elif step["type"] == "tap_text":
                        self.tap_visible_text(device, step["target_text"])
                    elif step["type"] == "tap_publish":
                        self.tap_visible_text(device, "Publicar")
                    elif step["type"] == "hide_keyboard":
                        self.hide_keyboard_if_visible(device)
                    elif step["type"] == "upload_media":
                        upload_result = self.upload_media_to_device(
                            device,
                            step["local_path"],
                            step["media_type"],
                            self.sequence_stop_event,
                        )
                        if upload_result == "cancelled":
                            result = "detenida"
                            break
                    elif step["type"] == "back":
                        ok, detail_result = self.run_on_device(
                            device, ["shell", "input", "keyevent", "4"], timeout=15
                        )
                        self.log(
                            f"[{device}] Secuencia: Atrás "
                            + ("ejecutado." if ok else f"falló: {detail_result}")
                        )
                    elif step["type"] == "text":
                        text_value = (
                            self.sequence_list_value(list_context, device)
                            if step["source"] == "list"
                            else step["text"]
                        )
                        if text_value is None:
                            self.log(f"[{device}] Secuencia: no existe un elemento actual de lista para escribir.")
                            continue
                        text_result = self.inject_text_with_interval(
                            device,
                            text_value,
                            step["char_min_seconds"],
                            step["char_max_seconds"],
                            self.sequence_stop_event,
                        )
                        if text_result == "cancelled":
                            result = "detenida"
                            break
                    elif step["type"] == "open_url":
                        url_value = (
                            self.sequence_list_value(list_context, device)
                            if step["source"] == "list"
                            else step["url"]
                        )
                        if url_value is None:
                            self.log(f"[{device}] Secuencia: no existe un elemento actual de lista para abrir.")
                            continue
                        self.open_url_on_device(device, url_value)
                    elif step["type"] == "warmup":
                        if not self.simular_navegacion_organica(
                            device,
                            step["min_seconds"],
                            step["max_seconds"],
                            self.sequence_stop_event,
                        ):
                            if self.sequence_stop_event.is_set() or self.app_closing.is_set():
                                result = "detenida"
                                break
                if result == "detenida":
                    break
        except Exception as error:
            result = "con error"
            self.log(f"[{device}] Secuencia: error inesperado: {error}")
        return result

    def finish_sequence_execution(self, result, devices, previous_tasks):
        self.sequence_running = False
        self.btn_sequence_step.config(state="normal")
        self.btn_sequence_all.config(state="normal")
        self.btn_sequence_stop.config(state="disabled")
        self.sequence_status_var.set(f"Secuencia {result}.")
        for device in devices:
            self.restore_device_task(device, "Secuencia de acciones", previous_tasks.get(device))
            self.release_device(device)

    def stop_sequence_execution(self):
        if not self.sequence_running:
            return
        self.sequence_stop_event.set()
        self.sequence_status_var.set("Deteniendo secuencia...")

    def create_console_widget(self):
        self.console_frame = tk.Frame(self.root, bg="#17233a", highlightthickness=0)
        self.console_frame.pack(side="bottom", fill="x", padx=12, pady=(0, 10))
        console_header = tk.Frame(self.console_frame, bg="#17233a", height=34)
        console_header.pack(fill="x")
        tk.Label(console_header, text="Registro de actividad", bg="#17233a", fg="white",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=12, pady=7)
        self.console_visible = True
        self.console_toggle_button = tk.Button(
            console_header, text="Ocultar", command=self.toggle_console,
            bg="#17233a", fg="#bcd0ea", activebackground="#23426d", activeforeground="white",
            relief="flat", bd=0, font=("Segoe UI", 8, "bold"), cursor="hand2"
        )
        self.console_toggle_button.pack(side="right", padx=10)
        self.console_body = tk.Frame(self.console_frame, bg="#101827")
        self.console_body.pack(fill="x")
        self.console = scrolledtext.ScrolledText(
            self.console_body, bg="#101827", fg="#8ee6a8", font=("Consolas", 9),
            insertbackground="white", height=5, relief="flat", bd=0
        )
        self.console.pack(fill="x", padx=10, pady=(3, 9))

    def toggle_console(self):
        if self.console_visible:
            self.console_body.pack_forget()
            self.console_toggle_button.configure(text="Mostrar")
        else:
            self.console_body.pack(fill="x")
            self.console_toggle_button.configure(text="Ocultar")
        self.console_visible = not self.console_visible

    def _drain_ui_queue(self):
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                if kind == "log":
                    self.console.insert(tk.END, payload + "\n")
                    self.console.see(tk.END)
                    self.route_device_log(payload)
                elif kind == "call":
                    payload()
        except queue.Empty: pass
        except tk.TclError: return
        if not self.app_closing.is_set(): self.root.after(100, self._drain_ui_queue)

    def post_ui(self, callback): self.ui_queue.put(("call", callback))
    def log(self, message): self.ui_queue.put(("log", str(message)))

    def on_close(self):
        self.app_closing.set()
        self.interaction_stop_event.set()
        self.search_stop_event.set()
        self.human_stop_event.set()
        self.report_stop_event.set()
        self.sequence_stop_event.set()
        for p in list(self.scrcpy_processes.values()):
            try: p.terminate()
            except: pass
        for window in list(self.device_log_windows.values()):
            try: window.destroy()
            except: pass
        self.root.destroy()

    def get_selected_devices(self):
        if not hasattr(self, "device_table"): return []
        return [s for s in self.device_table.selection() if s in self.devices]

    def select_all_devices(self):
        if self.devices: self.device_table.selection_set(self.devices)
        self.update_selection_label()

    def clear_device_selection(self):
        self.device_table.selection_remove(self.device_table.selection())
        self.update_selection_label()

    def update_selection_label(self, _e=None):
        selected = len(self.get_selected_devices())
        connected = len(self.devices)
        self.lbl_selection.config(text=f"Seleccionados: {selected} de {connected}")
        if hasattr(self, "header_device_var"):
            self.header_device_var.set(f"{connected} conectados  ·  {selected} seleccionados")

    def display_device_name(self, serial):
        return self.device_aliases.get(serial) or self.device_details.get(serial, {}).get("model") or serial

    def rename_selected_device(self):
        selected = self.get_selected_devices()
        if len(selected) != 1: return
        serial = selected[0]
        alias = simpledialog.askstring("Nombre", "Alias:", initialvalue=self.device_aliases.get(serial, ""), parent=self.root)
        if alias is not None:
            if alias.strip(): self.device_aliases[serial] = alias.strip()
            else: self.device_aliases.pop(serial, None)
            self.save_device_aliases()
            self.update_device_row(serial)

    def query_device_details(self, serial):
        try:
            output = self.adb_capture(serial, ["shell", "getprop ro.product.model; getprop ro.build.version.release"])
            vals = [v.strip() for v in output.splitlines() if v.strip()]
            return {"model": vals[0] if vals else "Android", "android": vals[1] if len(vals)>1 else "", "state": "Conectado"}
        except: return {"model": "Android", "android": "", "state": "Error"}

    def update_device_row(self, serial):
        if not hasattr(self, "device_table") or not self.device_table.exists(serial): return
        det = self.device_details.get(serial, {})
        task = self.device_tasks.get(serial, "Listo")
        self.device_table.item(serial, values=(self.device_aliases.get(serial, ""), det.get("model", ""), serial, det.get("android", ""), det.get("state", ""), task))
        status_var = self.device_log_status_vars.get(serial)
        if status_var is not None:
            status_var.set(f"Tarea actual: {task}")

    def set_device_task(self, serial, task):
        self.device_tasks[serial] = task
        self.post_ui(lambda dev=serial: self.update_device_row(dev))

    def restore_device_task(self, serial, expected_task, previous_task):
        if self.device_tasks.get(serial) == expected_task:
            if previous_task: self.device_tasks[serial] = previous_task
            else: self.device_tasks.pop(serial, None)
            self.update_device_row(serial)

    def get_devices(self):
        try:
            res = subprocess.run([self.adb, "devices"], capture_output=True, text=True, errors="replace", check=True, creationflags=NO_WINDOW)
            devices = []
            for line in res.stdout.strip().split("\n")[1:]:
                if "\t" in line:
                    serial, state = line.split("\t")
                    if state == "device":
                        devices.append(serial)
            return devices
        except Exception:
            return []

    def refresh_devices_async(self):
        threading.Thread(target=self._refresh_devices_worker, daemon=True).start()

    def _refresh_devices_worker(self):
        new_devices = self.get_devices()
        new_details = {s: self.query_device_details(s) for s in new_devices}
        def update_ui():
            prev_sel = set(self.get_selected_devices())
            self.devices, self.device_details = new_devices, new_details
            for s in set(self.device_table.get_children()) - set(self.devices):
                self.device_table.delete(s)
            for s in self.devices:
                if not self.device_table.exists(s): self.device_table.insert("", "end", iid=s)
                self.update_device_row(s)
            sel = [s for s in self.devices if s in prev_sel]
            if self.first_device_scan and self.devices: sel = list(self.devices)
            if sel: self.device_table.selection_set(sel)
            self.first_device_scan = False
            self.lbl_devices.config(text=f"Dispositivos detectados: {len(self.devices)}")
            self.update_selection_label()
        self.post_ui(update_ui)

    def run_on_device(self, device, command, timeout=60):
        try:
            res = subprocess.run([self.adb, "-s", device] + command, capture_output=True, text=True, errors="replace", timeout=timeout, creationflags=NO_WINDOW)
            if res.returncode != 0: return False, (res.stderr or res.stdout or f"Error").strip()
            return True, res.stdout.strip()
        except Exception as e: return False, str(e)

    def adb_capture(self, device, command, timeout=30):
        res = subprocess.run([self.adb, "-s", device] + command, capture_output=True, text=True, errors="replace", timeout=timeout, creationflags=NO_WINDOW)
        if res.returncode != 0: raise RuntimeError((res.stderr or res.stdout).strip())
        return res.stdout

    def execute_multithreaded(self, task_func, task_name="Tarea"):
        target_devs = self.get_selected_devices()
        if not target_devs: return messagebox.showwarning("Aviso", "Selecciona al menos un dispositivo.")
        for dev in target_devs:
            def run(d=dev):
                prev = self.device_tasks.get(d)
                self.set_device_task(d, task_name)
                try: task_func(d)
                finally: self.post_ui(lambda x=d, p=prev: self.restore_device_task(x, task_name, p))
            threading.Thread(target=run, daemon=True).start()

    def claim_devices(self, devices, task_name):
        """Evita que dos acciones controlen el mismo teléfono al mismo tiempo."""
        with self.device_tasks_lock:
            available = [device for device in devices if device not in self.busy_devices]
            busy = [device for device in devices if device in self.busy_devices]
            self.busy_devices.update(available)
        if busy:
            self.log(f"{task_name}: se omitieron equipos ocupados: {', '.join(busy)}")
        return available, busy

    def release_device(self, device):
        with self.device_tasks_lock:
            self.busy_devices.discard(device)

    def is_facebook_url(self, value):
        parsed = urlparse(value)
        host = parsed.hostname.casefold() if parsed.hostname else ""
        allowed_hosts = ("facebook.com", "fb.com", "fb.watch")
        return (
            parsed.scheme in {"http", "https"}
            and any(host == allowed or host.endswith("." + allowed) for allowed in allowed_hosts)
        )

    def wait_or_cancel(self, seconds, stop_event=None):
        deadline = time.monotonic() + max(0.0, seconds)
        while True:
            if self.app_closing.is_set() or (stop_event and stop_event.is_set()):
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            event = stop_event or self.app_closing
            event.wait(min(remaining, 0.20))

    def get_device_screen_size(self, device):
        size = self.screen_size_cache.get(device)
        if size:
            return size
        try:
            output = self.adb_capture(device, ["shell", "wm", "size"], timeout=10)
            matches = re.findall(r"(\d+)x(\d+)", output)
            if not matches:
                raise RuntimeError("Android no informó el tamaño de pantalla.")
            size = tuple(map(int, matches[-1]))
            self.screen_size_cache[device] = size
            return size
        except Exception as error:
            self.log(f"[{device}] No se pudo leer el tamaño de pantalla: {error}")
            return None

    def route_device_log(self, message):
        for serial in self.devices:
            if f"[{serial}]" in message or message.endswith(f": {serial}"):
                self.append_device_log(serial, message)
                break

    def append_device_log(self, device, message):
        widget = self.device_log_texts.get(device)
        if widget is None or not widget.winfo_exists():
            return
        widget.config(state="normal")
        widget.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        line_count = int(widget.index("end-1c").split(".")[0])
        if line_count > 400:
            widget.delete("1.0", f"{line_count - 350}.0")
        widget.see(tk.END)
        widget.config(state="disabled")

    def open_device_log_window(self, device, x, y, width, height):
        existing = self.device_log_windows.get(device)
        if existing is not None and existing.winfo_exists():
            existing.geometry(f"{width}x{height}+{x}+{y}")
            existing.deiconify()
            existing.lift()
            return

        window = tk.Toplevel(self.root)
        window.title(f"Log — {self.display_device_name(device)} [{device}]")
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.minsize(300, 110)

        header = ttk.Frame(window, padding=(8, 5))
        header.pack(fill="x")
        ttk.Label(
            header,
            text=f"{self.display_device_name(device)}  ·  {device}",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        ttk.Button(
            header,
            text="Cerrar pantalla",
            command=lambda dev=device: self.close_device_screen(dev),
        ).pack(side="right")

        status_var = tk.StringVar(value=f"Tarea actual: {self.device_tasks.get(device, 'Listo')}")
        ttk.Label(window, textvariable=status_var, foreground="#1d5f91").pack(fill="x", padx=8)
        log_text = scrolledtext.ScrolledText(
            window,
            bg="#1e1e1e",
            fg="#58e36b",
            font=("Consolas", 8),
            height=5,
            state="disabled",
        )
        log_text.pack(fill="both", expand=True, padx=6, pady=(3, 6))

        self.device_log_windows[device] = window
        self.device_log_texts[device] = log_text
        self.device_log_status_vars[device] = status_var
        window.protocol("WM_DELETE_WINDOW", lambda dev=device: self.close_device_screen(dev))
        self.append_device_log(device, f"[{device}] Monitor individual preparado.")

    def close_device_log_window(self, device):
        window = self.device_log_windows.pop(device, None)
        self.device_log_texts.pop(device, None)
        self.device_log_status_vars.pop(device, None)
        if window is not None:
            try:
                if window.winfo_exists():
                    window.destroy()
            except tk.TclError:
                pass

    def screen_layout(self, device_count):
        screen_width = max(800, self.root.winfo_screenwidth())
        screen_height = max(600, self.root.winfo_screenheight() - 45)
        margin = 8
        preferred_width = 420
        max_columns = max(1, screen_width // (preferred_width + margin))
        columns = min(device_count, max_columns)
        rows = max(1, math.ceil(device_count / columns))
        cell_width = min(preferred_width, (screen_width - margin * (columns + 1)) // columns)
        total_width = columns * cell_width + (columns - 1) * margin
        origin_x = max(margin, (screen_width - total_width) // 2)
        cell_height = max(360, (screen_height - margin * (rows + 1)) // rows)
        log_height = max(120, min(185, int(cell_height * 0.24)))
        phone_height = max(220, cell_height - log_height - 38)
        return origin_x, margin, columns, cell_width, cell_height, phone_height, log_height, margin

    def align_device_log_to_screen(self, device, screen_title, log_title, log_height, proc):
        if os.name != "nt":
            return
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            for _ in range(30):
                if self.app_closing.is_set() or proc.poll() is not None:
                    return
                screen_handle = user32.FindWindowW(None, screen_title)
                log_handle = user32.FindWindowW(None, log_title)
                if screen_handle and log_handle:
                    rect = wintypes.RECT()
                    if user32.GetWindowRect(screen_handle, ctypes.byref(rect)):
                        width = max(300, rect.right - rect.left)
                        user32.MoveWindow(
                            log_handle,
                            rect.left,
                            rect.bottom,
                            width,
                            log_height,
                            True,
                        )
                        self.log(
                            f"[{device}] Log alineado debajo de la pantalla con ancho real de {width}px."
                        )
                        return
                time.sleep(0.20)
            self.log(f"[{device}] No se pudo confirmar la alineación exacta del log.")
        except Exception as error:
            self.log(f"[{device}] Error al alinear el log individual: {error}")

    def open_all_screens(self):
        if not self.devices:
            return messagebox.showwarning("Aviso", "No hay celulares conectados.")
        self.device_table.selection_set(self.devices)
        self.update_selection_label()
        self.open_selected_screens()

    def open_selected_screens(self):
        devs = self.get_selected_devices()
        if not devs:
            return messagebox.showwarning("Aviso", "Selecciona al menos un celular.")
        if not self.scrcpy:
            return messagebox.showerror("Error", "No se encontró scrcpy en la carpeta herramientas.")
        origin_x, origin_y, cols, cell_w, cell_h, phone_h, log_h, margin = self.screen_layout(len(devs))
        for i, dev in enumerate(devs):
            column, row = i % cols, i // cols
            x = origin_x + column * (cell_w + margin)
            y = origin_y + row * cell_h
            log_y = y + phone_h + 30
            screen_title = f"{self.display_device_name(dev)} [{dev}]"
            log_title = f"Log — {self.display_device_name(dev)} [{dev}]"
            existing = self.scrcpy_processes.get(dev)
            if existing is not None and existing.poll() is None:
                self.scrcpy_processes.pop(dev, None)
                existing.terminate()
                try: existing.wait(timeout=2)
                except Exception: pass
            self.open_device_log_window(dev, x, log_y, cell_w, log_h)
            cmd = [
                self.scrcpy,
                "-s", dev,
                "--window-title", screen_title,
                f"--window-x={x}",
                f"--window-y={y}",
                f"--window-width={cell_w}",
                f"--window-height={phone_h}",
                "--max-size=600",
                "--max-fps=20",
                "--video-bit-rate=1M",
                "--no-audio",
            ]
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(Path(self.scrcpy).parent),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                    bufsize=1,
                    creationflags=NO_WINDOW,
                )
                self.scrcpy_processes[dev] = proc
                self.set_device_task(dev, "Pantalla abierta")
                self.log(f"[{dev}] Pantalla abierta sin consola CMD; log individual activo.")
                threading.Thread(target=self.monitor_scrcpy_process, args=(dev, proc), daemon=True).start()
                threading.Thread(
                    target=self.align_device_log_to_screen,
                    args=(dev, screen_title, log_title, log_h, proc),
                    daemon=True,
                ).start()
            except Exception as e:
                self.log(f"[{dev}] Error al abrir scrcpy: {e}")
                self.close_device_log_window(dev)

    def monitor_scrcpy_process(self, dev, proc):
        try:
            if proc.stdout is not None:
                for line in proc.stdout:
                    line = line.strip()
                    if line:
                        self.log(f"[{dev}] scrcpy: {line}")
        except Exception as error:
            self.log(f"[{dev}] No se pudo leer el estado de scrcpy: {error}")
        return_code = proc.wait()
        if self.scrcpy_processes.get(dev) is proc:
            self.scrcpy_processes.pop(dev, None)
            self.log(f"[{dev}] Pantalla cerrada (código {return_code}).")
            self.post_ui(lambda d=dev: self.restore_device_task(d, "Pantalla abierta", None))
            self.post_ui(lambda d=dev: self.close_device_log_window(d))

    def close_device_screen(self, dev):
        proc = self.scrcpy_processes.get(dev)
        if proc is not None and proc.poll() is None:
            proc.terminate()
        else:
            self.scrcpy_processes.pop(dev, None)
            self.close_device_log_window(dev)
            self.restore_device_task(dev, "Pantalla abierta", None)

    def close_selected_screens(self):
        for dev in self.get_selected_devices():
            self.close_device_screen(dev)

    def close_all_screens(self):
        for dev in list(set(self.scrcpy_processes) | set(self.device_log_windows)):
            self.close_device_screen(dev)

    def open_facebook_all(self):
        def task(dev):
            for pkg in ["com.facebook.lite", "com.facebook.katana"]:
                res = subprocess.run([self.adb, "-s", dev, "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
                if res.returncode == 0 and "Error" not in res.stdout:
                    self.log(f"-> Facebook abierto en: {dev}"); return
            self.log(f"-> No se pudo abrir Facebook en {dev}")
        self.execute_multithreaded(task, "Abrir Facebook")

    def simular_navegacion_organica(self, device, duracion_min_sec=5.0, duracion_max_sec=15.0, stop_event=None):
        duration = random.uniform(duracion_min_sec, duracion_max_sec)
        end_time = time.time() + duration
        self.log(f"[{device}] ☕ Calentamiento orgánico en Feed ({duration:.1f}s)...")
        size = self.screen_size_cache.get(device)
        if not size:
            try: o = self.adb_capture(device, ["shell", "wm", "size"], timeout=10); size = self.screen_size_cache[device] = tuple(map(int, re.findall(r"(\d+)x(\d+)", o)[-1]))
            except Exception: size = (1080, 1920)
        w, h = size
        while time.time() < end_time and not self.app_closing.is_set() and not (stop_event and stop_event.is_set()):
            accion = random.choice(["scroll_abajo", "scroll_arriba", "pausa_lectura"])
            if accion == "scroll_abajo":
                self.scroll_device_once_random(device)
                if self.wait_or_cancel(random.uniform(1.5, 3.5), stop_event): return False
            elif accion == "scroll_arriba":
                cx, sy, ey = (w // 2) + random.randint(-40, 40), int(h * 0.30), int(h * 0.70)
                self.run_on_device(device, ["shell", "input", "swipe", str(cx), str(sy), str(cx), str(ey), str(random.randint(400, 600))])
                if self.wait_or_cancel(random.uniform(1.8, 3.8), stop_event): return False
            elif accion == "pausa_lectura":
                if self.wait_or_cancel(random.uniform(2.5, 5.0), stop_event): return False
        self.log(f"[{device}] ✓ Calentamiento completado.")
        return not self.app_closing.is_set() and not (stop_event and stop_event.is_set())

    def scroll_device_once_random(self, dev):
        size = self.screen_size_cache.get(dev)
        if not size:
            try: o = self.adb_capture(dev, ["shell", "wm", "size"], timeout=10); size = self.screen_size_cache[dev] = tuple(map(int, re.findall(r"(\d+)x(\d+)", o)[-1]))
            except Exception: size = (1080, 1920)
        w, h = size
        cx = (w // 2) + random.randint(-28, 28)
        sy = int(h * (0.78 + random.uniform(-0.02, 0.02)))
        ey = int(h * (0.25 + random.uniform(-0.02, 0.02)))
        # Un gesto breve y amplio evita que Facebook interprete el final como toque
        # o pulsación prolongada sobre una tarjeta, enlace o anuncio.
        self.run_on_device(
            dev,
            ["shell", "input", "touchscreen", "swipe", str(cx), str(sy), str(cx), str(ey), str(random.randint(210, 300))],
        )

    @staticmethod
    def normalize_search_text(value): return "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c))

    def prepare_search_terms(self, keys):
        """Normaliza cada alternativa que el usuario separó explícitamente."""
        prepared = []
        for original in keys:
            normalized = re.sub(r"\s+", " ", self.normalize_search_text(original)).strip()
            if normalized and normalized not in {item[1] for item in prepared}:
                prepared.append((original.strip(), normalized))
        return dict(prepared)

    @staticmethod
    def phrase_matches_text(normalized_phrase, normalized_text):
        if not normalized_phrase or not normalized_text:
            return False
        phrase_pattern = re.escape(normalized_phrase).replace(r"\ ", r"\s+")
        return bool(re.search(r"(?<!\w)" + phrase_pattern + r"(?!\w)", normalized_text))

    def get_android_hierarchy(self, device):
        safe_device = re.sub(r"[^A-Za-z0-9_.-]", "_", device)
        remote_xml = f"/sdcard/window_dump_panel_{safe_device}.xml"
        with self.uiautomator_lock:
            self.adb_capture(device, ["shell", "uiautomator", "dump", remote_xml], timeout=20)
            xml = self.adb_capture(device, ["exec-out", "cat", remote_xml], timeout=20)
        if xml:
            try: return ET.fromstring(xml)
            except: pass
        return None

    def extract_visible_text(self, hierarchy):
        parts = []
        for n in hierarchy.iter("node"):
            for attr in ("text", "content-desc"):
                val = n.attrib.get(attr, "").strip()
                if val: parts.append(val)
        return "\n".join(dict.fromkeys(parts))

    def accessibility_text_records(self, hierarchy):
        records = []
        seen = set()
        if hierarchy is None:
            return records
        for node in hierarchy.iter("node"):
            bounds = self.parse_node_bounds(node)
            if not bounds:
                continue
            for attribute in ("text", "content-desc"):
                value = node.attrib.get(attribute, "").strip()
                key = (value, bounds)
                if not value or key in seen:
                    continue
                seen.add(key)
                records.append({
                    "text": value,
                    "bounds": bounds,
                    "source": "accessibility",
                    "class": node.attrib.get("class", ""),
                    "editable": node.attrib.get("editable", "false").casefold() == "true",
                })
        return records

    def windows_ocr_records(self, device):
        if not OPENCV_AVAILABLE:
            return []
        screen = self.capture_device_screen(device)
        if screen is None:
            return []
        script_path = RESOURCE_DIR / "herramientas" / "ocr_windows.ps1"
        if not script_path.exists():
            return []
        temp_path = None
        try:
            handle = tempfile.NamedTemporaryFile(prefix="panel_ocr_", suffix=".png", delete=False)
            temp_path = handle.name
            handle.close()
            if not cv2.imwrite(temp_path, screen):
                return []
            result = subprocess.run(
                [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(script_path), "-ImagePath", temp_path,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=25,
                creationflags=NO_WINDOW,
            )
            if result.returncode != 0 or not result.stdout.strip():
                if not self.ocr_warning_shown:
                    self.ocr_warning_shown = True
                    self.log(f"OCR local no disponible: {(result.stderr or result.stdout).strip()}")
                return []
            payload = json.loads(result.stdout)
            if isinstance(payload, dict):
                payload = [payload]
            records = []
            for item in payload:
                text_value = str(item.get("text", "")).strip()
                bounds = tuple(int(item[name]) for name in ("left", "top", "right", "bottom"))
                if text_value and bounds[2] > bounds[0] and bounds[3] > bounds[1]:
                    words = []
                    for word in item.get("words", []):
                        word_text = str(word.get("text", "")).strip()
                        word_bounds = tuple(int(word[name]) for name in ("left", "top", "right", "bottom"))
                        if word_text and word_bounds[2] > word_bounds[0] and word_bounds[3] > word_bounds[1]:
                            words.append({"text": word_text, "bounds": word_bounds})
                    records.append({"text": text_value, "bounds": bounds, "source": "ocr", "words": words})
            return records
        except Exception as error:
            if not self.ocr_warning_shown:
                self.ocr_warning_shown = True
                self.log(f"OCR local no disponible: {error}")
            return []
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def hierarchy_timestamp_records(self, hierarchy, screen_size):
        """Recupera la fila de fecha por geometría cuando Facebook oculta su texto."""
        if hierarchy is None or not screen_size:
            return []
        width, height = screen_size
        nodes = list(hierarchy.iter("node"))
        records = []
        for header in nodes:
            if header.attrib.get("clickable", "false").casefold() != "true":
                continue
            bounds = self.parse_node_bounds(header)
            if not bounds:
                continue
            left, top, right, bottom = bounds
            box_width, box_height = right - left, bottom - top
            if not width * 0.12 <= left <= width * 0.25:
                continue
            if not width * 0.45 <= box_width <= width * 0.76:
                continue
            if not height * 0.045 <= box_height <= height * 0.16:
                continue
            candidates = []
            for node in nodes:
                if node.attrib.get("class", "") != "android.view.View":
                    continue
                if node.attrib.get("clickable", "false").casefold() == "true":
                    continue
                if node.attrib.get("text", "").strip() or node.attrib.get("content-desc", "").strip():
                    continue
                child = self.parse_node_bounds(node)
                if not child:
                    continue
                c_left, c_top, c_right, c_bottom = child
                child_width, child_height = c_right - c_left, c_bottom - c_top
                if not (left <= c_left and c_right <= right and top <= c_top and c_bottom <= bottom):
                    continue
                if abs(c_left - left) > width * 0.035:
                    continue
                if c_top < top + box_height * 0.45:
                    continue
                if not width * 0.08 <= child_width <= width * 0.25:
                    continue
                if not height * 0.015 <= child_height <= height * 0.04:
                    continue
                candidates.append(child)
            if not candidates:
                continue
            candidates.sort(key=lambda item: item[1], reverse=True)
            timestamp_bounds = candidates[0]
            key = (timestamp_bounds[0], timestamp_bounds[1], timestamp_bounds[2], timestamp_bounds[3])
            if any(record["bounds"] == key for record in records):
                continue
            records.append({
                "text": "[fecha/hora visual]",
                "bounds": key,
                "source": "estructura geométrica",
                "timestamp_candidate": True,
            })
        return records

    def find_see_more_controls(self, records, screen_size):
        if not records or not screen_size:
            return []
        width, height = screen_size
        excluded = ("comentario", "respuesta", "resultado", "grupo", "persona", "traduccion")
        controls = []
        for record in records:
            text_value = self.normalize_search_text(record.get("text", "")).strip()
            bounds = record.get("bounds")
            if not bounds or "ver mas" not in text_value:
                continue
            if any(term in text_value for term in excluded):
                continue
            if not re.search(r"(?:\.{2,}\s*)?ver mas\s*$", text_value):
                continue
            left, top, right, bottom = bounds
            center_y = (top + bottom) // 2
            if not height * 0.16 <= center_y <= height * 0.90:
                continue
            if self.has_ad_label_above(records, center_y, height, max_distance_ratio=0.22):
                continue
            point = None
            words = record.get("words", [])
            for index in range(len(words) - 1, 0, -1):
                current = self.normalize_search_text(words[index].get("text", "")).strip(". ")
                previous = self.normalize_search_text(words[index - 1].get("text", "")).strip(". ")
                if current == "mas" and previous == "ver":
                    p_bounds = words[index - 1]["bounds"]
                    c_bounds = words[index]["bounds"]
                    point = ((p_bounds[0] + c_bounds[2]) // 2, (min(p_bounds[1], c_bounds[1]) + max(p_bounds[3], c_bounds[3])) // 2)
                    break
            if point is None:
                if text_value in {"ver mas", "... ver mas", "… ver mas"}:
                    point = ((left + right) // 2, center_y)
                else:
                    point = (max(left, right - min(50, max(18, (right - left) // 10))), center_y)
            controls.append({"point": point, "text": record["text"], "source": record.get("source", "unknown")})
        controls.sort(key=lambda item: item["point"][1])
        return controls

    def is_ad_label_record(self, record):
        text_value = self.normalize_search_text(record.get("text", "")).strip()
        bounds = record.get("bounds")
        if not text_value or not bounds or len(text_value) > 32:
            return False
        return bool(re.match(
            r"^(?:publicidad|patrocinad[oa]|sponsored|anuncio|advertisement)(?:\s|[·•.]|$)",
            text_value,
        ))

    def is_open_post_view(self, records, screen_size):
        """Detecta una publicación abierta fuera del flujo de coincidencia validada."""
        if not records or not screen_size:
            return False
        _, height = screen_size
        top_text = []
        bottom_editor = False
        comment_action_count = 0
        for record in records:
            bounds = record.get("bounds")
            if not bounds:
                continue
            text_value = self.normalize_search_text(record.get("text", "")).strip()
            if not text_value:
                continue
            center_y = (bounds[1] + bounds[3]) / 2.0
            if center_y <= height * 0.16:
                top_text.append(text_value)
            if center_y >= height * 0.84 and any(label in text_value for label in (
                "escribe un comentario", "comenta como", "write a comment", "comment as",
            )):
                bottom_editor = True
            if any(label in text_value for label in ("responder", "reply")):
                comment_action_count += 1
        header = " ".join(top_text)
        explicit_header = bool(re.search(r"\b(?:publicacion|post)\s+de\b", header))
        # El editor inferior sólo aparece cuando una publicación está abierta.
        # Algunas variantes de FB Lite omiten el título "Publicación de" y todavía
        # no muestran comentarios, por lo que no exigimos varios botones Responder.
        return explicit_header or bottom_editor or comment_action_count >= 2

    def find_open_post_back_control(self, hierarchy, screen_size, ocr_records=None):
        """Localiza el `<` superior de una publicación sin confundirlo con el feed."""
        if hierarchy is None or not screen_size:
            return None
        width, height = screen_size
        candidates = []
        back_labels = (
            "atras", "volver", "regresar", "back", "navigate up", "ir atras",
        )
        back_glyphs = {"<", "‹", "〈", "←"}
        for node in hierarchy.iter("node"):
            if node.attrib.get("visible-to-user", "true").casefold() == "false":
                continue
            if node.attrib.get("enabled", "true").casefold() == "false":
                continue
            bounds = self.parse_node_bounds(node)
            if not bounds:
                continue
            left, top, right, bottom = bounds
            center = ((left + right) // 2, (top + bottom) // 2)
            if not (center[0] <= width * 0.18 and height * 0.025 <= center[1] <= height * 0.14):
                continue
            if right - left > width * 0.24 or bottom - top > height * 0.13:
                continue
            labels = self.normalized_node_labels(node)
            labeled_back = any(
                label in back_glyphs or any(term == label or term in label for term in back_labels)
                for label in labels
            )
            clickable = node.attrib.get("clickable", "false").casefold() == "true"
            # FB Lite suele exponer la flecha como un ViewGroup sin texto:
            # en ese caso se acepta únicamente el botón pequeño, clicable y pegado
            # al borde superior izquierdo de una publicación ya confirmada.
            geometric_back = (
                clickable
                and left <= width * 0.04
                and right <= width * 0.22
                and (right - left) >= width * 0.055
                and (bottom - top) >= height * 0.025
            )
            if labeled_back or geometric_back:
                priority = 0 if labeled_back else 2
                candidates.append((priority, center[0], center[1], center, "accesibilidad" if labeled_back else "geometría"))

        for record in ocr_records or []:
            bounds = record.get("bounds")
            label = self.normalize_search_text(record.get("text", "")).strip()
            if not bounds or label not in back_glyphs:
                continue
            left, top, right, bottom = bounds
            center = ((left + right) // 2, (top + bottom) // 2)
            if center[0] <= width * 0.18 and height * 0.025 <= center[1] <= height * 0.14:
                candidates.append((1, center[0], center[1], center, "OCR"))

        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        _, _, _, point, source = candidates[0]
        return {"point": point, "source": source}

    def is_open_post_hierarchy(self, hierarchy, screen_size):
        """Confirma el diseño de publicación aun si FB Lite oculta sus textos."""
        if hierarchy is None or not screen_size:
            return False
        _, height = screen_size
        if not self.find_open_post_back_control(hierarchy, screen_size):
            return False
        for node in hierarchy.iter("node"):
            class_name = node.attrib.get("class", "").casefold()
            if "edittext" not in class_name and "autocompletetextview" not in class_name:
                continue
            bounds = self.parse_node_bounds(node)
            if bounds and (bounds[1] + bounds[3]) / 2.0 >= height * 0.82:
                return True
        return False

    def is_facebook_feed_hierarchy(self, hierarchy, screen_size):
        """Reconoce la fila de pestañas del feed para no pulsar un falso Atrás."""
        if hierarchy is None or not screen_size:
            return False
        width, height = screen_size
        tabs = []
        for node in hierarchy.iter("node"):
            if node.attrib.get("clickable", "false").casefold() != "true":
                continue
            bounds = self.parse_node_bounds(node)
            if not bounds:
                continue
            left, top, right, bottom = bounds
            box_width = right - left
            center_y = (top + bottom) / 2.0
            if (
                height * 0.075 <= center_y <= height * 0.19
                and width * 0.12 <= box_width <= width * 0.24
                and bottom - top <= height * 0.11
            ):
                tabs.append((left, right))
        tabs.sort()
        distinct = []
        for bounds in tabs:
            if not distinct or bounds[0] - distinct[-1][0] >= width * 0.08:
                distinct.append(bounds)
        return len(distinct) >= 4

    def looks_like_left_chevron(self, screen, bounds):
        """Valida visualmente dos diagonales que convergen como un símbolo `<`."""
        if not OPENCV_AVAILABLE or screen is None or not bounds:
            return False
        height, width = screen.shape[:2]
        left, top, right, bottom = bounds
        pad_x = max(3, int((right - left) * 0.08))
        pad_y = max(3, int((bottom - top) * 0.08))
        x1, x2 = max(0, left - pad_x), min(width, right + pad_x)
        y1, y2 = max(0, top - pad_y), min(height, bottom + pad_y)
        crop = screen[y1:y2, x1:x2]
        if crop.size == 0:
            return False
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        # El chevrón de navegación está dibujado sobre un fondo mayormente claro.
        # Este filtro elimina avatares y fotografías que también contienen muchas
        # diagonales y podrían parecer un `<` por pura geometría.
        dark_ratio = float(np.count_nonzero(gray < 160)) / float(gray.size)
        bright_ratio = float(np.count_nonzero(gray > 220)) / float(gray.size)
        if dark_ratio > 0.22 or bright_ratio < 0.58:
            return False
        edges = cv2.Canny(gray, 25, 100)
        crop_h, crop_w = gray.shape[:2]
        min_length = max(8, int(min(crop_w, crop_h) * 0.12))
        lines = cv2.HoughLinesP(
            edges,
            1,
            np.pi / 180.0,
            threshold=4,
            minLineLength=min_length,
            maxLineGap=max(5, int(min(crop_w, crop_h) * 0.12)),
        )
        if lines is None:
            return False
        negative = []
        positive = []
        for raw in np.asarray(lines).reshape(-1, 4):
            x_start, y_start, x_end, y_end = map(int, raw)
            if x_start > x_end:
                x_start, x_end = x_end, x_start
                y_start, y_end = y_end, y_start
            delta_x = x_end - x_start
            if delta_x <= 0:
                continue
            slope = (y_end - y_start) / float(delta_x)
            if not 0.35 <= abs(slope) <= 3.5:
                continue
            item = (x_start, y_start, x_end, y_end)
            (positive if slope > 0 else negative).append(item)
        for upper in negative:
            for lower in positive:
                left_x_gap = abs(upper[0] - lower[0])
                left_y_gap = abs(upper[1] - lower[1])
                left_y = (upper[1] + lower[1]) / 2.0
                if left_x_gap > crop_w * 0.28 or left_y_gap > crop_h * 0.30:
                    continue
                if upper[3] >= left_y - crop_h * 0.08:
                    continue
                if lower[3] <= left_y + crop_h * 0.08:
                    continue
                return True
        return False

    def find_intermediate_back_control(self, hierarchy, screen_size, ocr_records=None, screen=None):
        """Localiza el `<` lateral de una pantalla intermedia, no el del post."""
        if hierarchy is None or not screen_size:
            return None
        width, height = screen_size
        back_labels = ("atras", "volver", "regresar", "back", "navigate up", "ir atras")
        back_glyphs = {"<", "‹", "〈", "←"}
        candidates = []
        for node in hierarchy.iter("node"):
            if node.attrib.get("visible-to-user", "true").casefold() == "false":
                continue
            if node.attrib.get("enabled", "true").casefold() == "false":
                continue
            bounds = self.parse_node_bounds(node)
            if not bounds:
                continue
            left, top, right, bottom = bounds
            center = ((left + right) // 2, (top + bottom) // 2)
            if not (center[0] <= width * 0.22 and height * 0.14 <= center[1] <= height * 0.86):
                continue
            labels = self.normalized_node_labels(node)
            labeled_back = any(
                label in back_glyphs or any(term == label or term in label for term in back_labels)
                for label in labels
            )
            clickable = node.attrib.get("clickable", "false").casefold() == "true"
            box_width, box_height = right - left, bottom - top
            geometric_back = (
                clickable
                and left <= width * 0.055
                and width * 0.055 <= box_width <= width * 0.24
                and height * 0.022 <= box_height <= height * 0.13
            )
            if geometric_back and screen is not None:
                geometric_back = self.looks_like_left_chevron(screen, bounds)
            if labeled_back or geometric_back:
                priority = 0 if labeled_back else 2
                candidates.append((
                    priority,
                    abs(center[1] - height // 2),
                    center,
                    "accesibilidad" if labeled_back else "geometría visual",
                    bounds,
                ))
        for record in ocr_records or []:
            bounds = record.get("bounds")
            label = self.normalize_search_text(record.get("text", "")).strip()
            if not bounds or label not in back_glyphs:
                continue
            left, top, right, bottom = bounds
            center = ((left + right) // 2, (top + bottom) // 2)
            if center[0] <= width * 0.22 and height * 0.14 <= center[1] <= height * 0.86:
                candidates.append((1, abs(center[1] - height // 2), center, "OCR", bounds))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]))
        _, _, point, source, bounds = candidates[0]
        return {"point": point, "source": source, "bounds": bounds}

    def has_ad_label_above(self, records, target_y, screen_height, max_distance_ratio=0.30):
        for record in records:
            if not self.is_ad_label_record(record):
                continue
            bounds = record["bounds"]
            label_y = (bounds[1] + bounds[3]) / 2.0
            distance = target_y - label_y
            if 0 <= distance <= screen_height * max_distance_ratio:
                return True
        return False

    def expand_visible_see_more(self, device, screen_size, max_expansions=3):
        attempted = set()
        last_hierarchy = None
        last_accessibility = []
        last_ocr = None
        expanded = 0
        for _ in range(max_expansions + 1):
            last_hierarchy = self.get_android_hierarchy(device)
            last_accessibility = self.accessibility_text_records(last_hierarchy)
            last_ocr = self.windows_ocr_records(device)
            combined_records = last_accessibility + last_ocr
            if self.is_open_post_view(combined_records, screen_size):
                break
            if any(self.is_ad_label_record(record) for record in combined_records):
                self.log(f"[{device}] Publicidad visible; no se pulsa Ver más.")
                break
            controls = self.find_see_more_controls(combined_records, screen_size)
            if not controls or expanded >= max_expansions:
                break
            control = controls[0]
            point = control["point"]
            key = (round(point[0] / 12), round(point[1] / 12), self.normalize_search_text(control["text"]))
            if key in attempted:
                break
            attempted.add(key)
            ok, detail = self.run_on_device(
                device, ["shell", "input", "tap", str(point[0]), str(point[1])], timeout=15
            )
            if not ok:
                self.log(f"[{device}] Se encontró Ver más, pero no se pudo pulsar: {detail}")
                break
            expanded += 1
            self.log(f"[{device}] Ver más expandido en {point} mediante {control['source']}.")
            if self.wait_or_cancel(0.8, self.search_stop_event):
                break
        return last_hierarchy, last_accessibility, last_ocr, expanded

    def post_timestamp_word_point(self, record):
        """Devuelve sólo el centro de las palabras que forman una fecha/hora."""
        words = record.get("words", [])
        unit_pattern = re.compile(r"^(?:min(?:uto)?s?|m|h|hora?s?|d|dia?s?|sem(?:ana)?s?|a|ano?s?)$")
        compact_time = re.compile(r"^\d{1,3}(?:min|m|h|d|sem|a)$")
        ocr_h = re.compile(r"^\d{1,2}(?:11|ii|ll|l1)$")
        for index, word in enumerate(words):
            normalized = self.normalize_search_text(word.get("text", "")).strip(" ·•.�")
            word_bounds = word.get("bounds")
            if not normalized or not word_bounds:
                continue
            if compact_time.match(normalized) or ocr_h.match(normalized):
                return ((word_bounds[0] + word_bounds[2]) // 2, (word_bounds[1] + word_bounds[3]) // 2)
            if unit_pattern.match(normalized) and index > 0:
                previous = words[index - 1]
                previous_text = self.normalize_search_text(previous.get("text", "")).strip(" ·•.�")
                previous_bounds = previous.get("bounds")
                if previous_text.isdigit() and previous_bounds:
                    return (
                        (previous_bounds[0] + word_bounds[2]) // 2,
                        (min(previous_bounds[1], word_bounds[1]) + max(previous_bounds[3], word_bounds[3])) // 2,
                    )
        return None

    def is_post_timestamp_record(self, record, screen_size):
        text_value = self.normalize_search_text(record.get("text", "")).strip()
        bounds = record.get("bounds")
        if not text_value or not bounds or not screen_size:
            return False
        if record.get("timestamp_candidate"):
            return True
        width, height = screen_size
        left, top, right, bottom = bounds
        center_x, center_y = (left + right) / 2.0, (top + bottom) / 2.0
        if center_y < height * 0.15 or center_x > width * 0.62:
            return False
        record_width = right - left
        if record_width > width * 0.76 or len(text_value) > 88:
            return False
        standard = re.match(
            r"^(?:hace\s+)?\d{1,3}\s*(?:min(?:uto)?s?|m|h|hora?s?|d|dia?s?|sem(?:ana)?s?|a|ano?s?)\b",
            text_value,
        )
        if standard:
            return True
        embedded = re.search(
            r"(?:^|\s|[^\w\s])\d{1,3}\s*(?:min(?:uto)?s?|m|h|hora?s?|d|dia?s?|sem(?:ana)?s?|a|ano?s?)\b",
            text_value,
        )
        if embedded:
            # Una fecha puede compartir línea con un nombre largo de página. Para
            # superar el límite histórico de 48 %, exigimos palabras OCR que
            # permitan pulsar exactamente el segmento temporal, no el perfil.
            return record_width <= width * 0.48 or self.post_timestamp_word_point(record) is not None
        # OCR puede leer la h pequeña como "11" (por ejemplo: 9 h -> 911).
        compact = re.sub(r"\s+", "", text_value)
        if re.match(r"^\d{1,2}(?:11|ii|ll|l1)(?:\W.*)?$", compact):
            return True
        begins_with_number = bool(re.match(r"^\d{1,3}", text_value))
        has_audience_separator = "·" in text_value or "•" in text_value
        return begins_with_number and has_audience_separator

    def post_timestamp_click_point(self, record):
        bounds = record.get("bounds")
        if not bounds:
            return None
        word_point = self.post_timestamp_word_point(record)
        if word_point:
            return word_point
        left, top, right, bottom = bounds
        return ((left + right) // 2, (top + bottom) // 2)

    def post_header_anchor(self, text_value):
        """Extrae el nombre estable que aparece antes de la fecha/hora del post."""
        normalized = re.sub(r"\s+", " ", self.normalize_search_text(text_value or "")).strip()
        if not normalized:
            return ""
        parts = [part.strip(" .·•|-") for part in re.split(r"[·•|]", normalized)]
        time_pattern = re.compile(
            r"(?:^|\s)\d{1,3}\s*(?:min(?:uto)?s?|m|h|hora?s?|d|dia?s?|sem(?:ana)?s?|a|ano?s?)(?:\s|$)"
        )
        for part in parts:
            if len(part) >= 3 and re.search(r"[a-z]", part) and not time_pattern.search(part):
                return part[:100]
        without_time = time_pattern.sub(" ", normalized)
        without_time = re.sub(r"\b(?:publicacion|post|publicado|hace)\b", " ", without_time)
        without_time = re.sub(r"[^\w\s]", " ", without_time, flags=re.UNICODE)
        without_time = re.sub(r"\s+", " ", without_time).strip()
        return without_time[:100] if len(without_time) >= 3 and re.search(r"[a-z]", without_time) else ""

    def nearby_post_header_anchor(self, records, timestamp, screen_size):
        """Obtiene el encabezado cercano cuando fecha y nombre vienen en nodos separados."""
        direct = self.post_header_anchor(timestamp.get("text", ""))
        if direct:
            return direct
        if not screen_size or not timestamp.get("bounds"):
            return ""
        _, height = screen_size
        t_left, t_top, t_right, t_bottom = timestamp["bounds"]
        candidates = []
        for record in records:
            if record is timestamp or not record.get("bounds"):
                continue
            left, top, right, bottom = record["bounds"]
            if bottom > t_bottom + height * 0.015 or t_top - bottom > height * 0.10:
                continue
            text_value = record.get("text", "").strip()
            anchor = self.post_header_anchor(text_value)
            if not anchor or self.is_post_timestamp_record(record, screen_size):
                continue
            if self.is_ad_label_record(record):
                continue
            candidates.append((abs(t_top - bottom), -len(anchor), anchor))
        if not candidates:
            return ""
        candidates.sort()
        return candidates[0][2]

    def post_reference_from_snapshot(self, snapshot):
        """Conserva la identidad mínima necesaria para volver al mismo post."""
        return {
            "header_anchor": self.normalize_search_text(snapshot.get("header_anchor", "")).strip(),
            "matches": [
                self.normalize_search_text(value).strip()
                for value in snapshot.get("matches", [])
                if self.normalize_search_text(value).strip()
            ],
            "timestamp_text": self.normalize_search_text(snapshot.get("timestamp_text", "")).strip(),
        }

    def post_reference_matches(self, records, post_reference):
        """Compara el encabezado guardado con el texto de la pantalla actual."""
        if not post_reference:
            return True
        normalized_records = [
            re.sub(r"\s+", " ", self.normalize_search_text(record.get("text", ""))).strip()
            for record in records or []
            if record.get("text", "").strip()
        ]
        visible_text = " ".join(normalized_records)
        header = post_reference.get("header_anchor", "")
        if header:
            if self.phrase_matches_text(header, visible_text):
                return True
            for candidate in normalized_records:
                if len(candidate) < 3:
                    continue
                length_ratio = min(len(header), len(candidate)) / max(len(header), len(candidate))
                if length_ratio >= 0.62 and SequenceMatcher(None, header, candidate).ratio() >= 0.82:
                    return True
            return False
        timestamp = post_reference.get("timestamp_text", "")
        matches = post_reference.get("matches", [])
        timestamp_seen = bool(timestamp and self.phrase_matches_text(timestamp, visible_text))
        match_seen = any(self.phrase_matches_text(value, visible_text) for value in matches)
        return timestamp_seen and match_seen

    def find_post_match_snapshot(self, records, normalized_keywords, screen_size):
        if not records or not normalized_keywords or not screen_size:
            return None
        width, height = screen_size
        usable = []
        for record in records:
            bounds = record.get("bounds")
            text_value = record.get("text", "").strip()
            if not bounds or not text_value:
                continue
            if bounds[3] <= height * 0.14:
                continue
            usable.append(record)
        usable.sort(key=lambda record: (record["bounds"][1], record["bounds"][0]))
        timestamps = [record for record in usable if self.is_post_timestamp_record(record, screen_size)]
        if not timestamps:
            return None
        candidates = []
        for start in range(len(usable)):
            joined_parts = []
            left, top, right, bottom = usable[start]["bounds"]
            previous_bottom = bottom
            for end in range(start, min(len(usable), start + 5)):
                record = usable[end]
                r_left, r_top, r_right, r_bottom = record["bounds"]
                if end > start and r_top - previous_bottom > height * 0.075:
                    break
                joined_parts.append(record["text"])
                left, top = min(left, r_left), min(top, r_top)
                right, bottom = max(right, r_right), max(bottom, r_bottom)
                previous_bottom = r_bottom
                joined = " ".join(joined_parts)
                normalized_joined = self.normalize_search_text(joined)
                matches = [
                    original for original, normalized in normalized_keywords.items()
                    if self.phrase_matches_text(normalized, normalized_joined)
                ]
                if not matches:
                    continue
                anchor_y = (top + bottom) / 2.0
                if self.has_ad_label_above(usable, anchor_y, height, max_distance_ratio=0.85):
                    continue
                nearby_timestamps = []
                for timestamp in timestamps:
                    t_bounds = timestamp["bounds"]
                    timestamp_y = (t_bounds[1] + t_bounds[3]) / 2.0
                    delta = anchor_y - timestamp_y
                    if -height * 0.12 <= delta <= height * 0.40:
                        penalty = abs(delta) + (height * 0.035 if delta < 0 else 0)
                        nearby_timestamps.append((penalty, timestamp_y, timestamp))
                if not nearby_timestamps:
                    continue
                nearby_timestamps.sort(key=lambda item: item[0])
                _, timestamp_y, timestamp = nearby_timestamps[0]
                t_left, t_top, t_right, t_bottom = timestamp["bounds"]
                preview_records = [
                    item["text"] for item in usable
                    if timestamp_y - height * 0.13 <= (item["bounds"][1] + item["bounds"][3]) / 2.0 <= timestamp_y + height * 0.35
                ]
                preview = " ".join(preview_records)[:280]
                candidates.append({
                    "matches": matches,
                    "preview": preview or joined,
                    "timestamp_text": timestamp["text"],
                    "timestamp_point": self.post_timestamp_click_point(timestamp),
                    "timestamp_y": timestamp_y,
                    "source": timestamp.get("source", record.get("source", "unknown")),
                    "fingerprint": self.normalize_search_text(preview or joined),
                    "header_anchor": self.nearby_post_header_anchor(usable, timestamp, screen_size),
                })
                break
        if not candidates:
            return None
        candidates.sort(key=lambda item: item["timestamp_y"])
        return candidates[0]

    @staticmethod
    def parse_node_bounds(node):
        match = re.fullmatch(
            r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",
            node.attrib.get("bounds", ""),
        )
        if not match:
            return None
        left, top, right, bottom = map(int, match.groups())
        if right <= left or bottom <= top:
            return None
        return left, top, right, bottom

    def normalized_node_labels(self, node):
        return {
            self.normalize_search_text(node.attrib.get(attribute, "").strip())
            for attribute in ("text", "content-desc")
            if node.attrib.get(attribute, "").strip()
        }

    def find_accessible_control(
        self,
        hierarchy,
        exact_labels=(),
        prefix_labels=(),
        screen_size=None,
        ignore_top_pct=0.0,
        allow_nonclickable=False,
    ):
        """Devuelve el centro de un rótulo accesible validado."""
        if hierarchy is None:
            return None
        exact = {self.normalize_search_text(value) for value in exact_labels}
        prefixes = tuple(self.normalize_search_text(value) for value in prefix_labels)
        candidates = []
        for node in hierarchy.iter("node"):
            if node.attrib.get("visible-to-user", "true").casefold() == "false":
                continue
            if node.attrib.get("enabled", "true").casefold() == "false":
                continue
            labels = self.normalized_node_labels(node)
            priority = None
            if labels.intersection(exact):
                priority = 0
            elif any(label.startswith(prefix) for label in labels for prefix in prefixes):
                priority = 1
            if priority is None:
                continue
            if (
                not allow_nonclickable
                and node.attrib.get("clickable", "false").casefold() != "true"
            ):
                continue
            bounds = self.parse_node_bounds(node)
            if not bounds:
                continue
            left, top, right, bottom = bounds
            center = ((left + right) // 2, (top + bottom) // 2)
            if screen_size and center[1] <= screen_size[1] * ignore_top_pct:
                continue
            candidates.append((priority, center[1], center))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][2]

    def find_bottom_editable_control(self, hierarchy, screen_size):
        """Localiza un editor inferior, incluido MultiAutoCompleteTextView de FB Lite."""
        if hierarchy is None or not screen_size:
            return None
        screen_width, screen_height = screen_size
        candidates = []
        geometric = []
        for node in hierarchy.iter("node"):
            class_name = node.attrib.get("class", "").casefold()
            editable = node.attrib.get("editable", "false").casefold() == "true"
            if node.attrib.get("visible-to-user", "true").casefold() == "false":
                continue
            if node.attrib.get("enabled", "true").casefold() == "false":
                continue
            bounds = self.parse_node_bounds(node)
            if not bounds:
                continue
            left, top, right, bottom = bounds
            center = ((left + right) // 2, (top + bottom) // 2)
            recognized_editor = "edittext" in class_name or "autocompletetextview" in class_name or editable
            if recognized_editor and center[1] >= screen_height * 0.55:
                tap_x = screen_width // 2 if left <= screen_width // 2 <= right else center[0]
                priority = 0 if "autocompletetextview" in class_name else 1
                candidates.append((priority, -center[1], (tap_x, center[1])))
                continue
            box_width, box_height = right - left, bottom - top
            if (
                center[1] >= screen_height * 0.86
                and screen_width * 0.32 <= box_width <= screen_width * 0.72
                and screen_height * 0.012 <= box_height <= screen_height * 0.075
                and screen_width * 0.08 <= left <= screen_width * 0.30
                and right >= screen_width * 0.55
            ):
                tap_x = screen_width // 2 if left <= screen_width // 2 <= right else center[0]
                geometric.append((-center[1], (tap_x, center[1])))
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1]))
            return candidates[0][2]
        if geometric:
            geometric.sort(key=lambda item: item[0])
            return geometric[0][1]
        return None

    def find_keyword_anchor_y(self, hierarchy, normalized_keywords):
        for node in hierarchy.iter("node"):
            if node.attrib.get("visible-to-user", "true").casefold() == "false":
                continue
            labels = self.normalized_node_labels(node)
            if not any(keyword in label for label in labels for keyword in normalized_keywords):
                continue
            bounds = self.parse_node_bounds(node)
            if bounds:
                return (bounds[1] + bounds[3]) // 2
        return None

    def find_like_control(self, hierarchy, anchor_y=None):
        """Localiza Me gusta o su estado activo sin depender de coordenadas fijas."""
        if hierarchy is None:
            return "not_found", None
        exact_like = {"me gusta", "like"}
        exact_unlike = {"quitar me gusta", "unlike", "remove like"}
        controls = []
        for node in hierarchy.iter("node"):
            if node.attrib.get("visible-to-user", "true").casefold() == "false":
                continue
            if node.attrib.get("enabled", "true").casefold() == "false":
                continue
            labels = self.normalized_node_labels(node)
            exact_unlike_match = bool(labels.intersection(exact_unlike))
            unlike = exact_unlike_match or any(
                re.match(
                    r'^(?:boton\s+["“]?quitar me gusta|quitar me gusta(?:,?\s*boton)?|["“]?unlike["”]?(?:,?\s*button)?|remove like\b)',
                    label,
                )
                for label in labels
            )
            exact_like_match = bool(labels.intersection(exact_like))
            like = exact_like_match or any(
                re.match(
                    r'^(?:boton\s+["“]?me gusta["”]?(?:\.|$)|me gusta,?\s*boton(?:\.|$)|["“]?like["”]?,?\s*button(?:\.|$))',
                    label,
                )
                for label in labels
            )
            if not like and not unlike:
                continue
            bounds = self.parse_node_bounds(node)
            if not bounds:
                continue
            left, top, right, bottom = bounds
            point = ((left + right) // 2, (top + bottom) // 2)
            selected = (
                unlike
                or node.attrib.get("selected", "false").casefold() == "true"
                or node.attrib.get("checked", "false").casefold() == "true"
            )
            # Facebook Lite puede publicar el texto exacto en un hijo no pulsable;
            # tocar el centro de sus límites entrega el evento al contenedor padre.
            # Las descripciones extendidas siguen exigiendo un nodo pulsable.
            if (
                not selected
                and not exact_like_match
                and node.attrib.get("clickable", "false").casefold() != "true"
            ):
                continue
            distance = abs(point[1] - anchor_y) if anchor_y is not None else point[1]
            controls.append((distance, "already_liked" if selected else "available", point))
        if not controls:
            return "not_found", None
        controls.sort(key=lambda item: item[0])
        _, state, point = controls[0]
        return state, point

    def apply_like_action(self, device, hierarchy, anchor_y=None, stop_event=None):
        state, point = self.find_like_control(hierarchy, anchor_y)
        if state == "already_liked":
            self.log(f"[{device}] La publicación ya tenía Me gusta; no se tocó.")
            return "already_liked"
        if state == "not_found":
            self.log(f"[{device}] No se encontró un control accesible Me gusta.")
            return "not_found"
        x, y = point
        ok, detail = self.run_on_device(
            device, ["shell", "input", "tap", str(x), str(y)], timeout=15
        )
        if not ok:
            self.log(f"[{device}] No se pudo tocar Me gusta: {detail}")
            return "error"
        if self.wait_or_cancel(0.8, stop_event):
            return "cancelled"
        try:
            updated = self.get_android_hierarchy(device)
            updated_state, _ = self.find_like_control(updated, anchor_y)
            if updated_state == "already_liked":
                self.log(f"[{device}] Me gusta confirmado por accesibilidad.")
                return "confirmed"
        except Exception as error:
            self.log(f"[{device}] No se pudo verificar Me gusta: {error}")
        self.log(f"[{device}] Toque Me gusta enviado; estado no confirmado.")
        return "sent_unconfirmed"

    def find_reel_side_control(self, hierarchy, screen_size, action):
        """Identifica Me gusta/Comentario en la columna lateral de un Reel."""
        if hierarchy is None or not screen_size or action not in {"like", "comment"}:
            return None
        width, height = screen_size
        candidates = []
        for node in hierarchy.iter("node"):
            if node.attrib.get("visible-to-user", "true").casefold() == "false":
                continue
            if node.attrib.get("enabled", "true").casefold() == "false":
                continue
            if node.attrib.get("clickable", "false").casefold() != "true":
                continue
            bounds = self.parse_node_bounds(node)
            if not bounds:
                continue
            left, top, right, bottom = bounds
            box_width, box_height = right - left, bottom - top
            point = ((left + right) // 2, (top + bottom) // 2)
            # En Facebook Lite los controles del Reel forman una columna de
            # bloques pulsables a la derecha: Me gusta, Comentario y Compartir.
            if point[0] < width * 0.80:
                continue
            if not height * 0.50 <= point[1] <= height * 0.89:
                continue
            if box_width > width * 0.24 or not height * 0.035 <= box_height <= height * 0.13:
                continue
            candidates.append(point)
        if not candidates:
            return None
        candidates.sort(key=lambda point: point[1])
        distinct = []
        for point in candidates:
            if not distinct or point[1] - distinct[-1][1] > height * 0.045:
                distinct.append(point)
        index = 0 if action == "like" else 1
        return distinct[index] if len(distinct) > index else None

    def is_reel_like_active(self, screen, point):
        if not OPENCV_AVAILABLE or screen is None or not point:
            return False
        height, width = screen.shape[:2]
        radius = max(22, int(width * 0.055))
        x, y = point
        patch = screen[max(0, y-radius):min(height, y+radius), max(0, x-radius):min(width, x+radius)]
        if patch.size == 0:
            return False
        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        blue = cv2.inRange(hsv, np.array([90, 70, 65]), np.array([135, 255, 255]))
        return float(np.count_nonzero(blue)) / float(blue.size) >= 0.035

    def locate_reel_side_figure(self, screen, action):
        """Respaldo visual para las dos primeras siluetas blancas del Reel."""
        if not OPENCV_AVAILABLE or screen is None or action not in {"like", "comment"}:
            return None
        height, width = screen.shape[:2]
        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        mask = cv2.inRange(gray, 170, 255)
        mask[:int(height * 0.50), :] = 0
        mask[int(height * 0.89):, :] = 0
        mask[:, :int(width * 0.80)] = 0
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for contour in contours:
            x, y, box_width, box_height = cv2.boundingRect(contour)
            point = (x + box_width // 2, y + box_height // 2)
            if point[0] < width * 0.87:
                continue
            if not width * 0.04 <= box_width <= width * 0.13:
                continue
            if not height * 0.025 <= box_height <= height * 0.09:
                continue
            area = cv2.contourArea(contour)
            if area < width * height * 0.0007:
                continue
            candidates.append((point[1], point, area))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        distinct = []
        for candidate in candidates:
            if not distinct or candidate[0] - distinct[-1][0] > height * 0.045:
                distinct.append(candidate)
            elif candidate[2] > distinct[-1][2]:
                distinct[-1] = candidate
        index = 0 if action == "like" else 1
        if len(distinct) <= index:
            return None
        point = distinct[index][1]
        return {"point": point, "active": self.is_reel_like_active(screen, point)}

    def apply_reel_action(self, device, action, hierarchy, screen_size, stop_event=None):
        screen = self.capture_device_screen(device)
        point = self.find_reel_side_control(hierarchy, screen_size, action)
        source = "estructura lateral"
        visual = self.locate_reel_side_figure(screen, action)
        if point is None and visual:
            point = visual["point"]
            source = "silueta lateral"
        if point is None:
            self.log(f"[{device}] No se identificó el control lateral de {action} en el Reel.")
            return "not_found"
        if action == "like" and (
            (visual and visual.get("active")) or self.is_reel_like_active(screen, point)
        ):
            self.log(f"[{device}] El Me gusta del Reel ya aparece activo; no se tocó.")
            return "already_liked"
        ok, detail = self.run_on_device(
            device, ["shell", "input", "tap", str(point[0]), str(point[1])], timeout=15
        )
        if not ok:
            self.log(f"[{device}] Se identificó {action} del Reel, pero el toque falló: {detail}")
            return "error"
        self.log(f"[{device}] Control {action} de Reel pulsado en {point} mediante {source}.")
        if action == "comment":
            return "sent"
        if self.wait_or_cancel(0.9, stop_event):
            return "cancelled"
        updated = self.capture_device_screen(device)
        updated_match = self.locate_reel_side_figure(updated, "like")
        if updated_match and updated_match.get("active"):
            self.log(f"[{device}] Me gusta del Reel confirmado visualmente.")
            return "confirmed"
        self.log(f"[{device}] Toque de Me gusta del Reel enviado; estado no confirmado.")
        return "sent_unconfirmed"

    def append_search_result(self, msg):
        self.search_results.config(state="normal")
        self.search_results.insert(tk.END, msg + "\n")
        self.search_results.see(tk.END)
        self.search_results.config(state="disabled")

    def find_ocr_text_point(self, records, exact_labels=(), contains_labels=()):
        exact = {self.normalize_search_text(label).strip() for label in exact_labels}
        contains = tuple(self.normalize_search_text(label).strip() for label in contains_labels)
        candidates = []
        for record in records or []:
            bounds = record.get("bounds")
            text_value = self.normalize_search_text(record.get("text", "")).strip()
            if not bounds or not text_value:
                continue
            priority = 0 if text_value in exact else 1 if any(label in text_value for label in contains) else None
            if priority is None:
                continue
            left, top, right, bottom = bounds
            candidates.append((priority, top, ((left + right) // 2, (top + bottom) // 2)))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][2]

    def facebook_is_foreground(self, device):
        try:
            output = self.adb_capture(device, ["shell", "dumpsys", "activity", "activities"], timeout=15)
            resumed = next((line for line in output.splitlines() if "mResumedActivity" in line), "")
            return "com.facebook.lite" in resumed or "com.facebook.katana" in resumed
        except Exception:
            return False

    def read_pasted_facebook_url(self, hierarchy):
        if hierarchy is None:
            return None
        for node in hierarchy.iter("node"):
            for attribute in ("text", "content-desc"):
                value = node.attrib.get(attribute, "").strip()
                for candidate in re.findall(r"https?://[^\s]+", value):
                    candidate = candidate.rstrip(".,);]}")
                    if self.is_facebook_url(candidate):
                        return candidate
        return None

    def return_from_settings_to_post(self, device, screen_size=None, post_url=None, post_reference=None):
        """Regresa desde Ajustes y recupera exactamente la publicación original."""
        screen_size = screen_size or self.get_device_screen_size(device) or (1080, 1920)
        for _ in range(6):
            if self.facebook_is_foreground(device):
                break
            self.run_on_device(device, ["shell", "input", "keyevent", "4"])
            if self.wait_or_cancel(0.35, self.search_stop_event):
                return False
        if not self.facebook_is_foreground(device):
            self.log(f"[{device}] No se recuperó Facebook después de leer el enlace en Ajustes.")
            return False

        expected_header = (post_reference or {}).get("header_anchor", "")
        if expected_header:
            self.log(f"[{device}] Regreso dirigido al encabezado original: '{expected_header}'.")
        for step in range(10):
            if self.search_stop_event.is_set():
                return False
            hierarchy = self.get_android_hierarchy(device)
            records = self.accessibility_text_records(hierarchy)
            ocr_records = self.windows_ocr_records(device)
            records.extend(ocr_records)
            if self.is_facebook_feed_hierarchy(hierarchy, screen_size):
                self.log(f"[{device}] El retorno llegó al feed antes que a la publicación.")
                break
            screen = self.capture_device_screen(device)
            back_control = self.find_intermediate_back_control(
                hierarchy, screen_size, ocr_records, screen=screen
            )
            if back_control:
                point = back_control["point"]
                self.log(
                    f"[{device}] Publicación todavía no recuperada: control < inferior localizado por "
                    f"{back_control['source']} en {point}; regresando un paso."
                )
                ok, detail = self.run_on_device(
                    device,
                    ["shell", "input", "tap", str(point[0]), str(point[1])],
                    timeout=15,
                )
            elif (
                self.is_open_post_view(records, screen_size)
                or self.is_open_post_hierarchy(hierarchy, screen_size)
            ) and self.post_reference_matches(records, post_reference):
                self.log(
                    f"[{device}] Publicación original recuperada por encabezado y sin controles < inferiores; "
                    "ya se puede buscar la fila de acciones."
                )
                return True
            else:
                open_post = (
                    self.is_open_post_view(records, screen_size)
                    or self.is_open_post_hierarchy(hierarchy, screen_size)
                )
                reason = "publicación distinta al encabezado original" if open_post else "estado intermedio"
                self.log(
                    f"[{device}] {reason.capitalize()}; se ejecuta Atrás "
                    f"({step + 1}/10) y se vuelve a comparar."
                )
                ok, detail = self.run_on_device(
                    device, ["shell", "input", "keyevent", "4"], timeout=15
                )
            if not ok:
                self.log(f"[{device}] No se pudo retroceder hacia la publicación: {detail}")
                break
            if self.wait_or_cancel(0.60, self.search_stop_event):
                return False

        if post_url and self.is_facebook_url(post_url):
            self.log(f"[{device}] Se reabrirá el enlace capturado para recuperar la publicación exacta.")
            ok, detail = self.run_on_device(
                device,
                ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", post_url, "com.facebook.lite"],
                timeout=20,
            )
            if not ok:
                self.log(f"[{device}] No se pudo reabrir la publicación: {detail}")
                return False
            if self.wait_or_cancel(1.4, self.search_stop_event):
                return False
            if self.confirm_actionable_open_post(
                device, screen_size, attempts=4, delay=0.65, post_reference=post_reference
            ):
                self.log(
                    f"[{device}] Publicación original reabierta mediante su enlace y "
                    "confirmada contra el encabezado guardado."
                )
                return True
        self.log(f"[{device}] No se logró recuperar una vista confirmada de la publicación.")
        return False

    def capture_open_post_link(self, device, screen_size, post_reference=None):
        """Copia y lee el enlace de la publicación abierta sin instalar auxiliares."""
        if not screen_size or self.search_stop_event.is_set():
            return None
        width, height = screen_size
        hierarchy = self.get_android_hierarchy(device)
        records = self.accessibility_text_records(hierarchy) + self.windows_ocr_records(device)
        if not (
            self.is_open_post_view(records, screen_size)
            or self.is_open_post_hierarchy(hierarchy, screen_size)
        ):
            self.log(f"[{device}] No se confirmó una publicación abierta; no se intentó copiar su enlace.")
            return None

        # El menú de tres puntos está en el encabezado de la publicación abierta.
        ok, detail = self.run_on_device(
            device,
            ["shell", "input", "tap", str(int(width * 0.94)), str(int(height * 0.135))],
            timeout=15,
        )
        if not ok:
            self.log(f"[{device}] No se pudo abrir el menú para obtener el enlace: {detail}")
            return None
        if self.wait_or_cancel(0.65, self.search_stop_event):
            return None

        more_point = self.find_ocr_text_point(
            self.windows_ocr_records(device),
            exact_labels=("Más opciones", "More options"),
        )
        if not more_point:
            self.log(f"[{device}] El menú no mostró la opción exacta Más opciones; no se tocó otra alternativa.")
            self.run_on_device(device, ["shell", "input", "keyevent", "4"])
            return None
        self.run_on_device(device, ["shell", "input", "tap", str(more_point[0]), str(more_point[1])])
        if self.wait_or_cancel(0.65, self.search_stop_event):
            return None

        copy_point = self.find_ocr_text_point(
            self.windows_ocr_records(device),
            exact_labels=("Copiar enlace", "Copy link"),
        )
        if not copy_point:
            self.log(f"[{device}] No apareció la opción exacta Copiar enlace; el enlace no se capturó.")
            self.run_on_device(device, ["shell", "input", "keyevent", "4"])
            self.run_on_device(device, ["shell", "input", "keyevent", "4"])
            return None
        self.run_on_device(device, ["shell", "input", "tap", str(copy_point[0]), str(copy_point[1])])

        copied = False
        for _ in range(3):
            if self.wait_or_cancel(0.20, self.search_stop_event):
                return None
            toast_records = self.windows_ocr_records(device)
            if self.find_ocr_text_point(
                toast_records,
                contains_labels=("Enlace copiado correctamente", "Link copied"),
            ):
                copied = True
                break
        if not copied:
            self.log(f"[{device}] Facebook no confirmó que el enlace se copiara; no se usará el portapapeles anterior.")
            self.run_on_device(device, ["shell", "input", "keyevent", "4"])
            self.run_on_device(device, ["shell", "input", "keyevent", "4"])
            return None

        url = None
        try:
            self.run_on_device(device, ["shell", "am", "start", "-a", "android.settings.SETTINGS"])
            if self.wait_or_cancel(0.80, self.search_stop_event):
                return None
            settings_hierarchy = self.get_android_hierarchy(device)
            search_point = self.find_accessible_control(
                settings_hierarchy,
                exact_labels=("Buscar ajustes", "Search settings"),
                screen_size=screen_size,
                allow_nonclickable=True,
            )
            if not search_point:
                self.log(f"[{device}] No se localizó la búsqueda de Ajustes para leer el enlace copiado.")
                return None
            self.run_on_device(device, ["shell", "input", "tap", str(search_point[0]), str(search_point[1])])
            if self.wait_or_cancel(0.65, self.search_stop_event):
                return None
            self.run_on_device(device, ["shell", "input", "keyevent", "279"])
            if self.wait_or_cancel(0.45, self.search_stop_event):
                return None
            pasted_hierarchy = self.get_android_hierarchy(device)
            url = self.read_pasted_facebook_url(pasted_hierarchy)
            if not url:
                # Algunos teclados necesitan terminar de enfocarse antes de aceptar KEYCODE_PASTE.
                if self.wait_or_cancel(0.40, self.search_stop_event):
                    return None
                self.run_on_device(device, ["shell", "input", "keyevent", "279"])
                if self.wait_or_cancel(0.45, self.search_stop_event):
                    return None
                pasted_hierarchy = self.get_android_hierarchy(device)
                url = self.read_pasted_facebook_url(pasted_hierarchy)
            if url:
                self.log(f"[{device}] Enlace de publicación capturado: {url}")
            else:
                self.log(f"[{device}] El contenido pegado no fue un enlace válido de Facebook.")
            return url
        finally:
            self.return_from_settings_to_post(
                device, screen_size, post_url=url, post_reference=post_reference
            )

    def save_search_link_record(self, device, snapshot, url):
        if not url:
            return None, False
        self.search_record_dir.mkdir(parents=True, exist_ok=True)
        path = self.search_record_dir / f"enlaces_{time.strftime('%Y-%m-%d')}.csv"
        fields = ("fecha_hora", "serie", "nombre", "palabras", "enlace", "fecha_publicacion", "vista_previa")
        with self.search_record_lock:
            existing = set()
            if path.exists():
                try:
                    with path.open("r", encoding="utf-8-sig", newline="") as handle:
                        existing = {row.get("enlace", "") for row in csv.DictReader(handle)}
                except Exception as error:
                    self.log(f"[{device}] No se pudo revisar el registro diario: {error}")
            if url in existing:
                return path, False
            write_header = not path.exists() or path.stat().st_size == 0
            with path.open("a", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                if write_header:
                    writer.writeheader()
                writer.writerow({
                    "fecha_hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "serie": device,
                    "nombre": self.display_device_name(device),
                    "palabras": ", ".join(snapshot.get("matches", [])),
                    "enlace": url,
                    "fecha_publicacion": snapshot.get("timestamp_text", ""),
                    "vista_previa": snapshot.get("preview", ""),
                })
        return path, True

    def clear_search_results(self):
        if self.search_running: return
        self.search_results.config(state="normal"); self.search_results.delete("1.0", tk.END); self.search_results.config(state="disabled")
        self.search_status_var.set("Listo para buscar.")

    def start_keyword_search(self):
        keys = [k.strip() for k in re.split(r"[,;\n]+", self.search_keywords.get("1.0", tk.END)) if k.strip()]
        if not keys or not self.get_selected_devices(): return messagebox.showwarning("Aviso", "Escribe palabras clave y selecciona al menos un celular.")
        comment_on_match = bool(self.search_comment_var.get())
        comment_text = self.search_comment_text_var.get().strip()
        if comment_on_match and not comment_text:
            return messagebox.showwarning("Aviso", "Escribe el comentario que se enviará en las publicaciones coincidentes.")
        try:
            like_min = int(self.search_like_min_var.get())
            like_max = int(self.search_like_max_var.get())
            if not 1 <= like_min <= 60 or not 1 <= like_max <= 60 or like_min > like_max:
                raise ValueError
        except ValueError:
            return messagebox.showwarning("Intervalo no válido", "Usa mínimo y máximo enteros de 1 a 60; mínimo no puede superar máximo.")
        devices, busy = self.claim_devices(self.get_selected_devices(), "Búsqueda")
        if not devices:
            return messagebox.showwarning("Equipos ocupados", "Los equipos seleccionados ya ejecutan otra acción.")
        if busy:
            messagebox.showinfo("Equipos ocupados", "Se omitieron equipos que ya ejecutan otra acción.")
        self.search_devices = list(devices)
        for device in devices:
            self.set_device_task(device, "Búsqueda por palabras")
        self.search_stop_event.clear(); self.search_running = True
        self.btn_start_search.config(state="disabled"); self.btn_stop_search.config(state="normal")
        self.search_status_var.set("Búsqueda en curso...")
        threading.Thread(
            target=self.keyword_search_worker,
            args=(
                devices,
                keys,
                bool(self.search_like_var.get()),
                bool(self.search_save_link_var.get()),
                comment_on_match,
                comment_text,
                like_min,
                like_max,
                bool(self.search_continuous_var.get()),
            ),
            daemon=True,
        ).start()

    def find_post_action_row(self, hierarchy, screen_size):
        """Confirma los tres contenedores alineados: Me gusta, Comentar y Compartir."""
        if hierarchy is None or not screen_size:
            return None
        width, height = screen_size
        candidates = []
        for node in hierarchy.iter("node"):
            if node.attrib.get("visible-to-user", "true").casefold() == "false":
                continue
            if node.attrib.get("enabled", "true").casefold() == "false":
                continue
            if node.attrib.get("clickable", "false").casefold() != "true":
                continue
            bounds = self.parse_node_bounds(node)
            if not bounds:
                continue
            left, top, right, bottom = bounds
            box_width, box_height = right - left, bottom - top
            center_y = (top + bottom) // 2
            if not width * 0.26 <= box_width <= width * 0.40:
                continue
            if not height * 0.035 <= box_height <= height * 0.09:
                continue
            if not height * 0.15 <= center_y <= height * 0.88:
                continue
            icon_children = []
            for child in node.iter("node"):
                if child is node or child.attrib.get("class", "") != "android.view.View":
                    continue
                child_bounds = self.parse_node_bounds(child)
                if not child_bounds:
                    continue
                c_left, c_top, c_right, c_bottom = child_bounds
                if not (left <= c_left and c_right <= right and top <= c_top and c_bottom <= bottom):
                    continue
                child_width, child_height = c_right - c_left, c_bottom - c_top
                if (
                    width * 0.025 <= child_width <= width * 0.14
                    and height * 0.018 <= child_height <= height * 0.065
                ):
                    icon_children.append(child_bounds)
            if icon_children:
                candidates.append({"bounds": bounds, "center_y": center_y, "icons": icon_children})

        candidates.sort(key=lambda item: (item["center_y"], item["bounds"][0]))
        for first in candidates:
            same_row = [
                item for item in candidates
                if abs(item["center_y"] - first["center_y"]) <= height * 0.018
            ]
            same_row.sort(key=lambda item: item["bounds"][0])
            for index in range(max(0, len(same_row) - 2)):
                group = same_row[index:index + 3]
                if len(group) < 3:
                    continue
                lefts = [item["bounds"][0] for item in group]
                rights = [item["bounds"][2] for item in group]
                tops = [item["bounds"][1] for item in group]
                bottoms = [item["bounds"][3] for item in group]
                if lefts[0] > width * 0.05 or rights[-1] < width * 0.95:
                    continue
                if max(tops) - min(tops) > height * 0.018 or max(bottoms) - min(bottoms) > height * 0.018:
                    continue
                if any(lefts[pos + 1] - rights[pos] > width * 0.035 for pos in range(2)):
                    continue
                points = [
                    ((item["bounds"][0] + item["bounds"][2]) // 2, (item["bounds"][1] + item["bounds"][3]) // 2)
                    for item in group
                ]
                return {
                    "like": points[0],
                    "comment": points[1],
                    "share": points[2],
                    "top": min(tops),
                    "bottom": max(bottoms),
                    "y": int(sum(point[1] for point in points) / 3),
                    "bounds": [item["bounds"] for item in group],
                }
        return None

    def scroll_to_post_action_row(
        self, device, screen_size, stop_event=None, max_scrolls=18, post_reference=None
    ):
        """Desplaza desde una zona segura hasta confirmar la fila completa de acciones."""
        width, height = screen_size
        if not self.confirm_actionable_open_post(
            device,
            screen_size,
            attempts=2,
            delay=0.35,
            post_reference=post_reference,
        ):
            self.log(
                f"[{device}] No se iniciará el scroll de acciones: la publicación limpia "
                "todavía no está confirmada."
            )
            return None
        for attempt in range(max(0, max_scrolls) + 1):
            hierarchy = self.get_android_hierarchy(device)
            row = self.find_post_action_row(hierarchy, screen_size)
            if row:
                screen = self.capture_device_screen(device)
                like_visual = self.locate_action_figure(
                    screen, "like_outline.png", (0.00, 0.38)
                )
                comment_visual = self.locate_action_figure(
                    screen, "comment_outline.png", (0.25, 0.68)
                )
                tolerance = int(height * 0.035)
                if like_visual and abs(like_visual["point"][1] - row["y"]) <= tolerance:
                    row["like_visual"] = like_visual
                if comment_visual and abs(comment_visual["point"][1] - row["y"]) <= tolerance:
                    row["comment_visual"] = comment_visual
                self.log(
                    f"[{device}] Fila completa Me gusta/Comentar/Compartir confirmada "
                    f"en y={row['y']}."
                )
                return row
            if attempt >= max_scrolls:
                break
            self.log(
                f"[{device}] Fila de acciones aún no visible; desplazamiento seguro "
                f"{attempt + 1}/{max_scrolls}."
            )
            ok, detail = self.run_on_device(
                device,
                [
                    "shell", "input", "swipe", str(width // 2), str(int(height * 0.71)),
                    str(width // 2), str(int(height * 0.26)), "520",
                ],
                timeout=15,
            )
            if not ok:
                self.log(f"[{device}] No se pudo desplazar hacia la fila de acciones: {detail}")
                break
            if self.wait_or_cancel(0.85, stop_event):
                return None
        self.log(f"[{device}] No se confirmó la fila completa Me gusta/Comentar/Compartir.")
        return None

    def apply_confirmed_action_row_like(self, device, row, stop_event=None):
        """Pulsa Me gusta sólo dentro de una fila completa previamente validada."""
        visual = row.get("like_visual")
        if visual and visual.get("active"):
            self.log(f"[{device}] El Me gusta de la fila confirmada ya aparece activo.")
            return "already_liked"
        point = visual["point"] if visual else row["like"]
        ok, detail = self.run_on_device(
            device, ["shell", "input", "tap", str(point[0]), str(point[1])], timeout=15
        )
        if not ok:
            self.log(f"[{device}] No se pudo pulsar Me gusta en la fila confirmada: {detail}")
            return "error"
        self.log(f"[{device}] Me gusta pulsado en {point} dentro de la fila completa confirmada.")
        if self.wait_or_cancel(0.9, stop_event):
            return "cancelled"
        screen = self.capture_device_screen(device)
        verification = self.locate_action_figure(screen, "like_outline.png", (0.00, 0.38))
        if verification and verification.get("active"):
            self.log(f"[{device}] Me gusta confirmado visualmente en color activo.")
            return "confirmed"
        hierarchy = self.get_android_hierarchy(device)
        state, _ = self.find_like_control(hierarchy, anchor_y=row["y"])
        if state == "already_liked":
            self.log(f"[{device}] Me gusta confirmado por accesibilidad después del toque.")
            return "confirmed"
        self.log(f"[{device}] El toque se envió, pero Facebook no expuso confirmación visual.")
        return "sent_unconfirmed"

    def perform_search_post_like(self, device, post_reference=None):
        size = self.get_device_screen_size(device)
        if not size:
            return "screen_error"
        row = self.scroll_to_post_action_row(
            device,
            size,
            stop_event=self.search_stop_event,
            max_scrolls=18,
            post_reference=post_reference,
        )
        if not row:
            return "not_found"
        return self.apply_confirmed_action_row_like(
            device, row, stop_event=self.search_stop_event
        )

    def bottom_comment_editor_top(self, hierarchy, screen_size):
        if hierarchy is None or not screen_size:
            return None
        _, height = screen_size
        candidates = []
        for node in hierarchy.iter("node"):
            class_name = node.attrib.get("class", "").casefold()
            editable = node.attrib.get("editable", "false").casefold() == "true"
            if not ("edittext" in class_name or "autocompletetextview" in class_name or editable):
                continue
            bounds = self.parse_node_bounds(node)
            if not bounds:
                continue
            center_y = (bounds[1] + bounds[3]) // 2
            if center_y >= height * 0.55:
                candidates.append((center_y, bounds[1]))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]

    def find_comment_text_above_editor(
        self,
        records,
        expected_text,
        screen_size,
        section_top=None,
        editor_top=None,
    ):
        if not records or not expected_text or not screen_size:
            return False
        _, height = screen_size
        expected = self.normalize_search_text(expected_text)
        expected = re.sub(r"[^\w\s]", " ", expected, flags=re.UNICODE)
        expected = re.sub(r"\s+", " ", expected).strip()
        if len(expected) < 3:
            return False
        editor_top = int(editor_top if editor_top is not None else height * 0.98)
        section_top = int(section_top if section_top is not None else height * 0.55)
        section_headers = []
        for record in records:
            normalized = self.normalize_search_text(record.get("text", "")).strip()
            bounds = record.get("bounds")
            if not normalized or not bounds:
                continue
            if normalized.startswith(("escribe un comentario", "write a comment", "comenta como", "comentar como", "comment as", "add a comment")):
                editor_top = min(editor_top, bounds[1])
            if any(label in normalized for label in ("mas relevantes", "mas recientes", "todos los comentarios")):
                section_headers.append(bounds[3])
        if section_headers:
            section_top = max(section_headers)
        eligible = []
        for record in records:
            bounds = record.get("bounds")
            text_value = record.get("text", "").strip()
            if not bounds or not text_value:
                continue
            class_name = record.get("class", "").casefold()
            if record.get("editable") or "edittext" in class_name or "autocompletetextview" in class_name:
                continue
            center_y = (bounds[1] + bounds[3]) // 2
            normalized = self.normalize_search_text(text_value).strip()
            if normalized.startswith(("escribe un comentario", "write a comment", "comenta como", "comentar como", "comment as", "add a comment")):
                continue
            if center_y < section_top or bounds[3] >= editor_top - 3:
                continue
            eligible.append(record)
        eligible.sort(key=lambda record: (record["bounds"][1], record["bounds"][0]))
        for start in range(len(eligible)):
            parts = []
            previous_bottom = eligible[start]["bounds"][3]
            for end in range(start, min(len(eligible), start + 6)):
                record = eligible[end]
                if end > start and record["bounds"][1] - previous_bottom > height * 0.06:
                    break
                parts.append(record["text"])
                previous_bottom = record["bounds"][3]
                combined = self.normalize_search_text(" ".join(parts))
                combined = re.sub(r"[^\w\s]", " ", combined, flags=re.UNICODE)
                combined = re.sub(r"\s+", " ", combined).strip()
                if expected in combined:
                    return True
                length_ratio = min(len(expected), len(combined)) / max(1, max(len(expected), len(combined)))
                if length_ratio >= 0.72 and SequenceMatcher(None, expected, combined).ratio() >= 0.88:
                    return True
        return False

    def published_comment_visible(self, device, expected_text, checks=5, delay=1.0):
        size = self.get_device_screen_size(device)
        if not size:
            return False
        for attempt in range(max(1, checks)):
            hierarchy = self.get_android_hierarchy(device)
            records = self.accessibility_text_records(hierarchy)
            records.extend(self.windows_ocr_records(device))
            editor_top = self.bottom_comment_editor_top(hierarchy, size)
            visible_text = self.normalize_search_text(" ".join(record.get("text", "") for record in records))
            if any(message in visible_text for message in (
                "se publico tu comentario",
                "tu comentario se publico",
                "comentario publicado",
                "your comment was posted",
                "comment posted",
            )):
                self.log(f"[{device}] Comentario confirmado por el aviso de publicación de Facebook.")
                return True
            if self.find_comment_text_above_editor(
                records, expected_text, size, editor_top=editor_top
            ):
                self.log(f"[{device}] Comentario confirmado por su texto visible sobre el editor.")
                return True
            if attempt + 1 < checks and self.wait_or_cancel(delay, self.search_stop_event):
                return False
        return False

    def validate_recent_comment_after_actions(self, device, expected_text, max_scrolls=6):
        """Busca el comentario reciente debajo de Me gusta/Comentario/Compartir."""
        size = self.get_device_screen_size(device)
        if not size:
            return "inconclusive"
        width, height = size
        action_row_seen = False
        for attempt in range(max(0, max_scrolls) + 1):
            hierarchy = self.get_android_hierarchy(device)
            records = self.accessibility_text_records(hierarchy)
            records.extend(self.windows_ocr_records(device))
            editor_top = self.bottom_comment_editor_top(hierarchy, size)
            visible_text = self.normalize_search_text(
                " ".join(record.get("text", "") for record in records)
            )
            if any(message in visible_text for message in (
                "se publico tu comentario",
                "tu comentario se publico",
                "comentario publicado",
                "your comment was posted",
                "comment posted",
            )):
                self.log(f"[{device}] Comentario confirmado por el aviso de Facebook antes del reintento.")
                return "found"

            action_row = self.find_post_action_row(hierarchy, size)
            screen = self.capture_device_screen(device)
            action_points = []
            if screen is not None:
                for template_name, x_range in (
                    ("like_outline.png", (0.00, 0.38)),
                    ("comment_outline.png", (0.25, 0.68)),
                ):
                    match = self.locate_action_figure(screen, template_name, x_range)
                    if match:
                        action_points.append(match["point"])
            section_top = None
            if action_row:
                action_y = action_row["y"]
                action_row_seen = True
                section_top = action_row["bottom"] + max(8, int(height * 0.010))
                self.log(
                    f"[{device}] Fila completa de acciones localizada en y={action_y}; "
                    "validando debajo de ella."
                )
            elif len(action_points) >= 2:
                action_y = int(sum(point[1] for point in action_points) / len(action_points))
                action_row_seen = True
                section_top = action_y + max(12, int(height * 0.018))
                self.log(
                    f"[{device}] Figuras Me gusta y Comentar alineadas en y={action_y}; "
                    "validando debajo de ellas."
                )
            elif action_row_seen:
                section_top = int(height * 0.12)

            if action_row_seen and self.find_comment_text_above_editor(
                records,
                expected_text,
                size,
                section_top=section_top,
                editor_top=editor_top,
            ):
                self.log(
                    f"[{device}] Comentario reciente confirmado debajo de la fila de acciones; "
                    "se cancela el reintento."
                )
                return "found"

            if attempt >= max_scrolls:
                break
            ok, detail = self.run_on_device(
                device,
                [
                    "shell", "input", "swipe",
                    str(width // 2), str(int(height * 0.74)),
                    str(width // 2), str(int(height * 0.50)), "550",
                ],
                timeout=15,
            )
            if not ok:
                self.log(f"[{device}] No se pudo desplazar para validar el comentario: {detail}")
                return "inconclusive"
            if self.wait_or_cancel(0.85, self.search_stop_event):
                return "cancelled"

        if not action_row_seen:
            self.log(
                f"[{device}] No se localizó la fila Me gusta/Comentario/Compartir; "
                "no se reintentará para evitar duplicidad."
            )
            return "inconclusive"
        self.log(f"[{device}] La fila de acciones se revisó, pero el comentario reciente no apareció.")
        return "not_found"

    def perform_search_post_comment_once(self, device, comment_text, post_reference=None):
        size = self.get_device_screen_size(device)
        if not size:
            return "screen_error"
        width, height = size
        action_row = self.scroll_to_post_action_row(
            device,
            size,
            stop_event=self.search_stop_event,
            max_scrolls=18,
            post_reference=post_reference,
        )
        if not action_row:
            return "action_row_not_found"
        comment_visual = action_row.get("comment_visual")
        action_point = comment_visual["point"] if comment_visual else action_row["comment"]
        ok, detail = self.run_on_device(
            device,
            ["shell", "input", "tap", str(action_point[0]), str(action_point[1])],
            timeout=15,
        )
        if not ok:
            self.log(f"[{device}] No se pudo abrir Comentario desde la fila confirmada: {detail}")
            return "comment_action_error"
        self.log(
            f"[{device}] Comentar pulsado en {action_point} dentro de la fila completa confirmada."
        )
        if self.wait_or_cancel(0.9, self.search_stop_event):
            return "cancelled"
        comment_point = None
        comment_opened = True
        for attempt in range(9):
            hierarchy = self.get_android_hierarchy(device)
            comment_point = self.find_accessible_control(
                hierarchy,
                exact_labels=("escribe un comentario", "write a comment", "comenta como", "comment as"),
                prefix_labels=("escribe un comentario", "write a comment", "comenta como", "comentar como", "comment as", "add a comment"),
                screen_size=size,
                ignore_top_pct=0.20,
                allow_nonclickable=True,
            ) or self.find_bottom_editable_control(hierarchy, size)
            if comment_point:
                break
            if not comment_opened:
                result = self.apply_calculated_figure_action(device, "comment", self.search_stop_event)
                if result == "sent":
                    comment_opened = True
                    if self.wait_or_cancel(1.3, self.search_stop_event):
                        return "cancelled"
                    continue
            if attempt < 8:
                ok, _ = self.run_on_device(
                    device,
                    ["shell", "input", "swipe", str(width//2), str(int(height*0.72)), str(width//2), str(int(height*0.34)), "650"],
                    timeout=15,
                )
                if not ok or self.wait_or_cancel(0.9, self.search_stop_event):
                    break
        if not comment_point:
            return "field_not_found"
        ok, _ = self.run_on_device(
            device, ["shell", "input", "tap", str(comment_point[0]), str(comment_point[1])], timeout=15
        )
        if not ok or self.wait_or_cancel(0.8, self.search_stop_event):
            return "field_error"
        if not self.clear_focused_text(device, 500):
            return "clear_error"
        if self.wait_or_cancel(0.3, self.search_stop_event):
            return "cancelled"
        if not self.inject_text_adb(device, comment_text):
            return "write_error"
        if self.wait_or_cancel(0.9, self.search_stop_event):
            return "cancelled"
        text_verified = self.visible_text_contains(device, comment_text)
        if not text_verified:
            text_verified = bool(self.locate_blue_send_arrow(self.capture_device_screen(device)))
        if not text_verified:
            self.clear_focused_text(device, len(comment_text))
            return "text_not_verified"
        hierarchy = self.get_android_hierarchy(device)
        publish_point = self.find_accessible_control(
            hierarchy,
            exact_labels=("publicar", "publicar comentario", "enviar comentario", "post", "send"),
            prefix_labels=("publicar comentario", "enviar comentario", "post comment", "send comment"),
            screen_size=size,
            allow_nonclickable=True,
        )
        if publish_point:
            ok, _ = self.run_on_device(
                device, ["shell", "input", "tap", str(publish_point[0]), str(publish_point[1])], timeout=15
            )
            if not ok:
                return "send_error"
        elif not self.tap_blue_send_arrow(
            device, attempts=3, delay=0.45, stop_event=self.search_stop_event
        ):
            return "send_not_found"
        if self.wait_or_cancel(1.5, self.search_stop_event):
            return "cancelled"
        return "sent" if self.published_comment_visible(device, comment_text, checks=5, delay=1.0) else "not_confirmed"

    def perform_search_post_comment(self, device, comment_text, post_reference=None):
        last_result = "not_confirmed"
        for attempt in range(2):
            last_result = self.perform_search_post_comment_once(
                device,
                comment_text,
                post_reference=post_reference if attempt == 0 else None,
            )
            if last_result == "sent":
                return "sent" if attempt == 0 else "sent_after_retry"
            if last_result == "cancelled" or self.search_stop_event.is_set():
                return last_result
            if attempt == 0:
                if self.wait_or_cancel(1.5, self.search_stop_event):
                    return "cancelled"
                validation = self.validate_recent_comment_after_actions(device, comment_text)
                if validation == "found":
                    return "sent_scrolled_confirmed"
                if validation in {"cancelled", "inconclusive"}:
                    self.log(
                        f"[{device}] Validación final {validation}; no se reintentará el comentario "
                        "para evitar duplicidad."
                    )
                    return "cancelled" if validation == "cancelled" else "validation_inconclusive"
                self.log(
                    f"[{device}] El comentario no apareció después de pasar la fila de acciones; "
                    "se realizará un único reintento."
                )
                if self.wait_or_cancel(0.8, self.search_stop_event):
                    return "cancelled"
        self.log(f"[{device}] El comentario no se confirmó después del reintento; se continuará con la siguiente publicación.")
        return "not_confirmed_after_retry"

    def confirm_open_post(self, device, screen_size, attempts=3, delay=0.55):
        """Confirma que Facebook está en una publicación antes de ejecutar acciones."""
        for attempt in range(max(1, attempts)):
            hierarchy = self.get_android_hierarchy(device)
            records = self.accessibility_text_records(hierarchy)
            if self.is_open_post_view(records, screen_size) or self.is_open_post_hierarchy(hierarchy, screen_size):
                return True
            records.extend(self.windows_ocr_records(device))
            if self.is_open_post_view(records, screen_size):
                return True
            if attempt + 1 < attempts and self.wait_or_cancel(delay, self.search_stop_event):
                return False
        return False

    def confirm_actionable_open_post(
        self, device, screen_size, attempts=2, delay=0.45, post_reference=None
    ):
        """Confirma publicación, ausencia de `<` inferior e identidad del encabezado."""
        for attempt in range(max(1, attempts)):
            hierarchy = self.get_android_hierarchy(device)
            records = self.accessibility_text_records(hierarchy)
            ocr_records = self.windows_ocr_records(device)
            records.extend(ocr_records)
            if self.is_facebook_feed_hierarchy(hierarchy, screen_size):
                return False
            screen = self.capture_device_screen(device)
            back_control = self.find_intermediate_back_control(
                hierarchy, screen_size, ocr_records, screen=screen
            )
            if back_control:
                self.log(
                    f"[{device}] Aún existe un control < inferior en {back_control['point']}; "
                    "la publicación no está lista para acciones."
                )
                return False
            if (
                self.is_open_post_view(records, screen_size)
                or self.is_open_post_hierarchy(hierarchy, screen_size)
            ):
                if self.post_reference_matches(records, post_reference):
                    return True
                expected = (post_reference or {}).get("header_anchor", "")
                self.log(
                    f"[{device}] Hay una publicación abierta, pero no coincide con el "
                    f"encabezado guardado '{expected}'; no se iniciarán acciones."
                )
                return False
            if attempt + 1 < attempts and self.wait_or_cancel(delay, self.search_stop_event):
                return False
        return False

    def open_search_match_post(self, device, snapshot, screen_size):
        point = snapshot["timestamp_point"]
        self.log(
            f"[{device}] Coincidencia asociada a fecha/hora '{snapshot['timestamp_text']}' "
            f"por {snapshot['source']}; abriendo en {point}."
        )
        for attempt in range(2):
            ok, detail = self.run_on_device(
                device, ["shell", "input", "tap", str(point[0]), str(point[1])], timeout=15
            )
            if not ok:
                self.log(f"[{device}] No se pudo abrir la publicación coincidente: {detail}")
                return False
            if self.wait_or_cancel(1.5 if attempt == 0 else 1.0, self.search_stop_event):
                return False
            if self.confirm_open_post(device, screen_size, attempts=2):
                self.log(f"[{device}] Publicación coincidente abierta y confirmada.")
                return True
            if attempt == 0:
                self.log(f"[{device}] El primer toque no abrió la publicación; se reintentará una vez.")
        self.log(f"[{device}] No se confirmó la apertura; no se obtendrá enlace ni se ejecutarán acciones.")
        return False

    def perform_selected_search_actions(
        self,
        device,
        like_on_match,
        comment_on_match,
        comment_text,
        like_min,
        like_max,
        post_reference=None,
    ):
        """Ejecuta exclusivamente las acciones marcadas en la pestaña Búsqueda."""
        like_result = None
        comment_result = None
        if not like_on_match and not comment_on_match:
            return like_result, comment_result
        chosen_wait = random.randint(like_min, like_max)
        selected = "Me gusta y Comentario" if like_on_match and comment_on_match else (
            "Me gusta" if like_on_match else "Comentario"
        )
        self.log(f"[{device}] Acciones seleccionadas: {selected}; espera previa {chosen_wait} s.")
        self.post_ui(
            lambda d=device, s=chosen_wait: self.search_status_var.set(
                f"Publicación abierta en {d}; acciones en {s} s. Pulsa Detener para cancelar."
            )
        )
        if self.wait_or_cancel(chosen_wait, self.search_stop_event):
            return "cancelled" if like_on_match else None, "cancelled" if comment_on_match else None
        if like_on_match:
            like_result = self.perform_search_post_like(device, post_reference=post_reference)
        if comment_on_match and not self.search_stop_event.is_set():
            comment_result = self.perform_search_post_comment(
                device,
                self.parse_spintax(comment_text),
                post_reference=None if like_on_match else post_reference,
            )
        return like_result, comment_result

    def return_to_feed_after_post(self, device):
        size = self.get_device_screen_size(device) or (1080, 1920)
        for depth in range(4):
            hierarchy = self.get_android_hierarchy(device)
            records = self.accessibility_text_records(hierarchy)
            ocr_records = self.windows_ocr_records(device)
            records.extend(ocr_records)
            if not (
                self.is_open_post_view(records, size)
                or self.is_open_post_hierarchy(hierarchy, size)
            ):
                self.log(f"[{device}] Regreso al feed confirmado; se continuará el scroll.")
                return True
            back_control = self.find_open_post_back_control(hierarchy, size, ocr_records)
            if back_control:
                point = back_control["point"]
                self.log(
                    f"[{device}] Publicación abierta: control < identificado por "
                    f"{back_control['source']} en {point}; regresando al feed."
                )
                ok, detail = self.run_on_device(
                    device,
                    ["shell", "input", "tap", str(point[0]), str(point[1])],
                    timeout=15,
                )
                if not ok:
                    self.log(f"[{device}] No se pudo pulsar el control <: {detail}")
                    return False
            else:
                self.log(
                    f"[{device}] La publicación sigue abierta, pero no se identificó el control <; "
                    "se usa Atrás de Android como respaldo."
                )
                ok, detail = self.run_on_device(
                    device, ["shell", "input", "keyevent", "4"], timeout=15
                )
                if not ok:
                    self.log(f"[{device}] No se pudo ejecutar Atrás: {detail}")
                    return False
            if self.wait_or_cancel(1.0, self.search_stop_event):
                return False
            self.log(f"[{device}] Regreso {depth + 1}: comprobando si la publicación era anidada.")
        if not self.confirm_open_post(device, size, attempts=1):
            self.log(f"[{device}] Regreso al feed confirmado; se continuará el scroll.")
            return True
        self.log(f"[{device}] No se confirmó el feed después de cuatro regresos; se omite el siguiente scroll.")
        return False

    def keyword_search_worker(
        self,
        devices,
        keys,
        like_on_match=False,
        save_link_on_match=True,
        comment_on_match=False,
        comment_text="",
        like_min=3,
        like_max=8,
        continuous=True,
    ):
        norm_keys = self.prepare_search_terms(keys)
        step = 0
        max_scrolls = 20
        seen = set()
        found_count = 0
        ad_guard = {device: 0 for device in devices}
        scroll_ready = {device: True for device in devices}
        while not self.search_stop_event.is_set() and (continuous or step < max_scrolls):
            stop_after_match = False
            for dev in devices:
                if self.search_stop_event.is_set(): break
                try:
                    size = self.get_device_screen_size(dev)
                    if not size:
                        continue
                    hierarchy, accessibility_records, cached_ocr, _ = self.expand_visible_see_more(dev, size)
                    geometry_records = self.hierarchy_timestamp_records(hierarchy, size)
                    ocr_records = cached_ocr if cached_ocr is not None else self.windows_ocr_records(dev)
                    records = accessibility_records + ocr_records + geometry_records
                    if self.is_open_post_view(records, size):
                        self.log(
                            f"[{dev}] Facebook abrió una publicación durante el scroll sin coincidencia validada; "
                            "se regresa al feed sin ejecutar acciones."
                        )
                        scroll_ready[dev] = self.return_to_feed_after_post(dev)
                        ad_guard[dev] = 2
                        self.wait_or_cancel(1.2, self.search_stop_event)
                        continue
                    ad_visible = any(self.is_ad_label_record(record) for record in records)
                    if ad_visible:
                        ad_guard[dev] = 2
                        self.log(f"[{dev}] Publicidad detectada; se ignora el bloque completo y su continuación.")
                        continue
                    snapshot = self.find_post_match_snapshot(records, norm_keys, size)
                    if ad_guard[dev] > 0:
                        if snapshot is None:
                            ad_guard[dev] -= 1
                            self.log(f"[{dev}] Se omite la continuación visible del bloque publicitario.")
                            continue
                        ad_guard[dev] = 0
                        self.log(
                            f"[{dev}] Se detectó una publicación nueva con fecha/hora válida; "
                            "finaliza la protección del anuncio anterior."
                        )
                    if snapshot is None:
                        continue
                    fingerprint = (dev, hash(snapshot["fingerprint"]))
                    if fingerprint in seen:
                        continue
                    if len(seen) >= 1000:
                        seen.clear()
                    seen.add(fingerprint)
                    should_open_post = save_link_on_match or like_on_match or comment_on_match
                    post_url = None
                    record_path = None
                    link_added = False
                    like_result = None
                    comment_result = None
                    post_reference = self.post_reference_from_snapshot(snapshot)
                    if should_open_post:
                        if not self.open_search_match_post(dev, snapshot, size):
                            seen.discard(fingerprint)
                            continue
                        if save_link_on_match:
                            post_url = self.capture_open_post_link(
                                dev, size, post_reference=post_reference
                            )
                            record_path, link_added = self.save_search_link_record(dev, snapshot, post_url)
                        if like_on_match or comment_on_match:
                            post_ready = self.confirm_actionable_open_post(
                                dev,
                                size,
                                attempts=2,
                                post_reference=post_reference,
                            )
                            if not post_ready:
                                self.log(
                                    f"[{dev}] Después de obtener el enlace no se confirmó la publicación; "
                                    "se intentará recuperar la pantalla intermedia antes de las acciones."
                                )
                                post_ready = self.return_from_settings_to_post(
                                    dev,
                                    size,
                                    post_url=post_url,
                                    post_reference=post_reference,
                                )
                            if post_ready:
                                like_result, comment_result = self.perform_selected_search_actions(
                                    dev,
                                    like_on_match,
                                    comment_on_match,
                                    comment_text,
                                    like_min,
                                    like_max,
                                    post_reference=post_reference,
                                )
                            else:
                                self.log(
                                    f"[{dev}] No se recuperó la publicación exacta después del enlace; "
                                    "se omiten Me gusta y Comentario para no actuar en otra pantalla."
                                )
                    else:
                        self.log(
                            f"[{dev}] Coincidencia asociada a fecha/hora '{snapshot['timestamp_text']}' "
                            "contabilizada sin abrir la publicación."
                        )
                    found_count += 1
                    ctx = {
                        "device": dev,
                        "matches": snapshot["matches"],
                        "preview": snapshot["preview"],
                        "timestamp": snapshot["timestamp_text"],
                        "url": post_url,
                        "record_path": str(record_path) if record_path else "",
                    }
                    details = []
                    if like_result:
                        details.append(f"Me gusta: {like_result}")
                    if comment_result:
                        details.append(f"Comentario: {comment_result}")
                    if details:
                        suffix = f" · {' · '.join(details)}"
                    elif should_open_post:
                        suffix = " · publicación abierta"
                    else:
                        suffix = " · coincidencia contabilizada"
                    link_line = ""
                    if save_link_on_match:
                        link_text = post_url or "no disponible"
                        record_text = " · guardado en registro diario" if post_url and link_added else ""
                        link_line = f"\nEnlace: {link_text}{record_text}"
                    status = "La búsqueda continúa; pulsa Detener." if continuous else "Coincidencia encontrada."
                    self.post_ui(
                        lambda m=(
                            f"Coincidencia #{found_count} en {dev}: "
                            f"{', '.join(snapshot['matches'])}{suffix}"
                            f"{link_line}"
                        ), st=status, c=ctx: self.report_match(m, st, c)
                    )
                    if comment_result and comment_result not in {
                        "sent", "sent_late_confirmed", "sent_scrolled_confirmed",
                        "sent_after_retry", "cancelled",
                    }:
                        self.log(
                            f"[{dev}] Comentario sin confirmación final ({comment_result}); "
                            "se saldrá de la publicación y continuará la búsqueda."
                        )
                    if should_open_post:
                        returned_to_feed = self.return_to_feed_after_post(dev)
                        scroll_ready[dev] = returned_to_feed
                        if not returned_to_feed:
                            ad_guard[dev] = 2
                    if not continuous:
                        stop_after_match = True
                        break
                except Exception as e: self.log(f"Error {dev}: {e}")
            if stop_after_match or self.search_stop_event.is_set():
                break
            for dev in devices:
                if not self.search_stop_event.is_set() and scroll_ready.get(dev, True):
                    self.scroll_device_once_random(dev)
            step += 1
            if self.search_stop_event.wait(2.0):
                break
        if self.search_stop_event.is_set():
            message, status = f"Búsqueda detenida manualmente. Coincidencias: {found_count}.", "Detenida"
        elif stop_after_match:
            message, status = "Búsqueda detenida en la primera coincidencia.", "Coincidencia encontrada"
        else:
            message, status = "Búsqueda completada sin coincidencias nuevas.", "Completada"
        self.post_ui(lambda m=message, s=status: self.finish_search(m, s))

    def report_match(self, msg, status, ctx):
        self.append_search_result(msg); self.pending_search_match = ctx; self.search_status_var.set(status)

    def finish_search(self, msg, status):
        self.append_search_result(msg); self.search_status_var.set(status)
        self.btn_start_search.config(state="normal"); self.btn_stop_search.config(state="disabled")
        self.search_running = False
        for device in self.search_devices:
            self.restore_device_task(device, "Búsqueda por palabras", None)
            self.release_device(device)
        self.search_devices = []

    def stop_keyword_search(self): self.search_stop_event.set()

    def execute_vision_reaction(self, template_filename):
        template_path = self.templates_dir / template_filename
        if not template_path.exists(): return messagebox.showerror("Error", f"No se encontró {template_filename}")
        def task(dev):
            try:
                res = subprocess.run([self.adb, "-s", dev, "exec-out", "screencap", "-p"], stdout=subprocess.PIPE, creationflags=NO_WINDOW)
                if not res.stdout: return
                screen = cv2.imdecode(np.frombuffer(res.stdout, np.uint8), cv2.IMREAD_COLOR)
                tmpl = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
                if tmpl is None: return
                
                gray_screen = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
                gray_tmpl = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)

                best_score = 0.0
                best_loc = None
                best_shape = None

                for f in np.linspace(0.7, 1.3, 13):
                    p = cv2.resize(gray_tmpl, None, fx=f, fy=f)
                    if p.shape[0] > gray_screen.shape[0] or p.shape[1] > gray_screen.shape[1]:
                        continue
                    match = cv2.matchTemplate(gray_screen, p, cv2.TM_CCOEFF_NORMED)
                    _, score, _, loc = cv2.minMaxLoc(match)
                    if score > best_score:
                        best_score = score
                        best_loc = loc
                        best_shape = p.shape

                if best_score >= 0.80 and best_loc is not None:
                    th, tw = best_shape
                    cx = best_loc[0] + tw // 2
                    cy = best_loc[1] + th // 2
                    self.run_on_device(dev, ["shell", "input", "tap", str(cx), str(cy)])
                    self.log(f"[{dev}] Reacción enviada (Score: {best_score:.2f})")
            except Exception as e: self.log(f"Error en visión [{dev}]: {e}")
        self.execute_multithreaded(task, "Reacción visual")

    def begin_interaction_process(self, devices, label):
        self.interaction_stop_event.clear()
        with self.device_tasks_lock:
            self.interaction_running = True
            self.interaction_devices = set(devices)
        self.btn_start_selected.config(state="disabled")
        self.btn_stop_interaction.config(state="normal")
        self.interaction_status_var.set(label)

    def finish_interaction_device(self, device):
        with self.device_tasks_lock:
            self.interaction_devices.discard(device)
            finished = not self.interaction_devices
            if finished:
                self.interaction_running = False
        if finished:
            self.post_ui(self.finish_interaction_process)

    def finish_interaction_process(self):
        if self.combined_next_action == "comment" and not self.interaction_stop_event.is_set():
            self.combined_next_action = None
            self.interaction_status_var.set("Me gusta completado; iniciando Comentario...")
            self.start_comment_only_interaction()
            return
        self.btn_start_selected.config(state="normal")
        self.btn_stop_interaction.config(state="disabled")
        status = "Detenido" if self.interaction_stop_event.is_set() else "Completado"
        self.interaction_status_var.set(status)

    def stop_interaction_process(self):
        if not self.interaction_running:
            return
        self.combined_next_action = None
        self.interaction_stop_event.set()
        self.btn_stop_interaction.config(state="disabled")
        self.interaction_status_var.set("Deteniendo...")
        self.log("Interacciones: detención solicitada por el operador.")

    def start_selected_interactions(self):
        if self.interaction_running:
            return messagebox.showwarning("Proceso activo", "Detén o espera a que termine la interacción actual.")
        do_like = bool(self.int_do_like_var.get())
        do_comment = bool(self.int_do_comment_var.get())
        if not do_like and not do_comment:
            return messagebox.showwarning("Aviso", "Marca Me gusta, Comentario o ambas acciones.")
        if do_comment and not self.text_int_comment.get("1.0", tk.END).strip():
            return messagebox.showwarning("Aviso", "Escribe el texto del comentario.")
        self.combined_next_action = "comment" if do_like and do_comment else None
        if do_like:
            self.start_like_only_interaction()
            if not self.interaction_running:
                self.combined_next_action = None
        else:
            self.start_comment_only_interaction()

    def start_like_only_interaction(self):
        if self.interaction_running:
            return messagebox.showwarning("Proceso activo", "Detén o espera a que termine la interacción actual.")
        url = self.entry_int_url.get().strip()
        do_airplane = self.int_airplane_var.get()
        do_warmup = self.int_warmup_var.get()
        calculated_click = bool(self.int_calculated_click_var.get())
        reel_mode = bool(self.int_reel_mode_var.get())
        target_devs = self.get_selected_devices()
        if not target_devs: return messagebox.showwarning("Aviso", "Selecciona al menos un celular.")
        if not self.is_facebook_url(url):
            return messagebox.showwarning("Aviso", "Ingresa una URL válida de Facebook.")
        try:
            l_min, l_max = float(self.int_load_min.get()), float(self.int_load_max.get())
            if l_min < 0 or l_max < l_min:
                raise ValueError
        except ValueError:
            return messagebox.showwarning("Intervalo no válido", "Revisa el tiempo mínimo y máximo de carga.")
        try:
            calculated_scrolls = int(self.int_calculated_scrolls_var.get())
            if not 0 <= calculated_scrolls <= 30:
                raise ValueError
        except ValueError:
            return messagebox.showwarning("Desplazamientos no válidos", "Usa un valor entero de 0 a 30.")
        target_devs, busy = self.claim_devices(target_devs, "Solo Me gusta")
        if not target_devs:
            return messagebox.showwarning("Equipos ocupados", "Los equipos seleccionados ya ejecutan otra acción.")
        if busy:
            messagebox.showinfo("Equipos ocupados", "Se omitieron equipos que ya ejecutan otra acción.")
        self.begin_interaction_process(target_devs, "Me gusta en curso...")
        for idx, dev in enumerate(target_devs):
            delay = idx * 4.0
            def task(d=dev, wait_sec=delay):
                prev = self.device_tasks.get(d)
                self.set_device_task(d, "Solo Like FB Lite")
                try:
                    if wait_sec > 0 and self.wait_or_cancel(wait_sec, self.interaction_stop_event): return
                    if self.app_closing.is_set() or self.interaction_stop_event.is_set(): return
                    if do_airplane and not self.toggle_airplane_mode(d, self.interaction_stop_event): return
                    if do_warmup and not self.simular_navegacion_organica(d, 5.0, 15.0, self.interaction_stop_event): return
                    ok, detail = self.run_on_device(d, ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url, "com.facebook.lite"])
                    if not ok:
                        self.log(f"[{d}] No se pudo abrir la publicación: {detail}")
                        return
                    if self.wait_or_cancel(random.uniform(l_min, l_max), self.interaction_stop_event): return
                    size = self.get_device_screen_size(d)
                    if not size: return
                    w, h = size
                    result = "not_found"
                    if reel_mode:
                        hierarchy = self.get_android_hierarchy(d)
                        result = self.apply_reel_action(
                            d, "like", hierarchy, size, self.interaction_stop_event
                        )
                    else:
                        search_scrolls = calculated_scrolls if calculated_click else 2
                        # Analiza primero la pantalla tal como abrió el enlace y vuelve
                        # a analizar después de cada desplazamiento hasta encontrarlo.
                        for attempt in range(search_scrolls + 1):
                            hierarchy = self.get_android_hierarchy(d)
                            result = self.apply_like_action(d, hierarchy, stop_event=self.interaction_stop_event)
                            if result == "not_found" and calculated_click:
                                result = self.apply_calculated_figure_action(d, "like", self.interaction_stop_event)
                            if result != "not_found":
                                break
                            if attempt < search_scrolls:
                                if calculated_click:
                                    start_y, end_y, duration = int(h * 0.80), int(h * 0.32), "700"
                                    self.log(
                                        f"[{d}] Manita no localizada; desplazamiento largo {attempt + 1}/{search_scrolls}."
                                    )
                                else:
                                    start_y, end_y, duration = int(h * 0.58), int(h * 0.46), "650"
                                ok, detail = self.run_on_device(
                                    d,
                                    ["shell", "input", "swipe", str(w//2), str(start_y), str(w//2), str(end_y), duration],
                                    timeout=15,
                                )
                                if not ok:
                                    self.log(f"[{d}] No se pudo ajustar la publicación: {detail}")
                                    break
                                if self.wait_or_cancel(1.0, self.interaction_stop_event): return
                    if result == "not_found" and not reel_mode:
                        if self.tap_image_template(d, "like.png"):
                            if self.wait_or_cancel(0.8, self.interaction_stop_event): return
                            updated = self.get_android_hierarchy(d)
                            state, _ = self.find_like_control(updated)
                            if state == "already_liked":
                                self.log(f"[{d}] Me gusta confirmado después del reconocimiento visual.")
                            else:
                                self.log(f"[{d}] Toque visual enviado; estado de Me gusta no confirmado.")
                        else:
                            self.log(f"[{d}] No se encontró un control seguro para Me gusta; no se tocó por coordenadas.")
                    elif result == "not_found" and reel_mode:
                        self.log(f"[{d}] No se encontró un control seguro para Me gusta en el Reel.")
                    if self.wait_or_cancel(2.0, self.interaction_stop_event): return
                    self.run_on_device(d, ["shell", "input", "keyevent", "4"])
                except Exception as error:
                    self.log(f"[{d}] Error en Solo Me gusta: {error}")
                finally:
                    self.release_device(d)
                    self.finish_interaction_device(d)
                    self.post_ui(lambda device=d, previous=prev: self.restore_device_task(device, "Solo Like FB Lite", previous))
            threading.Thread(target=task, daemon=True).start()

    def start_comment_only_interaction(self):
        if self.interaction_running:
            return messagebox.showwarning("Proceso activo", "Detén o espera a que termine la interacción actual.")
        url = self.entry_int_url.get().strip()
        do_airplane = self.int_airplane_var.get()
        do_warmup = self.int_warmup_var.get()
        calculated_click = bool(self.int_calculated_click_var.get())
        reel_mode = bool(self.int_reel_mode_var.get())
        raw_comment_text = self.text_int_comment.get("1.0", tk.END).strip()
        target_devs = self.get_selected_devices()
        if not target_devs: return messagebox.showwarning("Aviso", "Selecciona al menos un celular.")
        if not self.is_facebook_url(url):
            return messagebox.showwarning("Aviso", "Ingresa una URL válida de Facebook.")
        if not raw_comment_text: return messagebox.showwarning("Aviso", "Escribe el texto del comentario.")
        try:
            l_min, l_max = float(self.int_load_min.get()), float(self.int_load_max.get())
            if l_min < 0 or l_max < l_min:
                raise ValueError
        except ValueError:
            return messagebox.showwarning("Intervalo no válido", "Revisa el tiempo mínimo y máximo de carga.")
        try:
            calculated_scrolls = int(self.int_calculated_scrolls_var.get())
            if not 0 <= calculated_scrolls <= 30:
                raise ValueError
        except ValueError:
            return messagebox.showwarning("Desplazamientos no válidos", "Usa un valor entero de 0 a 30.")
        target_devs, busy = self.claim_devices(target_devs, "Solo comentario")
        if not target_devs:
            return messagebox.showwarning("Equipos ocupados", "Los equipos seleccionados ya ejecutan otra acción.")
        if busy:
            messagebox.showinfo("Equipos ocupados", "Se omitieron equipos que ya ejecutan otra acción.")
        self.begin_interaction_process(target_devs, "Comentario en curso...")
        for idx, dev in enumerate(target_devs):
            unique_text = self.parse_spintax(raw_comment_text)
            delay = idx * 4.0
            def task(d=dev, wait_sec=delay, txt=unique_text):
                prev = self.device_tasks.get(d)
                self.set_device_task(d, "Solo Comentario FB Lite")
                try:
                    if wait_sec > 0 and self.wait_or_cancel(wait_sec, self.interaction_stop_event): return
                    if self.app_closing.is_set() or self.interaction_stop_event.is_set(): return
                    if do_airplane and not self.toggle_airplane_mode(d, self.interaction_stop_event): return
                    if do_warmup and not self.simular_navegacion_organica(d, 5.0, 15.0, self.interaction_stop_event): return
                    ok, detail = self.run_on_device(d, ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url, "com.facebook.lite"])
                    if not ok:
                        self.log(f"[{d}] No se pudo abrir la publicación: {detail}")
                        return
                    if self.wait_or_cancel(random.uniform(l_min, l_max), self.interaction_stop_event): return
                    size = self.get_device_screen_size(d)
                    if not size: return
                    comment_point = None
                    comment_action_opened = False
                    if reel_mode:
                        hierarchy = self.get_android_hierarchy(d)
                        reel_result = self.apply_reel_action(
                            d, "comment", hierarchy, size, self.interaction_stop_event
                        )
                        if reel_result != "sent":
                            self.log(f"[{d}] No se pudo abrir Comentarios desde el control lateral del Reel.")
                            return
                        comment_action_opened = True
                        if self.wait_or_cancel(1.4, self.interaction_stop_event): return
                        search_scrolls = 0
                    else:
                        search_scrolls = calculated_scrolls if calculated_click else 2
                    for attempt in range(search_scrolls + 1):
                        hierarchy = self.get_android_hierarchy(d)
                        comment_point = self.find_accessible_control(
                            hierarchy,
                            exact_labels=("escribe un comentario", "write a comment", "comenta como", "comment as"),
                            prefix_labels=("escribe un comentario", "write a comment", "comenta como", "comentar como", "comment as", "add a comment"),
                            screen_size=size,
                            ignore_top_pct=0.20,
                            allow_nonclickable=True,
                        )
                        if not comment_point:
                            comment_point = self.find_bottom_editable_control(hierarchy, size)
                        if comment_point:
                            break
                        if not reel_mode and calculated_click and not comment_action_opened:
                            visual_result = self.apply_calculated_figure_action(
                                d, "comment", self.interaction_stop_event
                            )
                            if visual_result == "sent":
                                comment_action_opened = True
                                if self.wait_or_cancel(1.4, self.interaction_stop_event): return
                                hierarchy = self.get_android_hierarchy(d)
                                comment_point = self.find_accessible_control(
                                    hierarchy,
                                    exact_labels=("escribe un comentario", "write a comment", "comenta como", "comment as"),
                                    prefix_labels=("escribe un comentario", "write a comment", "comenta como", "comentar como", "comment as", "add a comment"),
                                    screen_size=size,
                                    ignore_top_pct=0.20,
                                    allow_nonclickable=True,
                                ) or self.find_bottom_editable_control(hierarchy, size)
                                if comment_point:
                                    break
                        if attempt < search_scrolls:
                            w, h = size
                            ok, detail = self.run_on_device(
                                d,
                                ["shell", "input", "swipe", str(w//2), str(int(h*0.58)), str(w//2), str(int(h*0.46)), "650"],
                                timeout=15,
                            )
                            if not ok:
                                self.log(f"[{d}] No se pudo ajustar la publicación para buscar el comentario: {detail}")
                                break
                            if self.wait_or_cancel(1.0, self.interaction_stop_event): return
                    if not comment_point:
                        self.log(f"[{d}] No se encontró el campo exacto de comentario; no se tocó por coordenadas.")
                        return
                    ok, detail = self.run_on_device(d, ["shell", "input", "tap", str(comment_point[0]), str(comment_point[1])], timeout=15)
                    if not ok:
                        self.log(f"[{d}] No se pudo activar el campo de comentario: {detail}")
                        return
                    if self.wait_or_cancel(1.0, self.interaction_stop_event): return
                    if not self.clear_focused_text(d, 500):
                        self.log(f"[{d}] El editor conservó texto anterior; no se escribirá ni publicará otro comentario.")
                        return
                    if self.wait_or_cancel(0.4, self.interaction_stop_event): return
                    if not self.inject_text_adb(d, txt): return
                    if self.wait_or_cancel(1.0, self.interaction_stop_event): return
                    text_verified = self.visible_text_contains(d, txt)
                    if not text_verified and (calculated_click or reel_mode):
                        ready_screen = self.capture_device_screen(d)
                        text_verified = bool(self.locate_blue_send_arrow(ready_screen))
                        if text_verified:
                            self.log(
                                f"[{d}] Facebook no expone el texto a accesibilidad; la flecha azul activa confirma que el editor contiene texto."
                            )
                    if not text_verified:
                        self.clear_focused_text(d, len(txt))
                        self.log(f"[{d}] No se confirmó texto en el editor; no se intentará publicar.")
                        return
                    hierarchy = self.get_android_hierarchy(d)
                    publish_point = self.find_accessible_control(
                        hierarchy,
                        exact_labels=("publicar", "publicar comentario", "enviar comentario", "post", "send"),
                        prefix_labels=("publicar comentario", "enviar comentario", "post comment", "send comment"),
                        screen_size=size,
                        allow_nonclickable=True,
                    )
                    if publish_point:
                        ok, detail = self.run_on_device(d, ["shell", "input", "tap", str(publish_point[0]), str(publish_point[1])], timeout=15)
                        if not ok:
                            self.log(f"[{d}] No se pudo pulsar Publicar: {detail}")
                            return
                    elif (calculated_click or reel_mode) and self.tap_blue_send_arrow(
                        d, attempts=3, delay=0.45, stop_event=self.interaction_stop_event
                    ):
                        self.log(f"[{d}] Envío solicitado mediante la flecha azul calculada.")
                    else:
                        self.log(f"[{d}] No se encontró el botón ni la flecha azul de envío; el comentario queda sin enviar.")
                        return
                    if self.wait_or_cancel(2.5, self.interaction_stop_event): return
                    still_visible = self.visible_text_contains(d, txt)
                    if not still_visible and (calculated_click or reel_mode):
                        remaining_screen = self.capture_device_screen(d)
                        still_visible = bool(self.locate_blue_send_arrow(remaining_screen))
                    if still_visible:
                        self.log(f"[{d}] Publicar fue pulsado, pero el envío del comentario no quedó confirmado.")
                        return
                    else:
                        self.log(f"[{d}] Comentario enviado y confirmado por el cambio de pantalla.")
                    self.run_on_device(d, ["shell", "input", "keyevent", "4"])
                except Exception as error:
                    self.log(f"[{d}] Error en Solo comentario: {error}")
                finally:
                    self.release_device(d)
                    self.finish_interaction_device(d)
                    self.post_ui(lambda device=d, previous=prev: self.restore_device_task(device, "Solo Comentario FB Lite", previous))
            threading.Thread(target=task, daemon=True).start()

    def start_human_warming(self):
        target_devs = self.get_selected_devices()
        if not target_devs: return messagebox.showwarning("Aviso", "Selecciona al menos un celular.")
        try: duration_mins = float(self.hum_duration_var.get())
        except ValueError: duration_mins = 30.0
        self.human_stop_event.clear(); self.human_running = True
        self.btn_start_human.config(state="disabled"); self.btn_stop_human.config(state="normal")
        self.hum_status_var.set(f"Estado: Ejecutando calentamiento por {duration_mins:.0f} minutos...")
        threading.Thread(target=self.human_warming_worker, args=(target_devs, duration_mins), daemon=True).start()

    def human_warming_worker(self, devices, duration_mins):
        end_time = time.time() + (duration_mins * 60)
        while time.time() < end_time and not self.human_stop_event.is_set() and not self.app_closing.is_set():
            for dev in devices:
                if self.human_stop_event.is_set(): break
                self.set_device_task(dev, "Modo Humano (Calentamiento)")
                size = self.screen_size_cache.get(dev, (1080, 1920))
                w, h = size
                self.run_on_device(dev, ["shell", "input", "swipe", str(w//2), str(int(h*0.75)), str(w//2), str(int(h*0.30)), str(random.randint(350, 650))])
                time.sleep(random.uniform(3.0, 9.0))
        for dev in devices: self.restore_device_task(dev, "Modo Humano (Calentamiento)", None)
        self.post_ui(lambda: (self.btn_start_human.config(state="normal"), self.btn_stop_human.config(state="disabled"), self.hum_status_var.set("Estado: Calentamiento finalizado."), setattr(self, 'human_running', False)))

    def stop_human_warming(self):
        self.human_stop_event.set()
        self.hum_status_var.set("Estado: Deteniendo calentamiento...")
        self.btn_start_human.config(state="normal"); self.btn_stop_human.config(state="disabled")
        self.human_running = False

    def start_mass_report(self):
        url = self.entry_rep_url.get().strip()
        target_devs = self.get_selected_devices()
        if not target_devs or not url: return messagebox.showwarning("Aviso", "Selecciona dispositivos e ingresa URL.")
        reason = self.rep_reason_var.get()
        do_airplane = self.rep_airplane_var.get()
        self.report_stop_event.clear(); self.report_running = True
        self.btn_start_report.config(state="disabled"); self.btn_stop_report.config(state="normal")
        self.rep_status_var.set("Estado: Ejecutando reporte masivo...")
        threading.Thread(target=self.mass_report_worker, args=(target_devs, url, reason, do_airplane), daemon=True).start()

    def mass_report_worker(self, devices, url, reason, do_airplane):
        for idx, dev in enumerate(devices):
            if self.report_stop_event.is_set() or self.app_closing.is_set(): break
            prev = self.device_tasks.get(dev)
            self.set_device_task(dev, "Reportando en FB Lite")
            try:
                if do_airplane: self.toggle_airplane_mode(dev)
                self.run_on_device(dev, ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url, "com.facebook.lite"])
                time.sleep(7.0)
                size = self.screen_size_cache.get(dev, (1080, 1920))
                w, h = size
                if not self.find_node_and_tap(dev, ["opciones", "more", "options", "..."], size):
                    self.run_on_device(dev, ["shell", "input", "tap", str(int(w*0.92)), str(int(h*0.12))])
                time.sleep(2.0)
                if not self.find_node_and_tap(dev, ["reportar", "report"], size):
                    self.run_on_device(dev, ["shell", "input", "tap", str(int(w*0.5)), str(int(h*0.45))])
                time.sleep(2.0)
                keyword_motivo = "spam" if reason == "spam" else ("falsa" if reason == "falsa" else "cuenta")
                self.find_node_and_tap(dev, [keyword_motivo, "fraude", "falso"], size)
                time.sleep(2.0)
                if not self.find_node_and_tap(dev, ["enviar", "listo", "done", "submit"], size):
                    self.run_on_device(dev, ["shell", "input", "tap", str(int(w*0.85)), str(int(h*0.92))])
                time.sleep(2.0)
                self.run_on_device(dev, ["shell", "input", "keyevent", "4"])
            finally:
                self.restore_device_task(dev, "Reportando en FB Lite", prev)
        self.post_ui(lambda: (self.btn_start_report.config(state="normal"), self.btn_stop_report.config(state="disabled"), self.rep_status_var.set("Estado: Reportes masivos finalizados."), setattr(self, 'report_running', False)))

    def stop_mass_report(self):
        self.report_stop_event.set()
        self.rep_status_var.set("Estado: Deteniendo reportes...")
        self.btn_start_report.config(state="normal"); self.btn_stop_report.config(state="disabled")
        self.report_running = False

    def parse_spintax(self, text):
        while True:
            match = re.search(r'\{([^{}]*)\}', text)
            if not match: break
            options = match.group(1).split('|')
            text = text[:match.start()] + random.choice(options) + text[match.end():]
        return text

    def inject_text_adb(self, device, text):
        """Escribe texto y falla de forma explícita si Unicode no es compatible."""
        if not text:
            return True

        needs_unicode = any(ord(character) > 127 for character in text)
        if needs_unicode:
            ok, ime_list = self.run_on_device(device, ["shell", "ime", "list", "-s"], timeout=15)
            if not ok:
                self.log(f"[{device}] No se pudo consultar el teclado Android: {ime_list}")
                return False
            adb_ime = next(
                (line.strip() for line in ime_list.splitlines() if "com.android.adbkeyboard" in line.casefold()),
                None,
            )
            if not adb_ime:
                self.log(
                    f"[{device}] El comentario contiene Unicode, pero ADB Keyboard no está instalado; no se publicará texto incompleto."
                )
                return False
            ok, current_ime = self.run_on_device(
                device, ["shell", "settings", "get", "secure", "default_input_method"], timeout=15
            )
            if not ok:
                self.log(f"[{device}] No se pudo leer el teclado actual: {current_ime}")
                return False
            try:
                ok, detail = self.run_on_device(device, ["shell", "ime", "set", adb_ime], timeout=15)
                if not ok:
                    self.log(f"[{device}] No se pudo activar ADB Keyboard: {detail}")
                    return False
                payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
                ok, detail = self.run_on_device(
                    device,
                    ["shell", "am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", payload],
                    timeout=20,
                )
                if not ok:
                    self.log(f"[{device}] No se pudo inyectar texto Unicode: {detail}")
                    return False
            finally:
                previous = current_ime.strip()
                if previous and previous != "null":
                    self.run_on_device(device, ["shell", "ime", "set", previous], timeout=15)
            return True

        lines = text.splitlines() or [""]
        for index, line in enumerate(lines):
            # ADB interpreta %s como espacio. Los metacaracteres se escapan para
            # que el texto llegue directamente al campo enfocado, sin depender
            # de que Android incluya la utilidad externa base64.
            escaped = line.replace("\\", "\\\\").replace("%", "\\%").replace(" ", "%s")
            for character in ('"', "'", "&", "<", ">", ";", "|", "(", ")", "$", "`", "!", "*", "?", "[", "]", "{", "}"):
                escaped = escaped.replace(character, "\\" + character)
            ok, detail = self.run_on_device(
                device, ["shell", "input", "text", escaped], timeout=20
            )
            if not ok:
                self.log(f"[{device}] No se pudo escribir el comentario: {detail}")
                return False
            if index < len(lines) - 1:
                ok, detail = self.run_on_device(device, ["shell", "input", "keyevent", "66"], timeout=15)
                if not ok:
                    self.log(f"[{device}] No se pudo insertar un salto de línea: {detail}")
                    return False
        return True

    def clear_focused_text(self, device, character_count):
        """Limpia un borrador parcial sin tocar ningún botón de publicación."""
        placeholders = (
            "escribe un comentario", "write a comment", "comenta como",
            "comentar como", "comment as", "add a comment",
        )

        def current_editor_text():
            hierarchy = self.get_android_hierarchy(device)
            size = self.get_device_screen_size(device)
            if hierarchy is None or not size:
                return None
            _, height = size
            candidates = []
            for node in hierarchy.iter("node"):
                class_name = node.attrib.get("class", "").casefold()
                editable = node.attrib.get("editable", "false").casefold() == "true"
                if not ("edittext" in class_name or "autocompletetextview" in class_name or editable):
                    continue
                bounds = self.parse_node_bounds(node)
                if not bounds:
                    continue
                center_y = (bounds[1] + bounds[3]) // 2
                if center_y >= height * 0.55:
                    candidates.append((center_y, node.attrib.get("text", "").strip()))
            if not candidates:
                return None
            candidates.sort(reverse=True)
            value = candidates[0][1]
            normalized = self.normalize_search_text(value).strip()
            if not value or normalized.startswith(placeholders):
                return ""
            return value

        # Seleccionar todo evita residuos cuando Facebook divide el borrador en varias líneas.
        for _ in range(2):
            self.run_on_device(
                device, ["shell", "input", "keycombination", "113", "29"], timeout=15
            )
            ok, _ = self.run_on_device(device, ["shell", "input", "keyevent", "67"], timeout=15)
            if not ok:
                return False
            time.sleep(0.18)
            remaining = current_editor_text()
            if remaining == "":
                return True

        remaining = current_editor_text()
        count = max(1, min(len(remaining or "") + int(character_count) + 10, 500))
        self.run_on_device(device, ["shell", "input", "keyevent", "123"], timeout=15)
        ok, _ = self.run_on_device(
            device, ["shell", "input", "keyevent"] + (["67"] * count), timeout=20
        )
        if not ok:
            return False
        time.sleep(0.18)
        remaining = current_editor_text()
        if remaining is None:
            self.log(f"[{device}] No se pudo verificar que el editor quedara vacío; se cancela la escritura.")
            return False
        if remaining != "":
            self.log(f"[{device}] El editor no quedó vacío; se cancela la escritura para evitar concatenar texto.")
            return False
        return True

    def visible_text_contains(self, device, expected_text):
        hierarchy = self.get_android_hierarchy(device)
        if not hierarchy:
            return False
        visible = self.normalize_search_text(self.extract_visible_text(hierarchy))
        expected = self.normalize_search_text(expected_text).strip()
        return bool(expected) and expected in visible

    def capture_device_screen(self, device):
        if not OPENCV_AVAILABLE:
            return None
        try:
            result = subprocess.run(
                [self.adb, "-s", device, "exec-out", "screencap", "-p"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                creationflags=NO_WINDOW,
            )
            if result.returncode != 0 or not result.stdout:
                detail = result.stderr.decode(errors="replace").strip() if result.stderr else "captura vacía"
                self.log(f"[{device}] No se pudo capturar la pantalla: {detail}")
                return None
            return cv2.imdecode(np.frombuffer(result.stdout, np.uint8), cv2.IMREAD_COLOR)
        except Exception as error:
            self.log(f"[{device}] No se pudo capturar la pantalla: {error}")
            return None

    def locate_blue_send_arrow(self, screen):
        """Localiza un componente azul de envío en el sector derecho del editor."""
        if not OPENCV_AVAILABLE or screen is None:
            return None
        height, width = screen.shape[:2]
        hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
        blue = cv2.inRange(hsv, np.array([92, 85, 80]), np.array([132, 255, 255]))
        kernel = np.ones((3, 3), np.uint8)
        blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        screen_area = float(width * height)
        candidates = []
        for contour in contours:
            area = float(cv2.contourArea(contour))
            x, y, box_width, box_height = cv2.boundingRect(contour)
            center = (x + box_width // 2, y + box_height // 2)
            # La flecha real está en el extremo derecho del editor. Este filtro
            # excluye insignias azules de autores y reacciones dentro del hilo.
            if center[0] < width * 0.80:
                continue
            if not height * 0.18 <= center[1] <= height * 0.98:
                continue
            if not screen_area * 0.00018 <= area <= screen_area * 0.0035:
                continue
            if box_width < width * 0.018 or box_height < height * 0.012:
                continue
            if box_width > width * 0.12 or box_height > height * 0.10:
                continue
            aspect = box_width / max(1.0, float(box_height))
            if not 0.45 <= aspect <= 2.60:
                continue
            fill = area / max(1.0, float(box_width * box_height))
            if fill < 0.18:
                continue
            score = (center[0] / width) * 2.0 + fill + min(area / (screen_area * 0.01), 1.0)
            candidates.append((score, center, (x, y, box_width, box_height), fill))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        score, point, bounds, fill = candidates[0]
        return {"point": point, "bounds": bounds, "fill": fill, "score": score}

    def tap_blue_send_arrow(self, device, attempts=1, delay=0.45, stop_event=None):
        attempts = max(1, int(attempts))
        for attempt in range(attempts):
            screen = self.capture_device_screen(device)
            match = self.locate_blue_send_arrow(screen)
            if match:
                x, y = match["point"]
                ok, detail = self.run_on_device(
                    device, ["shell", "input", "tap", str(x), str(y)], timeout=15
                )
                if not ok:
                    self.log(f"[{device}] Se encontró la flecha azul, pero el toque falló: {detail}")
                    return False
                self.log(f"[{device}] Flecha azul de envío pulsada en ({x}, {y}).")
                return True
            if attempt + 1 < attempts and self.wait_or_cancel(delay, stop_event):
                return False
        return False

    def locate_action_figure(self, screen, template_name, x_range, threshold=0.46):
        """Calcula el centro de una figura por bordes y escala, sin coordenada fija."""
        if not OPENCV_AVAILABLE or screen is None:
            return None
        template_path = self.templates_dir / template_name
        template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
        if template is None:
            return None
        height, width = screen.shape[:2]
        x1 = max(0, int(width * x_range[0]))
        x2 = min(width, int(width * x_range[1]))
        y1 = max(0, int(height * 0.14))
        y2 = min(height, int(height * 0.94))
        roi = screen[y1:y2, x1:x2]
        if roi.size == 0:
            return None
        roi_edges = cv2.Canny(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 55, 145)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        reference_scale = width / 720.0
        best = None
        for factor in np.linspace(0.65, 1.45, 17):
            scale = reference_scale * factor
            resized = cv2.resize(template_gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            if min(resized.shape[:2]) < 18:
                continue
            if resized.shape[0] > roi_edges.shape[0] or resized.shape[1] > roi_edges.shape[1]:
                continue
            edges = cv2.Canny(resized, 55, 145)
            match = cv2.matchTemplate(roi_edges, edges, cv2.TM_CCOEFF_NORMED)
            _, score, _, location = cv2.minMaxLoc(match)
            if best is None or score > best[0]:
                best = (float(score), location, resized.shape)
        if best is None or best[0] < threshold:
            return None
        score, location, shape = best
        point = (
            x1 + location[0] + shape[1] // 2,
            y1 + location[1] + shape[0] // 2,
        )
        radius = max(18, min(shape[:2]) // 2)
        px1, px2 = max(0, point[0] - radius), min(width, point[0] + radius)
        py1, py2 = max(0, point[1] - radius), min(height, point[1] + radius)
        patch = screen[py1:py2, px1:px2]
        blue_ratio = 0.0
        if patch.size:
            hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
            blue = cv2.inRange(hsv, np.array([90, 65, 55]), np.array([135, 255, 255]))
            blue_ratio = float(np.count_nonzero(blue)) / float(blue.size)
        return {"point": point, "score": score, "active": blue_ratio >= 0.035}

    def apply_calculated_figure_action(self, device, action, stop_event=None):
        settings = {
            "like": ("like_outline.png", (0.00, 0.38)),
            "comment": ("comment_outline.png", (0.25, 0.68)),
        }
        template_name, x_range = settings[action]
        screen = self.capture_device_screen(device)
        match = self.locate_action_figure(screen, template_name, x_range)
        if not match:
            return "not_found"
        if action == "like" and match["active"]:
            self.log(f"[{device}] La manita calculada ya aparece activa; no se tocó.")
            return "already_liked"
        x, y = match["point"]
        ok, detail = self.run_on_device(
            device, ["shell", "input", "tap", str(x), str(y)], timeout=15
        )
        if not ok:
            self.log(f"[{device}] Se localizó la figura, pero el toque falló: {detail}")
            return "error"
        self.log(
            f"[{device}] Clic calculado en {action}: ({x}, {y}), coincidencia {match['score']:.2f}."
        )
        if action == "comment":
            return "sent"
        if self.wait_or_cancel(0.9, stop_event):
            return "cancelled"
        updated = self.capture_device_screen(device)
        verification = self.locate_action_figure(updated, template_name, x_range)
        if verification and verification["active"]:
            self.log(f"[{device}] Me gusta confirmado visualmente.")
            return "confirmed"
        self.log(f"[{device}] Clic calculado enviado; Me gusta no confirmado visualmente.")
        return "sent_unconfirmed"

    def toggle_airplane_mode(self, device, stop_event=None):
        self.run_on_device(device, ["shell", "settings", "put", "global", "airplane_mode_on", "1"])
        self.run_on_device(device, ["shell", "am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE", "--ez", "state", "true"])
        cancelled = self.wait_or_cancel(5.0, stop_event)
        self.run_on_device(device, ["shell", "settings", "put", "global", "airplane_mode_on", "0"])
        self.run_on_device(device, ["shell", "am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE", "--ez", "state", "false"])
        if cancelled:
            return False
        if self.wait_or_cancel(6.0, stop_event):
            return False
        return True

    def tap_image_template(self, device, template_name, threshold=0.75):
        if not OPENCV_AVAILABLE: return False
        template_path = self.templates_dir / template_name
        if not template_path.exists(): return False
        try:
            res = subprocess.run(
                [self.adb, "-s", device, "exec-out", "screencap", "-p"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                creationflags=NO_WINDOW,
            )
            if res.returncode != 0 or not res.stdout:
                detail = res.stderr.decode(errors="replace").strip() if res.stderr else "captura vacía"
                self.log(f"[{device}] No se pudo capturar pantalla para {template_name}: {detail}")
                return False
            screen = cv2.imdecode(np.frombuffer(res.stdout, np.uint8), cv2.IMREAD_COLOR)
            tmpl = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
            if screen is None or tmpl is None: return False
            gray_screen = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
            gray_tmpl = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
            best_score = 0.0; best_loc = None; best_shape = None
            for f in np.linspace(0.7, 1.3, 13):
                p = cv2.resize(gray_tmpl, None, fx=f, fy=f)
                if p.shape[0] > gray_screen.shape[0] or p.shape[1] > gray_screen.shape[1]: continue
                match = cv2.matchTemplate(gray_screen, p, cv2.TM_CCOEFF_NORMED)
                _, score, _, loc = cv2.minMaxLoc(match)
                if score > best_score: best_score = score; best_loc = loc; best_shape = p.shape
            if best_score >= threshold and best_loc is not None:
                cx = best_loc[0] + best_shape[1] // 2
                cy = best_loc[1] + best_shape[0] // 2
                ok, detail = self.run_on_device(device, ["shell", "input", "tap", str(cx), str(cy)], timeout=15)
                if not ok:
                    self.log(f"[{device}] Coincidencia visual encontrada, pero el toque falló: {detail}")
                    return False
                self.log(f"[{device}] Coincidencia visual {template_name}: {best_score:.2f}")
                return True
        except Exception as error:
            self.log(f"[{device}] Error en reconocimiento visual {template_name}: {error}")
        return False

    def find_node_and_tap(self, device, keywords, size, ignore_top_pct=0.10):
        try:
            hierarchy = self.get_android_hierarchy(device)
            if not hierarchy: return False
            for node in hierarchy.iter("node"):
                text = node.attrib.get("text", "").strip().lower()
                desc = node.attrib.get("content-desc", "").strip().lower()
                for kw in keywords:
                    if kw.lower() in text or kw.lower() in desc:
                        bounds_str = node.attrib.get("bounds", "")
                        match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                        if match:
                            x1, y1, x2, y2 = map(int, match.groups())
                            cy = (y1 + y2) // 2
                            cx = (x1 + x2) // 2
                            if cy > size[1] * ignore_top_pct: 
                                self.run_on_device(device, ["shell", "input", "tap", str(cx), str(cy)])
                                return True
        except Exception: pass
        return False

if __name__ == "__main__":
    try:
        if not acquire_single_instance(): sys.exit(0)
        set_windows_app_id()
        if getattr(sys, "frozen", False):
            from license_guard import run_startup_gate

            if not run_startup_gate():
                sys.exit(0)
        root = tk.Tk()
        app = ProfessionalPhoneController(root)
        root.mainloop()
    except Exception as e:
        with open("registro_errores.txt", "a", encoding="utf-8") as f:
            f.write(f"--- Error de Inicio ---\n{traceback.format_exc()}\n")
    finally:
        release_single_instance()
