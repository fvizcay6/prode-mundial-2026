import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import datetime
import pytz

# ==========================================
# 1. CONFIGURACIÓN VISUAL
# ==========================================
st.set_page_config(page_title="🏆 Prode Mundial 2026: Ranking Oficial", layout="wide", page_icon="🥇")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    h1 {
        font-family: 'Arial Black', sans-serif;
        background: -webkit-linear-gradient(45deg, #CF00FF, #00FF87);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-transform: uppercase;
        font-size: 3em;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONSTANTES
# ==========================================
NOMBRE_HOJA_GOOGLE = "DB_Prode_2026"

# ==========================================
# 3. MOTOR DE CÁLCULO (Copiado de Admin)
# ==========================================

def limpiar_prediccion_fase(datos_usuario, fase):
    """
    Limpia la predicción de fases finales para evitar errores con celdas vacías.
    """
    input_str = datos_usuario.get(fase, "")
    input_str = input_str.strip()
    if not input_str:
        return []
    return [x.strip() for x in input_str.split(",") if x.strip()]

def calcular_puntaje_participante(datos_usuario, reales):
    puntos = 0
    desglose = {}
    posiciones = [1, 2, 3] 

    # --- 1. RONDA PARTIDO X PARTIDO ---
    pts_partidos = 0
    if "PARTIDOS" in reales:
        for key, resultado_real in reales["PARTIDOS"].items():
            if resultado_real != "-":
                pronostico = datos_usuario.get(key, "-")
                if pronostico == resultado_real:
                    pts_partidos += 1
    puntos += pts_partidos
    desglose['Partidos'] = pts_partidos

    # --- 2. FASE DE GRUPOS ---
    pts_grupos = 0
    if "GRUPOS" in reales:
        for grupo, data_real in reales["GRUPOS"].items():
            # Verificamos que existan las claves antes de acceder
            if data_real.get("1", "-") != "-" and data_real.get("2", "-") != "-" and data_real.get("3", "-") != "-":
                
                real_top3 = [data_real["1"], data_real["2"], data_real["3"]]
                puntos_reales = {
                    data_real["1"]: data_real.get("pts_1", 0),
                    data_real["2"]: data_real.get("pts_2", 0),
                    data_real["3"]: data_real.get("pts_3", 0),
                }
                
                for i in posiciones:
                    campo_usuario = f"{grupo}_{i}"
                    u_equipo = datos_usuario.get(campo_usuario)
                    r_equipo_en_posicion = data_real[str(i)]
                    
                    if u_equipo in real_top3:
                        pts_grupos += 10 
                        if u_equipo in puntos_reales:
                            pts_grupos += puntos_reales[u_equipo]
                    
                    if u_equipo == r_equipo_en_posicion:
                        pts_grupos += 5
    puntos += pts_grupos
    desglose['Grupos'] = pts_grupos
    
    # --- 3. FASES FINALES ---
    pts_octavos = 0
    pts_cuartos = 0
    pts_semis_base = 0 
    pts_tercer_puesto = 0 
    pts_final_campeon = 0 
    
    # Octavos
    u_octavos = limpiar_prediccion_fase(datos_usuario, "Octavos")
    if "OCTAVOS" in reales:
        for eq in u_octavos:
            if eq in reales["OCTAVOS"]: pts_octavos += 15
        
    # Cuartos
    u_cuartos = limpiar_prediccion_fase(datos_usuario, "Cuartos")
    if "CUARTOS" in reales:
        for eq in u_cuartos:
            if eq in reales["CUARTOS"]: pts_cuartos += 20

    # Semis + Jugar 3er Puesto
    u_semis = limpiar_prediccion_fase(datos_usuario, "Semis")
    if "SEMIS" in reales:
        for eq in u_semis:
            if eq in reales["SEMIS"]: 
                pts_semis_base += 25
                
                # Regla 3er puesto por descarte (si no es campeón ni subcampeón)
                campeon_r = reales.get("CAMPEON", "-")
                sub_r = reales.get("SUBCAMPEON", "-")
                if eq != campeon_r and eq != sub_r and campeon_r != "-":
                    pts_tercer_puesto += 30 
                
    # Ganador 3er puesto
    u_tercero = datos_usuario.get("Tercero")
    if "TERCERO_GANADOR" in reales and u_tercero == reales["TERCERO_GANADOR"]: 
        pts_tercer_puesto += 35 
    
    # Finalistas y Campeón
    u_campeon = datos_usuario.get("Campeon")
    u_sub = datos_usuario.get("Subcampeon")
    
    if "FINALISTAS" in reales:
        if u_campeon in reales["FINALISTAS"]: pts_final_campeon += 40
        if u_sub in reales["FINALISTAS"]: pts_final_campeon += 40
    
    if "CAMPEON" in reales and u_campeon == reales["CAMPEON"]: pts_final_campeon += 50
    
    # Totales
    puntos += pts_octavos + pts_cuartos + pts_semis_base + pts_tercer_puesto + pts_final_campeon
    
    desglose['Octavos'] = pts_octavos
    desglose['Cuartos'] = pts_cuartos
    desglose['Semifinales'] = pts_semis_base
    desglose['Tercer Puesto'] = pts_tercer_puesto
    desglose['Final/Campeon'] = pts_final_campeon
    desglose['TOTAL'] = puntos
    
    return desglose

# ==========================================
# 4. CONEXIÓN A DATOS (LECTURA)
# ==========================================
def obtener_datos_participantes():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
        creds_dict = json.loads(contenido_json_texto, strict=False)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # Hoja 1: Predicciones de los usuarios
        sheet = client.open(NOMBRE_HOJA_GOOGLE).sheet1
        return sheet.get_all_records()
    except Exception as e:
        st.error(f"❌ ERROR: No se pudo conectar a la DB de participantes. ({e})")
        return None

def obtener_resultados_oficiales_admin():
    """
    Lee los resultados oficiales guardados por el Admin en la hoja 'Resultados_Admin'
    """
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
        creds_dict = json.loads(contenido_json_texto, strict=False)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        try:
            # Abrir la pestaña específica donde el admin guardó el JSON
            sheet = client.open(NOMBRE_HOJA_GOOGLE).worksheet("Resultados_Admin")
            # Leemos la celda A1 que contiene todo el JSON
            json_texto = sheet.acell('A1').value
            
            if json_texto:
                return json.loads(json_texto)
            else:
                return None
        except gspread.exceptions.WorksheetNotFound:
            st.warning("⚠️ Aún no se ha creado la hoja 'Resultados_Admin'. El Admin debe guardar los resultados primero.")
            return None
            
    except Exception as e:
        st.error(f"❌ Error al leer resultados oficiales: {e}")
        return None

@st.cache_data(ttl=600) # Cache de 10 minutos para no saturar la API
def generar_ranking(resultados_reales_dict):
    datos_usuarios = obtener_datos_participantes()
    
    if not datos_usuarios:
        return pd.DataFrame(), None

    tabla = []
    for usuario in datos_usuarios:
        puntajes = calcular_puntaje_participante(usuario, resultados_reales_dict)
        
        fila = {
            "Participante": usuario["Participante"],
            "TOTAL": puntajes["TOTAL"],
            "Grupos": puntajes["Grupos"],
            "Octavos": puntajes["Octavos"],
            "Cuartos": puntajes["Cuartos"],
            "Semifinales": puntajes["Semifinales"],
            "3er Puesto": puntajes["Tercer Puesto"],
            "Final/Campeon": puntajes["Final/Campeon"],
        }
        tabla.append(fila)
        
    df = pd.DataFrame(tabla)
    
    # Desempate
    if not df.empty:
        df['Playoffs_Desempate'] = df['Octavos'] + df['Cuartos'] + df['Semifinales'] + df['3er Puesto'] + df['Final/Campeon']
        df = df.sort_values(
            by=["TOTAL", "Grupos", "Playoffs_Desempate"], 
            ascending=[False, False, False]
        ).drop(columns=['Playoffs_Desempate']).reset_index(drop=True)
        df.index += 1
    
    # Fecha de actualización
    ahora_arg = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
    fecha_act = ahora_arg.strftime("%d/%m/%Y %H:%M")
    
    return df, fecha_act

# ==========================================
# 5. APP PRINCIPAL
# ==========================================

st.title("🏆 RANKING MUNDIAL 2026")

# 1. Intentamos cargar los resultados oficiales desde la nube
resultados_nube = obtener_resultados_oficiales_admin()

if resultados_nube:
    RESULTADOS_REALES_ACTUALES = resultados_nube
else:
    # Si falla o está vacío, usamos estructura vacía
    st.info("ℹ️ Esperando carga de primeros resultados oficiales por parte del Administrador...")
    RESULTADOS_REALES_ACTUALES = { 
        "PARTIDOS": {}, "GRUPOS": {}, "OCTAVOS": [], "CUARTOS": [], 
        "SEMIS": [], "TERCERO_EQUIPOS": [], "TERCERO_GANADOR": "-", 
        "FINALISTAS": [], "CAMPEON": "-", "SUBCAMPEON": "-"
    }

# 2. Generamos el ranking con esos datos
ranking_df, fecha = generar_ranking(RESULTADOS_REALES_ACTUALES)

if not ranking_df.empty:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"✅ Tabla Actualizada: {fecha} (Hora ARG)")
    with col2:
        if st.button("🔄 Refrescar"):
            st.cache_data.clear()
            st.rerun()

    # Mostrar Podio
    if len(ranking_df) >= 3 and ranking_df.iloc[0]['TOTAL'] > 0:
        c1, c2, c3 = st.columns(3)
        c2.metric("🥇 1er Lugar", f"{ranking_df.iloc[0]['Participante']}", f"{ranking_df.iloc[0]['TOTAL']} pts")
        c1.metric("🥈 2do Lugar", f"{ranking_df.iloc[1]['Participante']}", f"{ranking_df.iloc[1]['TOTAL']} pts")
        c3.metric("🥉 3er Lugar", f"{ranking_df.iloc[2]['Participante']}", f"{ranking_df.iloc[2]['TOTAL']} pts")
    elif not ranking_df.empty and ranking_df.iloc[0]['TOTAL'] > 0:
        st.metric("🥇 Líder", f"{ranking_df.iloc[0]['Participante']}", f"{ranking_df.iloc[0]['TOTAL']} pts")

    st.markdown("---")
    
    # Mostrar Tabla Completa
    st.dataframe(
        ranking_df,
        use_container_width=True,
        height=600,
        column_config={
            "TOTAL": st.column_config.NumberColumn("🏆 TOTAL", format="%d", width="medium"),
            "Grupos": st.column_config.NumberColumn("Grupos", format="%d"),
            "Octavos": st.column_config.NumberColumn("Octavos", format="%d"),
            "Cuartos": st.column_config.NumberColumn("Cuartos", format="%d"),
            "Semifinales": st.column_config.NumberColumn("Semis", format="%d"),
            "3er Puesto": st.column_config.NumberColumn("3er Puesto", format="%d"),
            "Final/Campeon": st.column_config.NumberColumn("Final/Camp.", format="%d"),
        }
    )

else:
    st.warning("⚠️ No hay participantes registrados o no se pudo conectar a la base de datos.")