import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="United EZE Ops Stats", layout="wide")

# Conexión a Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error de conexión a Google Sheets. Revisa los Secrets.")

def extract_data(pdf_file, log_file, cargo_file):
    # --- Extracción de PDF ---
    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    
    # Búsqueda de Tiempos y Nose
    out_time = re.search(r"OUT\s+(\d{2}:\d{2})", text)
    in_time = re.search(r"IN\s+(\d{2}:\d{2})", text)
    nose = re.search(r"Nose\s+(\d+)", text)
    
    # Búsqueda de Pasajeros (F, J, O, Y)
    pax_dict = {}
    for c in ["F", "J", "O", "Y"]:
        m = re.search(fr"{c}\s+Class\s+(\d+)", text)
        pax_dict[c] = int(m.group(1)) if m else 0

    # --- Extracción de CSV (WHLCHR) ---
    df_log = pd.read_csv(log_file)
    whcr = 0
    for desc in df_log.iloc[:, 3].astype(str): # Columna 'Transaction Description'
        if "whcr" in desc.lower():
            m_whcr = re.search(r'(\d+)\s*whcr', desc.lower())
            if m_whcr: whcr = int(m_whcr.group(1))

    # --- Extracción de Cargo ---
    # Sumamos la columna de peso (ajustar según tu archivo de cargo)
    df_cargo = pd.read_csv(cargo_file)
    peso_total = df_cargo.iloc[:, 1].sum() if not df_cargo.empty else 0

    return {
        "Fecha": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "Nose": nose.group(1) if nose else "N/A",
        "OUT": out_time.group(1) if out_time else "",
        "IN": in_time.group(1) if in_time else "",
        "Pax_F": pax_dict["F"], "Pax_J": pax_dict["J"], 
        "Pax_O": pax_dict["O"], "Pax_Y": pax_dict["Y"],
        "WHLCHR": whcr,
        "Cargo_LBS": peso_total
    }

# --- INTERFAZ ---
st.title("✈️ Ops Stats EZE Automator")

up_pdf = st.file_uploader("Subir PDF Flight Info", type="pdf")
up_log = st.file_uploader("Subir CSV Event Log", type="csv")
up_cargo = st.file_uploader("Subir CSV Cargo", type="csv")

if up_pdf and up_log and up_cargo:
    try:
        res = extract_data(up_pdf, up_log, up_cargo)
        df_row = pd.DataFrame([res])
        st.write("### Vista previa de los datos extraídos:")
        st.table(df_row)
        
        if st.button("🚀 Enviar a Google Sheets"):
            existing = conn.read()
            updated = pd.concat([existing, df_row], ignore_index=True)
            conn.update(data=updated)
            st.success("✅ ¡Guardado en Google Sheets!")
    except Exception as e:
        st.error(f"Hubo un problema procesando los archivos: {e}")
