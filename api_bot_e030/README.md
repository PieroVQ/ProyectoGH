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
