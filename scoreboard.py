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
    .stDataFrame { width: 100%; }
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
    """Trae participantes, resultados oficiales y ranking anterior en una sola llamada eficiente"""
    try:
        client = get_client()
        sh = client.open(NOMBRE_HOJA_GOOGLE)
        
        # 1. Participantes
        datos_p = sh.sheet1.get_all_records()
        
        # 2. Resultados Reales
        try:
            val_r = sh.worksheet("Resultados_Admin").acell('A1').value
            res_admin = json.loads(val_r) if val_r else {}
        except: res_admin = {}

        # 3. Ranking Anterior (Foto)
        try:
            val_h = sh.worksheet("Ranking_Anterior").acell('A1').value
            rank_ant = json.loads(val_h) if val_h else {}
        except: rank_ant = {}

        return datos_p, res_admin, rank_ant
    except Exception as e:
        return [], {}, {}

# ==========================================
# 4. ESTILOS Y FORMATO
# ==========================================
def color_trend(val):
    if "(+" in val: return 'color: #00FF87; font-weight: bold;' # Verde
    elif "(-" in val: return 'color: #FF4B4B; font-weight: bold;' # Rojo
    else: return 'font-weight: bold;'

def asignar_medalla(posicion):
    if posicion == 1: return "🥇"
    if posicion == 2: return "🥈"
    if posicion == 3: return "🥉"
    if 4 <= posicion <= 6: return "📜"
    return str(posicion)

def generar_ranking_df(datos_usuarios, resultados_reales, ranking_anterior):
    tabla = []
    for u in datos_usuarios:
        pts = calcular_puntaje_participante(u, resultados_reales)
        tabla.append({
            "Participante": u["Participante"], "TOTAL": pts["TOTAL"], "Partidos": pts["Partidos"],
            "Grupos": pts["Grupos"], "Octavos": pts["Octavos"], "Cuartos": pts["Cuartos"],
            "Semifinales": pts["Semifinales"], "3ro": pts["Tercer Puesto"], "Final": pts["Final/Campeon"]
        })
    df = pd.DataFrame(tabla)
    
    if not df.empty:
        # Ordenar (Regla 3-j)
        df['Sort'] = df['Octavos'] + df['Cuartos'] + df['Semifinales'] + df['3ro'] + df['Final']
        df = df.sort_values(by=["TOTAL", "Grupos", "Sort"], ascending=False).drop(columns=['Sort']).reset_index(drop=True)
        
        # Calcular posición actual
        df['Rank_Actual'] = df.index + 1
        
        # Comparar con Ranking Anterior
        def calc_diff(row):
            nombre = row['Participante']
            pos_actual = row['Rank_Actual']
            if nombre in ranking_anterior:
                pos_anterior = ranking_anterior[nombre]
                return pos_anterior - pos_actual # (+ es mejora)
            return 0

        df['Diff'] = df.apply(calc_diff, axis=1)

        # Formatear Nombre con Diff
        def format_name(row):
            n = row['Participante']; d = row['Diff']
            if d > 0: return f"{n} (+{d})"
            elif d < 0: return f"{n} ({d})"
            return n
            
        df['Participante'] = df.apply(format_name, axis=1)
        df['Pos'] = df['Rank_Actual'].apply(asignar_medalla)
        
        # Seleccionar columnas finales
        df = df[['Pos', 'Participante', 'TOTAL', 'Partidos', 'Grupos', 'Octavos', 'Cuartos', 'Semifinales', '3ro', 'Final']]
    
    return df

# ==========================================
# 5. APP PRINCIPAL
# ==========================================
st.title("🏆 RANKING MUNDIAL 2026")

datos_p, res_admin, rank_ant = obtener_todo()

if not res_admin: 
    res_admin = { "PARTIDOS": {}, "GRUPOS": {}, "OCTAVOS": [], "CUARTOS": [], "SEMIS": [], "TERCERO_GANADOR": "-", "FINALISTAS": [], "CAMPEON": "-", "SUBCAMPEON": "-" }

df = generar_ranking_df(datos_p, res_admin, rank_ant)
fecha = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).strftime("%d/%m %H:%M")

if not df.empty:
    c1, c2 = st.columns([3, 1])
    c1.success(f"✅ Última Actualización: {fecha} (Hora ARG)")
    if c2.button("🔄 Refrescar"): st.cache_data.clear(); st.rerun()

    if len(df)>=3 and df.iloc[0]['TOTAL'] > 0:
        c1, c2, c3 = st.columns(3)
        c2.metric("🥇 LÍDER", df.iloc[0]['Participante'].split('(')[0], f"{df.iloc[0]['TOTAL']}")
        c1.metric("🥈 SEGUNDO", df.iloc[1]['Participante'].split('(')[0], f"{df.iloc[1]['TOTAL']}")
        c3.metric("🥉 TERCERO", df.iloc[2]['Participante'].split('(')[0], f"{df.iloc[2]['TOTAL']}")

    st.markdown("---")
    st.dataframe(
        df.style.applymap(color_trend, subset=['Participante']),
        use_container_width=True, 
        height=800, 
        hide_index=True
    )
else:
    st.warning("⏳ Esperando datos...")