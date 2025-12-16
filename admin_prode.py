import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ==========================================
# 1. CONFIGURACIÓN Y SEGURIDAD
# ==========================================
st.set_page_config(page_title="Admin Prode 2026", layout="wide", page_icon="🔒")

def check_password():
    def password_entered():
        if st.session_state["username"] in st.secrets["passwords"] and \
           st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("### 🔒 Acceso Restringido")
        st.text_input("Usuario", key="username")
        st.text_input("Contraseña", type="password", key="password")
        st.button("Ingresar", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("### 🔒 Acceso Restringido")
        st.text_input("Usuario", key="username")
        st.text_input("Contraseña", type="password", key="password")
        st.button("Ingresar", on_click=password_entered)
        st.error("❌ Datos incorrectos")
        return False
    else:
        return True

if check_password():

    NOMBRE_HOJA_GOOGLE = "DB_Prode_2026"
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
    if st.button("Cerrar Sesión"):
        del st.session_state["password_correct"]
        st.rerun()

    # ==========================================
    # 2. CONEXIÓN Y GESTIÓN DB
    # ==========================================
    def get_client():
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
        creds_dict = json.loads(contenido_json_texto, strict=False)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)

    def cargar_memoria():
        try:
            client = get_client()
            sheet = client.open(NOMBRE_HOJA_GOOGLE).worksheet("Resultados_Admin")
            val = sheet.acell('A1').value
            return json.loads(val) if val else None
        except: return None

    def guardar_memoria(datos):
        """Guarda SOLO los resultados de partidos/fases"""
        try:
            client = get_client()
            sheet = client.open(NOMBRE_HOJA_GOOGLE).worksheet("Resultados_Admin")
            sheet.update_acell('A1', json.dumps(datos))
            return True
        except Exception as e:
            st.error(f"Error guardando resultados: {e}"); return False

    def guardar_cierre_dia(ranking_dict):
        """Guarda SOLO la foto del ranking (Historial)"""
        try:
            client = get_client()
            sheet = client.open(NOMBRE_HOJA_GOOGLE).worksheet("Ranking_Anterior")
            sheet.update_acell('A1', json.dumps(ranking_dict))
            return True
        except Exception as e:
            st.error(f"Error guardando historial: {e}"); return False

    def resetear_memoria():
        vacio = { "PARTIDOS": {}, "GRUPOS": {}, "OCTAVOS": [], "CUARTOS": [], "SEMIS": [], "TERCERO_GANADOR": "-", "FINALISTAS": [], "CAMPEON": "-", "SUBCAMPEON": "-"}
        return guardar_memoria(vacio)

    ESTADO_GUARDADO = cargar_memoria()
    if ESTADO_GUARDADO is None: ESTADO_GUARDADO = { "PARTIDOS": {}, "GRUPOS": {}, "OCTAVOS": [], "CUARTOS": [], "SEMIS": [], "TERCERO_GANADOR": "-", "FINALISTAS": [], "CAMPEON": "-", "SUBCAMPEON": "-"}

    # ==========================================
    # 3. CÁLCULO
    # ==========================================
    def limpiar_prediccion_fase(datos_usuario, fase):
        input_str = datos_usuario.get(fase, "")
        return [x.strip() for x in input_str.split(",") if x.strip()] if input_str.strip() else []

    def calcular_puntaje_participante(datos_usuario, reales):
        puntos = 0; desglose = {}
        # Partidos
        pts_partidos = 0
        if "PARTIDOS" in reales:
            for key, res_real in reales["PARTIDOS"].items():
                if res_real != "-" and datos_usuario.get(key, "-") == res_real: pts_partidos += 1
        puntos += pts_partidos; desglose['Partidos'] = pts_partidos
        # Grupos
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
        # Playoffs
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
    # 4. INTERFAZ
    # ==========================================
    st.header("👮‍♂️ PANEL DE CONTROL")

    def get_index_option(options, value):
        try: return options.index(value)
        except: return 0

    partidos_reales = {}; grupos_reales = {}
    st.subheader("1. Carga de Fases de Grupos")
    cols_pantalla = st.columns(2); idx_col = 0
    for nombre_grupo, equipos in GRUPOS.items():
        codigo = nombre_grupo.split(" ")[1]
        datos_grupo_saved = ESTADO_GUARDADO.get("GRUPOS", {}).get(nombre_grupo, {})
        with cols_pantalla[idx_col % 2]: 
            with st.expander(f"**{nombre_grupo}**", expanded=False):
                st.markdown("##### Partidos")
                for i, (idx_L, idx_V) in enumerate(FIXTURE_INDICES):
                    local, visita = equipos[idx_L], equipos[idx_V]
                    key_match = f"P_G{codigo}_{i+1}"
                    val_saved = ESTADO_GUARDADO.get("PARTIDOS", {}).get(key_match, "-")
                    opts = ["-", "L", "E", "V"]
                    partidos_reales[key_match] = st.radio(f"{local} vs {visita}", opts, horizontal=True, key=f"R_{key_match}", index=get_index_option(opts, val_saved))
                st.markdown("##### Clasificados")
                p1 = st.selectbox("🥇 1º", ["-"]+equipos, key=f"S1_{codigo}", index=get_index_option(["-"]+equipos, datos_grupo_saved.get("1", "-")))
                pts1 = st.number_input("Pts 1º", 0, 9, value=datos_grupo_saved.get("pts_1", 0), key=f"N1_{codigo}")
                p2 = st.selectbox("🥈 2º", ["-"]+equipos, key=f"S2_{codigo}", index=get_index_option(["-"]+equipos, datos_grupo_saved.get("2", "-")))
                pts2 = st.number_input("Pts 2º", 0, 9, value=datos_grupo_saved.get("pts_2", 0), key=f"N2_{codigo}")
                p3 = st.selectbox("🥉 3º", ["-"]+equipos, key=f"S3_{codigo}", index=get_index_option(["-"]+equipos, datos_grupo_saved.get("3", "-")))
                pts3 = st.number_input("Pts 3º", 0, 9, value=datos_grupo_saved.get("pts_3", 0), key=f"N3_{codigo}")
                grupos_reales[nombre_grupo] = {"1": p1, "2": p2, "3": p3, "pts_1": pts1, "pts_2": pts2, "pts_3": pts3}
        idx_col += 1

    st.markdown("---")
    st.subheader("2. Fases Finales")
    octavos_reales = st.multiselect("🏆 Octavos (16)", TODOS_LOS_EQUIPOS, default=ESTADO_GUARDADO.get("OCTAVOS", []), max_selections=16)
    opc_cuartos = octavos_reales if len(octavos_reales)==16 else TODOS_LOS_EQUIPOS
    cuartos_reales = st.multiselect("🏆 Cuartos (8)", opc_cuartos, default=[x for x in ESTADO_GUARDADO.get("CUARTOS", []) if x in opc_cuartos], max_selections=8)
    opc_semis = cuartos_reales if len(cuartos_reales)==8 else TODOS_LOS_EQUIPOS
    semis_reales = st.multiselect("🏆 Semis (4)", opc_semis, default=[x for x in ESTADO_GUARDADO.get("SEMIS", []) if x in opc_semis], max_selections=4)

    st.subheader("3. Podio")
    opc_podio = semis_reales if len(semis_reales) == 4 else TODOS_LOS_EQUIPOS
    col_cam, col_sub, col_ter = st.columns(3)
    with col_cam: campeon_real = st.selectbox("🥇 CAMPEÓN", ["-"]+opc_podio, index=get_index_option(["-"]+opc_podio, ESTADO_GUARDADO.get("CAMPEON", "-")), key="Sel_Camp")
    with col_sub: subcampeon_real = st.selectbox("🥈 SUBCAMPEÓN", ["-"]+opc_podio, index=get_index_option(["-"]+opc_podio, ESTADO_GUARDADO.get("SUBCAMPEON", "-")), key="Sel_Sub")
    with col_ter: tercero_ganador_real = st.selectbox("🥉 3ER PUESTO", ["-"]+opc_podio, index=get_index_option(["-"]+opc_podio, ESTADO_GUARDADO.get("TERCERO_GANADOR", "-")), key="Sel_Ter")

    RESULTADOS_REALES_DINAMICO = { "PARTIDOS": partidos_reales, "GRUPOS": grupos_reales, "OCTAVOS": octavos_reales, "CUARTOS": cuartos_reales, "SEMIS": semis_reales, "TERCERO_GANADOR": tercero_ganador_real, "FINALISTAS": [campeon_real, subcampeon_real] if campeon_real != "-" else [], "CAMPEON": campeon_real, "SUBCAMPEON": subcampeon_real }

    # ==========================================
    # 5. BOTONES DE ACCIÓN (LÓGICA CORREGIDA)
    # ==========================================
    st.markdown("---")
    st.header("ACCIONES")

    c1, c2, c3, c4 = st.columns(4)

    # BOTÓN 1: SOLO CALCULAR (Sin guardar nada)
    if c1.button("🔄 PREVISUALIZAR TABLA", use_container_width=True):
        client = get_client()
        datos = client.open(NOMBRE_HOJA_GOOGLE).sheet1.get_all_records()
        if datos:
            tabla = []
            for u in datos:
                pts = calcular_puntaje_participante(u, RESULTADOS_REALES_DINAMICO)
                tabla.append({"Participante": u["Participante"], "TOTAL": pts["TOTAL"], "Partidos": pts["Partidos"], "Grupos": pts["Grupos"], "8vos": pts["Octavos"], "4tos": pts["Cuartos"], "Semis": pts["Semifinales"], "Final": pts["Final/Campeon"]})
            df = pd.DataFrame(tabla)
            df['Sort'] = df['8vos'] + df['4tos'] + df['Semis'] + df['Final']
            df = df.sort_values(by=["TOTAL", "Grupos", "Sort"], ascending=False).drop(columns=['Sort']).reset_index(drop=True)
            df.index += 1
            st.dataframe(df, use_container_width=True)

    # BOTÓN 2: GUARDAR RESULTADOS (Genera cambios en el Scoreboard, NO TOCA EL HISTORIAL)
    if c2.button("💾 GUARDAR RESULTADOS", type="primary", use_container_width=True, help="Usa esto para actualizar los puntos en tiempo real."):
        if guardar_memoria(RESULTADOS_REALES_DINAMICO):
            st.success("✅ Resultados guardados. El Scoreboard ahora comparará los puntos nuevos con el Historial viejo.")
            st.rerun()

    # BOTÓN 3: CERRAR DÍA (Saca la FOTO para comparar MAÑANA)
    if c3.button("📸 CERRAR DÍA (Guardar Foto)", use_container_width=True, help="Usa esto SOLO al terminar la jornada."):
        with st.spinner("Guardando foto del ranking..."):
            client = get_client()
            datos = client.open(NOMBRE_HOJA_GOOGLE).sheet1.get_all_records()
            if datos:
                # 1. Calculamos tabla con los resultados ACTUALES
                tabla = []
                for u in datos:
                    pts = calcular_puntaje_participante(u, RESULTADOS_REALES_DINAMICO)
                    tabla.append({"Participante": u["Participante"], "TOTAL": pts["TOTAL"], "Grupos": pts["Grupos"], "Sort": pts["Octavos"]+pts["Cuartos"]+pts["Final/Campeon"]})
                
                # 2. Ordenamos
                df = pd.DataFrame(tabla).sort_values(by=["TOTAL", "Grupos", "Sort"], ascending=False).reset_index(drop=True)
                
                # 3. Guardamos {Participante: Posicion} en Ranking_Anterior
                ranking_dict = {}
                for idx, row in df.iterrows():
                    ranking_dict[row['Participante']] = idx + 1
                
                if guardar_cierre_dia(ranking_dict):
                    st.success("✅ Día cerrado. Las flechas del Scoreboard se han reseteado a (0).")
    
    # BOTÓN 4: RESET
    if c4.button("🗑️ RESETEAR", type="secondary", use_container_width=True):
        if resetear_memoria(): st.warning("⚠️ Borrado."); st.rerun()