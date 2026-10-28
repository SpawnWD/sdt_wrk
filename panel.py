import os
import queue
import re
import subprocess
import threading
import time
import tkinter as tk
import unicodedata
import xml.etree.ElementTree as ET
from tkinter import filedialog, messagebox, scrolledtext, ttk
from urllib.parse import urlparse

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
        self.root.geometry("900x750")
        self.root.minsize(850, 700)

        # Detectar la ruta de ADB automáticamente (busca en 'herramientas' o en el sistema)
        self.adb = self.find_adb()
        self.ui_queue = queue.Queue()
        self.search_stop_event = threading.Event()
        self.search_running = False
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

    def create_general_widgets(self):
        # --- Marco Superior: Dispositivos ---
        dev_frame = ttk.LabelFrame(
            self.tab_general, text=" Gestión de Dispositivos Conectados ", padding=10
        )
        dev_frame.pack(fill="x", padx=10, pady=10)

        btn_scan = ttk.Button(
            dev_frame,
            text="Escanear Dispositivos",
            command=self.refresh_devices,
            style="Success.TButton",
        )
        btn_scan.pack(side="left", padx=5)

        self.lbl_devices = ttk.Label(
            dev_frame,
            text="Dispositivos detectados: 0",
            font=("Segoe UI", 9, "bold"),
        )
        self.lbl_devices.pack(side="left", padx=15)

        # --- Marco Central: Acciones Masivas (URLs, Facebook y Publicaciones) ---
        act_frame = ttk.LabelFrame(
            self.tab_general, text=" Automatización de Contenido ", padding=10
        )
        act_frame.pack(fill="x", padx=10, pady=5)

        # Botón para abrir Facebook en todos los dispositivos conectados
        ttk.Button(
            act_frame,
            text="Abrir Facebook en Todos",
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
            text="Abrir en Todos",
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
            text="Enviar Texto Simultáneo a Todos",
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
                " inteligente en todos los dispositivos conectados."
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
        self.search_interval_var = tk.StringVar(value="4")
        ttk.Spinbox(
            settings_row,
            from_=1,
            to=60,
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
        self.root.destroy()

    def get_devices(self):
        try:
            result = subprocess.run(
                [self.adb, "devices"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
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
        self.devices = self.get_devices()
        count = len(self.devices)
        device_names = ", ".join(self.devices) if count > 0 else "Ninguno"
        self.lbl_devices.config(
            text=f"Dispositivos detectados: {count} ({device_names})"
        )
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
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "Error ADB").strip()
            raise RuntimeError(detail)
        return result.stdout

    def execute_multithreaded(self, task_func):
        if not self.devices:
            messagebox.showwarning(
                "Aviso", "No hay dispositivos conectados. Escanee primero."
            )
            return
        for dev in self.devices:
            threading.Thread(target=task_func, args=(dev,), daemon=True).start()

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
        width, height = self.get_screen_size(device)
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
            interval = int(self.search_interval_var.get())
            max_scrolls = int(self.search_max_scrolls_var.get())
        except ValueError:
            messagebox.showwarning(
                "Valores incorrectos", "El intervalo y el máximo deben ser números enteros."
            )
            return

        if not 1 <= interval <= 60:
            messagebox.showwarning("Intervalo incorrecto", "Usa un intervalo de 1 a 60 segundos.")
            return
        if not 1 <= max_scrolls <= 200:
            messagebox.showwarning(
                "Límite incorrecto", "Usa un máximo de 1 a 200 desplazamientos."
            )
            return

        devices = self.get_devices()
        self.devices = devices
        if not devices:
            messagebox.showwarning(
                "Sin dispositivos",
                "No hay celulares autorizados. Conecta uno y vuelve a intentar.",
            )
            return

        self.search_stop_event.clear()
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
            if self.search_stop_event.wait(interval):
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
        self.log("Abriendo Facebook en todos los dispositivos...")

        def task(dev):
            opened = False
            for pkg in ["com.facebook.katana", "com.facebook.lite"]:
                res = subprocess.run(
                    [self.adb, "-s", dev, "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"],
                    capture_output=True, text=True
                )
                if "No activities found" not in res.stdout and "Error" not in res.stdout and res.returncode == 0:
                    opened = True
                    break
            if opened:
                self.log(f"-> Facebook abierto en dispositivo: {dev}")
            else:
                self.log(f"-> [{dev}] No se pudo abrir Facebook o no está instalada.")

        self.execute_multithreaded(task)

    def open_url_all(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Aviso", "La URL no puede estar vacía.")
            return
        self.log(f"Abriendo URL en paralelo: {url}")

        def task(dev):
            self.run_on_device(
                dev,
                ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url],
            )
            self.log(f"-> URL abierta en dispositivo: {dev}")

        self.execute_multithreaded(task)

    def publish_text_all(self):
        text = self.text_post.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Aviso", "El texto de publicación está vacío.")
            return
        self.log("Enviando texto simultáneo a los dispositivos...")

        def task(dev):
            for line in text.split("\n"):
                formatted_line = line.replace(" ", "%s").replace("&", "\\&")
                self.run_on_device(dev, ["shell", "input", "text", formatted_line])
                self.run_on_device(dev, ["shell", "input", "keyevent", "66"])
            self.log(f"-> Texto enviado a dispositivo: {dev}")

        self.execute_multithreaded(task)

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

        self.execute_multithreaded(task)


if __name__ == "__main__":
    root = tk.Tk()
    app = ProfessionalPhoneController(root)
    root.mainloop()
