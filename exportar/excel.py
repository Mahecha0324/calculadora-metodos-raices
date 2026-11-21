"""Libro de Excel con: Resumen, Iteraciones, Procedimiento y Gráficas (gráficos nativos de Excel)."""
from __future__ import annotations

import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.chart.marker import Marker
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from metodos.resultado import CRITERIOS, Resultado

AZUL = "0F2D57"
AZUL_CLARO = "E8F0FB"
VERDE_CLARO = "DCFCE7"
COLORES_ESTADO = {"convergio": "15803D", "max_iter": "B45309", "fallo": "B91C1C"}
BORDE = Border(*(Side(style="thin", color="CBD5E1"),) * 4)
ENCABEZADO = Font(bold=True, color="FFFFFF")
RELLENO_ENCABEZADO = PatternFill("solid", fgColor=AZUL)


def _formato_numero(decimales: int) -> str:
    return "0." + "0" * decimales


def _hoja_resumen(wb: Workbook, r: Resultado, fmt_num: str) -> None:
    ws = wb.active
    ws.title = "Resumen"
    ws["A1"] = f"Reporte del método de {r.nombre_metodo}"
    ws["A1"].font = Font(bold=True, size=16, color=AZUL)
    ws["A2"] = f"Generado el {datetime.now():%d/%m/%Y %H:%M}"
    ws["A2"].font = Font(italic=True, color="64748B")

    p = r.parametros
    filas = [("DATOS DE ENTRADA", None), ("Método", r.nombre_metodo), ("Función f(x)", r.funcion)]
    if r.derivada:
        filas.append(("Derivada f'(x)", r.derivada))
    if r.metodo == "falsa_posicion":
        filas += [("Límite inferior (a)", p["a"]), ("Límite superior (b)", p["b"])]
    else:
        filas.append(("Valor inicial (x0)", p["x0"]))
    filas += [
        ("Tolerancia (ε)", p["tolerancia"]),
        ("Máximo de iteraciones", p["max_iter"]),
        ("Criterio de parada", CRITERIOS[p["criterio"]]),
        ("Fórmula", r.formula.texto),
        (None, None),
        ("RESULTADOS", None),
        ("Estado", r.etiqueta_estado),
        ("Raíz aproximada", r.raiz),
        ("f(raíz)", r.f_raiz),
        ("Error aproximado", r.error),
        ("Iteraciones realizadas", r.n_iteraciones),
        ("Mensaje", r.mensaje),
    ]
    fila_excel = 4
    for clave, valor in filas:
        if clave is None:
            fila_excel += 1
            continue
        celda_clave = ws.cell(row=fila_excel, column=1, value=clave)
        if valor is None and clave.isupper():
            celda_clave.font = ENCABEZADO
            celda_clave.fill = RELLENO_ENCABEZADO
            ws.cell(row=fila_excel, column=2).fill = RELLENO_ENCABEZADO
        else:
            celda_clave.font = Font(bold=True)
            celda_clave.fill = PatternFill("solid", fgColor=AZUL_CLARO)
            celda_valor = ws.cell(row=fila_excel, column=2, value="—" if valor is None else valor)
            celda_valor.alignment = Alignment(wrap_text=True, vertical="center", horizontal="left")
            if isinstance(valor, (int, float)) and clave not in ("Máximo de iteraciones", "Iteraciones realizadas"):
                celda_valor.number_format = fmt_num if clave != "Tolerancia (ε)" else "General"
            if clave == "Estado":
                celda_valor.font = Font(bold=True, color=COLORES_ESTADO[r.estado])
            celda_clave.border = celda_valor.border = BORDE
        fila_excel += 1
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 70


def _hoja_iteraciones(wb: Workbook, r: Resultado, fmt_num: str) -> None:
    ws = wb.create_sheet("Iteraciones")
    for col, c in enumerate(r.columnas, start=1):
        celda = ws.cell(row=1, column=col, value=c["titulo"])
        celda.font = ENCABEZADO
        celda.fill = RELLENO_ENCABEZADO
        celda.alignment = Alignment(horizontal="center")
        celda.border = BORDE
        ws.column_dimensions[get_column_letter(col)].width = 10 if c["clave"] == "iteracion" else 17
    for fila, it in enumerate(r.iteraciones, start=2):
        for col, c in enumerate(r.columnas, start=1):
            v = it.get(c["clave"])
            celda = ws.cell(row=fila, column=col, value="—" if v is None else v)
            celda.border = BORDE
            celda.alignment = Alignment(horizontal="center")
            if isinstance(v, (int, float)) and c["clave"] != "iteracion":
                celda.number_format = fmt_num
            if r.estado == "convergio" and fila == len(r.iteraciones) + 1:
                celda.fill = PatternFill("solid", fgColor=VERDE_CLARO)
    ws.freeze_panes = "A2"
    if r.iteraciones:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(r.columnas))}{len(r.iteraciones) + 1}"


def _hoja_procedimiento(wb: Workbook, r: Resultado) -> None:
    ws = wb.create_sheet("Procedimiento")
    ws["A1"] = "Procedimiento paso a paso"
    ws["A1"].font = Font(bold=True, size=14, color=AZUL)
    ws["A2"] = f"Fórmula: {r.formula.texto}"
    ws["A2"].font = Font(italic=True)
    fila = 4
    for paso in r.pasos:
        celda = ws.cell(row=fila, column=1, value=paso.titulo)
        celda.font = ENCABEZADO
        celda.fill = RELLENO_ENCABEZADO
        fila += 1
        for linea in paso.lineas:
            ws.cell(row=fila, column=1, value="   " + linea.texto)
            fila += 1
        fila += 1
    ws.column_dimensions["A"].width = 130


def _hoja_graficas(wb: Workbook, r: Resultado, fmt_num: str) -> None:
    ws = wb.create_sheet("Gráficas")
    g = r.grafica

    # Columnas A-B: curva de la función
    ws.append(["x", "f(x)", None, "Aproximación", "x", "f(x)", None, "Iteración", "Error abs."])
    for col in range(1, 10):
        ws.cell(row=1, column=col).font = Font(bold=True)
    for i, (x, y) in enumerate(zip(g["x"], g["y"]), start=2):
        ws.cell(row=i, column=1, value=x).number_format = fmt_num
        ws.cell(row=i, column=2, value=y).number_format = fmt_num
    n_curva = len(g["x"])

    # Columnas D-F: aproximaciones del método
    for i, punto in enumerate(g["puntos"], start=2):
        ws.cell(row=i, column=4, value=punto["n"])
        ws.cell(row=i, column=5, value=punto["x"]).number_format = fmt_num
        ws.cell(row=i, column=6, value=punto["y"]).number_format = fmt_num
    n_puntos = len(g["puntos"])

    # Columnas H-I: error por iteración
    errores = [e for e in g["errores"] if e["ea"] is not None]
    for i, e in enumerate(errores, start=2):
        ws.cell(row=i, column=8, value=e["n"])
        ws.cell(row=i, column=9, value=e["ea"]).number_format = fmt_num

    # Gráfico 1: función + aproximaciones + raíz
    graf = ScatterChart()
    graf.title = f"f(x) = {r.funcion}"
    graf.style = 13
    graf.x_axis.title = "x"
    graf.y_axis.title = "f(x)"
    graf.height, graf.width = 10, 18
    graf.x_axis.scaling.min, graf.x_axis.scaling.max = g["rango_x"]
    graf.y_axis.scaling.min, graf.y_axis.scaling.max = g["rango_y"]
    graf.x_axis.delete = False
    graf.y_axis.delete = False
    graf.x_axis.number_format = "0.00"
    graf.y_axis.number_format = "0.00"

    curva = Series(Reference(ws, min_col=2, min_row=2, max_row=n_curva + 1),
                   Reference(ws, min_col=1, min_row=2, max_row=n_curva + 1), title="f(x)")
    curva.marker = Marker(symbol="none")
    curva.graphicalProperties.line.solidFill = "1D4ED8"
    curva.graphicalProperties.line.width = 25000
    curva.smooth = True
    graf.series.append(curva)

    if n_puntos:
        aprox = Series(Reference(ws, min_col=6, min_row=2, max_row=n_puntos + 1),
                       Reference(ws, min_col=5, min_row=2, max_row=n_puntos + 1), title="Aproximaciones")
        aprox.marker = Marker(symbol="circle", size=7)
        aprox.marker.graphicalProperties.solidFill = "F59E0B"
        aprox.marker.graphicalProperties.line.solidFill = "B45309"
        aprox.graphicalProperties.line.noFill = True
        graf.series.append(aprox)

    if n_puntos and g["raiz"]:
        raiz = Series(Reference(ws, min_col=6, min_row=n_puntos + 1),
                      Reference(ws, min_col=5, min_row=n_puntos + 1), title="Raíz aproximada")
        raiz.marker = Marker(symbol="diamond", size=10)
        raiz.marker.graphicalProperties.solidFill = "DC2626"
        raiz.marker.graphicalProperties.line.solidFill = "DC2626"
        raiz.graphicalProperties.line.noFill = True
        graf.series.append(raiz)
    ws.add_chart(graf, "K2")

    # Gráfico 2: convergencia del error
    if len(errores) >= 2:
        graf_e = ScatterChart()
        graf_e.title = "Convergencia del error"
        graf_e.style = 13
        graf_e.x_axis.title = "Iteración"
        graf_e.y_axis.title = "Error absoluto"
        graf_e.height, graf_e.width = 8, 18
        graf_e.x_axis.delete = False
        graf_e.y_axis.delete = False
        if all(e["ea"] > 0 for e in errores):
            graf_e.y_axis.scaling.logBase = 10
        serie = Series(Reference(ws, min_col=9, min_row=2, max_row=len(errores) + 1),
                       Reference(ws, min_col=8, min_row=2, max_row=len(errores) + 1), title="Error abs.")
        serie.marker = Marker(symbol="circle", size=6)
        serie.graphicalProperties.line.solidFill = "1D4ED8"
        graf_e.series.append(serie)
        ws.add_chart(graf_e, "K24")

    for col, ancho in zip("ABCDEFGHI", [14, 14, 3, 13, 14, 14, 3, 10, 14]):
        ws.column_dimensions[col].width = ancho


def generar_excel(r: Resultado) -> bytes:
    fmt_num = _formato_numero(r.decimales)
    wb = Workbook()
    _hoja_resumen(wb, r, fmt_num)
    _hoja_iteraciones(wb, r, fmt_num)
    _hoja_procedimiento(wb, r)
    _hoja_graficas(wb, r, fmt_num)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
