# Bitácora de cambios — Panel Celulares V2

Esta bitácora registra el estado base del proyecto y todos los cambios que se realicen a partir de este momento. Su objetivo es mantener trazabilidad, facilitar diagnósticos y permitir una reversión controlada cuando sea necesario.

## Reglas de control

1. Antes de modificar código se debe registrar el objetivo, los archivos afectados, el riesgo y la referencia de rollback.
2. Cada cambio debe tener un identificador único con formato `CHG-AAAAMMDD-HHMM`.
3. No se deben mezclar correcciones independientes en una sola entrada.
4. Después de cada cambio se deben registrar las pruebas realizadas y su resultado real.
5. Un cambio no se considera terminado hasta comprobar sintaxis, arranque y funciones afectadas.
6. Los resultados no verificados deben marcarse expresamente como `Pendiente de prueba`.
7. Nunca se deben registrar contraseñas, tokens, claves, datos personales ni contenido privado de los celulares.
8. Antes de reemplazar o eliminar un archivo debe existir una copia recuperable o un commit de Git.
9. Para cambios publicados se debe preferir una reversión que conserve el historial.
10. La bitácora debe actualizarse en la misma sesión en la que se realiza el cambio.

## Cambios en curso

### CHG-20261027-2204 — Búsqueda asistida por palabras clave

- Fecha y hora: 2026-10-27 22:04:56 (America/Mexico_City)
- Tipo: Funcionalidad y optimización
- Estado: En curso
- Responsable: Codex, bajo solicitud del propietario
- Solicitud: Incorporar desplazamiento por intervalo, búsqueda de palabras clave y captura del enlace de una publicación.
- Motivo: Facilitar la localización asistida de publicaciones visibles en Facebook sin ejecutar reacciones, comentarios ni publicaciones automáticas.
- Comportamiento anterior: El programa sólo captura la pantalla para coincidencias visuales de iconos; no recorre contenido ni busca texto.
- Cambio propuesto:
  - Nueva pestaña de búsqueda asistida.
  - Caja de palabras clave separadas por comas o líneas.
  - Intervalo y máximo de desplazamientos configurables.
  - Inicio, detención y pausa automática al detectar una coincidencia.
  - Lectura del texto visible mediante la jerarquía de accesibilidad de Android.
  - Campo para conservar el enlace copiado manualmente desde Facebook.
  - Actualizaciones seguras de la interfaz desde tareas secundarias.
- Archivos previstos: `panel.py`, `LEEME.txt` y `BITACORA.md`.
- Riesgos:
  - Facebook puede no exponer todo el texto mediante accesibilidad.
  - Un desplazamiento podría saltar parcialmente una publicación.
  - El enlace no siempre puede extraerse directamente del dispositivo por restricciones de Android; se usará captura desde el portapapeles con intervención del operador.
- Límites de seguridad:
  - Sin desplazamiento indefinido.
  - Sin reacciones, comentarios, mensajes o publicaciones automáticas.
  - Sin técnicas para ocultar automatización.
  - Cancelación disponible en todo momento.
- Referencia previa de rollback: Línea base `BASE-20261027-2158` y commit Git local que se creará antes de editar archivos funcionales.
- Archivos modificados: Pendiente.
- Pruebas realizadas: Pendiente.
- Resultado de las pruebas: Pendiente.
- Hash, commit o versión resultante: Pendiente.
- Publicado o respaldado: Pendiente.
- Procedimiento de rollback: Restaurar `panel.py` y `LEEME.txt` desde el commit local de línea base.
- Observaciones: Esta entrada fue registrada antes de modificar el código funcional.

## Estado base protegido

### BASE-20261027-2158 — Registro inicial

- Fecha: 2026-10-27 21:58:42 (America/Mexico_City)
- Tipo: Línea base
- Estado: Registrado
- Responsable del registro: Codex, bajo solicitud del propietario
- Ubicación: `C:\Users\SpawnWD\Documents\Miguel Marquez\Pino\Panel Celulares V2`
- Repositorio Git local: No existe actualmente
- Commit o etiqueta: No disponible
- Motivo: Registrar el estado original antes de optimizar o corregir el proyecto
- Archivos funcionales modificados: Ninguno

### Entorno comprobado

- Python: 3.12.10, 64 bits
- Tkinter: 8.6
- OpenCV: 5.0.0
- NumPy: 2.5.4
- scrcpy: 5.0
- ADB: Incluido dentro de `herramientas`
- Lanzador `py`: Disponible
- Importación de `panel.py`: Correcta
- Reconocimiento visual: Habilitado

### Prueba funcional previa

- El panel abrió correctamente.
- El proceso de Python permaneció estable y respondió normalmente.
- Se detectó un dispositivo autorizado mediante ADB.
- Dispositivo detectado durante la prueba: Moto E6 Play.
- Serie observada: `ZE222HSLC9`.
- La consola mostró un dispositivo conectado.
- No se ejecutaron publicaciones, escritura de texto, apertura de Facebook ni reacciones sobre el dispositivo.
- No se observaron errores de inicio.

### Inventario inicial

| Archivo | Tamaño inicial | SHA-256 inicial |
|---|---:|---|
| `panel.py` | 14,380 bytes | `93013DE71E4FCE1B9B0AD982A2A207AFEB1614AAB9071C35CB9C3E3D6D3C5C6E` |
| `PanelCelulares.ps1` | 12,929 bytes | `9BD94E6E2ECBEF932BBF4F0E802D860ECAE755BD6B1ADC13DE2610306B0E9B25` |
| `Abrir Panel.bat` | 108 bytes | `CF9BBF94A8FE3C31A7CF39383CDCF76940AC3D0C3C6CB5D432B9C507B3704387` |
| `Diagnostico.bat` | 1,508 bytes | `31E2087CFE876E1FA9A6CE7631483F56625ADBBE8F47D242AED60B0304444457` |
| `LEEME.txt` | 4,672 bytes | `48D4862C3879482387A333F41C7C1E17B945AEC86284E4E168DDBFEC31503292` |

Los hashes permiten comprobar si alguno de estos archivos cambió respecto a la línea base. No sustituyen una copia de seguridad ni un historial Git.

### Condiciones conocidas antes de optimizar

- La documentación describe funciones que no están implementadas en `panel.py`.
- `PanelCelulares.ps1` contiene código Python, no PowerShell, y no es un componente funcional del lanzador actual.
- El programa no genera una bitácora operativa de las acciones realizadas sobre los celulares.
- La consola visible sólo conserva mensajes mientras la aplicación permanece abierta.
- No existe selección individual de dispositivos; las acciones actuales se aplican a todos los detectados.
- El envío de texto mediante ADB puede fallar con acentos, `ñ`, emojis y símbolos especiales.
- Algunas operaciones pueden informar éxito después de que una llamada ADB haya fallado.
- La interfaz de Tkinter recibe actualizaciones desde hilos secundarios, lo cual puede producir fallos intermitentes.
- El reconocimiento visual depende de resolución, escala, tema y apariencia de Facebook.
- El proyecto no se encuentra actualmente bajo control de versiones Git.

### Referencia de rollback inicial

Los hashes anteriores identifican la línea base, pero todavía no existe un mecanismo automático de rollback. Antes de modificar archivos funcionales se debe realizar una de estas acciones:

1. Inicializar Git y crear un commit de línea base; o
2. Crear una copia íntegra, fechada y verificada de la carpeta.

No se debe comenzar una modificación funcional hasta disponer de una referencia recuperable.

---

## Cambios de entorno anteriores a la bitácora

### ENV-20261027-2100 — Instalación de Python y dependencias

- Tipo: Entorno
- Estado: Completado
- Motivo: Permitir el arranque y la prueba del panel
- Cambios realizados:
  - Instalación de Python 3.12.10 para el usuario actual.
  - Actualización de `pip` a 26.2.2.
  - Instalación de OpenCV 5.0.0.
  - Instalación de NumPy 2.5.4.
- Archivos del proyecto modificados: Ninguno
- Verificación: El comando `py -3` funciona y `panel.py` importa correctamente con reconocimiento visual habilitado.
- Rollback: Desinstalar las dependencias o Python desde Aplicaciones instaladas; no afecta el contenido original del proyecto.

---

## Plantilla para próximos cambios

### CHG-AAAAMMDD-HHMM — Título breve

- Fecha y hora:
- Tipo: Corrección / Optimización / Funcionalidad / Seguridad / Documentación / Entorno
- Estado: Planeado / En curso / Completado / Fallido / Revertido
- Responsable:
- Solicitud:
- Motivo:
- Comportamiento anterior:
- Cambio propuesto:
- Archivos previstos:
- Riesgos:
- Referencia previa de rollback:
- Archivos modificados:
- Resumen de implementación:
- Pruebas realizadas:
- Resultado de las pruebas:
- Limitaciones o pruebas pendientes:
- Hash, commit o versión resultante:
- Publicado o respaldado: Sí / No
- Procedimiento de rollback:
- Observaciones:

