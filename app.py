import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 1. CONFIGURACIÓN DE SEGURIDAD (Credenciales)
# Este es el usuario que podrá entrar
USUARIO_AUTORIZADO = st.secrets["passwords"]


def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.title("🔐 Acceso Restringido")
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        
        if st.button("Entrar"):
            if usuario in USUARIO_AUTORIZADO and USUARIO_AUTORIZADO[usuario] == clave:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
        return False
    return True

# SOLO SI ESTÁ AUTENTICADO SE MUESTRA EL RESTO
if login():
    # --- TODO TU CÓDIGO ANTERIOR AQUÍ ---
    st.set_page_config(page_title="Mi Seguimiento Mensual", layout="wide")

    LIMITES = {
        "Comida": 200000,
        "Regalos": 60000,
        "Ropa": 100000,
        "Hogar": 50000
    }

    MEDIODEPAGO = {
        "Tarjeta de Crédito",
        "Tarjeta de Débito",
        "Efectivo"
    }    

    def format_clp(valor):
        return f"${valor:,.0f}".replace(",", ".")

    conn = st.connection("gsheets", type=GSheetsConnection)

    def leer_datos():
        return conn.read(ttl="0s")

    st.title("📊 Seguimiento de Gastos")
    
    # Botón para cerrar sesión
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    tab_ingreso, tab_status = st.tabs(["➕ Ingresar Compra", "📈 Status"])

    # --- PANTALLA: INGRESAR COMPRA ---
    with tab_ingreso:
        st.header("Nueva Compra")
        with st.form("form_compra", clear_on_submit=True):
            compra = st.text_input("Compra", placeholder="Ej: Supermercado...")
            col1, col2, col3 = st.columns(3)
            with col1:
                valor = st.number_input("Valor de la compra ($)", min_value=0, step=1000)
            with col2:
                categoria = st.selectbox("Categoría", list(LIMITES.keys()))
            with col3:
                mediodepago = st.selectbox("Medio de Pago", list(MEDIODEPAGO.keys()))
            fecha_dt = st.date_input("Fecha", value=datetime.now())
            
            btn_guardar = st.form_submit_button("Guardar Compra")

            if btn_guardar:
                if compra:
                    df_actual = leer_datos()
                    nueva_fila = pd.DataFrame([{
                        "Fecha": fecha_dt.strftime('%d/%m/%Y'),
                        "Compra": compra,
                        "Categoria": categoria,
                        "Valor": valor
                    }])
                    df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
                    conn.update(data=df_final)
                    st.success(f"✅ Registrado: {compra}")
                    st.rerun()

    # --- PANTALLA: STATUS ---
    with tab_status:
        df = leer_datos()
        if df is not None and not df.empty:
            df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
            
            st.subheader("Resumen de Disponibilidad")
            cols = st.columns(4)
            
            for i, (cat, limite) in enumerate(LIMITES.items()):
                gastado = df[df['Categoria'] == cat]['Valor'].sum()
                disponible = max(0, limite - gastado)
                
                with cols[i]:
                    st.markdown(f"### {cat}")
                    
                    if gastado >= limite:
                        labels, values, colors = ['Gastado'], [gastado], ['#FF4B4B']
                    else:
                        labels, values, colors = ['Gastado', 'Disponible'], [gastado, disponible], ['#FF4B4B', '#28A745']
                    
                    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.6, 
                                               marker_colors=colors, textinfo='percent')])
                    fig.update_layout(showlegend=False, height=200, margin=dict(l=0,r=0,t=0,b=0),
                                     annotations=[dict(text=f"{int((gastado/limite)*100)}%", x=0.5, y=0.5, font_size=20, showarrow=False)])
                    
                    st.plotly_chart(fig, use_container_width=True)
                    st.write(f"Gastado: **{format_clp(gastado)}**")
                    st.write(f"Quedan: **{format_clp(disponible)}**")

            st.divider()
            st.subheader("Historial en la Nube")
            st.dataframe(df, use_container_width=True)
