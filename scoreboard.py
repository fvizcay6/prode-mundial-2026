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
        text-align: center;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    /* Ajuste para centrar la tabla */
    .stDataFrame { width: 100%; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONSTANTES
# ==========================================
NOMBRE_HOJA_GOOGLE = "DB_Prode_2026"

# ==========================================
# 3. MOTOR DE CÁLCULO
# ==========================================

def limpiar_prediccion_fase(datos_usuario, fase):
    input_str = datos_usuario.get(fase, "")
    input_str = input_str.strip()
    if not input_str: return []
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
                if datos_usuario.get(key, "-") == resultado_real:
                    pts_partidos += 1
    puntos += pts_partidos
    desglose['Partidos'] = pts_partidos

    # --- 2. FASE DE GRUPOS ---
    pts_grupos = 0
    if "GRUPOS" in reales:
        for grupo, data_real in reales["GRUPOS"].items():
            if data_real.get("1", "-") != "-" and data_real.get("2", "-") != "-" and data_real.get("3", "-") != "-":
                real_top3 = [data_real["1"], data_real["2"], data_real["3"]]
                pts_reales = {data_real["1"]: data_real.get("pts_1", 0), data_real["2"]: data_real.get("pts_2", 0), data_real["3"]: data_real.get("pts_3", 0)}
                for i in posiciones:
                    campo_usuario = f"{grupo}_{i}"
                    u_equipo = datos_usuario.get(campo_usuario)
                    r_equipo = data_real[str(i)]
                    if u_equipo in real_top3:
                        pts_grupos += 10 
                        if u_equipo in pts_reales: pts_grupos += pts_reales[u_equipo]
                    if u_equipo == r_equipo: pts_grupos += 5
    puntos += pts_grupos
    desglose['Grupos'] = pts_grupos
    
    # --- 3. FASES FINALES ---
    pts_oct = 0; pts_cua = 0; pts_sem = 0; pts_ter = 0; pts_fin = 0
    
    u_oct = limpiar_prediccion_fase(datos_usuario, "Octavos")
    if "OCTAVOS" in reales:
        for eq in u_oct: 
            if eq in reales["OCTAVOS"]: pts_oct += 15
        
    u_cua = limpiar_prediccion_fase(datos_usuario, "Cuartos")
    if "CUARTOS" in reales:
        for eq in u_cua: 
            if eq in reales["CUARTOS"]: pts_cua += 20

    u_sem = limpiar_prediccion_fase(datos_usuario, "Semis")
    if "SEMIS" in reales:
        for eq in u_sem:
            if eq in reales["SEMIS"]: 
                pts_sem += 25
                camp = reales.get("CAMPEON","-"); sub = reales.get("SUBCAMPEON","-")
                if eq != camp and eq != sub and camp != "-": pts_ter += 30
                
    u_ter = datos_usuario.get("Tercero")
    if "TERCERO_GANADOR" in reales and u_ter == reales["TERCERO_GANADOR"]: pts_ter += 35
    
    u_cam = datos_usuario.get("Campeon"); u_sub = datos_usuario.get("Subcampeon")
    if "FINALISTAS" in reales:
        if u_cam in reales["FINALISTAS"]: pts_fin += 40
        if u_sub in reales["FINALISTAS"]: pts_fin += 40
    if "CAMPEON" in reales and u_cam == reales["CAMPEON"]: pts_fin += 50
    
    puntos += pts_oct + pts_cua + pts_sem + pts_ter + pts_fin
    
    desglose['Octavos']=pts_oct; desglose['Cuartos']=pts_cua; desglose['Semifinales']=pts_sem
    desglose['Tercer Puesto']=pts_ter; desglose['Final/Campeon']=pts_fin; desglose['TOTAL']=puntos
    return desglose

# ==========================================
# 4. CONEXIÓN A DATOS
# ==========================================
def obtener_datos_participantes():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
        creds_dict = json.loads(contenido_json_texto, strict=False)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open(NOMBRE_HOJA_GOOGLE).sheet1.get_all_records()
    except Exception as e:
        return None

def obtener_resultados_oficiales_admin():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
        creds_dict = json.loads(contenido_json_texto, strict=False)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        try:
            sheet = client.open(NOMBRE_HOJA_GOOGLE).worksheet("Resultados_Admin")
            json_texto = sheet.acell('A1').value
            return json.loads(json_texto) if json_texto else None
        except: return None
    except: return None

# ==========================================
# 5. ESTILOS Y FORMATO
# ==========================================

# Función para aplicar colores a la columna 'Participante'
def color_trend(val):
    if "(+" in val:
        return 'color: #00FF87; font-weight: bold;' # Verde Negrita
    elif "(-" in val:
        return 'color: #FF4B4B; font-weight: bold;' # Rojo Negrita
    else:
        return 'font-weight: bold;' # Negrita Normal

def asignar_medalla(posicion):
    if posicion == 1: return "🥇"
    if posicion == 2: return "🥈"
    if posicion == 3: return "🥉"
    if 4 <= posicion <= 6: return "📜"
    return str(posicion)

@st.cache_data(ttl=600)
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
            "Partidos": puntajes["Partidos"], # Agregada columna Partidos
            "Grupos": puntajes["Grupos"],
            "Octavos": puntajes["Octavos"],
            "Cuartos": puntajes["Cuartos"],
            "Semifinales": puntajes["Semifinales"],
            "3er Puesto": puntajes["Tercer Puesto"],
            "Final/Campeon": puntajes["Final/Campeon"],
        }
        tabla.append(fila)
        
    df = pd.DataFrame(tabla)
    
    if not df.empty:
        # 1. ORDENAR
        df['Playoffs_Desempate'] = df['Octavos'] + df['Cuartos'] + df['Semifinales'] + df['3er Puesto'] + df['Final/Campeon']
        df = df.sort_values(by=["TOTAL", "Grupos", "Playoffs_Desempate"], ascending=[False, False, False]).drop(columns=['Playoffs_Desempate']).reset_index(drop=True)
        
        # 2. CALCULAR TENDENCIA (Simulación por falta de histórico)
        # Nota: Aquí deberíamos leer el ranking de ayer. Como no existe, asumimos que 
        # Ranking Anterior = Ranking Actual.
        # Para probar colores, puedes descomentar la linea de abajo para "simular" movimientos aleatorios
        # import random; df['Prev_Rank'] = [i + 1 + random.randint(-1, 1) for i in df.index]
        
        df['Rank_Actual'] = df.index + 1
        df['Prev_Rank'] = df['Rank_Actual'] # Por ahora, neutro.
        
        df['Diff'] = df['Prev_Rank'] - df['Rank_Actual'] # Positivo es que mejoró (estaba 5, ahora 3 -> +2)
        
        # 3. FORMATO STRING PARTICIPANTE
        def format_name(row):
            nombre = row['Participante']
            diff = row['Diff']
            if diff > 0:
                return f"{nombre} (+{diff})"
            elif diff < 0:
                return f"{nombre} ({diff})"
            else:
                return nombre
                
        df['Participante'] = df.apply(format_name, axis=1)
        
        # 4. MEDALLAS
        df['Pos'] = df['Rank_Actual'].apply(asignar_medalla)
        
        # 5. REORDENAR COLUMNAS PARA VISUALIZACIÓN
        cols = ['Pos', 'Participante', 'TOTAL', 'Partidos', 'Grupos', 'Octavos', 'Cuartos', 'Semifinales', '3er Puesto', 'Final/Campeon']
        df = df[cols]
    
    ahora_arg = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
    fecha_act = ahora_arg.strftime("%d/%m/%Y %H:%M")
    
    return df, fecha_act

# ==========================================
# 6. APP PRINCIPAL
# ==========================================

st.title("🏆 RANKING MUNDIAL 2026")

resultados_nube = obtener_resultados_oficiales_admin()
RESULTADOS_REALES_ACTUALES = resultados_nube if resultados_nube else { "PARTIDOS": {}, "GRUPOS": {}, "OCTAVOS": [], "CUARTOS": [], "SEMIS": [], "TERCERO_GANADOR": "-", "FINALISTAS": [], "CAMPEON": "-", "SUBCAMPEON": "-" }

ranking_df, fecha = generar_ranking(RESULTADOS_REALES_ACTUALES)

if not ranking_df.empty:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"✅ Última Actualización: {fecha} (Hora ARG)")
    with col2:
        if st.button("🔄 Refrescar Tabla"):
            st.cache_data.clear()
            st.rerun()

    # PODIO DESTACADO
    if len(ranking_df) >= 3 and ranking_df.iloc[0]['TOTAL'] > 0:
        c1, c2, c3 = st.columns(3)
        # El 2do a la izquierda, 1ro al centro, 3ro a la derecha (estilo podio)
        with c2: st.metric("🥇 LÍDER", ranking_df.iloc[0]['Participante'].split('(')[0], f"{ranking_df.iloc[0]['TOTAL']} pts")
        with c1: st.metric("🥈 SEGUNDO", ranking_df.iloc[1]['Participante'].split('(')[0], f"{ranking_df.iloc[1]['TOTAL']} pts")
        with c3: st.metric("🥉 TERCERO", ranking_df.iloc[2]['Participante'].split('(')[0], f"{ranking_df.iloc[2]['TOTAL']} pts")

    st.markdown("---")
    
    # APLICAR ESTILOS DE PANDAS
    # Esto colorea la columna 'Participante' basado en el texto (+/-)
    styled_df = ranking_df.style.applymap(color_trend, subset=['Participante'])

    # MOSTRAR TABLA
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=800,
        column_config={
            "Pos": st.column_config.Column("Pos", width="small"),
            "Participante": st.column_config.Column("Participante", width="large"),
            "TOTAL": st.column_config.NumberColumn("🏆 TOTAL", format="%d"),
            "Partidos": st.column_config.NumberColumn("Partidos", format="%d"),
            "Grupos": st.column_config.NumberColumn("Grupos", format="%d"),
            "Octavos": st.column_config.NumberColumn("8vos", format="%d"),
            "Cuartos": st.column_config.NumberColumn("4tos", format="%d"),
            "Semifinales": st.column_config.NumberColumn("Semis", format="%d"),
            "3er Puesto": st.column_config.NumberColumn("3ro", format="%d"),
            "Final/Campeon": st.column_config.NumberColumn("Final", format="%d"),
        },
        hide_index=True # Ocultamos el índice numérico feo de pandas
    )

else:
    st.warning("⚠️ Esperando datos...")