# Solucionador de Ecuaciones — Falsa Posición y Newton-Raphson

Página web en **Python (Flask)** que encuentra raíces de una función f(x) con:

| Método | Tipo | Entradas |
|---|---|---|
| **Falsa Posición** | Cerrado | f(x), límite inferior *a*, límite superior *b*, tolerancia ε, máximo de iteraciones |
| **Newton-Raphson** | Abierto | f(x), valor inicial *x₀*, tolerancia ε, máximo de iteraciones (la derivada se calcula sola) |

Muestra la **tabla de iteraciones**, la **gráfica** (función, aproximaciones, rectas secantes/tangentes y convergencia del error), el **procedimiento paso a paso** con las fórmulas sustituidas y el **resumen** (raíz, error, iteraciones y estado). Todo se puede **exportar a PDF y a Excel**.

---

## 1. Cómo ejecutarlo en Visual Studio Code

Requisitos: **Python 3.10 o superior** y la extensión **Python** de VS Code.

1. Abra la carpeta `metodos-numericos` en VS Code (*Archivo → Abrir carpeta*).
2. Abra una terminal (*Terminal → Nueva terminal*) y cree un entorno virtual:

   **Windows (PowerShell)**
   ```bash
   python -m venv .venv
   ```
   ```bash
   .venv\Scripts\activate
   ```

   **macOS / Linux**
   ```bash
   python3 -m venv .venv
   ```
   ```bash
   source .venv/bin/activate
   ```

3. Instale las librerías:
   ```bash
   pip install -r requirements.txt
   ```
4. Ejecute la aplicación:
   ```bash
   python app.py
   ```
5. Abra en el navegador: **http://127.0.0.1:5000**

> También puede presionar **F5** en VS Code y elegir **"Ejecutar página web (Flask)"** (ya está configurado en `.vscode/launch.json`).
> Si VS Code pregunta por el intérprete, elija el de `.venv`.

La página funciona **sin internet**: Plotly se sirve desde la librería de Python y KaTeX está incluido en `static/vendor`.

### Pruebas automáticas
```bash
python -m pytest -v
```

---

## 2. Estructura del proyecto

```
metodos-numericos/
├── app.py                    # Servidor Flask: rutas de la página, API y exportaciones
├── metodos/
│   ├── funcion.py            # Lectura segura de f(x) con SymPy, derivada automática
│   ├── falsa_posicion.py     # Método cerrado
│   ├── newton_raphson.py     # Método abierto
│   ├── resultado.py          # Estructura del resultado, errores, criterio de parada, datos de la gráfica
│   ├── servicio.py           # Validación de los datos del formulario
│   └── formato.py            # Formato de números
├── exportar/
│   ├── pdf.py                # Reporte PDF (ReportLab)
│   ├── excel.py              # Libro Excel con gráficos nativos (openpyxl)
│   └── graficas.py           # Gráficas PNG para el PDF (matplotlib)
├── templates/index.html      # Interfaz
├── static/css/styles.css     # Estilos (tema claro/oscuro, adaptable a celular)
├── static/js/app.js          # Lógica de la interfaz, Plotly, pestañas, exportar
├── static/vendor/katex/      # Librería para mostrar fórmulas
└── tests/test_metodos.py     # Pruebas
```

---

## 3. Cómo escribir la función

| Escribe | Significa |
|---|---|
| `x^3 - x - 1` o `x**3 - x - 1` | x³ − x − 1 |
| `2x` o `2*x` | 2·x |
| `sin(x)`, `sen(x)`, `cos(x)`, `tan(x)` | trigonométricas (en radianes) |
| `exp(x)` o `e^x` | eˣ |
| `ln(x)` o `log(x)` | logaritmo natural · `log10(x)` logaritmo base 10 |
| `sqrt(x)` | √x · `abs(x)` valor absoluto |
| `pi`, `e` | constantes |
| `x^2 = 2` | también se aceptan ecuaciones (se convierte en x² − 2) |

En los campos numéricos se acepta `0.5`, `0,5`, `1e-4`, `pi/2`, `sqrt(2)`.

---

## 4. Métodos implementados

**Falsa Posición**

  xᵣ = b − f(b)·(b − a) / (f(b) − f(a))

Si f(a)·f(xᵣ) < 0 la raíz está en [a, xᵣ] → b = xᵣ; si es > 0 está en [xᵣ, b] → a = xᵣ.

**Newton-Raphson**

  xₙ₊₁ = xₙ − f(xₙ) / f′(xₙ)

**Error y criterio de parada** (se elige en *Opciones avanzadas*):

- Error absoluto: Eₐ = |xₙ − xₙ₋₁| < ε *(predeterminado)*
- Error relativo porcentual: Eᵣ = |xₙ − xₙ₋₁| / |xₙ| · 100 < ε %

---

## 5. Validaciones

- Función vacía, con sintaxis inválida, con variables distintas de *x* o con caracteres no permitidos.
- Campos vacíos o no numéricos; tolerancia > 0; iteraciones enteras entre 1 y 1000.
- Falsa Posición: *a* < *b*, la función debe estar definida en *a* y *b* y **debe existir cambio de signo**.
- Newton-Raphson: la función debe estar definida en x₀; se detecta **derivada cero**, **divergencia** y **puntos fuera del dominio** (ej. ln de un negativo) durante las iteraciones.
- Si no se alcanza la tolerancia se informa "No convergió" con la última aproximación.

---

## 6. Ejemplos incluidos (menú "Ejemplos")

| Función | Raíz |
|---|---|
| x³ − x − 1 | 1.324718 |
| cos(x) − x | 0.739085 |
| e⁻ˣ − x | 0.567143 |
| x² − 2 | 1.414214 (√2) |
| ln(x) + x − 2 | 1.557146 |
| x·sen(x) − 1 | 1.114157 |
| x³ − 2x + 2 con x₀ = 0 | Newton entra en un ciclo 0 → 1 → 0 (no converge) |
| x² − 1 con x₀ = 0 | Newton falla: f′(0) = 0 |

---

## 7. Publicar la página en internet (GitHub + Render)

1. **Subir el código a GitHub**
   - Cree un repositorio nuevo en https://github.com/new (por ejemplo `calculadora-metodos-numericos`).
   - Desde la carpeta del proyecto, en la terminal de VS Code:
     ```bash
     git init
     git add .
     git commit -m "Calculadora de Falsa Posición y Newton-Raphson"
     git branch -M main
     git remote add origin https://github.com/SU_USUARIO/calculadora-metodos-numericos.git
     git push -u origin main
     ```
2. **Publicar en Render**
   - Entre a https://render.com e inicie sesión con su cuenta de GitHub.
   - **New → Blueprint**, elija el repositorio y pulse **Apply**. Render lee el archivo `render.yaml`
     (instala `requirements.txt` y arranca con `gunicorn app:app`).
   - En unos minutos queda un enlace del tipo `https://calculadora-metodos-numericos.onrender.com`.

> En el plan gratuito la página "se duerme" si nadie la usa por un rato; la primera visita después de eso
> puede tardar alrededor de un minuto en cargar. Ábrala unos minutos antes de la exposición.
