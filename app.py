"""Servidor web (Flask) del Solucionador de Ecuaciones.

Ejecutar:   python app.py      y abrir   http://127.0.0.1:5000
"""
from __future__ import annotations

import io
from datetime import datetime

from flask import Flask, Response, jsonify, render_template, request, send_file

from exportar.excel import generar_excel
from exportar.pdf import generar_pdf
from metodos.funcion import ErrorFuncion
from metodos.servicio import ErrorValidacion, resolver, vista_previa

app = Flask(__name__)

_plotly_js: str | None = None


@app.get("/")
def inicio():
    return render_template("index.html")


@app.get("/vendor/plotly.min.js")
def plotly_js():
    """Sirve Plotly.js desde el paquete de Python instalado: la página funciona sin internet."""
    global _plotly_js
    if _plotly_js is None:
        from plotly.offline import get_plotlyjs

        _plotly_js = get_plotlyjs()
    respuesta = Response(_plotly_js, mimetype="application/javascript")
    respuesta.headers["Cache-Control"] = "public, max-age=86400"
    return respuesta


def _datos_json() -> dict:
    datos = request.get_json(silent=True)
    return datos if isinstance(datos, dict) else {}


@app.post("/api/vista-previa")
def api_vista_previa():
    try:
        return jsonify(ok=True, **vista_previa(_datos_json().get("funcion")))
    except ErrorFuncion as exc:
        return jsonify(ok=False, error=str(exc))


@app.post("/api/resolver")
def api_resolver():
    try:
        resultado = resolver(_datos_json())
    except ErrorValidacion as exc:
        return jsonify(ok=False, errores=exc.errores), 400
    return jsonify(ok=True, resultado=resultado.to_dict())


@app.post("/api/exportar/<formato>")
def api_exportar(formato: str):
    if formato not in ("pdf", "excel"):
        return jsonify(ok=False, error="Formato no soportado."), 404
    try:
        resultado = resolver(_datos_json())
    except ErrorValidacion as exc:
        return jsonify(ok=False, errores=exc.errores), 400

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    if formato == "pdf":
        contenido, tipo, extension = generar_pdf(resultado), "application/pdf", "pdf"
    else:
        contenido = generar_excel(resultado)
        tipo = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        extension = "xlsx"
    return send_file(io.BytesIO(contenido), mimetype=tipo, as_attachment=True,
                     download_name=f"{resultado.metodo}_{marca}.{extension}")


if __name__ == "__main__":
    app.run(debug=True)
