import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
import secrets

st.set_page_config(page_title="Cotizador Unidades Propias", layout="wide")

@st.cache_resource
def obtener_llave_dinamica():
    return secrets.token_hex(16)

try:
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)
except FileNotFoundError:
    st.error("⚠️ Archivo config.yaml no encontrado.")
    st.stop()

config['cookie']['key'] = obtener_llave_dinamica()

authenticator = stauth.Authenticate(
    config['credentials'], config['cookie']['name'], 
    config['cookie']['key'], config['cookie']['expiry_days']
)

# Login
if not st.session_state.get("authentication_status"):
    col1, col_login, col3 = st.columns([1, 1, 1])
    with col_login:
        st.markdown("<h3 style='text-align: center; color: #273176;'>ACCESO ESGARI</h3>", unsafe_allow_html=True)
        authenticator.login('main')
        if st.session_state["authentication_status"] is False:
            st.error('❌ Usuario o contraseña incorrectos')
    if st.session_state.get("authentication_status"):
        st.rerun()
else:
    # --- APP PRINCIPAL ---
    authenticator.logout('Cerrar Sesión', 'sidebar')
    st.sidebar.write(f'Hola, **{st.session_state["name"]}**')

    # Navegación Multipage nativa
    gestion = st.Page("pages/1_Gestion_Grupos.py", title="Gestión de Grupos", icon="⚙️")
    cotizador = st.Page("pages/2_Cotizador_Propias.py", title="Cotizador", icon="🚛")
    
    pg = st.navigation([gestion, cotizador])
    pg.run()