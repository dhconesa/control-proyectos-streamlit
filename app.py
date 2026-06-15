import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
from datetime import datetime
import json

# 1. Configuración de la página
st.set_page_config(page_title="Gestión de Proyectos v2.0", layout="wide", page_icon="📈")

# --- LISTA DE DEPARTAMENTOS ---
DEPARTAMENTOS = ["Marketing", "IT / Proyectos", "Supply Chain", "Operaciones", "Ventas", "Finanzas", "RRHH"]

# 2. Conexión segura a Google Sheets
@st.cache_resource
def conectar_gsheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_credentials" in st.secrets:
            creds_dict = json.loads(st.secrets["gcp_credentials"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        else:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Control_Proyectos_DB") 
        return sheet
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

db = conectar_gsheet()

def get_dataframe(sheet_name):
    if db:
        try:
            worksheet = db.worksheet(sheet_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data), worksheet
        except: return pd.DataFrame(), None
    return pd.DataFrame(), None

# --- LÓGICA DE CÁLCULO DE ESTADO ---
# --- LÓGICA DE CÁLCULO DE ESTADO ---
def calcular_estado_proyecto(id_proy, df_t):
    # 1. Validación de seguridad: Si la tabla de tareas está vacía o no tiene la columna, no calculamos nada.
    if df_t.empty or 'id_proyecto' not in df_t.columns:
        return "⏳ En proceso (Sin tareas)"
    
    # 2. Filtrar las tareas correspondientes a este proyecto específico
    tareas_p = df_t[df_t['id_proyecto'] == id_proy]
    
    # 3. Si el proyecto existe pero aún no se le han asignado tareas
    if tareas_p.empty:
        return "⏳ En proceso (Sin tareas)"
        
    # 4. Si TODAS las tareas asociadas tienen el estado 'Completado'
    if all(tareas_p['estado'] == 'Completado'):
        return "✅ Completado"
        
    return "⏳ En proceso"

# --- LOGIN (Simplificado para el ejemplo, mantener el anterior en producción) ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔑 Acceso al Sistema")
    u = st.text_input("Usuario")
    p = st.text_input("Password", type="password")
    if st.button("Entrar"):
        if u == "admin" and p == "admin123": # Usar lógica de DB del código anterior
            st.session_state.logged_in = True
            st.rerun()
else:
    # Carga de datos
    df_proyectos, ws_proyectos = get_dataframe("proyectos")
    df_tareas, ws_tareas = get_dataframe("tareas")

    menu = st.sidebar.radio("Menú", ["📊 Dashboard", "📁 Proyectos", "📝 Tareas"])

    if menu == "📁 Proyectos":
        st.title("📁 Gestión de Proyectos")
        t1, t2 = st.tabs(["✨ Nuevo Proyecto", "👀 Ver y Editar"])

        with t1:
            with st.form("nuevo_p"):
                nombre = st.text_input("Nombre")
                desc = st.text_area("Descripción")
                depto = st.selectbox("Departamento", DEPARTAMENTOS)
                if st.form_submit_button("Guardar"):
                    id_p = int(df_proyectos['id_proyecto'].max() + 1) if not df_proyectos.empty else 1
                    ws_proyectos.append_row([id_p, nombre, desc, depto, str(datetime.today().date())])
                    st.success("Proyecto Guardado")
                    st.rerun()

        with t2:
            if not df_proyectos.empty:
                # Calculamos el estado dinámico para cada proyecto antes de mostrar
                df_proyectos['Estado Proyecto'] = df_proyectos['id_proyecto'].apply(lambda x: calcular_estado_proyecto(x, df_tareas))
                
                # Reordenamos columnas para que sea legible
                cols = ['id_proyecto', 'nombre_proyecto', 'departamento', 'Estado Proyecto', 'descripcion', 'fecha_creacion']
                st.dataframe(df_proyectos[cols], use_container_width=True)

    elif menu == "📊 Dashboard":
        st.title("📊 Dashboard por Departamento")
        if not df_proyectos.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig = px.pie(df_proyectos, names='departamento', title="Proyectos por Departamento", hole=0.4)
                st.plotly_chart(fig)
            with c2:
                if not df_tareas.empty:
                    # Unimos tareas y proyectos para ver tareas por departamento
                    df_m = pd.merge(df_tareas, df_proyectos, on='id_proyecto')
                    fig2 = px.bar(df_m, x='departamento', color='estado', title="Estado de Tareas por Departamento")
                    st.plotly_chart(fig2)
