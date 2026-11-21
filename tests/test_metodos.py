"""Pruebas automáticas. Ejecutar con:  python -m pytest"""
import math

import pytest

from app import app
from metodos.funcion import ErrorFuncion, interpretar_funcion, interpretar_numero
from metodos.servicio import ErrorValidacion, resolver

FP = {"metodo": "falsa_posicion", "tolerancia": "1e-8", "max_iter": "100"}
NR = {"metodo": "newton_raphson", "tolerancia": "1e-10", "max_iter": "50"}


# ------------------------------------------------------------- interpretación de la función
@pytest.mark.parametrize("texto, x, esperado", [
    ("x^3 - x - 1", 2, 5),
    ("2x + 1", 3, 7),
    ("sen(x) + cos x", 0, 1),
    ("e^x", 1, math.e),
    ("ln(x) + log10(x)", 10, math.log(10) + 1),
    ("x^2 = 4", 3, 5),
    ("f(x) = sqrt(x)", 9, 3),
])
def test_interpretar_funcion(texto, x, esperado):
    assert interpretar_funcion(texto)(x) == pytest.approx(esperado)


@pytest.mark.parametrize("texto", ["", "x + y", "__import__('os')", "x.__class__", "5", "x^2 +", "1/0 + x",
                                   "open(x)", "lambda: 1"])
def test_funciones_invalidas(texto):
    with pytest.raises(ErrorFuncion):
        interpretar_funcion(texto)


def test_numeros():
    assert interpretar_numero("0,5", "a") == 0.5
    assert interpretar_numero("pi/2", "a") == pytest.approx(math.pi / 2)
    assert interpretar_numero("1e-4", "tol") == 1e-4
    with pytest.raises(ErrorFuncion):
        interpretar_numero("x", "a")


# ------------------------------------------------------------- Falsa Posición
def test_falsa_posicion_cubica():
    r = resolver({**FP, "funcion": "x^3 - x - 1", "a": "1", "b": "2"})
    assert r.estado == "convergio"
    assert r.raiz == pytest.approx(1.324717957244746, abs=1e-7)
    # en cada iteración la raíz queda dentro del intervalo [a, b]
    for it in r.iteraciones:
        assert it["a"] <= it["xr"] <= it["b"]


def test_falsa_posicion_sin_cambio_de_signo():
    with pytest.raises(ErrorValidacion) as exc:
        resolver({**FP, "funcion": "x^2 + 1", "a": "-1", "b": "1"})
    assert "intervalo" in exc.value.errores


def test_falsa_posicion_a_mayor_que_b():
    with pytest.raises(ErrorValidacion) as exc:
        resolver({**FP, "funcion": "x - 1", "a": "3", "b": "0"})
    assert "b" in exc.value.errores


def test_falsa_posicion_raiz_en_extremo():
    r = resolver({**FP, "funcion": "x^2 - 4", "a": "2", "b": "5"})
    assert r.estado == "convergio" and r.raiz == 2


def test_falsa_posicion_maximo_iteraciones():
    r = resolver({**FP, "funcion": "x^3 - x - 1", "a": "0", "b": "2", "max_iter": "3"})
    assert r.estado == "max_iter" and r.n_iteraciones == 3


# ------------------------------------------------------------- Newton-Raphson
def test_newton_coseno():
    r = resolver({**NR, "funcion": "cos(x) - x", "x0": "1"})
    assert r.estado == "convergio"
    assert r.raiz == pytest.approx(0.7390851332151607, abs=1e-10)
    assert r.derivada is not None
    assert r.n_iteraciones <= 6  # convergencia cuadrática


def test_newton_derivada_cero():
    r = resolver({**NR, "funcion": "x^2 - 1", "x0": "0"})
    assert r.estado == "fallo"
    assert "derivada" in r.mensaje.lower()


def test_newton_ciclo():
    r = resolver({**NR, "funcion": "x^3 - 2x + 2", "x0": "0", "max_iter": "20"})
    assert r.estado == "max_iter"


def test_newton_diverge():
    r = resolver({**NR, "funcion": "atan(x)", "x0": "3"})
    assert r.estado == "fallo"
    assert "diverge" in r.mensaje


def test_newton_fuera_de_dominio():
    with pytest.raises(ErrorValidacion) as exc:
        resolver({**NR, "funcion": "ln(x)", "x0": "-1"})
    assert "x0" in exc.value.errores


def test_criterio_relativo():
    r = resolver({**NR, "funcion": "x^2 - 2", "x0": "1", "criterio": "relativo", "tolerancia": "0.001"})
    assert r.estado == "convergio"
    assert r.error < 0.001
    assert r.raiz == pytest.approx(math.sqrt(2), abs=1e-6)


# ------------------------------------------------------------- API y exportaciones
@pytest.fixture
def cliente():
    app.config["TESTING"] = True
    return app.test_client()


def test_api_resolver(cliente):
    resp = cliente.post("/api/resolver", json={**FP, "funcion": "x^3 - x - 1", "a": "0", "b": "2"})
    datos = resp.get_json()
    assert resp.status_code == 200 and datos["ok"]
    assert datos["resultado"]["etiqueta_estado"] == "Convergió"
    assert len(datos["resultado"]["grafica"]["x"]) > 100


def test_api_errores(cliente):
    resp = cliente.post("/api/resolver", json={"metodo": "newton_raphson", "funcion": "x+", "x0": ""})
    assert resp.status_code == 400
    assert {"funcion", "x0", "tolerancia"} <= set(resp.get_json()["errores"])


@pytest.mark.parametrize("formato, firma", [("pdf", b"%PDF"), ("excel", b"PK")])
@pytest.mark.parametrize("datos", [
    {**FP, "funcion": "x^3 - x - 1", "a": "0", "b": "2"},
    {**NR, "funcion": "exp(-x) - x", "x0": "0"},
    {**NR, "funcion": "x^2 - 1", "x0": "0"},  # caso de fallo: también debe exportarse
])
def test_api_exportar(cliente, formato, firma, datos):
    resp = cliente.post(f"/api/exportar/{formato}", json=datos)
    assert resp.status_code == 200
    assert resp.data.startswith(firma)
