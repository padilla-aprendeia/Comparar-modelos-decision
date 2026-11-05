# Modelo a modelo · Laboratorio municipal

Aplicación local para comparar modelos de decisión y modelos de lenguaje al clasificar solicitudes **sintéticas** de un ayuntamiento ficticio. Es un experimento, no una prueba de aptitud para tramitar solicitudes reales sin supervisión. La interfaz toma como referencia `Plantilla.html`; no utiliza sus resultados simulados.

## Distribución

El repositorio contiene únicamente el código, los datos de ejemplo y las dependencias: **no contiene ni descarga modelos de Ollama, resultados previos ni credenciales**. Por tanto, se puede compartir por GitHub sin obligar a nadie a descargar los modelos que use quien lo publica.

Cada persona que clone el repositorio necesita:

- Windows 11, Python 3.11 o posterior y Ollama instalados.
- Ollama en ejecución en su equipo.
- Al menos un modelo local que Ollama identifique con la capacidad `decision` para que aparezca automáticamente como ficha seleccionable. Los modelos de lenguaje general son opcionales.

Al abrir la aplicación, esta consulta la instancia local de Ollama de cada usuario. Las fichas muestran exclusivamente sus propios modelos de decisión instalados; el botón **Actualizar** vuelve a realizar la detección. Si no hay modelos de decisión instalados, la aplicación se abre igualmente, pero no se podrá iniciar una prueba hasta instalar o seleccionar un modelo compatible.

## Requisitos e instalación en Windows 11

Necesitas Python 3.11 o posterior (se ha probado con Python 3.14), Ollama instalado y, para ejecutar una prueba, modelos ya registrados en Ollama. Abre PowerShell en esta carpeta y ejecuta:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app:app --host 127.0.0.1 --port 8765
```

Si no tienes Python 3.14, usa `py -3 -m venv .venv`. Abre **http://127.0.0.1:8765** en el navegador. Mantén abierta la terminal y pulsa **Ctrl+C** para detener el servidor. No uses varios procesos de Uvicorn: cada proceso tiene su propio control de ejecución. La aplicación se vincula solo a la interfaz local y no cambia la instalación de Ollama.

En VS Code: abre esta carpeta con **Archivo → Abrir carpeta**, selecciona `.venv\Scripts\python.exe` mediante **Python: Select Interpreter**, abre una terminal integrada y ejecuta el último comando anterior. Detén con Ctrl+C en esa terminal. Para ejecutar las pruebas: `.\.venv\Scripts\python -m pytest -q`.

## Preparar Ollama y los modelos

Inicia Ollama y usa el valor predeterminado `http://127.0.0.1:11434`. La aplicación consulta `/api/tags` y `/api/version`; **Actualizar** repite la consulta. Por seguridad solo admite una dirección HTTP de loopback (`localhost`, `127.0.0.1` o `::1`), con puerto configurable. Si no responde, inicia Ollama, comprueba que el puerto sea correcto y vuelve a actualizar. No se descarga ningún modelo ni se modifica configuración ni variables de Ollama.

La lista procede de la instancia activa, no del contenido de `F:\IA`: un archivo presente en disco que no esté registrado en esa instancia no aparece. La aplicación no determina la ruta de almacenamiento activa. Las fichas se crean automáticamente con los modelos locales que Ollama declara con la capacidad `decision`; muestran su nombre, tamaño y capacidades reales. Por ello el repositorio no incluye ni descarga modelos y cada persona ve solamente los que ya tiene instalados. Los modelos remotos detectados mediante metadatos o etiqueta cloud no se ofrecen para ejecución local. Un modelo sin esa capacidad se puede seleccionar de forma excepcional en «Otro modelo local», pero su compatibilidad se comprueba durante la ejecución. Una capacidad declarada no garantiza que el modelo vaya a responder correctamente.

Según la documentación de Ollama, `/v1/systemone` precisa la versión 0.35.0 o posterior para modelos locales y acepta de 2 a 26 opciones `choice`. No todos los modelos pueden usar ese endpoint o los formatos estructurados: los fallos se registran y los demás continúan. Las opciones de temperatura y semilla se envían solo al LLM; System One no admite controles de generación. `keep_alive` se envía a Ollama. La compatibilidad con la GPU y el controlador depende también de Ollama y de cada modelo; una respuesta correcta no demuestra que se usara la GPU en exclusiva.

Cada modelo local realiza primero una petición sintética de calentamiento, fuera del conjunto evaluado y con los mismos criterios e interfaz. Se usa `keep_alive=-1`; después la aplicación consulta `/api/ps`, registra memoria y VRAM declaradas, y solo inicia los casos si Ollama confirma la residencia. Verifica la residencia antes y después de cada caso. Al terminar solicita la descarga y la confirma antes de pasar al siguiente. El tiempo de preparación se guarda por separado. Un fallo de preparación se registra y deja los casos sin intentar; si no se confirma la descarga, se detiene la ejecución. La cancelación espera la petición activa e intenta descargar el modelo. Ante un cierre abrupto del proceso puede quedar cargado: usa `ollama ps` y `ollama stop NOMBRE` si corresponde.

Si otro modelo figura cargado en Ollama, la prueba se detiene sin descargarlo automáticamente. Cierra los demás usos de Ollama antes de empezar. La consulta de residencia no bloquea otros clientes ni demuestra que no hubiera una descarga y recarga entre comprobaciones; tampoco demuestra ausencia de procesos externos en GPU ni que el modelo esté enteramente en VRAM. Para comparaciones fiables evita otras cargas y revisa `size`, `size_vram` y `context_length` en los eventos exportados. Un modelo ya cargado al principio se registra como tal y se descarga al terminar. La prueba de calentamiento también afecta a cachés y estado: no interpretes sus tiempos como fríos. La etiqueta de fecha anterior declarada por el usuario ya no se utiliza.

### Dirección local y latencia

La aplicación usa `127.0.0.1` para evitar una demora de resolución o conexión IPv6 observada con `localhost` en Windows. Si introduces `http://localhost:PUERTO`, se usa la dirección IPv4 equivalente y se conserva el puerto; si Ollama escucha solo en IPv6, configura explícitamente `http://[::1]:PUERTO`. La URL efectiva se guarda en cada nueva ejecución. Los resultados antiguos conservan el tiempo medido originalmente y no se corrigen retroactivamente.

## Jev de TypeSafe AI

Opcional: copia `.env.example` a `.env`, abre el archivo en un editor e introduce `JEV_API_KEY` y, si lo deseas, `JEV_MODEL` con un identificador o alias disponible en tu cuenta de TypeSafe. Reinicia el servidor después de modificarlo. El archivo `.env` contiene la clave **en texto claro**: no lo compartas ni lo subas a repositorios. `.gitignore` lo excluye de Git. La clave no se envía al navegador, ni se almacena en la base de datos o la configuración de la ejecución.

Selecciona explícitamente **Incluir Jev** antes de iniciar. Solo entonces se envían a `https://api.typesafe.ai/v1/systemone` los textos sintéticos, el catálogo y las instrucciones; no se envían los identificadores, la respuesta esperada, la dificultad ni columnas adicionales. Es una llamada de pago según las condiciones de TypeSafe y requiere conexión a Internet y una clave válida. El alias por defecto `jev-latest` puede cambiar con el tiempo: para reproducibilidad utiliza un identificador de versión concreto disponible en tu cuenta. La respuesta completa se conserva, incluido el identificador de modelo que devuelva el proveedor. Jev no se ha probado con una clave real en esta entrega.

## Datos y catálogo

Carga un `.xlsx` o `.csv` UTF-8 con estas columnas exactas:

| ID | Solicitud | Departamento esperado | Dificultad |
| --- | --- | --- | --- |
| 001 | Una farola de la plaza está apagada. | alumbrado | Baja |

Los ID deben ser únicos y no vacíos, la solicitud debe contener texto y el departamento esperado debe coincidir exactamente, incluidas mayúsculas, con un código del catálogo. La dificultad puede dejarse vacía. Las columnas adicionales se ignoran. Los ID con ceros iniciales deben estar guardados como texto en Excel. Se informa de los errores de filas antes de ejecutar.

**Archivo incluido:** los códigos de departamento deben coincidir exactamente con el catálogo; en la versión actual se usa `estadistica`. Si modificas el catálogo, vuelve a validar el archivo.

## Uso y resultados

1. Comprueba la conexión y selecciona al menos un modelo. El LLM y Jev son opcionales. Los modelos se procesan secuencialmente, una solicitud por petición.
2. Edita el catálogo, abre **Esquema de preguntas** y modifica el JSON si lo deseas. Después selecciona el archivo validado y define repeticiones y parámetros.
3. Inicia la prueba. El progreso muestra modelo, ID, peticiones completadas y estado. **Cancelar** espera a que acabe o expire la petición en curso; los resultados ya guardados se conservan. Si se interrumpe el proceso, la ejecución queda marcada como interrumpida al iniciar de nuevo. Se puede consultar en el historial.
4. Revisa métricas, desglose, matriz de pares esperado/obtenido y casos individuales. Exporta el CSV y la configuración JSON. Esta última incluye las solicitudes, por lo que debe tratarse como el archivo de entrada. El CSV antepone un espacio a texto que pudiera interpretarse como fórmula en Excel.

La respuesta de evaluación (`Departamento esperado`), la dificultad, el ID y las columnas adicionales nunca se incluyen en las peticiones. El texto es dato y se instruye a los modelos para que no sigan instrucciones contenidas en él; esto reduce, pero no elimina, el riesgo de instrucciones adversarias. Los LLM reciben el catálogo y devuelven JSON validado con un solo código; respuestas ambiguas o fuera de catálogo son inválidas, no se corrigen.

### Esquema editable

En Preparación, abre **Esquema de preguntas** para editar el JSON enviado como `questions` a los modelos de decisión. Se admiten las dos preguntas existentes: `departamento` de tipo `choice` y `claridad` de tipo `score`. Puedes editar sus instrucciones, las descripciones de las opciones y entre 2 y 10 niveles ordenados de puntuación. Los códigos de las opciones deben coincidir exactamente con el catálogo; usa **Actualizar criterios desde el catálogo** para regenerarlos, lo que sustituye las descripciones editadas en el JSON. El esquema se valida antes de iniciar y se conserva en la configuración exportada.

La solicitud de cada fila se inserta automáticamente como dato de entrada; el ID, la referencia y la dificultad no se incorporan. El LLM recibe los mismos textos y opciones mediante sus mensajes y un esquema JSON equivalente, no la API `choice`/`score`. Cambiar instrucciones o criterios puede alterar la clasificación y debilitar las reglas frente a instrucciones incluidas en las solicitudes; conserva criterios equivalentes si comparas ejecuciones.

### Claridad, confianza y score

La pregunta adicional `claridad` es un `score` ordinal de 0 a 4 por defecto para modelos de decisión; si se cambia el número de niveles, la escala termina en el último índice. Se solicita al LLM un entero en la misma escala. `Modelo_pregunta.json` muestra el esquema. Valora la claridad aparente del caso para identificar un destino: **no es la probabilidad de que la clasificación sea correcta**, ni valida la decisión. En System One se guarda la distribución, la media ponderada y `confidence` tal como se reciben, junto con la respuesta completa; `confidence` mide la concentración de la distribución según el proveedor. En el LLM es una autoevaluación, no necesariamente comparable ni calibrada. La elección de `revision_manual` sigue los criterios, no un umbral automático de score.

### Interpretación de métricas

- Precisión válida = aciertos / respuestas válidas. Porcentaje sobre previstas = aciertos / todas las solicitudes previstas, incluso las no intentadas tras una cancelación.
- Los errores de clasificación son respuestas válidas distintas de la referencia; respuestas inválidas y fallos técnicos se cuentan aparte. Cada caso se guarda con sus reintentos y errores.
- Cada duración mide desde el inicio de la primera petición hasta la recepción completa, incluidos reintentos. La suma por modelo excluye preparación y descarga; la mediana, el p95 y las solicitudes/minuto emplean solamente mediciones locales verificadas (o peticiones de Jev, identificadas como remotas). Las ejecuciones anteriores sin control de residencia no se tratan como tiempos verificados. El CSV conserva cada tiempo y su marca; la configuración JSON incluye los eventos de preparación y descarga.
- La matriz usa respuestas válidas; el desglose indica muestra pequeña con menos de 10 respuestas válidas. Las comparaciones no sostienen conclusiones generales si hay pocos casos.
- El protocolo mide modelos residentes tras una consulta de calentamiento, no una ejecución en frío. Jev es remoto: no se puede controlar su carga y sus tiempos incluyen red. La primera inferencia y la preparación pueden diferir entre proveedores.

SQLite permite guardar cada respuesta en una transacción, consultar ejecuciones anteriores y sobrevivir a una interrupción sin mantener un servidor de base de datos. `experimentos.sqlite3` contiene solicitudes y resultados en claro en esta carpeta; protege el acceso a ella y haz copias si necesitas conservarlos. La configuración, instrucciones, fecha UTC, parámetros, versión y metadatos detectados se guardan con cada ejecución.

## Comprobaciones realizadas

- Pruebas automatizadas: validación de Excel/CSV, catálogo, respuestas, métricas, indisponibilidad de Ollama y ejecución/exportación con conector simulado.
- En el equipo se detectó Ollama 0.40.14 y NVIDIA GeForce RTX 4070. Las pruebas funcionales no son una evaluación de precisión. La disponibilidad de modelos puede cambiar.
- La inspección visual automatizada del navegador integrado no estuvo disponible. Jev está pendiente de prueba con credenciales del usuario.

## Referencias

- [Ollama: modelos de decisión y formato de respuesta](https://docs.ollama.com/capabilities/decision)
- [Ollama: especificación de la API System One](https://github.com/ollama/ollama/blob/main/docs/openapi.yaml)
- [TypeSafe AI: API oficial Jev](https://api.typesafe.ai/redoc)
