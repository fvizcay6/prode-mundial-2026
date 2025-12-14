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

# Función auxiliar para limpiar la entrada de las fases finales
def limpiar_prediccion_fase(datos_usuario, fase):
    """
    Obtiene la predicción de una fase final (Octavos, Cuartos, Semis)
    y la limpia para ser robusta:
    1. Quita espacios al inicio/fin.
    2. Convierte el string separado por comas en una lista.
    3. Elimina elementos vacíos resultantes (como [''] o elementos de solo espacios).
    """
    input_str = datos_usuario.get(fase, "")
    # Usa list comprehension para limpiar y filtrar elementos vacíos
    return [x.strip() for x in input_str.split(", ") if x.strip()]

def calcular_puntaje_participante(datos_usuario, reales):
    puntos = 0
    desglose = {}
    posiciones = [1, 2, 3] 

    # --- 1. RONDA PARTIDO X PARTIDO (Regla 2-j: 1 punto) ---
    pts_partidos = 0
    for key, resultado_real in reales["PARTIDOS"].items():
        if resultado_real != "-":
            pronostico = datos_usuario.get(key, "-")
            if pronostico == resultado_real:
                pts_partidos += 1
    puntos += pts_partidos
    desglose['Partidos'] = pts_partidos

    # --- 2. FASE DE GRUPOS (Reglas 1-a, 1-b, 1-c) ---
    pts_grupos = 0
    
    for grupo, data_real in reales["GRUPOS"].items():
        if data_real["1"] != "-" and data_real["2"] != "-" and data_real["3"] != "-":
            
            real_top3 = [data_real["1"], data_real["2"], data_real["3"]]
            puntos_reales = {
                data_real["1"]: data_real["pts_1"],
                data_real["2"]: data_real["pts_2"],
                data_real["3"]: data_real["pts_3"],
            }
            
            for i in posiciones:
                campo_usuario = f"{grupo}_{i}"
                u_equipo = datos_usuario.get(campo_usuario)
                r_equipo_en_posicion = data_real[str(i)]
                
                # Regla 1-a & 1-c: Acertar equipo clasificado + puntos reales obtenidos
                if u_equipo in real_top3:
                    pts_grupos += 10 # Regla 1-a: 10 Pts por equipo clasificado
                    if u_equipo in puntos_reales:
                        pts_grupos += puntos_reales[u_equipo] # Regla 1-c: Puntos que el equipo real hizo
                
                # Regla 1-b: Acertar posición exacta (5 pts extra)
                if u_equipo == r_equipo_en_posicion:
                    pts_grupos += 5

    puntos += pts_grupos
    desglose['Grupos'] = pts_grupos
    
    # --- 3. FASES FINALES (Desglose Detallado) ---
    
    # Inicializar contadores detallados
    pts_octavos = 0
    pts_cuartos = 0
    pts_semis_base = 0 
    pts_tercer_puesto = 0 
    pts_final_campeon = 0 
    
    # D: Octavos (15 pts) - USAMOS LIMPIEZA
    u_octavos = limpiar_prediccion_fase(datos_usuario, "Octavos")
    for eq in u_octavos:
        if eq in reales["OCTAVOS"]: pts_octavos += 15
        
    # E: Cuartos (20 pts) - USAMOS LIMPIEZA
    u_cuartos = limpiar_prediccion_fase(datos_usuario, "Cuartos")
    for eq in u_cuartos:
        if eq in reales["CUARTOS"]: pts_cuartos += 20

    # F: Semis (25 pts) + G: 3er Puesto (30 pts por jugar) - USAMOS LIMPIEZA
    u_semis = limpiar_prediccion_fase(datos_usuario, "Semis")
    for eq in u_semis:
        if eq in reales["SEMIS"]: 
            pts_semis_base += 25 # Regla 1-f: 25 Pts por semifinalista
            
            # Regla 1-g (30 Pts por jugar el 3er puesto):
            # Si el equipo fue semifinalista PERO NO fue Campeón ni Subcampeón
            if eq != reales["CAMPEON"] and eq != reales["SUBCAMPEON"] and reales["CAMPEON"] != "-":
                pts_tercer_puesto += 30 
                
    # Regla G: Acertar el 3er puesto (35 pts extra)
    u_tercero = datos_usuario.get("Tercero")
    if u_tercero == reales["TERCERO_GANADOR"]: 
        pts_tercer_puesto += 35 
    
    # H: Finalistas (40 pts) y I: Campeón (50 pts)
    u_campeon = datos_usuario.get("Campeon")
    u_sub = datos_usuario.get("Subcampeon")
    
    # Regla H: Finalistas
    if u_campeon in reales["FINALISTAS"]: pts_final_campeon += 40
    if u_sub in reales["FINALISTAS"]: pts_final_campeon += 40
    
    # Regla I: Campeón (Bonus)
    if u_campeon == reales["CAMPEON"]: pts_final_campeon += 50
    
    # Sumar todos los puntos
    pts_playoff_total = pts_octavos + pts_cuartos + pts_semis_base + pts_tercer_puesto + pts_final_campeon
    puntos += pts_playoff_total
    
    # Rellenar el desglose detallado
    desglose['Octavos'] = pts_octavos
    desglose['Cuartos'] = pts_cuartos
    desglose['Semifinales'] = pts_semis_base
    desglose['Tercer Puesto'] = pts_tercer_puesto
    desglose['Final/Campeon'] = pts_final_campeon
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
tercero_ganador_real = "-"
finalistas_reales = []
campeon_real = "-"
subcampeon_real = "-" 

# --- CARGA GRUPOS ---
for nombre_grupo, equipos in GRUPOS.items():
    codigo = nombre_grupo.split(" ")[1]
    with cols_pantalla[idx_col % 2]: 
        with st.expander(f"**RESULTADOS REALES:** {nombre_grupo}", expanded=False):
            st.markdown("##### Partidos (Regla 2-j: 1 Punto por acierto)")
            for i, (idx_L, idx_V) in enumerate(FIXTURE_INDICES):
                local, visita = equipos[idx_L], equipos[idx_V]
                
                radio_key = f"Real_Partido_{codigo}_{i+1}"
                
                col_btn, col_res = st.columns([1, 4])
                with col_btn:
                    res = st.radio(
                        label="", 
                        options=["-", "L", "E", "V"], 
                        horizontal=True, 
                        key=radio_key,
                    )
                with col_res:
                    st.caption(f"Resultado para **{local}** vs **{visita}**: L, E, V")
                
                partidos_reales[f"P_G{codigo}_{i+1}"] = res
            
            st.markdown("##### Clasificados y Puntos (Reglas 1-a, 1-b, 1-c)")
            
            # -- 1er Puesto --
            p1 = st.selectbox("🥇 1º REAL", ["-"]+equipos, key=f"Real_{codigo}_1", index=0)
            pts1 = st.number_input("Puntos REALES del 1º (Regla 1-c)", 0, 9, key=f"Real_{codigo}_pts1")
            
            # -- 2do Puesto --
            p2 = st.selectbox("🥈 2º REAL", ["-"]+equipos, key=f"Real_{codigo}_2", index=0)
            pts2 = st.number_input("Puntos REALES del 2º (Regla 1-c)", 0, 9, key=f"Real_{codigo}_pts2")
            
            # -- 3er Puesto (Nuevo) --
            p3 = st.selectbox("🥉 3º REAL (Clasifica o no)", ["-"]+equipos, key=f"Real_{codigo}_3", index=0)
            pts3 = st.number_input("Puntos REALES del 3º (Regla 1-c)", 0, 9, key=f"Real_{codigo}_pts3")
            
            grupos_reales[nombre_grupo] = {"1": p1, "2": p2, "3": p3, "pts_1": pts1, "pts_2": pts2, "pts_3": pts3}

    idx_col += 1

st.markdown("---")

# --- CARGA FASES FINALES ---
st.subheader("2. Carga de Fases Finales (Equipos Clasificados)")

octavos_reales = st.multiselect(
    "🏆 EQUIPOS REALES en Octavos de Final (16 equipos)", 
    TODOS_LOS_EQUIPOS, 
    max_selections=16,
    help="Solo los 16 equipos que jugaron realmente los Octavos. (Regla 1-d: 15 Pts)"
)

cuartos_reales = st.multiselect(
    "🏆 EQUIPOS REALES en Cuartos de Final (8 equipos)", 
    octavos_reales if len(octavos_reales) == 16 else TODOS_LOS_EQUIPOS,
    max_selections=8,
    help="Solo los 8 equipos que jugaron realmente los Cuartos. (Regla 1-e: 20 Pts)"
)

semis_reales = st.multiselect(
    "🏆 EQUIPOS REALES en Semifinales (4 equipos)", 
    cuartos_reales if len(cuartos_reales) == 8 else TODOS_LOS_EQUIPOS,
    max_selections=4,
    help="Solo los 4 equipos que llegaron a Semifinales. (Regla 1-f: 25 Pts)"
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
    tercero_ganador_real = st.selectbox("🥉 3ER PUESTO REAL (Regla 1-g: 35 Pts)", ["-"]+opc_podio, key="Real_3ro_Ganador")
    
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
    "CAMPEON": campeon_real,
    "SUBCAMPEON": subcampeon_real
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
        st.error(f"❌ ERROR: No se pudo conectar a Google Sheets. Revisa los Secrets o el nombre de la hoja. ({e})")
        return None

st.markdown("---")
st.header("TABLA DE POSICIONES")

if st.button("🔄 CALCULAR PUNTAJES Y ACTUALIZAR TABLA"):
    
    partidos_cargados = [v for k, v in RESULTADOS_REALES_DINAMICO["PARTIDOS"].items() if v != "-"]
    grupos_cargados = [v for g in RESULTADOS_REALES_DINAMICO["GRUPOS"].values() for k, v in g.items() if (k=="1" or k=="2" or k=="3") and v != "-"]
    
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
                    "Octavos": puntajes["Octavos"],
                    "Cuartos": puntajes["Cuartos"],
                    "Semifinales": puntajes["Semifinales"],
                    "3er Puesto": puntajes["Tercer Puesto"],
                    "Final/Campeon": puntajes["Final/Campeon"],
                }
                tabla.append(fila)
            
            # Crear DataFrame y Ordenar aplicando Reglas de Desempate (Regla 3-j)
            df = pd.DataFrame(tabla)
            
            df['Playoffs_Desempate'] = df['Octavos'] + df['Cuartos'] + df['Semifinales'] + df['3er Puesto'] + df['Final/Campeon']
            
            # Orden: 1. TOTAL, 2. Pts Grupos, 3. Pts Playoffs_Desempate
            df = df.sort_values(
                by=["TOTAL", "Grupos", "Playoffs_Desempate"], 
                ascending=[False, False, False]
            ).drop(columns=['Playoffs_Desempate']).reset_index(drop=True)
            
            df.index += 1
            
            st.success("✅ Cálculo completado (basado en resultados cargados).")
            
            # MOSTRAR TABLA
            st.dataframe(
                df, 
                use_container_width=True,
                column_config={
                    "TOTAL": st.column_config.NumberColumn("🏆 TOTAL", format="%d"),
                    "Partidos": st.column_config.NumberColumn("1 Pts x Partido", format="%d"),
                    "Grupos": st.column_config.NumberColumn("2 Grupos", format="%d"),
                    "Octavos": st.column_config.NumberColumn("3 Octavos", format="%d"),
                    "Cuartos": st.column_config.NumberColumn("4 Cuartos", format="%d"),
                    "Semifinales": st.column_config.NumberColumn("5 Semifinales", format="%d"),
                    "3er Puesto": st.column_config.NumberColumn("6 3er Puesto", format="%d"),
                    "Final/Campeon": st.column_config.NumberColumn("7 Final/Camp.", format="%d"),
                }
            )
            
            # PODIO
            if not df.empty:
                st.markdown("---")
                st.subheader(f"🥇 LÍDER ACTUAL: {df.iloc[0]['Participante']} ({df.iloc[0]['TOTAL']} pts)")