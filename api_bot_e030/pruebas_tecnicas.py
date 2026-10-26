"""Pruebas aisladas con una fila de la base GENERADA; no validación científica.

Ejecutar desde la raíz: .venv/Scripts/python.exe -m api_bot_e030.pruebas_tecnicas
No llama Telegram, DeepSeek, Render ni otros servicios externos.
"""
from __future__ import annotations

import copy
import io
import json
import math
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.TemporaryDirectory(prefix="rc_bot_tecnico_")
os.environ["BOT_DB_PATH"] = str(Path(_TMP.name) / "consultas.sqlite3")
os.environ["BOT_API_TOKEN"] = "credencial-exclusiva-de-prueba-local"

import pandas as pd
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader
from api_bot_e030 import main as api

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.getenv("RC_BOT_OUTPUT_DIR", str(ROOT / "outputs/pruebas_tecnicas")))
AUTH = {"Authorization": "Bearer " + os.environ["BOT_API_TOKEN"]}
CLIENT = TestClient(api.app)
EVIDENCE: dict = {"alcance": "Prueba técnica local aislada; datos sintéticos generados; sin validación científica", "casos": {}}


class TechnicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True, exist_ok=True)
        row = pd.read_excel(ROOT / "base_ml_ampliada/estructuras.xlsx", nrows=1).iloc[0]
        cls.payload = {
            "session_id": "prueba-tecnica-local",
            "idempotency_key": "prueba-tecnica-local-001",
            "chat_id": "chat-sintetico-no-enviar",
            "user_id": "usuario-sintetico-no-enviar",
            "origen_datos": "prueba_sintetica",
            "parametros": {k: None if pd.isna(row[k]) else float(row[k]) for k in api.INPUTS},
            "unidades": {k: api.metadata_for(k)["unidad"] for k in api.INPUTS},
            "supuestos_aceptados": [],
        }
        (OUT / "caso_sintetico_generado.json").write_text(json.dumps({
            "advertencia": "DATOS SINTÉTICOS GENERADOS; no corresponden a un edificio real",
            "fuente": "base_ml_ampliada/estructuras.xlsx, primera fila de la base generada",
            "solicitud": cls.payload,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        meta = [{"orden": i + 1, "nombre": k, **api.metadata_for(k), "dominio": api.DOMAIN[k]}
                for i, k in enumerate(api.INPUTS)]
        (OUT / "esquema_107.json").write_text(json.dumps({
            "modelo_sha256": api.MODEL_SHA256, "entradas": meta, "objetivos": api.TARGETS,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def ensure_query(self):
        r = CLIENT.post("/consultas", headers=AUTH, json=self.payload)
        self.assertEqual(r.status_code, 200, r.text)
        result = CLIENT.get("/consultas/" + r.json()["consulta_id"], headers=AUTH)
        self.assertEqual(result.status_code, 200)
        return result.json()

    def test_01_auth_and_schema(self):
        self.assertEqual(CLIENT.get("/schema").status_code, 401)
        self.assertEqual(CLIENT.get("/schema", headers={"Authorization": "Bearer incorrecta"}).status_code, 401)
        r = CLIENT.get("/schema", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["entradas"], api.INPUTS)
        self.assertEqual(len(r.json()["campos"]), 107)
        self.assertEqual(len(r.json()["objetivos"]), 8)
        EVIDENCE["casos"]["auth_local_y_esquema"] = "401 sin credencial/incorrecta; 200 con credencial local; 107 entradas/8 salidas"

    def test_02_valid_synthetic(self):
        r = CLIENT.post("/consultas/validar", headers=AUTH, json=self.payload)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["valido"], r.text)

    def test_03_reject_missing_units_and_boolean(self):
        p = copy.deepcopy(self.payload)
        p["unidades"] = {}
        self.assertFalse(CLIENT.post("/consultas/validar", headers=AUTH, json=p).json()["valido"])
        p = copy.deepcopy(self.payload)
        p["parametros"]["fc_kgf_cm2"] = True
        self.assertEqual(CLIENT.post("/consultas", headers=AUTH, json=p).status_code, 422)
        p["parametros"].pop("fc_kgf_cm2")
        self.assertEqual(CLIENT.post("/consultas", headers=AUTH, json=p).status_code, 422)

    def test_04_eight_predictions(self):
        r = self.ensure_query()
        self.assertEqual(r["origen_datos"], "prueba_sintetica")
        self.assertEqual(len(r["entradas_107"]), 107)
        self.assertEqual([p["nombre"] for p in r["predicciones"]], api.TARGETS)
        frame, errors, _ = api.validate(api.ValidationRequest(**self.payload))
        self.assertFalse(errors)
        for p in r["predicciones"]:
            self.assertTrue(math.isfinite(p["valor"]))
            self.assertTrue(p["unidad"])
            self.assertAlmostEqual(p["valor"], float(api.PACKAGE["modelos"][p["nombre"]].predict(frame)[0]), places=10)
        self.assertEqual(r["modelo"]["version"], api.MODEL_SHA256[:12])
        (OUT / "resultado_sintetico.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        EVIDENCE["casos"]["inferencia_sintetica"] = {"consulta_id": r["consulta_id"], "modelo_version": r["modelo"]["version"], "salidas": r["predicciones"]}

    def test_05_idempotency_and_minimization(self):
        a = self.ensure_query()
        b = self.ensure_query()
        self.assertEqual(a["consulta_id"], b["consulta_id"])
        with api.connect_db() as db:
            records = db.execute("SELECT idempotency_key,resultado_json FROM consultas").fetchall()
        self.assertEqual(len(records), 1)
        stored = json.dumps(records)
        self.assertNotIn(self.payload["chat_id"], stored)
        self.assertNotIn(self.payload["user_id"], stored)
        self.assertNotIn(self.payload["idempotency_key"], stored)

    def test_06_png_files(self):
        r = self.ensure_query()
        self.assertEqual([f["archivo_id"] for f in r["archivos"]], ["geometria", "predicciones"])
        for f in r["archivos"]:
            url = f"/consultas/{r['consulta_id']}/archivos/{f['archivo_id']}"
            self.assertEqual(CLIENT.get(url).status_code, 401)
            download = CLIENT.get(url, headers=AUTH)
            self.assertEqual(download.status_code, 200, download.text[:100] if download.status_code != 200 else "")
            self.assertEqual(download.headers["content-type"], "image/png")
            with Image.open(io.BytesIO(download.content)) as image:
                self.assertEqual(image.size, (1300, 910))
                image.verify()
            (OUT / f["nombre"]).write_bytes(download.content)
        self.assertEqual(CLIENT.get(f"/consultas/{r['consulta_id']}/archivos/no-existe", headers=AUTH).status_code, 404)
        self.assertEqual(CLIENT.get("/consultas/no-existe/archivos/geometria", headers=AUTH).status_code, 404)
        EVIDENCE["casos"]["figuras"] = "Dos PNG de 1300x910 verificados; 401 sin credencial; 404 para consulta/archivo inexistentes"

    def test_07_pdf_from_workflow_template(self):
        # Usa la plantilla Code de n8n guardada en el proyecto; las secciones IA
        # son texto fijo de prueba: no se llama un proveedor ni se simula su éxito.
        r = self.ensure_query()
        geometry = CLIENT.get(f"/consultas/{r['consulta_id']}/archivos/geometria", headers=AUTH)
        geometry.raise_for_status()
        (OUT / "resultado_sintetico.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        (OUT / "geometria.png").write_bytes(geometry.content)
        completed = subprocess.run([os.getenv("RC_BOT_NODE", "node"), str(ROOT / "api_bot_e030/probar_plantilla_n8n.mjs")], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.check_pdf((OUT / "index.html").read_text(encoding="utf-8"), r)

    def check_pdf(self, html, result):
        response = CLIENT.post("/informes/pdf", headers=AUTH, files=[
            ("files", ("index.html", html.encode(), "text/html")),
            ("files", ("footer.html", (OUT / "footer.html").read_bytes(), "text/html")),
        ])
        self.assertEqual(response.status_code, 200, response.text[:400] if response.status_code != 200 else "")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertEqual(response.headers["content-type"], "application/pdf")
        reader = PdfReader(io.BytesIO(response.content))
        text = "\n".join(page.extract_text() for page in reader.pages)
        self.assertIn("DATOS SINT", text)
        self.assertIn(result["consulta_id"], text)
        self.assertNotIn("font-family", text)
        self.assertGreaterEqual(sum(len(page.images) for page in reader.pages), 1)
        for target in api.TARGETS:
            self.assertIn(target, text)
        compact = "".join(text.split())
        for prediction in result["predicciones"]:
            self.assertIn(str(prediction["valor"]), compact)
        for name in api.INPUTS:
            self.assertIn(name, text)
        (OUT / "informe_prueba_sintetica.pdf").write_bytes(response.content)
        EVIDENCE["casos"]["pdf"] = {"http": 200, "paginas": len(reader.pages), "bytes": len(response.content), "verificado": "Firma PDF, tipo MIME, texto sintético, ocho variables de salida y las 107 entradas"}

    def test_08_pdf_reject_missing_html(self):
        self.assertEqual(CLIENT.post("/informes/pdf", headers=AUTH, files=[("files", ("otro.html", b"texto", "text/html"))]).status_code, 422)

    def test_09_geometry_consistency(self):
        p = copy.deepcopy(self.payload)
        p["parametros"]["altura_total_cm"] += 1
        self.assertEqual(CLIENT.post("/consultas", headers=AUTH, json=p).status_code, 422)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TechnicalTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    EVIDENCE["resumen"] = {"pruebas": result.testsRun, "fallos": len(result.failures), "errores": len(result.errors)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "evidencia_pruebas.json").write_text(json.dumps(EVIDENCE, ensure_ascii=False, indent=2), encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
