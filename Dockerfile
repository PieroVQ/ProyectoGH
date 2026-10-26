FROM python:3.12-slim

WORKDIR /app
COPY api_bot_e030/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY api_bot_e030/main.py /app/api_bot_e030/main.py
COPY api_bot_e030/figuras.py /app/api_bot_e030/figuras.py
COPY base_ml_ampliada/diccionario_columnas.json /app/base_ml_ampliada/diccionario_columnas.json
COPY resultados_ml_optimizado/modelo_final.joblib /app/resultados_ml_optimizado/modelo_final.joblib
COPY resultados_ml_optimizado/modelos_mejorados.py /app/resultados_ml_optimizado/modelos_mejorados.py
COPY resultados_ml_optimizado/variables_utilizadas.json /app/resultados_ml_optimizado/variables_utilizadas.json

ENV PYTHONUNBUFFERED=1
ENV BOT_DB_PATH=/tmp/consultas.sqlite3
CMD ["sh", "-c", "uvicorn api_bot_e030.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
