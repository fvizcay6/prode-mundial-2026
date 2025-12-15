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

# GRUPOS
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
# 2. GESTIÓN DE MEMORIA (GOOGLE SHEETS)
# ==========================================

def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
    creds_dict = json.loads(contenido_json_texto, strict=False)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def cargar_memoria():
    """Lee la hoja de Google Sheets para recuperar el estado anterior."""
    try:
        client = get_client()
        sheet = client.open(NOMBRE_HOJA_GOOGLE).worksheet("Resultados_Admin")
        val = sheet.acell('A1').value
        if val:
            return json.loads(val)
    except Exception:
        # Si falla (hoja no existe o está vacía), retornamos estructura vacía
        return None

def guardar_memoria(datos):
    """Guarda el estado actual en Google Sheets."""
    try:
        client = get_client()
        try:
            sheet = client.open(NOMBRE_HOJA_GOOGLE).worksheet("Resultados_Admin")
        except gspread.exceptions.WorksheetNotFound:
            st.error("❌ No existe la hoja 'Resultados_Admin'. Créala en Google Sheets.")
            return False
        
        sheet.update_acell('A1', json.dumps(datos))
        return True
    except Exception as e:
        st.error(f"Error guardando: {e}")
        return False

def resetear_memoria():
    """Borra todo en la nube."""
    vacio = { 
        "PARTIDOS": {}, "GRUPOS": {}, "OCTAVOS": [], "CUARTOS": [], 
        "SEMIS": [], "TERCERO_EQUIPOS": [], "TERCERO_GANADOR": "-", 
        "FINALISTAS": [], "CAMPEON": "-", "SUBCAMPEON": "-"
    }
    return guardar_memoria(vacio)

# --- CARGAR ESTADO AL INICIO ---
# Esto es lo que permite que la App "recuerde" al recargar.
ESTADO_GUARDADO = cargar_memoria()

if ESTADO_GUARDADO is None:
    # Si no hay memoria, arrancamos limpio
    ESTADO_GUARDADO = { "PARTIDOS": {}, "GRUPOS": {}, "OCTAVOS": [], "CUARTOS": [], "SEMIS": [], "TERCERO_GANADOR": "-", "FINALISTAS": [], "CAMPEON": "-", "SUBCAMPEON": "-"}

# ==========================================
# 3. FUNCIONES DE CÁLCULO
# ==========================================
def limpiar_prediccion_fase(datos_usuario, fase):
    input_str = datos_usuario.get(fase, "")
    input_str = input_str.strip()
    if not input_str: return []
    return [x.strip() for x in input_str.split(",") if x.strip()]

def calcular_puntaje_participante(datos_usuario, reales):
    # ... (Misma lógica de cálculo que ya validamos)
    puntos = 0
    desglose = {}
    
    # 1. Partidos
    pts_partidos = 0
    if "PARTIDOS" in reales:
        for key, res_real in reales["PARTIDOS"].items():
            if res_real != "-":
                if datos_usuario.get(key, "-") == res_real: pts_partidos += 1
    puntos += pts_partidos
    desglose['Partidos'] = pts_partidos

    # 2. Grupos
    pts_grupos = 0
    if "GRUPOS" in reales:
        for grupo, data in reales["GRUPOS"].items():
            if data.get("1", "-") != "-" and data.get("2", "-") != "-" and data.get("3", "-") != "-":
                real_top3 = [data["1"], data["2"], data["3"]]
                pts_reales = {data["1"]: data.get("pts_1",0), data["2"]: data.get("pts_2",0), data["3"]: data.get("pts_3",0)}
                for i in [1,2,3]:
                    u_eq = datos_usuario.get(f"{grupo}_{i}")
                    r_eq = data[str(i)]
                    if u_eq in real_top3:
                        pts_grupos += 10
                        if u_eq in pts_reales: pts_grupos += pts_reales[u_eq]
                    if u_eq == r_eq: pts_grupos += 5
    puntos += pts_grupos
    desglose['Grupos'] = pts_grupos

    # 3. Playoffs
    pts_oct = 0; pts_cua = 0; pts_sem = 0; pts_ter = 0; pts_fin = 0
    
    # Octavos
    u_oct = limpiar_prediccion_fase(datos_usuario, "Octavos")
    if "OCTAVOS" in reales:
        for eq in u_oct: 
            if eq in reales["OCTAVOS"]: pts_oct += 15
    
    # Cuartos
    u_cua = limpiar_prediccion_fase(datos_usuario, "Cuartos")
    if "CUARTOS" in reales:
        for eq in u_cua: 
            if eq in reales["CUARTOS"]: pts_cua += 20
            
    # Semis
    u_sem = limpiar_prediccion_fase(datos_usuario, "Semis")
    if "SEMIS" in reales:
        for eq in u_sem:
            if eq in reales["SEMIS"]: 
                pts_sem += 25
                camp = reales.get("CAMPEON","-"); sub = reales.get("SUBCAMPEON","-")
                if eq != camp and eq != sub and camp != "-": pts_ter += 30
    
    # 3er Puesto Ganador
    u_ter = datos_usuario.get("Tercero")
    if "TERCERO_GANADOR" in reales and u_ter == reales["TERCERO_GANADOR"]: pts_ter += 35
    
    # Final y Campeon
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
# 4. INTERFAZ DE CARGA (AQUÍ ESTÁ LA MAGIA)
# ==========================================

# Helpers para encontrar el índice de la opción guardada
def get_index_option(options, value):
    try: return options.index(value)
    except: return 0

partidos_reales = {}
grupos_reales = {}

st.subheader("1. Carga de Fases de Grupos")
cols_pantalla = st.columns(2)
idx_col = 0

for nombre_grupo, equipos in GRUPOS.items():
    codigo = nombre_grupo.split(" ")[1]
    
    # Recuperamos lo guardado para este grupo
    datos_grupo_saved = ESTADO_GUARDADO.get("GRUPOS", {}).get(nombre_grupo, {})
    
    with cols_pantalla[idx_col % 2]: 
        with st.expander(f"**RESULTADOS: {nombre_grupo}**", expanded=False):
            st.markdown("##### Partidos")
            for i, (idx_L, idx_V) in enumerate(FIXTURE_INDICES):
                local, visita = equipos[idx_L], equipos[idx_V]
                key_match = f"P_G{codigo}_{i+1}"
                
                # MEMORIA: Obtenemos valor guardado para el 'index'
                val_saved = ESTADO_GUARDADO.get("PARTIDOS", {}).get(key_match, "-")
                opts = ["-", "L", "E", "V"]
                
                res = st.radio(
                    label=f"{local} vs {visita}", 
                    options=opts, 
                    horizontal=True, 
                    key=f"R_{key_match}", 
                    index=get_index_option(opts, val_saved) # <--- AQUÍ SE APLICA LA MEMORIA
                )
                partidos_reales[key_match] = res
            
            st.markdown("##### Clasificados")
            # 1ro
            idx_1 = get_index_option(["-"]+equipos, datos_grupo_saved.get("1", "-"))
            p1 = st.selectbox("🥇 1º REAL", ["-"]+equipos, key=f"S1_{codigo}", index=idx_1)
            pts1 = st.number_input("Pts 1º", 0, 9, value=datos_grupo_saved.get("pts_1", 0), key=f"N1_{codigo}")
            
            # 2do
            idx_2 = get_index_option(["-"]+equipos, datos_grupo_saved.get("2", "-"))
            p2 = st.selectbox("🥈 2º REAL", ["-"]+equipos, key=f"S2_{codigo}", index=idx_2)
            pts2 = st.number_input("Pts 2º", 0, 9, value=datos_grupo_saved.get("pts_2", 0), key=f"N2_{codigo}")
            
            # 3ro
            idx_3 = get_index_option(["-"]+equipos, datos_grupo_saved.get("3", "-"))
            p3 = st.selectbox("🥉 3º REAL", ["-"]+equipos, key=f"S3_{codigo}", index=idx_3)
            pts3 = st.number_input("Pts 3º", 0, 9, value=datos_grupo_saved.get("pts_3", 0), key=f"N3_{codigo}")
            
            grupos_reales[nombre_grupo] = {"1": p1, "2": p2, "3": p3, "pts_1": pts1, "pts_2": pts2, "pts_3": pts3}
    idx_col += 1

st.markdown("---")

st.subheader("2. Carga de Fases Finales")

# MEMORIA PARA MULTISELECTS: Usamos el argumento 'default'
saved_oct = ESTADO_GUARDADO.get("OCTAVOS", [])
saved_cua = ESTADO_GUARDADO.get("CUARTOS", [])
saved_sem = ESTADO_GUARDADO.get("SEMIS", [])

# Validamos que los equipos guardados sigan existiendo en las listas filtradas para evitar errores
octavos_reales = st.multiselect("🏆 Octavos (16)", TODOS_LOS_EQUIPOS, default=saved_oct, max_selections=16)

opc_cuartos = octavos_reales if len(octavos_reales)==16 else TODOS_LOS_EQUIPOS
valid_saved_cua = [x for x in saved_cua if x in opc_cuartos]
cuartos_reales = st.multiselect("🏆 Cuartos (8)", opc_cuartos, default=valid_saved_cua, max_selections=8)

opc_semis = cuartos_reales if len(cuartos_reales)==8 else TODOS_LOS_EQUIPOS
valid_saved_sem = [x for x in saved_sem if x in opc_semis]
semis_reales = st.multiselect("🏆 Semis (4)", opc_semis, default=valid_saved_sem, max_selections=4)

st.subheader("3. Podio Final")
opc_podio = semis_reales if len(semis_reales) == 4 else TODOS_LOS_EQUIPOS
col_cam, col_sub, col_ter = st.columns(3)

# MEMORIA PARA PODIO
idx_cam = get_index_option(["-"]+opc_podio, ESTADO_GUARDADO.get("CAMPEON", "-"))
with col_cam: campeon_real = st.selectbox("🥇 CAMPEÓN", ["-"]+opc_podio, index=idx_cam, key="Sel_Camp")

idx_sub = get_index_option(["-"]+opc_podio, ESTADO_GUARDADO.get("SUBCAMPEON", "-"))
with col_sub: subcampeon_real = st.selectbox("🥈 SUBCAMPEÓN", ["-"]+opc_podio, index=idx_sub, key="Sel_Sub")

idx_ter = get_index_option(["-"]+opc_podio, ESTADO_GUARDADO.get("TERCERO_GANADOR", "-"))
with col_ter: tercero_ganador_real = st.selectbox("🥉 3ER PUESTO (Ganador)", ["-"]+opc_podio, index=idx_ter, key="Sel_Ter")

# Diccionario con TODO lo que está en pantalla ahora mismo
RESULTADOS_REALES_DINAMICO = {
    "PARTIDOS": partidos_reales,
    "GRUPOS": grupos_reales,
    "OCTAVOS": octavos_reales,
    "CUARTOS": cuartos_reales,
    "SEMIS": semis_reales,
    "TERCERO_GANADOR": tercero_ganador_real,
    "FINALISTAS": [campeon_real, subcampeon_real] if campeon_real != "-" and subcampeon_real != "-" else [],
    "CAMPEON": campeon_real,
    "SUBCAMPEON": subcampeon_real
}

# ==========================================
# 5. BOTONES DE ACCIÓN
# ==========================================

st.markdown("---")
st.header("ACCIONES DE ADMINISTRADOR")

col1, col2, col3 = st.columns(3)

# 1. BOTÓN CALCULAR (Simulación rápida)
with col1:
    if st.button("🔄 SOLO CALCULAR (Ver Tabla)", use_container_width=True):
        client = get_client()
        datos = client.open(NOMBRE_HOJA_GOOGLE).sheet1.get_all_records()
        if datos:
            tabla = []
            for u in datos:
                pts = calcular_puntaje_participante(u, RESULTADOS_REALES_DINAMICO)
                tabla.append({"Participante": u["Participante"], "TOTAL": pts["TOTAL"]})
            df = pd.DataFrame(tabla).sort_values("TOTAL", ascending=False)
            st.dataframe(df.reset_index(drop=True), use_container_width=True)

# 2. BOTÓN GUARDAR (Esto fija la memoria)
with col2:
    if st.button("💾 GUARDAR RESULTADOS (Mantener)", type="primary", use_container_width=True):
        with st.spinner("Guardando configuración..."):
            if guardar_memoria(RESULTADOS_REALES_DINAMICO):
                st.success("✅ Resultados guardados. Si recargas la página, seguirán aquí.")
                st.rerun() # Recargamos para que se vea reflejado que está guardado

# 3. BOTÓN RESET (Esto borra la memoria)
with col3:
    if st.button("🗑️ RESETEAR TODO (Borrar)", type="secondary", use_container_width=True):
        if resetear_memoria():
            st.warning("⚠️ Se han borrado todos los resultados cargados.")
            st.rerun() # Recargamos para que todo vuelva a "-"