# 📈 CEDEAR Dashboard

Dashboard personal para el seguimiento de CEDEARs y ADRs argentinos. Construido con Python y Streamlit — corre localmente.

---

## ¿Qué es un CEDEAR?

Un CEDEAR (Certificado de Depósito Argentino) es un instrumento que cotiza en la Bolsa de Buenos Aires y replica el precio de una acción extranjera (como Apple, Google o Caterpillar). Cada CEDEAR tiene un **ratio de conversión** que indica cuántos CEDEARs equivalen a una acción subyacente.

Este dashboard permite seguir una lista selecta de CEDEARs en tiempo real, calcular precios en pesos, analizar RSI y evaluar la calidad de los fundamentos de cada empresa.

---

## ¿Qué hace el dashboard?

### 📊 RSI Monitor
Muestra una grilla con todos los tickers monitoreados. Para cada uno calcula el **RSI 14 períodos** (método Wilder) usando velas de 1 hora de los últimos 3 meses. El precio se muestra en pesos argentinos usando la cotización del dólar blue en tiempo real.

- 🟢 RSI ≤ 30 → sobrevendido (posible oportunidad de compra)
- 🔴 RSI ≥ 70 → sobrecomprado (posible señal de cautela)

### 🔍 Búsqueda
Consultá cualquier ticker del mercado americano, no solo los del grid. Muestra precio USD, precio ARS (si cotiza en BYMA como `.BA`) y RSI.

### 💼 Calculadora de portfolio
Ingresás cuántos nominales tenés de un ticker de referencia y el dashboard calcula automáticamente cuántos nominales necesitás de cada ticker para mantener los pesos objetivo del portfolio. También muestra el error de aproximación y sugiere la cantidad óptima de referencia.
Disclaimer: esto no es recomendación de inversión.

### 📅 Vencimientos de opciones
Consulta los próximos vencimientos de opciones (calls y puts) para todos los tickers monitoreados en los próximos 90 días. Muestra open interest, volumen y un indicador de urgencia por proximidad del vencimiento.

### 📐 Valuación por quarters
Herramienta de análisis fundamental. Ingresás datos de hasta 5 quarters (OCF, shares, stock price, buyback) y el dashboard:
- Grafica la evolución de OCF/Share, precio y buyback
- Calcula métricas como drift precio vs OCF, dilución/recompra, múltiplo P/OCF
- Genera un **informe automático con veredicto** (score 0-100) e identifica escenarios como oportunidad potencial, expansión de múltiplo o dilución perjudicial
- Permite exportar e importar los datos en CSV

---

## Instalación

### Requisitos
- Python 3.9+
- Las dependencias listadas en `requirements.txt`

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/reddjedet/Cedear-dashboard.git
cd cedear-dashboard

# 2. Crear y activar un entorno virtual (opcional pero recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Correr la app
streamlit run app.py
```

La app queda disponible en `http://localhost:8501`.

---

## Dependencias principales

| Librería | Uso |
|---|---|
| `streamlit` | Framework de la interfaz |
| `yfinance` | Datos de mercado (Yahoo Finance) |
| `plotly` | Gráficos interactivos |
| `pandas` / `numpy` | Procesamiento de datos |
| `requests` | Cotización del dólar blue (bluelytics.com.ar) |

---

## Estructura

```
cedear-dashboard/
├── app.py          ← toda la aplicación en un solo archivo
├── requirements.txt
└── README.md
```

---

## Notas

- Los datos de mercado se cachean durante 5 minutos para no saturar la API de Yahoo Finance.
- El dólar blue se obtiene de [bluelytics.com.ar](https://bluelytics.com.ar). Si no está disponible, los precios en ARS no se muestran.
- La sección de opciones puede tardar ~30 segundos en cargar porque consulta todos los tickers en paralelo.
- Este proyecto es para uso personal. No constituye asesoramiento financiero.
