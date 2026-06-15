import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
from datetime import datetime
import json

# 1. Configuración de la página
st.set_page_config(page_title="Jota Jota Foods - Proyectos", layout="wide", page_icon="🌍")

# --- TEMA CORPORATIVO JOTAJOTA ---
def aplicar_tema_corporativo():
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                background-color: #f4f6f9;
            }
            .stButton > button {
                background-color: #002387;
                color: white;
                border-radius: 5px;
                border: none;
                font-weight: bold;
            }
            .stButton > button:hover {
                background-color: #6eb43f;
                color: white;
                border-color: #6eb43f;
            }
            h1, h2, h3 {
                color: #002387 !important;
            }
            .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
                font-weight: 600;
            }
            .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
                border-bottom-color: #6eb43f !important;
            }
            .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] [data-testid="stMarkdownContainer"] p {
                color: #6eb43f !important;
            }
        </style>
    """, unsafe_allow_html=True)

aplicar_tema_corporativo()

# --- LISTA DE DEPARTAMENTOS ---
DEPARTAMENTOS = ["Marketing", "IT / Proyectos", "Supply Chain", "Operaciones", "Ventas", "Finanzas", "RRHH"]

# 2. Conexión segura a Google Sheets
@st.cache_resource
def conectar_gsheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
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
        st.error(f"❌ Error de conexión a la Base de Datos: {e}")
        return None

db = conectar_gsheet()

def get_dataframe(sheet_name):
    if db:
        try:
            worksheet = db.worksheet(sheet_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data), worksheet
        except Exception as e:
            return pd.DataFrame(), None
    return pd.DataFrame(), None

# --- LÓGICA DE CÁLCULO DE ESTADO ---
def calcular_estado_proyecto(id_proy, df_t):
    if df_t.empty or 'id_proyecto' not in df_t.columns:
        return "⏳ En proceso (Sin tareas)"
    
    tareas_p = df_t[df_t['id_proyecto'] == id_proy]
    
    if tareas_p.empty:
        return "⏳ En proceso (Sin tareas)"
        
    if all(tareas_p['estado'] == 'Completado'):
        return "✅ Completado"
        
    return "⏳ En proceso"

# 3. Estado de la Sesión (Login)
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "login_user" not in st.session_state: st.session_state.login_user = ""
if "nombre_completo" not in st.session_state: st.session_state.nombre_completo = ""
if "user_role" not in st.session_state: st.session_state.user_role = ""

# --- PANTALLA DE LOGIN Y REGISTRO ---
if not st.session_state.logged_in:
    st.title("🌍 Jota Jota Foods - Portal de Proyectos")
    tab_login, tab_reg = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse"])
    
    df_users, ws_users = get_dataframe("usuarios")
    
    with tab_login:
        login_user = st.text_input("Usuario", key="login_u")
        login_pass = st.text_input("Contraseña", type="password", key="login_p")
        
        if st.button("Ingresar", use_container_width=True):
            if not df_users.empty:
                user_row = df_users[(df_users['usuario'] == login_user) & (df_users['password'] == str(login_pass))]
                if not user_row.empty:
                    if str(user_row.iloc[0]['activo']).upper() in ['TRUE', '1', 'SI']:
                        st.session_state.logged_in = True
                        st.session_state.login_user = login_user
                        st.session_state.nombre_completo = user_row.iloc[0]['nombre']
                        st.session_state.user_role = user_row.iloc[0]['rol']
                        st.rerun()
                    else:
                        st.warning("⚠️ Tu cuenta está pendiente de activación.")
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
            else:
                st.error("Error al cargar usuarios.")
                
    with tab_reg:
        reg_nombre = st.text_input("Nombre Completo")
        reg_user = st.text_input("Nombre de Usuario (Login)")
        reg_pass = st.text_input("Contraseña", type="password")
        
        if st.button("Enviar Registro", use_container_width=True):
            if reg_nombre and reg_user and reg_pass:
                if not df_users.empty and reg_user in df_users['usuario'].values:
                    st.error("❌ El usuario ya existe.")
                else:
                    nuevo_id = int(df_users['id'].max()) + 1 if not df_users.empty and pd.notna(df_users['id'].max()) else 1
                    ws_users.append_row([nuevo_id, reg_nombre, reg_user, reg_pass, "Usuario", "FALSE"])
                    st.success("✅ Registro enviado. Espera activación.")
            else:
                st.warning("⚠️ Rellena todos los campos.")

# --- APLICACIÓN PRINCIPAL (LOGUEADO) ---
else:
    with st.sidebar:
        st.markdown("## Jota Jota Foods")
            
        st.markdown("---")
        st.write(f"👤 **Usuario:** {st.session_state.nombre_completo}")
        st.write(f"🛡️ **Rol:** {st.session_state.user_role}")
        st.markdown("---")
        
        menu = st.radio("Navegación", ["📊 Dashboard & Métricas", "📁 Proyectos (CRUD)", "📝 Tareas", "📅 Vista Gantt"])
        
        if st.session_state.user_role == "Admin":
            st.markdown("---")
            if st.checkbox("⚙️ Admin Usuarios"):
                menu = "Admin Usuarios"
                
        st.markdown("---")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.logged_in = False
            st.session_state.login_user = ""
            st.session_state.nombre_completo = ""
            st.session_state.user_role = ""
            st.rerun()

    df_proyectos, ws_proyectos = get_dataframe("proyectos")
    df_tareas, ws_tareas = get_dataframe("tareas")

    # ------------------ MENU: DASHBOARD ------------------
    if menu == "📊 Dashboard & Métricas":
        st.title("📊 Dashboard de Control")
        if df_proyectos.empty:
            st.info("Agrega proyectos para ver estadísticas.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                if 'departamento' in df_proyectos.columns:
                    fig = px.pie(df_proyectos, names='departamento', title="Proyectos por Departamento", hole=0.4,
                                 color_discrete_sequence=['#002387', '#6eb43f', '#a3d182', '#3350a0'])
                    st.plotly_chart(fig, use_container_width=True)
            with c2:
                if not df_tareas.empty and 'departamento' in df_proyectos.columns:
                    df_m = pd.merge(df_tareas, df_proyectos, on='id_proyecto', how='left')
                    fig2 = px.bar(df_m, x='departamento', color='estado', title="Estado de Tareas por Departamento",
                                  color_discrete_map={"Completado": "#00c875", "En curso": "#fdab3d", "Bloqueado": "#e2445c", "No iniciado": "#c4c4c4"})
                    st.plotly_chart(fig2, use_container_width=True)

    # ------------------ MENU: CRUD PROYECTOS ------------------
    elif menu == "📁 Proyectos (CRUD)":
        st.title("📁 Gestión de Proyectos")
        tab1, tab2, tab3 = st.tabs(["✨ Crear Proyecto", "👀 Ver y Editar", "🗑️ Eliminar"])
        
        with tab1:
            with st.form("crear_proyecto_form"):
                n_proy = st.text_input("Nombre del Proyecto")
                d_proy = st.text_area("Descripción")
                depto = st.selectbox("Departamento", DEPARTAMENTOS)
                
                if st.form_submit_button("Guardar Proyecto") and n_proy:
                    nuevo_id = int(df_proyectos['id_proyecto'].max()) + 1 if not df_proyectos.empty and pd.notna(df_proyectos['id_proyecto'].max()) else 1
                    fecha_hoy = datetime.today().strftime('%d/%m/%Y')
                    ws_proyectos.append_row([nuevo_id, n_proy, d_proy, depto, fecha_hoy])
                    st.success(f"Proyecto '{n_proy}' creado.")
                    st.rerun()

        with tab2:
            if not df_proyectos.empty:
                df_proyectos['Estado Proyecto'] = df_proyectos['id_proyecto'].apply(lambda x: calcular_estado_proyecto(x, df_tareas))
                
                st.markdown("### 🔍 Filtro de Visualización")
                lista_deptos_p = ["Todos"] + sorted(df_proyectos['departamento'].dropna().unique().tolist())
                filtro_depto_p = st.selectbox("🏢 Filtrar por Departamento", lista_deptos_p, key="filtro_proyectos_depto")
                
                df_proyectos_view = df_proyectos.copy()
                if filtro_depto_p != "Todos":
                    df_proyectos_view = df_proyectos_view[df_proyectos_view['departamento'] == filtro_depto_p]
                
                st.dataframe(df_proyectos_view, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.markdown("### ✏️ Editar Proyecto")
                
                if not df_proyectos_view.empty:
                    proy_editar = st.selectbox("Selecciona Proyecto a editar", df_proyectos_view['nombre_proyecto'].values, key="edit_select_proy")
                    idx = df_proyectos[df_proyectos['nombre_proyecto'] == proy_editar].index[0]
                    datos_proy = df_proyectos.iloc[idx]
                    
                    with st.form("editar_proy_form"):
                        edit_nombre = st.text_input("Nombre", value=datos_proy['nombre_proyecto'])
                        edit_desc = st.text_area("Descripción", value=datos_proy['descripcion'])
                        
                        depto_actual = datos_proy.get('departamento', DEPARTAMENTOS[0])
                        idx_depto = DEPARTAMENTOS.index(depto_actual) if depto_actual in DEPARTAMENTOS else 0
                        edit_depto = st.selectbox("Departamento", DEPARTAMENTOS, index=idx_depto)
                        
                        if st.form_submit_button("Actualizar"):
                            num_fila = int(idx) + 2
                            ws_proyectos.update_cell(num_fila, 2, edit_nombre)
                            ws_proyectos.update_cell(num_fila, 3, edit_desc)
                            ws_proyectos.update_cell(num_fila, 4, edit_depto)
                            st.success("Proyecto actualizado!")
                            st.rerun()
                else:
                    st.info("No hay proyectos en este departamento para editar.")

        with tab3:
            if not df_proyectos.empty:
                proy_borrar = st.selectbox("Selecciona Proyecto a ELIMINAR", df_proyectos['nombre_proyecto'].values)
                if st.button("🔥 Confirmar Borrado Total", use_container_width=True):
                    idx_p = df_proyectos[df_proyectos['nombre_proyecto'] == proy_borrar].index[0]
                    id_p_real = df_proyectos.iloc[idx_p]['id_proyecto']
                    
                    if not df_tareas.empty and 'id_proyecto' in df_tareas.columns:
                        indices_tareas = df_tareas[df_tareas['id_proyecto'] == id_p_real].index.tolist()
                        for i in sorted(indices_tareas, reverse=True):
                            ws_tareas.delete_rows(i + 2)
                    
                    ws_proyectos.delete_rows(int(idx_p) + 2)
                    st.success("Proyecto eliminado.")
                    st.rerun()

    # ------------------ MENU: CRUD TAREAS ------------------
    elif menu == "📝 Tareas":
        st.title("📝 Control de Tareas")
        
        if df_proyectos.empty:
            st.warning("Primero debes crear un Proyecto antes de asignar tareas.")
        else:
            tab_t1, tab_t2, tab_t3 = st.tabs(["➕ Añadir Tarea", "✏️ Gestionar y Modificar", "📋 Vista Lista (Interactiva)"])
            
            with tab_t1:
                dict_proy = dict(zip(df_proyectos['nombre_proyecto'], df_proyectos['id_proyecto']))
                sel_proy = st.selectbox("Proyecto Asociado", list(dict_proy.keys()))
                
                with st.form("crear_tarea_form"):
                    t_nombre = st.text_input("Nombre de la Tarea")
                    t_prioridad = st.selectbox("Prioridad", ["Baja", "Media", "Alta"])
                    t_estado = st.selectbox("Estado", ["No iniciado", "Bloqueado", "En curso", "Completado"])
                    t_resp = st.text_input("Responsable")
                    t_inicio = st.date_input("Fecha de Inicio")
                    t_entrega = st.date_input("Fecha de Entrega")
                    t_obs = st.text_area("Observaciones")
                    
                    if st.form_submit_button("Crear Tarea") and t_nombre:
                        f_inicio_fmt = t_inicio.strftime('%d/%m/%Y')
                        f_entrega_fmt = t_entrega.strftime('%d/%m/%Y')
                        
                        nuevo_id_t = int(df_tareas['id_tarea'].max()) + 1 if not df_tareas.empty and 'id_tarea' in df_tareas.columns and pd.notna(df_tareas['id_tarea'].max()) else 1
                        ws_tareas.append_row([
                            nuevo_id_t, int(dict_proy[sel_proy]), t_nombre, t_prioridad, 
                            t_estado, t_resp, f_inicio_fmt, f_entrega_fmt, t_obs
                        ])
                        st.success("Tarea registrada.")
                        st.rerun()

            with tab_t2:
                if not df_tareas.empty and 'tarea' in df_tareas.columns:
                    df_merge_t = pd.merge(df_tareas, df_proyectos, on='id_proyecto', how='left')
                    df_merge_t['descriptivo'] = df_merge_t['nombre_proyecto'] + " -> " + df_merge_t['tarea']
                    
                    sel_tarea_edit = st.selectbox("Selecciona la Tarea a gestionar", df_merge_t['descriptivo'].values)
                    idx_t = df_merge_t[df_merge_t['descriptivo'] == sel_tarea_edit].index[0]
                    datos_t = df_tareas.iloc[idx_t]
                    
                    col_ed1, col_ed2 = st.columns(2)
                    with col_ed1:
                        with st.form("form_ed_tar"):
                            ed_t_estado = st.selectbox("Estado", ["No iniciado", "Bloqueado", "En curso", "Completado"], index=["No iniciado", "Bloqueado", "En curso", "Completado"].index(datos_t.get('estado', 'No iniciado')))
                            ed_t_prio = st.selectbox("Prioridad", ["Baja", "Media", "Alta"], index=["Baja", "Media", "Alta"].index(datos_t.get('prioridad', 'Baja')))
                            ed_t_resp = st.text_input("Responsable", value=datos_t.get('responsable', ''))
                            ed_t_obs = st.text_area("Observaciones", value=datos_t.get('observaciones', ''))
                            
                            if st.form_submit_button("Guardar Cambios"):
                                fila_t = int(idx_t) + 2
                                ws_tareas.update_cell(fila_t, 4, ed_t_prio)
                                ws_tareas.update_cell(fila_t, 5, ed_t_estado)
                                ws_tareas.update_cell(fila_t, 6, ed_t_resp)
                                ws_tareas.update_cell(fila_t, 9, ed_t_obs)
                                st.success("Tarea modificada.")
                                st.rerun()
                                
                    with col_ed2:
                        if st.button("🗑️ Eliminar esta Tarea", use_container_width=True):
                            ws_tareas.delete_rows(int(idx_t) + 2)
                            st.success("Tarea eliminada.")
                            st.rerun()
                else:
                    st.write("No hay tareas registradas.")

            with tab_t3:
                if not df_tareas.empty and 'tarea' in df_tareas.columns:
                    df_ver = pd.merge(df_tareas, df_proyectos, on='id_proyecto', how='left')
                    
                    st.markdown("### 🔍 Filtros")
                    col_f1, col_f2 = st.columns(2)
                    
                    with col_f1:
                        lista_deptos = ["Todos"] + sorted(df_ver['departamento'].dropna().unique().tolist())
                        filtro_depto = st.selectbox("🏢 Filtrar por Departamento", lista_deptos, key="list_depto")
                        
                    if filtro_depto != "Todos":
                        df_ver = df_ver[df_ver['departamento'] == filtro_depto]
                        
                    with col_f2:
                        lista_proys = ["Todos"] + sorted(df_ver['nombre_proyecto'].dropna().unique().tolist())
                        filtro_proy = st.selectbox("📁 Filtrar por Proyecto", lista_proys, key="list_proy")
                        
                    if filtro_proy != "Todos":
                        df_ver = df_ver[df_ver['nombre_proyecto'] == filtro_proy]
                        
                    st.markdown("---")
                    
                    if df_ver.empty:
                        st.info("No se encontraron tareas con los filtros seleccionados.")
                    else:
                        def color_estado(val):
                            if val == 'Completado': return 'background-color: #00c875; color: white; font-weight: bold; text-align: center;'
                            elif val == 'En curso': return 'background-color: #fdab3d; color: white; font-weight: bold; text-align: center;'
                            elif val == 'Bloqueado': return 'background-color: #e2445c; color: white; font-weight: bold; text-align: center;'
                            elif val == 'No iniciado': return 'background-color: #c4c4c4; color: white; font-weight: bold; text-align: center;'
                            return ''

                        def color_prioridad(val):
                            if val == 'Alta': return 'background-color: #e2445c; color: white; font-weight: bold; text-align: center;'
                            elif val == 'Media': return 'background-color: #fdab3d; color: white; font-weight: bold; text-align: center;'
                            elif val == 'Baja': return 'background-color: #00c875; color: white; font-weight: bold; text-align: center;'
                            return ''

                        cols_mostrar = ['departamento', 'nombre_proyecto', 'tarea', 'responsable', 'prioridad', 'estado', 'fecha_inicio', 'fecha_entrega', 'observaciones']
                        cols_existentes = [c for c in cols_mostrar if c in df_ver.columns]
                        
                        df_final = df_ver[cols_existentes].copy()
                        
                        df_final.rename(columns={
                            'departamento': 'Departamento',
                            'nombre_proyecto': 'Proyecto',
                            'tarea': 'Elemento / Tarea',
                            'responsable': 'Responsable',
                            'prioridad': 'Prioridad',
                            'estado': 'Estado',
                            'fecha_inicio': 'F. Inicio',
                            'fecha_entrega': 'F. Entrega',
                            'observaciones': 'Observaciones'
                        }, inplace=True)
                        
                        styler = df_final.style.map(color_estado, subset=['Estado']).map(color_prioridad, subset=['Prioridad'])
                        
                        st.info("💡 **Consejo:** Haz clic en la casilla vacía a la izquierda de cualquier tarea para editarla rápidamente.")
                        
                        evento_seleccion = st.dataframe(
                            styler, 
                            use_container_width=True, 
                            hide_index=True,
                            on_select="rerun",
                            selection_mode="single-row"
                        )
                        
                        # --- DESPLIEGUE DEL FORMULARIO DE EDICIÓN RÁPIDA ---
                        if hasattr(evento_seleccion, "selection") and len(evento_seleccion.selection.rows) > 0:
                            indice_seleccionado = evento_seleccion.selection.rows[0]
                            id_tarea_seleccionada = df_ver.iloc[indice_seleccionado]['id_tarea']
                            
                            idx_t_real = df_tareas[df_tareas['id_tarea'] == id_tarea_seleccionada].index[0]
                            datos_tarea_real = df_tareas.iloc[idx_t_real]
                            
                            st.markdown("---")
                            st.markdown(f"### ✏️ Edición Rápida: **{datos_tarea_real['tarea']}**")
                            
                            col_ed1, col_ed2 = st.columns(2)
                            with col_ed1:
                                # ¡EL TRUCO ESTÁ AQUÍ! Añadimos el ID de la tarea a la clave del formulario para forzar su actualización
                                with st.form(f"form_ed_tar_rapida_{id_tarea_seleccionada}"):
                                    ed_t_estado = st.selectbox("Estado", ["No iniciado", "Bloqueado", "En curso", "Completado"], index=["No iniciado", "Bloqueado", "En curso", "Completado"].index(datos_tarea_real.get('estado', 'No iniciado')))
                                    ed_t_prio = st.selectbox("Prioridad", ["Baja", "Media", "Alta"], index=["Baja", "Media", "Alta"].index(datos_tarea_real.get('prioridad', 'Baja')))
                                    ed_t_resp = st.text_input("Responsable", value=datos_tarea_real.get('responsable', ''))
                                    ed_t_obs = st.text_area("Observaciones", value=datos_tarea_real.get('observaciones', ''))
                                    
                                    if st.form_submit_button("Guardar Cambios Rápidos"):
                                        fila_t = int(idx_t_real) + 2
                                        ws_tareas.update_cell(fila_t, 4, ed_t_prio)
                                        ws_tareas.update_cell(fila_t, 5, ed_t_estado)
                                        ws_tareas.update_cell(fila_t, 6, ed_t_resp)
                                        ws_tareas.update_cell(fila_t, 9, ed_t_obs)
                                        st.success("¡Tarea actualizada correctamente!")
                                        st.rerun()
                                        
                            with col_ed2:
                                st.write("Opciones críticas:")
                                if st.button("🗑️ Eliminar esta Tarea permanentemente", use_container_width=True, key=f"del_rapida_{id_tarea_seleccionada}"):
                                    ws_tareas.delete_rows(int(idx_t_real) + 2)
                                    st.success("Tarea eliminada.")
                                    st.rerun()
                else:
                    st.info("No hay tareas registradas en la base de datos.")

    # ------------------ MENU: GANTT ------------------
    elif menu == "📅 Vista Gantt":
        st.title("📅 Cronograma (Gantt)")
        if not df_tareas.empty and 'fecha_inicio' in df_tareas.columns:
            try:
                df_gantt = df_tareas.copy()
                df_gantt = pd.merge(df_gantt, df_proyectos, on='id_proyecto', how='left')
                
                df_gantt['fecha_inicio'] = pd.to_datetime(df_gantt['fecha_inicio'], format='%d/%m/%Y', errors='coerce')
                df_gantt['fecha_entrega'] = pd.to_datetime(df_gantt['fecha_entrega'], format='%d/%m/%Y', errors='coerce')
                
                df_gantt = df_gantt.dropna(subset=['fecha_inicio', 'fecha_entrega'])
                
                st.markdown("### 🔍 Filtros")
                col_g1, col_g2 = st.columns(2)
                
                with col_g1:
                    lista_deptos_g = ["Todos"] + sorted(df_gantt['departamento'].dropna().unique().tolist())
                    filtro_depto_g = st.selectbox("🏢 Filtrar por Departamento", lista_deptos_g, key="gantt_depto")
                    
                if filtro_depto_g != "Todos":
                    df_gantt = df_gantt[df_gantt['departamento'] == filtro_depto_g]
                    
                with col_g2:
                    lista_proys_g = ["Todos"] + sorted(df_gantt['nombre_proyecto'].dropna().unique().tolist())
                    filtro_proy_g = st.selectbox("📁 Filtrar por Proyecto", lista_proys_g, key="gantt_proy")
                    
                if filtro_proy_g != "Todos":
                    df_gantt = df_gantt[df_gantt['nombre_proyecto'] == filtro_proy_g]
                    
                st.markdown("---")
                
                if df_gantt.empty:
                    st.info("No se encontraron tareas con los filtros seleccionados.")
                else:
                    fig = px.timeline(df_gantt, x_start="fecha_inicio", x_end="fecha_entrega", y="tarea", color="estado", hover_data=["responsable", "nombre_proyecto"],
                                      color_discrete_map={"Completado": "#00c875", "En curso": "#fdab3d", "Bloqueado": "#e2445c", "No iniciado": "#c4c4c4"})
                    fig.update_yaxes(autorange="reversed")
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error al graficar el cronograma: {e}")
        else:
            st.info("No hay datos suficientes para el Gantt.")

    # ------------------ MENU: ADMIN ------------------
    elif menu == "Admin Usuarios":
        st.title("⚙️ Gestión de Usuarios")
        df_users, ws_users = get_dataframe("usuarios")
        if not df_users.empty:
            st.dataframe(df_users[['id', 'nombre', 'usuario', 'rol', 'activo']], use_container_width=True, hide_index=True)
            usuario_sel = st.selectbox("Selecciona usuario a modificar", df_users['usuario'].values)
            idx_u = df_users[df_users['usuario'] == usuario_sel].index[0]
            datos_u = df_users.iloc[idx_u]
            
            c1, c2 = st.columns(2)
            with c1:
                nuevo_estado = st.selectbox("Activo", ["TRUE", "FALSE"], index=0 if str(datos_u['activo']).upper() in ['TRUE', '1'] else 1)
            with c2:
                nuevo_rol = st.selectbox("Rol", ["Usuario", "Admin"], index=0 if datos_u['rol'] == "Usuario" else 1)
                
            if st.button("Aplicar cambios", use_container_width=True):
                fila_u = int(idx_u) + 2
                ws_users.update_cell(fila_u, 5, nuevo_rol)
                ws_users.update_cell(fila_u, 6, nuevo_estado)
                st.success("Usuario actualizado.")
                st.rerun()
