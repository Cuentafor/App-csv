import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Descargar Históricos - Yahoo Finance", layout="centered")
st.title("📈 Descargar Datos Históricos de Acciones e Índices")
st.markdown("Usa **yfinance** para obtener precios históricos y descargarlos en CSV.")

# --- Sidebar para configuración ---
st.sidebar.header("⚙️ Parámetros de descarga")

# Entrada de tickers
ticker_input = st.sidebar.text_input(
    "Símbolo (Ticker)",
    value="AAPL",
    help="Ejemplos: AAPL, MSFT, ^GSPC, SAN.MC, BBVA.MC"
)

# Selección de fechas
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input(
        "Fecha inicio",
        value=datetime.now() - timedelta(days=365),
        max_value=datetime.now()
    )
with col2:
    end_date = st.date_input(
        "Fecha fin",
        value=datetime.now(),
        max_value=datetime.now()
    )

# Intervalo
interval = st.sidebar.selectbox(
    "Intervalo",
    options=["1d", "1wk", "1mo"],
    index=0,
    format_func=lambda x: {"1d": "Diario", "1wk": "Semanal", "1mo": "Mensual"}[x]
)

# Botón de descarga
if st.sidebar.button("🔍 Obtener y mostrar datos", type="primary"):
    if start_date >= end_date:
        st.error("La fecha de inicio debe ser anterior a la fecha de fin.")
    else:
        with st.spinner(f"Descargando datos para {ticker_input}..."):
            try:
                df = yf.download(ticker_input, start=start_date, end=end_date, interval=interval)
                if df.empty:
                    st.warning("No se encontraron datos para el ticker especificado.")
                else:
                    st.success(f"✅ Datos obtenidos: {len(df)} registros")
                    
                    # Mostrar tabla
                    st.subheader("📋 Vista previa de los datos")
                    st.dataframe(df.tail(10), use_container_width=True)
                    
                    # Preparar CSV para descarga
                    csv = df.to_csv()
                    st.download_button(
                        label="⬇️ Descargar CSV completo",
                        data=csv,
                        file_name=f"{ticker_input.replace('^', '')}_{start_date}_{end_date}.csv",
                        mime="text/csv"
                    )
                    
                    # Gráfico de cierre ajustado
                    st.subheader("📊 Precio de cierre ajustado")
                    st.line_chart(df['Adj Close'] if 'Adj Close' in df.columns else df['Close'])
                    
            except Exception as e:
                st.error(f"Error al obtener datos: {str(e)}")

# --- Información adicional ---
st.sidebar.markdown("---")
st.sidebar.markdown("""
**📌 Ejemplos de tickers válidos**  
- Acciones: `AAPL`, `MSFT`, `GOOGL`, `SAN.MC`, `BBVA.MC`  
- Índices: `^GSPC` (S&P 500), `^IXIC` (Nasdaq), `^IBEX` (IBEX 35)
""")
