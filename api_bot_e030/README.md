# API del bot Telegram para el modelo E.030

Esta API carga el `modelo_final.joblib` de este mismo repositorio y expone las
107 entradas y ocho predicciones que utilizan los tres workflows RC Bot de n8n.
No reentrena el modelo ni modifica la base original. Los modelos seleccionados
pueden ser distintos para cada respuesta; las ocho salidas no son todas Random
Forest. La predicción no reemplaza un análisis estructural ni la verificación
normativa.

## Desplegar en Render

1. Cree un **Web Service** desde este repositorio con la opción **Public Git
   Repository** y use la URL `https://github.com/PieroVQ/ProyectoGH`.
2. Elija **Docker** como entorno. El `Dockerfile` está en la raíz del repositorio.
3. Configure `BOT_API_TOKEN` como variable secreta con un valor aleatorio largo.
   Nunca lo guarde en Git ni lo envíe por chat.
4. Use `GET /health` para comprobar que el servicio arrancó. Los demás endpoints
   requieren `Authorization: Bearer <BOT_API_TOKEN>`.

Render proporciona el puerto en `PORT`. La URL HTTPS asignada por Render será
`BACKEND_URL` en los tres workflows de n8n. La opción Public Git Repository
requiere iniciar manualmente las nuevas versiones; para despliegues automáticos,
conecte el proveedor Git y autorice a Render para este repositorio.

El `Dockerfile` escribe la base SQLite en `/tmp/consultas.sqlite3`. En una
instancia gratuita de Render, ese archivo puede perderse al reiniciar o dormir
el servicio. Para conservar consultas e idempotencia durante varios días, use
almacenamiento persistente y configure `BOT_DB_PATH` en su ruta.

## Ejecutar localmente

Desde la raíz del repositorio, con Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r api_bot_e030/requirements.txt
$env:BOT_API_TOKEN = '<valor-local-no-compartido>'
.\.venv\Scripts\python.exe -m uvicorn api_bot_e030.main:app --host 127.0.0.1 --port 8000
```

El esquema OpenAPI está en `/docs`. Endpoints usados por n8n:

- `GET /schema`: características, unidades y rangos del modelo.
- `POST /consultas/validar`: valida las 107 entradas sin llamar al modelo.
- `POST /consultas`: calcula ocho predicciones con una clave idempotente.
- `GET /consultas/{consulta_id}`: devuelve el resultado guardado.
- `POST /informes/pdf`: recibe `index.html` y `footer.html` como archivos
  multipart llamados `files` y devuelve un PDF.

En n8n, el flujo **Generar y entregar informe** debe llamar a
`<BACKEND_URL>/informes/pdf` con la misma credencial Bearer. Si una copia
importada del flujo aún apunta a Gotenberg, cambie esa URL antes de publicarla.

## Figuras de cada consulta

Las consultas nuevas incluyen dos archivos `image/png` en `archivos`:

- `geometria`: ejes idealizados definidos exclusivamente por las luces y alturas
  confirmadas. No representa deformaciones, daños ni resultados de un análisis.
- `predicciones`: ocho salidas guardadas, agrupadas por unidad en cuatro paneles.
  No agrega curvas, límites normativos ni comparaciones con OpenSees.

Se descargan con `GET /consultas/{consulta_id}/archivos/{archivo_id}` usando la
misma credencial Bearer. Se representan al solicitar la descarga desde el
resultado guardado, sin repetir la inferencia. Una consulta/archivo inexistente
devuelve 404; una solicitud sin autorización devuelve 401. Las consultas antiguas
que se guardaron con `archivos: []` conservan ese estado; cree una consulta nueva
para obtener figuras. No se genera un HTML 3D interactivo.

`POST /consultas` admite `origen_datos` con valores `no_declarado` (predeterminado),
`real_declarado` o `prueba_sintetica`. La clasificación se conserva en el resultado;
las figuras sintéticas se identifican visiblemente. `real_declarado` registra la
declaración del usuario, sin certificar la procedencia. La plantilla Code de n8n
revisada está en `plantilla_informe.js`; copie su contenido a `Plantilla HTML
artículo` antes de publicar el workflow. El motor PDF conserva las imágenes
embebidas y el pie de página sin imprimir el CSS del footer.

## Pruebas técnicas aisladas

Instale las dependencias de desarrollo y tenga Node.js disponible. Desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pip install -r api_bot_e030/requirements-desarrollo.txt
.\.venv\Scripts\python.exe -m api_bot_e030.pruebas_tecnicas
```

Puede indicar el ejecutable Node con `RC_BOT_NODE` y una carpeta de evidencias
con `RC_BOT_OUTPUT_DIR`. De forma predeterminada se usa `outputs/pruebas_tecnicas`.
Las pruebas usan un token local exclusivo y SQLite temporal. No contactan Render,
Telegram ni un proveedor de IA. La fila utilizada procede del Excel GENERADO de
entrenamiento; el JSON, las figuras y el PDF se identifican como pruebas sintéticas.
Se comprueban autenticación local, esquema, validación, ocho predicciones finitas
contra la inferencia directa del mismo artefacto, idempotencia, PNG, PDF, imagen
embebida, cifras y rechazo de entradas incorrectas. Esto verifica implementación;
no mide precisión ni constituye validación científica o prueba de n8n Cloud.

La plantilla del informe se ejecuta en Node con respuestas narrativas fijas de
prueba. La credencial y la respuesta del LLM deben probarse por separado.

## Ingresar datos de una estructura

La plantilla Excel entregada contiene 107 variables en `Entradas` y el diccionario
extraído de `modelo_final.joblib`. Complete Valor y Fuente; preserve nombres y
unidades. Los límites son los del dominio de entrenamiento. Los campos de pisos,
vanos y paños inexistentes se dejan vacíos según su aplicabilidad, sin reemplazarlos
por ceros. Para revisar el archivo y crear un JSON local sin enviar información:

```powershell
.\.venv\Scripts\python.exe -m api_bot_e030.importar_excel C:\ruta\RC_Bot_plantilla_107.xlsx --salida consulta_validada.json
```

Este comando no consulta la IA ni el modelo predictivo; valida el formato y dominio
con el validador del backend. No implica que el trigger Telegram acepte archivos
Excel: esa recepción necesita una rama específica. Para el flujo de texto actual,
registre los valores por grupos, revise `/resumen` y confirme solo cuando coincidan
con la fuente técnica.
