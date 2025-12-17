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
st.set_page_config(page_title="🏆 Ranking Mundial 2026", layout="wide", page_icon="🥇")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    h1 { font-family: 'Arial Black', sans-serif; background: -webkit-linear-gradient(45deg, #CF00FF, #00FF87); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-transform: uppercase; font-size: 3em; text-align: center; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }
    .stDataFrame { width: 100%; }
    .report-card { background-color: #1A1A1A; border: 1px solid #333; border-radius: 10px; padding: 15px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .report-title { color: #00FF87; font-size: 18px; font-weight: bold; margin-bottom: 5px; text-transform: uppercase; }
    .report-stat { font-size: 24px; font-weight: bold; color: white; }
    .report-desc { font-size: 14px; color: #aaa; }
    </style>
""", unsafe_allow_html=True)

NOMBRE_HOJA_GOOGLE = "DB_Prode_2026"

# ==========================================
# 2. MOTOR DE CÁLCULO
# ==========================================
def limpiar_prediccion_fase(datos_usuario, fase):
    input_str = datos_usuario.get(fase, "")
    return [x.strip() for x in input_str.split(",") if x.strip()] if input_str.strip() else []

def calcular_puntaje_participante(datos_usuario, reales):
    puntos = 0; desglose = {}
    
    # 1. Partidos
    pts_partidos = 0
    if "PARTIDOS" in reales:
        for key, res_real in reales["PARTIDOS"].items():
            if res_real != "-" and datos_usuario.get(key, "-") == res_real: pts_partidos += 1
    puntos += pts_partidos; desglose['Partidos'] = pts_partidos

    # 2. Grupos
    pts_grupos = 0
    if "GRUPOS" in reales:
        for grupo, data in reales["GRUPOS"].items():
            if data.get("1", "-") != "-" and data.get("2", "-") != "-" and data.get("3", "-") != "-":
                real_top3 = [data["1"], data["2"], data["3"]]
                pts_reales = {data["1"]: data.get("pts_1",0), data["2"]: data.get("pts_2",0), data["3"]: data.get("pts_3",0)}
                for i in [1,2,3]:
                    u_eq = datos_usuario.get(f"{grupo}_{i}"); r_eq = data[str(i)]
                    if u_eq in real_top3:
                        pts_grupos += 10 
                        if u_eq in pts_reales: pts_grupos += pts_reales[u_eq]
                    if u_eq == r_eq: pts_grupos += 5
    puntos += pts_grupos; desglose['Grupos'] = pts_grupos
    
    # 3. Fases Finales
    pts_oct=0; pts_cua=0; pts_sem=0; pts_ter=0; pts_fin=0
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
                if eq != reales.get("CAMPEON","-") and eq != reales.get("SUBCAMPEON","-") and reales.get("CAMPEON","-") != "-": pts_ter += 30
    u_ter = datos_usuario.get("Tercero")
    if "TERCERO_GANADOR" in reales and u_ter == reales["TERCERO_GANADOR"]: pts_ter += 35
    u_cam = datos_usuario.get("Campeon"); u_sub = datos_usuario.get("Subcampeon")
    if "FINALISTAS" in reales:
        if u_cam in reales["FINALISTAS"]: pts_fin += 40
        if u_sub in reales["FINALISTAS"]: pts_fin += 40
    if "CAMPEON" in reales and u_cam == reales["CAMPEON"]: pts_fin += 50
    
    puntos += pts_oct + pts_cua + pts_sem + pts_ter + pts_fin
    desglose.update({'Octavos':pts_oct, 'Cuartos':pts_cua, 'Semifinales':pts_sem, 'Tercer Puesto':pts_ter, 'Final/Campeon':pts_fin, 'TOTAL':puntos})
    return desglose

# ==========================================
# 3. CONEXIÓN A DATOS
# ==========================================
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    contenido = st.secrets["google_json"]["contenido_archivo"]
    return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(json.loads(contenido, strict=False), scope))

@st.cache_data(ttl=600)
def obtener_todo():
    try:
        client = get_client()
        sh = client.open(NOMBRE_HOJA_GOOGLE)
        datos_p = sh.sheet1.get_all_records()
        try:
            val_r = sh.worksheet("Resultados_Admin").acell('A1').value
            res_admin = json.loads(val_r) if val_r else {}
        except: res_admin = {}
        try:
            val_h = sh.worksheet("Ranking_Anterior").acell('A1').value
            rank_ant = json.loads(val_h) if val_h else {}
        except: rank_ant = {}
        return datos_p, res_admin, rank_ant
    except: return [], {}, {}

# --- Obtener todas las ligas (INCLUIDAS LAS OCULTAS/PREMIUM) ---
@st.cache_data(ttl=600)
def obtener_listado_ligas_existentes():
    try:
        client = get_client()
        sheet = client.open(NOMBRE_HOJA_GOOGLE).sheet1
        columna_ligas = sheet.col_values(8)
        
        ligas_unicas = set()
        for celda in columna_ligas[1:]:
            if celda:
                partes = celda.split(',')
                for p in partes:
                    clean = p.strip().upper()
                    if clean: ligas_unicas.add(clean)
        return sorted(list(ligas_unicas))
    except: return []

# ==========================================
# 4. FUNCIONES AUXILIARES
# ==========================================
def color_trend(val):
    if "(+" in val: return 'color: #00FF87; font-weight: bold;' 
    elif "(-" in val: return 'color: #FF4B4B; font-weight: bold;'
    else: return 'font-weight: bold;'

def asignar_medalla(posicion):
    if posicion == 1: return "🥇"
    if posicion == 2: return "🥈"
    if posicion == 3: return "🥉"
    if 4 <= posicion <= 6: return "📜"
    return str(posicion)

def generar_ranking_df(datos_usuarios, resultados_reales, ranking_anterior, filtro_liga=None):
    tabla = []
    
    # 1. Calculamos puntos
    for u in datos_usuarios:
        pts = calcular_puntaje_participante(u, resultados_reales)
        tabla.append({
            "Participante": u["Participante"], "TOTAL": pts["TOTAL"], "Partidos": pts["Partidos"],
            "Grupos": pts["Grupos"], "Octavos": pts["Octavos"], "Cuartos": pts["Cuartos"],
            "Semifinales": pts["Semifinales"], "3ro": pts["Tercer Puesto"], "Final": pts["Final/Campeon"],
            "Liga": str(u.get("Liga", "")).upper().strip() # Datos crudos
        })
    df = pd.DataFrame(tabla)
    
    if df.empty: return pd.DataFrame(), pd.DataFrame()

    # 2. FILTRO DE LIGA (Lógica Multi-Liga)
    if filtro_liga and filtro_liga != "TODAS":
        filtro_clean = filtro_liga.upper().strip()
        
        def pertenece_a_liga(row_liga):
            ligas_usuario = [l.strip() for l in row_liga.split(',')]
            return filtro_clean in ligas_usuario
            
        df = df[df['Liga'].apply(pertenece_a_liga)]
        
        if df.empty: return pd.DataFrame(), pd.DataFrame()

    # 3. Ordenar
    df['Sort'] = df['Octavos'] + df['Cuartos'] + df['Semifinales'] + df['3ro'] + df['Final']
    df = df.sort_values(by=["TOTAL", "Grupos", "Sort"], ascending=False).drop(columns=['Sort']).reset_index(drop=True)
    
    # 4. Calcular Ranking
    df['Rank_Actual'] = df.index + 1
    
    # 5. Diff (Solo calculamos diff si NO hay filtro activo)
    def calc_diff(row):
        if filtro_liga and filtro_liga != "TODAS": return 0 
        nombre = row['Participante']
        pos_actual = row['Rank_Actual']
        if nombre in ranking_anterior:
            return ranking_anterior[nombre] - pos_actual
        return 0

    df['Diff'] = df.apply(calc_diff, axis=1)
    
    df_analytics = df.copy()

    def format_name(row):
        n = row['Participante']; d = row['Diff']
        if d > 0: return f"{n} (+{d})"
        elif d < 0: return f"{n} ({d})"
        return n
        
    df['Participante'] = df.apply(format_name, axis=1)
    df['Pos'] = df['Rank_Actual'].apply(asignar_medalla)
    
    return df[['Pos', 'Participante', 'TOTAL', 'Partidos', 'Grupos', 'Octavos', 'Cuartos', 'Semifinales', '3ro', 'Final']], df_analytics

# ==========================================
# 5. REPORTE
# ==========================================
def mostrar_reporte_diario(df_analytics, es_filtrado):
    if df_analytics.empty or es_filtrado: return

    subidas = df_analytics[df_analytics['Diff'] > 0].sort_values('Diff', ascending=False)
    bajadas = df_analytics[df_analytics['Diff'] < 0].sort_values('Diff', ascending=True)

    if not subidas.empty or not bajadas.empty:
        with st.expander("📰 REPORTE DIARIO DE TENDENCIAS (General)", expanded=True):
            r1, r2, r3 = st.columns(3)
            with r1:
                if not subidas.empty:
                    st.markdown(f"<div class='report-card'><div class='report-title'>🚀 LA REMONTADA</div><div class='report-stat'>{subidas.iloc[0]['Participante']}</div><div class='report-desc'>+{subidas.iloc[0]['Diff']} puestos.</div></div>", unsafe_allow_html=True)
            with r2:
                if not bajadas.empty:
                     st.markdown(f"<div class='report-card'><div class='report-title'>📉 CAÍDA LIBRE</div><div class='report-stat'>{bajadas.iloc[0]['Participante']}</div><div class='report-desc'>Perdió {abs(bajadas.iloc[0]['Diff'])} puestos.</div></div>", unsafe_allow_html=True)
            with r3:
                st.markdown(f"<div class='report-card'><div class='report-title'>📊 MOVIMIENTOS</div><div class='report-desc'>🟢 {len(subidas)} Subieron<br>🔴 {len(bajadas)} Bajaron</div></div>", unsafe_allow_html=True)

# ==========================================
# 6. APP PRINCIPAL
# ==========================================
st.title("🏆 RANKING MUNDIAL 2026")

# --- SIDEBAR: BUSCADOR DE LIGAS CON SELECTBOX ---
with st.sidebar:
    st.header("🕵️ Filtrar por Liga")
    
    # 1. Traemos las ligas existentes (INCLUIDAS LAS OCULTAS/PREMIUM)
    opciones_ligas = ["TODAS"] + obtener_listado_ligas_existentes()
    
    # 2. Mostramos el Selectbox
    filtro_liga = st.selectbox("Selecciona una Liga:", opciones_ligas)
    
    if filtro_liga != "TODAS":
        st.caption(f"Viendo ranking exclusivo de: **{filtro_liga}**")
        if st.button("❌ Borrar Filtro"):
            st.rerun()

datos_p, res_admin, rank_ant = obtener_todo()
if not res_admin: res_admin = { "PARTIDOS": {}, "GRUPOS": {}, "OCTAVOS": [], "CUARTOS": [], "SEMIS": [], "TERCERO_GANADOR": "-", "FINALISTAS": [], "CAMPEON": "-", "SUBCAMPEON": "-" }

df_display, df_analytics = generar_ranking_df(datos_p, res_admin, rank_ant, filtro_liga)
fecha = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).strftime("%d/%m %H:%M")

if not df_display.empty:
    c1, c2 = st.columns([3, 1])
    titulo_tabla = f"Resultados: {filtro_liga}" if filtro_liga != "TODAS" else "Ranking General"
    c1.subheader(f"📊 {titulo_tabla}")
    c1.caption(f"Actualizado: {fecha}")
    if c2.button("🔄 Refrescar"): st.cache_data.clear(); st.rerun()

    if len(df_display)>=3 and df_display.iloc[0]['TOTAL'] > 0:
        c1, c2, c3 = st.columns(3)
        c2.metric("🥇 LÍDER", df_display.iloc[0]['Participante'].split('(')[0], f"{df_display.iloc[0]['TOTAL']}")
        c1.metric("🥈 SEGUNDO", df_display.iloc[1]['Participante'].split('(')[0], f"{df_display.iloc[1]['TOTAL']}")
        c3.metric("🥉 TERCERO", df_display.iloc[2]['Participante'].split('(')[0], f"{df_display.iloc[2]['TOTAL']}")
    
    st.markdown("---")
    mostrar_reporte_diario(df_analytics, filtro_liga != "TODAS")
    st.dataframe(df_display.style.applymap(color_trend, subset=['Participante']), use_container_width=True, height=800, hide_index=True)
else:
    if filtro_liga != "TODAS": st.warning(f"⚠️ No hay participantes en la liga '{filtro_liga}'.")
    else: st.warning("⏳ Esperando datos...")