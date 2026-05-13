import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json
import time
import pytz # <--- NECESARIO PARA LA HORA ARGENTINA

# ==========================================
# ⚙️ CONFIGURACIÓN GENERAL (EDITAR AQUÍ)
# ==========================================
# FECHA TOPE PARA INSCRIBIRSE (Formato: AAAA-MM-DD HH:MM)
# Hora de Argentina
FECHA_LIMITE = "2026-06-10 23:59" 

# LIGAS OCULTAS (No aparecen en el menú)
LIGAS_OCULTAS = ["LIGA PREMIUM", "VIP", "ADMINISTRACION"]

# ==========================================
# 1. CONFIGURACIÓN VISUAL Y CSS
# ==========================================
st.set_page_config(page_title="Prode Mundial 2026", layout="wide", page_icon="🏆")

st.markdown("""
    <style>
    div[data-baseweb="select"] > div { color: black !important; }
    li[role="option"] { color: black !important; background-color: white !important; }
    ul[role="listbox"] { background-color: white !important; }
    .stApp { background-color: #000000; color: #ffffff; }
    p, label, .stMarkdown, .stCaption, .stCheckbox, li { color: #ffffff !important; font-family: 'Helvetica Neue', sans-serif; }
    h1, h2, h3 { font-family: 'Arial Black', sans-serif; background: -webkit-linear-gradient(45deg, #CF00FF, #00FF87); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-transform: uppercase; margin-bottom: 0px; }
    div[role="radiogroup"] { display: flex; justify-content: center !important; width: 100% !important; gap: 15px; margin-bottom: 10px; margin-left: auto !important; margin-right: auto !important; }
    div[role="radiogroup"] label { background-color: #1a1a1a; border: 1px solid #444; padding: 5px 20px; border-radius: 20px; transition: all 0.2s; display: flex; align-items: center; justify-content: center; min-width: 60px; cursor: pointer; }
    div[role="radiogroup"] label:hover { border-color: #00FF87; background-color: #222; }
    div[role="radiogroup"] label p { font-size: 16px !important; font-weight: bold; margin-bottom: 0px !important; padding-left: 5px; }
    .match-title { text-align: center; font-weight: bold; font-size: 15px; margin-bottom: 5px; color: #ddd; margin-top: 15px; }
    div.stButton > button { background: linear-gradient(90deg, #00C853 0%, #B2FF59 100%); color: black; font-weight: 800; border: none; padding: 15px 20px; font-size: 18px; text-transform: uppercase; width: 100%; border-radius: 8px; margin-top: 20px; }
    .stTextInput input, .stNumberInput input { background-color: #222; color: white; border: 1px solid #555; border-radius: 5px; }
    .stAlert { background-color: #222; color: white; border: 1px solid #555; }
    strong { color: #00FF87; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. VALIDACIÓN DE FECHA LÍMITE
# ==========================================
def verificar_fecha_limite():
    tz_ar = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz_ar)
    
    # Convertimos el string de config a objeto fecha con zona horaria
    fecha_dt = datetime.strptime(FECHA_LIMITE, "%Y-%m-%d %H:%M")
    limite = tz_ar.localize(fecha_dt)
    
    if ahora > limite:
        return False, limite.strftime("%d/%m/%Y a las %H:%M hs")
    return True, limite.strftime("%d/%m/%Y a las %H:%M hs")

esta_habilitado, texto_limite = verificar_fecha_limite()

with st.sidebar:
    if os.path.exists("logo.jpg"): st.image("logo.jpg", use_container_width=True)
    elif os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.markdown("---")
    st.markdown("### 🎵 AMBIENTACIÓN")
    st.components.v1.iframe("https://www.youtube.com/embed/kyXRhggUmG8", height=150)
    
    if esta_habilitado:
        if st.button("🧹 Empezar de Cero"):
            st.session_state.clear()
            st.cache_data.clear()
            st.rerun()

c_logo, c_tit = st.columns([1, 5])
with c_logo:
    if os.path.exists("logo.jpg"): st.image("logo.jpg", use_container_width=True)
    elif os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
with c_tit:
    st.title("FIFA WORLD CUP 2026")
    st.markdown("### OFFICIAL PREDICTION GAME")

# ==========================================
# ⛔ BLOQUEO SI VENCIÓ LA FECHA
# ==========================================
if not esta_habilitado:
    st.error(f"⛔ **INSCRIPCIONES CERRADAS**")
    st.warning(f"El tiempo límite para cargar tu pronóstico finalizó el {texto_limite}.")
    st.info("¡Gracias a todos por participar! Ya puedes consultar los resultados en el Ranking.https://appe-mundial-2026-wgkggumkwsthcrnsqnepcn.streamlit.app/")
    st.stop() # DETIENE LA EJECUCIÓN AQUÍ

# ==========================================
# ... CONTINÚA EL CÓDIGO NORMAL ...
# ==========================================

NOMBRE_HOJA_GOOGLE = "DB_Prode_2026"
GRUPOS = {
        "GRUPO A": ["🇲🇽 MEXICO", "🇿🇦 SUDAFRICA", "🇰🇷 COREA DEL SUR", "🇨🇿 REP. CHECA"],
        "GRUPO B": ["🇨🇦 CANADA", "🇧🇦 BOSNIA", "🇶🇦 QATAR", "🇨🇭 SUIZA"],
        "GRUPO C": ["🇧🇷 BRASIL", "🇲🇦 MARRUECOS", "🇭🇹 HAITI", "🏴󠁧󠁢󠁳󠁣󠁴󠁿 ESCOCIA"],
        "GRUPO D": ["🇺🇸 USA", "🇵🇾 PARAGUAY", "🇦🇺 AUSTRALIA", "🇹🇷 TURQUIA"],
        "GRUPO E": ["🇩🇪 ALEMANIA", "🇨🇼 CURAZAO", "🇨🇮 COSTA DE MARFIL", "🇪🇨 ECUADOR"],
        "GRUPO F": ["🇳🇱 HOLANDA", "🇯🇵 JAPON", "🇸🇪 SUECIA", "🇹🇳 TUNEZ"],
        "GRUPO G": ["🇧🇪 BELGICA", "🇪🇬 EGIPTO", "🇮🇷 IRAN", "🇳🇿 NUEVA ZELANDA"],
        "GRUPO H": ["🇪🇸 ESPAÑA", "🇨🇻 CABO VERDE", "🇸🇦 ARABIA SAUDITA", "🇺🇾 URUGUAY"],
        "GRUPO I": ["🇫🇷 FRANCIA", "🇸🇳 SENEGAL", "🇮🇶 IRAK", "🇳🇴 NORUEGA"],
        "GRUPO J": ["🇦🇷 ARGENTINA", "🇩🇿 ARGELIA", "🇦🇹 AUSTRIA", "🇯🇴 JORDANIA"],
        "GRUPO K": ["🇵🇹 PORTUGAL", "🇯🇲 JAMAICA", "🇺🇿 UZBEKISTAN", "🇨🇴 COLOMBIA"],
        "GRUPO L": ["🏴󠁧󠁢󠁥󠁮󠁧󠁿 INGLATERRA", "🇭🇷 CROACIA", "🇬🇭 GHANA", "🇵🇦 PANAMA"],
    }
TODOS_LOS_EQUIPOS = sorted([eq for lista in GRUPOS.values() for eq in lista])
FIXTURE_INDICES = [(0,1), (2,3), (0,2), (1,3), (0,3), (1,2)]

if 'paso_actual' not in st.session_state:
    st.session_state.paso_actual = 1
if 'datos_usuario' not in st.session_state:
    st.session_state.datos_usuario = {}
if 'equipos_clasificados_usuario' not in st.session_state:
    st.session_state.equipos_clasificados_usuario = []

def obtener_client_gs():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    contenido = st.secrets["google_json"]["contenido_archivo"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(contenido, strict=False), scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=60) 
def traer_datos_validacion():
    try:
        client = obtener_client_gs()
        sheet = client.open(NOMBRE_HOJA_GOOGLE).sheet1
        datos = sheet.get_all_values()
        emails = [fila[2] for fila in datos[1:] if len(fila) > 2]
        dnis = [fila[3] for fila in datos[1:] if len(fila) > 3]
        ligas_raw = [fila[7] for fila in datos[1:] if len(fila) > 7]
        return emails, dnis, ligas_raw
    except Exception as e:
        st.error(f"Error conectando con DB: {e}")
        return [], [], []

def obtener_listado_ligas_existentes():
    _, _, ligas_columna = traer_datos_validacion()
    ligas_unicas = set()
    for celda in ligas_columna:
        if celda:
            partes = celda.split(',')
            for p in partes:
                clean = p.strip().upper()
                if clean and clean not in LIGAS_OCULTAS:
                    ligas_unicas.add(clean)
    return sorted(list(ligas_unicas))

def enviar_correo_confirmacion(datos):
    try:
        email_origen = st.secrets["email_credentials"]["EMAIL_ORIGEN"]
        password_app = st.secrets["email_credentials"]["PASSWORD_APP"]
    except: return False
    destinatario = datos["Email"]
    asunto = f"🏆 Ticket Oficial Mundial 2026 - {datos['Participante']}"
    html_partidos = ""
    for nombre_grupo, equipos in GRUPOS.items():
        codigo = nombre_grupo.split(" ")[1]
        p1 = datos.get(f"{nombre_grupo}_1", "-"); p2 = datos.get(f"{nombre_grupo}_2", "-"); p3 = datos.get(f"{nombre_grupo}_3", "-")
        html_partidos += f"<div style='margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom:5px;'><b>{nombre_grupo}:</b><br>"
        for i, (idx_L, idx_V) in enumerate(FIXTURE_INDICES):
            local, visita = equipos[idx_L], equipos[idx_V]
            eleccion = datos.get(f"P_G{codigo}_{i+1}", "-")
            res_txt = "EMPATE" if eleccion == "E" else (local if eleccion == "L" else visita)
            html_partidos += f"<span style='font-size: 12px;'>• {local} vs {visita} 👉 <b>{res_txt}</b></span><br>"
        html_partidos += f"<br><span style='font-size: 12px; color: #444;'><i>Clasificados: 1. {p1} | 2. {p2} | 3. {p3}</i></span></div>"
    lista_octavos = "".join([f"<div style='margin-left:10px;'>- {eq}</div>" for eq in datos['Octavos']])
    lista_cuartos = "".join([f"<div style='margin-left:10px;'>- {eq}</div>" for eq in datos['Cuartos']])
    lista_semis = "".join([f"<div style='margin-left:10px;'><b>- {eq}</b></div>" for eq in datos['Semis']])
    liga_info = f"<p><b>Ligas Privadas:</b> {datos['Liga']}</p>" if datos['Liga'] else ""
    cuerpo = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px; background-color: #f9f9f9;">
        <div style="text-align: center; background-color: #000; padding: 20px; color: white;">
            <h1 style="color: #00FF87; margin:0;">COPA MUNDIAL 2026</h1>
            <p>TICKET OFICIAL</p>
        </div>
        <div style="padding: 20px;">
            <h3>Hola, {datos['Participante']}</h3>
            <p>Tu participación ha sido registrada correctamente.</p>
            <p><b>WhatsApp:</b> {datos['WhatsApp']}</p>
            {liga_info}
            <h3 style="color: #CF00FF;">🏆 TU PODIO FINAL</h3>
            <div style="background-color: #eee; padding: 15px; border-radius: 8px; text-align: center; font-size: 18px;">
                🥇 <b>1º: {datos['Campeon']}</b><br>🥈 2º: {datos['Subcampeon']}<br>🥉 3º: {datos['Tercero']}
            </div>
            <h3 style="color: #009688;">⚔️ FASES FINALES</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div style="background: #e0f2f1; padding: 10px; border-radius: 5px;"><b>SEMIFINALISTAS (4)</b><br>{lista_semis}</div>
                <div style="background: #e0f2f1; padding: 10px; border-radius: 5px;"><b>CUARTOS DE FINAL (8)</b><br>{lista_cuartos}</div>
            </div>
            <div style="background: #f1f8e9; padding: 10px; border-radius: 5px; margin-top: 10px;"><b>OCTAVOS DE FINAL (16)</b><br>{lista_octavos}</div>
            <h3 style="color: #000;">⚽ FASE DE GRUPOS</h3>
            {html_partidos}
        </div>
    </div>"""
    try:
        msg = MIMEMultipart(); msg['From'] = email_origen; msg['To'] = destinatario; msg['Subject'] = asunto
        # --- AQUÍ ESTÁ EL CAMBIO ---
        msg.attach(MIMEText(cuerpo, 'html', 'utf-8'))
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls()
        server.login(email_origen, password_app); server.sendmail(email_origen, destinatario, msg.as_string())
        server.quit(); return True
    except Exception as e:
        st.error(f"Error técnico enviando el correo: {e}")
        return False

def validar_duplicados_en_sheet(dni_input, email_input):
    emails, dnis, _ = traer_datos_validacion()
    if dni_input in dnis: return False, f"⚠️ El DNI {dni_input} ya está registrado."
    if email_input in emails: return False, f"⚠️ El correo {email_input} ya fue utilizado."
    return True, "OK"

def guardar_en_google_sheets(datos):
    intentos = 0; max_intentos = 3
    while intentos < max_intentos:
        try:
            client = obtener_client_gs()
            sheet = client.open(NOMBRE_HOJA_GOOGLE).sheet1
            fila = [
                datos["Fecha"], datos["Participante"], datos["Email"],
                datos["DNI"], datos["Edad"], datos["Direccion"],
                datos["WhatsApp"], datos["Liga"]
            ]
            for grupo in GRUPOS:
                codigo = grupo.split(" ")[1]
                for i in range(1, 7): fila.append(datos.get(f"P_G{codigo}_{i}", "-"))
            for grupo in GRUPOS: fila.extend([datos[f"{grupo}_1"], datos[f"{grupo}_2"], datos[f"{grupo}_3"]])
            fila.append(", ".join(datos["Octavos"])); fila.append(", ".join(datos["Cuartos"])); fila.append(", ".join(datos["Semis"]))
            fila.extend([datos["Campeon"], datos["Subcampeon"], datos["Tercero"]])
            sheet.append_row(fila)
            traer_datos_validacion.clear()
            return True
        except Exception as e:
            if "429" in str(e):
                intentos += 1; time.sleep(2)
            else:
                st.error(f"❌ Error conectando a Google Sheets: {e}"); return False
    return False

def actualizar_liga_existente(dni_check, email_check, nueva_liga_input):
    try:
        nueva_liga = nueva_liga_input.upper().strip()
        if nueva_liga in LIGAS_OCULTAS: return False, "⛔ Esta es una Liga Privada restringida."
        client = obtener_client_gs()
        sheet = client.open(NOMBRE_HOJA_GOOGLE).sheet1
        cell_dni = sheet.find(dni_check)
        if not cell_dni: return False, "❌ DNI no encontrado."
        row_idx = cell_dni.row
        email_en_sheet = sheet.cell(row_idx, 3).value
        if email_en_sheet.strip().lower() != email_check.strip().lower():
            return False, "❌ El Email no coincide con el DNI registrado."
        ligas_actuales_str = sheet.cell(row_idx, 8).value
        if not ligas_actuales_str: valor_final = nueva_liga
        else:
            lista_ligas = [x.strip() for x in ligas_actuales_str.split(',')]
            if nueva_liga in lista_ligas: return False, f"⚠️ Ya estás unido a {nueva_liga}."
            lista_ligas.append(nueva_liga)
            valor_final = ", ".join(lista_ligas)
        sheet.update_cell(row_idx, 8, valor_final)
        traer_datos_validacion.clear()
        return True, f"✅ ¡Te has unido a {nueva_liga}! Tus ligas ahora: {valor_final}"
    except Exception as e: return False, f"Error: {e}"

# ==========================================
# GESTIÓN DE LIGAS (PARA USUARIOS YA REGISTRADOS)
# ==========================================
if st.session_state.paso_actual == 1:
    listado_ligas_db = obtener_listado_ligas_existentes()
    opciones_ligas_existentes = ["Seleccionar..."] + listado_ligas_db + ["➕ CREAR NUEVA LIGA..."]

    with st.expander("🤝 ¿Ya estás registrado? Súmate a más Ligas aquí"):
        st.info("Ingresa tus datos y selecciona la liga.")
        c_exist1, c_exist2 = st.columns(2)
        dni_exist = c_exist1.text_input("Tu DNI (registrado)", key="dni_ex")
        email_exist = c_exist2.text_input("Tu Email (registrado)", key="email_ex")
        liga_seleccionada = st.selectbox("Selecciona la Liga a unirte:", opciones_ligas_existentes, key="sel_liga_ex")
        liga_final_unirse = ""
        if liga_seleccionada == "➕ CREAR NUEVA LIGA...":
            liga_final_unirse = st.text_input("Escribe el nombre de la nueva liga:", key="new_liga_ex").upper().strip()
        elif liga_seleccionada != "Seleccionar...":
            liga_final_unirse = liga_seleccionada

        if st.button("UNIRME A ESTA LIGA"):
            if not dni_exist or not email_exist or not liga_final_unirse:
                st.error("Completa todos los campos.")
            else:
                with st.spinner("Procesando..."):
                    ok, msg = actualizar_liga_existente(dni_exist, email_exist, liga_final_unirse)
                    if ok: st.success(msg)
                    else: st.warning(msg)

# ==========================================
# PASO 1: DATOS + GRUPOS (CON ST.FORM)
# ==========================================
if st.session_state.paso_actual == 1:
    st.markdown("---")
    st.subheader("📜 REGLAMENTO SUPER PRODE 2026")
    
    # --- AQUI SE MUESTRA LA FECHA DINAMICAMENTE ---
    st.info(f"""
    **1. SISTEMA DE PUNTUACIÓN**
    * **Fase de Grupos:** 10 pts por Clasificado | 5 pts extra por Posición Exacta | 1 pt por Resultado de Partido acertado.
    * **Bonus:** Se suman los puntos reales que tus equipos logren en el grupo.
    * **Playoffs:** Octavos 15 pts | Cuartos 20 pts | Semis 25 pts.
    * **Finales:** 3er Puesto 30 pts (+35 si aciertas ganador) | Finalista 40 pts | Campeón 50 pts.

    **2. LIGAS PRIVADAS Y MULTI-LIGA**
    * **Crear Ligas:** Puedes crear tu propia Liga Privada seleccionando "CREAR NUEVA LIGA" en el menú de inscripción.
    * **Multi-Liga:** ¡Puedes participar en varias ligas a la vez!
    * **Ligas Premium:** Existen ligas exclusivas gestionadas por la organización.

    **3. DINÁMICA DE CARGA**
    * **PASO 1:** Completa tus Datos y la Fase de Grupos.
    * **PASO 2:** Elige las Fases Finales con TUS clasificados.
    
    **4. FECHA LÍMITE DE INSCRIPCIÓN**
    * ⚠️ Tienes tiempo para cargar o modificar tu pronóstico hasta el: **{texto_limite}**. Pasada esa fecha, el formulario se bloqueará automáticamente.
    """)
    
    acepta_terminos = st.checkbox("✅ Acepto el reglamento.")
    
    if acepta_terminos:
        st.markdown("---")
        with st.form("form_paso_1"):
            st.subheader("1️⃣ PASO 1: DATOS Y GRUPOS")
            
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre y Apellido")
            dni_raw = c2.text_input("DNI / Documento (Sin puntos)")
            dni = dni_raw.replace(".", "").strip()
            email = c1.text_input("Correo Electrónico")
            direccion = c2.text_input("Localidad / Dirección")
            c3, c4 = st.columns(2)
            edad = c3.number_input("Edad", 0, 100, step=1)
            whatsapp = c4.text_input("WhatsApp / Celular")
            
            st.markdown("### 👥 LIGA PRIVADA (Opcional)")
            col_liga, col_info = st.columns([1, 2])
            with col_liga:
                liga_reg_sel = st.selectbox("Unirse a Liga existente", ["Sin Liga"] + listado_ligas_db + ["➕ CREAR NUEVA LIGA..."])
                liga_reg_final = ""
                if liga_reg_sel == "➕ CREAR NUEVA LIGA...":
                    liga_reg_final = st.text_input("Nombre nueva liga:", placeholder="Ej: OFICINA2026").upper().strip()
                elif liga_reg_sel != "Sin Liga":
                    liga_reg_final = liga_reg_sel
            
            st.markdown("---")
            seleccion_grupos = {}
            resultados_partidos = {}
            cols_pantalla = st.columns(2)
            idx_col = 0
            for nombre_grupo, equipos in GRUPOS.items():
                codigo = nombre_grupo.split(" ")[1]
                with cols_pantalla[idx_col % 2]: 
                    st.markdown(f"##### {nombre_grupo}")
                    for i, (idx_L, idx_V) in enumerate(FIXTURE_INDICES):
                        local, visita = equipos[idx_L], equipos[idx_V]
                        res = st.radio(f"{local} vs {visita}", ["L", "E", "V"], key=f"P_G{codigo}_{i+1}", horizontal=True)
                        resultados_partidos[f"P_G{codigo}_{i+1}"] = res
                    p1 = st.selectbox("1º Clasificado", ["-"]+equipos, key=f"{nombre_grupo}_1")
                    p2 = st.selectbox("2º Clasificado", ["-"]+equipos, key=f"{nombre_grupo}_2")
                    p3 = st.selectbox("3º Clasificado", ["-"]+equipos, key=f"{nombre_grupo}_3")
                    seleccion_grupos[nombre_grupo] = [p1, p2, p3]
                idx_col += 1
            
            submitted_1 = st.form_submit_button("SIGUIENTE PASO ➡️")
            
            if submitted_1:
                errores = []
                if not nombre or not dni or not email or not whatsapp: errores.append("⚠️ Faltan datos personales.")
                if liga_reg_final in LIGAS_OCULTAS: errores.append("⛔ Liga restringida.")
                clasificados_temp = []
                for g, e in seleccion_grupos.items():
                    if "-" in e or len(set(e))!=3: errores.append(f"Revisar selección en {g}")
                    else: clasificados_temp.extend(e)
                
                if errores:
                    for e in errores: st.error(e)
                else:
                    st.session_state.datos_usuario = {
                        "Nombre": nombre, "DNI": dni, "Email": email, "Direccion": direccion,
                        "Edad": edad, "WhatsApp": whatsapp, "Liga": liga_reg_final,
                        "Grupos": seleccion_grupos, "Partidos": resultados_partidos
                    }
                    st.session_state.equipos_clasificados_usuario = sorted(list(set(clasificados_temp)))
                    st.session_state.paso_actual = 2
                    st.rerun()

# ==========================================
# PASO 2: PLAYOFFS (SIN ST.FORM)
# ==========================================
elif st.session_state.paso_actual == 2:
    st.header("2️⃣ PASO 2: FASES FINALES")
    st.success("✅ Fase de grupos guardada temporalmente. Ahora elige a los campeones entre TUS clasificados.")
    
    mis_equipos = st.session_state.equipos_clasificados_usuario
    
    octavos = st.multiselect(f"Octavos de Final (Elige 16 de {len(mis_equipos)})", mis_equipos, max_selections=16)
    
    opciones_cuartos = octavos if len(octavos) == 16 else []
    if not opciones_cuartos: st.caption("👆 Completa los 16 de Octavos para habilitar Cuartos.")
    cuartos = st.multiselect("Cuartos de Final (Elige 8)", opciones_cuartos, max_selections=8)
    
    opciones_semis = cuartos if len(cuartos) == 8 else []
    if not opciones_semis and opciones_cuartos: st.caption("👆 Completa los 8 de Cuartos para habilitar Semis.")
    semis = st.multiselect("Semifinales (Elige 4)", opciones_semis, max_selections=4)
    
    st.divider()
    st.subheader("🏆 PODIO FINAL")
    opc_final = semis if len(semis)==4 else []
    if not opc_final and opciones_semis: st.caption("👆 Completa las Semis para elegir Campeón.")
    
    c1, c2, c3 = st.columns(3)
    campeon = c1.selectbox("CAMPEÓN", ["-"]+opc_final)
    subcampeon = c2.selectbox("SUBCAMPEÓN", ["-"]+opc_final)
    tercero = c3.selectbox("3ER PUESTO", ["-"]+opc_final)
    
    st.markdown("---")
    
    if st.button("CONFIRMAR Y ENVIAR PRONÓSTICO 🚀", type="primary"):
        errores = []
        if len(octavos)!=16: errores.append(f"Debes elegir 16 en Octavos (elegiste {len(octavos)})")
        if len(cuartos)!=8: errores.append(f"Debes elegir 8 en Cuartos (elegiste {len(cuartos)})")
        if len(semis)!=4: errores.append(f"Debes elegir 4 en Semis (elegiste {len(semis)})")
        if "-" in [campeon, subcampeon, tercero]: errores.append("Falta completar el Podio.")
        
        if errores:
            for e in errores: st.error(e)
        else:
            d = st.session_state.datos_usuario
            
            with st.spinner("Guardando en la nube..."):
                es_valido, mensaje = validar_duplicados_en_sheet(d["DNI"], d["Email"])
                if not es_valido:
                    st.error(mensaje)
                else:
                    datos_flat = {f"{g}_{i+1}": eq for g, lista in d["Grupos"].items() for i, eq in enumerate(lista)}
                    datos_finales = {
                        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Participante": d["Nombre"], "Email": d["Email"], "DNI": d["DNI"], 
                        "Edad": d["Edad"], "Direccion": d["Direccion"], "WhatsApp": d["WhatsApp"], 
                        "Liga": d["Liga"], 
                        **d["Partidos"], **datos_flat,
                        "Octavos": octavos, "Cuartos": cuartos, "Semis": semis,
                        "Campeon": campeon, "Subcampeon": subcampeon, "Tercero": tercero
                    }
                    
                    if guardar_en_google_sheets(datos_finales):
                        st.balloons()
                        st.success("✅ ¡PRONÓSTICO GUARDADO CON ÉXITO!")
                        if enviar_correo_confirmacion(datos_finales): 
                            st.success(f"📧 Copia enviada a {d['Email']}")
                        time.sleep(5)
                        st.session_state.clear()
                        st.rerun()
                    else:
                        st.error("Error al guardar. Intenta nuevamente.")

    if st.button("⬅️ Volver a corregir Grupos"):
        st.session_state.paso_actual = 1
        st.rerun()