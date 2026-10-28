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

## Cambios completados

### CHG-20261028-1746 — Instancia única y expansión de “Ver más”

- Fecha y hora: 2026-10-28 17:46:20 (America/Mexico_City)
- Tipo: Corrección y mejora de búsqueda
- Estado: Completado el 2026-10-28 17:48:43 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Solicitud:
  - Evitar paneles y ventanas duplicadas.
  - Expandir texto contraído de publicaciones antes de descartar palabras clave.
- Cambio propuesto:
  - Bloqueo de instancia única en Windows.
  - Mantener una sola ventana scrcpy por serie dentro del panel activo.
  - Opción configurable para expandir textos cuyo control visible sea exactamente `Ver más` o `See more`.
  - Límite de expansiones por pantalla y espera configurable.
  - Volver a leer la jerarquía de accesibilidad después de cada expansión.
- Exclusiones intencionales:
  - No pulsar `Ver más comentarios`, `Ver respuestas` o coincidencias parciales.
  - No reaccionar, comentar, compartir ni publicar.
  - No realizar expansiones indefinidas.
- Archivos modificados: `panel.py`, `LEEME.txt` y `BITACORA.md`.
- Referencia de rollback: Commit anterior `277edcf`.
- Implementación:
  - Se agregó un mutex con nombre en Windows para impedir que dos paneles administren los mismos celulares simultáneamente.
  - Se agregó una casilla para habilitar o deshabilitar la expansión, un máximo de 1 a 10 expansiones por pantalla y una espera de 0.2 a 5 segundos.
  - La búsqueda obtiene una nueva jerarquía accesible después de cada toque y vuelve a analizar el texto antes de hacer scroll.
  - El resultado informa cuántas expansiones se hicieron y conserva los límites de scroll existentes.
- Pruebas realizadas:
  - Validación de sintaxis mediante AST y revisión de `git diff --check`.
  - Jerarquía XML simulada con `Ver más`, `See more`, `Ver más comentarios`, `Ver respuestas` y un control invisible; sólo se aceptaron los dos controles exactos y visibles.
  - Ciclo simulado de búsqueda: la palabra oculta se detectó después de una expansión y no se ejecutó scroll adicional.
  - Comprobación del mutex: la primera adquisición fue aceptada y la segunda fue rechazada.
  - Creación real de la interfaz y validación de los valores iniciales de los nuevos controles.
  - Lectura no invasiva de la jerarquía del teléfono autorizado `ZE222HSLC9`; se detectaron cero controles exactos en la pantalla actual y no se enviaron toques.
- Resultado: Correcto. La búsqueda puede revelar texto contraído con límites configurables y una segunda copia del panel queda bloqueada.
- Limitación verificada: La prueba física de expansión requiere que Facebook muestre una publicación con un control accesible etiquetado exactamente `Ver más`; no estaba presente en la pantalla durante esta sesión.
- Hash resultante de `panel.py`: `7D294E97BA0D2FFBEBC1FF862E732CDB6CC7C27C5A6515D84F671191737FC9B2`.
- Hash resultante de `LEEME.txt`: `99664D4F648D0B8A6617EA9F85F992944435B0D98AB4B4983F39454763861886`.
- Commit resultante: El commit Git local que contiene esta entrada.
- Rollback: `git revert` sobre el commit resultante o restaurar `277edcf`.

### CHG-20261028-1738 — Ocultar consolas de procesos ADB

- Fecha y hora: 2026-10-28 17:38:07 (America/Mexico_City)
- Tipo: Corrección de experiencia de uso
- Estado: Completado el 2026-10-28 17:38:47 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Problema: Durante el uso del panel aparecen varias ventanas negras de consola al ejecutar ADB y otras herramientas auxiliares.
- Causa: El panel se ejecuta con `pythonw.exe`, pero las llamadas a programas de consola no solicitan explícitamente el modo sin ventana de Windows.
- Cambio propuesto: Aplicar `CREATE_NO_WINDOW` a todos los procesos ADB y scrcpy iniciados por el panel.
- Alcance: Sólo presentación de procesos; no cambia comandos, tareas ni comportamiento de los celulares.
- Archivos modificados: `panel.py` y `BITACORA.md`.
- Referencia de rollback: Commit anterior `b938492`.
- Implementación: Se definió una bandera común `NO_WINDOW` y se aplicó a las seis llamadas `subprocess.run` o `subprocess.Popen` utilizadas para ADB y scrcpy.
- Pruebas realizadas:
  - Validación de sintaxis mediante AST.
  - Inspección automática para confirmar que todas las llamadas a subprocesos incluyen `creationflags`.
  - Cinco escaneos consecutivos del dispositivo desde una instancia de Tkinter.
  - Comprobación de procesos de consola después de la prueba; no quedaron nuevas ventanas o procesos persistentes.
- Resultado: Correcto. Los procesos auxiliares se ejecutan sin crear ventanas de consola visibles.
- Hash resultante de `panel.py`: `0A071EBB100DFC1C7FA4D50A562CC36FBBA14350CFABB911CC36F1094F92353B`.
- Commit resultante: El commit Git local que contiene esta entrada.
- Rollback: `git revert` sobre el commit resultante o restaurar `b938492`.

### CHG-20261028-1125 — Administración simultánea de varios teléfonos

- Fecha y hora: 2026-10-28 11:25:42 (America/Mexico_City)
- Tipo: Funcionalidad y arquitectura
- Estado: Completado el 2026-10-28 11:29:32 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Solicitud: Administrar varios teléfonos simultáneamente, verlos y asignar procesos o tareas diferentes.
- Objetivo:
  - Mostrar los dispositivos en una tabla con selección múltiple.
  - Conservar nombres personalizados por número de serie.
  - Ejecutar acciones únicamente sobre los equipos seleccionados.
  - Abrir y cerrar pantallas independientes mediante scrcpy.
  - Mostrar la tarea actual de cada dispositivo.
  - Permitir seleccionar distintos grupos y asignar tareas diferentes de manera simultánea.
- Archivos modificados: `panel.py`, `LEEME.txt`, `.gitignore` y `BITACORA.md`.
- Datos locales previstos: `dispositivos.json`, excluido de Git por contener nombres definidos por el operador.
- Autoría y compatibilidad: Se preservarán las funciones existentes y se agregarán controles alrededor de ellas; no se reclamará autoría sobre el código original.
- Riesgos:
  - Una desconexión durante una tarea debe afectar sólo al dispositivo correspondiente.
  - Varias ventanas scrcpy pueden consumir memoria y procesador.
  - La selección debe conservarse al actualizar sin ejecutar acciones sobre equipos no elegidos.
- Referencia de rollback: Commit anterior `1370416`.
- Implementación:
  - Tabla multi-selección con nombre, modelo, serie, Android, conexión y tarea actual.
  - Selección de todos, limpieza de selección y nombres persistentes por serie.
  - Todas las acciones generales, búsqueda y visión limitadas a los equipos seleccionados.
  - Ejecución independiente por dispositivo mediante hilos de trabajo.
  - Apertura de scrcpy por equipo, organización automática en cuadrícula y cierre desde el panel.
  - Restauración del estado de tarea cuando termina una operación.
  - Cierre controlado de las ventanas scrcpy al salir.
  - Exclusión de `dispositivos.json` del repositorio local.
- Pruebas realizadas:
  - Sintaxis e importación de `panel.py`.
  - Validación de todas las opciones scrcpy utilizadas.
  - Carga real del Moto E6 Play con modelo, Android 9 y estado conectado.
  - Selección inicial y lectura de filas en la tabla.
  - Simulación de dos dispositivos con tareas independientes y concurrentes.
  - Persistencia aislada de nombres en JSON.
  - Apertura real de scrcpy para `ZE222HSLC9`, comprobación del proceso y cierre controlado.
  - Arranque del panel actualizado y comprobación de proceso responsivo.
- Resultado: Correcto para las pruebas disponibles.
- Limitación de validación: Sólo había un teléfono físico conectado. La coordinación de dos teléfonos se validó con dispositivos simulados; debe repetirse una prueba física cuando haya dos o más equipos disponibles.
- Hashes resultantes:
  - `panel.py`: `F0AAAC19E75B03131158CB7CFF8787D41D5F512E1FA8CE9AE787A4A4CC7AEAB1`
  - `LEEME.txt`: `EB26F395A003C8AB809C445081FCFCFA4DD981E9C4405B33D1954B942B8C958C`
  - `.gitignore`: `2506FE8D9306FE0430FDDDC9C8D07C9656A492A4FC2AD4CBD18934C21A89264A`
- Commit resultante: El commit Git local que contiene esta entrada.
- Rollback: `git revert` sobre el commit resultante o restaurar el commit anterior `1370416`.
- Observaciones: Se preservaron el título, las funciones existentes y la autoría del proyecto original.

### CHG-20261028-0620 — Optimización de velocidad del scroll

- Fecha y hora: 2026-10-28 06:20:31 (America/Mexico_City)
- Tipo: Optimización
- Estado: Completado el 2026-10-28 06:23:40 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Solicitud: Reducir el tiempo entre desplazamientos durante la búsqueda por palabras.
- Diagnóstico inicial:
  - Lectura normal de accesibilidad y descarga: aproximadamente 1.29 segundos en el Moto E6 Play.
  - El intervalo predeterminado agrega actualmente 4 segundos después de cada análisis.
  - El tamaño de pantalla se consulta nuevamente en cada desplazamiento.
  - El modo comprimido de `uiautomator` resultó más lento en este dispositivo y no se utilizará.
- Cambio propuesto:
  - Reducir el intervalo predeterminado.
  - Permitir intervalos decimales seguros.
  - Interpretar el intervalo como duración mínima total del ciclo, evitando sumar esperas innecesarias al tiempo del análisis.
  - Obtener y reutilizar las coordenadas de scroll por dispositivo.
- Archivos modificados: `panel.py`, `LEEME.txt` y `BITACORA.md`.
- Referencia de rollback: Commit anterior `7d9ab44`.
- Límites preservados: máximo de desplazamientos, cancelación y análisis de cada pantalla.
- Pruebas realizadas:
  - Comparación de lectura normal, comprimida y salida directa de `uiautomator`.
  - Prueba real de dos desplazamientos en el Moto E6 Play `ZE222HSLC9`.
  - Verificación de caché del tamaño de pantalla.
  - Comprobación de sintaxis y diferencias Git.
- Resultado:
  - Intervalo predeterminado reducido de 4 a 1 segundo.
  - Intervalos decimales aceptados desde 0.5 segundos.
  - La espera ahora completa sólo el tiempo restante del ciclo y no se suma íntegramente al análisis.
  - El tamaño de pantalla se consulta una vez por búsqueda y se reutiliza.
  - El modo comprimido no se adoptó porque fue más lento en el dispositivo probado.
  - Dos desplazamientos con análisis completo tardaron 14.33 segundos. Bajo las mismas condiciones, el comportamiento anterior habría añadido 8 segundos de espera, para un estimado de 22.33 segundos; la reducción estimada es de aproximadamente 36 %.
- Limitación: La lectura de accesibilidad de Android sigue siendo el principal cuello de botella y puede variar según la pantalla de Facebook.
- Hashes resultantes:
  - `panel.py`: `95D1D7C0D4CAD4259AA44B7EC132684CE68BE089C3597D6C0E5B8B997FAC0DC5`
  - `LEEME.txt`: `838E62172DE0C1622EB352AB36D03625D328D832C36226E269155C5DC29CBC67`
- Commit resultante: El commit Git local que contiene esta entrada.

### CHG-20261027-2204 — Búsqueda asistida por palabras clave

- Fecha y hora: 2026-10-27 22:04:56 (America/Mexico_City)
- Tipo: Funcionalidad y optimización
- Estado: Completado el 2026-10-28 06:06:51 (America/Mexico_City)
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
- Referencia previa de rollback: Línea base `BASE-20261027-2158`, commit Git local `ad09ce2`.
- Archivos modificados:
  - `panel.py`: nueva pestaña, búsqueda limitada, lectura accesible, scroll proporcional, cancelación, captura de enlace y cola segura para actualizar Tkinter.
  - `LEEME.txt`: instrucciones, alcance y limitaciones del modo de búsqueda.
  - `BITACORA.md`: cierre y resultados de este cambio.
- Pruebas realizadas:
  - Análisis de sintaxis e importación de `panel.py`.
  - Comprobación de OpenCV.
  - Creación de la interfaz Tkinter en memoria y verificación de sus tres pestañas.
  - Prueba simulada de coincidencia inmediata, límite de desplazamientos y normalización de acentos.
  - Lectura real mediante ADB y `uiautomator` en el Moto E6 Play `ZE222HSLC9`.
  - Prueba real de coincidencia sobre texto visible y detención antes del siguiente scroll.
  - Ejecución real de un desplazamiento ADB controlado.
  - Prueba aislada de validación y captura de un enlace de Facebook.
  - Arranque visual del panel actualizado y comprobación de proceso responsivo.
- Resultado de las pruebas: Correcto. Se detectó y corrigió durante la validación un problema de codificación de caracteres provenientes de ADB; la lectura interna conserva Unicode y la búsqueda ignora diferencias de acentos y mayúsculas.
- Limitaciones pendientes:
  - Falta validar la detección dentro de una publicación real de Facebook, porque la aplicación puede ocultar parte del texto a la accesibilidad de Android.
  - La captura real del enlace requiere que el operador use `Compartir > Copiar enlace`; no se probó con una cuenta de Facebook durante este cambio.
  - La búsqueda no usa OCR; sólo analiza texto expuesto por Android.
- Hashes resultantes:
  - `panel.py`: `39F377041A4C60A5486A29F16E693829A9A73D500856CB6538F9F3ED549A492E`
  - `LEEME.txt`: `E1F49B6F1C369600F4F91974A6093A8118D383BE596E901E46B2833E17BB47F9`
- Commit resultante: El commit Git local que contiene esta entrada y los archivos modificados.
- Publicado o respaldado: Respaldado en Git local; no se configuró ni utilizó un repositorio remoto.
- Procedimiento de rollback: Restaurar `panel.py` y `LEEME.txt` desde el commit local de línea base.
- Observaciones: La entrada se creó antes de modificar el código funcional. Se conservaron la autoría, estructura y funciones originales; la nueva capacidad se agregó como una pestaña independiente.

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

