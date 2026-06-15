import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
from datetime import datetime, json

# 1. Configuración de la página
st.set_page_config(page_title="Gestión de Proyectos Pro", layout="wide", page_icon="📊")

# 2. Conexión segura a Google Sheets
@st.cache_resource
def conectar_gsheet():
    # Ámbitos requeridos para Sheets y Drive
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Intenta leer desde secrets (Producción en Streamlit Cloud) o local (credentials.json)
    try:
        if "gcp_credentials" in st.secrets:
            # Convierte el string JSON de secrets en diccionario
            creds_dict = json.loads(st.secrets["gcp_credentials"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        else:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        
        client = gspread.authorize(creds)
        # Reemplaza con el nombre exacto de tu archivo de Google Sheets
        sheet = client.open("Control_Proyectos_DB") 
        return sheet
    except Exception as e:
        st.error(f"❌ Error de conexión a la Base de Datos: {e}")
        return None

db = conectar_gsheet()

# Helper para obtener datos de una pestaña como DataFrame
def get_dataframe(sheet_name):
    if db:
        try:
            worksheet = db.worksheet(sheet_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data), worksheet
        except Exception as e:
            st.error(f"Error al leer la pestaña {sheet_name}: {e}")
            return pd.DataFrame(), None
    return pd.DataFrame(), None

# 3. Estado de la Sesión (Login)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_role" not in st.session_state:
    st.session_state.user_role = ""

# --- PANTALLA DE LOGIN Y REGISTRO ---
if not st.session_state.logged_in:
    st.title("🚀 Sistema de Gestión de Proyectos")
    tab_login, tab_reg = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse"])
    
    df_users, ws_users = get_dataframe("usuarios")
    
    with tab_login:
        login_user = st.text_input("Usuario", key="login_u")
        login_pass = st.text_input("Contraseña", type="password", key="login_p")
        
        if st.button("Ingresar", use_container_width=True):
            if not df_users.empty:
                # Filtrar usuario
                user_row = df_users[(df_users['usuario'] == login_user) & (df_users['password'] == str(login_pass))]
                if not user_row.empty:
                    if str(user_row.iloc[0]['activo']).upper() in ['TRUE', '1', 'SI']:
                        st.session_state.logged_in = True
                        st.session_state.username = login_user
                        st.session_state.user_role = user_row.iloc[0]['rol']
                        st.success(f"¡Bienvenido {user_row.iloc[0]['nombre']}!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Tu cuenta está pendiente de activación por el Administrador.")
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
            else:
                st.error("Error al cargar la base de datos de usuarios.")
                
    with tab_reg:
        reg_nombre = st.text_input("Nombre Completo")
        reg_user = st.text_input("Nombre de Usuario (Login)")
        reg_pass = st.text_input("Contraseña", type="password")
        
        if st.button("Enviar Registro", use_container_width=True):
            if reg_nombre and reg_user and reg_pass:
                if not df_users.empty and reg_user in df_users['usuario'].values:
                    st.error("❌ El nombre de usuario ya existe.")
                else:
                    nuevo_id = int(df_users['id'].max()) + 1 if not df_users.empty and pd.notna(df_users['id'].max()) else 1
                    # Todo usuario nuevo se registra como 'Usuario' y 'FALSE' (Inactivo) hasta que el admin lo valide
                    ws_users.append_row([nuevo_id, reg_nombre, reg_user, reg_pass, "Usuario", "FALSE"])
                    st.success("✅ Registro enviado. Espera a que el Administrador valide tu cuenta.")
            else:
                st.warning("⚠️ Por favor rellena todos los campos.")

# --- APLICACIÓN PRINCIPAL (LOGUEADO) ---
else:
    # Barra lateral de navegación
    with st.sidebar:
        st.write(f"👤 **Usuario:** {st.session_state.username} ({st.session_state.user_role})")
        menu = st.radio("Navegación", ["📊 Dashboard & Métricas", "📁 Proyectos (CRUD)", "📝 Tareas", "📅 Vista Gantt"])
        
        if st.session_state.user_role == "Admin":
            st.markdown("---")
            st.write("⚙️ **Panel de Administración**")
            if st.checkbox("Validar Usuarios"):
                menu = "Admin Usuarios"
                
        st.markdown("---")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_role = ""
            st.rerun()

    # Carga de datos global para las pestañas de la app
    df_proyectos, ws_proyectos = get_dataframe("proyectos")
    df_tareas, ws_tareas = get_dataframe("tareas")

    # ------------------ MENU: DASHBOARD ------------------
    if menu == "📊 Dashboard & Métricas":
        st.title("📊 Dashboard de Control")
        
        if df_tareas.empty or df_proyectos.empty:
            st.info("Aún no hay suficientes datos para generar estadísticas. Empieza agregando proyectos y tareas.")
        else:
            # Métricas KPI Top
            total_tareas = len(df_tareas)
            completadas = len(df_tareas[df_tareas['estado'] == 'Completado'])
            en_curso = len(df_tareas[df_tareas['estado'] == 'En curso'])
            bloqueadas = len(df_tareas[df_tareas['estado'] == 'Bloqueado'])
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Tareas", total_tareas)
            c2.metric("Completadas ✅", completadas)
            c3.metric("En Curso ⏳", en_curso)
            c4.metric("Bloqueadas 🚨", bloqueadas)
            
            st.markdown("---")
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.subheader("Estado de Tareas por Proyecto")
                # Unir DataFrames para tener el nombre del proyecto
                df_merge = pd.merge(df_tareas, df_proyectos, on='id_proyecto', how='left')
                if not df_merge.empty:
                    fig_proy = px.bar(df_merge, x='nombre_proyecto', color='estado', 
                                      title="Tareas por Proyecto y su Estado",
                                      barmode='stack')
                    st.plotly_chart(fig_proy, use_container_width=True)
            
            with col_graf2:
                st.subheader("Carga de Trabajo por Responsable")
                if 'responsable' in df_tareas.columns and not df_tareas.empty:
                    fig_resp = px.histogram(df_tareas, x='responsable', color='estado',
                                            title="Distribución de tareas asignadas")
                    st.plotly_chart(fig_resp, use_container_width=True)

    # ------------------ MENU: CRUD PROYECTOS ------------------
    elif menu == "📁 Proyectos (CRUD)":
        st.title("📁 Gestión de Proyectos")
        
        tab1, tab2, tab3 = st.tabs(["✨ Crear Proyecto", "👀 Ver y Editar", "🗑️ Eliminar"])
        
        with tab1:
            with st.form("crear_proyecto_form"):
                n_proy = st.text_input("Nombre del Proyecto")
                d_proy = st.text_area("Descripción")
                enviar = st.form_submit_button("Guardar Proyecto")
                
                if enviar and n_proy:
                    nuevo_id = int(df_proyectos['id_proyecto'].max()) + 1 if not df_proyectos.empty and pd.notna(df_proyectos['id_proyecto'].max()) else 1
                    fecha_hoy = datetime.today().strftime('%Y-%m-%d')
                    ws_proyectos.append_row([nuevo_id, n_proy, d_proy, fecha_hoy])
                    st.success(f"Proyecto '{n_proy}' creado correctamente.")
                    st.rerun()

        with tab2:
            if df_proyectos.empty:
                st.write("No hay proyectos registrados.")
            else:
                st.dataframe(df_proyectos, use_container_width=True)
                st.markdown("### Editar Proyecto")
                proy_editar = st.selectbox("Selecciona Proyecto a modificar", df_proyectos['nombre_proyecto'].values)
                
                # Obtener la fila correspondiente
                idx = df_proyectos[df_proyectos['nombre_proyecto'] == proy_editar].index[0]
                datos_proy = df_proyectos.iloc[idx]
                
                with st.form("editar_proy_form"):
                    edit_nombre = st.text_input("Nombre del Proyecto", value=datos_proy['nombre_proyecto'])
                    edit_desc = st.text_area("Descripción", value=datos_proy['descripcion'])
                    btn_editar = st.form_submit_button("Actualizar")
                    
                    if btn_editar:
                        # En gspread, las filas empiezan en 1 y la cabecera es la 1. Por ende, la fila real es index + 2
                        num_fila = int(idx) + 2
                        ws_proyectos.update_cell(num_fila, 2, edit_nombre)
                        ws_proyectos.update_cell(num_fila, 3, edit_desc)
                        st.success("¡Proyecto actualizado con éxito!")
                        st.rerun()

        with tab3:
            if df_proyectos.empty:
                st.write("No hay proyectos para eliminar.")
            else:
                proy_borrar = st.selectbox("Selecciona Proyecto a ELIMINAR permanentemente", df_proyectos['nombre_proyecto'].values, key="del_p")
                st.warning("⚠️ ATENCIÓN: Al borrar este proyecto, se eliminarán en cascada todas las tareas vinculadas.")
                
                if st.button("🔥 Confirmar Borrado Total", use_container_width=True):
                    idx_p = df_proyectos[df_proyectos['nombre_proyecto'] == proy_borrar].index[0]
                    id_p_real = df_proyectos.iloc[idx_p]['id_proyecto']
                    
                    # 1. Borrar tareas vinculadas en el gsheet (de abajo hacia arriba para no alterar índices concurrentes)
                    if not df_tareas.empty:
                        # Buscar los índices de filas correspondientes en tareas
                        indices_tareas = df_tareas[df_tareas['id_proyecto'] == id_p_real].index.tolist()
                        for i in sorted(indices_tareas, reverse=True):
                            ws_tareas.delete_rows(i + 2)
                    
                    # 2. Borrar el proyecto
                    ws_proyectos.delete_rows(int(idx_p) + 2)
                    st.success("Proyecto y tareas asociadas eliminados correctamente.")
                    st.rerun()

    # ------------------ MENU: CRUD TAREAS ------------------
    elif menu == "📝 Tareas":
        st.title("📝 Control de Tareas")
        
        if df_proyectos.empty:
            st.warning("Primero debes crear un Proyecto antes de asignar tareas.")
        else:
            tab_t1, tab_t2, tab_t3 = st.tabs(["➕ Añadir Tarea", "✏️ Gestionar y Modificar", "📋 Vista Lista"])
            
            with tab_t1:
                # Diccionario para mapear nombres de proyecto con su ID
                dict_proy = dict(zip(df_proyectos['nombre_proyecto'], df_proyectos['id_proyecto']))
                sel_proy = st.selectbox("Proyecto Asociado", list(dict_proy.keys()))
                
                with st.form("crear_tarea_form"):
                    t_nombre = st.text_input("Nombre de la Tarea")
                    t_prioridad = st.selectbox("Prioridad", ["Baja", "Media", "Alta"])
                    t_estado = st.selectbox("Estado", ["No iniciado", "Bloqueado", "En curso", "Completado"])
                    t_resp = st.text_input("Responsable (Email o Nombre)")
                    t_inicio = st.date_input("Fecha de Inicio")
                    t_entrega = st.date_input("Fecha de Entrega")
                    t_obs = st.text_area("Observaciones")
                    
                    btn_tarea = st.form_submit_button("Crear Tarea")
                    
                    if btn_tarea and t_nombre:
                        nuevo_id_t = int(df_tareas['id_tarea'].max()) + 1 if not df_tareas.empty and pd.notna(df_tareas['id_tarea'].max()) else 1
                        ws_tareas.append_row([
                            nuevo_id_t, 
                            int(dict_proy[sel_proy]), 
                            t_nombre, 
                            t_prioridad, 
                            t_estado, 
                            t_resp, 
                            str(t_inicio), 
                            str(t_entrega), 
                            t_obs
                        ])
                        st.success("Tarea registrada correctamente.")
                        st.rerun()

            with tab_t2:
                if df_tareas.empty:
                    st.write("No hay tareas registradas aún.")
                else:
                    # Buscador de tarea por nombre descriptivo
                    df_merge_t = pd.merge(df_tareas, df_proyectos, on='id_proyecto', how='left')
                    df_merge_t['descriptivo'] = df_merge_t['nombre_proyecto'] + " -> " + df_merge_t['tarea']
                    
                    sel_tarea_edit = st.selectbox("Selecciona la Tarea a gestionar", df_merge_t['descriptivo'].values)
                    
                    # Extraer índice de la tarea seleccionada
                    idx_t = df_merge_t[df_merge_t['descriptivo'] == sel_tarea_edit].index[0]
                    datos_t = df_tareas.iloc[idx_t]
                    
                    col_ed1, col_ed2 = st.columns(2)
                    with col_ed1:
                        st.markdown("#### Actualizar Datos")
                        with st.form("form_ed_tar"):
                            ed_t_estado = st.selectbox("Estado", ["No iniciado", "Bloqueado", "En curso", "Completado"], index=["No iniciado", "Bloqueado", "En curso", "Completado"].index(datos_t['estado']))
                            ed_t_prio = st.selectbox("Prioridad", ["Baja", "Media", "Alta"], index=["Baja", "Media", "Alta"].index(datos_t['prioridad']))
                            ed_t_resp = st.text_input("Responsable", value=datos_t['responsable'])
                            ed_t_obs = st.text_area("Observaciones", value=datos_t['observaciones'])
                            
                            if st.form_submit_button("Guardar Cambios"):
                                fila_t = int(idx_t) + 2
                                ws_tareas.update_cell(fila_t, 4, ed_t_prio)
                                ws_tareas.update_cell(fila_t, 5, ed_t_estado)
                                ws_tareas.update_cell(fila_t, 6, ed_t_resp)
                                ws_tareas.update_cell(fila_t, 9, ed_t_obs)
                                st.success("Tarea modificada con éxito.")
                                st.rerun()
                                
                    with col_ed2:
                        st.markdown("#### Acciones Críticas")
                        st.write("Si deseas eliminar solo esta tarea del proyecto:")
                        if st.button("🗑️ Eliminar esta Tarea", use_container_width=True):
                            ws_tareas.delete_rows(int(idx_t) + 2)
                            st.success("Tarea eliminada.")
                            st.rerun()

            with tab_t3:
                if not df_tareas.empty:
                    df_ver = pd.merge(df_tareas, df_proyectos, on='id_proyecto', how='left')
                    st.dataframe(df_ver[['nombre_proyecto', 'tarea', 'prioridad', 'estado', 'responsable', 'fecha_inicio', 'fecha_entrega', 'observaciones']], use_container_width=True)
                else:
                    st.write("Sin tareas en la lista.")

    # ------------------ MENU: GANTT ------------------
    elif menu == "📅 Vista Gantt":
        st.title("📅 Calendario y Diagrama de Gantt")
        
        if df_tareas.empty:
            st.info("Agrega tareas con fechas de inicio y entrega para visualizar el Gantt.")
        else:
            try:
                # Copia para formateo
                df_gantt = df_tareas.copy()
                df_gantt = pd.merge(df_gantt, df_proyectos, on='id_proyecto', how='left')
                
                # Conversión de fechas limpias
                df_gantt['fecha_inicio'] = pd.to_datetime(df_gantt['fecha_inicio'])
                df_gantt['fecha_entrega'] = pd.to_datetime(df_gantt['fecha_entrega'])
                
                fig = px.timeline(
                    df_gantt, 
                    start="fecha_inicio", 
                    end="fecha_entrega", 
                    y="tarea", 
                    color="estado",
                    hover_data=["responsable", "nombre_proyecto"],
                    title="Cronograma de Tareas"
                )
                fig.update_yaxis(autorange="reversed") # Tareas más recientes arriba
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error al estructurar las fechas del Gantt: {e}. Asegúrate de usar el formato YYYY-MM-DD.")

    # ------------------ MENU: VALIDAR USUARIOS (ADMIN) ------------------
    elif menu == "Admin Usuarios":
        st.title("⚙️ Activación y Gestión de Usuarios")
        df_users, ws_users = get_dataframe("usuarios")
        
        if not df_users.empty:
            st.dataframe(df_users[['id', 'nombre', 'usuario', 'rol', 'activo']], use_container_width=True)
            
            st.markdown("### Modificar estado de un usuario")
            usuario_sel = st.selectbox("Selecciona usuario", df_users['usuario'].values)
            idx_u = df_users[df_users['usuario'] == usuario_sel].index[0]
            datos_u = df_users.iloc[idx_u]
            
            c_act1, c_act2 = st.columns(2)
            with c_act1:
                nuevo_estado = st.selectbox("Activo", ["TRUE", "FALSE"], index=0 if str(datos_u['activo']).upper() in ['TRUE', '1'] else 1)
            with c_act2:
                nuevo_rol = st.selectbox("Rol", ["Usuario", "Admin"], index=0 if datos_u['rol'] == "Usuario" else 1)
                
            if st.button("Aplicar cambios de usuario", use_container_width=True):
                fila_u = int(idx_u) + 2
                ws_users.update_cell(fila_u, 5, nuevo_rol)
                ws_users.update_cell(fila_u, 6, nuevo_estado)
                st.success(f"Usuario {usuario_sel} actualizado.")
                st.rerun()