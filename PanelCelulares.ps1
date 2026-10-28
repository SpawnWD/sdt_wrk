import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

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

        self.notebook.add(self.tab_general, text=" Control y Automatización General ")
        self.notebook.add(
            self.tab_vision, text=" Reacciones por Forma (Computer Vision) "
        )

        self.create_general_widgets()
        self.create_vision_widgets()

        # Consola de Registros global inferior
        self.create_console_widget()

        self.refresh_devices()

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

        # --- Marco Central: Acciones Masivas (URLs y Publicaciones) ---
        act_frame = ttk.LabelFrame(
            self.tab_general, text=" Automatización de Contenido ", padding=10
        )
        act_frame.pack(fill="x", padx=10, pady=5)

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
            style="Primary.TButton",
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

    def log(self, message):
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)

    def get_devices(self):
        try:
            result = subprocess.run(
                ["adb", "devices"], capture_output=True, text=True, check=True
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

    def run_on_device(self, device, command):
        try:
            full_cmd = ["adb", "-s", device] + command
            subprocess.run(full_cmd, capture_output=True, text=True, check=True)
        except Exception as e:
            self.log(f"Error en [{device}]: {e}")

    def execute_multithreaded(self, task_func):
        if not self.devices:
            messagebox.showwarning(
                "Aviso", "No hay dispositivos conectados. Escanee primero."
            )
            return
        for dev in self.devices:
            threading.Thread(target=task_func, args=(dev,), daemon=True).start()

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
                # 1. Capturar pantalla directamente desde ADB en memoria binaria
                result = subprocess.run(
                    ["adb", "-s", dev, "exec-out", "screencap", "-p"],
                    stdout=subprocess.PIPE,
                )
                screen_bytes = result.stdout
                if not screen_bytes:
                    self.log(f"[{dev}] Error: No se pudo capturar la pantalla.")
                    return

                # 2. Decodificar imagen para OpenCV
                nparr = np.frombuffer(screen_bytes, np.uint8)
                screen_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                # 3. Cargar la plantilla (forma de la reacción)
                template_img = cv2.imread(template_path, cv2.IMREAD_COLOR)
                if template_img is None:
                    self.log(f"Error al leer la plantilla {template_filename}")
                    return

                h, w = template_img.shape[:2]

                # 4. Realizar Template Matching (búsqueda de la forma)
                match_result = cv2.matchTemplate(
                    screen_img, template_img, cv2.TM_CCOEFF_NORMED
                )
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match_result)

                # Umbral de coincidencia (80% de similitud de forma)
                threshold = 0.80
                if max_val >= threshold:
                    # Calcular el centro exacto del icono encontrado
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2

                    # Ejecutar toque táctil en el dispositivo en las coordenadas encontradas
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
    app = Professional