import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# ==========================================
# 1. CONFIGURACIÓN VISUAL (RESPONSIVE + ESTILO 2026)
# ==========================================
st.set_page_config(page_title="Prode Mundial 2026", layout="wide", page_icon="🏆")

# --- ESTILOS CSS AVANZADOS (PC Y MÓVIL) ---
st.markdown("""
    <style>
    /* 1. FONDO Y TEXTOS GENERALES */
    .stApp {
        background-color: #000000;
        color: #ffffff;
    }
    p, label, .stMarkdown, .stCaption {
        color: #ffffff !important;
        font-family: 'Helvetica Neue', sans-serif;
    }

    /* 2. ENCABEZADOS DEGRADADOS */
    h1, h2, h3 {
        font-family: 'Arial Black', sans-serif;
        background: -webkit-linear-gradient(45deg, #CF00FF, #00FF87);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-transform: uppercase;
        margin-bottom: 0px;
    }

    /* 3. OPTIMIZACIÓN DE BOTONES DE RADIO (PARTIDOS) */
    /* Contenedor de los botones */
    div[role="radiogroup"] {
        justify-content: center;
    }
    /* Los botones individuales */
    div[role="radiogroup"] label {
        background-color: #1a1a1a;
        border: 1px solid #444;
        padding: 4px 12px;
        border-radius: 4px;
        color: white;
        font-size: 14px;
        margin-right: 4px;
        transition: all 0.3s;
    }
    /* Efecto al pasar el mouse */
    div[role="radiogroup"] label:hover {
        border-color: #00FF87;
        background-color: #222;
        cursor: pointer;
    }

    /* 4. ESTILOS ESPECÍFICOS PARA MÓVILES (PANTALLAS CHICAS) */
    @media only screen and (max-width: 600px) {
        /* Achicar título principal */
        h1 { font-size: 28px !important; }
        
        /* Achicar nombres de equipos en los partidos */
        .team-text { 
            font-size: 11px !important; 
            line-height: 1.2 !important;
        }
        
        /* Ajustar los botones de radio para que entren */
        div[role="radiogroup"] label {
            padding: 2px 6px !important;
            font-size: 12px !important;
        }
        
        /* Reducir márgenes laterales */
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }

    /* 5. BOTÓN DE ENVIAR */
    div.stButton > button {
        background: linear-gradient(90deg, #00C853 0%, #B2FF59 100%);
        color: black;
        font-weight: 800;
        border: none;
        padding: 15px 20px;
        font-size: 18px;
        text-transform: uppercase;
        width: 100%;
        border-radius: 8px;
        margin-top: 20px;
    }
    
    /* 6. INPUTS */
    .stTextInput input, .stNumberInput input {
        background-color: #222;
        color: white;
        border: 1px solid #555;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL CON REPRODUCTOR Y LOGO ---
with st.sidebar:
    # Intenta cargar el logo local, si no existe, no muestra nada (para evitar error)
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.warning("⚠️ Sube la imagen 'logo.png' a la carpeta.")
    
    st.markdown("---")
    st.markdown("### 🎵 AMBIENTACIÓN")
    st.components.v1.iframe("https://www.youtube.com/embed/kyXRhggUmG8", height=150)
    st.caption("Dale Play para escuchar el himno oficial.")

# --- TÍTULO PRINCIPAL (Visible en PC y Celu) ---
c_logo_main, c_tit_main = st.columns([1, 5])
with c_logo_main:
     if os.path.exists("logo.jpg"): st.image("logo.jpg", use_container_width=True)
with c_tit_main:
    st.title("FIFA WORLD CUP 2026")
    st.markdown("### OFFICIAL PREDICTION GAME")

# ==========================================
# 2. CONFIGURACIÓN DE DATOS
# ==========================================
NOMBRE_HOJA_GOOGLE = "DB_Prode_2026"
ARCHIVO_CREDENCIALES = "credentials.json"
EMAIL_ORIGEN = "fvizcay@gmail.com"  # <--- TU EMAIL
PASSWORD_APP = "ecih oqsy kndp ilys" # <--- TU CLAVE

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
# 3. FUNCIONES
# ==========================================
def enviar_correo_confirmacion(datos):
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
            <p>TICKET OFICIAL DE PRONÓSTICOS</p>
        </div>
        <div style="padding: 20px;">
            <h3>Hola, {datos['Participante']}</h3>
            <p>Tu participación ha sido registrada correctamente.</p>
            <table style="width:100%; border-collapse: collapse; margin-top: 20px;">
                <tr style="background-color: #ddd;">
                    <td style="padding: 10px;"><b>DNI:</b> {datos['DNI']}</td>
                    <td style="padding: 10px;"><b>Email:</b> {datos['Email']}</td>
                </tr>
            </table>
            <h3 style="color: #CF00FF; border-bottom: 2px solid #CF00FF; margin-top: 30px;">🏆 TU PODIO</h3>
            <p style="font-size: 18px; font-weight: bold;">
                🥇 1. {datos['Campeon']}<br>
                🥈 2. {datos['Subcampeon']}<br>
                🥉 3. {datos['Tercero']}
            </p>
            <h3 style="color: #000; margin-top: 30px;">⚽ FASE DE GRUPOS</h3>
            {html_partidos}
            <h3 style="color: #000; margin-top: 30px;">⚔️ ELIMINATORIAS</h3>
            <p><b>Semifinales:</b> {', '.join(datos['Semis'])}</p>
            <p><b>Cuartos:</b> {', '.join(datos['Cuartos'])}</p>
            <p><b>Octavos:</b> {', '.join(datos['Octavos'])}</p>
        </div>
    </div>
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ORIGEN
        msg['To'] = destinatario
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ORIGEN, PASSWORD_APP)
        server.sendmail(EMAIL_ORIGEN, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error mail: {e}")
        return False

def guardar_en_google_sheets(datos):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(ARCHIVO_CREDENCIALES, scope)
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
        st.error(f"❌ Error Sheets: {e}")
        return False

# ==========================================
# 4. INTERFAZ GRÁFICA
# ==========================================

st.markdown("---")
st.markdown("#### 👤 DATOS PERSONALES")
c1, c2 = st.columns(2)
nombre = c1.text_input("Nombre y Apellido")
dni = c2.text_input("DNI / Documento")
email = c1.text_input("Correo Electrónico")
direccion = c2.text_input("Localidad / Dirección")
edad = c1.number_input("Edad", 0, 100, step=1)

st.markdown("---")

# --- GRUPOS ---
st.header("1. FASE DE GRUPOS")
st.info("Pronostica los resultados (L=Local, E=Empate, V=Visitante).")

seleccion_grupos = {}
resultados_partidos = {}

# En PC usamos 2 columnas, en celular se apilarán solas gracias a Streamlit
cols_pantalla = st.columns(2)
idx_col = 0

for nombre_grupo, equipos in GRUPOS.items():
    codigo = nombre_grupo.split(" ")[1]
    with cols_pantalla[idx_col % 2]: 
        with st.expander(f"{nombre_grupo}", expanded=False):
            st.markdown(f"<h5 style='color:#00FF87'>PARTIDOS {nombre_grupo}</h5>", unsafe_allow_html=True)
            
            for i, (idx_L, idx_V) in enumerate(FIXTURE_INDICES):
                local, visita = equipos[idx_L], equipos[idx_V]
                
                # OPTIMIZACIÓN MÓVIL: Columnas ajustadas
                # Usamos clases CSS 'team-text' para controlarlas desde el estilo
                c_loc, c_btn, c_vis = st.columns([3.5, 3, 3.5])
                
                with c_loc: 
                    st.markdown(f"<div class='team-text' style='text-align: right; font-weight: bold; font-size: 13px; padding-top: 10px;'>{local}</div>", unsafe_allow_html=True)
                with c_btn:
                    res = st.radio("R", ["L", "E", "V"], key=f"P_G{codigo}_{i+1}", horizontal=True, label_visibility="collapsed")
                with c_vis: 
                    st.markdown(f"<div class='team-text' style='text-align: left; font-weight: bold; font-size: 13px; padding-top: 10px;'>{visita}</div>", unsafe_allow_html=True)
                
                resultados_partidos[f"P_G{codigo}_{i+1}"] = res
            
            st.markdown("<hr style='border-top: 1px solid #333;'>", unsafe_allow_html=True)
            st.markdown(f"<h5 style='color:#CF00FF'>POSICIONES {nombre_grupo}</h5>", unsafe_allow_html=True)
            p1 = st.selectbox("1º Lugar", ["-"]+equipos, key=f"{nombre_grupo}_1")
            p2 = st.selectbox("2º Lugar", ["-"]+equipos, key=f"{nombre_grupo}_2")
            p3 = st.selectbox("3º Lugar", ["-"]+equipos, key=f"{nombre_grupo}_3")
            seleccion_grupos[nombre_grupo] = [p1, p2, p3]
    idx_col += 1

st.divider()

# --- PLAYOFFS ---
st.header("2. FASES ELIMINATORIAS")

st.subheader("Octavos de Final")
octavos = st.multiselect("Selecciona 16:", TODOS_LOS_EQUIPOS, max_selections=16)
if len(octavos) < 16: st.caption(f"Faltan: {16 - len(octavos)}")

st.subheader("Cuartos de Final")
cuartos = st.multiselect("Selecciona 8:", octavos if len(octavos) == 16 else [], max_selections=8, disabled=(len(octavos)!=16))

st.subheader("Semifinales")
semis = st.multiselect("Selecciona 4:", cuartos if len(cuartos) == 8 else [], max_selections=4, disabled=(len(cuartos)!=8))

st.divider()

# --- PODIUM ---
st.header("3. PODIO FINAL")
hab_final = (len(semis) == 4)
opciones_final = semis if hab_final else []

c1, c2, c3 = st.columns(3)
campeon = c1.selectbox("🏆 CAMPEÓN", ["-"] + opciones_final, disabled=not hab_final)
subcampeon = c2.selectbox("🥈 SUBCAMPEÓN", ["-"] + opciones_final, disabled=not hab_final)
tercero = c3.selectbox("🥉 3ER PUESTO", ["-"] + opciones_final, disabled=not hab_final)

st.markdown("---")

if st.button("ENVIAR PRONÓSTICO 🚀", type="primary", use_container_width=True):
    errores = []
    if not nombre or not dni or not email or not direccion: errores.append("⚠️ Faltan tus datos personales.")
    if "@" not in email: errores.append("⚠️ Email inválido.")
    
    for grupo, elegidos in seleccion_grupos.items():
        if "-" in elegidos: errores.append(f"⚠️ {grupo} incompleto.")
        elif len(set(elegidos)) != 3: errores.append(f"⛔ {grupo}: Posiciones repetidas.")

    if len(octavos)!=16 or len(cuartos)!=8 or len(semis)!=4: errores.append("⚠️ Fases finales incompletas.")
    
    podio = [campeon, subcampeon, tercero]
    if "-" in podio and hab_final: errores.append("⚠️ Falta podio.")
    elif len(set(podio)) != 3 and hab_final: errores.append("⛔ Podio con repetidos.")

    if errores:
        for e in errores: st.error(e)
    else:
        # Armar datos
        datos_flat = {f"{g}_{i+1}": eq for g, lista in seleccion_grupos.items() for i, eq in enumerate(lista)}
        
        datos_finales = {
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Participante": nombre,
            "Email": email, "DNI": dni, "Edad": edad, "Direccion": direccion,
            **resultados_partidos,
            **datos_flat,
            "Octavos": octavos, "Cuartos": cuartos, "Semis": semis,
            "Campeon": campeon, "Subcampeon": subcampeon, "Tercero": tercero
        }
        
        with st.spinner("Guardando..."):
            if guardar_en_google_sheets(datos_finales):
                enviar_correo_confirmacion(datos_finales)
                st.success(f"¡LISTO! Ticket enviado a {email}")
                st.balloons()