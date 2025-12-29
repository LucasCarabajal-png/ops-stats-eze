import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import pdfplumber
import re

# --- CONFIGURACIÓN Y TÍTULO ---
st.set_page_config(page_title="United EZE Ops Stats", layout="wide")
st.title("✈️ EZE Ops Stats - Automatización")

# Conexión a Google Sheets (usando el link de tu hoja)
# Nota: Deberás configurar el link en los "Secrets" de Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIONES DE EXTRACCIÓN ---
def procesar_todo(pdf_file, log_file, cargo_file):
    # 1. Procesar PDF
    with pdfplumber.open(pdf_file) as pdf:
        texto = "\n".join([page.extract_text() for page in pdf.pages])
    
    # Extraer Tiempos y Nose
    out_t = re.search(r"OUT\s+(\d{2}:\d{2})", texto)
    in_t = re.search(r"IN\s+(\d{2}:\d{2})", texto)
    nose = re.search(r"Nose\s+(\d+)", texto)
    
    # Extraer Pasajeros
    pax = {}
    for c in ["F", "J", "O", "Y"]:
        m = re.search(fr"{c} Class\s+(\d+)", texto)
        pax[c] = int(m.group(1)) if m else 0
    total_pax = sum(pax.values())

    # 2. Procesar Event Log (Sillas de ruedas)
    df_log = pd.read_csv(log_file)
    whcr = 0
    for desc in df_log['Transaction Description'].astype(str):
        if "whcr" in desc.lower():
            match = re.search(r'(\d+)\s*whcr', desc.lower())
            if match: whcr = int(match.group(1))

    # 3. Procesar Cargo (Asumiendo que es un CSV/Excel con una columna de peso)
    df_cargo = pd.read_csv(cargo_file) if cargo_file.name.endswith('.csv') else pd.read_excel(cargo_file)
    peso_cargo = df_cargo.iloc[:, 1].sum() # Ejemplo: suma la segunda columna

    return {
        "Vuelo": "UA818", # Se puede extraer dinámico
        "A/C Nose": nose.group(1) if nose else "N/A",
        "OUT": out_t.group(1) if out_t else "--:--",
        "IN": in_t.group(1) if in_t else "--:--",
        "Pax F": pax["F"], "Pax J": pax["J"], "Pax O": pax["O"], "Pax Y": pax["Y"],
        "Total Pax": total_pax,
        "WHLCHR": whcr,
        "Cargo": peso_cargo
    }

# --- INTERFAZ DE USUARIO ---
col1, col2, col3 = st.columns(3)
with col1: pdf = st.file_uploader("1. Flight Info (PDF)", type="pdf")
with col2: log = st.file_uploader("2. Event Log (CSV)", type="csv")
with col3: cargo = st.file_uploader("3. Cargo Data", type=["csv", "xlsx"])

if pdf and log and cargo:
    datos = procesar_todo(pdf, log, cargo)
    
    st.subheader("📊 Vista previa de los datos")
    df_preview = pd.DataFrame([datos])
    st.dataframe(df_preview)

    if st.button("🚀 Enviar a Google Sheets"):
        # Leer datos actuales
        existing_data = conn.read()
        # Agregar nueva fila
        updated_df = pd.concat([existing_data, df_preview], ignore_index=True)
        # Guardar de nuevo
        conn.update(data=updated_df)
        st.success("¡Datos guardados correctamente en Google Sheets!")
