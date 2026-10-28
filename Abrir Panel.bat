@echo off
cd /d "%~dp0"
py -3 panel.py
if errorlevel 1 (
  echo No se pudo iniciar panel.py.
  pause
)