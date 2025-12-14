import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ==========================================
# 1. CONFIGURACIÓN Y CONEXIÓN
# ==========================================
st.set_page_config(page_title="Admin Prode 2026", layout="wide", page_icon="👮‍♂️")
st.title("👮‍♂️ PANEL DE CONTROL Y PUNTUACIÓN")

NOMBRE_HOJA_GOOGLE = "DB_Prode_2026"

# --- CARGA DE RESULTADOS REALES (SIMULACIÓN) ---
# AQUI ES DONDE TÚ CARGARÁS LA "VERDAD" A MEDIDA QUE PASE EL MUNDIAL
# Por ahora, inventamos que estos son los resultados para probar el cálculo.
RESULTADOS_REALES = {
    # PARTE 1: PARTIDOS DE GRUPO (Regla 2-i: 1 punto)
    # Formato: "P_G[Grupo]_[Partido]": "Resultado" (L, E, V)
    "PARTIDOS": {
        "P_GA_1": "L", "P_GA_2": "E", # Grupo A
        "P_GB_1": "V", # Grupo B... y así con todos
    },
    
    # PARTE 2: CLASIFICADOS Y POSICIONES (Reglas 1-a, 1-b, 1-c)
    # Formato: [1ro, 2do, Puntos_1ro, Puntos_2do]
    # (Los puntos son para la regla C)
    "GRUPOS": {
        "GRUPO A": {"1": "🇲🇽 MEXICO", "2": "🇿🇦 SUDAFRICA", "pts_1": 7, "pts_2": 5},
        "GRUPO B": {"1": "🇨🇦 CANADA", "2": "🇨🇭 SUIZA", "pts_1": 9, "pts_2": 6},
        # ... agregar el resto ...
    },
    
    # PARTE 3: FASES FINALES (Reglas d, e, f, g, h, i)
    "OCTAVOS": ["🇲🇽 MEXICO", "🇿🇦 SUDAFRICA", "🇨🇦 CANADA", "🇨🇭 SUIZA", "🇧🇷 BRASIL"], # etc
    "CUARTOS": ["🇲🇽 MEXICO", "🇨🇦 CANADA", "🇧🇷 BRASIL"],
    "SEMIS": ["🇧🇷 BRASIL", "🇨🇦 CANADA"],
    "TERCERO_EQUIPOS": ["🇫🇷 FRANCIA", "🇪🇸 ESPAÑA"], # Los que juegan por el 3er puesto
    "TERCERO_GANADOR": "🇫🇷 FRANCIA",
    "FINALISTAS": ["🇧🇷 BRASIL", "🇦🇷 ARGENTINA"],
    "CAMPEON": "🇦🇷 ARGENTINA"
}

# ==========================================
# 2. FUNCIÓN DE CÁLCULO (EL MOTOR)
# ==========================================
def calcular_puntaje_participante(datos_usuario, reales):
    puntos = 0
    desglose = {} # Para saber de dónde salen los puntos

    # --- 1. RONDA PARTIDO X PARTIDO (Regla 2-i) ---
    pts_partidos = 0
    for key, resultado_real in reales["PARTIDOS"].items():
        pronostico = datos_usuario.get(key, "-")
        if pronostico == resultado_real:
            pts_partidos += 1
    puntos += pts_partidos
    desglose['Partidos'] = pts_partidos

    # --- 2. FASE DE GRUPOS (Reglas 1-a, 1-b, 1-c) ---
    pts_grupos = 0
    for grupo, data_real in reales["GRUPOS"].items():
        # Usuario predijo:
        u_1 = datos_usuario.get(f"{grupo}_1")
        u_2 = datos_usuario.get(f"{grupo}_2")
        
        real_1 = data_real["1"]
        real_2 = data_real["2"]
        pts_reales_1 = data_real["pts_1"] # Puntos reales que obtuvo el equipo
        pts_reales_2 = data_real["pts_2"]

        # Regla A: Acertar equipo clasificado (10 pts)
        # Verificamos si los equipos del usuario están en el Top 2 Real
        clasificados_real = [real_1, real_2]
        
        # Chequeamos el 1ro del usuario
        if u_1 in clasificados_real:
            pts_grupos += 10 # Regla A
            # Regla C: Sumar los puntos que hizo el equipo
            if u_1 == real_1: pts_grupos += pts_reales_1
            elif u_1 == real_2: pts_grupos += pts_reales_2
        
        # Chequeamos el 2do del usuario
        if u_2 in clasificados_real:
            pts_grupos += 10 # Regla A
            # Regla C
            if u_2 == real_1: pts_grupos += pts_reales_1
            elif u_2 == real_2: pts_grupos += pts_reales_2

        # Regla B: Acertar posición exacta (5 pts extra)
        if u_1 == real_1: pts_grupos += 5
        if u_2 == real_2: pts_grupos += 5

    puntos += pts_grupos
    desglose['Grupos'] = pts_grupos

    # --- 3. FASES FINALES ---
    pts_playoff = 0
    
    # Regla D: Octavos (15 pts por equipo)
    # El usuario guardó Octavos como un string separado por comas, hay que convertirlo a lista
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

    # Regla G: Tercer Puesto
    u_tercero = datos_usuario.get("Tercero")
    # 30 pts por acertar equipo en partido 3er puesto (difícil de validar sin lista especifica, asumimos si acertó el ganador del 3ro)
    if u_tercero in reales["TERCERO_EQUIPOS"]: pts_playoff += 30
    if u_tercero == reales["TERCERO_GANADOR"]: pts_playoff += 35

    # Regla H: Finalistas (40 pts) y Regla I: Campeón (50 pts)
    u_campeon = datos_usuario.get("Campeon")
    u_sub = datos_usuario.get("Subcampeon")
    
    # Finalistas
    if u_campeon in reales["FINALISTAS"]: pts_playoff += 40
    if u_sub in reales["FINALISTAS"]: pts_playoff += 40
    
    # Campeón (Bonus)
    if u_campeon == reales["CAMPEON"]: pts_playoff += 50
    
    puntos += pts_playoff
    desglose['Playoffs'] = pts_playoff
    
    desglose['TOTAL'] = puntos
    return desglose

# ==========================================
# 3. INTERFAZ Y LECTURA DE DATOS
# ==========================================
def obtener_datos():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
    creds_dict = json.loads(contenido_json_texto, strict=False)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(NOMBRE_HOJA_GOOGLE).sheet1
    return sheet.get_all_records()

if st.button("🔄 ACTUALIZAR TABLA DE POSICIONES"):
    with st.spinner("Descargando predicciones y calculando..."):
        try:
            datos_usuarios = obtener_datos()
            tabla = []
            
            for usuario in datos_usuarios:
                puntajes = calcular_puntaje_participante(usuario, RESULTADOS_REALES)
                fila = {
                    "Participante": usuario["Participante"],
                    "TOTAL": puntajes["TOTAL"],
                    "Partidos": puntajes["Partidos"],
                    "Grupos": puntajes["Grupos"],
                    "Playoffs": puntajes["Playoffs"]
                }
                tabla.append(fila)
            
            # Crear DataFrame y Ordenar
            df = pd.DataFrame(tabla)
            df = df.sort_values(by=["TOTAL", "Grupos", "Playoffs"], ascending=False).reset_index(drop=True)
            df.index += 1 # Para que arranque en puesto 1
            
            st.success("✅ Cálculo completado")
            
            # MOSTRAR TABLA
            st.dataframe(
                df, 
                use_container_width=True,
                column_config={
                    "TOTAL": st.column_config.NumberColumn("🏆 PUNTOS", format="%d"),
                }
            )
            
            # PODIO
            if not df.empty:
                st.markdown("### 🥇 LÍDER ACTUAL")
                st.header(f"{df.iloc[0]['Participante']} ({df.iloc[0]['TOTAL']} pts)")

        except Exception as e:
            st.error(f"Error: {e}")