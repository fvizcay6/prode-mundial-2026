import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ==========================================
# 1. CONFIGURACIÓN Y DEFINICIONES
# ==========================================
st.set_page_config(page_title="Admin Prode 2026", layout="wide", page_icon="👮‍♂️")

NOMBRE_HOJA_GOOGLE = "DB_Prode_2026"

# GRUPOS (Reutilizados de la app principal para construir los selectores)
GRUPOS = {
    "GRUPO A": ["🇲🇽 MEXICO", "🇿🇦 SUDAFRICA", "🇰🇷 COREA DEL SUR", "🌍 REP. EUR (DIN/MACE)"],
    "GRUPO B": ["🇨🇦 CANADA", "🌍 REP. EUR (ITA/BOS)", "🇶🇦 QATAR", "🇨🇭 SUIZA"],
    "GRUPO C": ["🇧🇷 BRASIL", "🇲🇦 MARRUECOS", "🇭🇹 HAITI", "🏴󠁧󠁢󠁳󠁣󠁴󠁿 ESCOCIA"],
    "GRUPO D": ["🇺🇸 USA", "🇵🇾 PARAGUAY", "🇦🇺 AUSTRALIA", "🌍 REP. EUR (RUM/TUR)"],
    "GRUPO E": ["🇩🇪 ALEMANIA", "🇨🇼 CURAZAO", "🇨🇮 COSTA DE MARFIL", "🇪🇨 ECUADOR"],
    "GRUPO F": ["🇳🇱 HOLANDA", "🇯🇵 JAPON", "🌍 REP. EUR (SWE/UKR)", "🇹🇳 TUNEZ"],
    "GRUPO G": ["🇧🇪 BELGICA", "🇪🇬 EGIPTO", "🇮🇷 IRAN", "🇳🇿 NUEVA ZELANDA"],
    "GRUPO H": ["🇪🇸 ESPAÑA", "🇨🇻 CABO VERDE", "🇸🇦 ARABIA SAUDITA", "🇺🇾 URUGUAY"],
    "GRUPO I": ["🇫🇷 FRANCIA", "🇸🇳 SENEGAL", "🌍 REP. (BOL/IRAK)", "🇳🇴 NORUEGA"],
    "GRUPO J": ["🇦🇷 ARGENTINA", "🇩🇿 ARGELIA", "🇦🇹 AUSTRIA", "🇯🇴 JORDANIA"],
    "GRUPO K": ["🇵🇹 PORTUGAL", "🇯🇲 JAMAICA", "🇺🇿 UZBEKISTAN", "🇨🇴 COLOMBIA"],
    "GRUPO L": ["🏴󠁧󠁢󠁥󠁮󠁧󠁿 INGLATERRA", "🇭🇷 CROACIA", "🇬🇭 GHANA", "🇵🇦 PANAMA"],
}
TODOS_LOS_EQUIPOS = sorted([eq for lista in GRUPOS.values() for eq in lista])
FIXTURE_INDICES = [(0,1), (2,3), (0,2), (1,3), (0,3), (1,2)]

st.title("⚽ Administrador de Resultados Reales")
st.header("👮‍♂️ PANEL DE CONTROL Y PUNTUACIÓN")

# ==========================================
# 2. FUNCIÓN DE CÁLCULO (EL MOTOR DE PUNTOS)
# ==========================================
def calcular_puntaje_participante(datos_usuario, reales):
    puntos = 0
    desglose = {}

    # --- 1. RONDA PARTIDO X PARTIDO (Regla 2-j: 1 punto) ---
    pts_partidos = 0
    for key, resultado_real in reales["PARTIDOS"].items():
        if resultado_real != "-": # Solo cuenta si el resultado real fue cargado
            pronostico = datos_usuario.get(key, "-")
            if pronostico == resultado_real:
                pts_partidos += 1
    puntos += pts_partidos
    desglose['Partidos'] = pts_partidos

    # --- 2. FASE DE GRUPOS (Reglas 1-a, 1-b, 1-c) ---
    pts_grupos = 0
    for grupo, data_real in reales["GRUPOS"].items():
        if data_real["1"] != "-" and data_real["2"] != "-": # Solo calcula si el Top 2 real está cargado
            
            u_1 = datos_usuario.get(f"{grupo}_1")
            u_2 = datos_usuario.get(f"{grupo}_2")
            
            real_1 = data_real["1"]
            real_2 = data_real["2"]
            pts_reales_1 = data_real["pts_1"] 
            pts_reales_2 = data_real["pts_2"]
            clasificados_real = [real_1, real_2]
            
            # Regla A & C (1er puesto predicho)
            if u_1 in clasificados_real:
                pts_grupos += 10 # Regla A: Acertar equipo clasificado (10 Pts)
                # Regla C: Sumar puntos reales
                if u_1 == real_1: pts_grupos += pts_reales_1
                elif u_1 == real_2: pts_grupos += pts_reales_2
            
            # Regla A & C (2do puesto predicho)
            if u_2 in clasificados_real:
                pts_grupos += 10 # Regla A: Acertar equipo clasificado (10 Pts)
                # Regla C
                if u_2 == real_1: pts_grupos += pts_reales_1
                elif u_2 == real_2: pts_grupos += pts_reales_2

            # Regla B: Acertar posición exacta (5 pts extra)
            if u_1 == real_1: pts_grupos += 5
            if u_2 == real_2: pts_grupos += 5

    puntos += pts_grupos
    desglose['Grupos'] = pts_grupos

    # --- 3. FASES FINALES (Reglas 1-d a 1-i) ---
    pts_playoff = 0
    
    # Regla D: Octavos (15 pts)
    u_octavos = datos_usuario.get("Octavos", "").split(", ")
    for eq in u_octavos:
        if eq in reales["OCTAVOS"]: pts_playoff += 15
        
    # Regla E: Cuartos (20 pts)
    u_cuartos = datos_usuario.get("Cuartos", "").split(", ")
    for eq in u_cuartos:
        if eq in reales["CUARTOS"]: pts_playoff += 20

    # Regla F: Semis (25 pts)
    u_semis = datos_usuario.get("Semis", "").split(", ")
    for eq in u_semis:
        if eq in reales["SEMIS"]: pts_playoff += 25

    # Regla G: Tercer Puesto (30 pts por equipo + 35 pts por acierto)
    u_tercero = datos_usuario.get("Tercero")
    if u_tercero in reales["TERCERO_EQUIPOS"]: pts_playoff += 30 # Acertó uno de los dos equipos que jugaron el 3er puesto
    if u_tercero == reales["TERCERO_GANADOR"]: pts_playoff += 35 # Acertó el ganador exacto
    
    # Regla H: Finalistas (40 pts) y Regla I: Campeón (50 pts)
    u_campeon = datos_usuario.get("Campeon")
    u_sub = datos_usuario.get("Subcampeon")
    
    # Regla H: Finalistas
    if u_campeon in reales["FINALISTAS"]: pts_playoff += 40
    if u_sub in reales["FINALISTAS"]: pts_playoff += 40
    
    # Regla I: Campeón (Bonus)
    if u_campeon == reales["CAMPEON"]: pts_playoff += 50
    
    puntos += pts_playoff
    desglose['Playoffs'] = pts_playoff
    
    desglose['TOTAL'] = puntos
    return desglose

# ==========================================
# 3. INTERFAZ DE CARGA DE RESULTADOS REALES
# ==========================================

st.subheader("1. Carga de Fases de Grupos (Resultados Reales)")
st.caption("Utilice estos controles para ingresar los resultados reales del Mundial. El cálculo se hará basado en su entrada.")
cols_pantalla = st.columns(2)
idx_col = 0

# Diccionarios para almacenar los datos cargados dinámicamente
partidos_reales = {}
grupos_reales = {}
octavos_reales = []
cuartos_reales = []
semis_reales = []
tercero_equipos_reales = []
tercero_ganador_real = "-"
finalistas_reales = []
campeon_real = "-"

# --- CARGA GRUPOS ---
for nombre_grupo, equipos in GRUPOS.items():
    codigo = nombre_grupo.split(" ")[1]
    with cols_pantalla[idx_col % 2]: 
        with st.expander(f"**RESULTADOS REALES:** {nombre_grupo}", expanded=False):
            st.markdown("##### Partidos (Regla 2-j: 1 Punto por acierto)")
            for i, (idx_L, idx_V) in enumerate(FIXTURE_INDICES):
                local, visita = equipos[idx_L], equipos[idx_V]
                
                # Creamos la clave única
                radio_key = f"Real_Partido_{codigo}_{i+1}"
                
                col_btn, col_res = st.columns([1, 4])
                with col_btn:
                    res = st.radio(
                        label="", 
                        options=["-", "L", "E", "V"], 
                        horizontal=True, 
                        key=radio_key, # LA CLAVE ÚNICA CORREGIDA
                    )
                with col_res:
                    st.caption(f"Resultado para **{local}** vs **{visita}**: L, E, V")
                
                partidos_reales[f"P_G{codigo}_{i+1}"] = res
            
            st.markdown("##### Clasificados y Puntos (Reglas 1-a, 1-b, 1-c)")
            p1 = st.selectbox("🥇 1º REAL", ["-"]+equipos, key=f"Real_{codigo}_1", index=0)
            pts1 = st.number_input("Puntos REALES del 1º (Regla 1-c)", 0, 9, key=f"Real_{codigo}_pts1")
            
            p2 = st.selectbox("🥈 2º REAL", ["-"]+equipos, key=f"Real_{codigo}_2", index=0)
            pts2 = st.number_input("Puntos REALES del 2º (Regla 1-c)", 0, 9, key=f"Real_{codigo}_pts2")
            
            grupos_reales[nombre_grupo] = {"1": p1, "2": p2, "pts_1": pts1, "pts_2": pts2}

    idx_col += 1

st.markdown("---")

# --- CARGA FASES FINALES ---
st.subheader("2. Carga de Fases Finales (Equipos Clasificados)")

octavos_reales = st.multiselect(
    "🏆 EQUIPOS REALES en Octavos de Final (16 equipos)", 
    TODOS_LOS_EQUIPOS, 
    max_selections=16,
    help="Solo los equipos que jugaron realmente los Octavos. (Regla 1-d: 15 Pts)"
)

cuartos_reales = st.multiselect(
    "🏆 EQUIPOS REALES en Cuartos de Final (8 equipos)", 
    octavos_reales if len(octavos_reales) == 16 else TODOS_LOS_EQUIPOS,
    max_selections=8,
    help="Solo los equipos que jugaron realmente los Cuartos. (Regla 1-e: 20 Pts)"
)

semis_reales = st.multiselect(
    "🏆 EQUIPOS REALES en Semifinales (4 equipos)", 
    cuartos_reales if len(cuartos_reales) == 8 else TODOS_LOS_EQUIPOS,
    max_selections=4,
    help="Solo los equipos que llegaron a Semifinales. (Regla 1-f: 25 Pts)"
)

# --- CARGA PODIO ---
st.subheader("3. Podio Final (Resultados Reales)")
opc_podio = semis_reales if len(semis_reales) == 4 else TODOS_LOS_EQUIPOS

col_cam, col_sub, col_ter = st.columns(3)

with col_cam:
    campeon_real = st.selectbox("🥇 CAMPEÓN REAL (Regla 1-h/i)", ["-"]+opc_podio, key="Real_Campeon")

with col_sub:
    subcampeon_real = st.selectbox("🥈 SUBCAMPEÓN REAL (Regla 1-h)", ["-"]+opc_podio, key="Real_Sub")

with col_ter:
    tercero_ganador_real = st.selectbox("🥉 TERCER PUESTO REAL (Regla 1-g: 35 Pts)", ["-"]+opc_podio, key="Real_3ro_Ganador")
    
    # Lógica para determinar quiénes jugaron por el 3er puesto (los 4tos y 3ros)
    jugaron_tercero = [eq for eq in semis_reales if eq not in [campeon_real, subcampeon_real] and eq != "-"]
    tercero_equipos_reales = jugaron_tercero
            

# --- CREAR EL DICCIONARIO FINAL DE "LA VERDAD" ---
RESULTADOS_REALES_DINAMICO = {
    "PARTIDOS": partidos_reales,
    "GRUPOS": grupos_reales,
    "OCTAVOS": octavos_reales,
    "CUARTOS": cuartos_reales,
    "SEMIS": semis_reales,
    "TERCERO_EQUIPOS": tercero_equipos_reales, 
    "TERCERO_GANADOR": tercero_ganador_real,
    "FINALISTAS": [campeon_real, subcampeon_real] if campeon_real != "-" and subcampeon_real != "-" else [],
    "CAMPEON": campeon_real
}

# ==========================================
# 4. EJECUCIÓN DEL CÁLCULO
# ==========================================
def obtener_datos():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
        creds_dict = json.loads(contenido_json_texto, strict=False)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(NOMBRE_HOJA_GOOGLE).sheet1
        return sheet.get_all_records()
    except Exception as e:
        st.error(f"❌ ERROR: No se pudo conectar a Google Sheets. Revisa los Secrets. ({e})")
        return None

st.markdown("---")
st.header("TABLA DE POSICIONES")

if st.button("🔄 CALCULAR PUNTAJES Y ACTUALIZAR TABLA"):
    
    # Validar que al menos haya resultados cargados para evitar cálculos vacíos
    partidos_cargados = [v for k, v in RESULTADOS_REALES_DINAMICO["PARTIDOS"].items() if v != "-"]
    grupos_cargados = [v for k, v in RESULTADOS_REALES_DINAMICO["GRUPOS"].items() if v["1"] != "-"]
    
    if not partidos_cargados and not grupos_cargados and not RESULTADOS_REALES_DINAMICO["OCTAVOS"]:
         st.warning("⚠️ No ha cargado ningún resultado real. La tabla mostrará ceros.")

    with st.spinner("Descargando predicciones y calculando..."):
        datos_usuarios = obtener_datos()
        
        if datos_usuarios is not None:
            tabla = []
            
            for usuario in datos_usuarios:
                puntajes = calcular_puntaje_participante(usuario, RESULTADOS_REALES_DINAMICO)
                fila = {
                    "Participante": usuario["Participante"],
                    "TOTAL": puntajes["TOTAL"],
                    "Partidos": puntajes["Partidos"],
                    "Grupos": puntajes["Grupos"],
                    "Playoffs": puntajes["Playoffs"]
                }
                tabla.append(fila)
            
            # Crear DataFrame y Ordenar aplicando Reglas de Desempate (Regla 3-j)
            df = pd.DataFrame(tabla)
            
            # Orden: 1. TOTAL, 2. Pts Grupos, 3. Pts Playoffs
            df = df.sort_values(
                by=["TOTAL", "Grupos", "Playoffs"], 
                ascending=[False, False, False] # Queremos mayor a menor en todos
            ).reset_index(drop=True)
            
            df.index += 1
            
            st.success("✅ Cálculo completado (basado en resultados cargados).")
            
            # MOSTRAR TABLA
            st.dataframe(
                df, 
                use_container_width=True,
                column_config={
                    "TOTAL": st.column_config.NumberColumn("🏆 PUNTOS TOTALES", format="%d"),
                }
            )
            
            # PODIO
            if not df.empty:
                st.markdown("---")
                st.subheader(f"🥇 LÍDER ACTUAL: {df.iloc[0]['Participante']} ({df.iloc[0]['TOTAL']} pts)")