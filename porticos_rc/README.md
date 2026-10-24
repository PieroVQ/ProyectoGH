# Generador de pórticos de concreto armado

Proyecto Python para Windows / Visual Studio / VS Code. Genera edificios de
2–5 pisos, analiza pórticos espaciales con OpenSeesPy y exporta una sola hoja
Excel: una fila por estructura, un valor por celda. Incluye familias,
alternativas de secciones y gráfico 3D interactivo. No incluye Random Forest.

## Instalar y ejecutar

Use **Python 3.12 de 64 bits**, versión comprobada para este proyecto en Windows.
Abra una terminal en la carpeta que contiene `main.py`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py generar
```

No es necesario activar el entorno ni cambiar la política de ejecución de Windows.
En Visual Studio seleccione `.venv\Scripts\python.exe` como intérprete y
`main.py` como archivo inicial; argumentos de ejecución: `generar`.
En VS Code seleccione ese mismo intérprete y ejecute los comandos en la terminal.

Por defecto se solicitan **100 estructuras**. Para cambiar la cantidad:

```powershell
.\.venv\Scripts\python.exe main.py generar --cantidad 100 --salida mi_base
.\.venv\Scripts\python.exe main.py ver --excel mi_base/estructuras.xlsx --id 37 --abrir
```

Omitir `--id` permite escribir el número cuando el programa lo solicite.
El gráfico HTML incluye Plotly localmente: puede abrirse sin conexión.
Pulse los nombres de la leyenda para ocultar losas o grupos de elementos.

Para continuar o ampliar una ejecución compatible:

```powershell
.\.venv\Scripts\python.exe main.py generar --cantidad 200 --salida mi_base --reanudar
```

El programa rechaza mezclar una base existente con otra configuración o versión
de código. Use una carpeta nueva cuando cambie parámetros. Cierre el Excel antes
de reanudar; Windows puede impedir reemplazar un libro abierto.

## Configuración y resultados

Edite `config.json`. Longitudes en cm, fuerzas en kgf, tiempo en s; concreto
inicial 280 kgf/cm². El generador calcula el peso y asigna cargas automáticamente.

Archivos en la carpeta de salida:

- `estructuras.xlsx`: única hoja **Estructuras**, sin hojas ocultas.
- `diccionario_columnas.json`: significado, unidades y papel de cada campo.
- `variables_ml.json`: propuesta de entradas y objetivos; no entrena modelos.
- `configuracion_ejecutada.json`: configuración, versiones y firma del código.
- `registro.jsonl`: descartes, fallos e información de modelos irregulares.
- `estado.json`: recuperación de una ejecución interrumpida.
- `resumen_ejecucion.json`: cantidad obtenida y estadísticas.
- `estructura_XXXX.html`: visualización solicitada por ID.

Los campos de pisos, vanos o bloques inexistentes quedan vacíos. No son ceros.
Todas las variantes de una geometría comparten `ID_familia`; manténgalas juntas
al separar entrenamiento y evaluación. No use los identificadores como predictores.

Los paños macizos/aligerados y su ubicación se repiten en altura. Las secciones
pueden cambiar una vez por bloques. Las losas se agrupan por tipo con espesor
común, gobernado por el paño exigente.

## Alcance de los resultados

Es una herramienta de investigación y **predimensionamiento**, con respuesta
elástica de secciones brutas y diafragmas rígidos asumidos. No diseña armaduras.
`regularidad_evaluable=True` significa que pasaron los criterios implementados
de geometría, masa, rigidez y torsión; **no certifica regularidad por resistencia**.
R=8 y el factor de desplazamientos se emplean bajo la hipótesis documentada de
pórticos dúctiles regulares, no como resultado de diseñar el refuerzo.

Se conservan modelos que no satisfacen derivas. No se incluyen efectos P–Delta
en la rigidez: se informa un indicador de sensibilidad, que no constituye una
verificación normativa de estabilidad. Tampoco se verifica resistencia del
diafragma, nudos, capacidad axial-flexión, cortante ni flecha de largo plazo.
Las divisiones se asumen desacopladas de las deformaciones de las losas para
aplicar las reglas de espesor correspondientes. Véase `METODOLOGIA.md`.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Incluyen solución cerrada de voladizo, simetría, intercambio de ejes, comparación
modal con OpenSees, equilibrio, Excel/reconstrucción y recuperación determinista.

## Resistencias de concreto variables

`fc_kgf_cm2` admite una lista, inicialmente `[210.0, 280.0]`, o un valor único. Se selecciona reproduciblemente por familia con igual probabilidad, independientemente de la geometría; las alternativas conservan la resistencia familiar. La proporción final puede variar por los descartes. Se recalculan secciones y respuesta con la resistencia asignada.

210 kgf/cm² equivale a 20.59 MPa: se permite sólo como caso de estudio mediante `permitir_fc_inferior_21MPa_estudio`. La columna `fc_alcanza_21MPa` registra el umbral; no es una certificación de diseño. R sigue siendo una hipótesis del estudio.

Genere una carpeta nueva (por ejemplo `--salida nuevas_estructuras`); las bases anteriores no se transforman ni se pueden reanudar con esta configuración. El manifiesto `variables_ml.json` generado incluye `fc_kgf_cm2` y `fy_kgf_cm2` como entradas.

## Reemplazar en la misma carpeta

`generar --cantidad 1500 --semilla 20261119 --salida nuevas_estructuras --reemplazar` genera una base nueva y reemplaza los archivos conocidos sólo al completar la cantidad. Conserva un respaldo ZIP. No se combina con --reanudar. Cierre Excel antes de actualizar. Los HTML anteriores deben regenerarse con ver. Las longitudes ordenadas de vanos ahora se incluyen en el manifiesto para ML.
