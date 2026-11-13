import ctypes
from datetime import date, timedelta
import hashlib
import hmac
import json
import os
from pathlib import Path
import shutil
import sys
import tkinter as tk
from tkinter import ttk
import uuid


LICENSE_VERSION = 2
VALIDITY_DAYS = 20
DRIVE_REMOVABLE = 2
XOR_MASK = 0x5A

# Los fragmentos de validación no se almacenan como texto legible ni se escriben en la licencia.
_PREFIX_DATA = (48, 53, 41, 63, 48, 53, 41, 63, 104, 107, 107, 111)
_SUFFIX_DATA = (104, 106)
_SIGNING_DATA = (
    210, 149, 110, 226, 94, 13, 188, 218, 46, 32, 174, 55, 154, 141, 121, 3,
    0, 162, 211, 47, 112, 125, 229, 11, 150, 132, 107, 138, 145, 251, 235, 149,
)


def _decode_bytes(values):
    return bytes(value ^ XOR_MASK for value in values)


def executable_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_directory():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()


def _set_window_icon(root):
    icon_png = resource_directory() / "assets" / "app_icon.png"
    icon_ico = resource_directory() / "assets" / "app_icon.ico"
    try:
        if icon_png.exists():
            root._app_icon = tk.PhotoImage(file=str(icon_png))
            root.iconphoto(True, root._app_icon)
        if os.name == "nt" and icon_ico.exists():
            root.iconbitmap(default=str(icon_ico))
    except tk.TclError:
        root._app_icon = None


def _drive_root(path):
    anchor = Path(path).resolve().anchor
    return anchor if anchor else os.path.abspath(os.sep)


def _drive_type(root):
    if os.name != "nt":
        return 3
    try:
        return int(ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root)))
    except Exception:
        return 3


def _volume_serial(root):
    if os.name != "nt":
        return "0"
    serial = ctypes.c_uint32()
    maximum_component = ctypes.c_uint32()
    flags = ctypes.c_uint32()
    volume_name = ctypes.create_unicode_buffer(261)
    filesystem_name = ctypes.create_unicode_buffer(261)
    try:
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            volume_name,
            len(volume_name),
            ctypes.byref(serial),
            ctypes.byref(maximum_component),
            ctypes.byref(flags),
            filesystem_name,
            len(filesystem_name),
        )
        if ok:
            return f"{serial.value:08X}"
    except Exception:
        pass
    return "0"


def _machine_guid():
    if os.name == "nt":
        try:
            import winreg

            access = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                access,
            ) as key:
                return str(winreg.QueryValueEx(key, "MachineGuid")[0])
        except Exception:
            pass
    return f"{uuid.getnode():012x}"


class LicenseManager:
    def __init__(self, app_directory=None, today_provider=None):
        self.app_directory = Path(app_directory or executable_directory()).resolve()
        self.today_provider = today_provider or date.today
        self.root = _drive_root(self.app_directory)
        self.mode = "usb" if _drive_type(self.root) == DRIVE_REMOVABLE else "machine"
        self.fingerprint = self._build_fingerprint()
        self.license_path = self._license_path()

    def _build_fingerprint(self):
        if self.mode == "usb":
            try:
                capacity = shutil.disk_usage(self.root).total
            except Exception:
                capacity = 0
            # No se incluye la letra de unidad: Windows puede asignar otra a la misma USB.
            material = f"usb|{_volume_serial(self.root)}|{capacity}"
        else:
            system_root = _drive_root(os.environ.get("SystemRoot", self.root))
            material = f"machine|{_machine_guid()}|{_volume_serial(system_root)}"
        return hashlib.sha256(material.encode("utf-8", errors="replace")).hexdigest()

    def _license_path(self):
        if self.mode == "usb":
            return self.app_directory / ".panel_celulares_v2.license"
        local_app_data = Path(os.environ.get("LOCALAPPDATA", self.app_directory))
        return local_app_data / "PanelCelularesV2" / "license.json"

    @staticmethod
    def _signature(payload):
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(_decode_bytes(_SIGNING_DATA), canonical, hashlib.sha256).hexdigest()

    def _read_record(self):
        try:
            record = json.loads(self.license_path.read_text(encoding="utf-8"))
            signature = str(record.pop("signature", ""))
            if not signature or not hmac.compare_digest(signature, self._signature(record)):
                return None
            return record
        except Exception:
            return None

    def _write_record(self, record):
        payload = dict(record)
        payload["signature"] = self._signature(record)
        self.license_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.license_path.with_suffix(self.license_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.license_path)
        if os.name == "nt" and self.mode == "usb":
            try:
                ctypes.windll.kernel32.SetFileAttributesW(str(self.license_path), 0x02)
            except Exception:
                pass

    def expected_password(self, current_date=None):
        current_date = current_date or self.today_provider()
        prefix = _decode_bytes(_PREFIX_DATA).decode("utf-8")
        suffix = _decode_bytes(_SUFFIX_DATA).decode("utf-8")
        return f"{prefix}{current_date:%d%m%Y}{suffix}"

    def password_is_valid(self, candidate, current_date=None):
        expected = self.expected_password(current_date)
        return hmac.compare_digest(str(candidate or ""), expected)

    def inspect(self):
        today = self.today_provider()
        record = self._read_record()
        if record is None:
            return False, "Se requiere la activación inicial."
        if record.get("version") != LICENSE_VERSION:
            return False, "La licencia pertenece a otra versión."
        if record.get("mode") != self.mode or record.get("fingerprint") != self.fingerprint:
            target = "memoria USB" if self.mode == "usb" else "equipo"
            return False, f"La copia actual debe vincularse a este {target}."
        try:
            next_validation = date.fromisoformat(record["next_validation"])
            last_seen = date.fromisoformat(record["last_seen"])
        except (KeyError, TypeError, ValueError):
            return False, "La licencia local no es válida."
        if today < last_seen:
            return False, "La fecha del equipo retrocedió; se requiere una nueva validación."
        if today >= next_validation:
            return False, "Han transcurrido 20 días; se requiere renovar la validación."
        if today != last_seen:
            record["last_seen"] = today.isoformat()
            try:
                self._write_record(record)
            except Exception:
                return False, "No se pudo actualizar la licencia local."
        remaining = (next_validation - today).days
        return True, f"Licencia vigente por {remaining} día(s)."

    def activate(self, candidate):
        today = self.today_provider()
        if not self.password_is_valid(candidate, today):
            return False, "Contraseña incorrecta para la fecha actual."
        record = {
            "version": LICENSE_VERSION,
            "mode": self.mode,
            "fingerprint": self.fingerprint,
            "validated_on": today.isoformat(),
            "next_validation": (today + timedelta(days=VALIDITY_DAYS)).isoformat(),
            "last_seen": today.isoformat(),
        }
        try:
            self._write_record(record)
        except Exception as error:
            return False, f"No se pudo guardar la licencia: {error}"
        return True, "Activación correcta. El acceso será válido durante 20 días."


def run_startup_gate():
    manager = LicenseManager()
    root = tk.Tk()
    root.title("Administración de móviles (移动设备管理)")
    _set_window_icon(root)
    root.resizable(False, False)
    root.configure(bg="#eef3f8")
    width, height = 590, 370
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    header = tk.Frame(root, bg="#145ea8", height=115)
    header.pack(fill="x")
    header.pack_propagate(False)
    tk.Label(
        header,
        text="Administración de móviles (移动设备管理)",
        bg="#145ea8",
        fg="white",
        font=("Microsoft YaHei UI", 18, "bold"),
    ).pack(pady=(22, 2))
    tk.Label(
        header,
        text="Control multi-dispositivo",
        bg="#145ea8",
        fg="#dcecff",
        font=("Segoe UI", 10),
    ).pack()

    body = tk.Frame(root, bg="#eef3f8", padx=34, pady=24)
    body.pack(fill="both", expand=True)
    mode_text = "Memoria USB" if manager.mode == "usb" else "Equipo local"
    tk.Label(
        body,
        text=f"Licencia vinculada a: {mode_text}",
        bg="#eef3f8",
        fg="#334b61",
        font=("Segoe UI", 10, "bold"),
    ).pack(anchor="w")
    status_var = tk.StringVar(value="Comprobando licencia...")
    status_label = tk.Label(
        body,
        textvariable=status_var,
        bg="#eef3f8",
        fg="#334b61",
        justify="left",
        wraplength=515,
        font=("Segoe UI", 10),
    )
    status_label.pack(anchor="w", pady=(9, 12))
    progress = ttk.Progressbar(body, mode="indeterminate")
    progress.pack(fill="x")
    progress.start(12)

    password_frame = tk.Frame(body, bg="#eef3f8")
    result = {"allowed": False}

    def finish(allowed):
        result["allowed"] = allowed
        try:
            root.destroy()
        except tk.TclError:
            pass

    def submit_password(event=None):
        accepted, message = manager.activate(password_var.get())
        password_var.set("")
        status_var.set(message)
        if accepted:
            status_label.configure(fg="#1b7a3d")
            activate_button.configure(state="disabled")
            root.after(650, lambda: finish(True))
        else:
            status_label.configure(fg="#b42318")
            password_entry.focus_set()

    def show_activation(reason):
        progress.stop()
        progress.pack_forget()
        status_var.set(reason)
        status_label.configure(fg="#9a3412")
        password_frame.pack(fill="x", pady=(2, 0))
        password_entry.focus_set()

    password_var = tk.StringVar()
    tk.Label(
        password_frame,
        text="Contraseña de activación:",
        bg="#eef3f8",
        fg="#334b61",
        font=("Segoe UI", 9, "bold"),
    ).pack(anchor="w")
    password_entry = ttk.Entry(password_frame, textvariable=password_var, show="●", font=("Segoe UI", 11))
    password_entry.pack(fill="x", pady=(5, 10))
    password_entry.bind("<Return>", submit_password)
    button_row = tk.Frame(password_frame, bg="#eef3f8")
    button_row.pack(fill="x")
    activate_button = ttk.Button(button_row, text="Activar y continuar", command=submit_password)
    activate_button.pack(side="left")
    ttk.Button(button_row, text="Cancelar", command=lambda: finish(False)).pack(side="right")

    def inspect_license():
        valid, message = manager.inspect()
        status_var.set(message)
        if valid:
            status_label.configure(fg="#1b7a3d")
            root.after(750, lambda: finish(True))
        else:
            show_activation(message)

    root.protocol("WM_DELETE_WINDOW", lambda: finish(False))
    root.after(120, inspect_license)
    root.mainloop()
    return result["allowed"]
