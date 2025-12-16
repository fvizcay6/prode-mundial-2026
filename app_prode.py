import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import datetime
import pytz

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS (CSS)
# ==========================================
st.set_page_config(page_title="Prode Mundial 2026", layout="wide", page_icon="⚽")

# CSS PARA CORREGIR EL ERROR DE "TEXTO INVISIBLE" EN DESPLEGABLES
st.markdown("""
    <style>
    /* Forzar color negro en las opciones de los selectbox */
    div[data-baseweb="select"] > div {
        color: black !important;
    }
    li[role="option"] {
        color: black !important;
        background-color: white !important;
    }
    /* Asegurar que el contenedor del menú tenga fondo blanco */
    ul[role="listbox"] {
        background-color: white !important;
    }
    /* Estilo general de la app */
    .stApp { background-color: #0e1117; color: #ffffff; }
    h1 { color: #00FF87; }
    h2, h3 { color: #CF00FF; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DEFINICIÓN DE EQUIPOS Y GRUPOS
# ==========================================
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

# Lista completa de equipos ordenada para los desplegables de fases finales
TODOS_LOS_EQUIPOS = sorted([eq for lista in GRUPOS.values() for eq in lista])

# Índices para generar los partidos (fixture) dentro de cada grupo
# (0 vs 1), (2 vs 3), (0 vs 2), etc.
FIXTURE_INDICES = [(0,1), (2,3), (0,2), (1,3), (0,3), (1,2)]

# ==========================================
# 3. CONEXIÓN A GOOGLE SHEETS
# ==========================================
def guardar_en_google_sheets(datos):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Leemos las credenciales desde st.secrets
        contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
        creds_dict = json.loads(contenido_json_texto, strict=False)
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Nombre de tu archivo en Google Drive
        sheet = client.open("DB_Prode_2026").sheet1 
        
        # Convertimos el diccionario 'datos' en una lista ordenada para la fila
        # IMPORTANTE: El orden aquí debe coincidir con tus columnas en Sheets
        fila = [
            datos["Fecha"],
            datos["Participante"],
            datos["Email"],
            datos["WhatsApp"],  # <--- NUEVO CAMPO
            # ... Aquí se agregan dinámicamente el resto de las predicciones ...
        ]
        
        # Agregamos los valores de las predicciones al final de la fila
        # Excluimos las llaves de metadatos ya agregadas
        keys_meta = ["Fecha", "Participante", "Email", "WhatsApp"]
        for k, v in datos.items():
            if k not in keys_meta:
                fila.append(str(v)) # Convertimos a string por seguridad
                
        sheet.append_row(fila)
        return True
    except Exception as e:
        st.error(f"Error al guardar en Google Sheets: {e}")
        return False

# ==========================================
# 4. INTERFAZ DE USUARIO
# ==========================================

st.title("🏆 TU PRODE MUNDIAL 2026")
st.markdown("¡Completa tus pronósticos y participa por la gloria!")

# --- SECCIÓN A: DATOS DEL PARTICIPANTE ---
with st.container():
    st.subheader("📋 Datos de Inscripción")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        nombre = st.text_input("Nombre y Apellido", placeholder="Ej: Lionel Messi")
    with col2:
        email = st.text_input("Correo Electrónico", placeholder="Ej: leo@correo.com")
    with col3:
        whatsapp = st.text_input("WhatsApp (con cód. área)", placeholder="Ej: 11 5555 9999") # <--- NUEVO CAMPO

st.markdown("---")

# DICCIONARIO PRINCIPAL DONDE GUARDAREMOS TODO
predicciones = {}

# --- SECCIÓN B: FASE DE GRUPOS ---
st.header("1. FASE DE GRUPOS")
st.info("Predice: (L)ocal, (E)mpate, (V)isitante y los 3 clasificados de cada grupo.")

tabs = st.tabs(list(GRUPOS.keys()))

for i, (nombre_grupo, equipos) in enumerate(GRUPOS.items()):
    with tabs[i]:
        st.subheader(f"{nombre_grupo}")
        col_partidos, col_tabla = st.columns([1.5, 1])
        
        # B.1 Partidos del Grupo
        with col_partidos:
            st.markdown("##### ⚽ Partidos")
            codigo_grupo = nombre_grupo.split(" ")[1] # "A", "B", etc.
            
            for idx_p, (idx_L, idx_V) in enumerate(FIXTURE_INDICES):
                local = equipos[idx_L]
                visita = equipos[idx_V]
                
                # ID único para cada partido: Ej "P_GA_1" (Partido Grupo A nro 1)
                key_partido = f"P_G{codigo_grupo}_{idx_p+1}"
                
                predicciones[key_partido] = st.radio(
                    f"{local} vs {visita}",
                    options=["L", "E", "V"],
                    horizontal=True,
                    key=key_partido
                )
        
        # B.2 Clasificados del Grupo
        with col_tabla:
            st.markdown("##### 📊 Clasificados")
            # Selectores para 1ro, 2do y 3ro
            # Usamos una lista con una opción vacía al principio
            opciones_clasificados = ["Seleccionar..."] + equipos
            
            p1 = st.selectbox(f"🥇 1er Lugar {nombre_grupo}", opciones_clasificados, key=f"G{codigo_grupo}_1")
            p2 = st.selectbox(f"🥈 2do Lugar {nombre_grupo}", opciones_clasificados, key=f"G{codigo_grupo}_2")
            p3 = st.selectbox(f"🥉 3er Lugar {nombre_grupo}", opciones_clasificados, key=f"G{codigo_grupo}_3")
            
            predicciones[f"{nombre_grupo}_1"] = p1
            predicciones[f"{nombre_grupo}_2"] = p2
            predicciones[f"{nombre_grupo}_3"] = p3

st.markdown("---")

# --- SECCIÓN C: FASES FINALES (MULTISELECCION) ---
st.header("2. FASES FINALES")
st.warning("⚠️ Importante: Selecciona los equipos que crees que llegarán a cada instancia.")

col_oct, col_cuar = st.columns(2)

with col_oct:
    st.subheader("🏆 Octavos de Final")
    octavos = st.multiselect(
        "Elige 16 equipos que pasan a Octavos:",
        TODOS_LOS_EQUIPOS,
        max_selections=16
    )
    # Guardamos como string separado por comas
    predicciones["Octavos"] = ", ".join(octavos)

with col_cuar:
    st.subheader("🏆 Cuartos de Final")
    # Filtramos para que solo pueda elegir de los que puso en octavos (opcional, pero mejor UX)
    opciones_cuartos = octavos if len(octavos) > 0 else TODOS_LOS_EQUIPOS
    cuartos = st.multiselect(
        "Elige 8 equipos que pasan a Cuartos:",
        opciones_cuartos,
        max_selections=8
    )
    predicciones["Cuartos"] = ", ".join(cuartos)

col_semi, col_final = st.columns(2)

with col_semi:
    st.subheader("🏆 Semifinales")
    opciones_semis = cuartos if len(cuartos) > 0 else TODOS_LOS_EQUIPOS
    semis = st.multiselect(
        "Elige 4 equipos Semifinalistas:",
        opciones_semis,
        max_selections=4
    )
    predicciones["Semis"] = ", ".join(semis)

with col_final:
    st.subheader("🥇 PODIO FINAL")
    # Solo permitimos elegir campeón entre los semifinalistas seleccionados
    opciones_podio = semis if len(semis) > 0 else TODOS_LOS_EQUIPOS
    
    campeon = st.selectbox("🏆 CAMPEÓN DEL MUNDO", ["-"] + opciones_podio)
    subcampeon = st.selectbox("🥈 Subcampeón", ["-"] + opciones_podio)
    tercero = st.selectbox("🥉 Tercer Puesto", ["-"] + opciones_podio)
    
    predicciones["Campeon"] = campeon
    predicciones["Subcampeon"] = subcampeon
    predicciones["Tercero"] = tercero

st.markdown("---")

# --- SECCIÓN D: ENVÍO ---
st.subheader("🚀 Enviar Pronóstico")

if st.button("CONFIRMAR Y ENVIAR PRODE", type="primary", use_container_width=True):
    # Validaciones básicas
    if not nombre or not email or not whatsapp:
        st.error("❌ Por favor completa tu Nombre, Email y WhatsApp.")
    elif len(octavos) != 16:
        st.error(f"❌ Debes seleccionar exactamente 16 equipos en Octavos (llevas {len(octavos)}).")
    elif len(cuartos) != 8:
        st.error(f"❌ Debes seleccionar exactamente 8 equipos en Cuartos (llevas {len(cuartos)}).")
    elif len(semis) != 4:
        st.error(f"❌ Debes seleccionar exactamente 4 equipos en Semifinales (llevas {len(semis)}).")
    elif campeon == "-" or subcampeon == "-" or tercero == "-":
        st.error("❌ Debes definir el Podio completo (Campeón, Sub y Tercero).")
    elif campeon == subcampeon or campeon == tercero or subcampeon == tercero:
        st.error("❌ No puedes repetir el mismo equipo en el Podio.")
    else:
        # Preparamos el paquete de datos
        ahora_arg = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
        
        datos_finales = {
            "Fecha": ahora_arg.strftime("%d/%m/%Y %H:%M:%S"),
            "Participante": nombre,
            "Email": email,
            "WhatsApp": whatsapp, # <--- Se agrega al paquete
            **predicciones
        }
        
        with st.spinner("Guardando tu prode... ⏳"):
            if guardar_en_google_sheets(datos_finales):
                st.balloons()
                st.success(f"✅ ¡Excelente {nombre}! Tu prode ha sido registrado exitosamente.")
                st.info("Te hemos enviado una copia a tu correo (Simulado). ¡Mucha suerte!")