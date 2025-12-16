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

# ==========================================
# 1. CONFIGURACIÓN VISUAL Y CSS
# ==========================================
st.set_page_config(page_title="Prode Mundial 2026", layout="wide", page_icon="🏆")

st.markdown("""
    <style>
    /* 1. CORRECCIÓN VISUAL PARA DESPLEGABLES (TEXTO NEGRO) */
    div[data-baseweb="select"] > div { color: black !important; }
    li[role="option"] { color: black !important; background-color: white !important; }
    ul[role="listbox"] { background-color: white !important; }
    
    /* 2. ESTILOS GENERALES */
    .stApp { background-color: #000000; color: #ffffff; }
    p, label, .stMarkdown, .stCaption, .stCheckbox, li { color: #ffffff !important; font-family: 'Helvetica Neue', sans-serif; }
    h1, h2, h3 {
        font-family: 'Arial Black', sans-serif;
        background: -webkit-linear-gradient(45deg, #CF00FF, #00FF87);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-transform: uppercase;
        margin-bottom: 0px;
    }
    
    /* 3. OPTIMIZACIÓN RADIO BUTTONS (L-E-V) PARA CELULARES */
    div[role="radiogroup"] {
        display: flex;
        justify-content: center;
        width: 100%;
        margin-bottom: 10px;
    }
    div[role="radiogroup"] label {
        background-color: #1a1a1a;
        border: 1px solid #444;
        padding: 10px 0px; /* Botones más altos para tocar fácil */
        width: 30%;        /* Ocupan todo el ancho disponible dividido en 3 */
        text-align: center;
        border-radius: 6px;
        color: white;
        font-size: 16px;
        font-weight: bold;
        margin: 0 4px;     /* Separación entre botones */
        transition: all 0.2s;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    div[role="radiogroup"] label:hover {
        border-color: #00FF87;
        background-color: #222;
        cursor: pointer;
    }
    /* Ocultar el círculo del radio button para que parezca botón rectangular */
    div[role="radiogroup"] label > div:first-child {
        display: none;
    }
    
    /* 4. TEXTO DE EQUIPOS EN MÓVIL */
    .match-title {
        text-align: center;
        font-weight: bold;
        font-size: 15px;
        margin-bottom: 8px;
        color: #ddd;
        margin-top: 15px;
    }
    
    /* 5. BOTÓN ENVIAR */
    div.stButton > button {
        background: linear-gradient(90deg, #00C853 0%, #B2FF59 100%);
        color: black; font-weight: 800; border: none; padding: 15px 20px;
        font-size: 18px; text-transform: uppercase; width: 100%; border-radius: 8px; margin-top: 20px;
    }
    .stTextInput input, .stNumberInput input { background-color: #222; color: white; border: 1px solid #555; border-radius: 5px; }
    .stAlert { background-color: #222; color: white; border: 1px solid #555; }
    strong { color: #00FF87; }
    </style>
""", unsafe_allow_html=True)

# BARRA LATERAL
with st.sidebar:
    if os.path.exists("logo.jpg"): st.image("logo.jpg", use_container_width=True)
    elif os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.markdown("---")
    st.markdown("### 🎵 AMBIENTACIÓN")
    st.components.v1.iframe("https://www.youtube.com/embed/kyXRhggUmG8", height=150)

# HEADER
c_logo, c_tit = st.columns([1, 5])
with c_logo:
    if os.path.exists("logo.jpg"): st.image("logo.jpg", use_container_width=True)
    elif os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
with c_tit:
    st.title("FIFA WORLD CUP 2026")
    st.markdown("### OFFICIAL PREDICTION GAME")

# ==========================================
# 2. CONFIGURACIÓN DE DATOS
# ==========================================
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

# ==========================================
# 3. FUNCIONES DE CONEXIÓN Y VALIDACIÓN
# ==========================================
def enviar_correo_confirmacion(datos):
    try:
        email_origen = st.secrets["email_credentials"]["EMAIL_ORIGEN"]
        password_app = st.secrets["email_credentials"]["PASSWORD_APP"]
    except:
        st.error("⚠️ Configuración: No se encontraron las credenciales de Email en Secrets.")
        return False

    destinatario = datos["Email"]
    asunto = f"🏆 Ticket Oficial Mundial 2026 - {datos['Participante']}"
    
    html_partidos = ""
    for nombre_grupo, equipos in GRUPOS.items():
        codigo = nombre_grupo.split(" ")[1]
        p1 = datos.get(f"{nombre_grupo}_1", "-")
        p2 = datos.get(f"{nombre_grupo}_2", "-")
        p3 = datos.get(f"{nombre_grupo}_3", "-")

        html_partidos += f"<div style='margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom:5px;'><b>{nombre_grupo}:</b><br>"
        for i, (idx_L, idx_V) in enumerate(FIXTURE_INDICES):
            local, visita = equipos[idx_L], equipos[idx_V]
            key = f"P_G{codigo}_{i+1}"
            eleccion = datos.get(key, "-")
            res_txt = "EMPATE" if eleccion == "E" else (local if eleccion == "L" else visita)
            html_partidos += f"<span style='font-size: 12px;'>• {local} vs {visita} 👉 <b>{res_txt}</b></span><br>"
        html_partidos += f"<br><span style='font-size: 12px; color: #444;'><i>Clasificados: 1. {p1} | 2. {p2} | 3. {p3}</i></span></div>"

    lista_octavos = "".join([f"<div style='margin-left:10px;'>- {eq}</div>" for eq in datos['Octavos']])
    lista_cuartos = "".join([f"<div style='margin-left:10px;'>- {eq}</div>" for eq in datos['Cuartos']])
    lista_semis = "".join([f"<div style='margin-left:10px;'><b>- {eq}</b></div>" for eq in datos['Semis']])

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
            <h3 style="color: #CF00FF;">🏆 TU PODIO FINAL</h3>
            <div style="background-color: #eee; padding: 15px; border-radius: 8px; text-align: center; font-size: 18px;">
                🥇 <b>1º: {datos['Campeon']}</b><br>
                🥈 2º: {datos['Subcampeon']}<br>
                🥉 3º: {datos['Tercero']}
            </div>
            <h3 style="color: #009688;">⚔️ FASES FINALES</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div style="background: #e0f2f1; padding: 10px; border-radius: 5px;"><b>SEMIFINALISTAS (4)</b><br>{lista_semis}</div>
                <div style="background: #e0f2f1; padding: 10px; border-radius: 5px;"><b>CUARTOS DE FINAL (8)</b><br>{lista_cuartos}</div>
            </div>
            <div style="background: #f1f8e9; padding: 10px; border-radius: 5px; margin-top: 10px;">
                <b>OCTAVOS DE FINAL (16)</b><br>{lista_octavos}
            </div>
            <h3 style="color: #000;">⚽ FASE DE GRUPOS</h3>
            {html_partidos}
        </div>
    </div>
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = email_origen
        msg['To'] = destinatario
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_origen, password_app)
        server.sendmail(email_origen, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"❌ Error enviando email: {e}")
        return False

def validar_duplicados_en_sheet(dni_input, email_input):
    """Verifica si el DNI o Email ya existen en Google Sheets"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
        creds_dict = json.loads(contenido_json_texto, strict=False)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(NOMBRE_HOJA_GOOGLE).sheet1
        
        # Ojo con los índices de columnas si agregas WhatsApp
        lista_emails = sheet.col_values(3) # Col C
        lista_dnis = sheet.col_values(4)   # Col D
        
        if dni_input in lista_dnis:
            return False, f"⚠️ El DNI {dni_input} ya está registrado en el torneo."
        
        if email_input in lista_emails:
            return False, f"⚠️ El correo {email_input} ya fue utilizado."
            
        return True, "OK"
    except Exception as e:
        return False, f"Error validando base de datos: {e}"

def guardar_en_google_sheets(datos):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
        creds_dict = json.loads(contenido_json_texto, strict=False)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(NOMBRE_HOJA_GOOGLE).sheet1
        
        fila = [
            datos["Fecha"], datos["Participante"], datos["Email"],
            datos["DNI"], datos["Edad"], datos["Direccion"],
            datos["WhatsApp"] # <--- AGREGADO: Columna G
        ]
        # PARTIDOS
        for grupo in GRUPOS:
            codigo = grupo.split(" ")[1]
            for i in range(1, 7): fila.append(datos.get(f"P_G{codigo}_{i}", "-"))
        # CLASIFICADOS DE GRUPO
        for grupo in GRUPOS:
            fila.extend([datos[f"{grupo}_1"], datos[f"{grupo}_2"], datos[f"{grupo}_3"]])
        # FASES FINALES
        fila.append(", ".join(datos["Octavos"]))
        fila.append(", ".join(datos["Cuartos"]))
        fila.append(", ".join(datos["Semis"]))
        fila.extend([datos["Campeon"], datos["Subcampeon"], datos["Tercero"]])
        
        sheet.append_row(fila)
        return True
    except Exception as e:
        st.error(f"❌ Error conectando a Google Sheets: {e}")
        return False

# ==========================================
# 4. REGLAMENTO Y DATOS
# ==========================================
st.markdown("---")
st.subheader("📜 REGLAMENTO SUPER PRODE USA-MEXICO-CANADA 2026")

reglamento_texto = """
**1. Sistema de puntuación:**
* **a)** Se sumará **10 Pts.** por cada equipo que Ud. acierte en la primera fase.
* **b)** Además se sumará **5 Pts.** si Ud. acierta la posición de los equipos clasificados en sus respectivos grupos.
* **c)** También se sumarán los Pts. que los equipos clasificados sumen en sus grupos.
* **d)** En **Octavos de Final**, Ud. sumará **15 Pts.** por cada equipo acertado.
* **e)** En **Cuartos de Final**, Ud. sumará **20 Pts.** por cada equipo acertado.
* **f)** En **Semifinales**, Ud. sumará **25 Pts.** por cada equipo acertado.
* **g)** En el partido por el **Tercer Puesto** se sumará **30 Pts.** por equipo acertado, más **35 Pts.** si acierta al tercer puesto.
* **h)** Se sumará **40 Pts.** por cada equipo que Ud. acierte en la **Final**.
* **i)** Si Ud. acierta el equipo **Campeón**, sumará un bonus de **50 Pts.**

**2. Ronda Partido X Partido:**
* **j)** Se tomarán todos los partidos de la fase de grupos. Deberá seleccionar el resultado (Local, Empate o Visitante). Cada acierto sumará **1 punto** para esta ronda, como también para el total del SUPER PRODE 2026.

**3. Aclaraciones del juego:**
* **k)** En caso de empate en la puntuación final se desempatará de la siguiente forma:
    1.  El participante que haya logrado mayor cantidad de Pts. en la fase de grupos.
    2.  De persistir el empate, ganará el participante que logre más Pts. sumados entre octavos, cuartos, semifinales, tercer puesto y final.
    3.  De persistir el empate, el ganador se decidirá por sorteo.
* **l)** Solo se permitirá un prode por persona.
"""

st.info(reglamento_texto)
acepta_terminos = st.checkbox("✅ He leído, comprendo y ACEPTO el reglamento del juego.")

if not acepta_terminos:
    st.warning("⚠️ Debes aceptar el reglamento para desbloquear el formulario de inscripción.")
    st.stop()

st.markdown("---")
st.subheader("👤 DATOS DEL PARTICIPANTE")
c1, c2 = st.columns(2)
nombre = c1.text_input("Nombre y Apellido")
dni_raw = c2.text_input("DNI / Documento (Sin puntos)")
email = c1.text_input("Correo Electrónico")
direccion = c2.text_input("Localidad / Dirección")

c3, c4 = st.columns(2)
edad = c3.number_input("Edad", 0, 100, step=1)
whatsapp = c4.text_input("WhatsApp / Celular (con cód. área)") # <--- NUEVO CAMPO

dni = dni_raw.replace(".", "").strip()

# ==========================================
# 5. JUEGO (GRUPOS Y FINALES)
# ==========================================
st.markdown("---")
st.header("1. FASE DE GRUPOS")
seleccion_grupos = {}
resultados_partidos = {}
cols_pantalla = st.columns(2)
idx_col = 0

for nombre_grupo, equipos in GRUPOS.items():
    codigo = nombre_grupo.split(" ")[1]
    with cols_pantalla[idx_col % 2]: 
        with st.expander(f"{nombre_grupo}", expanded=False):
            # Titulo del grupo
            st.markdown(f"<h5 style='color:#00FF87; text-align:center;'>{nombre_grupo}</h5>", unsafe_allow_html=True)
            
            # --- LOOP PARTIDOS OPTIMIZADO PARA CELULAR ---
            for i, (idx_L, idx_V) in enumerate(FIXTURE_INDICES):
                local, visita = equipos[idx_L], equipos[idx_V]
                
                # 1. Título del partido centrado
                st.markdown(f"<div class='match-title'>{local} <span style='color:#00FF87; font-size:12px;'>vs</span> {visita}</div>", unsafe_allow_html=True)
                
                # 2. Botones L-E-V abajo
                res = st.radio(
                    f"{local} vs {visita}",
                    ["L", "E", "V"],
                    key=f"P_G{codigo}_{i+1}",
                    horizontal=True,
                    label_visibility="collapsed"
                )
                resultados_partidos[f"P_G{codigo}_{i+1}"] = res
                
                # Separador
                if i < len(FIXTURE_INDICES) - 1:
                    st.markdown("<div style='margin-bottom: 10px; border-bottom: 1px solid #333;'></div>", unsafe_allow_html=True)
            # ---------------------------------------------
            
            st.markdown("<hr style='border-top: 2px solid #00FF87; margin-top: 20px;'>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; margin-bottom:10px;'><b>📊 Clasificados</b></div>", unsafe_allow_html=True)
            p1 = st.selectbox("1º Clasificado", ["-"]+equipos, key=f"{nombre_grupo}_1")
            p2 = st.selectbox("2º Clasificado", ["-"]+equipos, key=f"{nombre_grupo}_2")
            p3 = st.selectbox("3º Clasificado", ["-"]+equipos, key=f"{nombre_grupo}_3")
            seleccion_grupos[nombre_grupo] = [p1, p2, p3]
    idx_col += 1

st.divider()
st.header("2. FASES FINALES")
equipos_clasificados = []
for lista_equipos in seleccion_grupos.values():
    for equipo in lista_equipos:
        if equipo != "-": equipos_clasificados.append(equipo)
equipos_clasificados = sorted(list(set(equipos_clasificados)))

if len(equipos_clasificados) < 32: st.info("ℹ️ Completa las posiciones (1º, 2º y 3º) de todos los grupos arriba para ver a tus equipos aquí.")
octavos = st.multiselect(f"Octavos ({len(equipos_clasificados)} clasificados)", equipos_clasificados, max_selections=16)
cuartos = st.multiselect("Cuartos (8)", octavos if len(octavos)==16 else [], max_selections=8)
semis = st.multiselect("Semis (4)", cuartos if len(cuartos)==8 else [], max_selections=4)

st.divider()
st.header("3. PODIO")
opc_final = semis if len(semis)==4 else []
c1, c2, c3 = st.columns(3)
campeon = c1.selectbox("🏆 CAMPEÓN", ["-"]+opc_final)
subcampeon = c2.selectbox("🥈 SUBCAMPEÓN", ["-"]+opc_final)
tercero = c3.selectbox("🥉 3ER PUESTO", ["-"]+opc_final)

# ==========================================
# 6. BOTÓN DE ENVÍO CON VALIDACIÓN
# ==========================================
st.markdown("---")
if st.button("ENVIAR PRONÓSTICO 🚀", type="primary"):
    errores = []
    if not nombre or not dni or not email or not whatsapp: errores.append("⚠️ Faltan datos personales (incluido WhatsApp).")
    if "@" not in email: errores.append("⚠️ El correo electrónico no parece válido.")
    if len(dni) < 6 or not dni.isdigit(): errores.append("⚠️ El DNI debe contener solo números (mínimo 6).")
    
    for g, e in seleccion_grupos.items():
        if "-" in e or len(set(e))!=3: errores.append(f"Revisar {g}")
    if len(octavos)!=16 or len(cuartos)!=8 or len(semis)!=4: errores.append("Falta completar Playoffs.")
    if "-" in [campeon, subcampeon, tercero]: errores.append("Falta Podio.")
    
    if errores:
        for e in errores: st.error(e)
    else:
        with st.spinner("Verificando disponibilidad de usuario..."):
            es_valido, mensaje_validacion = validar_duplicados_en_sheet(dni, email)
        
        if not es_valido:
            st.error(mensaje_validacion)
        else:
            datos_flat = {f"{g}_{i+1}": eq for g, lista in seleccion_grupos.items() for i, eq in enumerate(lista)}
            datos_finales = {
                "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Participante": nombre, "Email": email, "DNI": dni, "Edad": edad, "Direccion": direccion,
                "WhatsApp": whatsapp, 
                **resultados_partidos, **datos_flat,
                "Octavos": octavos, "Cuartos": cuartos, "Semis": semis,
                "Campeon": campeon, "Subcampeon": subcampeon, "Tercero": tercero
            }
            
            with st.spinner("Guardando pronóstico..."):
                guardo_ok = guardar_en_google_sheets(datos_finales)
                if guardo_ok:
                    st.success("✅ ¡Datos guardados correctamente!")
                    email_ok = enviar_correo_confirmacion(datos_finales)
                    if email_ok:
                        st.success(f"📧 ¡Correo enviado a {email}!")
                        st.balloons()
                    else:
                        st.warning("⚠️ Datos guardados, pero falló el email.")