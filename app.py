import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

st.set_page_config(page_title="Descargar Históricos - Yahoo Finance (Mejorado)", layout="centered")
st.title("📈 Descargar Datos Históricos de Acciones e Índices (Mejorado)")
st.markdown("Usa **yfinance** para obtener precios históricos y descargarlos en CSV/Excel. Soporta múltiples tickers y selección de columnas.")

# --- Sidebar ---
st.sidebar.header("⚙️ Parámetros de descarga")

# Entrada de tickers (múltiples)
ticker_input = st.sidebar.text_input(
    "Símbolo(s) (ticker)",
    value="AAPL, MSFT, ^GSPC",
    help="Separa por comas o espacios. Ejemplos: AAPL, MSFT, ^GSPC, SAN.MC, BBVA.MC"
)

# Limpieza y lista de tickers
def parse_tickers(ticker_str):
    # Separa por comas o espacios, elimina espacios en blanco, ignora vacíos
    parts = re.split(r'[ ,]+', ticker_str.strip())
    return [p for p in parts if p]

# Fechas
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

# --- Nuevas funcionalidades ---
# Selección de columnas a exportar
available_columns = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
selected_columns = st.sidebar.multiselect(
    "Columnas a exportar",
    options=available_columns,
    default=available_columns,
    help="Elige qué campos quieres incluir en el archivo descargado."
)

# Formato de salida
output_format = st.sidebar.radio(
    "Formato de descarga",
    options=["CSV", "Excel"],
    index=0,
    horizontal=True
)

# Opción de descarga separada por ticker o combinada
multi_mode = st.sidebar.radio(
    "Múltiples tickers",
    options=["Archivo combinado (columnas multi-nivel)", "Archivos separados (por ticker)"],
    index=0,
    help="Si hay varios tickers, ¿los quieres en un solo DataFrame o en archivos independientes?"
)

# --- Validaciones robustas ---
if start_date >= end_date:
    st.sidebar.error("❌ La fecha de inicio debe ser anterior a la fecha de fin.")
    st.stop()

tickers = parse_tickers(ticker_input)
if not tickers:
    st.sidebar.error("❌ Introduce al menos un ticker válido.")
    st.stop()

# Validación extra: comprobar que el intervalo es compatible con el rango de fechas
days_diff = (end_date - start_date).days
if interval == "1mo" and days_diff < 30:
    st.warning("⚠️ El intervalo mensual ('1mo') con menos de 30 días puede devolver pocos datos. Considera usar '1d' o '1wk'.")
if interval == "1wk" and days_diff < 7:
    st.warning("⚠️ El intervalo semanal con menos de 7 días puede devolver solo una fila.")

# --- Función para descargar un ticker de forma robusta ---
@st.cache_data(ttl=3600, show_spinner=False)
def descargar_ticker(ticker, start, end, interval):
    """Devuelve DataFrame con datos o None si falla."""
    try:
        # Ajuste de zona horaria: usamos tz=None para evitar conflictos con fechas
        data = yf.download(
            ticker,
            start=start,
            end=end,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=True
        )
        if data.empty:
            return None
        # Reset index para que la fecha sea columna (más fácil exportar)
        data = data.reset_index()
        # Renombrar columna de fecha a 'Date' (por si acaso)
        if 'Date' not in data.columns and data.columns[0] == 'Date':
            pass
        elif 'Datetime' in data.columns:
            data.rename(columns={'Datetime': 'Date'}, inplace=True)
        else:
            # En algunos casos la primera columna es la fecha sin nombre
            data.rename(columns={data.columns[0]: 'Date'}, inplace=True)
        return data
    except Exception as e:
        st.error(f"Error descargando {ticker}: {str(e)}")
        return None

# --- Botón principal ---
if st.sidebar.button("🔍 Obtener y mostrar datos", type="primary"):
    if not selected_columns:
        st.error("❌ Debes seleccionar al menos una columna para exportar.")
        st.stop()

    # Descarga en paralelo si hay varios tickers
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
                    st.warning(f"⚠️ No se obtuvieron datos para {ticker}. Puede ser inválido o sin datos en el rango.")

    if not resultados:
        st.error("❌ No se pudo descargar ningún ticker. Revisa los símbolos y tu conexión.")
        st.stop()

    st.success(f"✅ Descargados {len(resultados)} tickers con éxito.")

    # --- Mostrar vista previa ---
    st.subheader("📋 Vista previa de los datos (últimos 5 registros del primer ticker)")
    primer_ticker = list(resultados.keys())[0]
    df_preview = resultados[primer_ticker][['Date'] + selected_columns] if 'Date' in resultados[primer_ticker].columns else resultados[primer_ticker]
    st.dataframe(df_preview.tail(5), use_container_width=True)

    # --- Preparar descarga según modo ---
    if len(tickers) == 1:
        multi_mode = "Archivo combinado (columnas multi-nivel)"  # forzamos combinado si solo uno

    if multi_mode == "Archivo combinado (columnas multi-nivel)":
        # Crear un DataFrame combinado con columnas multi-nivel (ticker, columna)
        combined = None
        for ticker, df in resultados.items():
            if 'Date' not in df.columns:
                st.warning(f"El DataFrame de {ticker} no tiene columna Date. Se usará el índice.")
                df = df.reset_index()
            # Asegurar que Date sea datetime para merge
            df['Date'] = pd.to_datetime(df['Date'])
            df = df[['Date'] + [col for col in selected_columns if col in df.columns]]
            df = df.set_index('Date')
            # Añadir nivel de columnas
            df.columns = pd.MultiIndex.from_product([[ticker], df.columns])
            if combined is None:
                combined = df
            else:
                combined = combined.join(df, how='outer')
        combined = combined.reset_index()
        # Reemplazar NaN por vacío para CSV/Excel
        combined = combined.fillna('')
        df_to_export = combined
        file_prefix = "multi_ticker"
    else:
        # Archivos separados: se mostrarán múltiples botones o un zip? Streamlit no tiene zip nativo fácil, pero podemos ofrecer descarga individual.
        # Para simplificar, mostraremos un botón por cada ticker.
        st.subheader("📁 Descarga individual por ticker")
        for ticker, df in resultados.items():
            # Filtrar columnas seleccionadas y mantener Date
            cols_to_keep = ['Date'] + [col for col in selected_columns if col in df.columns]
            df_export = df[cols_to_keep].copy()
            df_export = df_export.fillna('')
            # Convertir a bytes según formato
            if output_format == "CSV":
                data_bytes = df_export.to_csv(index=False).encode('utf-8')
                mime = "text/csv"
                ext = "csv"
            else:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_export.to_excel(writer, index=False, sheet_name=ticker[:31])
                data_bytes = output.getvalue()
                mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ext = "xlsx"
            st.download_button(
                label=f"⬇️ Descargar {ticker} en {output_format}",
                data=data_bytes,
                file_name=f"{ticker.replace('^', '')}_{start_date}_{end_date}.{ext}",
                mime=mime,
                key=f"download_{ticker}"
            )
        st.stop()  # No mostrar el bloque combinado

    # --- Descarga del archivo combinado ---
    if output_format == "CSV":
        csv_data = df_to_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Descargar CSV combinado",
            data=csv_data,
            file_name=f"datos_{start_date}_{end_date}.csv",
            mime="text/csv"
        )
    else:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_to_export.to_excel(writer, index=False, sheet_name='Datos')
        st.download_button(
            label="⬇️ Descargar Excel combinado",
            data=output.getvalue(),
            file_name=f"datos_{start_date}_{end_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # --- Gráfico de cierre ajustado (del primer ticker) ---
    st.subheader(f"📊 Precio de cierre ajustado - {primer_ticker}")
    if 'Adj Close' in resultados[primer_ticker].columns:
        close_col = 'Adj Close'
    elif 'Close' in resultados[primer_ticker].columns:
        close_col = 'Close'
    else:
        close_col = None
    if close_col:
        # Necesitamos serie con índice fecha para line_chart
        df_plot = resultados[primer_ticker].set_index('Date')[close_col]
        st.line_chart(df_plot)
    else:
        st.info("No hay columna de cierre para graficar.")

# --- Información en sidebar ---
st.sidebar.markdown("---")
st.sidebar.markdown("""
**📌 Mejoras incluidas**  
- ✅ Múltiples tickers simultáneos  
- ✅ Selección de columnas a exportar  
- ✅ Formatos CSV o Excel  
- ✅ Archivo combinado con columnas multi-nivel o archivos separados  
- ✅ Descarga en paralelo (más rápida)  
- ✅ Validación robusta de entradas y errores  
- ✅ Cache para evitar redescargas innecesarias  
""")
