import json
import math
import os
import queue
import re
import subprocess
import threading
import time
import tkinter as tk
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
from urllib.parse import urlparse

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

# Intentar importar OpenCV y NumPy para el reconocimiento de formas
try:
    import cv2
    import numpy as np

    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


class ProfessionalPhoneController:

    def __init__(self, root):
        self.root = root
        self.root.title(
            "Panel de Control Multi-Dispositivo - Facebook Automation & Vision"
        )
        self.root.geometry("1050x850")
        self.root.minsize(950, 750)

        # Detectar la ruta de ADB automáticamente (busca en 'herramientas' o en el sistema)
        self.adb = self.find_adb()
        self.scrcpy = self.find_scrcpy()
        self.ui_queue = queue.Queue()
        self.search_stop_event = threading.Event()
        self.search_running = False
        self.screen_size_cache = {}
        self.device_config_file = Path(__file__).resolve().parent / "dispositivos.json"
        self.device_aliases = self.load_device_aliases()
        self.device_details = {}
        self.device_tasks = {}
        self.scrcpy_processes = {}
        self.search_devices = []
        self.first_device_scan = True
        self.root.after(100, self._drain_ui_queue)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Configuración de Estilo Global (TTK)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TButton", font=("Segoe UI", 9, "bold"), padding=6, relief="flat"
        )
        style.configure(
            "Primary.TButton", background="#1877f2", foreground="white"
        )
        style.configure(
            "Success.TButton", background="#42b72a", foreground="white"
        )

        # Crear carpeta de plantillas si no existe
        if not os.path.exists("templates"):
            os.makedirs("templates")

        self.devices = []

        # --- Creación de Pestañas (Notebook) ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_general = ttk.Frame(self.notebook)
        self.tab_vision = ttk.Frame(self.notebook)
        self.tab_search = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_general, text=" Control y Automatización General ")
        self.notebook.add(
            self.tab_vision, text=" Reacciones por Forma (Computer Vision) "
        )
        self.notebook.add(
            self.tab_search, text=" Búsqueda por Palabras "
        )

        self.create_general_widgets()
        self.create_vision_widgets()
        self.create_search_widgets()

        # Consola de Registros global inferior
        self.create_console_widget()

        self.refresh_devices()

    def find_adb(self):
        # Buscar adb.exe dentro de la carpeta 'herramientas' del proyecto
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        tools_path = os.path.join(base_dir, "herramientas")
        if os.path.exists(tools_path):
            for root, dirs, files in os.walk(tools_path):
                if "adb.exe" in files:
                    return os.path.join(root, "adb.exe")
        
        import shutil
        sys_adb = shutil.which("adb")
        if sys_adb:
            return sys_adb
            
        return "adb"

    def find_scrcpy(self):
        base_dir = Path(__file__).resolve().parent
        for candidate in (base_dir / "herramientas").glob("**/scrcpy.exe"):
            return str(candidate)
        return None

    def load_device_aliases(self):
        try:
            if self.device_config_file.exists():
                data = json.loads(self.device_config_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {
                        str(serial): str(alias).strip()
                        for serial, alias in data.items()
                        if str(alias).strip()
                    }
        except Exception as error:
            self.log(f"No se pudieron cargar los nombres de dispositivos: {error}")
        return {}

    def save_device_aliases(self):
        try:
            self.device_config_file.write_text(
                json.dumps(self.device_aliases, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as error:
            messagebox.showerror(
                "No se pudo guardar",
                f"No se guardó el nombre del dispositivo:\n{error}",
            )

    def create_general_widgets(self):
        # --- Marco Superior: Dispositivos ---
        dev_frame = ttk.LabelFrame(
            self.tab_general, text=" Gestión de Dispositivos Conectados ", padding=10
        )
        dev_frame.pack(fill="x", padx=10, pady=10)

        device_toolbar = ttk.Frame(dev_frame)
        device_toolbar.pack(fill="x", pady=(0, 7))

        ttk.Button(
            device_toolbar,
            text="Escanear Dispositivos",
            command=self.refresh_devices,
            style="Success.TButton",
        ).pack(side="left")
        ttk.Button(
            device_toolbar, text="Seleccionar todos", command=self.select_all_devices
        ).pack(side="left", padx=(7, 0))
        ttk.Button(
            device_toolbar, text="Ninguno", command=self.clear_device_selection
        ).pack(side="left", padx=(7, 0))
        ttk.Button(
            device_toolbar, text="Asignar nombre", command=self.rename_selected_device
        ).pack(side="left", padx=(7, 0))
        ttk.Button(
            device_toolbar,
            text="Ver y controlar",
            command=self.open_selected_screens,
            style="Primary.TButton",
        ).pack(side="left", padx=(18, 0))
        ttk.Button(
            device_toolbar,
            text="Cerrar pantallas",
            command=self.close_selected_screens,
        ).pack(side="left", padx=(7, 0))

        self.lbl_devices = ttk.Label(
            device_toolbar,
            text="Dispositivos detectados: 0",
            font=("Segoe UI", 9, "bold"),
        )
        self.lbl_devices.pack(side="right", padx=5)

        table_frame = ttk.Frame(dev_frame)
        table_frame.pack(fill="x")
        columns = ("nombre", "modelo", "serial", "android", "estado", "tarea")
        self.device_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="extended",
            height=4,
        )
        headings = {
            "nombre": "Nombre",
            "modelo": "Modelo",
            "serial": "Serie",
            "android": "Android",
            "estado": "Estado",
            "tarea": "Tarea actual",
        }
        widths = {
            "nombre": 140,
            "modelo": 135,
            "serial": 135,
            "android": 70,
            "estado": 95,
            "tarea": 180,
        }
        for column in columns:
            self.device_table.heading(column, text=headings[column])
            self.device_table.column(column, width=widths[column], anchor="w")
        self.device_table.pack(side="left", fill="x", expand=True)
        device_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.device_table.yview
        )
        device_scroll.pack(side="right", fill="y")
        self.device_table.configure(yscrollcommand=device_scroll.set)
        self.device_table.bind("<<TreeviewSelect>>", self.update_selection_label)
        self.device_table.bind("<Double-1>", lambda _event: self.rename_selected_device())

        self.lbl_selection = ttk.Label(
            dev_frame,
            text="Seleccionados: 0",
            foreground="#1d5f91",
            font=("Segoe UI", 9, "bold"),
        )
        self.lbl_selection.pack(anchor="w", pady=(6, 0))

        # --- Marco Central: acciones para la selección actual ---
        act_frame = ttk.LabelFrame(
            self.tab_general, text=" Tareas para los dispositivos seleccionados ", padding=10
        )
        act_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            act_frame,
            text="Abrir Facebook en seleccionados",
            command=self.open_facebook_all,
            style="Primary.TButton",
        ).pack(anchor="w", padx=5, pady=5)

        ttk.Label(
            act_frame, text="Abrir Link / URL en Facebook:", font=("Segoe UI", 9)
        ).pack(anchor="w", padx=5, pady=2)
        url_row = ttk.Frame(act_frame)
        url_row.pack(fill="x", padx=5, pady=2)

        self.entry_url = ttk.Entry(url_row, font=("Segoe UI", 10))
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_url.insert(0, "https://www.facebook.com")

        ttk.Button(
            url_row,
            text="Abrir en seleccionados",
            command=self.open_url_all,
            style="Success.TButton",
        ).pack(side="right")

        ttk.Label(
            act_frame,
            text="Texto para Publicar / Redactar:",
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=5, pady=(10, 2))
        self.text_post = scrolledtext.ScrolledText(
            act_frame, width=80, height=4, font=("Segoe UI", 10)
        )
        self.text_post.pack(fill="x", padx=5, pady=2)

        ttk.Button(
            act_frame,
            text="Enviar texto a seleccionados",
            command=self.publish_text_all,
            style="Success.TButton",
        ).pack(anchor="w", padx=5, pady=5)

    def create_vision_widgets(self):
        # --- Pestaña de Reacciones por Forma ---
        vision_frame = ttk.LabelFrame(
            self.tab_vision,
            text=" Búsqueda y Reacción Automática por Icono (OpenCV) ",
            padding=15,
        )
        vision_frame.pack(fill="both", expand=True, padx=10, pady=10)

        if not OPENCV_AVAILABLE:
            lbl_warning = ttk.Label(
                vision_frame,
                text=(
                    "⚠️ Advertencia: Las librerías 'opencv-python' y 'numpy' no están"
                    " instaladas.\nEjecuta en tu terminal: pip install opencv-python"
                    " numpy"
                ),
                foreground="red",
                font=("Segoe UI", 10, "bold"),
            )
            lbl_warning.pack(pady=20)
            return

        ttk.Label(
            vision_frame,
            text=(
                "Instrucciones:\n1. Coloca imágenes recortadas de las reacciones"
                " (ej: like.png, love.png, haha.png) en la carpeta 'templates'.\n2."
                " Selecciona la reacción que deseas buscar y aplicar de forma"
                " inteligente en los dispositivos seleccionados en la pestaña General."
            ),
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=5)

        btn_container = ttk.Frame(vision_frame)
        btn_container.pack(pady=20)

        reactions_vision = [
            ("👍 Reaccionar 'Me gusta' (Forma)", "like.png"),
            ("❤️ Reaccionar 'Me encanta' (Forma)", "love.png"),
            ("😆 Reaccionar 'Me divierte' (Forma)", "haha.png"),
            ("😢 Reaccionar 'Me entristece' (Forma)", "sad.png"),
            ("😡 Reaccionar 'Me enoja' (Forma)", "angry.png"),
        ]

        for label_text, filename in reactions_vision:
            ttk.Button(
                btn_container,
                text=label_text,
                command=lambda f=filename: self.execute_vision_reaction(f),
            ).pack(fill="x", pady=6, ipadx=10, ipady=3)

    def create_search_widgets(self):
        """Crea el modo asistido de búsqueda de publicaciones visibles."""
        search_frame = ttk.LabelFrame(
            self.tab_search,
            text=" Búsqueda asistida en el contenido visible ",
            padding=12,
        )
        search_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            search_frame,
            text=(
                "Escribe palabras o frases separadas por comas o líneas. El panel "
                "revisa el texto visible, desplaza la pantalla a intervalos y se "
                "detiene al encontrar una coincidencia."
            ),
            wraplength=800,
            justify="left",
        ).pack(fill="x", pady=(0, 8))

        ttk.Label(search_frame, text="Palabras clave:").pack(anchor="w")
        self.search_keywords = scrolledtext.ScrolledText(
            search_frame, height=4, font=("Segoe UI", 10)
        )
        self.search_keywords.pack(fill="x", pady=(3, 9))

        settings_row = ttk.Frame(search_frame)
        settings_row.pack(fill="x", pady=3)

        ttk.Label(settings_row, text="Intervalo entre desplazamientos:").pack(
            side="left"
        )
        self.search_interval_var = tk.StringVar(value="1")
        ttk.Spinbox(
            settings_row,
            from_=0.5,
            to=60,
            increment=0.5,
            width=5,
            textvariable=self.search_interval_var,
        ).pack(side="left", padx=(6, 4))
        ttk.Label(settings_row, text="segundos").pack(side="left")

        ttk.Label(settings_row, text="Máximo de desplazamientos:").pack(
            side="left", padx=(22, 0)
        )
        self.search_max_scrolls_var = tk.StringVar(value="20")
        ttk.Spinbox(
            settings_row,
            from_=1,
            to=200,
            width=6,
            textvariable=self.search_max_scrolls_var,
        ).pack(side="left", padx=(6, 0))

        button_row = ttk.Frame(search_frame)
        button_row.pack(fill="x", pady=(10, 6))
        self.btn_start_search = ttk.Button(
            button_row,
            text="Iniciar búsqueda",
            command=self.start_keyword_search,
            style="Success.TButton",
        )
        self.btn_start_search.pack(side="left")
        self.btn_stop_search = ttk.Button(
            button_row,
            text="Detener",
            command=self.stop_keyword_search,
            state="disabled",
        )
        self.btn_stop_search.pack(side="left", padx=7)
        ttk.Button(
            button_row,
            text="Limpiar resultados",
            command=self.clear_search_results,
        ).pack(side="left")

        self.search_status_var = tk.StringVar(value="Listo para buscar.")
        ttk.Label(
            search_frame,
            textvariable=self.search_status_var,
            foreground="#1d5f91",
            font=("Segoe UI", 9, "bold"),
        ).pack(fill="x", pady=(2, 7))

        ttk.Label(search_frame, text="Resultados:").pack(anchor="w")
        self.search_results = scrolledtext.ScrolledText(
            search_frame,
            height=8,
            font=("Consolas", 9),
            state="disabled",
        )
        self.search_results.pack(fill="both", expand=True, pady=(3, 9))

        link_frame = ttk.LabelFrame(
            search_frame, text=" Enlace de la publicación encontrada ", padding=8
        )
        link_frame.pack(fill="x")
        ttk.Label(
            link_frame,
            text=(
                "En Facebook usa Compartir > Copiar enlace. Después captura el "
                "portapapeles o pega el enlace aquí para conservarlo."
            ),
            wraplength=780,
            justify="left",
        ).pack(fill="x", pady=(0, 6))
        link_row = ttk.Frame(link_frame)
        link_row.pack(fill="x")
        self.search_link_var = tk.StringVar()
        ttk.Entry(link_row, textvariable=self.search_link_var).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            link_row,
            text="Capturar portapapeles",
            command=self.capture_link_from_clipboard,
        ).pack(side="left", padx=(7, 0))

    def create_console_widget(self):
        console_frame = ttk.LabelFrame(
            self.root, text=" Consola de Estado y Operaciones ", padding=10
        )
        console_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.console = scrolledtext.ScrolledText(
            console_frame,
            bg="#1e1e1e",
            fg="#00ff00",
            font=("Consolas", 9),
            insertbackground="white",
        )
        self.console.pack(fill="both", expand=True, padx=5, pady=5)

    def _drain_ui_queue(self):
        """Procesa en el hilo de Tkinter los mensajes enviados por tareas ADB."""
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                if kind == "log" and hasattr(self, "console"):
                    self.console.insert(tk.END, payload + "\n")
                    self.console.see(tk.END)
                elif kind == "call":
                    payload()
        except queue.Empty:
            pass
        except tk.TclError:
            return

        try:
            self.root.after(100, self._drain_ui_queue)
        except tk.TclError:
            pass

    def post_ui(self, callback):
        self.ui_queue.put(("call", callback))

    def log(self, message):
        self.ui_queue.put(("log", str(message)))

    def on_close(self):
        self.search_stop_event.set()
        for process in list(self.scrcpy_processes.values()):
            try:
                if process.poll() is None:
                    process.terminate()
            except Exception:
                pass
        self.root.destroy()

    def get_selected_devices(self):
        if not hasattr(self, "device_table"):
            return []
        return [serial for serial in self.device_table.selection() if serial in self.devices]

    def select_all_devices(self):
        if self.devices:
            self.device_table.selection_set(self.devices)
        self.update_selection_label()

    def clear_device_selection(self):
        self.device_table.selection_remove(self.device_table.selection())
        self.update_selection_label()

    def update_selection_label(self, _event=None):
        count = len(self.get_selected_devices())
        self.lbl_selection.config(
            text=f"Seleccionados: {count} de {len(self.devices)}"
        )

    def display_device_name(self, serial):
        detail = self.device_details.get(serial, {})
        return self.device_aliases.get(serial) or detail.get("model") or serial

    def rename_selected_device(self):
        selected = self.get_selected_devices()
        if len(selected) != 1:
            messagebox.showwarning(
                "Selecciona un celular",
                "Selecciona exactamente un dispositivo para asignarle un nombre.",
            )
            return
        serial = selected[0]
        current = self.device_aliases.get(serial, "")
        alias = simpledialog.askstring(
            "Nombre del dispositivo",
            "Escribe un nombre o responsable para este celular:",
            initialvalue=current,
            parent=self.root,
        )
        if alias is None:
            return
        alias = alias.strip()
        if alias:
            self.device_aliases[serial] = alias
        else:
            self.device_aliases.pop(serial, None)
        self.save_device_aliases()
        self.update_device_row(serial)
        self.log(f"Nombre actualizado para [{serial}]: {alias or '(sin alias)'}")

    def query_device_details(self, serial):
        try:
            output = self.adb_capture(
                serial,
                [
                    "shell",
                    "getprop ro.product.model; getprop ro.build.version.release",
                ],
                timeout=10,
            )
            values = [value.strip() for value in output.splitlines() if value.strip()]
            return {
                "model": values[0] if values else "Android",
                "android": values[1] if len(values) > 1 else "",
                "state": "Conectado",
            }
        except Exception as error:
            return {"model": "Android", "android": "", "state": f"Error: {error}"}

    def update_device_row(self, serial):
        if not hasattr(self, "device_table") or not self.device_table.exists(serial):
            return
        detail = self.device_details.get(serial, {})
        self.device_table.item(
            serial,
            values=(
                self.device_aliases.get(serial, ""),
                detail.get("model", ""),
                serial,
                detail.get("android", ""),
                detail.get("state", "Conectado"),
                self.device_tasks.get(serial, "Listo"),
            ),
        )

    def set_device_task(self, serial, task):
        self.device_tasks[serial] = task
        self.post_ui(lambda device=serial: self.update_device_row(device))

    def restore_device_task(self, serial, expected_task, previous_task):
        if self.device_tasks.get(serial) == expected_task:
            if previous_task:
                self.device_tasks[serial] = previous_task
            else:
                self.device_tasks.pop(serial, None)
            self.update_device_row(serial)

    def get_devices(self):
        try:
            result = subprocess.run(
                [self.adb, "devices"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
                creationflags=NO_WINDOW,
            )
            lines = result.stdout.strip().split("\n")[1:]
            devices = []
            for line in lines:
                if "\tdevice" in line:
                    devices.append(line.split("\t")[0])
            return devices
        except Exception as e:
            self.log(f"Error al escanear ADB: {e}")
            return []

    def refresh_devices(self):
        previous_selection = set(self.get_selected_devices())
        self.devices = self.get_devices()
        self.device_details = {
            serial: self.query_device_details(serial) for serial in self.devices
        }
        existing_rows = set(self.device_table.get_children())
        for serial in existing_rows - set(self.devices):
            self.device_table.delete(serial)
            self.device_tasks.pop(serial, None)
        for serial in self.devices:
            if not self.device_table.exists(serial):
                self.device_table.insert("", "end", iid=serial)
            self.update_device_row(serial)

        selected = [serial for serial in self.devices if serial in previous_selection]
        if self.first_device_scan and self.devices:
            selected = list(self.devices)
        if selected:
            self.device_table.selection_set(selected)
        self.first_device_scan = False
        count = len(self.devices)
        self.lbl_devices.config(text=f"Dispositivos detectados: {count}")
        self.update_selection_label()
        self.log(f"Dispositivos actualizados correctamente. Total: {count}")

    def run_on_device(self, device, command, timeout=60):
        try:
            full_cmd = [self.adb, "-s", device] + command
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
                timeout=timeout,
                creationflags=NO_WINDOW,
            )
            return True, result.stdout.strip()
        except Exception as e:
            self.log(f"Error en [{device}]: {e}")
            return False, str(e)

    def adb_capture(self, device, command, timeout=30):
        """Ejecuta ADB y devuelve texto o genera un error descriptivo."""
        result = subprocess.run(
            [self.adb, "-s", device] + command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=NO_WINDOW,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "Error ADB").strip()
            raise RuntimeError(detail)
        return result.stdout

    def execute_multithreaded(self, task_func, task_name="Tarea", devices=None):
        target_devices = list(devices if devices is not None else self.get_selected_devices())
        if not target_devices:
            messagebox.showwarning(
                "Aviso", "Selecciona al menos un dispositivo conectado."
            )
            return

        def run_task(device):
            previous_task = self.device_tasks.get(device)
            self.set_device_task(device, task_name)
            try:
                task_func(device)
            finally:
                self.post_ui(
                    lambda dev=device, name=task_name, previous=previous_task: self.restore_device_task(
                        dev, name, previous
                    )
                )

        for dev in target_devices:
            threading.Thread(target=run_task, args=(dev,), daemon=True).start()

    def open_selected_screens(self):
        devices = self.get_selected_devices()
        if not devices:
            messagebox.showwarning(
                "Sin selección", "Selecciona al menos un dispositivo para verlo."
            )
            return
        if not self.scrcpy or not Path(self.scrcpy).exists():
            messagebox.showerror(
                "Falta scrcpy",
                "No se encontró scrcpy dentro de la carpeta herramientas.",
            )
            return

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        columns = max(1, math.ceil(math.sqrt(len(devices))))
        rows = max(1, math.ceil(len(devices) / columns))
        window_width = max(320, screen_width // columns)
        window_height = max(420, (screen_height - 80) // rows)

        for index, device in enumerate(devices):
            existing = self.scrcpy_processes.get(device)
            if existing and existing.poll() is None:
                self.log(f"La pantalla de [{device}] ya está abierta.")
                continue

            title = self.display_device_name(device)
            x = (index % columns) * window_width
            y = (index // columns) * window_height
            command = [
                self.scrcpy,
                "-s",
                device,
                "--window-title",
                title,
                "--max-size=900",
                "--no-audio",
                "--stay-awake",
                f"--window-x={x}",
                f"--window-y={y}",
                f"--window-width={window_width}",
                f"--window-height={window_height}",
            ]
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(Path(self.scrcpy).parent),
                    creationflags=NO_WINDOW,
                )
                self.scrcpy_processes[device] = process
                self.set_device_task(device, "Pantalla abierta")
                self.log(f"Pantalla abierta para [{device}] como '{title}'.")
                threading.Thread(
                    target=self.monitor_scrcpy_process,
                    args=(device, process),
                    daemon=True,
                ).start()
            except Exception as error:
                self.log(f"No se pudo abrir scrcpy para [{device}]: {error}")

    def monitor_scrcpy_process(self, device, process):
        process.wait()
        if self.scrcpy_processes.get(device) is process:
            self.scrcpy_processes.pop(device, None)
            self.post_ui(
                lambda dev=device: self.restore_device_task(
                    dev, "Pantalla abierta", None
                )
            )
            self.log(f"Pantalla cerrada para [{device}].")

    def close_selected_screens(self):
        devices = self.get_selected_devices()
        if not devices:
            messagebox.showwarning(
                "Sin selección", "Selecciona los dispositivos cuyas ventanas cerrarás."
            )
            return
        closed = 0
        for device in devices:
            process = self.scrcpy_processes.get(device)
            if process and process.poll() is None:
                process.terminate()
                closed += 1
        self.log(f"Se solicitó cerrar {closed} ventana(s) de dispositivo.")

    @staticmethod
    def normalize_search_text(value):
        decomposed = unicodedata.normalize("NFKD", value.casefold())
        return "".join(char for char in decomposed if not unicodedata.combining(char))

    def parse_search_keywords(self):
        raw = self.search_keywords.get("1.0", tk.END)
        keywords = [item.strip() for item in re.split(r"[,;\n]+", raw) if item.strip()]
        return list(dict.fromkeys(keywords))

    def get_visible_android_text(self, device):
        """Obtiene el texto expuesto por la accesibilidad de la pantalla actual."""
        remote_xml = "/sdcard/window_dump_panel.xml"
        self.adb_capture(
            device,
            ["shell", "uiautomator", "dump", remote_xml],
            timeout=20,
        )
        xml_data = self.adb_capture(
            device,
            ["exec-out", "cat", remote_xml],
            timeout=20,
        )
        root = ET.fromstring(xml_data)
        visible_parts = []
        for node in root.iter("node"):
            for attribute in ("text", "content-desc"):
                value = node.attrib.get(attribute, "").strip()
                if value:
                    visible_parts.append(value)
        return "\n".join(dict.fromkeys(visible_parts))

    def get_screen_size(self, device):
        output = self.adb_capture(device, ["shell", "wm", "size"], timeout=10)
        matches = re.findall(r"(\d+)x(\d+)", output)
        if not matches:
            raise RuntimeError("No se pudo determinar el tamaño de pantalla.")
        width, height = matches[-1]
        return int(width), int(height)

    def scroll_device_once(self, device):
        size = self.screen_size_cache.get(device)
        if size is None:
            size = self.get_screen_size(device)
            self.screen_size_cache[device] = size
        width, height = size
        center_x = width // 2
        start_y = int(height * 0.78)
        end_y = int(height * 0.28)
        ok, detail = self.run_on_device(
            device,
            [
                "shell",
                "input",
                "swipe",
                str(center_x),
                str(start_y),
                str(center_x),
                str(end_y),
                "450",
            ],
            timeout=15,
        )
        if not ok:
            raise RuntimeError(detail)

    def append_search_result(self, message):
        self.search_results.config(state="normal")
        self.search_results.insert(tk.END, message + "\n")
        self.search_results.see(tk.END)
        self.search_results.config(state="disabled")

    def clear_search_results(self):
        if self.search_running:
            messagebox.showwarning("Búsqueda activa", "Detén la búsqueda antes de limpiar.")
            return
        self.search_results.config(state="normal")
        self.search_results.delete("1.0", tk.END)
        self.search_results.config(state="disabled")
        self.search_status_var.set("Listo para buscar.")

    def start_keyword_search(self):
        if self.search_running:
            return

        keywords = self.parse_search_keywords()
        if not keywords:
            messagebox.showwarning(
                "Faltan palabras", "Escribe al menos una palabra o frase para buscar."
            )
            return

        try:
            interval = float(self.search_interval_var.get().replace(",", "."))
            max_scrolls = int(self.search_max_scrolls_var.get())
        except ValueError:
            messagebox.showwarning(
                "Valores incorrectos",
                "El intervalo debe ser numérico y el máximo debe ser un número entero.",
            )
            return

        if not 0.5 <= interval <= 60:
            messagebox.showwarning(
                "Intervalo incorrecto", "Usa un intervalo de 0.5 a 60 segundos."
            )
            return
        if not 1 <= max_scrolls <= 200:
            messagebox.showwarning(
                "Límite incorrecto", "Usa un máximo de 1 a 200 desplazamientos."
            )
            return

        selected_devices = self.get_selected_devices()
        connected_devices = set(self.get_devices())
        devices = [device for device in selected_devices if device in connected_devices]
        if not devices:
            messagebox.showwarning(
                "Sin dispositivos seleccionados",
                "Selecciona al menos un celular autorizado y vuelve a intentar.",
            )
            return

        self.search_stop_event.clear()
        self.screen_size_cache.clear()
        self.search_devices = list(devices)
        self.search_running = True
        self.btn_start_search.config(state="disabled")
        self.btn_stop_search.config(state="normal")
        self.search_status_var.set("Búsqueda en curso...")
        self.append_search_result(
            f"[{time.strftime('%H:%M:%S')}] Inicio · {len(devices)} dispositivo(s) · "
            f"palabras: {', '.join(keywords)}"
        )
        self.log(
            f"Búsqueda por palabras iniciada en {len(devices)} dispositivo(s)."
        )
        for device in devices:
            self.set_device_task(device, "Búsqueda por palabras")

        threading.Thread(
            target=self.keyword_search_worker,
            args=(devices, keywords, interval, max_scrolls),
            daemon=True,
        ).start()

    def stop_keyword_search(self):
        if self.search_running:
            self.search_stop_event.set()
            self.search_status_var.set("Deteniendo búsqueda...")
            self.log("Se solicitó detener la búsqueda por palabras.")

    def keyword_search_worker(self, devices, keywords, interval, max_scrolls):
        normalized_keywords = {
            keyword: self.normalize_search_text(keyword) for keyword in keywords
        }
        found_result = None
        completed_scrolls = 0
        errors = []

        for step in range(max_scrolls + 1):
            if self.search_stop_event.is_set():
                break
            cycle_started = time.monotonic()

            for device in devices:
                if self.search_stop_event.is_set():
                    break
                try:
                    visible_text = self.get_visible_android_text(device)
                    normalized_text = self.normalize_search_text(visible_text)
                    matches = [
                        original
                        for original, normalized in normalized_keywords.items()
                        if normalized in normalized_text
                    ]
                    if matches:
                        found_result = (device, matches, step, visible_text)
                        self.search_stop_event.set()
                        break
                except Exception as error:
                    errors.append(f"{device}: {error}")
                    self.log(f"Error analizando pantalla de [{device}]: {error}")

            if found_result or self.search_stop_event.is_set():
                break
            if step >= max_scrolls:
                break

            for device in devices:
                if self.search_stop_event.is_set():
                    break
                try:
                    self.scroll_device_once(device)
                except Exception as error:
                    errors.append(f"{device}: {error}")
                    self.log(f"Error desplazando pantalla de [{device}]: {error}")
            completed_scrolls += 1
            elapsed = time.monotonic() - cycle_started
            remaining = max(0.0, interval - elapsed)
            if self.search_stop_event.wait(remaining):
                break

        if found_result:
            device, matches, step, visible_text = found_result
            preview = " ".join(visible_text.split())[:240]
            result_message = (
                f"[{time.strftime('%H:%M:%S')}] COINCIDENCIA en {device} · "
                f"{', '.join(matches)} · después de {step} desplazamiento(s)\n"
                f"Vista previa: {preview}"
            )
            status = f"Coincidencia encontrada en {device}. Revisa la pantalla."
            self.log(
                f"Coincidencia encontrada en [{device}]: {', '.join(matches)}."
            )
        elif self.search_stop_event.is_set():
            result_message = (
                f"[{time.strftime('%H:%M:%S')}] Búsqueda detenida · "
                f"{completed_scrolls} desplazamiento(s)."
            )
            status = "Búsqueda detenida por el operador."
        else:
            result_message = (
                f"[{time.strftime('%H:%M:%S')}] Sin coincidencias · "
                f"límite de {max_scrolls} desplazamiento(s) alcanzado."
            )
            status = "Búsqueda terminada sin coincidencias."

        if errors:
            result_message += f"\nAvisos técnicos: {len(errors)}"

        self.post_ui(
            lambda message=result_message, final_status=status: self.finish_keyword_search(
                message, final_status
            )
        )

    def finish_keyword_search(self, message, status):
        self.append_search_result(message)
        self.search_status_var.set(status)
        self.btn_start_search.config(state="normal")
        self.btn_stop_search.config(state="disabled")
        self.search_running = False
        for device in self.search_devices:
            self.restore_device_task(device, "Búsqueda por palabras", None)
        self.search_devices = []

    def capture_link_from_clipboard(self):
        try:
            value = self.root.clipboard_get().strip()
        except tk.TclError:
            messagebox.showwarning(
                "Portapapeles vacío",
                "Copia primero el enlace de la publicación desde Facebook.",
            )
            return

        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            messagebox.showwarning(
                "Contenido no válido", "El portapapeles no contiene un enlace web."
            )
            return

        host = parsed.netloc.casefold().split(":")[0]
        facebook_hosts = ("facebook.com", "fb.com", "fb.watch")
        if not any(host == item or host.endswith("." + item) for item in facebook_hosts):
            messagebox.showwarning(
                "Enlace no reconocido",
                "El enlace no parece pertenecer a Facebook. Revísalo antes de guardarlo.",
            )
            return

        self.search_link_var.set(value)
        self.append_search_result(
            f"[{time.strftime('%H:%M:%S')}] Enlace capturado: {value}"
        )
        self.log("Enlace de publicación capturado desde el portapapeles.")

    def open_facebook_all(self):
        self.log("Abriendo Facebook en los dispositivos seleccionados...")

        def task(dev):
            opened = False
            for pkg in ["com.facebook.katana", "com.facebook.lite"]:
                res = subprocess.run(
                    [self.adb, "-s", dev, "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=NO_WINDOW,
                )
                if "No activities found" not in res.stdout and "Error" not in res.stdout and res.returncode == 0:
                    opened = True
                    break
            if opened:
                self.log(f"-> Facebook abierto en dispositivo: {dev}")
            else:
                self.log(f"-> [{dev}] No se pudo abrir Facebook o no está instalada.")

        self.execute_multithreaded(task, "Abrir Facebook")

    def open_url_all(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Aviso", "La URL no puede estar vacía.")
            return
        self.log(f"Abriendo URL en paralelo: {url}")

        def task(dev):
            ok, detail = self.run_on_device(
                dev,
                ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url],
            )
            if ok:
                self.log(f"-> URL abierta en dispositivo: {dev}")
            else:
                self.log(f"-> No se abrió la URL en [{dev}]: {detail}")

        self.execute_multithreaded(task, "Abrir enlace")

    def publish_text_all(self):
        text = self.text_post.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Aviso", "El texto de publicación está vacío.")
            return
        self.log("Enviando texto simultáneo a los dispositivos...")

        def task(dev):
            for line in text.split("\n"):
                formatted_line = line.replace(" ", "%s").replace("&", "\\&")
                ok, detail = self.run_on_device(
                    dev, ["shell", "input", "text", formatted_line]
                )
                if not ok:
                    self.log(f"-> Error enviando texto a [{dev}]: {detail}")
                    return
                self.run_on_device(dev, ["shell", "input", "keyevent", "66"])
            self.log(f"-> Texto enviado al dispositivo: {dev}")

        self.execute_multithreaded(task, "Enviar texto")

    def execute_vision_reaction(self, template_filename):
        template_path = os.path.join("templates", template_filename)
        if not os.path.exists(template_path):
            messagebox.showerror(
                "Falta Plantilla",
                f"No se encontró el archivo de imagen '{template_filename}' en la"
                " carpeta 'templates'. Por favor, guárdalo ahí antes de buscarlo por"
                " forma.",
            )
            return

        self.log(
            f"Iniciando búsqueda visual de reacción usando molde:"
            f" [{template_filename}]"
        )

        def task(dev):
            try:
                result = subprocess.run(
                    [self.adb, "-s", dev, "exec-out", "screencap", "-p"],
                    stdout=subprocess.PIPE,
                    creationflags=NO_WINDOW,
                )
                screen_bytes = result.stdout
                if not screen_bytes:
                    self.log(f"[{dev}] Error: No se pudo capturar la pantalla.")
                    return

                nparr = np.frombuffer(screen_bytes, np.uint8)
                screen_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                template_img = cv2.imread(template_path, cv2.IMREAD_COLOR)
                if template_img is None:
                    self.log(f"Error al leer la plantilla {template_filename}")
                    return

                h, w = template_img.shape[:2]

                match_result = cv2.matchTemplate(
                    screen_img, template_img, cv2.TM_CCOEFF_NORMED
                )
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match_result)

                threshold = 0.80
                if max_val >= threshold:
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2

                    self.run_on_device(
                        dev, ["shell", "input", "tap", str(center_x), str(center_y)]
                    )
                    self.log(
                        f"[{dev}] ¡Reacción encontrada por forma! Coordenadas"
                        f" aplicadas: X={center_x}, Y={center_y} (Confianza:"
                        f" {max_val:.2f})"
                    )
                else:
                    self.log(
                        f"[{dev}] No se detectó la forma de la reacción en pantalla"
                        f" (Coincidencia máxima: {max_val:.2f})"
                    )

            except Exception as e:
                self.log(f"Error en procesamiento visual para [{dev}]: {e}")

        self.execute_multithreaded(task, f"Reacción visual: {template_filename}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ProfessionalPhoneController(root)
    root.mainloop()
