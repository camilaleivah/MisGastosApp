import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Mi Seguimiento Mensual", layout="wide")

LIMITES = {
    "Comida": 200000,
    "Regalos": 50000,
    "Ropa": 100000,
    "Hogar": 60000
}

def format_clp(valor):
    return f"${valor:,.0f}".replace(",", ".")

# 2. CONEXIÓN A GOOGLE SHEETS
# Streamlit leerá las credenciales de un archivo secreto
conn = st.connection("gsheets", type=GSheetsConnection)

def leer_datos():
    return conn.read(ttl="0s") # ttl=0 para que siempre lea datos frescos

# --- TÍTULO ---
st.title("📊 Seguimiento de Gastos")

tab_ingreso, tab_status = st.tabs(["➕ Ingresar Compra", "📈 Status"])

# --- PANTALLA: INGRESAR COMPRA ---
with tab_ingreso:
    st.header("Nueva Compra")
    with st.form("form_compra", clear_on_submit=True):
        compra = st.text_input("Compra", placeholder="Ej: Supermercado...")
        col1, col2 = st.columns(2)
        with col1:
            valor = st.number_input("Valor de la compra ($)", min_value=0, step=1000)
        with col2:
            categoria = st.selectbox("Categoría", list(LIMITES.keys()))
        fecha_dt = st.date_input("Fecha", value=datetime.now())
        
        btn_guardar = st.form_submit_button("Guardar Compra")

        if btn_guardar:
            if compra:
                # Leer datos actuales
                df_actual = leer_datos()
                
                # Crear nueva fila
                nueva_fila = pd.DataFrame([{
                    "Fecha": fecha_dt.strftime('%d/%m/%Y'),
                    "Compra": compra,
                    "Categoria": categoria,
                    "Valor": valor
                }])
                
                # Concatenar y subir
                df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
                conn.update(data=df_final)
                st.success(f"✅ Registrado en Google Sheets: {compra}")
                st.rerun()

# --- PANTALLA: STATUS ---
with tab_status:
    df = leer_datos()
    
    if df.empty:
        st.info("No hay registros en Google Sheets.")
    else:
        # Asegurar que Valor sea numérico (Google Sheets a veces lo trae como texto)
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
        
        st.subheader("Resumen de Disponibilidad")
        cols = st.columns(4)
        
        for i, (cat, limite) in enumerate(LIMITES.items()):
            gastado = df[df['Categoria'] == cat]['Valor'].sum()
            disponible = max(0, limite - gastado)
            
            with cols[i]:
                st.markdown(f"### {cat}")
                
                # Gráfico: Rojo (Gastado), Verde (Disponible)
                labels = ['Gastado', 'Disponible']
                values = [gastado, disponible]
                colors = ['#FF4B4B', '#28A745']
                
                fig = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=.6,
                    marker_colors=colors,
                    textinfo='percent'
                )])
                
                fig.update_layout(showlegend=False, height=200, margin=dict(l=0,r=0,t=0,b=0),
                                 annotations=[dict(text=f"{int((gastado/limite)*100)}%", x=0.5, y=0.5, font_size=20, showarrow=False)])
                
                st.plotly_chart(fig, use_container_width=True)
                st.write(f"Gastado: **{format_clp(gastado)}**")
                st.write(f"Quedan: **{format_clp(disponible)}**")

        st.divider()
        st.subheader("Historial en la Nube")
        st.dataframe(df, use_container_width=True)
