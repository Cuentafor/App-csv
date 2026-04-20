import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date, timedelta

# Configuración de la página para móvil y escritorio
st.set_page_config(
    page_title="Extractor Bolsa 10 Años", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Estilo personalizado para botones grandes en el móvil
st.markdown("""
    <style>
    .stDownloadButton button {
        width: 100%;
        height: 3em;
        background-color: #007bff;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Extractor Histórico Pro")
st.write("Configurado para obtener datos de los últimos 10 años.")

# --- BARRA LATERAL (Configuración) ---
st.sidebar.header("Rango de Fechas")
# Calculamos 10 años atrás (3650 días aprox)
default_start = date.today() - timedelta(days=3650)
start_date = st.sidebar.date_input("Desde:", value=default_start)
end_date = st.sidebar.date_input("Hasta:", value=date.today())

# --- ENTRADA DE TICKERS ---
tickers_input = st.text_input(
    "Introduce Tickers (separados por coma):", 
    value="SAN.MC, TEF.MC",
    help="Ejemplo: SAN.MC para Santander, ITX.MC para Inditex, AAPL para Apple"
)

if tickers_input:
    list_tickers = [t.strip().upper() for t in tickers_input.split(",")]
    
    try:
        with st.spinner('Accediendo a Yahoo Finance...'):
            # Descargamos los datos
            data = yf.download(list_tickers, start=start_date, end=end_date, group_by='ticker')

        if not data.empty:
            st.success(f"¡Éxito! Datos obtenidos.")
            
            # Gráfico interactivo para ver la tendencia de 10 años
            if len(list_tickers) > 1:
                st.subheader("Evolución Comparativa (Cierre)")
                # Extraemos solo la columna 'Close' para el gráfico
                closes = data.xs('Close', level=1, axis=1) if len(list_tickers) > 1 else data['Close']
                st.line_chart(closes)
            
            st.divider()
            st.subheader("📥 Descargar Archivos CSV")
            
            # Generar botones de descarga
            if len(list_tickers) == 1:
                ticker = list_tickers[0]
                csv = data.to_csv().encode('utf-8')
                st.download_button(
                    label=f"DESCARGAR CSV: {ticker}",
                    data=csv,
                    file_name=f"{ticker}_{start_date}_{end_date}.csv",
                    mime='text/csv',
                )
            else:
                # Crear columnas para los botones en el móvil
                for ticker in list_tickers:
                    if ticker in data.columns.levels[0]:
                        df_ticker = data[ticker].dropna()
                        csv_multi = df_ticker.to_csv().encode('utf-8')
                        st.download_button(
                            label=f"Descargar {ticker} ({len(df_ticker)} filas)",
                            data=csv_multi,
                            file_name=f"{ticker}_{start_date}_{end_date}.csv",
                            mime='text/csv',
                            key=ticker # Clave única para Streamlit
                        )

        else:
            st.error("No se encontraron datos. Verifica los tickers y el rango de fechas.")

    except Exception as e:
        st.error(f"Error técnico: {e}")

st.caption("Nota: Los tickers de la Bolsa de Madrid terminan en .MC")
