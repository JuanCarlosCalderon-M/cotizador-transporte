import requests
import pandas as pd
import streamlit as st
import json
import math

# --- PEGA TU NUEVA URL AQUÍ ---
URL_APP_SCRIPT = "https://script.google.com/macros/s/AKfycbx3ayhAZz6Xqm0tilnQO2IHWCO1d7R8TA0P5MMYcwMim3fUuO4c_fCue-jR8SVBule2/exec"

def obtener_grupos_operativos():
    """Lee todos los grupos desde Google Sheets y convierte los JSON a diccionarios."""
    try:
        respuesta = requests.get(f"{URL_APP_SCRIPT}?hoja=Grupos_Operativos", timeout=15)
        respuesta.raise_for_status()
        df = pd.DataFrame(respuesta.json())
        
        # Si el DataFrame no está vacío, convertimos las columnas de texto a diccionarios
        if not df.empty:
            columnas_json = ['Configuracion_Operativa', 'Costos_Variables', 'Costos_Fijos_Vehiculo', 'Costos_Fijos_Operador']
            for col in columnas_json:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: json.loads(x) if pd.notna(x) and str(x).strip() != '' else {})
        return df
    except Exception as e:
        st.error(f"Error al cargar grupos operativos: {e}")
        return pd.DataFrame()

# Solo modifica los parámetros de esta función en tu utils.py
def gestionar_grupo_operativo(accion, datos=None, id_grupo=None, usuario=None):
    payload = {"accion": accion}
    if datos is not None:
        payload["datos"] = datos
    if id_grupo is not None:
        payload["id_grupo"] = id_grupo
    if usuario is not None:
        payload["usuario"] = usuario # <--- AQUÍ ENVIAMOS EL USUARIO AL SCRIPT

    try:
        respuesta = requests.post(URL_APP_SCRIPT, json=payload, timeout=15)
        respuesta.raise_for_status()
        resultado = respuesta.json()
        
        if resultado.get("status") == "success":
            return True, "Operación exitosa."
        else:
            return False, f"Error en BD: {resultado.get('message')}"
    except Exception as e:
        return False, f"Error de conexión: {e}"

def inyectar_css():
    st.markdown("""
    <style>
        h1, h2, h3 { color: #273176; font-family: sans-serif; }
        div.stButton > button {
            background-color: #273176; color: white; width: 100%; height: 45px;
            font-weight: bold; border-radius: 8px; border: none;
        }
        div.stButton > button:hover { background-color: #1a2155; }
    </style>
    """, unsafe_allow_html=True)
    
import math

def calcular_tarifa_viaje(inputs, grupo_data):
    """
    Realiza el cálculo matemático de prorrateo y variables para obtener la tarifa final.
    """
    config = grupo_data.get("Configuracion_Operativa", {})
    variables = grupo_data.get("Costos_Variables", {})
    fijos_veh = grupo_data.get("Costos_Fijos_Vehiculo", {})
    fijos_op = grupo_data.get("Costos_Fijos_Operador", {})

    velocidad = float(config.get("Velocidad", 60))
    margen = float(config.get("Margen", 0.03))
    num_operadores = inputs.get("num_operadores", 1)

    # --- Variables por km ---
    combustible = float(variables.get("Combustible_Km", 0))
    bono = float(variables.get("Bono_Operador", 0)) * num_operadores 
    riesgo = float(variables.get("Factor_Riesgo", 0))
    km_arrendadora = float(variables.get("Km_Arrendadora", 0))
    
    costo_km_total = combustible + bono + riesgo + km_arrendadora

    # --- Fijos Mensuales ---
    total_fijo_veh = sum([float(v) for v in fijos_veh.values()])
    total_fijo_op = sum([float(v) for v in fijos_op.values()]) * num_operadores
    total_fijo_mensual = total_fijo_veh + total_fijo_op

    # --- Distancia y Tiempos Base ---
    distancia_total = inputs["distancia_ida"] * 2
    t_r = distancia_total / velocidad if velocidad > 0 else 0  # Tiempo de recorrido total
    t_c = inputs["horas_carga"]
    t_d = inputs["horas_descarga"]

    # --- Lógica NOM-087-SCT-2-2017 ---
    # Pausa de 30 min (0.5 hrs) por cada 5 horas de conducción
    t_p = math.floor(t_r / 5.0) * 0.5
    
    # Descanso de 8 horas por cada 14 horas de conducción
    # Si hay 2 o más operadores, el camión no se detiene a dormir (t_s = 0)
    if num_operadores >= 2:
        t_s = 0
    else:
        t_s = math.floor(t_r / 14.0) * 8.0

    # Tiempo de Ciclo Total (T_ciclo)
    horas_totales = t_r + t_c + t_d + t_p + t_s

    # --- Cálculos de Frecuencia (Base 144 hrs = 6 días laborales) ---
    if horas_totales > 0:
        viajes_semana_puros = 144.0 / horas_totales
    else:
        viajes_semana_puros = 0

    viajes_semana = round(viajes_semana_puros * 2) / 2
    
    viajes_mes_bruto = viajes_semana * 4.34 
    viajes_mes = round(viajes_mes_bruto * 2) / 2

    # --- Cálculos Financieros ---
    fijo_por_viaje = total_fijo_mensual / viajes_mes if viajes_mes > 0 else 0
    variable_km_viaje = distancia_total * costo_km_total
    
    casetas_totales = inputs["casetas"] * 2
    extras_viaje = casetas_totales + inputs["pension"] + inputs["maniobras"] + inputs["otros"]

    costo_total_base = fijo_por_viaje + variable_km_viaje + extras_viaje

    if inputs["modalidad"] == "Round trip":
        costo_total_viaje = costo_total_base * 1.60
    else:
        costo_total_viaje = costo_total_base

    precio_venta = costo_total_viaje / (1 - margen) if margen < 1 else costo_total_viaje

    return {
        "distancia_total": distancia_total,
        "horas_totales": round(horas_totales, 1),
        "viajes_semana": viajes_semana,
        "viajes_mes": viajes_mes,
        "fijo_mensual": round(total_fijo_mensual, 2),
        "fijo_por_viaje": round(fijo_por_viaje, 2),
        "variable_km_viaje": round(variable_km_viaje, 2),
        "extras_viaje": round(extras_viaje, 2),
        "costo_total": round(costo_total_viaje, 2),
        "precio_venta": round(precio_venta, 2),
        "margen_esperado": margen
    }