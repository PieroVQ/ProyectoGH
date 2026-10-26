"""Figuras deterministas a partir de entradas y salidas guardadas, sin análisis adicional."""
from __future__ import annotations

from io import BytesIO
from threading import RLock
from typing import Any

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

_RENDER_LOCK = RLock()
FIGURES = {
    "geometria": ("geometria.png", "Geometría idealizada según luces y alturas confirmadas; sin deformaciones."),
    "predicciones": ("predicciones.png", "Ocho salidas del modelo agrupadas por unidad; sin comparación normativa."),
}


def figure_metadata() -> list[dict[str, str]]:
    return [{"archivo_id": key, "nombre": name, "mime": "image/png", "descripcion": desc}
            for key, (name, desc) in FIGURES.items()]


def render_figure(result: dict[str, Any], figure_id: str) -> bytes:
    if figure_id not in FIGURES:
        raise KeyError(figure_id)
    with _RENDER_LOCK:
        fig = Figure(figsize=(10, 7), dpi=130, facecolor="white")
        try:
            if figure_id == "geometria":
                _geometry(fig, result)
            else:
                _predictions(fig, result)
            synthetic = result.get("origen_datos") == "prueba_sintetica"
            label = "PRUEBA TÉCNICA · DATOS SINTÉTICOS · SIN VALIDACIÓN CIENTÍFICA" if synthetic else "Predicción bajo las hipótesis del proyecto"
            fig.text(.5, .025, label, ha="center", fontsize=9, color="#9c261b" if synthetic else "#455266")
            fig.text(.5, .005, "Consulta " + str(result["consulta_id"]), ha="center", fontsize=7, color="#455266")
            stream = BytesIO()
            FigureCanvasAgg(fig).print_png(stream)
            return stream.getvalue()
        finally:
            fig.clear()


def _geometry(fig: Figure, result: dict[str, Any]) -> None:
    p = result["parametros_confirmados"]
    x = np.r_[0, np.cumsum([p[f"luz_X_{i}_cm"] for i in range(1, int(p["vanos_X"]) + 1)])]
    y = np.r_[0, np.cumsum([p[f"luz_Y_{i}_cm"] for i in range(1, int(p["vanos_Y"]) + 1)])]
    z = np.r_[0, np.cumsum([p[f"piso{i}_altura_cm"] for i in range(1, int(p["pisos"]) + 1)])]
    ax = fig.add_subplot(111, projection="3d")
    for xi in x:
        for yi in y:
            ax.plot([xi, xi], [yi, yi], [0, z[-1]], color="#475569", linewidth=.8)
    for zi in z[1:]:
        for yi in y:
            ax.plot(x, np.full(len(x), yi), np.full(len(x), zi), color="#2563eb", linewidth=1)
        for xi in x:
            ax.plot(np.full(len(y), xi), y, np.full(len(y), zi), color="#2563eb", linewidth=1)
    ax.set(xlabel="X (cm)", ylabel="Y (cm)", zlabel="Altura (cm)", title="Geometría idealizada de los ejes del pórtico")
    ax.set_box_aspect((x[-1], y[-1], z[-1]))
    ax.view_init(elev=24, azim=-55)
    fig.subplots_adjust(bottom=.13, top=.90, left=.02, right=.98)
    fig.text(.5, .085, "Ejes definidos por las entradas; no representa desplazamientos ni daños.", ha="center", fontsize=9)


def _predictions(fig: Figure, result: dict[str, Any]) -> None:
    values = {p["nombre"]: float(p["valor"]) for p in result["predicciones"]}
    groups = [
        ("Períodos", "s", ["Tx_s", "Ty_s"]),
        ("Cortante modal ajustado", "kgf", ["V_modal_ajustado_X_kgf", "V_modal_ajustado_Y_kgf"]),
        ("Desplazamiento máximo del techo", "cm", ["desplazamiento_techo_max_X_cm", "desplazamiento_techo_max_Y_cm"]),
        ("Deriva máxima", "adimensional", ["deriva_max_X", "deriva_max_Y"]),
    ]
    for ax, (title, unit, names) in zip(fig.subplots(2, 2).flat, groups):
        bars = ax.bar(["X", "Y"], [values[k] for k in names], color=["#2563eb", "#0f766e"], width=.5)
        ax.bar_label(bars, labels=[f"{values[k]:.6g}" for k in names], padding=5, fontsize=10)
        ax.set(title=title, ylabel=unit)
        ax.margins(y=.25)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=.15)
        ax.set_axisbelow(True)
    fig.suptitle("Salidas del modelo E.030", fontsize=15)
    fig.subplots_adjust(bottom=.14, top=.86, hspace=.48, wspace=.35)
