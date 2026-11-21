"""Reporte PDF con datos, resumen, tabla de iteraciones, gráficas y procedimiento paso a paso."""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from metodos.formato import fmt
from metodos.resultado import CRITERIOS, Resultado

from .graficas import grafica_error, grafica_funcion

AZUL_OSCURO = colors.HexColor("#0f2d57")
AZUL_CLARO = colors.HexColor("#e8f0fb")
VERDE = colors.HexColor("#15803d")
ROJO = colors.HexColor("#b91c1c")
NARANJA = colors.HexColor("#b45309")

# DejaVu Sans viene incluida con matplotlib y tiene símbolos como ε, ₙ, ≈, →
_FUENTES = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DejaVu", str(_FUENTES / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(_FUENTES / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", parent=base["Title"], fontName="DejaVu-Bold", fontSize=18,
                                 textColor=AZUL_OSCURO, spaceAfter=4),
        "subtitulo": ParagraphStyle("subtitulo", parent=base["Normal"], fontName="DejaVu", fontSize=9,
                                    textColor=colors.HexColor("#475569"), alignment=TA_CENTER),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="DejaVu-Bold", fontSize=13,
                             textColor=AZUL_OSCURO, spaceBefore=10, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName="DejaVu-Bold", fontSize=10,
                             textColor=AZUL_OSCURO, spaceBefore=6, spaceAfter=2),
        "normal": ParagraphStyle("normal", parent=base["Normal"], fontName="DejaVu", fontSize=9, leading=13),
        "paso": ParagraphStyle("paso", parent=base["Normal"], fontName="DejaVu", fontSize=8.5, leading=12,
                               leftIndent=12),
        "celda": ParagraphStyle("celda", parent=base["Normal"], fontName="DejaVu", fontSize=8, leading=10),
    }


def _tabla_clave_valor(filas, estilos, anchos):
    datos = [[Paragraph(f"<b>{escape(k)}</b>", estilos["celda"]), Paragraph(escape(v), estilos["celda"])]
             for k, v in filas]
    t = Table(datos, colWidths=anchos)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), AZUL_CLARO),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _pie_de_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFont("DejaVu", 7.5)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(1.5 * cm, 0.9 * cm, "Solucionador de Ecuaciones — Métodos de Falsa Posición y Newton-Raphson")
    canvas.drawRightString(doc.pagesize[0] - 1.5 * cm, 0.9 * cm, f"Página {doc.page}")
    canvas.restoreState()


def generar_pdf(r: Resultado) -> bytes:
    d = r.decimales
    est = _estilos()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.3 * cm, bottomMargin=1.5 * cm,
                            title=f"Reporte {r.nombre_metodo}", author="Solucionador de Ecuaciones")
    ancho_util = doc.width
    h = []

    h.append(Paragraph(f"Reporte del método de {escape(r.nombre_metodo)}", est["titulo"]))
    h.append(Paragraph(f"Generado el {datetime.now():%d/%m/%Y %H:%M}", est["subtitulo"]))
    h.append(Spacer(1, 10))

    # --- Datos de entrada y resumen, lado a lado
    p = r.parametros
    entradas = [("Método", r.nombre_metodo), ("Función", f"f(x) = {r.funcion}")]
    if r.derivada:
        entradas.append(("Derivada", f"f'(x) = {r.derivada}"))
    if r.metodo == "falsa_posicion":
        entradas += [("Límite inferior (a)", fmt(p["a"], d)), ("Límite superior (b)", fmt(p["b"], d))]
    else:
        entradas.append(("Valor inicial (x₀)", fmt(p["x0"], d)))
    entradas += [
        ("Tolerancia (ε)", f"{p['tolerancia']:g}" + (" %" if p["criterio"] == "relativo" else "")),
        ("Máximo de iteraciones", str(p["max_iter"])),
        ("Criterio de parada", CRITERIOS[p["criterio"]]),
        ("Fórmula", r.formula.texto),
    ]
    resumen = [
        ("Estado", r.etiqueta_estado),
        ("Raíz aproximada", "—" if r.raiz is None else f"x ≈ {fmt(r.raiz, d)}"),
        ("f(raíz)", fmt(r.f_raiz, d)),
        ("Error aproximado", fmt(r.error, d) + (" %" if p["criterio"] == "relativo" and r.error is not None else "")),
        ("Iteraciones realizadas", str(r.n_iteraciones)),
        ("Mensaje", r.mensaje),
    ]
    mitad = (ancho_util - 0.6 * cm) / 2
    bloque = Table(
        [[Paragraph("Datos de entrada", est["h2"]), Paragraph("Resumen de resultados", est["h2"])],
         [_tabla_clave_valor(entradas, est, [4 * cm, mitad - 4 * cm]),
          _tabla_clave_valor(resumen, est, [4 * cm, mitad - 4 * cm])]],
        colWidths=[mitad + 0.3 * cm, mitad + 0.3 * cm],
    )
    bloque.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    h.append(bloque)

    color_estado = {"convergio": VERDE, "max_iter": NARANJA, "fallo": ROJO}[r.estado]
    h.append(Spacer(1, 4))
    h.append(Paragraph(f'<font color="{color_estado.hexval()}"><b>{escape(r.etiqueta_estado)}:</b></font> '
                       f"{escape(r.mensaje)}", est["normal"]))

    # --- Gráficas
    h.append(KeepTogether([
        Paragraph("Gráfica de la función", est["h2"]),
        Image(io.BytesIO(grafica_funcion(r)), width=17 * cm, height=7.3 * cm, kind="proportional"),
    ]))
    png_error = grafica_error(r)
    if png_error:
        h.append(KeepTogether([
            Paragraph("Convergencia del error", est["h2"]),
            Image(io.BytesIO(png_error), width=19 * cm, height=7.4 * cm, kind="proportional"),
        ]))

    # --- Tabla de iteraciones
    h.append(Paragraph(f"Tabla de iteraciones ({escape(r.nombre_metodo)})", est["h2"]))
    if r.iteraciones:
        encabezado = [c["titulo"] for c in r.columnas]
        filas = [encabezado]
        for it in r.iteraciones:
            fila = []
            for c in r.columnas:
                v = it.get(c["clave"])
                if c["clave"] == "iteracion" or isinstance(v, str):
                    fila.append(str(v))
                else:
                    fila.append(fmt(v, d))
            filas.append(fila)
        anchos = [ancho_util / len(encabezado)] * len(encabezado)
        tabla = Table(filas, colWidths=anchos, repeatRows=1)
        estilo = [
            ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
            ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("BACKGROUND", (0, 0), (-1, 0), AZUL_OSCURO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fd")]),
        ]
        if r.estado == "convergio":
            estilo.append(("BACKGROUND", (0, len(filas) - 1), (-1, len(filas) - 1), colors.HexColor("#dcfce7")))
        tabla.setStyle(TableStyle(estilo))
        h.append(tabla)
    else:
        h.append(Paragraph("No se realizaron iteraciones.", est["normal"]))

    # --- Procedimiento
    h.append(PageBreak())
    h.append(Paragraph("Procedimiento paso a paso", est["h2"]))
    h.append(Paragraph(f"<b>Fórmula del método:</b> {escape(r.formula.texto)}", est["normal"]))
    for paso in r.pasos:
        contenido = [Paragraph(escape(paso.titulo), est["h3"])]
        contenido += [Paragraph(escape(linea.texto), est["paso"]) for linea in paso.lineas]
        h.append(KeepTogether(contenido))

    doc.build(h, onFirstPage=_pie_de_pagina, onLaterPages=_pie_de_pagina)
    return buffer.getvalue()
