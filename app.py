import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date

# Configuración de la página
st.set_page_config(page_title="Extractor de CSV Financiero", layout="wide")

st.title("📊 Extractor de Datos Históricos (Yahoo Finance)")
st.markdown("Introduce los tickers de las acciones separados por comas (ejemplo: `SAN.MC, TEF.MC, BBVA.MC, AAPL`)")

# --- BARRA LATERAL (Configuración) ---
st.sidebar.header("Configuración de la descarga")
start_date = st.sidebar.date_input("Fecha de inicio", value=pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("Fecha de fin", value=date.today())

# --- CUERPO PRINCIPAL ---
tickers_input = st.text_input("Lista de Tickers:", value="SAN.MC")

if tickers_input:
    # Limpiar la entrada de texto
    list_tickers = [t.strip().upper() for t in tickers_input.split(",")]
    
    try:
        # Descargar datos
        with st.spinner('Descargando datos...'):
            data = yf.download(list_tickers, start=start_date, end=end_date, group_by='ticker')

        if not data.empty:
            st.success(f"Datos cargados correctamente para: {', '.join(list_tickers)}")
            
            # Si es solo un ticker, mostramos la tabla directamente
            if len(list_tickers) == 1:
                df_display = data
                st.dataframe(df_display.tail(10), use_container_width=True)
                
                # Botón de descarga para un solo archivo
                csv = df_display.to_csv().encode('utf-8')
                st.download_button(
                    label="⬇️ Descargar CSV de " + list_tickers[0],
                    data=csv,
                    file_name=f"{list_tickers[0]}_historico.csv",
                    mime='text/csv',
                )
            else:
                # Si son varios, damos opciones para cada uno
                st.write("### Selecciona qué acción descargar:")
                cols = st.columns(len(list_tickers))
                for i, t in enumerate(list_tickers):
                    csv_multi = data[t].to_csv().encode('utf-8')
                    cols[i].download_button(
                        label=f"CSV {t}",
                        data=csv_multi,
                        file_name=f"{t}_historico.csv",
                        mime='text/csv',
                    )
                st.line_chart(data.xs('Close', level=1, axis=1))
        else:
            st.warning("No se encontraron datos. Revisa si los tickers son correctos.")

    except Exception as e:
        st.error(f"Ocurrió un error: {e}")

st.info("Nota: Para acciones de la bolsa española, recuerda añadir el sufijo .MC (ej: ITX.MC)")
