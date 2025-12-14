import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ==========================================
# 1. CONFIGURACIÓN VISUAL
# ==========================================
st.set_page_config(page_title="🏆 Prode Mundial 2026: Ranking Oficial", layout="wide", page_icon="🥇")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #ffffff; }
    h1 {
        font-family: 'Arial Black', sans-serif;
        background: -webkit-linear-gradient(45deg, #CF00FF, #00FF87);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-transform: uppercase;
    }
    .stDataFrame { color: white; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DEFINICIONES DE LA LÓGICA (Necesarias para el cálculo)
# ==========================================
NOMBRE_HOJA_GOOGLE = "DB_Prode_2026"

# GRUPOS (Solo necesitamos el nombre para la función de cálculo)
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
# Lista de posiciones para el cálculo de grupos
POSICIONES_GRUPO = [1, 2, 3] 

# Función auxiliar para limpiar la entrada de las fases finales
def limpiar_prediccion_fase(datos_usuario, fase):
    input_str = datos_usuario.get(fase, "")
    input_str = input_str.strip()
    if not input_str:
        return []
    return [x.strip() for x in input_str.split(",") if x.strip()]

# La función de cálculo completa debe estar aquí (se asume que se trae de admin_prode.py)
# POR FAVOR, PEGA EL CÓDIGO DE TU FUNCIÓN COMPLETA 'calcular_puntaje_participante' AQUÍ
# (La omito aquí para no repetir el código que ya tienes)
# ...
# =========================================================================
# *** COPIAR Y PEGAR LA FUNCIÓN 'calcular_puntaje_participante' AQUÍ ***
# (Recomendación: Pega todo el bloque de la función, incluyendo sus variables,
#  para que este script sea autónomo y use la última lógica verificada.)
# =========================================================================
# ...

def obtener_datos():
    # Esta función debe ser idéntica a la de admin_prode para leer la DB
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
        creds_dict = json.loads(contenido_json_texto, strict=False)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(NOMBRE_HOJA_GOOGLE).sheet1
        return sheet.get_all_records()
    except Exception as e:
        st.error(f"❌ ERROR: No se pudo conectar a Google Sheets. ({e})")
        return None

# --- LA FUNCIÓN PRINCIPAL DE RANKING ---
@st.cache_data(ttl=600) # Recalcula la tabla cada 10 minutos
def generar_ranking(resultados_reales_dict):
    # 1. Obtener las predicciones de los participantes
    datos_usuarios = obtener_datos()
    
    if datos_usuarios is None:
        return pd.DataFrame() 

    tabla = []
    for usuario in datos_usuarios:
        # 2. Calcular el puntaje usando el motor completo
        puntajes = calcular_puntaje_participante(usuario, resultados_reales_dict)
        
        # 3. Crear la fila con el desglose completo
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
    
    # Aplicar Criterios de Desempate (Regla 3-j)
    df['Playoffs_Desempate'] = df['Octavos'] + df['Cuartos'] + df['Semifinales'] + df['3er Puesto'] + df['Final/Campeon']
    
    df = df.sort_values(
        by=["TOTAL", "Grupos", "Playoffs_Desempate"], 
        ascending=[False, False, False]
    ).drop(columns=['Playoffs_Desempate']).reset_index(drop=True)
    
    df.index += 1
    
    return df

# ==========================================
# 3. LECTURA DE RESULTADOS REALES (El desafío)
# ==========================================

# *** NOTA IMPORTANTE ***
# ESTA ES LA PARTE QUE DEBES ADAPTAR
# Para que esta App funcione, necesita saber cuáles son los resultados reales
# cargados por el Admin. Si el Admin NO guarda los resultados en Google Sheets,
# esta App no podrá leerlos.
# ASUMIREMOS que leerás un diccionario de resultados REALES desde un archivo
# o una celda fija de Google Sheets.

st.error("⚠️ ESTA ES UNA VERSIÓN DE PRUEBA: Falta la LECTURA DE RESULTADOS REALES. Por ahora, solo simulará ceros.")

# Diccionario vacío (SIMULACIÓN) - Reemplazar con la lectura real de la DB
RESULTADOS_REALES_VACIO = { 
    "PARTIDOS": {}, "GRUPOS": {}, "OCTAVOS": [], "CUARTOS": [], 
    "SEMIS": [], "TERCERO_EQUIPOS": [], "TERCERO_GANADOR": "-", 
    "FINALISTAS": [], "CAMPEON": "-", "SUBCAMPEON": "-"
}

# ==========================================
# 4. INTERFAZ Y EJECUCIÓN
# ==========================================

st.header("🏆 RANKING OFICIAL")
st.info("La tabla se actualiza cada 10 minutos automáticamente. La posición de desempate se basa en la Regla 3-j.")

if st.button("Actualizar Ranking Ahora ⚡"):
    with st.spinner("Calculando posiciones..."):
        # REEMPLAZAR RESULTADOS_REALES_VACIO con la fuente de datos REAL
        ranking_df = generar_ranking(RESULTADOS_REALES_VACIO)
        
        if not ranking_df.empty:
            st.dataframe(
                ranking_df,
                use_container_width=True,
                column_config={
                    "TOTAL": st.column_config.NumberColumn("🏆 TOTAL", format="%d"),
                    "Grupos": st.column_config.NumberColumn("Grupos", format="%d"),
                    "Octavos": st.column_config.NumberColumn("Octavos", format="%d"),
                    "Cuartos": st.column_config.NumberColumn("Cuartos", format="%d"),
                    "Semifinales": st.column_config.NumberColumn("Semis", format="%d"),
                    "3er Puesto": st.column_config.NumberColumn("3er Puesto", format="%d"),
                    "Final/Campeon": st.column_config.NumberColumn("Final/Camp.", format="%d"),
                },
                hide_index=False
            )
            st.subheader(f"🥇 LÍDER: {ranking_df.iloc[0]['Participante']} ({ranking_df.iloc[0]['TOTAL']} pts)")

        else:
            st.warning("Aún no hay participantes o la fuente de resultados reales está vacía.")