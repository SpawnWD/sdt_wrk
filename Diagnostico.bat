@echo off
title Diagnostico - Panel de Celulares
cd /d "%~dp0"
set "OUT=%~dp0diagnostico.txt"
set "SCR="
for /d %%D in ("%~dp0herramientas\scrcpy-win64-*") do set "SCR=%%D"
echo Revisando la computadora, espera unos segundos...
echo.
> "%OUT%" echo ==== DIAGNOSTICO PANEL DE CELULARES ====
>>"%OUT%" echo Carpeta: %~dp0
>>"%OUT%" ver
>>"%OUT%" echo.
>>"%OUT%" echo ---- Archivos ----
>>"%OUT%" dir /b "%~dp0"
>>"%OUT%" dir /b "%SCR%" 2>&1
>>"%OUT%" echo.
>>"%OUT%" echo ---- PowerShell ----
>>"%OUT%" 2>&1 powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "'Version: ' + $PSVersionTable.PSVersion; 'Modo: ' + $ExecutionContext.SessionState.LanguageMode; Get-ExecutionPolicy -List | Out-String; try { Add-Type -AssemblyName System.Windows.Forms; 'Ventanas: OK' } catch { 'Ventanas: ERROR ' + $_ }"
>>"%OUT%" echo.
>>"%OUT%" echo ---- ADB (celulares conectados) ----
>>"%OUT%" 2>&1 "%SCR%\adb.exe" devices -l
>>"%OUT%" echo.
>>"%OUT%" echo ---- Registro de inicio ----
if exist "%~dp0registro_inicio.txt" type "%~dp0registro_inicio.txt" >>"%OUT%"
>>"%OUT%" echo ---- Registro de errores ----
if exist "%~dp0registro_errores.txt" type "%~dp0registro_errores.txt" >>"%OUT%"
"%SCR%\adb.exe" kill-server >nul 2>&1
type "%OUT%"
echo.
echo ================================================================
echo  Listo. Se guardo todo en "diagnostico.txt" en esta carpeta.
echo  Envia ese archivo (o una captura de esta ventana).
echo ================================================================
pause
