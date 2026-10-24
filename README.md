# Pórticos de concreto armado: guía de uso

Este proyecto genera estructuras de concreto armado, calcula su respuesta con
OpenSees y utiliza un modelo de aprendizaje automático (ML) para predecir ocho
resultados. Se entrega una base original de **1.500 estructuras de 1.500 familias**,
los modelos entrenados y sus resultados.

El recorrido habitual es: **instalar → consultar los resultados originales →
generar un lote nuevo → ver sus estructuras en 3D → obtener predicciones → abrir
los informes HTML**. No hace falta entrenar el modelo para utilizarlo.

## 1. Qué necesitas antes de empezar

- Una computadora Windows de 64 bits.
- Python 3.12 de 64 bits. El entorno original usa Python 3.12.4. Instálalo desde
  el sitio oficial de Python e incluye el lanzador `py` al instalarlo.
- Un navegador para abrir los archivos HTML. Excel es opcional: sirve para
  consultar las tablas, pero no es necesario para ejecutar el proyecto.
- La carpeta completa del proyecto descargada y descomprimida. Si la obtienes
  como ZIP desde GitHub, descomprímela antes de ejecutar los comandos.
- Conexión a Internet para instalar las dependencias por primera vez. Los
  modelos y las visualizaciones HTML no requieren un servicio de predicción en línea.

Abre PowerShell y entra en la carpeta que contiene este `README.md`:

```powershell
cd "D:\AECODE\ProyectoGH"
```

Si guardaste el proyecto en otro lugar, cambia esa ruta por la tuya. **Todos los
comandos siguientes se ejecutan desde esa misma carpeta**, no desde las carpetas
`ml_porticos` o `porticos_rc`.

Comprueba que Python está disponible:

```powershell
py -3.12 --version
```

Debe mostrar una versión 3.12. Si no reconoce `py`, revisa la instalación de Python.
No necesitas instalar Visual Studio, VS Code, Excel ni OpenSees por separado para
seguir esta guía; la biblioteca OpenSeesPy se instala en el siguiente paso.

## 2. Crear el entorno virtual e instalar todo

Un entorno virtual es una carpeta que guarda el Python y las bibliotecas usados
por este proyecto. Se llamará `.venv` y estará dentro de la raíz del proyecto.

Ejecuta estos comandos una sola vez:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Espera a que finalice la instalación sin errores. El último comando comprueba
si las dependencias instaladas son compatibles entre sí.

**¿Qué se instala dentro de `.venv`?** El archivo `requirements.txt` de la raíz
contiene las versiones para el proyecto completo:

| Biblioteca | Para qué se utiliza |
|---|---|
| OpenSeesPy y su componente para Windows | Generar y analizar las estructuras. |
| NumPy y SciPy | Operaciones numéricas. |
| pandas y openpyxl | Leer y escribir Excel y tablas. |
| scikit-learn y joblib | Cargar los modelos, predecir y entrenar. |
| Plotly | Crear las visualizaciones 3D interactivas. |
| pytest | Ejecutar las pruebas del generador. |
| Otras dependencias del mismo archivo | Completar el entorno utilizado por esas bibliotecas. |

No tienes que instalar las bibliotecas una por una ni ejecutar los archivos de
requisitos de cada subcarpeta: utiliza el de la raíz. No cambies las versiones
fijadas para intentar resolver un fallo de instalación sin comprobar la
compatibilidad con los modelos originales.

En esta guía **no es necesario activar el entorno**. Todos los comandos empiezan
con `.\.venv\Scripts\python.exe`, por lo que utilizan directamente el entorno
correcto. Esto también evita problemas de permisos al activar PowerShell.

Para volver a trabajar otro día, abre PowerShell, entra otra vez en la raíz y
continúa con los mismos comandos. No vuelvas a crear `.venv` cada vez.

Crea la carpeta para tus resultados nuevos:

```powershell
New-Item -ItemType Directory -Path outputs -Force | Out-Null
```

## 3. Qué contiene cada carpeta y qué debes conservar intacto

| Carpeta | Contenido |
|---|---|
| `porticos_rc` | Generador, análisis OpenSees, visualización 3D y pruebas. |
| `ml_porticos` | Creación de bases, entrenamiento, optimización, predicción e informes. |
| `base_ml_ampliada` | Base original de las 1.500 estructuras, configuración y descripción de variables. |
| `resultados_ml_optimizado` | Modelos entrenados, comparación entre algoritmos, métricas e informes originales. |
| `outputs` | Lotes, predicciones y visualizaciones que generes durante el uso. Se crea al trabajar y se excluye de Git. |
| `.venv` | Bibliotecas instaladas localmente. No se sube a GitHub. |

**La base de datos original se llama `base_ml_ampliada/estructuras.xlsx`. No la
modifiques, no borres filas y no pegues nuevos datos dentro de ella.** Sus
respuestas estructurales, la división de evaluación y los modelos corresponden
a ese archivo concreto.

Puedes abrirla para consultar sus datos, pero evita guardarla desde Excel: incluso
un guardado sin cambios visibles puede cambiar la huella del archivo que verifica
el informe original. Cierra Excel después de consultarla.

Conserva también intacta la carpeta `resultados_ml_optimizado`. No borres ni
sustituyas sus modelos o informes. Los ejemplos de esta guía escriben resultados
nuevos dentro de `outputs`.

**Para probar más estructuras, genera archivos nuevos y pásalos al modelo.**
Las predicciones no se agregan automáticamente a la base y el modelo no aprende
de ellas. No debes usar una predicción como si fuera una respuesta de OpenSees
para entrenarlo.

## 4. Consultar los resultados originales del modelo de 1.500 datos

Para abrir el informe general que ya viene con el proyecto:

```powershell
Start-Process ".\resultados_ml_optimizado\informe.html"
```

También puedes abrir ese archivo con doble clic. Contiene la comparación de
configuraciones, las métricas y la selección de modelos por respuesta.

Los archivos de esa misma carpeta permiten consultar más detalle:

| Archivo | Qué muestra |
|---|---|
| `comparacion_configuraciones.csv` | Resultados de siete configuraciones de Random Forest, Extra Trees y Gradient Boosting en validación interna. |
| `comparacion_conjunta.csv` | Comparación global de las configuraciones. Un criterio menor es mejor. |
| `seleccion.json` | Configuraciones elegidas para cada respuesta. |
| `metricas.csv` | MAE, RMSE, R² y errores relativos de validación, prueba y referencias de comparación. |
| `predicciones_prueba.csv` | Los valores de referencia y las predicciones para cada una de las 300 estructuras de prueba. |
| `division.csv` | Identifica las 1.200 estructuras de desarrollo y las 300 reservadas para prueba. |
| `curva_aprendizaje.csv` | Cómo cambia el desempeño al entrenar con distintas cantidades de datos. |
| `importancias.csv` | Dependencia de cada modelo respecto a sus entradas; no demuestra causalidad. |
| `metricas_por_grupo.csv` e `intervalos_R2.csv` | Diagnósticos por grupos e intervalos descriptivos de R². |

Los CSV son tablas que puedes abrir en Excel. Si todos los datos aparecen en una
sola columna, usa **Datos → Desde texto/CSV**, con separador coma, codificación
UTF-8 y punto como separador decimal.

Para ver en HTML las predicciones de prueba que ya están guardadas:

```powershell
Import-Csv .\resultados_ml_optimizado\predicciones_prueba.csv | ConvertTo-Html -Title "Predicciones originales de prueba" | Set-Content -Encoding utf8 .\outputs\prueba_original.html
Start-Process ".\outputs\prueba_original.html"
```

Este último HTML es una tabla de los resultados almacenados; no vuelve a predecir.

## 5. Ver en 3D cualquier estructura de la base original

El número de una estructura está en la columna `ID_estructura` del Excel. Para
visualizar la estructura 1:

```powershell
.\.venv\Scripts\python.exe porticos_rc/main.py ver --excel base_ml_ampliada/estructuras.xlsx --id 1 --html outputs/original_0001_3d.html --abrir
```

Cambia `--id 1` por el identificador que quieras consultar, entre los disponibles
en ese Excel. Se abre un HTML con la geometría 3D y la planta. Puedes arrastrar para
girar, usar la rueda para acercarte y pulsar la leyenda para ocultar elementos.

El archivo se guarda en `outputs/original_0001_3d.html`; cambiar el ID no cambia
automáticamente ese nombre de salida, así que cambia también el nombre para
guardar varias visualizaciones. El HTML incluye Plotly y se puede abrir sin conexión.

La visualización representa la geometría almacenada; no es una animación del
movimiento sísmico. Ver una estructura no vuelve a analizarla ni modifica el Excel.

## 6. Generar nuevas estructuras para probar sus predicciones

Para una primera prueba, genera un lote nuevo de 20 estructuras, una por familia:

```powershell
.\.venv\Scripts\python.exe ml_porticos/crear_base_ml.py --cantidad 20 --semilla 20261120 --procesos 2 --salida outputs/lote_01
```

Este comando utiliza el generador y OpenSees, calcula las entradas y las respuestas
estructurales y las guarda separadas de la base original. Durante la ejecución
muestra el progreso. Espera a que termine antes de abrir el Excel.

| Opción | Significado |
|---|---|
| `--cantidad 20` | Número de estructuras aceptadas que se desea generar; el mínimo de este comando es 20. |
| `--semilla 20261120` | Controla la generación reproducible. Cambiarla permite crear otro lote. Repetirla con la misma configuración reproduce las mismas familias. |
| `--procesos 2` | Ejecuta los análisis en dos procesos; el comando admite de 1 a 8. |
| `--salida outputs/lote_01` | Carpeta del lote. Debe estar vacía o no existir; el programa la crea. |

Usa una semilla diferente de la original `20261119` para ensayar otra población.
Esto cambia el muestreo, pero no constituye una comprobación de que todas las
geometrías sean distintas de las anteriores.

Al finalizar encontrarás:

- `outputs/lote_01/estructuras.xlsx`: el Excel nuevo, con una fila por estructura.
- `variables_ml.json` y `diccionario_columnas.json`: entradas y descripción de columnas.
- `configuracion_base.json` y `resumen_base.json`: parámetros y resumen de generación.
- `descartes.jsonl`: registro de intentos descartados o fallidos.

El generador puede analizar más de 20 candidatos porque rechaza los que no cumplen
sus filtros. No todas las estructuras aceptadas cumplen el límite de deriva.
La base amplia no tiene reanudación por checkpoint: si se interrumpe, conserva
los archivos parciales disponibles y utiliza otra carpeta vacía para reiniciar.

Para otro lote, cambia la semilla y la salida, por ejemplo a `outputs/lote_02`.
No concatentes estos archivos con la base original ni mezcles IDs de distintos
lotes: los identificadores pueden repetirse entre carpetas.

### Otra forma: generador habitual con variantes de una familia

También existe un generador con recuperación del avance y variantes de secciones:

```powershell
.\.venv\Scripts\python.exe porticos_rc/main.py generar --cantidad 20 --semilla 20261121 --salida outputs/lote_variantes_01
```

Genera varias alternativas de una misma familia, por lo que no equivale a 20
familias independientes. Si necesitas continuar una ejecución compatible:

```powershell
.\.venv\Scripts\python.exe porticos_rc/main.py generar --cantidad 30 --semilla 20261121 --salida outputs/lote_variantes_01 --reanudar
```

`--cantidad 30` significa llegar a 30 estructuras en total, no añadir 30. La
reanudación requiere la misma configuración y código. Esta opción **no aplica**
al comando `crear_base_ml.py` del primer ejemplo.

### Para qué sirve `porticos_rc/config.json`

Define los rangos de pisos, vanos, alturas, materiales, cargas y otros límites de
generación. Los dos generadores utilizan este archivo; las opciones de línea de
comandos sustituyen algunos valores de esa configuración.

Para las primeras pruebas, conserva sus valores. Cambiarlo afecta las estructuras
que generes después, no la base original ni el modelo entrenado. El predictor
rechaza entradas fuera del dominio aprendido, incluso si OpenSees pudo analizarlas.

No edites manualmente entradas de una fila analizada y conserves sus respuestas
antiguas: dejarían de corresponder a esa estructura. Genera y analiza otra fila.

## 7. Consultar el Excel nuevo y ver sus estructuras en 3D

### Qué archivos permiten obtener predicciones, reportes y vista 3D

| Archivo de entrada | Predicción ML | Reporte HTML de predicción | Vista 3D con el visualizador actual |
|---|---|---|---|
| Excel completo producido por el generador del proyecto | Sí, si sus entradas están dentro del dominio del modelo. | Sí. | Sí; incluye los datos que necesita el visualizador. |
| Excel preparado con solo las 107 entradas y los identificadores | Sí, si respeta el formato y dominio del modelo. | Sí. | No directamente; el visualizador también requiere campos adicionales del generador. |

**Para obtener las tres salidas de cualquier estructura nueva, genera el lote con
el proyecto y conserva su Excel completo.** No elimines columnas para preparar la
predicción: el predictor selecciona automáticamente las entradas que utiliza.

Un Excel con solo entradas puede ser suficiente para predecir, pero el comando
`porticos_rc/main.py ver` espera el formato completo del generador. Si solo
conservas las entradas, necesitas también la definición completa de esa misma
estructura para reconstruirla con el visualizador actual. No basta con disponer
del CSV de predicciones o del reporte HTML.

Las predicciones deben respetar el dominio aprendido; una estructura válida para
el generador no tiene garantizada su aceptación por el predictor.

Abre el nuevo Excel para consultar la geometría y los resultados de OpenSees:

```powershell
Start-Process ".\outputs\lote_01\estructuras.xlsx"
```

Este comando usa la aplicación asociada a `.xlsx`. Si no tienes una, puedes omitir
este paso. Cierra el archivo antes de continuar trabajando con ese lote.

Para ver la estructura 1 de ese lote:

```powershell
.\.venv\Scripts\python.exe porticos_rc/main.py ver --excel outputs/lote_01/estructuras.xlsx --id 1 --html outputs/lote_01/estructura_0001_3d.html --abrir
```

Cambia el Excel y el ID para visualizar cualquier otra estructura creada. Busca
el ID dentro del Excel del lote correspondiente; el ID 1 de un lote no identifica
necesariamente la misma estructura que el ID 1 de otro.

## 8. Pasar el lote nuevo al modelo de predicción

No se arrastra ni se pega el Excel dentro de un modelo. Se indica su ubicación
mediante `--excel` al ejecutar el comando:

```powershell
.\.venv\Scripts\python.exe ml_porticos/ml.py predecir --modelo resultados_ml_optimizado/modelo_final.joblib --excel outputs/lote_01/estructuras.xlsx --salida outputs/lote_01/predicciones.csv
```

- `--modelo` señala el modelo final ya entrenado con las 1.500 estructuras.
- `--excel` señala el lote de estructuras que quieres predecir.
- `--salida` señala el CSV donde se guardarán las ocho predicciones por estructura.

El archivo de salida debe tener un nombre nuevo: el comando rechaza sobrescribir
un CSV existente. Si repites la prueba, usa, por ejemplo, `predicciones_02.csv`.
Ejecutar una predicción no vuelve a entrenar el modelo ni agrega datos a su base.

Las columnas predichas son:

| Respuesta | Unidad |
|---|---|
| `Tx_s_predicho`, `Ty_s_predicho` | Segundos. |
| `V_modal_ajustado_X_kgf_predicho`, `V_modal_ajustado_Y_kgf_predicho` | kgf. |
| `desplazamiento_techo_max_X_cm_predicho`, `desplazamiento_techo_max_Y_cm_predicho` | cm. |
| `deriva_max_X_predicho`, `deriva_max_Y_predicho` | Adimensional. |

El generador ya entrega las 107 entradas requeridas. Si utilizas un Excel externo,
debe tener una sola hoja y contener todas las columnas de entrada listadas en
`resultados_ml_optimizado/variables_utilizadas.json`, con los mismos nombres y
unidades. No necesita las ocho respuestas de OpenSees. No basta con introducir
únicamente pisos y resistencia del concreto. Para los informes de esta guía,
incluye también un `ID_estructura` entero, único y completo en cada fila.

Los vanos mantienen su orden desde el origen; los inexistentes y los elementos
no aplicables deben permanecer vacíos. No los rellenes con ceros. El modelo valida
rango de entradas, resistencias y otras categorías; si un dato está fuera del
dominio entrenado, rechaza la predicción. Estar dentro de todos los rangos tampoco
garantiza que una combinación esté bien representada en el entrenamiento.

## 9. Abrir el HTML con todas las predicciones del lote nuevo

Después de crear el CSV del paso anterior:

```powershell
.\.venv\Scripts\python.exe ml_porticos/informe_predicciones.py --excel outputs/lote_01/estructuras.xlsx --predicciones outputs/lote_01/predicciones.csv --salida outputs/lote_01/informe_predicciones.html --abrir
```

Se abre una tabla HTML con todas las estructuras y sus ocho predicciones. Si el
Excel incluye resultados de OpenSees, también muestra comparaciones y errores por
respuesta. Si solo contiene entradas, presenta únicamente las predicciones.

El informe lee el CSV existente: no entrena, no vuelve a predecir y no modifica
el Excel. Debes usar el Excel y el CSV del mismo lote. Verifica sus rutas; IDs
iguales entre archivos de distintos lotes no garantizan que sean las mismas entradas.

El HTML se guarda en la ruta indicada y puedes abrirlo después con doble clic.
Si ya existe, elige otro nombre para conservar el anterior.

## 10. Abrir el HTML de una predicción aislada del lote nuevo

Usa el mismo comando anterior y añade el identificador:

```powershell
.\.venv\Scripts\python.exe ml_porticos/informe_predicciones.py --excel outputs/lote_01/estructuras.xlsx --predicciones outputs/lote_01/predicciones.csv --id 1 --salida outputs/lote_01/prediccion_0001.html --abrir
```

Muestra únicamente la estructura 1: predicciones, comparación con OpenSees cuando
está disponible y los datos del Excel. Cambia el ID y el nombre del HTML para
consultar otras estructuras. El CSV debe incluir ese ID.

El informe individual muestra las ocho salidas y las 107 entradas en tablas visibles. Si el lote contiene una sola estructura, ese formato se aplica automáticamente, aunque no se indique `--id`.

### ¿Y si quiero predecir solamente una estructura?

Puedes crear un Excel **nuevo** de una sola hoja con la fila completa de esa
estructura, conservando los encabezados y las 107 entradas, y ejecutar el mismo
comando `predecir` con ese archivo. Genera su CSV y después su HTML con las rutas
de ese nuevo par de archivos. Nunca recortes ni guardes encima del Excel original.

## 11. Informe individual de una estructura de la base original

Para consultar la comparación original sin sustituir los informes guardados:

```powershell
.\.venv\Scripts\python.exe ml_porticos/caso.py --excel base_ml_ampliada/estructuras.xlsx --modelos resultados_ml_optimizado --id 1 --html outputs/original_0001_comparacion.html --abrir
```

Este comando es distinto del informe de lotes nuevos: `caso.py` comprueba que el
Excel sea exactamente el usado durante el entrenamiento. **No lo uses con un
lote nuevo**; para eso están los pasos 9 y 10.

| Modelo | Datos usados para ajustarlo | Uso |
|---|---|---|
| `modelo_evaluacion.joblib` | 1.200 estructuras. | Evaluar con las 300 estructuras reservadas. Lo utiliza `caso.py`. |
| `modelo_final.joblib` | Las 1.500 estructuras. | Predecir los lotes nuevos mediante el comando `predecir`. |

El informe original identifica si una estructura participó en el entrenamiento o
quedó reservada para prueba. Para elegir una de prueba, consulta `division.csv` o
ejecuta en PowerShell:

```powershell
Import-Csv .\resultados_ml_optimizado\division.csv | Where-Object conjunto -eq "prueba" | Select-Object -First 10 ID_estructura, ID_familia
```

Una comparación sobre un caso que participó en entrenamiento no demuestra la
precisión del modelo en casos nuevos. Ambos archivos usan la selección optimizada;
la diferencia es con cuántas estructuras se ajustaron.

**OpenSees es la referencia calculada**, no una medición de un edificio construido.
El ML aprende a aproximar los resultados de ese análisis. Menor error absoluto o
relativo significa mayor coincidencia en el caso comparado; R² se interpreta sobre
un conjunto de casos, no sobre una estructura aislada.

## 12. Archivos y programas que intervienen

| Archivo | Función |
|---|---|
| `porticos_rc/config.json` | Parámetros para generar nuevas estructuras. |
| `porticos_rc/main.py` | Generación habitual, recuperación del avance y visualización 3D. |
| `ml_porticos/crear_base_ml.py` | Generación de lotes con una estructura por familia. |
| `ml_porticos/ml.py` | Comandos para predecir, entrenar y solicitar la optimización. |
| `ml_porticos/optimizar.py` | Comparación y selección de configuraciones por respuesta. |
| `ml_porticos/modelos_mejorados.py` | Definición de los modelos optimizados y sus transformaciones. Es necesario para cargar los modelos guardados. |
| `ml_porticos/informe_predicciones.py` | HTML general o individual a partir de predicciones ya guardadas. |
| `ml_porticos/caso.py` | Comparación individual sobre la base original con el modelo de evaluación. |

El archivo `.joblib` no funciona por sí solo: necesita el código de sus clases y
las bibliotecas compatibles. Conserva completa la carpeta del proyecto.

## 13. Entrenamiento: no es necesario para utilizar el modelo

Agregar un Excel a `outputs` o ejecutar `predecir` no actualiza el modelo entrenado.
El uso normal de esta guía consiste en conservarlo y consultar nuevas predicciones.

Si necesitas reproducir el proceso de optimización como tarea independiente,
puedes ejecutarlo sobre la base original **en modo lectura**, con salida nueva:

```powershell
.\.venv\Scripts\python.exe ml_porticos/ml.py optimizar --excel base_ml_ampliada/estructuras.xlsx --salida outputs/entrenamiento_experimental --semilla 48371
```

Este proceso compara las configuraciones, entrena y crea resultados nuevos. Puede
tardar y no es un paso previo a predecir. No uses como salida
`resultados_ml_optimizado` ni la opción `--reemplazar` si quieres conservar la
referencia entregada. Un entrenamiento nuevo debe verificarse por separado;
esta guía no garantiza archivos idénticos entre entornos distintos.

## 14. Problemas frecuentes

| Mensaje o situación | Qué revisar |
|---|---|
| No se reconoce `py`. | Instalación de Python 3.12 y su lanzador; cierra y vuelve a abrir PowerShell. |
| No se encuentra `.venv\Scripts\python.exe`. | Ejecuta los comandos desde la raíz y crea primero `.venv`. |
| Falta una biblioteca. | Instala el `requirements.txt` de la raíz con el Python de `.venv`. |
| La instalación no encuentra una versión fijada. | Revisa Python de 64 bits, el índice usado y la disponibilidad de la versión exacta. No se sustituye automáticamente por otra. |
| La carpeta de generación ya contiene archivos. | Elige una salida nueva, como `outputs/lote_02`; el generador de base amplia requiere una carpeta vacía. |
| El archivo de predicciones o HTML ya existe. | Usa otro nombre de salida para conservar la prueba anterior. |
| Predicción rechazada por rango o valor no entrenado. | El lote contiene entradas fuera del dominio observado. No fuerces valores para que pase; prueba otro lote dentro del dominio o revisa el problema de modelado. |
| Faltan columnas. | Usa el Excel generado o completa las entradas exactas del manifiesto; no cambies encabezados. |
| El Excel cambió desde el entrenamiento. | `caso.py` necesita el original intacto. Para otro Excel, usa `predecir` e `informe_predicciones.py`. |
| ID inexistente. | Busca `ID_estructura` dentro del Excel del lote correspondiente. |
| Error de permisos al guardar. | Cierra el archivo en Excel y confirma que puedes escribir en la carpeta de salida. |
| No se abre automáticamente el HTML. | Abre con doble clic el archivo de la ruta indicada en PowerShell. |

## 15. Comprobar el código y conocer su alcance

Las pruebas son opcionales para una consulta de predicción:

```powershell
.\.venv\Scripts\python.exe -m pytest -o pythonpath=porticos_rc porticos_rc/tests -q
.\.venv\Scripts\python.exe -m unittest discover -s ml_porticos -p "test_*.py"
```

El análisis de origen usa secciones brutas y diafragmas rígidos. No incluye
P–Delta ni diseño de armaduras. Los resultados sirven dentro de las hipótesis
documentadas; no certifican resistencia, ductilidad ni seguridad de una obra.
La metodología se describe en `porticos_rc/METODOLOGIA.md`.

Las longitudes están en cm, las fuerzas en kgf y el tiempo en segundos. El concreto
de 210 kgf/cm² es un caso de estudio bajo las condiciones indicadas en la metodología.

Para compartir el proyecto en GitHub, conserva el código, `requirements.txt`, la
base original y `resultados_ml_optimizado`. `.gitignore` excluye `.venv`, cachés y
los resultados locales de `outputs`.
