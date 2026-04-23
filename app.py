import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import io
import zipfile
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Descargar Históricos - Yahoo Finance", layout="centered")
st.title("📈 Descargar Datos Históricos de Acciones e Índices")
st.markdown("Usa **yfinance** para obtener precios históricos. **Cada ticker se descarga en su propio archivo CSV/Excel**.")

# --- Sidebar ---
st.sidebar.header("⚙️ Parámetros")

ticker_input = st.sidebar.text_input(
    "Símbolo(s) (ticker)",
    value="AAPL, MSFT, ^GSPC",
    help="Separa por comas o espacios. Ejemplos: AAPL, MSFT, ^GSPC, SAN.MC"
)

def parse_tickers(ticker_str):
    parts = re.split(r'[ ,]+', ticker_str.strip())
    return [p for p in parts if p]

col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("Fecha inicio", value=datetime.now() - timedelta(days=365), max_value=datetime.now())
with col2:
    end_date = st.date_input("Fecha fin", value=datetime.now(), max_value=datetime.now())

interval = st.sidebar.selectbox("Intervalo", ["1d", "1wk", "1mo"], format_func=lambda x: {"1d": "Diario", "1wk": "Semanal", "1mo": "Mensual"}[x])

available_columns = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
selected_columns = st.sidebar.multiselect("Columnas a exportar", options=available_columns, default=available_columns)

output_format = st.sidebar.radio("Formato de descarga", ["CSV", "Excel"], index=0, horizontal=True)

# --- Validaciones ---
if start_date >= end_date:
    st.sidebar.error("❌ La fecha de inicio debe ser anterior a la fecha de fin.")
    st.stop()

tickers = parse_tickers(ticker_input)
if not tickers:
    st.sidebar.error("❌ Introduce al menos un ticker válido.")
    st.stop()

# --- Función de descarga robusta ---
@st.cache_data(ttl=3600, show_spinner=False)
def descargar_ticker(ticker, start, end, interval):
    try:
        data = yf.download(ticker, start=start, end=end, interval=interval, progress=False, auto_adjust=False, threads=True)
        if data.empty:
            return None
        data = data.reset_index()
        if 'Date' not in data.columns:
            data.rename(columns={data.columns[0]: 'Date'}, inplace=True)
        return data
    except Exception as e:
        st.error(f"Error con {ticker}: {str(e)}")
        return None

# --- Botón principal ---
if st.sidebar.button("🔍 Obtener y mostrar datos", type="primary"):
    if not selected_columns:
        st.error("❌ Selecciona al menos una columna.")
        st.stop()

    resultados = {}
    with st.spinner(f"Descargando {len(tickers)} ticker(s)..."):
        with ThreadPoolExecutor(max_workers=min(5, len(tickers))) as executor:
            futures = {executor.submit(descargar_ticker, t, start_date, end_date, interval): t for t in tickers}
            for future in as_completed(futures):
                ticker = futures[future]
                df = future.result()
                if df is not None:
                    resultados[ticker] = df
                else:
                    st.warning(f"⚠️ No se obtuvieron datos para {ticker}.")

    if not resultados:
        st.error("❌ No se pudo descargar ningún ticker.")
        st.stop()

    st.success(f"✅ Descargados {len(resultados)} tickers correctamente.")

    # --- Vista previa del primer ticker ---
    primer_ticker = list(resultados.keys())[0]
    st.subheader(f"📋 Vista previa - {primer_ticker} (últimos 5 registros)")
    df_preview = resultados[primer_ticker][['Date'] + selected_columns]
    st.dataframe(df_preview.tail(5), use_container_width=True)

    # --- Función para generar el contenido de un ticker (bytes) ---
    def generar_archivo_bytes(df, ticker, formato):
        cols = ['Date'] + [col for col in selected_columns if col in df.columns]
        df_export = df[cols].copy()
        df_export = df_export.fillna('')
        if formato == "CSV":
            return df_export.to_csv(index=False).encode('utf-8')
        else:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name=ticker[:31])
            return output.getvalue()

    # --- Botones de descarga individual ---
    st.subheader("⬇️ Descarga individual por ticker")
    for ticker, df in resultados.items():
        archivo_bytes = generar_archivo_bytes(df, ticker, output_format)
        ext = "csv" if output_format == "CSV" else "xlsx"
        st.download_button(
            label=f"📥 {ticker} - {output_format}",
            data=archivo_bytes,
            file_name=f"{ticker.replace('^', '')}_{start_date}_{end_date}.{ext}",
            mime="text/csv" if output_format == "CSV" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_{ticker}"
        )

    # --- Botón de descarga de todos en ZIP ---
    if len(resultados) > 1:
        st.subheader("📦 Descarga masiva")
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for ticker, df in resultados.items():
                archivo_bytes = generar_archivo_bytes(df, ticker, output_format)
                ext = "csv" if output_format == "CSV" else "xlsx"
                nombre_archivo = f"{ticker.replace('^', '')}_{start_date}_{end_date}.{ext}"
                zip_file.writestr(nombre_archivo, archivo_bytes)
        zip_buffer.seek(0)
        st.download_button(
            label="📦 Descargar TODOS en ZIP",
            data=zip_buffer,
            file_name=f"tickers_{start_date}_{end_date}.zip",
            mime="application/zip"
        )

    # --- Gráfico del primer ticker ---
    st.subheader(f"📊 Precio de cierre - {primer_ticker}")
    if 'Adj Close' in resultados[primer_ticker].columns:
        close_col = 'Adj Close'
    elif 'Close' in resultados[primer_ticker].columns:
        close_col = 'Close'
    else:
        close_col = None
    if close_col:
        df_plot = resultados[primer_ticker].set_index('Date')[close_col]
        st.line_chart(df_plot)
    else:
        st.info("No hay columna de cierre para graficar.")
