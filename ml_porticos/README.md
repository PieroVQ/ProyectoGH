# Modelo mejorado: instrucciones principales

El modelo principal compara Random Forest, Extra Trees y Gradient Boosting y elige
la mejor configuración para cada respuesta. Se entrenó con una base nueva de 1500
estructuras de familias diferentes: 1200 para desarrollo y 300 para prueba final.
Las siete configuraciones y combinaciones se seleccionan exclusivamente por
validación interna de tres particiones, manteniendo juntas las familias.

## Abrir los resultados

Desde la raíz del repositorio:

```powershell
Start-Process .\resultados_ml_optimizado\informe.html
```

El modelo principal es `resultados_ml_optimizado/modelo_final.joblib`. Para comparar con
OpenSees sin haber entrenado con el caso, se usa `modelo_evaluacion.joblib` y se
elige un ID de prueba en `division.csv`. La base correspondiente es ahora
`base_ml_ampliada/estructuras.xlsx`; la misma utilizada en el entrenamiento.

## Volver a optimizar con el Excel actualizado

```powershell
.\.venv\Scripts\python.exe .\ml_porticos\ml.py optimizar --excel base_ml_ampliada\estructuras.xlsx --salida nuevo_entrenamiento_ml
```

El comando `entrenar` conserva el entrenamiento sencillo anterior como comparación.
Para mantener la selección mejorada use `optimizar`. El proceso compara modelos,
guarda los resultados en la carpeta indicada. No modifica el Excel de entrada.
Los archivos HTML de casos anteriores no se regeneran automáticamente.

## Generar otra base amplia

```powershell
.\.venv\Scripts\python.exe .\ml_porticos\crear_base_ml.py --cantidad 1500 --semilla 20261120 --procesos 4 --salida otra_base_ml
```

Genera una alternativa por familia, con análisis aislados en cuatro procesos.
Conserva las reglas y límites del generador, incluyendo el supuesto de ductilidad,
secciones brutas, ausencia de brazos rígidos y P–Delta. El concreto de 210 sigue
siendo un caso de estudio con la advertencia correspondiente en el Excel.
Este generador de base amplia usa una carpeta vacía y no utiliza el checkpoint del
generador habitual. Si se interrumpe, el Excel parcial guardado puede inspeccionarse;
para reiniciar use otra salida vacía. No concatene bases sin resolver familias e IDs.

## Qué cambió y por qué

1. Más familias independientes; no se multiplicaron variantes casi iguales.
2. Se utilizan los vanos ordenados, alturas de todos los pisos, distribución de
   paños, pesos por piso y centros de masa calculables por metrado.
3. Se calculan 27 entradas auxiliares a partir de geometría, materiales y cargas:
   estimaciones simplificadas de rigidez, período y demanda. No se leen períodos,
   derivas, rigideces del análisis ni otros resultados como entradas.
4. Se ensayó aprender la corrección respecto a esas estimaciones en escala
   logarítmica. Esto hace comparables edificios de tamaños y demandas diferentes.
5. Se eligió por respuesta entre siete configuraciones y el promedio de las dos/tres
   mejores, sólo cuando reducía el error interno. La prueba final no elige modelos.

Las aproximaciones auxiliares son características de ML, no un sustituto de un
análisis estructural ni una comprobación normativa. Se usa un límite inferior de
cortante coherente con la fórmula del propio generador. La alta precisión mide la
reproducción de ese generador dentro de su dominio, no la realidad construida.
No se garantiza la mayor precisión universal: se conserva la mejor opción ensayada.

## Archivos para entender la comparación

- `informe.html`: resumen y tablas legibles.
- `comparacion_configuraciones.csv`: error de cada configuración y respuesta en validación interna.
- `comparacion_conjunta.csv`: promedio del error normalizado, peor respuesta y criterio conjunto; menor es mejor.
- `seleccion.json`: configuraciones elegidas y parámetros exactos.
- `curva_aprendizaje.csv`: efecto de entrenar con 100, 300, 600 y 800 ejemplos sobre una validación fija del desarrollo.
- `metricas.csv`: prueba final, referencia de media y Random Forest directo en la misma base.
- `metricas_por_grupo.csv` e `intervalos_R2.csv`: diagnóstico posterior de la ejecución entregada, sin volver a seleccionar.
- `importancias.csv`: diagnóstico posterior; permutar entradas puede crear combinaciones no físicas y no demuestra causalidad.

Los pesos y centros son información de entrada calculada por metrado, no mediciones
dinámicas. El Excel contiene las 107 entradas requeridas. No basta con introducir
sólo pisos y f'c. Al portar el modelo a otra aplicación, incluya `modelos_mejorados.py`
y las dependencias de `requirements-tested.txt`: esta versión tiene estimadores
propios y necesita ese módulo además del archivo joblib. No necesita OpenSees para
predecir una vez calculadas todas las entradas.

Fuentes técnicas: https://scikit-learn.org/stable/modules/generated/sklearn.compose.TransformedTargetRegressor.html
https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html

## Predecir

```powershell
.\.venv\Scripts\python.exe ml_porticos/ml.py predecir --modelo resultados_ml_optimizado/modelo_final.joblib --excel base_ml_ampliada/estructuras.xlsx --salida predicciones_nuevas.csv
```

Para otras estructuras, el Excel debe contener las 107 entradas de
`variables_utilizadas.json`. No necesita las ocho respuestas estructurales.

## Comparación individual

```powershell
.\.venv\Scripts\python.exe ml_porticos/caso.py --excel base_ml_ampliada/estructuras.xlsx --modelos resultados_ml_optimizado --id 1 --abrir
```

El informe utiliza el modelo de evaluación y muestra si el caso pertenece al
entrenamiento o a la prueba reservada. La referencia de OpenSees se lee del Excel.
