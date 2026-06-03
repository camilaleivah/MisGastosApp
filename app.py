import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Mi Seguimiento Mensual", layout="wide")

# 2. SISTEMA DE AUTENTICACIÓN
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Restringido")
        st.text_input("Usuario", key="username")
        st.text_input("Contraseña", type="password", key="password")
        if st.button("Entrar"):
            if (st.session_state["username"] in st.secrets["passwords"] and 
                st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]):
                st.session_state["password_correct"] = True
                del st.session_state["password"]
                del st.session_state["username"]
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
        return False
    return st.session_state["password_correct"]

if check_password():

    # Límites configurados
    LIMITES = {
        "Alimentación": 260320,
        "Farmacia": 255345,
        "Transporte": 273740,
        "Otros": 145000
    }

    MEDIODEPAGO = {
        "Tarjeta de Crédito",
        "Tarjeta de Débito",
        "Cami",
        "Efectivo"
        
    }   

    def format_clp(valor):
        return f"${valor:,.0f}".replace(",", ".")

    conn = st.connection("gsheets", type=GSheetsConnection)

    def leer_datos():
        return conn.read(ttl="0s")

    # Header
    col_t, col_b = st.columns([0.8, 0.2])
    with col_t:
        st.title("📊 Seguimiento de Gastos")
    with col_b:
        if st.button("Cerrar Sesión"):
            st.session_state["password_correct"] = False
            st.rerun()

    tab_ingreso, tab_status = st.tabs(["➕ Ingresar Compra", "📈 Status"])

    # --- PANTALLA: INGRESAR COMPRA ---
    with tab_ingreso:
        st.header("Nueva Compra")
        with st.form("form_compra", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            
            monto = st.number_input("Monto de la compra ($)", min_value=0, step=1000)
            with col1:
                compra = st.text_input("Compra (Regalo,Hogar,Est,Varios", placeholder="Ej: Supermercado...")
            

            with col2:
                categoria = st.selectbox("Categoría", list(LIMITES.keys()))
            with col3:
                mediodepago = st.selectbox("Medio de Pago", MEDIODEPAGO)
            fecha_dt = st.date_input("Fecha", value=datetime.now())
            
            btn_guardar = st.form_submit_button("Guardar Compra")

            if btn_guardar:
                if compra:
                    df_actual = leer_datos()
                    nueva_fila = pd.DataFrame([{
                        "Fecha": fecha_dt.strftime('%d/%m/%Y'),
                        "Compra": compra,
                        "Categoria": categoria,
                        "Monto": monto,
                        "Medio de Pago": mediodepago
                    }])
                    df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
                    conn.update(data=df_final)
                    st.success(f"✅ Registrado: {compra}")
                    st.rerun()

    with tab_status:
        df = leer_datos()
        if df is not None and not df.empty:
            df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
            
            # --- CÁLCULOS GLOBALES ---
            total_presupuesto_global = sum(LIMITES.values())
            total_gastado_global = df['Monto'].sum()
            total_disponible_global = max(0, total_presupuesto_global - total_gastado_global)
            porcentaje_total = int((total_gastado_global / total_presupuesto_global) * 100) if total_presupuesto_global > 0 else 0

            # --- SECCIÓN: BALANCE TOTAL ---
            st.subheader("💰 Balance Total del Mes")
            col_chart, col_metrics = st.columns([1, 1])

            with col_chart:
                # Gráfico Global: Rojo (Gastado), Verde (Disponible)
                fig_global = go.Figure(data=[go.Pie(
                    labels=['Gastado', 'Disponible'],
                    values=[total_gastado_global, total_disponible_global],
                    hole=.7,
                    marker_colors=['#FF4B4B', '#28A745'],
                    textinfo='percent'
                )])
                fig_global.update_layout(showlegend=True, height=300, margin=dict(l=0,r=0,t=0,b=0),
                                        annotations=[dict(text=f"{porcentaje_total}%", x=0.5, y=0.5, font_size=30, showarrow=False)])
                st.plotly_chart(fig_global, use_container_width=True)

            with col_metrics:
                st.write("### Resumen General")
                st.metric("Presupuesto Total", format_clp(total_presupuesto_global))
                st.metric("Total Gastado", format_clp(total_gastado_global), delta=format_clp(total_gastado_global), delta_color="inverse")
                st.metric("Total Disponible", format_clp(total_disponible_global))

            st.divider()

            # --- SECCIÓN: DESGLOSE POR CATEGORÍA ---
            st.subheader("📂 Desglose por Categoría")
            cols = st.columns(4)
            for i, (cat, limite) in enumerate(LIMITES.items()):
                gastado = df[df['Categoria'] == cat]['Monto'].sum()
                disponible = max(0, limite - gastado)
                with cols[i]:
                    st.markdown(f"**{cat}**")
                    fig = go.Figure(data=[go.Pie(labels=['Gastado', 'Disponible'], values=[gastado, disponible], 
                                               hole=.6, marker_colors=['#FF4B4B', '#28A745'], textinfo='none')])
                    fig.update_layout(showlegend=False, height=150, margin=dict(l=0,r=0,t=0,b=0),
                                     annotations=[dict(text=f"{int((gastado/limite)*100)}%", x=0.5, y=0.5, font_size=16, showarrow=False)])
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(f"Quedan: {format_clp(disponible)}")

            st.divider()
            st.subheader("📝 Historial")
            st.dataframe(df, use_container_width=True)
