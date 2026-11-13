# Bitácora de cambios — Administración de móviles (移动设备管理)

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

- Ninguno.

## Cambios completados

### CHG-20261113-0046 — Acción garantizada sobre el vínculo capturado

- Fecha y hora de inicio: 2026-11-13 00:46:12 (America/Mexico_City)
- Estado: Completado y validado en el teléfono real el 2026-11-13 00:53:46 (America/Mexico_City)
- Tipo: Corrección y prueba funcional controlada
- Solicitud: Probar Búsqueda con `artemio`; después de obtener el vínculo, abrir exactamente ese vínculo, realizar Me gusta según la configuración y regresar al feed.
- Diagnóstico en ejecución 1.88.8: Android abrió Ajustes a las 00:05:57 y la búsqueda de Ajustes a las 00:06:03, pero no hubo un `VIEW` posterior hacia Facebook ni se creó el CSV del día. La lectura del texto pegado devolvió una URL vacía y el proceso regresó al feed para continuar el scroll.
- Alcance: respaldo OCR para leer la URL pegada, apertura obligatoria de la URL válida antes de acciones, validación del post abierto, ejecución de Me gusta y retorno al feed.
- Riesgo controlado: una URL inválida no habilita acciones; se realizó un único Me gusta real sobre la publicación coincidente solicitada por el usuario.
- Referencia de rollback: commit `6d8e2ba` de la rama `integracion`.
- Implementación:
  - Añade lectura OCR del campo de búsqueda de Ajustes cuando UIAutomator no expone el vínculo pegado.
  - Observa el campo hasta tres veces sin volver a pegar, evitando concatenar o corromper la URL.
  - Toda URL válida se abre obligatoriamente mediante `android.intent.action.VIEW` antes de Me gusta/Comentario; el regreso por encabezado queda como respaldo si la apertura falla.
  - Confirma una publicación limpia antes de entregar la vista a las acciones seleccionadas.
  - Me gusta revisa directamente la proporción de azul dentro del contenedor izquierdo antes y después del toque, además de las verificaciones por plantilla y accesibilidad.
- Prueba funcional real:
  - Coincidencia encontrada: `Artemio Hernández Garrido`, encabezado `Claudia Medrano · 21 min`.
  - Vínculo capturado y guardado: `https://www.facebook.com/share/p/1RMnh6ADwy/` en `registros_busqueda/enlaces_2026-11-13.csv`.
  - El mismo vínculo se abrió explícitamente y Facebook confirmó la publicación.
  - La fila completa Me gusta/Comentar/Compartir fue localizada después de dos desplazamientos seguros.
  - Me gusta fue pulsado una vez; una reapertura de verificación mostró el pulgar azul y contador `1`.
  - El detector actualizado reconoció correctamente el azul en la captura real.
  - El regreso al feed fue confirmado y la publicación original volvió a quedar visible.
  - No se publicó ningún comentario.
- Pruebas adicionales: URL OCR reconstruida, `VIEW` obligatorio, rechazo de URL inválida, compilación de `panel.py` y `license_guard.py`, `git diff --check`, hash y construcción PyInstaller correctos.
- Archivos modificados: `panel.py`, `LEEME.txt`, `Construir Ejecutable.ps1` y `BITACORA.md`.
- Entrega: `release_1.88.9/AdministracionDeMoviles.exe` (87,080,186 bytes) y `SHA256.txt`.
- SHA-256: `3E7AAC3EC74169005FE7DA6C4F28FC02D5008517AC0CE74F027896518370D5ED`.
- Commit resultante: el commit de la rama `integracion` que contiene esta entrada.
- Publicado o respaldado: Sí; cambio funcional publicado en la rama `integracion` de GitHub mediante el commit `c4cbd62`.
- Procedimiento de rollback: revertir el commit resultante o restaurar `6d8e2ba` en una rama de recuperación.

### CHG-20261112-2103 — Acciones sobre el enlace recuperado desde el feed

- Fecha y hora de inicio: 2026-11-12 21:03:26 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 23:34:20 (America/Mexico_City)
- Tipo: Corrección del flujo posterior a la captura del enlace
- Solicitud: Si el regreso no encuentra la publicación original y llega al feed, abrir el enlace obtenido y ejecutar sobre esa publicación Me gusta y/o Comentario según la configuración.
- Diagnóstico: el enlace ya se reabría como último recurso, pero la comprobación posterior volvía a exigir el encabezado anterior y podía retroceder de nuevo aunque la URL exacta hubiera abierto la publicación correcta.
- Alcance: conservar por dispositivo el resultado del retorno, aceptar como identidad fuerte la URL copiada después de abrirla explícitamente, confirmar una publicación limpia y entregar ese estado al ejecutor de acciones.
- Riesgo controlado: no ejecutar acciones si la URL no es válida o Facebook no confirma una publicación abierta; conservar el botón Detener y las selecciones actuales.
- Referencia de rollback: commit `811d04c` de la rama `integracion`.
- Implementación:
  - Añade un estado de recuperación independiente para cada teléfono conectado.
  - Si el regreso encuentra el encabezado original, conserva la validación estricta anterior.
  - Si llega al feed o agota los regresos, abre explícitamente la URL capturada mediante Facebook.
  - Después de abrir esa URL, la dirección exacta funciona como identidad fuerte y sólo se exige una publicación limpia, sin capas ni `<` inferiores.
  - El trabajador recibe el resultado de recuperación y evita retroceder otra vez; Me gusta y/o Comentario se ejecutan sobre la publicación abierta desde el enlace según las casillas seleccionadas.
- Pruebas realizadas:
  - Caso simulado feed → URL válida → publicación limpia: abrió exactamente la URL, confirmó el estado `ready/via_url` y la entregó como destino de acciones.
  - Caso negativo con URL ajena a Facebook: no ejecutó `android.intent.action.VIEW` y no habilitó acciones.
  - Compilación de `panel.py` y `license_guard.py`, `git diff --check`, verificación de hash y construcción PyInstaller: correctos.
  - No se ejecutaron Me gusta ni Comentario durante las pruebas.
- Archivos modificados: `panel.py`, `LEEME.txt`, `Construir Ejecutable.ps1` y `BITACORA.md`.
- Entrega: `release_1.88.8/AdministracionDeMoviles.exe` (87,079,555 bytes) y `SHA256.txt`.
- SHA-256: `6AC8A13EA8BD8E3B174AE036A5F1944E78C70F3BE7C5F14E84B865E94E359CE0`.
- Commit resultante: el commit de la rama `integracion` que contiene esta entrada.
- Publicado o respaldado: Sí; cambio funcional publicado en la rama `integracion` de GitHub mediante el commit `e3c04c1`.
- Procedimiento de rollback: revertir el commit resultante o restaurar `811d04c` en una rama de recuperación.

### CHG-20261112-2030 — Recuperación de la publicación original por encabezado

- Fecha y hora de inicio: 2026-11-12 20:30:27 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 20:38:00 (America/Mexico_City)
- Tipo: Corrección de navegación posterior a la captura del enlace
- Solicitud: Después de obtener el enlace, ejecutar Atrás y comparar cada pantalla hasta regresar a la publicación original identificada por su encabezado; sólo entonces iniciar el scroll que localiza Me gusta.
- Diagnóstico: confirmar únicamente que existe una vista de publicación no distingue la publicación original de capas o publicaciones anidadas que conservan elementos similares.
- Alcance: guardar una referencia del encabezado y contenido antes de abrir los menús, validar esa identidad durante cada regreso, limitar los retrocesos, reabrir el enlace como recuperación y bloquear el scroll/Me gusta mientras no coincida la publicación.
- Riesgo controlado: evitar retroceder más allá del feed o actuar en otra publicación; no se tocó Me gusta durante las pruebas locales.
- Referencia de rollback: commit `a3ca34d` de la rama `integracion`.
- Implementación:
  - Extrae el nombre estable del encabezado situado antes de la fecha/hora y admite que nombre y fecha vengan en nodos separados.
  - Conserva esa referencia junto con las palabras coincidentes y la fecha de la publicación antes de abrir menús o Ajustes.
  - Tras obtener el enlace, compara hasta diez pantallas: una publicación con encabezado distinto provoca otro Atrás; un `<` inferior se resuelve primero; llegar al feed activa la reapertura segura mediante el enlace capturado.
  - La publicación sólo queda lista cuando coincide el encabezado original, no existe un `<` inferior y se confirma la estructura de publicación abierta.
  - El primer scroll hacia la fila Me gusta/Comentar/Compartir vuelve a validar la misma referencia. En una ejecución combinada, la validación se hace antes del primer scroll para no exigir que el encabezado siga visible después de desplazarse.
- Pruebas realizadas:
  - Caso simulado con una publicación `Canal 19` seguida de `Farmacia Monte de Yavé`: ejecutó exactamente un Atrás y sólo aceptó la segunda al coincidir el encabezado.
  - Captura real del teléfono conectado: la publicación exterior `Informativo Alcance · 1 h` fue distinguida de la publicación compartida `Alcance Informativo`; la referencia resultante fue `informativo alcance` y coincidió con la pantalla original.
  - Compilación de `panel.py` y `license_guard.py`, `git diff --check`, comparación de hash y construcción PyInstaller: correctos.
  - No se ejecutaron Me gusta ni Comentario durante las pruebas.
- Archivos modificados: `panel.py`, `LEEME.txt`, `Construir Ejecutable.ps1` y `BITACORA.md`.
- Entrega: `release_1.88.7/AdministracionDeMoviles.exe` (87,079,045 bytes) y `SHA256.txt`.
- SHA-256: `64E7128D2AEBC470D925BDB229EFDCA0A481E42052E12658B0C70A8304AA4175`.
- Commit resultante: el commit de la rama `integracion` que contiene esta entrada.
- Publicado o respaldado: Sí; cambio funcional publicado en la rama `integracion` de GitHub mediante el commit `b53f5c8`.
- Procedimiento de rollback: revertir el commit resultante o restaurar `a3ca34d` en una rama de recuperación.

### CHG-20261112-2015 — Validación del regreso intermedio antes del scroll de acciones

- Fecha y hora de inicio: 2026-11-12 20:15:39 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 20:20:08 (America/Mexico_City)
- Tipo: Corrección de navegación posterior a la captura del enlace
- Solicitud: Después del mensaje `Publicación original recuperada después de obtener el enlace`, comprobar que no exista un `<` lateral en la parte media o inferior; su presencia indica que aún falta regresar un nivel antes de desplazar para buscar Me gusta.
- Diagnóstico: `return_from_settings_to_post` confirma primero el diseño de publicación y sólo después busca un control intermedio. Una capa puede conservar visibles el editor o el contenido subyacentes, haciendo que la publicación parezca recuperada aunque todavía muestre otro `<` lateral.
- Alcance: verificación visual del chevrón lateral, prioridad del regreso intermedio sobre la confirmación de publicación, confirmación limpia antes de acciones, documentación, pruebas y ejecutable.
- Riesgo controlado: no confundir avatares, tarjetas o controles del feed con un `<`; se conservará la detección previa del feed y los candidatos geométricos deberán tener forma visual de chevrón izquierdo.
- Referencia de rollback: commit `49e9ab2` de la rama `integracion`.
- Implementación:
  - Añade reconocimiento visual del `<` mediante dos diagonales de pendientes opuestas que convergen en un vértice izquierdo.
  - Exige un fondo mayormente claro para candidatos geométricos; así descarta fotografías y avatares con diagonales accidentales.
  - En el retorno desde Ajustes, detecta primero el feed y después cualquier `<` inferior verificado. La publicación sólo se acepta cuando ambas comprobaciones son negativas y su diseño sigue confirmado.
  - Si aparece el `<` inferior, lo pulsa una sola vez, espera y vuelve a inspeccionar desde cero antes de emitir el mensaje de recuperación.
  - Añade `confirm_actionable_open_post`, usada después de reabrir el enlace, antes de ejecutar acciones y al inicio del método de scroll.
  - El scroll hacia Me gusta/Comentar/Compartir queda bloqueado mientras la publicación limpia no esté confirmada.
- Pruebas realizadas:
  - Flecha superior real de publicación reconocida como chevrón; al estar fuera de la zona inferior no se trató como capa intermedia.
  - Avatar real del feed en `(16,806)-(120,910)` rechazado por su densidad visual; el feed se confirmó y no recibió toques.
  - Capa simulada con editor y contenido subyacentes más un `<` en `(50,700)`: fue rechazada como lista, recibió un único toque de regreso y después confirmó la publicación limpia.
  - Prueba del guardián de scroll: con capa intermedia activa no ejecutó ningún gesto.
  - Compilación de `panel.py` y `license_guard.py`, `git diff --check`, verificación de hash y constructor PyInstaller: correctos.
  - No se ejecutaron Me gusta ni Comentario durante las pruebas.
- Archivos modificados: `panel.py`, `LEEME.txt`, `Construir Ejecutable.ps1` y `BITACORA.md`.
- Entrega: `release_1.88.6/AdministracionDeMoviles.exe` (87,075,134 bytes) y `SHA256.txt`.
- SHA-256: `7A3E7A832F748AAEB47B59889D5196B6AD7FB87D797F30F0BFCF30C30F0BF5AD`.
- Commit resultante: el commit de la rama `integracion` que contiene esta entrada.
- Publicado o respaldado: Sí; cambio funcional publicado en la rama `integracion` de GitHub mediante el commit `077a014`.
- Procedimiento de rollback: revertir el commit resultante o restaurar `49e9ab2` en una rama de recuperación.

### CHG-20261112-2006 — Coincidencia OCR con fecha integrada en encabezado ancho

- Fecha y hora de inicio: 2026-11-12 20:06:47 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 20:08:41 (America/Mexico_City)
- Tipo: Corrección del detector de coincidencias
- Solicitud: Revisar por qué la publicación visible que contiene la frase completa `farmacia monte` no fue identificada por Búsqueda.
- Diagnóstico real:
  - OCR leyó `¡OFERTA ESPECIAL EN FARMACIA` y `MONTE DE YAVÉ!` en dos líneas consecutivas, además de una segunda aparición `Exclusivamente en Farmacia Monte de`.
  - La publicación no contiene `Publicidad`, `Patrocinado` ni otra etiqueta publicitaria.
  - OCR leyó la fecha dentro del encabezado `Informativo Alcance · 1 h ·` con límites `(136,867)-(482,891)`.
  - El ancho fue `346 px`; el límite vigente era `48 %` de `720 px`, equivalente a `345.6 px`. La diferencia de `0.4 px` descartó la fecha y dejó la coincidencia sin publicación asociada.
- Alcance: aceptar encabezados OCR más anchos únicamente cuando sus palabras contienen una fecha/hora verificable, pulsar sólo el segmento temporal, pruebas con la captura real, documentación y ejecutable.
- Riesgo controlado: no convertir cualquier línea ancha con números en fecha; se exigirá una combinación explícita como `1` + `h`, `48` + `min` o una unidad compacta válida.
- Referencia de rollback: commit `d39d8c7` de la rama `integracion`.
- Implementación:
  - Extrae en una función independiente el centro exacto de palabras temporales como `1` + `h`, `48` + `min` o `9h`.
  - Amplía hasta `76 %` el ancho permitido de una línea OCR con fecha integrada, en coherencia con el detector geométrico de encabezados.
  - Cuando la línea supera el límite histórico de `48 %`, sólo se acepta si existe geometría OCR de palabras que permita pulsar exclusivamente la fecha/hora.
  - `post_timestamp_click_point` reutiliza la misma geometría verificada; sin palabras temporales conserva su comportamiento seguro anterior.
- Pruebas realizadas:
  - Captura real de `720×1520`: `farmacia monte` fue reconocida como frase completa en dos líneas y también en una segunda aparición.
  - La publicación fue asociada con `Informativo Alcance · 1 h ·`; el punto temporal calculado fue `(408,878)`.
  - La publicación real no fue clasificada como publicidad.
  - Caso negativo: un encabezado ancho con texto `1 h` pero sin límites OCR de palabras fue rechazado.
  - Compilación de `panel.py` y `license_guard.py`, `git diff --check`, verificación de hash y constructor PyInstaller: correctos.
  - No se abrió la publicación ni se ejecutaron Me gusta o Comentario durante las pruebas.
- Archivos modificados: `panel.py`, `LEEME.txt`, `Construir Ejecutable.ps1` y `BITACORA.md`.
- Entrega: `release_1.88.5/AdministracionDeMoviles.exe` (87,074,479 bytes) y `SHA256.txt`.
- SHA-256: `8D88B760839C819DA88FD73FCB5B4ADEA6F38E8BB884EE99B8F352F5C9D3924F`.
- Commit resultante: el commit de la rama `integracion` que contiene esta entrada.
- Publicado o respaldado: Sí; cambio funcional publicado en la rama `integracion` de GitHub mediante el commit `7972b45`.
- Procedimiento de rollback: revertir el commit resultante o restaurar `d39d8c7` en una rama de recuperación.

### CHG-20261112-1956 — Acciones validadas por la fila completa de la publicación

- Fecha y hora de inicio: 2026-11-12 19:56:14 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 20:00:19 (America/Mexico_City)
- Tipo: Corrección de interacción y navegación
- Solicitud: En la publicación coincidente con `huauchinango`, desplazar hasta encontrar la fila completa Me gusta, Comentar y Compartir; usarla como confirmación antes de dar Me gusta y revisar que Comentario se abra y se ejecute correctamente.
- Diagnóstico real:
  - La publicación individual contiene una republicación anidada, una imagen larga, una bandeja fija de stickers y el editor inferior.
  - El gesto anterior comenzaba en `82 %` de la altura y podía caer sobre la zona fija de stickers/editor.
  - Accesibilidad no publica los textos de las acciones, pero sí expone tres contenedores clicables consecutivos: `[0,884][240,964]`, `[240,884][480,964]` y `[480,884][720,964]`.
  - En la captura real, los detectores visuales localizaron Me gusta en `(105,926)` con puntuación `0.9630` y Comentar en `(355,926)` con puntuación `1.0`; ambos estaban alineados con Compartir.
- Alcance: detector estructural de la fila de tres acciones, scroll desde una zona central segura, toque restringido al contenedor validado, confirmación visual de Me gusta, apertura validada del comentario, documentación, pruebas y ejecutable.
- Riesgo controlado: no usar una manita aislada o un control de comentario dentro de otra publicación; se exigirá la fila completa, contigua y alineada.
- Referencia de rollback: commit `ba90a25` de la rama `integracion`.
- Implementación:
  - Añade un detector estructural que exige tres contenedores clicables consecutivos, alineados, con un icono hijo en cada uno y cobertura completa del ancho de la publicación.
  - Devuelve los centros seguros de izquierda, centro y derecha como Me gusta, Comentar y Compartir; en la publicación real fueron `(120,924)`, `(360,924)` y `(600,924)`.
  - Combina la estructura con las figuras visuales: Me gusta real en `(105,926)` y Comentar en `(355,926)`.
  - El scroll comienza en `71 %` de la altura y termina en `26 %`, por encima de la bandeja fija de stickers y del editor; revisa la pantalla después de cada gesto hasta 18 veces.
  - Me gusta sólo pulsa la figura izquierda dentro de la fila confirmada y verifica después el estado azul o la señal accesible de `Quitar Me gusta`.
  - Comentario sólo comienza después de confirmar la misma fila: pulsa el centro, localiza el editor inferior, lo limpia, escribe, verifica el texto, envía y conserva la validación posterior contra duplicados.
  - La validación de un comentario publicado ahora prefiere la fila estructural completa; como respaldo acepta Me gusta y Comentar visualmente alineados.
- Pruebas realizadas:
  - Publicación real abierta mediante su fecha `48 min`; publicación individual y editor inferior confirmados.
  - Dos desplazamientos manuales desde la zona segura bastaron para alcanzar la fila real sin tocar stickers ni editor.
  - Detector real: límites `[0,884][240,964]`, `[240,884][480,964]` y `[480,884][720,964]`; centros correctos para las tres acciones.
  - Me gusta simulado: efectuó un único toque en `(105,926)` y sólo devolvió `confirmed` después de recibir el estado visual activo.
  - Comentario simulado: secuencia exacta `(355,926)` → editor `(360,1410)` → envío `(680,1400)`; escritura y confirmación final correctas.
  - Un feed con seis pestañas fue rechazado como fila de acciones.
  - Compilación de `panel.py` y `license_guard.py`, `git diff --check`, verificación de hash y constructor PyInstaller: correctos.
  - No se dio Me gusta ni se publicó ningún comentario durante las pruebas; la publicación quedó abierta mostrando la fila para revisión del operador.
- Archivos modificados: `panel.py`, `LEEME.txt`, `Construir Ejecutable.ps1` y `BITACORA.md`.
- Entrega: `release_1.88.4/AdministracionDeMoviles.exe` (87,072,965 bytes) y `SHA256.txt`.
- SHA-256: `60349190E479CD0934C55267A0BC8DA0F6CA0BBFEB2645C18B98DDD8EAEB0276`.
- Commit resultante: el commit de la rama `integracion` que contiene esta entrada.
- Publicado o respaldado: Sí; cambio funcional publicado en la rama `integracion` de GitHub mediante el commit `ddade39`.
- Procedimiento de rollback: revertir el commit resultante o restaurar `ba90a25` en una rama de recuperación.

### CHG-20261112-1931 — Recuperación posterior al enlace y scroll largo para Me gusta

- Fecha y hora de inicio: 2026-11-12 19:31:34 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 19:36:51 (America/Mexico_City)
- Tipo: Corrección de navegación y búsqueda visual
- Solicitud: Con `Me gusta` y `Guardar enlace` seleccionados, obtener el enlace, regresar desde la pantalla intermedia marcada con `<`, recuperar la publicación original, desplazar una publicación larga hasta encontrar Me gusta y finalmente volver al feed para continuar la búsqueda.
- Diagnóstico inicial: la lectura del portapapeles abre Ajustes y el retorno actual ejecuta dos Atrás fijos al recuperar Facebook; esa cantidad no representa todos los estados posibles y puede dejar una pantalla intermedia o sobrepasar la publicación. La búsqueda de Me gusta ya desplaza, pero está limitada a ocho gestos sin registrar ni validar la recuperación previa.
- Alcance: retorno guiado por estado, identificación del `<` intermedio, reapertura segura mediante el enlace recién obtenido cuando sea necesario, scroll progresivo para Me gusta, documentación, pruebas y ejecutable.
- Riesgo controlado: no pulsar controles laterales del feed como si fueran Atrás; antes de tocar se distinguirán publicación, pantalla intermedia y feed.
- Referencia de rollback: commit `1ce2e1b` de la rama `integracion`.
- Implementación:
  - Sustituye los dos Atrás fijos posteriores a Ajustes por una inspección de hasta seis transiciones.
  - Distingue publicación abierta, feed y pantalla intermedia. El feed se reconoce por su fila de pestañas para no confundir tarjetas laterales con el control de regreso.
  - En una pantalla intermedia localiza `<`, `Atrás`, `Volver`, `Back` o su botón geométrico lateral y retrocede exactamente un paso antes de volver a inspeccionar.
  - Si el retorno sobrepasa la publicación y llega al feed, reabre la URL que acaba de copiar y confirma la publicación antes de ejecutar acciones.
  - El trabajador de Búsqueda repite esta recuperación si la primera comprobación posterior al enlace no confirma la publicación; si aun así falla, omite las acciones para no tocar otra pantalla.
  - Me gusta se busca en la pantalla inicial y después de hasta 18 desplazamientos amplios, deteniéndose inmediatamente al localizar el control accesible o la figura validada.
- Pruebas realizadas:
  - Pantalla intermedia simulada: detectó el botón lateral en `(50,700)`, ejecutó un solo toque y confirmó después la publicación.
  - Feed simulado: no tocó sus controles y reabrió la URL mediante Facebook Lite; la publicación fue confirmada.
  - Publicación larga simulada: realizó tres desplazamientos y se detuvo al encontrar Me gusta en el cuarto análisis.
  - Pantalla real actual de `720×1520`: reconoció correctamente el feed; aunque existía un falso candidato geométrico en `(68,859)`, quedó bloqueado por la confirmación previa del feed y no se tocó.
  - Compilación de `panel.py` y `license_guard.py`, `git diff --check`, verificación de hash y constructor PyInstaller: correctos.
  - No se dio Me gusta, no se escribió ni se publicó ningún comentario durante las pruebas.
- Archivos modificados: `panel.py`, `LEEME.txt`, `Construir Ejecutable.ps1` y `BITACORA.md`.
- Entrega: `release_1.88.3/AdministracionDeMoviles.exe` (87,069,287 bytes) y `SHA256.txt`.
- SHA-256: `F25F9C32FF84AF447DB2E863B015B3E95F2800404145365A16C2D08095EC09D9`.
- Commit resultante: el commit de la rama `integracion` que contiene esta entrada.
- Publicado o respaldado: Sí; cambio funcional publicado en la rama `integracion` de GitHub mediante el commit `8e9c7ee`.
- Procedimiento de rollback: revertir el commit resultante o restaurar `1ce2e1b` en una rama de recuperación.

### CHG-20261112-1835 — Regreso visual desde publicación abierta al feed

- Fecha y hora de inicio: 2026-11-12 18:35:10 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 18:39:11 (America/Mexico_City)
- Tipo: Corrección de navegación
- Objetivo: Después de obtener el enlace, comentar o dar Me gusta, identificar el control de regreso `<` de la esquina superior izquierda, salir de la publicación abierta y continuar el scroll principal desde el punto anterior.
- Alcance: detección accesible/geométrica del control Atrás, regreso seguro desde publicaciones simples o anidadas, documentación, constructor y pruebas sin ejecutar reacciones ni publicar comentarios.
- Riesgo controlado: evitar un toque en la esquina superior izquierda cuando el teléfono ya se encuentre en el feed; el control sólo podrá usarse si antes se confirma una vista de publicación abierta.
- Referencia de rollback: commit `2b1fae7` de la rama `integracion`.
- Implementación:
  - Busca rótulos accesibles `Atrás`, `Volver`, `Back`, los glifos `<`, `‹`, `〈`, `←` y la lectura OCR equivalente.
  - Cuando Facebook Lite expone la flecha como un `ViewGroup` sin texto, valida que sea un botón pequeño y clicable pegado al borde superior izquierdo.
  - Una vista sin texto se considera publicación únicamente si combina ese control superior con un editor `EditText` o `MultiAutoCompleteTextView` en la zona inferior.
  - Tras pulsar `<`, vuelve a inspeccionar la pantalla; si continúa dentro de una publicación anidada repite hasta cuatro niveles. Sin control identificable usa Atrás de Android como respaldo.
  - El scroll sólo se habilita después de que la pantalla deje de cumplir las condiciones de una publicación abierta.
- Pruebas realizadas:
  - En la pantalla real de `720×1600`, identificó el botón sin texto con límites `[0,60][96,153]` y centro `(48,106)`.
  - Prueba real de regreso: antes del toque confirmó la publicación; después del toque desapareció el editor y la vista dejó de clasificarse como publicación.
  - El feed mostró otro elemento izquierdo en `(60,204)`, pero fue descartado al no existir editor inferior, por lo que no se efectuó un segundo toque.
  - Prueba simulada del flujo: ejecutó exactamente `tap 48 106`, confirmó el feed y habilitó la continuación.
  - Compilación de `panel.py` y `license_guard.py`, `git diff --check` y constructor PyInstaller: correctos.
  - No se dio Me gusta, no se escribió ni se publicó ningún comentario durante las pruebas.
- Archivos modificados: `panel.py`, `LEEME.txt`, `Construir Ejecutable.ps1` y `BITACORA.md`.
- Entrega: `release_1.88.2/AdministracionDeMoviles.exe` (87,067,301 bytes) y `SHA256.txt`.
- SHA-256: `B21A9EAEA607F2B74DB50A1D14F275E70587A0ADB56DD8108A52F66344A90455`.
- Commit resultante: el commit de la rama `integracion` que contiene esta entrada.
- Publicado o respaldado: Sí; cambio funcional publicado en la rama `integracion` de GitHub mediante el commit `10105f6`.
- Procedimiento de rollback: revertir el commit resultante o restaurar `2b1fae7` en una rama de recuperación.

### CHG-20261112-1528 — Validación desplazada del comentario antes del reintento

- Fecha y hora de inicio: 2026-11-12 15:28:58 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 15:36:11 (America/Mexico_City)
- Tipo: Corrección para evitar comentarios duplicados
- Objetivo: Después del primer envío, pasar visualmente la fila Me gusta/Comentario/Compartir y comprobar el texto del comentario reciente antes de autorizar un reintento.
- Regla de seguridad: nunca se reintenta mientras el comentario esperado aparezca debajo de la fila de acciones; la prueba de desarrollo no publicó otro comentario.
- Alcance: flujo de comentarios en Búsqueda, limpieza del editor, documentación y bitácora.
- Referencia de rollback: commit `8abeebe` de la rama `integracion`.
- Rama Git: `integracion`.
- Diagnóstico real:
  - El primer comentario estaba publicado como reciente debajo de la fila de acciones.
  - La validación se ejecutó antes de desplazar hasta esa zona y comenzó el segundo intento.
  - El segundo intento permanecía únicamente como borrador porque el operador detuvo el proceso antes del envío.
  - Facebook mostraba una corrección ortográfica de un carácter respecto del texto solicitado; la similitud era suficiente para considerarlo el mismo comentario.
- Implementación:
  - La validación desplaza en pasos cortos hasta seis veces para localizar visualmente Me gusta y Comentario.
  - Sólo compara texto situado debajo de la fila de acciones y por encima del editor inferior.
  - Los nodos `EditText` y `MultiAutoCompleteTextView`, además de su zona OCR, quedan excluidos para no confundir un borrador con un comentario publicado.
  - Se admiten diferencias OCR u ortográficas pequeñas mediante la comparación difusa existente.
  - Resultado `found`: cancela el reintento; `not_found`: permite un único reintento; `inconclusive`: no reintenta para evitar duplicidad.
  - La limpieza del editor ahora usa Seleccionar todo, borra y verifica el resultado. Si no puede demostrar que quedó vacío, cancela la escritura.
  - El borrador duplicado que permanecía en el teléfono se eliminó sin tocar el comentario ya publicado.
- Pruebas:
  - Compilación y `git diff --check`: correctos.
  - Caso real visible: fila de acciones localizada en `y=885` y comentario reciente confirmado debajo de ella.
  - La diferencia ortográfica mínima fue aceptada; el mismo texto dentro del editor fue rechazado como evidencia de publicación.
  - Simulación con la fila fuera de pantalla: realizó un desplazamiento y confirmó después.
  - Estados `found`, `not_found` e `inconclusive`: uno, dos y un intento respectivamente.
  - No se envió ningún comentario durante las pruebas.
  - Constructor oficial completado sin cerrar la versión activa.
- Entrega: `release_1.88.1/AdministracionDeMoviles.exe` (87,064,918 bytes) y `SHA256.txt`.
- SHA-256: `A4BE1E82112C74E31BC481097DE7BC887A257E00D062613F410D5D007A3F89F1`.
- Commit resultante: El commit de la rama `integracion` que contiene esta entrada.

### CHG-20261112-1450 — Enlace y acciones opcionales en publicaciones sin texto accesible

- Fecha y hora de inicio: 2026-11-12 14:50:41 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 15:01:44 (America/Mexico_City)
- Tipo: Corrección funcional y recurso visual solicitados por el cliente
- Objetivos:
  - Reconocer publicaciones de Facebook Lite que muestran fecha y contenido visualmente pero no exponen texto en accesibilidad.
  - Abrir la publicación correcta y obtener su enlace cuando `Guardar enlace` esté seleccionado.
  - Verificar que `Me gusta` y `Comentario` se ejecuten únicamente cuando sus casillas estén seleccionadas.
  - Regresar desde publicaciones simples o anidadas hasta el feed principal antes de reanudar el scroll.
  - Incorporar un icono de aplicación con un teléfono caricaturizado, ojos y sombrero cónico, visible en ventana, barra de tareas y ejecutable.
- Diagnóstico inicial: la publicación visible de Información Sierra Norte no era publicidad y mostraba `22 h`, pero el encabezado accesible medía 71.4 % del ancho y el detector geométrico sólo aceptaba hasta 70 %; además, Facebook Lite exponía el bloque como vistas sin texto.
- Referencia de rollback: commit `938f6b1` de la rama `integracion`.
- Rama Git: `integracion`.
- Implementación:
  - El detector geométrico acepta encabezados válidos de hasta 76 % del ancho y reconoció la fecha real en `(221, 319)`.
  - Después de pulsar la fecha, el panel confirma el encabezado o editor propio de una publicación y reintenta una sola vez; sin confirmación no obtiene enlaces ni pulsa acciones.
  - La captura existente de `Más opciones` y `Copiar enlace` se conservó y se comprobó correctamente en la publicación real.
  - La selección de acciones se aisló en una función que ejecuta exclusivamente `Me gusta`, `Comentario`, ambas o ninguna según los checkboxes.
  - Tras una publicación simple o anidada, el panel repite Atrás hasta cuatro veces mientras siga detectando una vista de publicación. El scroll sólo se reanuda cuando el feed queda confirmado.
  - Se añadió un identificador de aplicación de Windows, icono de ventana y recursos nativos PNG/ICO dentro de `assets`.
  - El icono fue generado con la herramienta integrada de imágenes: teléfono azul amistoso, ojos curvos de caricatura, sombrero cónico de paja, fondo transparente y sin texto.
  - El constructor incorpora el icono al `.exe` y genera esta actualización en `release_1.88`, sin cerrar ni reemplazar la versión anterior que permanece en uso.
- Pruebas:
  - Compilación, `git diff --check`, icono Tk y recursos: correctos.
  - Árbol real de Facebook Lite: fecha geométrica detectada en el punto esperado.
  - Captura real del enlace: correcta; no se registró el URL en la bitácora.
  - Detectores visuales sin toque: Me gusta en `(105, 1017)` con puntuación `0.95`; Comentario en `(341, 1017)` con puntuación `1.00`.
  - Las cuatro combinaciones de checkboxes fueron simuladas y sólo invocaron las acciones seleccionadas.
  - Regreso anidado simulado con dos niveles: correcto; regreso real desde la publicación al feed: confirmado.
  - No se dio Me gusta ni se publicó comentario durante las pruebas.
  - Icono asociado extraído del ejecutable y revisado en tamaño pequeño; icono de ventana comprobado visualmente.
  - Constructor oficial ejecutado correctamente sin interrumpir el panel anterior.
- Entrega: `release_1.88/AdministracionDeMoviles.exe` (87,060,919 bytes) y `SHA256.txt`.
- SHA-256: `7C254DB3A8E0B6CEC9F5443B5A76C1BA4B919074B8A8BF4735BB0A9B75E92894`.
- Commit resultante: El commit de la rama `integracion` que contiene esta entrada.

### CHG-20261112-1323 — Cambio de nombre bilingüe y versión visible

- Fecha y hora de inicio: 2026-11-12 13:23:24 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 13:26:11 (America/Mexico_City)
- Tipo: Identidad visual y distribución solicitadas por el cliente
- Objetivo: Cambiar el nombre visible a `Administración de móviles (移动设备管理)` y mostrar `版本 1.88` en el extremo inferior derecho.
- Alcance: títulos del panel y activación, encabezado, pie de página, nombre del ejecutable, constructor, documentación y bitácora.
- Compatibilidad: no se cambiaron funciones, secuencias, licencia, huella del equipo ni comportamiento de automatización.
- Riesgo: referencias antiguas al nombre del ejecutable en accesos directos o instrucciones externas.
- Referencia de rollback: commit `79e19e5` de la rama `integracion`.
- Rama Git: `integracion`.
- Implementación:
  - El título de la ventana, el encabezado principal y la pantalla de activación muestran el nombre bilingüe solicitado.
  - Se agregó un pie permanente en el extremo inferior derecho con `版本 1.88`.
  - El ejecutable pasó a llamarse `AdministracionDeMoviles.exe` y el constructor genera el SHA-256 con ese nombre.
  - Se conservan internamente la ruta de licencia y el mutex anteriores para no romper compatibilidad operativa.
- Pruebas:
  - Compilación de `panel.py` y `license_guard.py`, aserciones de textos y `git diff --check`: correctos.
  - Revisión visual: caracteres chinos correctos en ventana y encabezado; pie completo con escala de Windows.
  - Ejecutable compilado: pantalla de activación bilingüe abierta correctamente y cancelada sin crear una licencia nueva.
  - Entrega: `AdministracionDeMoviles.exe` (85,516,620 bytes) y `SHA256.txt`.
  - SHA-256: `AD68675EC75FB5053F4D4B2C9EF7CA3F91541952798E42908EED7BAFD0837A09`.
- Commit resultante: El commit de la rama `integracion` que contiene esta entrada.

### CHG-20261112-1012 — Ejecutable protegido, pantalla de inicio y licencia por equipo/USB

- Fecha y hora de inicio: 2026-11-12 10:12:58 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 13:21:25 (America/Mexico_City)
- Tipo: Distribución y control de acceso solicitados por el cliente
- Autoría: Se conserva la autoría del proyecto original; el trabajo se limita a empaquetar y proteger la distribución solicitada.
- Objetivos:
  - Generar un ejecutable portable sin archivos fuente `.py` en la carpeta entregable.
  - Mostrar una pantalla de inicio antes del panel.
  - Solicitar una contraseña dinámica basada en la fecha local al activar y cada 20 días.
  - Vincular la licencia al equipo si se ejecuta desde disco fijo o a la unidad USB si se ejecuta desde una unidad removible.
  - Solicitar una nueva activación cuando el paquete se copie a otro equipo o a otra USB.
  - Mejorar la organización visual del panel sin retirar ni alterar funciones existentes.
- Diseño solicitado durante la implementación:
  - Sustituir la fila saturada de pestañas por una navegación lateral agrupada.
  - Incorporar encabezado con página actual y resumen de teléfonos.
  - Unificar tipografía, colores, espaciado, tablas, botones y campos.
  - Convertir la consola global en un panel compacto que pueda mostrarse u ocultarse.
- Seguridad prevista: licencia firmada, detección de retroceso de fecha, contraseña no almacenada y huella SHA-256; no se registrarán claves ni huellas completas en la bitácora.
- Limitación explícita: Un ejecutable local puede dificultar la recuperación del código, pero no puede garantizar que sea técnicamente imposible analizarlo o modificarlo.
- Distribución: Las herramientas ADB, scrcpy, OCR y plantillas se incluirán dentro del ejecutable; los datos operativos permanecerán junto al ejecutable.
- Archivos previstos: `panel.py`, módulo de licencia, script de construcción, `.gitignore`, `LEEME.txt` y esta bitácora.
- Riesgos: falsos positivos de antivirus por ejecutable sin firma, tamaño del paquete, cambio de hardware/volumen y manipulación del reloj local.
- Referencia de rollback: commit `4459fa7` de la rama `integracion`.
- Rama Git: `integracion`.
- Implementación:
  - `license_guard.py` incorpora una licencia local firmada, renovación cada 20 días, detección de retroceso de fecha y validación sin almacenar la contraseña acordada.
  - La huella de equipo combina identificadores locales; la huella USB usa el número de volumen y capacidad, sin depender de la letra asignada por Windows.
  - La pantalla de inicio informa si la vinculación corresponde al equipo o a una USB y permite cancelar sin crear licencia.
  - `Construir Ejecutable.ps1` genera una distribución de un solo archivo con PyInstaller e incluye ADB, scrcpy, OCR y plantillas.
  - El panel reconoce correctamente las rutas internas del ejecutable y conserva los datos operativos fuera del paquete.
  - La interfaz se reorganizó con encabezado de estado, navegación lateral agrupada, página activa resaltada, estilos uniformes y un registro de actividad compacto y plegable.
  - Se mantienen las nueve secciones y sus controles; el cambio de diseño no retira acciones existentes.
  - `release` contiene sólo `PanelCelularesV2.exe` y `SHA256.txt`; las carpetas de construcción y entrega quedan excluidas de Git.
- Pruebas:
  - Compilación de `panel.py` y `license_guard.py`, `git diff --check` y pruebas internas de navegación/consola: correctos.
  - Activación válida, contraseña incorrecta, vigencia hasta el día 19, renovación exacta el día 20, firma alterada y archivo sin contraseña almacenada: correctos.
  - Revisión visual de Dispositivos y Secuencias: navegación lateral, encabezado, selección y controles sin recortes relevantes.
  - Arranque del ejecutable final: correcto; se mostró la activación compilada y se canceló sin crear licencia.
  - Comprobación de entrega: no hay `.py`, `.pyc`, `.ps1` ni `.bat` visibles; ADB, scrcpy y plantillas están incluidos internamente.
  - Búsqueda binaria del prefijo legible de la contraseña: sin coincidencias.
  - SHA-256 final: `64397D95308DB79BA7CA12824EDFA9E67B872F693E0B17DE48ADE8E1E1E1F068`.
  - Firma Authenticode: `NotSigned`; Windows o el antivirus pueden advertir sobre un editor desconocido.
- Entrega local: `release/PanelCelularesV2.exe` (85,516,852 bytes) y `release/SHA256.txt`.
- Limitación verificada: el empaquetado evita entregar fuentes visibles, pero una protección completamente local no garantiza que el ejecutable sea imposible de analizar o alterar.
- Commit resultante: El commit de la rama `integracion` que contiene esta entrada.

### CHG-20261112-0847 — Tiempo de espera en saltos de 500 ms y secuencias paralelas

- Fecha y hora de inicio: 2026-11-12 08:47:03 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 08:48:58 (America/Mexico_City)
- Tipo: Mejora funcional solicitada por el cliente
- Autoría: Se conserva la autoría del proyecto original; el ajuste se limita al constructor de tareas solicitado.
- Objetivo: Mostrar una acción `Tiempo de espera` con mínimo `1` y máximo `4` segundos, eligiendo aleatoriamente sólo valores separados por `0.5` segundos.
- Interpretación del ejemplo: Al solicitar incrementos de 500 ms, el valor indicado como `2.3` se interpreta como `2.5`; las opciones de 1 a 4 serán `1, 1.5, 2, 2.5, 3, 3.5, 4`.
- Simultaneidad: Cada teléfono seleccionado debe ejecutar la secuencia completa en su propio hilo y elegir su propio tiempo aleatorio, sin esperar a que otro teléfono termine sus acciones.
- Compatibilidad: Las secuencias JSON antiguas sin marca de incremento conservarán su espera continua anterior; las nuevas usarán `0.5` segundos.
- Alcance: `panel.py`, `LEEME.txt` y esta bitácora.
- Riesgos: coordinación del botón Detener, liberación de dispositivos al finalizar y mensajes concurrentes en la interfaz.
- Referencia de rollback: commit `dea191f` de la rama `integracion`.
- Rama Git: `integracion`.
- Implementación:
  - El catálogo ahora muestra `Tiempo de espera` con valores iniciales mínimo `1` y máximo `4` segundos.
  - Los nuevos pasos guardan `interval_step: 0.5` y sólo aceptan límites alineados a 500 ms.
  - Cada ejecución elige mediante enteros de medio segundo, evitando decimales intermedios.
  - Las secuencias antiguas sin `interval_step` conservan su comportamiento continuo anterior y no quedan corruptas.
  - El controlador crea un trabajador independiente por teléfono seleccionado; cada uno mantiene su propia lista, posición, pasos y tiempo aleatorio.
  - La finalización y liberación de equipos ocurre únicamente después de que todos los trabajadores terminan; `Detener` continúa siendo compartido.
- Pruebas:
  - Compilación de `panel.py` y `git diff --check`: correctos.
  - Para 1–4 segundos se generó exactamente el conjunto `1, 1.5, 2, 2.5, 3, 3.5, 4`.
  - Límites no alineados a 500 ms rechazados; espera antigua no alineada aceptada por compatibilidad.
  - Dos teléfonos simulados alcanzaron la espera en paralelo y eligieron valores independientes válidos.
  - Catálogo, valores iniciales y paso JSON verificados en una instancia aislada de la interfaz.
  - No se ejecutaron acciones reales sobre los teléfonos.
- Commit resultante: El commit de la rama `integracion` que contiene esta entrada.

### CHG-20261112-0839 — Acción dedicada para identificar Publicar y pulsarlo

- Fecha y hora de inicio: 2026-11-12 08:39:27 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 08:41:22 (America/Mexico_City)
- Tipo: Funcionalidad solicitada por el cliente
- Autoría: Se conserva la autoría del proyecto original; el ajuste se limita al constructor de tareas solicitado.
- Objetivo: Agregar una acción directa que identifique el control `Publicar` visible y pulse su centro.
- Evidencia del teléfono conectado: La pantalla real muestra `Publicar` en la barra superior y al final del formulario; OCR local los ubicó en `(557,60)-(681,83)` y `(299,1430)-(423,1456)` respectivamente. Facebook Lite no expuso el texto en la jerarquía Android.
- Criterio: Priorizar la coincidencia superior para evitar ambigüedad; reutilizar la búsqueda existente por accesibilidad/OCR y no usar coordenadas fijas.
- Alcance: `panel.py`, `LEEME.txt` y esta bitácora.
- Riesgos: cambios visuales de Facebook Lite o aparición de otro texto idéntico por encima del botón.
- Referencia de rollback: commit `39f90ea` de la rama `integracion`.
- Rama Git: `integracion`.
- Implementación:
  - Se agregó `Identificar Publicar y pulsar` al catálogo de Secuencias de acciones.
  - La acción busca el texto correcto `Publicar` mediante la función existente de accesibilidad/OCR.
  - Cuando hay varias coincidencias exactas, se elige la superior; no se guardan coordenadas fijas.
  - La ejecución registra el origen y las coordenadas calculadas o informa si no encuentra el control.
- Pruebas:
  - Compilación de `panel.py` y `git diff --check`: correctos.
  - Pantalla real del teléfono conectado: OCR local identificó el control superior en `(619,71)`.
  - Prioridad de coincidencia superior y validación del paso: correctas.
  - Acción y explicación verificadas en una instancia aislada de la interfaz.
  - No se pulsó `Publicar` ni se transmitió contenido durante las pruebas.
- Commit resultante: El commit de la rama `integracion` que contiene esta entrada.

### CHG-20261112-0830 — Acción para subir imagen o video al teléfono

- Fecha y hora de inicio: 2026-11-12 08:30:29 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 08:32:41 (America/Mexico_City)
- Tipo: Funcionalidad solicitada por el cliente
- Autoría: Se conserva la autoría del proyecto original; el ajuste se limita al constructor de tareas solicitado.
- Objetivo: Permitir seleccionar una imagen o video local y agregar su transferencia al teléfono como un paso de la secuencia.
- Estrategia: Enviar imágenes a `Pictures/PanelCelulares` y videos a `Movies/PanelCelulares`, después notificar al escáner multimedia de Android para que aparezcan en Galería/Archivos.
- Privacidad y repositorio: La secuencia guardará únicamente la ruta local; el archivo multimedia no se copiará al proyecto ni se publicará en Git.
- Alcance: `panel.py`, `LEEME.txt` y esta bitácora.
- Riesgos: archivo movido después de guardar la secuencia, espacio insuficiente en el teléfono o desconexión durante la transferencia.
- Referencia de rollback: commit `d550f69` de la rama `integracion`.
- Rama Git: `integracion`.
- Implementación:
  - Se agregó `Subir imagen/video al teléfono` al catálogo de Secuencias de acciones.
  - El selector admite formatos comunes de imagen y video y muestra la ruta elegida sin copiar el archivo al proyecto.
  - Al ejecutar, crea `Pictures/PanelCelulares` para imágenes o `Movies/PanelCelulares` para videos y transfiere el archivo mediante ADB.
  - Después solicita el escaneo multimedia de Android para que el archivo aparezca en Galería/Archivos.
  - La transferencia puede detenerse con el botón `Detener` y tiene protección ante desconexión o una espera superior a diez minutos.
  - Si el archivo local fue movido o eliminado, el paso lo informa y no intenta transferirlo.
- Pruebas:
  - Compilación de `panel.py` y `git diff --check`: correctos.
  - Clasificación de imagen/video, validación del paso, destino remoto y URI de escaneo: correctos mediante simulación local.
  - Cancelación de una transferencia activa mediante `Detener`: correcta.
  - Selector y acción verificados en una instancia aislada de la interfaz.
  - No se transfirieron archivos reales ni se ejecutaron acciones sobre el teléfono.
- Commit resultante: El commit de la rama `integracion` que contiene esta entrada.

### CHG-20261112-0825 — Acción para ocultar el teclado

- Fecha y hora de inicio: 2026-11-12 08:25:56 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 08:27:06 (America/Mexico_City)
- Tipo: Funcionalidad solicitada por el cliente
- Autoría: Se conserva la autoría del proyecto original; el ajuste se limita al constructor de tareas solicitado.
- Objetivo: Agregar una acción independiente que cierre el teclado después de invocarlo, sin abandonar accidentalmente la pantalla cuando el teclado ya esté oculto.
- Estrategia: Comprobar el estado del teclado mediante Android y enviar Atrás únicamente cuando se confirme que está visible.
- Alcance: `panel.py`, `LEEME.txt` y esta bitácora.
- Riesgos: diferencias de diagnóstico entre versiones y fabricantes de Android.
- Referencia de rollback: commit `77bace5` de la rama `integracion`.
- Rama Git: `integracion`.
- Implementación:
  - Se agregó `Ocultar teclado` al catálogo de Secuencias de acciones.
  - La acción consulta `dumpsys input_method` y reconoce los indicadores habituales de distintas versiones de Android.
  - Si el diagnóstico no es concluyente, revisa la jerarquía accesible para detectar el paquete del teclado.
  - Sólo envía `KEYCODE_BACK` cuando confirma que el teclado está visible; si ya está oculto, no cambia de pantalla.
- Pruebas:
  - Compilación de `panel.py` y `git diff --check`: correctos.
  - Teclado visible: se envía una sola orden Atrás.
  - Teclado oculto: no se envía Atrás.
  - Alternativa por accesibilidad y variantes de diagnóstico Android: correctas mediante simulación local.
  - Catálogo y explicación de la acción verificados en una instancia aislada de la interfaz.
  - No se ejecutaron acciones reales sobre el teléfono.
- Commit resultante: El commit de la rama `integracion` que contiene esta entrada.

### CHG-20261112-0001 — Acción para identificar texto y pulsarlo

- Fecha de inicio: 2026-11-12 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-12 02:26:47 (America/Mexico_City)
- Tipo: Funcionalidad solicitada por el cliente
- Autoría: Se conserva la autoría del proyecto original; el ajuste se limita al constructor de tareas solicitado.
- Objetivo: Agregar una acción que localice un texto visible configurable —inicialmente `Escribe algo...`— y pulse el centro del elemento encontrado.
- Estrategia: Buscar primero en la información accesible de Android y, si el texto no está expuesto, usar el OCR local existente. No se usarán coordenadas fijas.
- Alcance: `panel.py`, `LEEME.txt` y esta bitácora.
- Riesgos: variantes de puntos suspensivos, texto duplicado en pantalla y controles sin información accesible.
- Referencia de rollback: commit `d4dd396` de la rama `integracion`.
- Rama Git: `integracion`.
- Implementación:
  - Se agregó `Identificar texto y pulsar` al catálogo de Secuencias de acciones.
  - El campo comienza con `Escribe algo...` y permite configurar otra frase completa.
  - La búsqueda prioriza la jerarquía accesible de Android y usa el OCR local existente como alternativa.
  - `...` y `…` se consideran equivalentes; se normalizan espacios y mayúsculas, pero no se aceptan coincidencias parciales.
  - El toque se ejecuta en el centro calculado del texto encontrado, sin coordenadas fijas.
- Pruebas:
  - Compilación de `panel.py`: correcta.
  - `git diff --check`: correcto.
  - Coincidencia accesible, variante de puntos suspensivos, alternativa OCR, centro calculado y rechazo de coincidencia parcial: correctos mediante simulación local.
  - Catálogo visual y valor inicial del campo creados correctamente en una instancia aislada del panel.
  - No se pulsó ningún control real del teléfono durante la prueba.
- Commit resultante: El commit de la rama `integracion` que contiene esta entrada.

### CHG-20261106-1822 — Restaurar Dar clic y agregar gesto sostenido

- Fecha y hora de inicio: 2026-11-06 18:22:13 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-06 18:29:00 (America/Mexico_City)
- Tipo: Corrección funcional solicitada por el cliente
- Autoría: Se conserva la autoría del proyecto original; sólo se restituye la función solicitada.
- Problema: El toque proporcional continuó existiendo al pulsar la captura, pero la ampliación del constructor omitió la acción `Dar clic` en el catálogo visible.
- Objetivo: Volver a mostrar `Dar clic` en la lista de acciones y conservar exactamente el registro mediante cruz numerada y coordenadas proporcionales sobre la captura del teléfono.
- Ampliación solicitada: Agregar `Presionar y deslizar`; el primer punto marca dónde se mantiene presionada la pantalla y el segundo dónde termina el desplazamiento, ambos con coordenadas proporcionales.
- Alcance: `panel.py`, `LEEME.txt` y esta bitácora; no se modifican las demás acciones ni pestañas.
- Referencia de rollback: commit `1bb641b` de la rama `integracion`.
- Rama Git: `integracion`.
- Implementación:
  - `Dar clic en la captura` volvió al catálogo; `Agregar acción` activa el registro y un clic sobre la imagen crea la cruz roja numerada con X/Y proporcionales.
  - Se agregó `Presionar y deslizar` con duración configurable entre 100 y 10000 ms.
  - El primer punto marca el inicio sostenido, el segundo marca el destino y una flecha naranja muestra la dirección.
  - La ejecución convierte ambos puntos proporcionales a la resolución real de cada teléfono y usa el gesto Android `input touchscreen swipe` con la duración guardada.
  - La validación, guardado y carga JSON versión 1 aceptan ambos tipos de acción sin afectar secuencias anteriores.
- Pruebas:
  - `python -m py_compile panel.py`: correcto.
  - `git diff --check`: correcto.
  - Catálogo `tap`/`swipe`, validación de dos puntos, coordenadas proporcionales y comando sostenido: correctos mediante simulación local.
  - No se ejecutó el toque ni el deslizamiento sobre el teléfono durante la prueba.
- Commit resultante: El commit de la rama `integracion` que contiene esta entrada.

### CHG-20261106-1805 — Constructor ampliado de procesos y acciones

- Fecha y hora de inicio: 2026-11-06 18:05:30 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-06 18:14:15 (America/Mexico_City)
- Tipo: Ampliación solicitada por el cliente
- Autoría: Se conserva la autoría del proyecto original; sólo se implementa y documenta la solicitud.
- Objetivo: Evolucionar `Secuencias de acciones` al diseño de un constructor de escritorio con catálogo de acciones, parámetros visibles y ejecución ordenada.
- Acciones solicitadas:
  - Cargar una lista donde cada renglón representa el siguiente elemento del proceso.
  - Avanzar explícitamente al siguiente elemento cargado.
  - Escribir texto con intervalo aleatorio mínimo y máximo entre caracteres.
  - Abrir una URL reutilizando únicamente el mecanismo existente de `Abrir Link / URL`.
  - Ejecutar calentamiento orgánico reutilizando `simular_navegacion_organica`.
  - Conservar captura visual, toque proporcional, espera aleatoria y Atrás.
- Valores iniciales: espera `3–8 s`, calentamiento `5–15 s` e intervalo entre letras `0.05–0.15 s`; se conservan las pausas internas existentes del calentamiento.
- Límites: Sin acciones específicas de reportes; sin duplicar la lógica existente de URL o calentamiento; sin modificar las demás pestañas.
- Archivos modificados: `panel.py`, `LEEME.txt`, `BITACORA.md`.
- Riesgos: contexto correcto de listas por teléfono, Unicode al escribir, cancelación entre caracteres y compatibilidad con JSON anteriores.
- Referencia de rollback: commit `1f7c217` de la rama `integracion`.
- Rama Git: `integracion`.
- Implementación:
  - Se agregó un catálogo visible con `Escribir texto`, `Cargar lista por renglones`, `Siguiente elemento de lista`, `Abrir liga / link`, `Calentamiento orgánico`, `Espera aleatoria` y `Atrás`.
  - La captura del teléfono y los toques proporcionales permanecen disponibles como referencia visual.
  - Cada teléfono conserva su propio contexto de lista y posición; avanzar no reinicia la lista al llegar al final.
  - La escritura admite texto literal o el elemento actual de la lista y aplica una espera aleatoria entre cada carácter.
  - `Abrir liga / link` reutiliza exclusivamente la apertura de Facebook Lite por `android.intent.action.VIEW`; no ejecuta Me gusta, comentario ni otro flujo posterior.
  - `Calentamiento orgánico` reutiliza `simular_navegacion_organica` y respeta el botón Detener.
  - El diseño se compactó para mantener visibles la captura, la lista de pasos y los controles de ejecución en una pantalla de escritorio.
- Pruebas:
  - `python -m py_compile panel.py`: correcto.
  - `git diff --check`: correcto.
  - Validación simulada del catálogo, carga/avance de lista, escritura, apertura de URL, calentamiento, espera, Atrás y toque proporcional: correcta.
  - Escritura simulada carácter por carácter, espacios, demora aleatoria y cancelación: correcta.
  - Compatibilidad de carga con esperas fijas del JSON anterior: correcta.
  - Revisión visual del panel: catálogo completo y controles de ejecución visibles.
  - No se ejecutaron acciones reales sobre el teléfono durante esta verificación.
- Commit resultante: El commit de la rama `integracion` que contiene esta entrada.

### CHG-20261106-1747 — Espera aleatoria mínima y máxima en Secuencias

- Fecha y hora de inicio: 2026-11-06 17:47:00 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-06 18:14:15 (America/Mexico_City)
- Tipo: Mejora solicitada por el cliente
- Autoría: Se conserva la autoría del proyecto original; sólo se implementa y documenta la solicitud.
- Objetivo: Sustituir la espera fija del constructor de secuencias por una espera aleatoria configurable entre un mínimo y un máximo, como la opción existente en Interacciones y Búsqueda.
- Compatibilidad: Los JSON anteriores que contengan `seconds` deben cargarse como una espera fija equivalente, sin quedar corruptos.
- Archivos modificados: `panel.py`, `LEEME.txt`, `BITACORA.md`.
- Riesgos: validar mínimo y máximo, conservar la cancelación inmediata y guardar un formato estable.
- Referencia de rollback: commit `1f7c217` de la rama `integracion`.
- Rama Git: `integracion`.
- Implementación: La espera se guarda como `min_seconds` y `max_seconds`, elige un valor aleatorio al ejecutar y sigue siendo cancelable.
- Compatibilidad: Una espera antigua con `seconds` se normaliza como mínimo y máximo iguales.
- Pruebas: Compilación, validación de formato, espera aleatoria simulada y compatibilidad anterior correctas.
- Commit resultante: El commit de la rama `integracion` que contiene esta entrada.

### CHG-20261106-1735 — Pestaña inicial de Secuencias de acciones

- Fecha y hora de inicio: 2026-11-06 17:35:00 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-06 17:44:03 (America/Mexico_City)
- Tipo: Funcionalidad solicitada por el cliente
- Autoría: Se conserva la autoría del proyecto original; este trabajo se limita a implementar la solicitud y documentar el cambio.
- Objetivo: Crear una pestaña independiente para construir, guardar y ejecutar procedimientos sencillos paso a paso, sin modificar el comportamiento de las pestañas existentes.
- Implementación:
  - Captura real de la pantalla del teléfono seleccionado dentro del panel.
  - Registro visual de toques mediante marcadores numerados; cada toque se almacena como proporción de ancho y alto.
  - Pasos de espera entre 0.1 y 3600 segundos y acción Atrás de Android.
  - Lista con reordenamiento, eliminación y limpieza de pasos.
  - Ejecución de un paso seleccionado o de la secuencia completa en los teléfonos disponibles.
  - Exclusión de dispositivos ocupados, tarea visible por teléfono, log individual y detención mediante evento cancelable.
  - Guardado y carga JSON versión 1 con límite de 500 pasos y lista cerrada de acciones `tap`, `wait` y `back`.
  - Carpeta operativa `secuencias` excluida de Git.
- Límites intencionales: Sin funciones específicas de reportes, sin rotación de IP, sin calentamiento, sin ejecución oculta y sin captura directa de toques físicos.
- Pruebas realizadas:
  - Compilación de Python y `git diff --check`: correctos.
  - Validación de JSON: acepta las tres acciones admitidas y rechaza tipos desconocidos, proporciones fuera de rango y esperas inválidas.
  - Escalado simulado: un toque grabado al 25% × 50% se convirtió correctamente en `(180, 760)` sobre una pantalla de 720 × 1520.
  - Secuencia simulada: ejecutó Toque, Espera y Atrás en el orden esperado.
  - Cancelación simulada durante una espera: no ejecutó el paso posterior y terminó como `detenida`.
  - Arranque real del panel: proceso responsivo, pestaña visible y controles completos.
  - Prueba visual real: capturó el teléfono `W555`, mostró una imagen de 720 × 1520 y registró un toque con marcador y coordenadas proporcionales sin enviarlo al dispositivo.
- Referencia de rollback: commit `586c136` de la rama `integracion`.
- Rama Git: `integracion`.
- Hash de `panel.py`: `21716B5CC6E4BD739678C9B118650AE213EFE283767C949279675D6BF9B839ED`.
- Hash de `LEEME.txt`: `937B5D6308E92639D5C9C231F90B8850B1183057CF94DA9BE8D628067B72E209`.
- Hash de `.gitignore`: `6F84380EC8166BCD4F8920513EFB58E1BD97065A0ABB6A01DC1D9FD1E9C69EA0`.

### CHG-20261106-0950 — Casilla Guardar enlace en Búsqueda

- Fecha y hora de inicio: 2026-11-06 09:50:00 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-06 09:52:10 (America/Mexico_City)
- Tipo: Mejora funcional solicitada
- Objetivo: Añadir una casilla `Guardar enlace` antes de `Comentario` en la pestaña Búsqueda.
- Implementación:
  - La nueva casilla aparece entre `Me gusta` y `Comentario` y comienza activada para conservar el comportamiento anterior.
  - Activada: abre la publicación, obtiene el enlace y lo registra en el CSV diario.
  - Desactivada y sin otras acciones: contabiliza y muestra la coincidencia sin abrir la publicación, consultar menús ni modificar el CSV.
  - Desactivada con Me gusta o Comentario activos: abre la publicación únicamente para las acciones seleccionadas; no obtiene ni muestra una línea de enlace.
- Pruebas realizadas:
  - Compilación de Python y `git diff --check`: correctos.
  - Casilla desactivada sin otras acciones: cero toques, cero capturas, cero escrituras y resultado `coincidencia contabilizada`.
  - Casilla activada: apertura, captura, registro y regreso al feed en el orden esperado.
  - El resultado no muestra `Enlace: no disponible` cuando la captura fue desactivada voluntariamente.
- Referencia de rollback: commit `52bfb6f` de la rama `integracion`.
- Rama Git: `integracion`.
- Hash de `panel.py`: `2B150E7FB82BD55BA70A069F2CFDF77F24115C062A81347107F9EAFC5798CE11`.
- Hash de `LEEME.txt`: `7C5350AE9A70F4106675A864C9974F0AAE4B6BC82097D75DD5C7B92B6C5F577F`.

### CHG-20261106-0946 — No omitir una publicación normal después de publicidad

- Fecha y hora de inicio: 2026-11-06 09:46:00 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-06 09:49:00 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Problema observado: Búsqueda omitió una publicación de `Voltaje Noticias` que contenía `Huauchinango`, mostraba `14 min ·` y no era publicidad; por lo tanto no abrió la publicación ni obtuvo su enlace.
- Diagnóstico real:
  - Android no expuso el texto de la tarjeta, pero el OCR sí reconoció `Huauchinango` y `14 min`.
  - La asociación aislada produjo correctamente el punto de fecha `(172, 389)` y no detectó rótulos publicitarios.
  - El descarte provino de `ad_guard`: después de un anuncio se omitían dos pantallas completas, incluso cuando ya aparecía una publicación nueva con fecha válida.
- Implementación:
  - La protección posterior a publicidad continúa descartando pantallas sin una publicación nueva validada.
  - Si aparece una coincidencia asociada a una fecha/hora válida, se cancela la protección anterior y se procesa la publicación normalmente.
- Pruebas realizadas:
  - Compilación de Python y `git diff --check`: correctos.
  - Captura real reportada: coincidencia `huauchinango`, fecha `14 min`, punto `(172, 389)` y cero rótulos publicitarios.
  - Simulación con protección publicitaria activa: la publicación real con fecha válida queda autorizada.
  - Simulación de continuación sin fecha: permanece rechazada.
  - Prueba real completa sobre la publicación omitida: se abrió mediante `14 min`, se capturó `https://www.facebook.com/share/p/19nmGJVp2W/` y se agregó al CSV diario.
- Referencia de rollback: commit `1c6faff` de la rama `integracion`.
- Rama Git: `integracion`.
- Hash de `panel.py`: `464752FC84F396608E44C19A0C52ACF148B7C58C313B41F11EE25DE601AF219D`.
- Hash de `LEEME.txt`: `58E9B792645D6C3FE5793CFA10AAB23632E2936F754258A8E806670BDDB8ED08`.

### CHG-20261106-0614 — Captura y registro del enlace de cada coincidencia

- Fecha y hora de inicio: 2026-11-06 06:14:42 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-06 09:36:24 (America/Mexico_City)
- Tipo: Mejora funcional solicitada
- Objetivo: Cuando Búsqueda abra una publicación coincidente, obtener su enlace, mostrarlo junto a la coincidencia y guardarlo en el CSV diario sin duplicados.
- Implementación:
  - La vista abierta se valida antes de tocar controles de la publicación.
  - Se usan exclusivamente los rótulos exactos `Más opciones` y `Copiar enlace`; si no aparecen, se informa `Enlace: no disponible` y la búsqueda continúa.
  - El portapapeles del teléfono se pega temporalmente en la búsqueda de Ajustes para leer el URL sin instalar aplicaciones ni publicar el contenido.
  - El panel regresa a la misma publicación, cierra los menús y continúa con las acciones configuradas.
  - El resultado de Búsqueda muestra `Enlace: <URL> · guardado en registro diario`.
  - Cada URL válida se guarda sin duplicados en `registros_busqueda/enlaces_AAAA-MM-DD.csv` con fecha, dispositivo, palabras, fecha de la publicación y vista previa.
- Pruebas realizadas:
  - Compilación de Python y `git diff --check`: correctos.
  - Extracción aislada desde Ajustes: recuperó `https://www.facebook.com/share/p/1FTwJvGAJi/`.
  - Validación de dominio: rechazó un URL ajeno a Facebook.
  - Registro CSV: creación correcta y segundo intento del mismo URL sin duplicarlo.
  - Prueba completa en el celular `W555NEU0100057516`: abrió `Más opciones`, copió el enlace, lo recuperó desde Ajustes y obtuvo `https://www.facebook.com/share/p/1DrrfC4PBi/`.
  - Verificación visual final: regresó a la publicación correcta con ambos menús cerrados; después se restauró el feed.
- Referencia de rollback: `_rollback\CHG-20261106-0614`.
- Rama Git: `integracion`.
- Hash de `panel.py`: `52C085A0970AC4D3449D1C4969E770E7DEEB3B77A1EDFB332F9556661B7B0EE7`.
- Hash de `LEEME.txt`: `1736D8750646B1CA8407C44CA1488F7A704408751318CD57D0AF0BEED624B7E9`.

### CHG-20261106-0531 — Monitor multi-celular con logs individuales

- Fecha y hora de inicio: 2026-11-06 05:31:56 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-06 09:36:24 (America/Mexico_City)
- Tipo: Mejora funcional solicitada
- Implementación:
  - `Ver en Pantalla` usa las opciones compatibles con scrcpy 5.0 y ya no crea una consola CMD por teléfono.
  - Las pantallas se distribuyen según el tamaño del monitor y cada teléfono tiene un log individual debajo.
  - El borde real de la ventana de scrcpy se lee en Windows para alinear el log con el mismo margen izquierdo y exactamente el mismo ancho exterior.
  - Se añadieron `Ver todos`, `Cerrar pantallas` y `Cerrar todas`, además de cierre y seguimiento independiente por dispositivo.
  - La salida de scrcpy y los mensajes identificados por serie se muestran en el log del teléfono correspondiente.
- Pruebas realizadas:
  - Cálculo de distribución verificado para 1, 2, 4, 6 y 8 equipos.
  - Prueba real con un celular: scrcpy abrió sin consola CMD y el log individual recibió la salida del monitor.
  - Compilación de Python y `git diff --check`: correctos.
- Prueba pendiente no bloqueante: validar visualmente la distribución simultánea cuando estén conectados varios celulares físicos.
- Referencia de rollback: `_rollback\CHG-20261106-0531`.
- Rama Git: `integracion`.
- Hash de `panel.py`: `52C085A0970AC4D3449D1C4969E770E7DEEB3B77A1EDFB332F9556661B7B0EE7`.
- Hash de `LEEME.txt`: `1736D8750646B1CA8407C44CA1488F7A704408751318CD57D0AF0BEED624B7E9`.

### CHG-20261106-0504 — Evitar aperturas accidentales durante el scroll

- Fecha y hora de inicio: 2026-11-06 05:04:35 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-06 05:06:09 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Problema reportado: Durante el scroll automático, Facebook abrió una publicación publicitaria aunque el filtro estaba identificando `Publicidad`.
- Evidencia y causa:
  - La búsqueda se detuvo manualmente con cero coincidencias; por lo tanto, la frase y las acciones no ocasionaron la entrada.
  - El registro mostraba repetidamente `Publicidad detectada` y `Se omite la continuación visible del bloque publicitario`.
  - La pantalla real estaba dentro de `Publicación de Senderos Herba…`, en la sección de comentarios.
  - El gesto anterior duraba entre 380 y 620 ms; Facebook podía interpretar su final sobre una tarjeta como toque o pulsación prolongada.
- Implementación:
  - El scroll vertical ahora usa un recorrido ligeramente más amplio y una duración de 210 a 300 ms.
  - Se agregó detección de publicación abierta mediante el encabezado `Publicación de` o la estructura de comentarios.
  - Si Facebook abre una publicación sin una coincidencia validada, el panel pulsa Atrás, regresa al feed y no ejecuta Me gusta ni Comentario.
  - `Ver más` tampoco se procesa mientras la aplicación está dentro de una publicación abierta accidentalmente.
- Pruebas realizadas:
  - Se detuvo la búsqueda activa desde el panel; resultado: cero coincidencias.
  - Se capturaron pantalla y jerarquía reales del estado abierto para el diagnóstico.
  - Se regresó manualmente al feed mediante Atrás.
  - Pruebas unitarias: una cabecera `Publicación de Senderos Herba` se reconoce como publicación abierta; el feed normal no se confunde.
  - Prueba reversible real del nuevo gesto de 250 ms: el teléfono permaneció en el feed y desplazó hasta un anuncio de Adobe Acrobat sin abrirlo.
  - Compilación de Python correcta.
  - Panel local reiniciado; proceso 29880 estable y respondiendo.
- Referencia de rollback: `_rollback\CHG-20261106-0504`.
- Hash local de `panel.py`: `6E4D2A8512FFE6439CEB52F4EBDB85B2FBC6F5EE87AE96B0997F6D5A4031C486`.
- Hash local de `LEEME.txt`: `61F453910C5157AEFBB2AD83AA2E63B21047CE9C3F3C37C1DB426E25819F2877`.
- Publicación remota: No realizada.
- Git/GitHub: No utilizado.

### CHG-20261106-0440 — Frase completa y bloqueo persistente de publicidad

- Fecha y hora de inicio: 2026-11-06 04:40:07 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-06 04:42:49 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Problema reportado:
  - La búsqueda abrió una publicación marcada como `Publicidad`.
  - Se tomó `huauchinango` como coincidencia aunque la búsqueda requerida era la frase completa `huauchinango se llena`.
- Causa confirmada:
  - La protección anterior dependía de que el rótulo publicitario permaneciera visible y cercano al texto candidato; después del scroll, el rótulo podía salir de pantalla mientras el cuerpo del anuncio seguía visible.
  - La coincidencia usaba inclusión de subcadena y no expresaba de forma estricta la regla de frase completa.
- Implementación:
  - Sin comas, todo el contenido del cuadro se evalúa como una frase completa y consecutiva, con límites de palabra.
  - Con comas, cada segmento conserva su significado de alternativa independiente.
  - Accesibilidad y OCR se combinan antes de pulsar `Ver más`; si cualquiera identifica un rótulo publicitario, no se expande el contenido.
  - Cuando se detecta publicidad, se omite el bloque actual y los dos ciclos de desplazamiento siguientes, evitando evaluar el cuerpo residual cuando el rótulo ya salió de pantalla.
  - La distancia vertical de protección dentro de una pantalla se amplió para cubrir el bloque completo del anuncio.
- Pruebas realizadas:
  - Compilación de Python correcta.
  - `huauchinango` no satisface la frase `huauchinango se llena`.
  - `hoy huauchinango se llena de visitantes` sí satisface la frase completa.
  - `pan` no coincide parcialmente con `pantalón`.
  - `huauchinango, xicotepec` conserva dos alternativas independientes.
  - El rótulo real `Publicidad ·` de la captura diagnosticada se reconoce como publicidad y bloquea el contenido inferior.
  - Panel local reiniciado; proceso 5844 estable y respondiendo.
- Referencia de rollback: `_rollback\CHG-20261106-0440`.
- Hash local de `panel.py`: `C7129033832B8C46E06C15E6B84DE0E05808D96A11928B10967A281562A1D99B`.
- Hash local de `LEEME.txt`: `ECA8FCC238A298244E5147E9272399392A4BD99024CAAE9C76631E3BF10434BD`.
- Publicación remota: No realizada.
- Git/GitHub: No utilizado.

### CHG-20261106-0428 — Fechas embebidas en republicaciones compartidas

- Fecha y hora: 2026-11-06 04:28:19 (America/Mexico_City)
- Estado: Completado localmente el 2026-11-06 04:31:37 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Problema reportado: La frase `Huauchinango se llena` estaba visible, pero Búsqueda la omitió y continuó el scroll.
- Causa confirmada:
  - OCR reconoció la frase en el texto exterior y en la publicación compartida interior.
  - La fecha exterior se leyó como `Canal 19 · 5 h ·`, con el nombre de la página antes del tiempo.
  - La fecha interior `5 h` se leyó como `511 ·`, confundiendo la letra `h` con `11`.
  - El detector anterior exigía que la línea comenzara directamente con la fecha.
- Implementación:
  - Se reconoce una unidad temporal válida en cualquier segmento corto del renglón de encabezado, aunque antes aparezca el nombre de la página.
  - Se admite `11`, `ii`, `ll` o `l1` como lectura OCR de la letra `h`, incluso seguida por un símbolo no reconocido.
  - Para renglones mixtos, el punto de toque se calcula usando los límites individuales del número y su unidad; no se usa el centro de toda la línea.
  - Los contadores sin unidad temporal y textos como `Canal 19 publicó en 2 grupos` continúan rechazados.
- Pruebas realizadas:
  - OCR real: fechas `Canal 19 · 5 h ·` y `511 ·` reconocidas.
  - La frase se asoció con la fecha exterior.
  - Primer diagnóstico reversible: el centro del renglón `(224,480)` abrió incorrectamente la página Canal 19; esta evidencia motivó el cálculo por palabra.
  - Límites de `5 h`: `(263,470)-(293,490)`; punto corregido `(278,480)`.
  - Prueba reversible final: `(278,480)` abrió correctamente la publicación de Huauchinango Expresión con el texto buscado.
  - Contadores `13`, `3`, `19`, `20 mil miembros` y texto descriptivo rechazados.
  - Se regresó al feed; no se ejecutó Me gusta ni Comentario.
  - Compilación correcta; panel local reiniciado y estable.
- Referencia de rollback: `_rollback\CHG-20261106-0428`.
- Hash local de `panel.py`: `76F57DE4E15CAC9A6320D26E0EA72CD0E0F5A35A60BDEFAED12831EEDF7742B3`.
- Hash local de `LEEME.txt`: `935105872EA6DB2A31C65E96924A58B4F0F03805143C28B71D456D18D097A241`.
- Publicación remota: No realizada.
- Git/GitHub: No utilizado.

### CHG-20261105-2144 — Campo inferior Comenta como en publicaciones compartidas

- Fecha y hora de inicio: 2026-11-05 21:44:37 (America/Mexico_City)
- Fecha de finalización: 2026-11-06 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Estado: Completado localmente
- Problema reportado: En una republicación compartida, Me gusta funcionó pero Comentario no; la caja inferior cambió a `Comenta como…`.
- Diagnóstico real:
  - Android expuso la caja cerrada en `[116,1392][472,1428]` como `android.widget.MultiAutoCompleteTextView`.
  - El selector anterior sólo admitía clases con `EditText` o `editable=true`, descartando este campo válido.
  - OCR reconoció `Comenta como Josef…` en la franja inferior.
- Implementación:
  - `MultiAutoCompleteTextView` y `AutoCompleteTextView` se aceptan como editores reales y tienen prioridad sobre respaldos genéricos.
  - Se agregaron rótulos `Comenta como`, `Comentar como`, `Comment as` y `Add a comment` en Búsqueda e Interacciones.
  - El punto horizontal se calcula en el centro de la pantalla cuando ese centro permanece dentro de los límites del editor.
  - Si Facebook no expone una clase editable, se acepta una caja inferior con ancho de 32–72% de pantalla, altura de 1.2–7.5%, margen izquierdo de 8–30% y ubicación por debajo de 86% de altura.
  - Se mantienen la escritura verificada, la flecha azul y la confirmación posterior antes de considerar enviado el comentario.
- Pruebas realizadas:
  - Jerarquía real cerrada: campo localizado en `(360,1410)`.
  - Respaldo geométrico sin clase editable: campo localizado en `(360,1410)`.
  - Prueba reversible real: el toque en `(360,1410)` activó `Comenta como…` y abrió el teclado.
  - Jerarquía con teclado abierto: `MultiAutoCompleteTextView` localizado en `(360,1409)`.
  - El teclado se cerró después de la prueba; no se escribió ni envió texto.
  - Compilación de Python correcta; panel local reiniciado y estable.
- Referencia de rollback: `_rollback\CHG-20261105-2144`.
- Hash local de `panel.py`: `A2C3249CDC829B87A555200EEC3B916B72BDCE54A227DB369FC3F77DC2912C5F`.
- Hash local de `LEEME.txt`: `F0907EA1A0D4063466168EECF6F3898EA0B262C8FC68EBD51B7293B631FCBE7C`.
- Publicación remota: No realizada.
- Git/GitHub: No utilizado.

### CHG-20261105-2134 — Ignorar publicaciones marcadas como publicidad

- Fecha y hora: 2026-11-05 21:34:27 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Estado: Completado localmente el 2026-11-05 21:36:02 (America/Mexico_City)
- Solicitud: Ignorar publicaciones que muestran `Publicidad` en lugar de fecha/hora, aunque contengan `Ver más`.
- Evidencia real:
  - OCR localizó `Publicidad` en `(138,773)-(270,792)`.
  - El `Ver más` del mismo anuncio quedó en `(619,854)`.
  - No existía fecha/hora válida ni registro geométrico para el anuncio.
- Implementación:
  - Se reconocen etiquetas cortas `Publicidad`, `Patrocinado`, `Patrocinada`, `Sponsored`, `Anuncio` y `Advertisement`.
  - Para cada `Ver más`, se comprueba si una etiqueta publicitaria aparece encima y dentro de 22% de la altura de pantalla.
  - Para cada coincidencia de palabras, se descarta el bloque si una etiqueta publicitaria aparece encima y dentro de 32% de la altura.
  - El filtro se aplica antes de expandir y antes de asociar una fecha, evitando entrada, Me gusta o Comentario.
- Pruebas realizadas:
  - Captura real del anuncio: ningún control `Ver más` utilizable fue devuelto.
  - La palabra del contenido publicitario fue rechazada incluso al agregar una fecha geométrica falsa en la simulación.
  - Todas las variantes de etiqueta configuradas fueron reconocidas.
  - Captura orgánica de control: `Ver más` continuó localizado correctamente en `(624,1132)`.
  - Compilación de Python correcta; panel local reiniciado y estable.
- Interacciones reales durante pruebas: No se pulsó el anuncio.
- Referencia de rollback: `_rollback\CHG-20261105-2134`.
- Hash local de `panel.py`: `77D9561EACC364EBB1C8820BBC2910B5CB27E9040DB7B060AABA44B66AFC5B98`.
- Hash local de `LEEME.txt`: `8879CE42DD2EEF81ADAA8D82A43741A632FF398EA710FAEFD3366416FA8E38D9`.
- Publicación remota: No realizada.
- Git/GitHub: No utilizado.

### CHG-20261105-2125 — Evitar reintento cuando el primer comentario sí fue publicado

- Fecha y hora: 2026-11-05 21:25:32 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Estado: Completado localmente el 2026-11-05 21:27:10 (America/Mexico_City)
- Problema reportado: El panel realizó el reintento aunque el primer comentario sí había sido publicado; la salida de la publicación y continuación del scroll funcionaron correctamente.
- Causa confirmada:
  - En la vista de comentarios abierta, `Más relevantes` apareció cerca del 27% de la pantalla y el comentario nuevo cerca del 35%.
  - La validación anterior conservaba un inicio mínimo del 55%, excluyendo el comentario aunque OCR lo hubiera leído.
  - OCR puede leer diferencias menores, por ejemplo `con/usted` como `com/uste`.
- Implementación:
  - Si existe `Más relevantes`, `Más recientes` o `Todos los comentarios`, su borde inferior reemplaza por completo el límite porcentual y marca el inicio de la sección.
  - La comparación exacta se conserva y se agregó coincidencia aproximada con proporción de longitud mínima de 0.72 y similitud mínima de 0.88.
  - Se reconoce como éxito el aviso `Se publicó tu comentario` y variantes en español/inglés.
  - Antes de reintentar se realizan hasta cinco comprobaciones normales, una espera adicional de 1.5 segundos y dos comprobaciones tardías.
  - Una confirmación tardía devuelve `sent_late_confirmed` y bloquea el segundo envío.
- Pruebas realizadas:
  - Captura real: comentario nuevo reconocido correctamente debajo de `Más relevantes`.
  - Coincidencia exacta: correcta.
  - Coincidencia OCR aproximada `con/usted` frente a `com/uste`: correcta.
  - Comentario anterior dentro de la sección: localizable.
  - Texto `Eliseo Ortiz Guzmán` del cuerpo principal: rechazado.
  - Aviso sintético `Se publicó tu comentario`: confirmado.
  - Simulación crítica: primer envío sin confirmación inmediata, confirmación tardía positiva y exactamente un intento de publicación.
  - Compilación de Python correcta; panel local reiniciado y estable.
- Acciones reales durante pruebas: No se publicó ningún comentario adicional.
- Referencia de rollback: `_rollback\CHG-20261105-2125`.
- Hash local de `panel.py`: `FBB87A0B615C06BAEE259BB117DB57C5B6AE5740849AED0CE1FB7D7B83D6AEA1`.
- Hash local de `LEEME.txt`: `8FE0350422718B672F4DB9DCB1B7E510D3C47CE635ED3391EDC4271F70F180CE`.
- Publicación remota: No realizada.
- Git/GitHub: No utilizado.

### CHG-20261105-2116 — Confirmar comentario visible y continuar búsqueda

- Fecha y hora: 2026-11-05 21:16:45 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Estado: Completado localmente el 2026-11-05 21:19:09 (America/Mexico_City)
- Problema reportado: El comentario sí fue publicado, pero el panel mostró `Búsqueda detenida: el comentario requiere revisión en la publicación abierta`.
- Diagnóstico real:
  - El comentario publicado aparece en la sección visible, varias líneas por encima de `Escribe un comentario`.
  - Android expuso únicamente el campo inferior; no mostró el comentario publicado.
  - OCR reconoció correctamente el comentario, pero la confirmación anterior sólo comprobaba el editor y la flecha azul.
- Implementación:
  - La confirmación busca el texto esperado en toda la sección visible situada por encima del editor.
  - Si existe `Más relevantes`, `Más recientes` o `Todos los comentarios`, se utiliza como inicio de la zona para excluir el cuerpo principal de la publicación.
  - Si el texto está dividido visualmente, se combinan hasta seis líneas consecutivas.
  - Se eliminan diferencias de mayúsculas, acentos, signos y espacios al comparar.
  - Después del envío se hacen hasta tres comprobaciones separadas por 0.8 segundos.
  - Si el texto no aparece, se repite escritura y envío exactamente una vez.
  - Si tampoco aparece tras el segundo intento, se registra `not_confirmed_after_retry`, se sale de la publicación y continúa el scroll; ya no se activa la detención global.
- Pruebas realizadas:
  - Captura real: el comentario publicado fue localizado correctamente varias líneas por encima del editor.
  - El texto principal `Eliseo Ortiz Guzmán` fue rechazado como confirmación porque está fuera de la zona de comentarios.
  - Prueba sintética multilínea: frase dividida en dos líneas confirmada correctamente.
  - Simulación primer intento fallido/segundo exitoso: resultado `sent_after_retry` y exactamente dos intentos.
  - Simulación de dos fallos: resultado `not_confirmed_after_retry`, dos intentos y búsqueda global todavía activa.
  - Compilación de Python correcta; panel local reiniciado y estable.
- Acciones reales durante pruebas: No se publicó ningún comentario adicional.
- Referencia de rollback: `_rollback\CHG-20261105-2116`.
- Hash local de `panel.py`: `58FA4DD96712324DB278FBC681C3B2FB59A561B60C7F8B3B513C0079A277F67E`.
- Hash local de `LEEME.txt`: `A25F7A6E14548307DF9D1E69E154CEF1D09CFF5D275B13B3EB2ACE69AA3765BE`.
- Publicación remota: No realizada.
- Git/GitHub: No utilizado.

### CHG-20261105-2108 — Expandir Ver más y recuperar fechas no leídas

- Fecha y hora: 2026-11-05 21:08:36 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Estado: Completado localmente el 2026-11-05 21:12:04 (America/Mexico_City)
- Problema reportado: Una publicación con el texto buscado `Eliseo Ortiz` no fue identificada y no ejecutó las acciones seleccionadas.
- Diagnóstico real:
  - El OCR reconoció correctamente `Eliseo Ortiz Guzmán` dentro del texto completo.
  - Facebook Lite entregó 76 nodos Android sin texto ni descripción.
  - El OCR omitió la línea pequeña `1 h ·`; al faltar una fecha validada, la versión anterior rechazó la coincidencia para no abrir una publicación equivocada.
  - Android sí expuso la geometría exacta de esa fecha en `[138,636][238,670]`.
- Implementación:
  - Antes de buscar palabras, se detecta `… Ver más` al final del cuerpo de publicaciones visibles.
  - OCR devuelve ahora límites individuales de cada palabra, permitiendo pulsar el centro de `Ver más` en vez del centro de toda la línea.
  - Después de cada expansión se vuelve a capturar accesibilidad/OCR y se recalculan las posiciones.
  - Se permiten hasta tres expansiones por pantalla y se recuerda cada intento para evitar ciclos.
  - Se excluyen controles que contengan comentarios, respuestas, resultados, grupos, personas o traducciones.
  - Cuando la fecha no tiene texto, se identifica el último renglón geométrico del encabezado de la publicación; exige dimensiones, posición y relación con el bloque del autor.
  - El registro geométrico se combina con el texto OCR para asociar la frase a su propia publicación.
- Pruebas realizadas:
  - Captura colapsada real: `… Ver más` localizado en `(624, 1132)`.
  - Simulación de expansión realista: un toque, nueva lectura sin `Ver más` y continuación con contenido expandido.
  - Captura real del caso reportado: `Eliseo Ortiz` asociado a la fecha geométrica `(188, 653)`.
  - Prueba reversible real: el toque en `(188, 653)` abrió exactamente `Publicación de Miguel Márquez…` con el texto de Eliseo Ortiz; después se regresó al feed.
  - Publicación ya expandida: no produjo un segundo toque de `Ver más`.
  - Compilación de Python correcta; panel local reiniciado y estable.
- Acciones reales durante pruebas: No se dio Me gusta ni se publicó comentario.
- Referencia de rollback: `_rollback\CHG-20261105-2108`.
- Hash local de `panel.py`: `3291FEBEB1408422CCA912C457AC5A652FD4092685C33470D8882F9E95E7FFDE`.
- Hash local de `LEEME.txt`: `0A95D3E6ED7136896EBD43855B3C7B1D71EF55B067EC366AA026E5249F2A0B64`.
- Hash local de `herramientas\ocr_windows.ps1`: `7149500B86207088A474E020F272E4DE4C8084823AA10306E91778EF850D18A9`.
- Publicación remota: No realizada.
- Git/GitHub: No utilizado.

### CHG-20261105-2044 — Abrir la publicación coincidente por fecha/hora

- Fecha y hora: 2026-11-05 20:44:39 (America/Mexico_City)
- Tipo: Funcionalidad solicitada
- Estado: Completado localmente el 2026-11-05 20:56:05 (America/Mexico_City)
- Alcance: Pestaña `Búsqueda (Escucha)`.
- Solicitud: Interpretar palabras o frases separadas por coma, asociar la coincidencia a su publicación, pulsar el enlace pequeño de fecha/hora —por ejemplo `9 h ·` junto al icono de audiencia— y ejecutar dentro de la publicación las acciones existentes de Me gusta y Comentario.
- Diagnóstico real:
  - Facebook Lite mostró el contenido y el enlace temporal, pero su jerarquía Android entregó 72 elementos sin texto ni descripción.
  - Se confirmó disponibilidad del OCR local de Windows en español de México y España; no se instaló software adicional.
- Implementación:
  - Las palabras o frases separadas por coma se evalúan como alternativas normalizadas, sin distinguir mayúsculas ni acentos.
  - Se usa accesibilidad como fuente principal y OCR local como respaldo cuando Facebook no expone el texto.
  - El detector agrupa hasta cinco líneas próximas para reconocer frases divididas por saltos de línea.
  - Cada coincidencia debe tener una fecha/hora cercana en el mismo bloque; sin esa asociación no se toca ninguna publicación.
  - Se admiten rótulos normales como `9 h ·` y errores OCR frecuentes, por ejemplo la `h` pequeña interpretada como `11`.
  - Se excluyen la barra de estado, contadores de reacciones, comentarios y compartidos mediante texto, geometría y ubicación.
  - La publicación se abre pulsando el centro calculado de la fecha/hora.
  - Búsqueda incorpora casillas independientes `Me gusta` y `Comentario`, desactivadas inicialmente, además de un campo para el texto del comentario.
  - Dentro de la publicación, Me gusta reutiliza accesibilidad, figura y desplazamiento; Comentario reutiliza campo validado, escritura y flecha azul.
  - Al terminar se vuelve al feed y continúa el scroll. Si un comentario queda sin confirmar, el proceso se detiene en esa publicación para revisión.
  - Las capturas OCR temporales se eliminan inmediatamente después de la lectura.
- Pruebas realizadas:
  - OCR real sobre pantalla de 720 × 1512: 19 líneas reconocidas.
  - Tres expresiones visibles de la misma publicación se asociaron con la fecha/hora localizada en `(180, 995)`.
  - El texto de un anuncio anterior fue rechazado porque su fecha/hora no estaba visible dentro del mismo bloque.
  - Los contadores `350`, `73` y `25`, y la hora de la barra del teléfono, fueron rechazados como enlaces de publicación.
  - Prueba reversible real: el toque en `(180, 995)` abrió exactamente la vista `Publicación de Huauchinangue…`; después se regresó al feed.
  - Simulación completa: apertura por fecha, Me gusta, Comentario y retorno al feed en ese orden.
  - Simulación interna de Me gusta: dos desplazamientos y confirmación en el tercer análisis.
  - Simulación interna de Comentario: campo localizado, texto validado por flecha, envío y desaparición de la flecha.
  - Interfaz: ambas acciones desactivadas inicialmente y campo de comentario vacío.
  - Compilación de Python correcta; panel local reiniciado y estable.
- Acciones reales durante pruebas: No se dio Me gusta ni se publicó comentario.
- Referencia de rollback: `_rollback\CHG-20261105-2044`.
- Hash local de `panel.py`: `6AFD60F52B890CFBC9E60B88EF53A7CE2E2A7F71169DD864CA951856CA01A2FB`.
- Hash local de `LEEME.txt`: `F5AC0A1F9B417CFC091EBFCF8EDCDE34EDF2C5F6AFB3445646E6B4216EE2E0B7`.
- Hash local de `herramientas\ocr_windows.ps1`: `B6B7328680CB0AD25EAF59AB786FCC22AE6AA7FC24523F39F355E4C96DE1501D`.
- Publicación remota: No realizada.
- Git/GitHub: No utilizado.

### CHG-20261105-1930 — Finalización del envío de comentario en Reel

- Fecha y hora: 2026-11-05 19:30:47 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Estado: Completado localmente
- Problema observado: El texto se escribió correctamente en el comentario del Reel, pero el proceso se detuvo antes de pulsar la flecha azul.
- Diagnóstico: El último paso sólo usaba la flecha calculada cuando estaba activa la opción general `Clic calculado por figura`; además hacía una sola captura, por lo que podía perder una flecha que apareciera con retraso.
- Implementación:
  - En modo Reel, la presencia de la flecha azul valida que el editor contiene texto independientemente de la opción general de clic calculado.
  - El envío mediante la flecha azul también queda habilitado directamente por el modo Reel.
  - Se realizan hasta tres capturas, separadas por 0.45 segundos, antes de informar que la flecha no fue encontrada.
  - La confirmación posterior aplica la misma regla de Reel para comprobar que la flecha desapareció.
- Verificación real:
  - La flecha pendiente fue detectada en `(659, 1431)`.
  - Se pulsó por solicitud del operador.
  - Facebook mostró `Se publicó tu comentario`, el editor quedó vacío y el comentario apareció en la lista.
- Pruebas técnicas:
  - Captura anterior: flecha localizada correctamente.
  - Captura posterior: la flecha ya no fue detectada.
  - Simulación de aparición tardía: dos capturas sin flecha y éxito en el tercer intento con un único toque.
  - Compilación de Python: correcta.
  - Panel local reiniciado y estable con la corrección.
- Referencia de rollback: `_rollback\CHG-20261105-1930`.
- Hash local de `panel.py`: `F5483B45076E5445958257EDDF5675A22FC28EE226099209187C6A4CDC3C9867`.
- Hash local de `LEEME.txt`: `84AC90A5A048C68F5F511A642C788E12D19B67776D6AAB6C9F1912224C954EA6`.
- Publicación remota: No realizada.
- Git/GitHub: No utilizado.

### CHG-20261105-1916 — Modo Reel en Interacciones

- Fecha y hora: 2026-11-05 19:16:06 (America/Mexico_City)
- Tipo: Funcionalidad solicitada
- Estado: Completado localmente el 2026-11-05 19:21:09 (America/Mexico_City)
- Alcance: Pestaña `Interacciones`, sin alterar el flujo normal de publicaciones.
- Solicitud: Agregar una casilla `Reel` y, al activarla, identificar los controles de Me gusta y Comentario propios de la vista de Reels.
- URL de diagnóstico: `https://www.facebook.com/reel/28054416567568667`.
- Implementación:
  - Se agregó la casilla `Reel`, desactivada inicialmente.
  - Con `Reel` activo, la estructura de Android identifica los bloques pulsables de la columna lateral; el primero corresponde a Me gusta y el segundo a Comentario.
  - Si Android no expone correctamente los bloques, un respaldo visual reconoce las primeras siluetas de acción del costado derecho.
  - Antes de tocar Me gusta se comprueba el color azul para evitar retirar una reacción ya activa; después del toque se intenta confirmar el cambio visual.
  - Comentario abre la bandeja desde el globo lateral y después reutiliza el campo accesible, la escritura verificada y la flecha azul de envío existentes.
  - Con `Reel` desactivado se conserva la ruta anterior para publicaciones, fotos y videos normales.
- Pruebas realizadas:
  - Captura y jerarquía reales del Reel proporcionado, sin ejecutar reacciones ni publicar comentarios.
  - Detección estructural real: Me gusta `(666, 969)` y Comentario `(666, 1113)` en pantalla de 720 × 1512.
  - Respaldo visual real: silueta de Me gusta `(665, 951)` y silueta de Comentario `(665, 1096)`; el Me gusta inactivo no fue confundido con estado azul.
  - Apertura reversible de la bandeja de comentarios: campo `Escribe un comentario…` localizado en `(294, 1413)`; no se escribió texto.
  - Interfaz real en modo de prueba: casilla `Reel` presente y desactivada por defecto.
  - Compilación de Python: correcta.
  - Nueva instancia local del panel iniciada y estable.
- Resultado: Disponible localmente para prueba manual.
- Exclusiones confirmadas: No se ejecutó ningún Me gusta, no se envió ningún comentario y no se modificó la ruta del modo normal.
- Referencia de rollback: `_rollback\CHG-20261105-1916`.
- Hash local de `panel.py`: `DA7015F1201784BC3AC199D6ACD76DD62C25B7182DA9F184F2609F8A694908E3`.
- Hash local de `LEEME.txt`: `487E835E23515003D27A85D38635EAA8B237CE4561EDDA6904E54E34925B433A`.
- Publicación remota: No realizada.
- Git/GitHub: No utilizado.

### CHG-20261105-1235 — Selección combinada de Me gusta y Comentario

- Fecha y hora: 2026-11-05 12:35:02 (America/Mexico_City)
- Tipo: Mejora de interfaz y secuencia solicitada
- Estado: Completado localmente el 2026-11-05 12:36:27 (America/Mexico_City)
- Alcance: Pestaña `Interacciones`.
- Solicitud: Convertir `Me gusta` y `Comentario` en casillas para poder ejecutar ambas acciones sobre el mismo enlace.
- Cambio propuesto:
  - Casillas independientes `Me gusta` y `Comentario`.
  - Un solo botón `Ejecutar acciones seleccionadas`.
  - Si ambas están activas, ejecutar Me gusta y después Comentario con la misma URL y los mismos teléfonos.
  - `Detener proceso` cancela la acción actual y elimina la siguiente acción pendiente.
  - Conservar validaciones, clic calculado y reservas de dispositivos existentes.
- Exclusiones: Sin cambios a la detección interna de figuras o escritura; sin servidor y sin Git.
- Rollback local: `_rollback\CHG-20261105-1235`.
- Implementación:
  - Se reemplazaron los dos botones separados por las casillas `Me gusta` y `Comentario`, activadas inicialmente.
  - Se agregó un único botón `Ejecutar acciones seleccionadas`.
  - Con ambas casillas activas se agenda `Comentario` después de que todos los teléfonos terminen `Me gusta`.
  - La segunda acción usa los mismos campos de URL, comentario, tiempos y dispositivos seleccionados.
  - Si sólo hay una casilla activa, se ejecuta únicamente esa acción.
  - `Detener proceso` elimina `combined_next_action` para que Comentario no comience después de cancelar Me gusta.
- Pruebas realizadas:
  - Compilación de Python: correcta.
  - Creación real de interfaz: dos casillas activas y botón combinado visibles.
  - Secuencia simulada: `Me gusta` terminó y después inició `Comentario`.
  - Cancelación simulada durante Me gusta: la acción Comentario pendiente fue eliminada.
  - No se ejecutaron acciones reales en Facebook durante estas pruebas.
- Resultado: Implementación local lista para prueba manual.
- Publicación remota: No autorizada; el servidor no fue modificado.
- Hash local de `panel.py`: `59CF62AB9C3E67F586E989AE89CD19CC7D8626F29C78A768F2DA138C8B750489`.
- Hash local de `LEEME.txt`: `3E208FE9B3868093AF37C572776812E2F44317B948BAD94D9D54787542D48C18`.
- Git/GitHub: No utilizado.

### CHG-20261105-1142 — Escritura de comentario y flecha azul de envío

- Fecha y hora: 2026-11-05 11:42:37 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Estado: Completado localmente el 2026-11-05 12:23:31 (America/Mexico_City)
- Alcance: Únicamente la escritura y el envío dentro de `Solo Comentario`.
- Problema reportado: El campo se abre y muestra el teclado, pero no recibe texto; el envío se representa mediante una flecha azul sin rótulo accesible.
- Evidencia: Imagen proporcionada por el operador. El teléfono remoto no estaba conectado al iniciar el diagnóstico.
- Cambio propuesto:
  - Sustituir la escritura ASCII indirecta por `adb shell input text` directo como método principal.
  - Verificar que el texto completo aparezca antes de buscar el envío.
  - Conservar ADB Keyboard para Unicode cuando esté instalado, sin alterar silenciosamente acentos o emojis.
  - Detectar por color y geometría una flecha azul en el sector derecho del área de comentario cuando no exista botón accesible.
  - Pulsar la flecha sólo después de confirmar el texto.
- Exclusiones: Sin publicar comentarios reales durante las pruebas técnicas y sin coordenada absoluta fija.
- Rollback local: `_rollback\CHG-20261105-1142`.
- Git/GitHub: No autorizado.
- Implementación:
  - Texto ASCII enviado directamente con `adb shell input text` y espacios codificados como `%s`.
  - Antes de escribir se limpia el campo enfocado con retrocesos, evitando concatenar un borrador anterior.
  - Si la verificación falla, se limpia el borrador parcial y no se intenta publicar.
  - Se agregó reconocimiento HSV de componentes azules pequeños por encima del 80% del ancho para excluir insignias de autores y reacciones.
  - La búsqueda vertical cubre hasta el 98% de la pantalla para reconocer la flecha con teclado abierto o cerrado.
  - La flecha sólo se pulsa después de confirmar que el texto completo aparece en la interfaz.
  - Cuando Facebook no expone el `EditText` ni su contenido, la presencia de la flecha azul activa valida visualmente que el editor contiene texto.
  - Después del toque, la desaparición de la flecha confirma que el editor se vació; si permanece, se conserva la pantalla para revisión.
  - Si el texto continúa después del toque, se informa `no confirmado` y se deja la publicación abierta; ya no regresa al feed.
  - Se conserva ADB Keyboard como requisito seguro para Unicode cuando esté disponible.
- Pruebas realizadas:
  - Escritura física en el teléfono conectado: `Prueba temporal` apareció completo en el buscador de Ajustes, después se borró y se regresó.
  - Primera prueba real: el texto se escribió, pero un detector demasiado amplio confundió la insignia azul del autor en `(427, 1216)` con la flecha.
  - Captura real con teclado abierto: flecha localizada correctamente en `(659, 863)`.
  - Captura real con teclado cerrado: flecha localizada correctamente en `(659, 1429)`.
  - Los filtros nuevos rechazaron la insignia del autor y la tecla azul del teclado.
  - Jerarquía real durante el fallo: Facebook sólo expuso un `FrameLayout` enfocado, sin `EditText` ni texto, aunque el comentario era visible.
  - Flujo simulado con accesibilidad vacía: la flecha activa permitió continuar y su desaparición confirmó el envío.
  - Flujo completo simulado: texto verificado, ausencia de botón accesible y uso correcto de la flecha calculada.
  - Compilación local de Python: correcta.
  - No se publicó ningún comentario real.
- Publicación remota:
  - No autorizada por el operador.
  - Una sincronización iniciada antes de recibir la indicación fue revertida inmediatamente desde `_rollback\CHG-20261105-1142`.
  - Se verificó que `panel.py` y `LEEME.txt` remotos coinciden con sus respaldos y que la versión restaurada compila correctamente.
- Resultado: Corrección disponible únicamente en la copia local.
- Hash local de `panel.py`: `708BCD3FF34C38A71F1E8D798654166A242255BDA752C6FA1DC937B655658361`.
- Hash local de `LEEME.txt`: `6DA5E7F58E600789E6492CDC7A1DCE188AC182A8B2A4BC48ECC3E2E3FE3BBFE6`.
- Git/GitHub: No utilizado.

### CHG-20261104-2324 — Botón para detener Interacciones

- Fecha y hora: 2026-11-04 23:24:38 (America/Mexico_City)
- Tipo: Mejora funcional solicitada
- Estado: Completado el 2026-11-05 10:40:34 (America/Mexico_City)
- Alcance: Procesos `Me gusta` y `Comentario` de la pestaña `Interacciones`.
- Solicitud: Agregar un botón para detener el proceso actual.
- Cambio propuesto:
  - Botón visible `Detener proceso`, habilitado sólo durante una interacción.
  - Cancelación compartida para esperas, calentamiento, desplazamientos, análisis visual y procesamiento por teléfono.
  - Liberación de dispositivos y restauración de botones cuando terminen todos los trabajadores.
  - No afectar búsquedas ni procesos de otras pestañas.
- Exclusiones: Sin cambios funcionales a la detección, Me gusta o publicación de comentarios.
- Rollback local: `_rollback\CHG-20261104-2324`.
- Git/GitHub: No autorizado.
- Implementación:
  - Se agregaron botones identificables para iniciar `Me gusta`, iniciar `Comentario` y `Detener proceso`.
  - Mientras una interacción está activa, ambos botones de inicio quedan deshabilitados y `Detener proceso` queda habilitado.
  - La detención interrumpe esperas, calentamiento, búsqueda visual y desplazamientos mediante `interaction_stop_event`.
  - Si se detiene durante modo avión, primero se envía la orden para desactivarlo.
  - Al terminar todos los teléfonos, se liberan los dispositivos, se restauran los botones y el estado muestra `Detenido` o `Completado`.
  - El cierre del panel también activa la señal de detención.
- Pruebas realizadas:
  - Compilación local de Python: correcta.
  - Creación real de la interfaz: botón inicialmente deshabilitado y habilitado durante el proceso.
  - Cancelación de una espera de 10 segundos: respuesta en 0.078 segundos.
  - Restauración de botones y estado `Detenido`: correcta.
- Publicación remota:
  - Completada el 2026-11-05 mediante WinRM HTTPS.
  - Respaldo creado en `C:\Users\Admin\Desktop\Panel Celulares V2\_rollback\CHG-20261104-2324`.
  - Código, documentación, bitácora y plantillas visuales sincronizados con hashes coincidentes.
  - Compilación remota de Python correcta.
  - El panel estaba cerrado; no se interrumpió ningún proceso.
  - No se modificó la configuración remota y no se accedió a Git.
- Hash local de `panel.py`: `A29FE5141159A640623BB4B7D63D8E5EA694EED4A44322F2091B5392E2A30474`.
- Hash local de `LEEME.txt`: `5402C370C76B7BEA8727D4BF2AD0184B9A3D20E688E0A228C4E5369EDC8F78E9`.

### CHG-20261104-1505 — Scroll extendido para localizar Me gusta

- Fecha y hora: 2026-11-04 15:05:44 (America/Mexico_City)
- Tipo: Ajuste funcional solicitado
- Estado: Completado el 2026-11-04 15:06:49 (America/Mexico_City)
- Alcance: Únicamente la búsqueda de la manita en `Solo Me gusta` con clic calculado.
- Problema: Cada desplazamiento actual recorre cerca de 12% de la pantalla y puede no superar una imagen o video largo.
- Cambio propuesto:
  - En clic calculado, ampliar cada desplazamiento a aproximadamente 48% de la altura útil.
  - Mantener análisis antes del primer desplazamiento y después de cada paso hasta encontrar la figura o completar el valor visible configurado.
  - Conservar el desplazamiento corto en el modo sin clic calculado y no modificar Comentario.
- Exclusiones: Sin clic real durante pruebas, sin coordenada absoluta de botón y sin cambios a otros módulos.
- Rollback local: `_rollback\CHG-20261104-1505`.
- Git/GitHub: No autorizado.
- Implementación:
  - En clic calculado, el gesto comienza al 80% y termina al 32% de la altura, recorriendo aproximadamente 48% por paso.
  - La captura y el reconocimiento se ejecutan antes del primer desplazamiento y después de cada paso.
  - El ciclo se detiene inmediatamente al localizar o confirmar la manita.
  - El número de pasos continúa controlado por `Desplazamientos máximos`; en modo no calculado se conserva el ajuste corto anterior.
  - Comentario no fue modificado.
- Pruebas realizadas:
  - Flujo simulado con manita ausente en dos capturas y presente en la tercera.
  - Resultado: exactamente dos desplazamientos de 48%, reanálisis entre ambos y detención inmediata al encontrarla.
  - Compilación local y remota de Python: correctas.
  - No se ejecutó un Me gusta real durante la prueba.
- Publicación remota:
  - Respaldo creado en `C:\Users\Admin\Desktop\Panel Celulares V2\_rollback\CHG-20261104-1505`.
  - `panel.py` y `LEEME.txt` actualizados; hashes locales/remotos coincidentes.
  - No había una instancia del panel activa.
- Resultado: Ajuste publicado y listo para prueba manual.
- Hash de `panel.py`: `F4AEEAE2FAA51FBC32ECC3499538DAAF344FFF8D4052C191F359AC642F70F137`.
- Hash de `LEEME.txt`: `757A4916562EA0BF9EA1DF918715242FA999BD04493395321FC2B76AF22596D2`.
- Git/GitHub: No utilizado.

### CHG-20261104-1500 — Clic calculado por figura en Interacciones

- Fecha y hora: 2026-11-04 15:00:57 (America/Mexico_City)
- Tipo: Mejora funcional solicitada
- Estado: Completado el 2026-11-04 15:04:54 (America/Mexico_City)
- Alcance: Opciones `Me gusta` y `Comentario` de la pestaña `Interacciones`.
- Solicitud:
  - Agregar una opción de clic calculado que localice visualmente la manita de `Me gusta` y desplace la publicación hasta encontrarla.
  - Considerar que el campo de comentario aparece en la parte inferior de la pantalla.
- Evidencia revisada:
  - Fotografía proporcionada por el operador.
  - Captura ADB real del teléfono conectado: manita en la acción izquierda y globo de comentario en la acción central.
  - La jerarquía accesible actual no publica esos controles, por lo que se requiere respaldo visual.
- Cambio propuesto:
  - Opción visible `Clic calculado por figura`, activada inicialmente.
  - Reconocimiento multiescala por bordes para manita y globo, limitado a la zona lógica de cada acción.
  - Desplazamiento por pasos hasta encontrar la fila de acciones o detectar que la pantalla dejó de avanzar.
  - Detección de color para no desmarcar una manita ya activa.
  - En Comentario, apertura calculada del globo cuando el campo inferior todavía no esté disponible y búsqueda posterior del campo.
- Exclusiones: Sin coordenada fija absoluta, sin cambios a otros módulos y sin reacciones/comentarios reales durante las pruebas técnicas.
- Rollback local: `_rollback\CHG-20261104-1500`.
- Git/GitHub: No autorizado.
- Implementación:
  - Se agregó la opción visible `Clic calculado por figura (manita / comentario)`, activada inicialmente.
  - Se agregó un campo visible de `Desplazamientos máximos`, con valor inicial 8 y rango 0–30; controla sólo la búsqueda visual, no limita acciones.
  - `locate_action_figure` usa bordes Canny, coincidencia multiescala y zonas lógicas horizontales para calcular el centro real de cada figura.
  - `Me gusta` combina accesibilidad y figura; desplaza por pasos hasta encontrarla y comprueba color azul para evitar desmarcarla.
  - `Comentario` localiza el globo cuando `Escribe un comentario` todavía no está disponible, lo abre y busca un `EditText` real por debajo del 62% de la pantalla.
  - Se agregaron `templates/like_outline.png` y `templates/comment_outline.png`, obtenidas de una captura ADB real sin contenido personal dentro del recorte.
  - Se conserva la plantilla anterior como último respaldo y no se agregó una coordenada absoluta de acción.
- Pruebas realizadas:
  - Compilación local y remota de Python: correctas.
  - Interfaz real creada en modo de prueba: opción activada y ocho desplazamientos visibles.
  - Captura real de 720×1512: manita calculada en `(95, 1065)` con 0.99 y globo en `(332, 1065)` con 1.00.
  - Prueba multiescala al 75%, 100% y 125%: ambas figuras localizadas correctamente.
  - Estado azul simulado: reconocido como activo; se evitó un segundo toque.
  - Flujo simulado de Me gusta: un solo clic y confirmación visual.
  - Flujo simulado de Comentario: apertura del globo y selección del `EditText` inferior.
  - No se ejecutaron reacciones ni comentarios reales durante las pruebas.
- Publicación remota:
  - Respaldo creado en `C:\Users\Admin\Desktop\Panel Celulares V2\_rollback\CHG-20261104-1500`.
  - Código, documentación y dos plantillas copiados; hashes locales/remotos coincidentes.
  - No había una instancia del panel activa; no se interrumpió ningún proceso.
- Resultado: Implementación publicada y lista para prueba manual.
- Hash de `panel.py`: `8E1DB24B9E161DD215CFC374C3A5B5727DBF62497976E9B56E4336788AF538EF`.
- Hash de `LEEME.txt`: `548B564ED2D51075D603A7681E5A1140BA52A4B1695B7C5A01301B9CD1669540`.
- Hash de `templates/like_outline.png`: `5D2BDBB87E5FACB71B6F5C9EA1A675A86E0F2A1CC955CB1B83C3F9FF0B6AD69C`.
- Hash de `templates/comment_outline.png`: `0DCA8194D55AF974FA76A2251D787BB84F7804F1B4B6FD34D4A5C5CD68A5AD39`.
- Git/GitHub: No utilizado.

### CHG-20261104-1452 — Corrección de Comentario en Interacciones

- Fecha y hora: 2026-11-04 14:52:11 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Estado: Completado el 2026-11-04 14:54:02 (America/Mexico_City)
- Alcance: Únicamente la opción `Comentario` de la pestaña `Interacciones` y el selector accesible compartido que utiliza.
- Problema: Facebook Lite puede exponer `Escribe un comentario` y `Publicar` como rótulos hijos con `clickable=false`; el flujo actual los descarta aunque el contenedor reciba el toque.
- Cambio propuesto:
  - Aceptar únicamente coincidencias exactas no pulsables para el campo y el botón, manteniendo el rechazo de textos ambiguos.
  - Buscar el campo al abrir y después de hasta dos desplazamientos cortos.
  - Conservar la comprobación del texto antes de pulsar Publicar y no agregar coordenadas fijas.
- Diagnóstico adicional: El teléfono conectado no tiene ADB Keyboard; los textos Unicode continuarán cancelándose de forma segura y los textos ASCII son compatibles.
- Exclusiones: No se instalarán aplicaciones o teclados y no se publicará un comentario real en las pruebas.
- Rollback local: `_rollback\CHG-20261104-1452`.
- Git/GitHub: No autorizado.
- Implementación:
  - El selector accesible puede aceptar rótulos validados no pulsables únicamente cuando el flujo lo solicita expresamente.
  - `Comentario` acepta `Escribe un comentario…` / `Write a comment` aunque sea un nodo hijo con `clickable=false`, sin aceptar textos ambiguos como `Ver comentarios anteriores`.
  - Busca el campo al abrir y, si no está visible, después de hasta dos desplazamientos cortos.
  - El botón exacto `Publicar`, `Enviar comentario`, `Post` o `Send` recibe la misma compatibilidad controlada.
  - Se conserva la verificación del texto antes de publicar, el registro posterior y la ausencia de coordenadas fijas.
- Pruebas realizadas:
  - Compilación local de Python: correcta.
  - Selector simulado: eligió el campo exacto no pulsable e ignoró `Ver comentarios anteriores`.
  - Flujo completo ASCII simulado: abrió la publicación, activó el campo, escribió y verificó el texto, pulsó `Publicar` y comprobó el cambio de pantalla.
  - Resultado del flujo: dos toques exactos y ningún desplazamiento innecesario.
  - No se publicó un comentario real durante las pruebas.
- Publicación remota:
  - Respaldo creado en `C:\Users\Admin\Desktop\Panel Celulares V2\_rollback\CHG-20261104-1452`.
  - `panel.py` y `LEEME.txt` actualizados; hashes locales/remotos coincidentes y compilación remota correcta.
  - No había una instancia del panel activa; no se interrumpió ningún proceso.
- Resultado: Corrección publicada y lista para prueba manual con texto ASCII.
- Observación: El teléfono conectado no tiene ADB Keyboard; los comentarios con acentos, eñes o emojis se cancelan para evitar enviar texto incompleto.
- Hash resultante de `panel.py`: `FA78CCBC67D499D14803149E689EC87509D13C014FD08C676DC24AA7B9C8B069`.
- Hash resultante de `LEEME.txt`: `D0AD7F2DE3081E7AD613ED1467A1A3D62A0F64E08900F0EA497A72CD192C6168`.
- Git/GitHub: No utilizado.

### CHG-20261104-1449 — Corrección de Me gusta en Interacciones

- Fecha y hora: 2026-11-04 14:49:10 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Estado: Completado el 2026-11-04 14:51:20 (America/Mexico_City)
- Alcance: Únicamente la opción `Me gusta` de la pestaña `Interacciones`.
- Problema reportado: La publicación se abre, pero no se aplica `Me gusta`.
- Diagnóstico inicial:
  - La integración descartaba un rótulo exacto `Me gusta` cuando Android lo exponía en un nodo hijo con `clickable=false`, aunque el área respondiera al toque; la primera versión sí aceptaba este caso.
  - El flujo analizaba una sola vez y únicamente después de desplazar la publicación.
  - La plantilla `like.png` representa una reacción circular y no necesariamente coincide con el botón textual actual de Facebook Lite.
- Cambio propuesto:
  - Recuperar la compatibilidad con rótulos exactos no pulsables de la primera versión, conservando la detección de `Quitar Me gusta` para evitar desmarcarlo.
  - Analizar antes y después de desplazamientos pequeños, con intentos limitados y sin coordenada fija de botón.
  - Registrar claramente si el toque fue confirmado, enviado sin confirmación o no se encontró el control.
- Exclusiones: No se modificará Comentario ni otros módulos y no se ejecutará una reacción real durante las pruebas técnicas.
- Rollback local: `_rollback\CHG-20261104-1449`.
- Publicación Git/GitHub: No autorizada.
- Implementación:
  - El rótulo exacto `Me gusta` vuelve a ser utilizable aunque su nodo Android indique `clickable=false`; el toque se dirige a los límites reales de ese rótulo para que lo reciba su contenedor.
  - Se añadieron variantes accesibles actuales `Me gusta, botón` y `Like, button`.
  - Se conserva la detección de `Quitar Me gusta`, `Unlike` y estados seleccionados para no desmarcar una reacción existente.
  - Interacciones analiza antes de desplazar y, si no encuentra el control, repite después de hasta dos desplazamientos cortos.
  - La plantilla visual queda como último respaldo y no se añadió una coordenada fija.
- Pruebas realizadas:
  - Compilación local de Python: correcta.
  - Pruebas simuladas de rótulo hijo no pulsable, variantes español/inglés, estado ya activo y rechazo de texto narrativo: correctas.
  - Flujo completo simulado de la pestaña Interacciones: abrió el enlace, detectó antes del desplazamiento, envió un solo toque, confirmó `Quitar Me gusta` y no usó la plantilla.
  - No se ejecutó una reacción real durante las pruebas técnicas.
- Publicación remota:
  - Respaldo creado en `C:\Users\Admin\Desktop\Panel Celulares V2\_rollback\CHG-20261104-1449`.
  - `panel.py` y `LEEME.txt` actualizados en `C:\Users\Admin\Desktop\Panel Celulares V2`.
  - Hashes locales/remotos coincidentes y compilación remota correcta.
  - Había un teléfono autorizado conectado y ninguna instancia del panel activa; no se interrumpió un proceso.
- Resultado: Corrección publicada y lista para prueba manual.
- Hash resultante de `panel.py`: `5C09806C00C107C7BBB6CAD16AEB2238BA0F0C75B386748A7FC1CE028DE87087`.
- Hash resultante de `LEEME.txt`: `4EE7FAB4FA240273DB33A68D562D73D766AB40BC883FCBBF41B9DF2FB4489682`.
- Git/GitHub: No utilizado.

### CHG-20261104-1245 — Integración segura de Me gusta y comentario

- Fecha y hora: 2026-11-04 12:45:08 (America/Mexico_City)
- Tipo: Corrección funcional solicitada
- Estado: Completado el 2026-11-04 12:52:39 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Autoría: El proyecto y su código original pertenecen a sus autores. Este trabajo integra únicamente los mecanismos solicitados y no reclama autoría sobre el resto del sistema.
- Solicitud:
  - Combinar el detector de `Me gusta` por accesibilidad de la primera versión con el control operativo de `Panel V2`.
  - Corregir el flujo de comentarios para evitar campos, botones y coordenadas ambiguas.
  - Publicar la actualización en `C:\Users\Admin\Desktop\Panel Celulares V2` mediante WinRM para pruebas del operador.
- Cambio propuesto:
  - Acción opcional `Me gusta` dentro de la búsqueda por palabras.
  - Detección accesible de `Me gusta`/`Quitar Me gusta`, sin toque fijo de respaldo.
  - En `Solo Me gusta`, accesibilidad como método principal y plantilla visual sólo como respaldo validado.
  - Comentarios con coincidencias exactas, texto Unicode compatible y comprobaciones antes de enviar.
  - Reserva de dispositivos y serialización de lecturas `uiautomator` para evitar controles simultáneos.
- Exclusiones: No se modificarán los demás módulos; no se ejecutarán comentarios ni reacciones reales durante las pruebas técnicas.
- Archivos previstos: `panel.py`, `LEEME.txt` y `BITACORA.md`.
- Referencia de rollback local: Copia previa identificada con este cambio.
- Referencia de rollback remoto: Copia del archivo remoto antes de reemplazarlo.
- Publicación Git/GitHub: No autorizada; no se accederá a GitHub.
- Implementación:
  - La búsqueda por palabras puede ejecutar opcionalmente `Me gusta` mediante el estado accesible de la publicación, con intervalo mínimo/máximo y cancelación durante la espera.
  - Se distingue `Me gusta` de `Quitar Me gusta` y se evita un segundo toque cuando la publicación ya está marcada.
  - `Solo Me gusta` usa accesibilidad como primera opción y `like.png` como único respaldo; se retiró su coordenada fija.
  - `Solo comentario` usa coincidencias exactas para el campo y el botón de publicación; se retiraron los dos respaldos por coordenadas.
  - El texto del comentario se comprueba antes de publicar. Unicode requiere ADB Keyboard y, si no está disponible, el flujo se cancela sin enviar texto incompleto.
  - Las tareas afectadas reservan cada teléfono y las lecturas de `uiautomator` se serializan para evitar interferencias.
- Pruebas realizadas:
  - Compilación local de `panel.py` con Python: correcta.
  - Jerarquías Android simuladas: reconoce el control real `Botón "Me gusta"`, detecta `Quitar Me gusta`, rechaza texto narrativo como `A Juan le gusta esto` y realiza un solo toque confirmado.
  - Selector de comentario simulado: ignora `Ver comentarios anteriores` y elige `Escribe un comentario`.
  - Entrada de texto simulada: ASCII genera una orden segura; Unicode sin ADB Keyboard se cancela expresamente.
  - No se ejecutaron reacciones ni comentarios reales durante las pruebas.
- Publicación remota:
  - Conexión WinRM HTTPS verificada.
  - Respaldo creado en `C:\Users\Admin\Desktop\Panel Celulares V2\_rollback\CHG-20261104-1245`.
  - `panel.py`, `LEEME.txt` y `BITACORA.md` copiados a `C:\Users\Admin\Desktop\Panel Celulares V2`.
  - Hashes locales y remotos coincidentes y compilación remota de Python correcta.
  - No había una instancia remota del panel activa; no se interrumpió ningún proceso.
- Resultado: Correcto y listo para prueba manual en los teléfonos autorizados.
- Hash resultante de `panel.py`: `5EC6E41BB69CDEF5424D8A013A88157628636F38E5B0DEE043844E52F831F8EB`.
- Hash resultante de `LEEME.txt`: `AB8B41351EBC2F535ACF332D3459DF2C38C4A49B4A479000C0B1E003E3ADAF9F`.
- Git/GitHub: No utilizado por instrucción expresa del operador.

### CHG-20261028-2212 — Retiro de límite no solicitado

- Fecha y hora: 2026-10-28 22:12:29 (America/Mexico_City)
- Tipo: Corrección de alcance
- Estado: Completado el 2026-10-28 22:13:47 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Autoría y alcance: El proyecto no es propiedad del equipo que realiza el ajuste; se retirará toda modificación no solicitada y no se alterarán otras funciones.
- Problema: Se agregó unilateralmente un máximo de 5 acciones `Me gusta` por sesión, configurable hasta 100.
- Solicitud: No agregar límites ni comportamientos que el cliente no haya solicitado.
- Cambio propuesto:
  - Eliminar el campo `Máximo de Me gusta por sesión`.
  - Eliminar su validación y la omisión de acciones al alcanzar el límite.
  - Conservar únicamente búsqueda continua hasta `Detener`, intervalo mínimo/máximo y un toque máximo por coincidencia.
- Archivos modificados: `panel.py`, `LEEME.txt` y `BITACORA.md`.
- Publicación remota: No autorizada; no se accederá a GitHub.
- Implementación:
  - Se eliminó el campo `Máximo de Me gusta por sesión` y sus valores 5–100.
  - Se eliminó su lectura, validación, parámetro del trabajador y condición de omisión.
  - La búsqueda continua conserva el intervalo solicitado y termina al pulsar `Detener`.
  - El resumen mantiene un contador informativo de acciones realmente enviadas, sin usarlo como límite.
- Pruebas realizadas:
  - Validación de sintaxis mediante AST.
  - Comprobación automática de ausencia de `search_max_like_actions_var` en el código y la interfaz.
  - Sesión simulada con dos coincidencias: ambas ejecutaron la acción y sólo finalizó por el evento manual de detención.
  - El resumen final registró dos acciones enviadas sin aplicar un tope añadido.
- Resultado: Correcto. Se retiró completamente la restricción no solicitada sin modificar las funciones requeridas.
- Hash resultante de `panel.py`: `A7E854BA6FEC8E55EF0A3A1FE351EA45F65192DF9D412A2C30565F18C3FE771B`.
- Hash resultante de `LEEME.txt`: `7AC72DAB04455BB7EDE7391D514778BF678C23FB7F0A59DE8F77A1E3B951B4AD`.
- Commit resultante: Pendiente por instrucción del operador; no se creó ni publicó un commit para este cambio.

### CHG-20261028-2209 — Búsqueda continua hasta detención manual

- Fecha y hora: 2026-10-28 22:09:13 (America/Mexico_City)
- Tipo: Corrección de ciclo de búsqueda
- Estado: Completado el 2026-10-28 22:10:43 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Problema: Después de la primera coincidencia el trabajador ejecuta `search_stop_event.set()` y finaliza, aunque el operador requiere mantenerlo activo.
- Solicitud: Continuar la búsqueda hasta que el operador pulse `Detener`.
- Controles que se conservarán:
  - Máximo configurable de acciones `Me gusta` por sesión.
  - Un toque máximo por coincidencia.
  - Intervalo mínimo/máximo y cancelación durante la espera.
  - Omisión de la misma pantalla coincidente para evitar procesamiento consecutivo duplicado.
- Cambio propuesto:
  - Agregar modo `Continuar hasta pulsar Detener`, activado inicialmente.
  - Registrar cada coincidencia y seguir con el siguiente desplazamiento.
  - Mantener el límite de desplazamientos para el modo no continuo.
  - Finalizar el proceso continuo únicamente por `Detener`, cierre del panel o error de infraestructura no recuperable.
- Archivos modificados: `panel.py`, `LEEME.txt` y `BITACORA.md`.
- Publicación remota: No autorizada; no se accederá a GitHub.
- Implementación:
  - Se agregó `Continuar buscando hasta pulsar Detener`, activado inicialmente.
  - En modo continuo ya no se llama `search_stop_event.set()` al encontrar una coincidencia.
  - Cada coincidencia se publica inmediatamente en Resultados y luego continúa el desplazamiento.
  - Se agregó `Máximo de Me gusta por sesión`, con valor inicial 5 y rango de 1 a 100.
  - Al alcanzar el límite, la búsqueda continúa pero informa `sin toque`.
  - Se conserva el modo no continuo para detenerse en la primera coincidencia cuando el operador necesite revisar o copiar un enlace.
  - Se conservan hasta 1,000 huellas de pantallas coincidentes para evitar el procesamiento consecutivo repetido.
- Pruebas realizadas:
  - Validación de sintaxis mediante AST.
  - Sesión continua simulada con dos coincidencias y detención manual después del segundo desplazamiento.
  - Con límite de una acción: primera coincidencia ejecutó una acción y la segunda continuó sin toque.
  - El resumen final registró dos coincidencias y sólo terminó al activar el evento `Detener`.
  - Modo no continuo: terminó en la primera coincidencia sin ejecutar scroll adicional.
  - Creación real de la interfaz: modo continuo activado, límite inicial 5 y botón `Detener` visibles.
- Resultado: Correcto. En modo continuo la búsqueda permanece activa hasta la detención manual, conservando el límite de acciones.
- Hash resultante de `panel.py`: `7E87C96D0F964863093A94BD2CE5B15CFD16E3337AC702717260C1124F88A3BF`.
- Hash resultante de `LEEME.txt`: `002FC9442136881422C149F7C7F6E60A487866B14AD1951CB6A58CF2D930C5A2`.
- Commit resultante: Pendiente por instrucción del operador; no se creó ni publicó un commit para este cambio.

### CHG-20261028-2206 — Compatibilidad con etiqueta accesible de Facebook

- Fecha y hora: 2026-10-28 22:06:49 (America/Mexico_City)
- Tipo: Corrección de acción `Me gusta`
- Estado: Completado el 2026-10-28 22:07:24 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Diagnóstico: Facebook expone el control como `Botón "Me gusta". Toca dos veces y mantén presionado para reaccionar al comentario.` y no como la etiqueta exacta `Me gusta`; por eso la búsqueda terminaba con `control exacto no encontrado; sin toque`.
- Cambio propuesto:
  - Reconocer la descripción accesible que comienza exactamente con `Botón "Me gusta"` además de las etiquetas breves existentes.
  - Exigir que la descripción extendida corresponda a un nodo visible, habilitado y pulsable.
  - Seguir rechazando `Quitar Me gusta`, estados seleccionados y frases genéricas.
- Archivos modificados: `panel.py`, `LEEME.txt` y `BITACORA.md`.
- Publicación remota: No autorizada; no se accederá a GitHub.
- Implementación:
  - Se aceptan `Me gusta`, `Like`, `Botón "Me gusta"...` y su variante observada con carácter de reemplazo en `Bot�n`.
  - La descripción extendida sólo se admite en nodos `clickable=true`, visibles, habilitados y con límites válidos.
  - Se ampliaron las detecciones de `Quitar Me gusta`/`Unlike` para conservar la omisión de reacciones ya aplicadas.
- Pruebas realizadas:
  - Validación de sintaxis mediante AST.
  - XML con la descripción exacta observada en el Moto E6 Play: detectó el centro `(84, 1070)`.
  - XML negativos: rechazó `A Juan le gusta esto` y una descripción extendida no pulsable.
  - Estados `selected=true` y `Botón "Quitar Me gusta"`: ambos se clasificaron como ya marcados.
  - Lectura física no invasiva de `ZE222HSLC9`: el control actual se detectó como disponible en `(84, 1070)`; no se envió toque.
  - Acción simulada: generó exactamente un comando de toque con las coordenadas detectadas.
- Resultado: Correcto. La acción reconoce la etiqueta real de Facebook conservando filtros de seguridad.
- Hash resultante de `panel.py`: `5829DEF63C84AB61BAD487C4932E17DCB0498E538FE23D4434CD9B24CFF79261`.
- Hash resultante de `LEEME.txt`: `430E82AB59A10B5223C4DFFAA905345678F2BE0E35CA70F51F48BD6514813CA1`.
- Commit resultante: Pendiente por instrucción del operador; no se creó ni publicó un commit para este cambio.

### CHG-20261028-2201 — Intervalo operativo mínimo/máximo

- Fecha y hora: 2026-10-28 22:01:03 (America/Mexico_City)
- Tipo: Ajuste solicitado por el cliente
- Estado: Completado el 2026-10-28 22:01:39 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Autoría: Se conserva la autoría del proyecto original; el ajuste se limita a parametrizar la espera de la acción existente.
- Aclaración del operador: El intervalo aleatorio forma parte del comportamiento solicitado por el cliente y no tiene como propósito ocultar o disimular la automatización.
- Cambio propuesto:
  - Sustituir la espera fija por campos `Mínimo` y `Máximo`, ambos de 1 a 60 segundos.
  - Validar que el mínimo no sea mayor que el máximo.
  - Elegir una sola espera entera dentro del rango al encontrar una coincidencia.
  - Mostrar y registrar el valor elegido; conservar cancelación y límite de un toque.
- Archivos modificados: `panel.py`, `LEEME.txt` y `BITACORA.md`.
- Publicación remota: No autorizada; no se accederá a GitHub.
- Implementación:
  - Se sustituyó el campo fijo por `Mínimo` y `Máximo`, con valores iniciales 3 y 8.
  - Ambos campos aceptan enteros de 1 a 60 y el inicio rechaza mínimo mayor que máximo.
  - Al encontrar la coincidencia se elige una vez un entero del rango inclusivo mediante `random.randint`.
  - La cuenta regresiva, el resultado y la bitácora operativa muestran la espera elegida; `Detener` conserva la cancelación sin toque.
- Pruebas realizadas:
  - Validación de sintaxis mediante AST.
  - Rango simulado 3–8 forzado a 6: se verificó la llamada exacta `randint(3, 8)`, espera 6 y un solo toque.
  - Cancelación con espera elegida de 8: cero llamadas a la acción y resultado `sin toque`.
  - Creación real de la pestaña en 1050 × 850: los rótulos Mínimo, Máximo y el rango 1–60 están visibles.
- Resultado: Correcto. La acción usa una espera elegida dentro de los dos límites definidos por el operador.
- Hash resultante de `panel.py`: `C155F69ED811036570E1D1CAC3684F25BB232D474DEEAA5C91DB145F09DE4BB9`.
- Hash resultante de `LEEME.txt`: `599347B5746854AB153399592169D2DEBE1A07024B6ACFFE1DF45BB4E00FE621`.
- Commit resultante: Pendiente por instrucción del operador; no se creó ni publicó un commit para este cambio.

### CHG-20261028-2157 — Visibilidad del campo de espera

- Fecha y hora: 2026-10-28 21:57:00 (America/Mexico_City)
- Tipo: Corrección de interfaz
- Estado: Completado el 2026-10-28 21:58:21 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Problema: El operador no identifica el campo para configurar la espera de 1 a 60 segundos.
- Causa: El campo quedó al final de la misma fila que una descripción larga y sólo se rotuló como `Espera fija`.
- Cambio propuesto: Colocar el campo en una fila independiente con el rótulo `Tiempo antes de ejecutar` y mostrar expresamente `permitido: 1 a 60 segundos`.
- Alcance: Sólo distribución y claridad visual; no cambia la espera, cancelación ni límite de un toque.
- Archivos modificados: `panel.py` y `BITACORA.md`.
- Publicación remota: No autorizada; no se accederá a GitHub.
- Implementación: El control se movió a una fila independiente con etiqueta en negritas, campo más ancho y rango permitido visible en azul.
- Pruebas realizadas:
  - Validación de sintaxis mediante AST.
  - Apertura real de la pestaña de búsqueda en una instancia de prueba de 1050 × 850.
  - Comprobación de que etiqueta, campo y rango están mapeados dentro de la ventana.
  - Posición vertical verificada: 365 de 845 píxeles; no queda oculto al pie del panel.
  - Valor inicial verificado: 3 segundos.
- Resultado: Correcto. El campo y el rango `1 a 60` quedan visibles en una fila propia.
- Hash resultante de `panel.py`: `5E5584F9CA33F05B51E6016E8DCFEABD235A19300566604C3C4B2D46CF860310`.
- Commit resultante: Pendiente por instrucción del operador; no se creó ni publicó un commit para este cambio.

### CHG-20261028-2155 — Espera controlada antes de “Me gusta”

- Fecha y hora: 2026-10-28 21:55:30 (America/Mexico_City)
- Tipo: Control temporal de acción
- Estado: Completado el 2026-10-28 21:56:13 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Autoría: El código original pertenece a sus autores; este ajuste se limita a envolver la acción opcional existente sin reclamar autoría ni alterar otras funciones.
- Solicitud: Incorporar un intervalo de tiempo antes de ejecutar la acción `Me gusta`.
- Cambio propuesto:
  - Agregar una espera fija configurable entre 1 y 60 segundos.
  - Mostrar el tiempo pendiente en el estado de la búsqueda.
  - Permitir cancelar durante la espera con el botón `Detener`.
  - Conservar el máximo de un toque por coincidencia y registrar el resultado.
- Exclusión intencional: No se implementará aleatoriedad destinada a simular comportamiento humano o evadir detección.
- Archivos modificados: `panel.py`, `LEEME.txt` y `BITACORA.md`.
- Referencia de rollback: Estado local documentado en `CHG-20261028-1816`; último commit autorizado disponible `b2f6f15`.
- Publicación remota: No autorizada; no se accederá a GitHub.
- Implementación:
  - Se añadió `Espera fija` junto a la acción `Me gusta`, con valor inicial de 3 segundos y rango de 1 a 60.
  - El estado muestra una cuenta regresiva en segundos después de encontrar la coincidencia.
  - La espera utiliza el mismo evento de detención de la búsqueda; `Detener` cancela antes del toque.
  - El resultado diferencia entre toque enviado y acción cancelada sin toque.
- Pruebas realizadas:
  - Validación de sintaxis mediante AST.
  - Espera simulada completada respetando el tiempo solicitado.
  - Cancelación simulada inmediata de una espera de 10 segundos.
  - Ciclo completo con espera de 7 segundos: se llamó una vez a la acción.
  - Ciclo cancelado: se verificó que no se llamara a la acción y que el resultado indicara `sin toque`.
  - Creación real de la interfaz: valor inicial `3` y acción `Me gusta` apagada.
- Resultado: Correcto en pruebas controladas. No se envió ninguna reacción real durante la validación.
- Hash resultante de `panel.py`: `9DDADA10DF8B987870BF89F0B814972E2CE1CDB054992A854AC0B95245EF6D36`.
- Hash resultante de `LEEME.txt`: `C8A0687CAA2ABE30A25D86FA2246A85E46477C70EC394073149A010FCE78F695`.
- Commit resultante: Pendiente por instrucción del operador; no se creó ni publicó un commit para este cambio.
- Rollback: Restaurar el estado local anterior documentado en `CHG-20261028-1816` cuando el operador autorice el procedimiento.

### CHG-20261028-1816 — Acción opcional “Me gusta” en coincidencias

- Fecha y hora: 2026-10-28 18:16:03 (America/Mexico_City)
- Tipo: Acción de búsqueda controlada
- Estado: Completado el 2026-10-28 18:17:04 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Solicitud: Agregar como acción de una coincidencia el toque de la manita con dedo arriba (`Me gusta`).
- Cambio propuesto:
  - Agregar una casilla independiente, desactivada inicialmente.
  - Buscar únicamente controles accesibles con etiqueta exacta `Me gusta` o `Like`.
  - No tocar controles etiquetados `Quitar Me gusta`, `Unlike` o coincidencias parciales.
  - Ejecutar como máximo un toque por coincidencia y registrar éxito, omisión o ausencia del control.
- Riesgo y control: La acción cambia el estado de una publicación en Facebook; sólo se ejecutará cuando el operador la seleccione expresamente antes de iniciar la búsqueda.
- Exclusiones intencionales: No usar coordenadas fijas, reconocimiento visual incierto, bucles de reacciones ni mecanismos para evadir detección.
- Archivos modificados: `panel.py`, `LEEME.txt` y `BITACORA.md`.
- Referencia de rollback: Estado local documentado en `CHG-20261028-1813`; último commit autorizado disponible `b2f6f15`.
- Publicación remota: No autorizada; no se accederá a GitHub.
- Comprobación previa: El teléfono fue detectado, pero la lectura de jerarquía devolvió `Error ADB`; no se envió ningún toque.
- Implementación:
  - Se agregó la casilla `Dar "Me gusta" al encontrar la coincidencia`, desactivada inicialmente.
  - El filtro acepta únicamente las etiquetas accesibles exactas `Me gusta` y `Like`.
  - Los estados `Quitar Me gusta`, `Unlike`, `Remove Like`, `selected=true` y `checked=true` se consideran ya marcados y no generan toque.
  - La acción envía como máximo un toque y agrega su resultado al bloque de la coincidencia.
- Pruebas realizadas:
  - Validación de sintaxis mediante AST.
  - XML simulado: aceptó `Me gusta` exacto y rechazó `A Juan le gusta esto`.
  - XML simulado: reconoció como ya marcados `Quitar Me gusta` y un control `selected=true`.
  - Arnés de acción: envió un solo toque al control exacto y ninguno al estado ya marcado.
  - Ciclo completo simulado: la acción se ejecutó una vez y el resultado quedó visible en la coincidencia.
  - Creación real de la interfaz: la nueva acción aparece apagada inicialmente.
- Resultado: Correcto en pruebas controladas. No se realizó una reacción real durante la validación.
- Limitación física: La jerarquía del teléfono no pudo leerse antes de la implementación por `Error ADB`; el panel no adivina coordenadas si la etiqueta no está disponible.
- Hash resultante de `panel.py`: `01073FE38428009035644172CAA59F0228102138E22F7FC15B3DDE378B8ADB58`.
- Hash resultante de `LEEME.txt`: `E762424AC22CCB9540232CDC05F23A222A4B078AEB0B9F6ED1767A8EF7AA4CA0`.
- Commit resultante: Pendiente por instrucción del operador; no se creó ni publicó un commit para este cambio.
- Rollback: Restaurar el estado local anterior documentado en `CHG-20261028-1813` cuando el operador autorice el procedimiento.

### CHG-20261028-1813 — Acciones de coincidencia y registro diario de enlaces

- Fecha y hora: 2026-10-28 18:13:50 (America/Mexico_City)
- Tipo: Mejora de búsqueda y trazabilidad operativa
- Estado: Completado el 2026-10-28 18:15:19 (America/Mexico_City)
- Responsable: Codex, bajo solicitud del propietario
- Solicitud: Agregar acciones a la búsqueda; como primera acción, guardar el enlace encontrado en un archivo de registro separado por día.
- Cambio propuesto:
  - Mostrar una acción configurable al iniciar la búsqueda para registrar coincidencias.
  - Conservar el contexto de la coincidencia: hora, celular, palabras y vista previa.
  - Permitir capturar o pegar el enlace y guardarlo en un CSV diario.
  - Evitar registros duplicados del mismo enlace dentro del archivo del día.
  - Permitir abrir el registro correspondiente al día actual desde el panel.
- Privacidad: Los registros diarios serán datos operativos locales y se excluirán del control de versiones.
- Exclusiones intencionales: No abrir Compartir, no copiar enlaces automáticamente desde Facebook y no publicar, comentar ni reaccionar.
- Archivos modificados: `panel.py`, `LEEME.txt`, `.gitignore` y `BITACORA.md`.
- Referencia de rollback: Commit local anterior `b2f6f15`.
- Publicación remota: No autorizada en este momento; no se accederá a GitHub.
- Implementación:
  - Se añadió la acción seleccionable `Preparar el enlace para guardarlo en el registro diario`, activada de forma predeterminada.
  - La búsqueda conserva como contexto el dispositivo, las palabras coincidentes y una vista previa cuando se detiene.
  - `Capturar portapapeles` guarda automáticamente el enlace si existe una coincidencia pendiente; `Guardar enlace` permite confirmar uno pegado manualmente.
  - Cada día usa `registros_busqueda/enlaces_AAAA-MM-DD.csv` con fecha y hora, serie, nombre del dispositivo, palabras, enlace y vista previa.
  - Se evita repetir el mismo enlace dentro del CSV del día y se añadió `Abrir registro de hoy`.
  - La carpeta de registros se agregó a `.gitignore` para mantener los datos operativos fuera del código versionado.
- Pruebas realizadas:
  - Validación de sintaxis mediante AST y revisión de `git diff --check`.
  - Creación del CSV en una carpeta temporal y validación de los seis campos registrados.
  - Segundo intento con el mismo enlace; el archivo conservó un solo renglón de datos.
  - Ciclo simulado de búsqueda; entregó correctamente dispositivo, palabra y vista previa a la acción diaria.
  - Creación real de la interfaz y validación de que la acción aparece activada inicialmente.
- Resultado: Correcto. El enlace de una coincidencia puede quedar registrado por día después de capturarlo o confirmarlo manualmente.
- Hash resultante de `panel.py`: `FE4C5C4C60E849ABD8158B4F283282CD8AF151648A0D11C5E110C064802C4216`.
- Hash resultante de `LEEME.txt`: `9A46C76F21F0848D4662CBEA7870243843D8733C91330840C4F315C97914B2B7`.
- Hash resultante de `.gitignore`: `B082D3883E6ADAC3AEF4919F82E82C06D2772C4E9CBBBFA75ECC024425CAAC55`.
- Commit resultante: Pendiente por instrucción del operador; no se creó ni publicó un commit para este cambio.
- Rollback: Restaurar el estado local anterior identificado por `b2f6f15` usando el procedimiento de control de versiones cuando el operador lo autorice.

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

