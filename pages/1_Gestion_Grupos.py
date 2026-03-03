import streamlit as st
import json
import pandas as pd
import time
from utils import obtener_grupos_operativos, gestionar_grupo_operativo, inyectar_css

@st.cache_data
def cargar_opciones_excel():
    try:
        df = pd.read_excel("Administrador_Cotizaciones.xlsx", sheet_name="Cotizacion_Rapida")
        unidades = sorted([str(x).strip() for x in df["TIPO DE UNIDAD"].dropna().unique() if str(x).strip() != '']) if "TIPO DE UNIDAD" in df.columns else []
        equipos = sorted([str(x).strip() for x in df["TIPO DE GRUPOS DE EQUIPO"].dropna().unique() if str(x).strip() != '']) if "TIPO DE GRUPOS DE EQUIPO" in df.columns else []
        rutas = sorted([str(x).strip() for x in df["TIPO DE RUTA"].dropna().unique() if str(x).strip() != '']) if "TIPO DE RUTA" in df.columns else []
        return unidades, equipos, rutas
    except Exception as e:
        st.error(f"⚠️ Error al leer Excel: {e}")
        return [], [], []

inyectar_css()
st.title("Gestión de Grupos Operativos")

tab1, tab2 = st.tabs(["➕ Crear Nuevo Grupo", "📋 Ver / Editar / Inactivar"])
opciones_unidad, opciones_equipo, opciones_ruta = cargar_opciones_excel()
usuario_actual = st.session_state.get("name", "Desconocido")

# ==========================================
# PESTAÑA 1: CREAR GRUPO
# ==========================================
with tab1:
    with st.form("form_crear_grupo", clear_on_submit=False):
        st.subheader("Datos Generales")
        col1, col2, col3 = st.columns(3)
        tipo_unidad = col1.selectbox("Tipo de Unidad", options=opciones_unidad, index=None, placeholder="Selecciona...", key="new_uni")
        tipo_equipo = col2.selectbox("Tipo de Equipo", options=opciones_equipo, index=None, placeholder="Selecciona...", key="new_equi")
        tipo_ruta = col3.selectbox("Tipo de Ruta", options=opciones_ruta, index=None, placeholder="Selecciona...", key="new_ruta")
        
        st.subheader("Configuración y Variables")
        col5, col6 = st.columns(2)
        with col5:
            vel_gobernada = st.number_input("Velocidad Gobernada (Km/hr)", value=60.0, key="new_vel")
            rendimiento = st.number_input("Rendimiento Promedio (Km/Lt)", value=2.5, key="new_rend")
            margen_porcentaje = st.number_input("Margen Objetivo (%)", value=3.0, step=0.5, format="%.2f", key="new_mar")
            horas_lab = st.number_input("Horas Laborales/Semana", value=48.0, step=1.0, key="new_h_lab")
            horas_ext = st.number_input("Horas Extra/Semana", value=0.0, step=1.0, key="new_h_ext")
            
        with col6:
            precio_combustible = st.number_input("Precio Combustible ($/Lt)", value=23.50, key="new_comb")
            bono_operador = st.number_input("Bono Operador $/km", value=5.35, key="new_bono")
            carga_fiscal = st.number_input("Carga Fiscal (%)", value=7.5, step=0.5, format="%.2f", key="new_fiscal")
            carga_social = st.number_input("Carga Social (%)", value=31.0, step=0.5, format="%.2f", key="new_social")
            factor_riesgo = st.number_input("Factor de Riesgo $/km", value=1.5, key="new_riesgo")
            km_arrendadora = st.number_input("Km Arrendadora $/km", value=1.25, key="new_kma")

        st.subheader("Costos Fijos Mensuales (Tablas Dinámicas)")
        st.info("💡 **Instrucciones:** Escribe en la fila inferior para agregar. Doble clic para editar. Selecciona la casilla izquierda y presiona **Suprimir** para eliminar.")
        
        col7, col8 = st.columns(2)
        with col7:
            st.markdown("**Vehículo**")
            df_def_veh = pd.DataFrame([
                {"Concepto": "Arrendamiento", "Monto ($)": 34870.05},
                {"Concepto": "Intereses", "Monto ($)": 14294.97},
                {"Concepto": "Seguro", "Monto ($)": 9542.28},
                {"Concepto": "Mantenimiento", "Monto ($)": 15441.55}
            ])
            df_vehiculo_final = st.data_editor(df_def_veh, num_rows="dynamic", width="stretch", key="grid_veh_new")
            
        with col8:
            st.markdown("**Operador**")
            df_def_op = pd.DataFrame([
                {"Concepto": "Sueldo", "Monto ($)": 9577.52},
                {"Concepto": "Prestaciones", "Monto ($)": 4884.54},
                {"Concepto": "Seguro RC", "Monto ($)": 250.00},
                {"Concepto": "Celular", "Monto ($)": 350.00}
            ])
            df_operador_final = st.data_editor(df_def_op, num_rows="dynamic", width="stretch", key="grid_op_new")

        submit_btn = st.form_submit_button("Guardar Grupo Operativo")

        if submit_btn:
            df_existentes = obtener_grupos_operativos()
            es_duplicado = False
            id_conflicto = ""
            
            if not df_existentes.empty:
                if 'Tipo_Ruta' not in df_existentes.columns:
                    df_existentes['Tipo_Ruta'] = ""
                df_existentes['Tipo_Ruta'] = df_existentes['Tipo_Ruta'].fillna("")
                ruta_str = tipo_ruta if tipo_ruta else ""
                
                duplicados = df_existentes[
                    (df_existentes['Estado'] == 'Activo') & 
                    (df_existentes['Tipo_Unidad'] == tipo_unidad) & 
                    (df_existentes['Tipo_Equipo'] == tipo_equipo) &
                    (df_existentes['Tipo_Ruta'] == ruta_str)
                ]
                if not duplicados.empty:
                    es_duplicado = True
                    id_conflicto = duplicados.iloc[0]['ID_Grupo']

            unidad_str = str(tipo_unidad).lower().replace("ó", "o").replace(" ", "") if tipo_unidad else ""
            equipo_str = str(tipo_equipo).lower().replace(" ", "") if tipo_equipo else ""

            if not tipo_unidad or not tipo_equipo or not tipo_ruta:
                st.error("⚠️ Por favor selecciona Unidad, Equipo y Ruta.")
            elif es_duplicado:
                st.error(f"❌ **Este grupo ya ha sido creado bajo el ID '{id_conflicto}'.**\n\nPor favor, dirígete a la pestaña 'Ver / Editar / Inactivar' para hacer cambios sobre ese registro en lugar de crear uno nuevo.")
            elif ("porta" in equipo_str or "chasis" in equipo_str) and ("tractocamion" not in unidad_str):
                st.error(f"❌ Error de compatibilidad: El equipo '{tipo_equipo}' NO se puede asignar a una unidad de tipo '{tipo_unidad}'. Solo se permite en Tractocamiones.")
            else:
                margen_decimal = margen_porcentaje / 100.0
                combustible_km = precio_combustible / rendimiento if rendimiento > 0 else 0
                
                config_op = {
                    "Velocidad": vel_gobernada, 
                    "Rendimiento": rendimiento, 
                    "Margen": margen_decimal,
                    "Horas_Laborales_Semana": horas_lab,
                    "Horas_Extra_Semana": horas_ext
                }
                
                costos_var = {
                    "Precio_Combustible": precio_combustible, 
                    "Combustible_Km": combustible_km, 
                    "Bono_Operador": bono_operador, 
                    "Carga_Fiscal": carga_fiscal,
                    "Carga_Social": carga_social,
                    "Factor_Riesgo": factor_riesgo, 
                    "Km_Arrendadora": km_arrendadora
                }
                
                df_vehiculo_limpio = df_vehiculo_final.dropna(subset=["Concepto", "Monto ($)"])
                fijos_vehiculo = dict(zip(df_vehiculo_limpio["Concepto"], df_vehiculo_limpio["Monto ($)"]))
                
                df_operador_limpio = df_operador_final.dropna(subset=["Concepto", "Monto ($)"])
                fijos_operador = dict(zip(df_operador_limpio["Concepto"], df_operador_limpio["Monto ($)"]))

                datos_fila = [
                    tipo_unidad, tipo_equipo, tipo_ruta,
                    json.dumps(config_op), json.dumps(costos_var), 
                    json.dumps(fijos_vehiculo), json.dumps(fijos_operador)
                ]

                with st.spinner("Guardando..."):
                    exito, msj = gestionar_grupo_operativo("crear_grupo", datos=datos_fila, usuario=usuario_actual)
                if exito:
                    st.success("✅ " + msj)
                    time.sleep(1.5)
                    st.rerun() 
                else:
                    st.error("❌ " + msj)

# ==========================================
# PESTAÑA 2: VER / EDITAR / INACTIVAR
# ==========================================
with tab2:
    col_ref, col_vacia = st.columns([1, 4])
    if col_ref.button("🔄 Refrescar Datos"):
        st.rerun()
        
    df_grupos = obtener_grupos_operativos()
    
    if not df_grupos.empty:
        columnas_mostrar = ['ID_Grupo', 'Estado', 'Tipo_Unidad', 'Tipo_Equipo']
        if 'Tipo_Ruta' in df_grupos.columns:
            columnas_mostrar.append('Tipo_Ruta')
            
        st.dataframe(df_grupos[columnas_mostrar], width="stretch")
        st.markdown("---")
        
        st.subheader("Gestionar Grupo Existente")
        
        # --- CAMBIO: Función para formatear el texto del dropdown ---
        def formato_grupo(id_g):
            fila = df_grupos[df_grupos['ID_Grupo'] == id_g].iloc[0]
            uni = fila.get('Tipo_Unidad', '')
            equi = fila.get('Tipo_Equipo', '')
            rut = fila.get('Tipo_Ruta', '')
            return f"{id_g} - {uni} | {equi} | {rut}"

        grupos_activos = df_grupos[df_grupos['Estado'] == 'Activo']['ID_Grupo'].tolist()
        
        # --- CAMBIO: Aplicamos el format_func ---
        id_a_gestionar = st.selectbox("Selecciona el Grupo a Editar o Inactivar:", grupos_activos, format_func=formato_grupo, index=None)
        
        if id_a_gestionar:
            grupo_data = df_grupos[df_grupos['ID_Grupo'] == id_a_gestionar].iloc[0]
            
            config_actual = grupo_data.get('Configuracion_Operativa', {})
            var_actual = grupo_data.get('Costos_Variables', {})
            fijo_veh_actual = grupo_data.get('Costos_Fijos_Vehiculo', {})
            fijo_op_actual = grupo_data.get('Costos_Fijos_Operador', {})

            idx_unidad = opciones_unidad.index(grupo_data['Tipo_Unidad']) if grupo_data['Tipo_Unidad'] in opciones_unidad else None
            idx_equipo = opciones_equipo.index(grupo_data['Tipo_Equipo']) if grupo_data['Tipo_Equipo'] in opciones_equipo else None
            ruta_actual = grupo_data.get('Tipo_Ruta', '')
            idx_ruta = opciones_ruta.index(ruta_actual) if ruta_actual in opciones_ruta else None

            st.markdown(f"### ✏️ Editando: `{id_a_gestionar}`")
            with st.form("form_editar_grupo"):
                st.subheader("Datos Generales")
                c1, c2, c3 = st.columns(3)
                
                tipo_unidad_ed = c1.selectbox("Tipo de Unidad", options=opciones_unidad, index=idx_unidad, key=f"ed_uni_{id_a_gestionar}")
                tipo_equipo_ed = c2.selectbox("Tipo de Equipo", options=opciones_equipo, index=idx_equipo, key=f"ed_equi_{id_a_gestionar}")
                tipo_ruta_ed = c3.selectbox("Tipo de Ruta", options=opciones_ruta, index=idx_ruta, key=f"ed_ruta_{id_a_gestionar}")
                
                st.subheader("Configuración y Variables")
                c5, c6 = st.columns(2)
                with c5:
                    vel_ed = st.number_input("Velocidad Gobernada (Km/hr)", value=float(config_actual.get("Velocidad", 60.0)), key=f"ed_vel_{id_a_gestionar}")
                    rend_ed = st.number_input("Rendimiento Promedio (Km/Lt)", value=float(config_actual.get("Rendimiento", 2.5)), key=f"ed_rend_{id_a_gestionar}")
                    margen_ed = st.number_input("Margen Objetivo (%)", value=float(config_actual.get("Margen", 0.03) * 100), step=0.5, format="%.2f", key=f"ed_mar_{id_a_gestionar}")
                    horas_lab_ed = st.number_input("Horas Laborales/Semana", value=float(config_actual.get("Horas_Laborales_Semana", 48.0)), step=1.0, key=f"ed_h_lab_{id_a_gestionar}")
                    horas_ext_ed = st.number_input("Horas Extra/Semana", value=float(config_actual.get("Horas_Extra_Semana", 0.0)), step=1.0, key=f"ed_h_ext_{id_a_gestionar}")

                with c6:
                    rend_actual = float(config_actual.get("Rendimiento", 2.5))
                    comb_km_actual = float(var_actual.get("Combustible_Km", 11.25))
                    precio_base_actual = float(var_actual.get("Precio_Combustible", comb_km_actual * rend_actual))
                    
                    precio_comb_ed = st.number_input("Precio Combustible ($/Lt)", value=precio_base_actual, key=f"ed_comb_{id_a_gestionar}")
                    bono_ed = st.number_input("Bono Operador $/km", value=float(var_actual.get("Bono_Operador", 5.35)), key=f"ed_bono_{id_a_gestionar}")
                    fiscal_ed = st.number_input("Carga Fiscal (%)", value=float(var_actual.get("Carga_Fiscal", 7.5)), step=0.5, format="%.2f", key=f"ed_fiscal_{id_a_gestionar}")
                    social_ed = st.number_input("Carga Social (%)", value=float(var_actual.get("Carga_Social", 31.0)), step=0.5, format="%.2f", key=f"ed_social_{id_a_gestionar}")
                    riesgo_ed = st.number_input("Factor de Riesgo $/km", value=float(var_actual.get("Factor_Riesgo", 1.5)), key=f"ed_riesgo_{id_a_gestionar}")
                    kma_ed = st.number_input("Km Arrendadora $/km", value=float(var_actual.get("Km_Arrendadora", 1.25)), key=f"ed_kma_{id_a_gestionar}")

                st.subheader("Costos Fijos Mensuales (Tablas Dinámicas)")
                c7, c8 = st.columns(2)
                
                df_veh_edit_base = pd.DataFrame(list(fijo_veh_actual.items()), columns=["Concepto", "Monto ($)"])
                df_op_edit_base = pd.DataFrame(list(fijo_op_actual.items()), columns=["Concepto", "Monto ($)"])

                with c7:
                    st.markdown("**Vehículo**")
                    df_veh_ed_final = st.data_editor(df_veh_edit_base, num_rows="dynamic", width="stretch", key=f"grid_veh_ed_{id_a_gestionar}")
                with c8:
                    st.markdown("**Operador**")
                    df_op_ed_final = st.data_editor(df_op_edit_base, num_rows="dynamic", width="stretch", key=f"grid_op_ed_{id_a_gestionar}")

                submit_ed = st.form_submit_button("💾 Guardar Cambios")

                if submit_ed:
                    es_duplicado_ed = False
                    id_conflicto_ed = ""
                    
                    if not df_grupos.empty:
                        if 'Tipo_Ruta' not in df_grupos.columns:
                            df_grupos['Tipo_Ruta'] = ""
                        df_grupos['Tipo_Ruta'] = df_grupos['Tipo_Ruta'].fillna("")
                        ruta_str_ed = tipo_ruta_ed if tipo_ruta_ed else ""
                        
                        duplicados_ed = df_grupos[
                            (df_grupos['Estado'] == 'Activo') & 
                            (df_grupos['Tipo_Unidad'] == tipo_unidad_ed) & 
                            (df_grupos['Tipo_Equipo'] == tipo_equipo_ed) &
                            (df_grupos['Tipo_Ruta'] == ruta_str_ed) &
                            (df_grupos['ID_Grupo'] != id_a_gestionar)
                        ]
                        if not duplicados_ed.empty:
                            es_duplicado_ed = True
                            id_conflicto_ed = duplicados_ed.iloc[0]['ID_Grupo']

                    unidad_str_ed = str(tipo_unidad_ed).lower().replace("ó", "o").replace(" ", "") if tipo_unidad_ed else ""
                    equipo_str_ed = str(tipo_equipo_ed).lower().replace(" ", "") if tipo_equipo_ed else ""

                    if not tipo_unidad_ed or not tipo_equipo_ed or not tipo_ruta_ed:
                        st.error("⚠️ Por favor selecciona Unidad, Equipo y Ruta.")
                    elif es_duplicado_ed:
                        st.error(f"❌ ¡No puedes cambiar este grupo a esa combinación! El grupo '{id_conflicto_ed}' ya la está usando.")
                    elif ("porta" in equipo_str_ed or "chasis" in equipo_str_ed) and ("tractocamion" not in unidad_str_ed):
                        st.error(f"❌ Error de compatibilidad: El equipo '{tipo_equipo_ed}' NO se puede asignar a una unidad de tipo '{tipo_unidad_ed}'. Solo se permite en Tractocamiones.")
                    else:
                        margen_decimal_ed = margen_ed / 100.0
                        combustible_km_ed = precio_comb_ed / rend_ed if rend_ed > 0 else 0
                        
                        config_op_nuevo = {
                            "Velocidad": vel_ed, 
                            "Rendimiento": rend_ed, 
                            "Margen": margen_decimal_ed,
                            "Horas_Laborales_Semana": horas_lab_ed,
                            "Horas_Extra_Semana": horas_ext_ed
                        }
                        
                        costos_var_nuevo = {
                            "Precio_Combustible": precio_comb_ed, 
                            "Combustible_Km": combustible_km_ed, 
                            "Bono_Operador": bono_ed, 
                            "Carga_Fiscal": fiscal_ed,
                            "Carga_Social": social_ed,
                            "Factor_Riesgo": riesgo_ed, 
                            "Km_Arrendadora": kma_ed
                        }
                        
                        df_veh_ed_limpio = df_veh_ed_final.dropna(subset=["Concepto", "Monto ($)"])
                        fijos_veh_nuevo = dict(zip(df_veh_ed_limpio["Concepto"], df_veh_ed_limpio["Monto ($)"]))
                        
                        df_op_ed_limpio = df_op_ed_final.dropna(subset=["Concepto", "Monto ($)"])
                        fijos_op_nuevo = dict(zip(df_op_ed_limpio["Concepto"], df_op_ed_limpio["Monto ($)"]))

                        datos_fila_ed = [
                            tipo_unidad_ed, tipo_equipo_ed, tipo_ruta_ed,
                            json.dumps(config_op_nuevo), json.dumps(costos_var_nuevo), 
                            json.dumps(fijos_veh_nuevo), json.dumps(fijos_op_nuevo)
                        ]

                        with st.spinner("Actualizando..."):
                            exito, msj = gestionar_grupo_operativo("editar_grupo", datos=datos_fila_ed, id_grupo=id_a_gestionar, usuario=usuario_actual)
                        
                        if exito:
                            st.success("✅ Información actualizada. Refrescando pantalla...")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("❌ " + msj)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⚠️ Inactivar este Grupo", type="primary"):
                exito, msj = gestionar_grupo_operativo("inactivar_grupo", id_grupo=id_a_gestionar, usuario=usuario_actual)
                if exito:
                    st.success(f"✅ Grupo {id_a_gestionar} inactivado.")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("❌ " + msj)
    else:
        st.info("No hay grupos registrados o hubo un error de conexión.")