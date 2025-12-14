import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json  # Librería esencial para leer el JSON completo

# ==========================================
# 1. CONFIGURACIÓN VISUAL
# ==========================================
st.set_page_config(page_title="Prode Mundial 2026", layout="wide", page_icon="🏆")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #ffffff; }
    p, label, .stMarkdown, .stCaption { color: #ffffff !important; font-family: 'Helvetica Neue', sans-serif; }
    h1, h2, h3 {
        font-family: 'Arial Black', sans-serif;
        background: -webkit-linear-gradient(45deg, #CF00FF, #00FF87);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-transform: uppercase;
        margin-bottom: 0px;
    }
    div[role="radiogroup"] { justify-content: center; }
    div[role="radiogroup"] label {
        background-color: #1a1a1a; border: 1px solid #444;
        padding: 4px 12px; border-radius: 4px; color: white;
        font-size: 14px; margin-right: 4px; transition: all 0.3s;
    }
    div[role="radiogroup"] label:hover { border-color: #00FF87; background-color: #222; cursor: pointer; }
    @media only screen and (max-width: 600px) {
        h1 { font-size: 28px !important; }
        .team-text { font-size: 11px !important; line-height: 1.2 !important; }
        div[role="radiogroup"] label { padding: 2px 6px !important; font-size: 12px !important; }
        .block-container { padding-left: 1rem; padding-right: 1rem; }
    }
    div.stButton > button {
        background: linear-gradient(90deg, #00C853 0%, #B2FF59 100%);
        color: black; font-weight: 800; border: none; padding: 15px 20px;
        font-size: 18px; text-transform: uppercase; width: 100%; border-radius: 8px; margin-top: 20px;
    }
    .stTextInput input, .stNumberInput input { background-color: #222; color: white; border: 1px solid #555; border-radius: 5px; }
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

# ==========================================
# 3. FUNCIONES DE CONEXIÓN
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
        html_partidos += f"<div style='margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom:5px;'><b>{nombre_grupo}:</b><br>"
        for i, (idx_L, idx_V) in enumerate(FIXTURE_INDICES):
            local, visita = equipos[idx_L], equipos[idx_V]
            key = f"P_G{codigo}_{i+1}"
            eleccion = datos.get(key, "-")
            res_txt = "EMPATE" if eleccion == "E" else (local if eleccion == "L" else visita)
            html_partidos += f"<span style='font-size: 12px;'>• {local} vs {visita} 👉 <b>{res_txt}</b></span><br>"
        html_partidos += "</div>"

    cuerpo = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px; background-color: #f9f9f9;">
        <div style="text-align: center; background-color: #000; padding: 20px; color: white;">
            <h1 style="color: #00FF87; margin:0;">COPA MUNDIAL 2026</h1>
            <p>TICKET OFICIAL</p>
        </div>
        <div style="padding: 20px;">
            <h3>Hola, {datos['Participante']}</h3>
            <p>Tu participación ha sido registrada.</p>
            <h3 style="color: #CF00FF;">🏆 TU PODIO</h3>
            <p>1. {datos['Campeon']} | 2. {datos['Subcampeon']} | 3. {datos['Tercero']}</p>
            <h3 style="color: #000;">⚽ DETALLE DE GRUPOS</h3>
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
        
        # Conexión al servidor Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_origen, password_app)
        server.sendmail(email_origen, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        # AQUI MOSTRAMOS EL ERROR EN PANTALLA
        st.error(f"❌ Error enviando email: {e}")
        return False

def guardar_en_google_sheets(datos):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Lectura del JSON completo con tolerancia a caracteres especiales
        contenido_json_texto = st.secrets["google_json"]["contenido_archivo"]
        creds_dict = json.loads(contenido_json_texto, strict=False)

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(NOMBRE_HOJA_GOOGLE).sheet1
        
        fila = [
            datos["Fecha"], datos["Participante"], datos["Email"],
            datos["DNI"], datos["Edad"], datos["Direccion"]
        ]
        for grupo in GRUPOS:
            codigo = grupo.split(" ")[1]
            for i in range(1, 7): fila.append(datos.get(f"P_G{codigo}_{i}", "-"))
        for grupo in GRUPOS:
            fila.extend([datos[f"{grupo}_1"], datos[f"{grupo}_2"], datos[f"{grupo}_3"]])
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
# 4. INTERFAZ
# ==========================================
st.markdown("---")
c1, c2 = st.columns(2)
nombre = c1.text_input("Nombre y Apellido")
dni = c2.text_input("DNI / Documento")
email = c1.text_input("Correo Electrónico")
direccion = c2.text_input("Localidad / Dirección")
edad = c1.number_input("Edad", 0, 100, step=1)

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
            st.markdown(f"<h5 style='color:#00FF87'>{nombre_grupo}</h5>", unsafe_allow_html=True)
            for i, (idx_L, idx_V) in enumerate(FIXTURE_INDICES):
                local, visita = equipos[idx_L], equipos[idx_V]
                c_loc, c_btn, c_vis = st.columns([3.5, 3, 3.5])
                with c_loc: st.markdown(f"<div class='team-text' style='text-align: right; font-weight: bold; font-size: 13px; padding-top: 10px;'>{local}</div>", unsafe_allow_html=True)
                with c_btn:
                    res = st.radio("R", ["L", "E", "V"], key=f"P_G{codigo}_{i+1}", horizontal=True, label_visibility="collapsed")
                with c_vis: st.markdown(f"<div class='team-text' style='text-align: left; font-weight: bold; font-size: 13px; padding-top: 10px;'>{visita}</div>", unsafe_allow_html=True)
                resultados_partidos[f"P_G{codigo}_{i+1}"] = res
            st.markdown("<hr style='border-top: 1px solid #333;'>", unsafe_allow_html=True)
            p1 = st.selectbox("1º", ["-"]+equipos, key=f"{nombre_grupo}_1")
            p2 = st.selectbox("2º", ["-"]+equipos, key=f"{nombre_grupo}_2")
            p3 = st.selectbox("3º", ["-"]+equipos, key=f"{nombre_grupo}_3")
            seleccion_grupos[nombre_grupo] = [p1, p2, p3]
    idx_col += 1

st.divider()
st.header("2. FASES FINALES")
octavos = st.multiselect("Octavos (16)", TODOS_LOS_EQUIPOS, max_selections=16)
cuartos = st.multiselect("Cuartos (8)", octavos if len(octavos)==16 else [], max_selections=8)
semis = st.multiselect("Semis (4)", cuartos if len(cuartos)==8 else [], max_selections=4)

st.divider()
st.header("3. PODIO")
opc_final = semis if len(semis)==4 else []
c1, c2, c3 = st.columns(3)
campeon = c1.selectbox("🏆 CAMPEÓN", ["-"]+opc_final)
subcampeon = c2.selectbox("🥈 SUBCAMPEÓN", ["-"]+opc_final)
tercero = c3.selectbox("🥉 3ER PUESTO", ["-"]+opc_final)

st.markdown("---")
if st.button("ENVIAR PRONÓSTICO 🚀", type="primary"):
    errores = []
    if not nombre or not dni or not email: errores.append("⚠️ Faltan datos personales.")
    for g, e in seleccion_grupos.items():
        if "-" in e or len(set(e))!=3: errores.append(f"Revisar {g}")
    if len(octavos)!=16 or len(cuartos)!=8 or len(semis)!=4: errores.append("Falta completar Playoffs.")
    if "-" in [campeon, subcampeon, tercero]: errores.append("Falta Podio.")
    
    if errores:
        for e in errores: st.error(e)
    else:
        datos_flat = {f"{g}_{i+1}": eq for g, lista in seleccion_grupos.items() for i, eq in enumerate(lista)}
        datos_finales = {
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Participante": nombre, "Email": email, "DNI": dni, "Edad": edad, "Direccion": direccion,
            **resultados_partidos, **datos_flat,
            "Octavos": octavos, "Cuartos": cuartos, "Semis": semis,
            "Campeon": campeon, "Subcampeon": subcampeon, "Tercero": tercero
        }
        
        with st.spinner("Procesando..."):
            # 1. Intentar Guardar en Google Sheets
            guardo_ok = guardar_en_google_sheets(datos_finales)
            
            if guardo_ok:
                st.success("✅ ¡Datos guardados correctamente en la Base de Datos!")
                
                # 2. Intentar Enviar Email (Solo si se guardó bien)
                email_ok = enviar_correo_confirmacion(datos_finales)
                
                if email_ok:
                    st.success(f"📧 ¡Correo de confirmación enviado a {email}!")
                    st.balloons()
                else:
                    st.warning("⚠️ Tus datos se guardaron, pero falló el envío del email.")
                    st.info("Revisa el mensaje de error rojo arriba para saber la causa.")