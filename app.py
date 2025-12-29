import streamlit as st
from st_gsheets_connection import GSheetsConnection
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="Ops Stats EZE", layout="wide")

st.title("✈️ United EZE - Ops Stats Automator")

# Conexión con manejo de error suave
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.warning("Configurando conexión... Si este mensaje persiste, revisa los Secrets.")

# Función de extracción
def procesar_archivos(pdf, log):
    # Extraer de PDF
    with pdfplumber.open(pdf) as p:
        texto = "\n".join([page.extract_text() for page in p.pages if page.extract_text()])
    
    # Buscar Pasajeros (F, J, O, Y)
    pax = {}
    for c in ["F", "J", "O", "Y"]:
        m = re.search(fr"{c} Class\s+(\d+)", texto)
        pax[c] = int(m.group(1)) if m else 0
    
    # Buscar Tiempos
    out_t = re.search(r"OUT\s+(\d{2}:\d{2})", texto)
    in_t = re.search(r"IN\s+(\d{2}:\d{2})", texto)
    
    # Extraer de Log (CSV)
    df_log = pd.read_csv(log)
    whcr = 0
    for row in df_log.iloc[:, 3].astype(str): # Columna 'Transaction Description'
        if "whcr" in row.lower():
            match = re.search(r'(\d+)\s*whcr', row.lower())
            if match: whcr = int(match.group(1))
            
    return {
        "Vuelo": "UA818",
        "OUT": out_t.group(1) if out_t else "",
        "IN": in_t.group(1) if in_t else "",
        "F": pax["F"], "J": pax["J"], "O": pax["O"], "Y": pax["Y"],
        "Total": sum(pax.values()),
        "WHLCHR": whcr
    }

# Interfaz
up_pdf = st.file_uploader("1. Subir PDF Flight Info", type="pdf")
up_log = st.file_uploader("2. Subir CSV Event Log", type="csv")

if up_pdf and up_log:
    res = procesar_archivos(up_pdf, up_log)
    df_new = pd.DataFrame([res])
    st.table(df_new)
    
    if st.button("🚀 Enviar a Google Sheets"):
        try:
            # Leer lo que hay en el Sheet
            df_actual = conn.read()
            # Unir con lo nuevo
            df_final = pd.concat([df_actual, df_new], ignore_index=True)
            # Guardar
            conn.update(data=df_final)
            st.success("¡Datos guardados!")
        except Exception as e:
            st.error(f"Error al guardar: {e}")
