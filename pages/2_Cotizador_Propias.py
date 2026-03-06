import streamlit as st
import pandas as pd
from utils import obtener_grupos_operativos, calcular_tarifa_viaje, inyectar_css

inyectar_css()
st.title("🚛 Cotizador de Unidades Propias")

@st.cache_data(ttl=60)
def cargar_grupos_activos():
    df = obtener_grupos_operativos()
    if not df.empty:
        return df[df['Estado'] == 'Activo']
    return pd.DataFrame()

df_activos = cargar_grupos_activos()

if df_activos.empty:
    st.warning("⚠️ No hay Grupos Operativos activos. Por favor crea uno en la pestaña de 'Gestión de Grupos'.")
    st.stop()

df_activos['Etiqueta_Visual'] = df_activos['Tipo_Unidad'] + " | " + df_activos['Tipo_Equipo'] + " | " + df_activos.get('Tipo_Ruta', '')

# ==========================================
# INTERFAZ DE INPUTS
# ==========================================
with st.container(border=True):
    st.subheader("1. Parámetros Operativos")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        grupo_seleccionado = st.selectbox("Selecciona el Grupo Operativo (Unidad | Equipo | Ruta)", df_activos['Etiqueta_Visual'].tolist(), index=None)
    with col2:
        modalidad = st.selectbox("Modalidad", ["One way", "Round trip"])
    with col3:
        num_operadores = st.number_input("Nº de Operadores", min_value=1, max_value=3, value=1, step=1)

    c_orig, c_dest, c_dist = st.columns(3)
    ciudad_origen = c_orig.text_input("Ciudad Origen", placeholder="Ej. Manzanillo, Col.")
    ciudad_destino = c_dest.text_input("Ciudad Destino", placeholder="Ej. Guadalajara, Jal.")
    distancia_ida = c_dist.number_input("Distancia Ida (km) [Se cobrará Ida y Vuelta automáticamente]", min_value=1.0, value=234.0)

    c_h1, c_h2, c_h3 = st.columns(3)
    horas_carga = c_h1.number_input("Horas de Carga estimadas", min_value=0.0, value=6.0)
    horas_descarga = c_h2.number_input("Horas de Descarga estimadas", min_value=0.0, value=6.0)
    
    # --- CAMBIO: Se usa un selectbox cerrado para forzar los saltos exactos de 0.5 ---
    opciones_viajes = [x / 2.0 for x in range(2, 19)] # Esto crea la lista: [1.0, 1.5, 2.0 ... 9.0]
    viajes_semana_input = c_h3.selectbox("Viajes a la semana", options=opciones_viajes, index=1) # index 1 corresponde al valor 1.5

with st.container(border=True):
    st.subheader("2. Costos Extras por Viaje")
    c_ext1, c_ext2, c_ext3 = st.columns(3)
    casetas = c_ext1.number_input("Casetas Ida ($) [Se considerará el doble automáticamente]", min_value=0.0, value=1687.0)
    pension = c_ext2.number_input("Pensión ($)", min_value=0.0, value=300.0)
    maniobras = c_ext3.number_input("Maniobras ($)", min_value=0.0, value=0.0)
    
    st.markdown("**Otros Gastos Adicionales (Dinámico)**")
    df_def_otros = pd.DataFrame([{"Concepto": "Ej. Permiso Especial", "Monto ($)": 0.0}])
    df_otros_final = st.data_editor(df_def_otros, num_rows="dynamic", width="stretch", key="grid_otros_cot")
    
    df_otros_limpio = df_otros_final.dropna(subset=["Concepto", "Monto ($)"])
    total_otros = pd.to_numeric(df_otros_limpio["Monto ($)"], errors='coerce').fillna(0).sum()

# ==========================================
# CÁLCULO Y RESULTADOS
# ==========================================
if st.button("🧮 Calcular Tarifa", type="primary", use_container_width=True):
    if not grupo_seleccionado or not ciudad_origen or not ciudad_destino:
        st.error("Por favor llena la ruta y selecciona un grupo operativo.")
    else:
        grupo_data = df_activos[df_activos['Etiqueta_Visual'] == grupo_seleccionado].iloc[0]
        
        inputs_viaje = {
            "modalidad": modalidad,
            "num_operadores": num_operadores,
            "distancia_ida": distancia_ida,
            "horas_carga": horas_carga,
            "horas_descarga": horas_descarga,
            "viajes_semana": viajes_semana_input, 
            "casetas": casetas,
            "pension": pension,
            "maniobras": maniobras,
            "otros": total_otros
        }

        res = calcular_tarifa_viaje(inputs_viaje, grupo_data)

        st.markdown("---")
        st.markdown(f"<h3 style='text-align: center;'>Tarifa Sugerida de Compra: <span style='color:#273176;'>${res['costo_total']:,.2f} MXN</span></h3>", unsafe_allow_html=True)
        
        texto_modalidad = " (+60% aplicado al Costo Total y Tarifa)" if modalidad == "Round trip" else ""
        
        st.markdown(f"<p style='text-align: center; color: gray;'>Modalidad: <strong>{modalidad}</strong>{texto_modalidad} | Operadores: {num_operadores} | Margen base: {res['margen_esperado']*100}% | Viajes est. semana: <strong>{res['viajes_semana']}</strong> | Viajes est. mes: <strong>{res['viajes_mes']}</strong></p>", unsafe_allow_html=True)
        
        st.subheader("Gran Total de Costos")
        m0, m1, m2, m3, m4 = st.columns(5)
        m0.metric("Fijos Mensuales", f"${res['fijo_mensual']:,.2f}")
        m1.metric("Fijo (Prorrateo Viaje)", f"${res['fijo_por_viaje']:,.2f}")
        m2.metric("Variables (Km)", f"${res['variable_km_viaje']:,.2f}", f"{res['distancia_total']} km totales", delta_color="off")
        m3.metric("Extras (Casetas x2, etc)", f"${res['extras_viaje']:,.2f}")
        
        margen_porcentaje = res['margen_esperado'] * 100
        m4.metric(f"Tarifa Venta ({margen_porcentaje:.0f}%)", f"${res['precio_venta']:,.2f}")

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📊 Ver Desglose Detallado por Viaje", expanded=False):
            col_fijos, col_vars = st.columns(2)
            
            with col_fijos:
                st.markdown("#### Costos Fijos (Prorrateados a este viaje)")
                df_fijos_v = pd.DataFrame(list(res["desglose_fijos_veh"].items()), columns=["Concepto (Vehículo)", "Monto ($)"])
                st.dataframe(df_fijos_v[df_fijos_v["Monto ($)"] > 0], hide_index=True, width="stretch")
                
                df_fijos_o = pd.DataFrame(list(res["desglose_fijos_op"].items()), columns=["Concepto (Operador)", "Monto ($)"])
                st.dataframe(df_fijos_o[df_fijos_o["Monto ($)"] > 0], hide_index=True, width="stretch")
                
            with col_vars:
                st.markdown("#### Costos Variables (Por Km de este viaje)")
                df_vars = pd.DataFrame(list(res["desglose_variables"].items()), columns=["Concepto Variable", "Monto ($)"])
                st.dataframe(df_vars[df_vars["Monto ($)"] > 0], hide_index=True, width="stretch")

                if not df_otros_limpio.empty and total_otros > 0:
                    st.markdown("#### Costos Extras")
                    st.dataframe(df_otros_limpio, hide_index=True, width="stretch")