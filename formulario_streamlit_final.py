import requests
import streamlit as st
import pandas as pd
import io
from io import BytesIO
import re
import os
import pickle
import copy
import datetime


# --- Login simple (sin base de datos)
USUARIO = "pedro"
CLAVE = "1234"

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    with st.form("login_form"):
        st.subheader("🔐 Iniciar sesión")
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        ingresar = st.form_submit_button("Ingresar")
        
        if ingresar:
            if usuario == USUARIO and clave == CLAVE:
                st.session_state.autenticado = True
                st.success("Acceso concedido.")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    st.stop()  # Detiene la ejecución si no está logueado


# 🔄 Convertir el diccionario respuestas anidado en una lista de DataFrames
from pandas import json_normalize
PROGRESO_FILE = "progreso_usuario.pkl"

# ✅ Carga segura del progreso guardado (filtra claves conflictivas)
if os.path.exists(PROGRESO_FILE):
    try:
        with open(PROGRESO_FILE, "rb") as f:
            estado_guardado = pickle.load(f)
            for k, v in estado_guardado.items():
                if (
                    not k.startswith("delete_")
                    and not k.startswith("eliminar_cultivo_")
                    and not k.startswith("FormSubmitter:")
                    and "Agregar Cultivo" not in k
                ):
                    if k not in st.session_state:
                        st.session_state[k] = v
        # st.success("🟢 Progreso cargado automáticamente.")
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar el progreso: {e}")



# Crear Tabs principales 
@st.cache_data(ttl=86400, show_spinner=False )
def obtener_provincias_y_localidades():
    url = "https://apis.datos.gob.ar/georef/api/provincias"
    response = requests.get(url)
    provincias = response.json()["provincias"]
    provincias.sort(key=lambda x: x["nombre"])

    prov_localidades = {}
    for prov in provincias:
        prov_name = prov["nombre"]
        loc_url = f"https://apis.datos.gob.ar/georef/api/localidades?provincia={prov_name}&max=5000"
        loc_resp = requests.get(loc_url)
        if loc_resp.status_code == 200:
            localidades = loc_resp.json()["localidades"]
            nombres_localidades = [loc["nombre"] for loc in localidades]
            nombres_localidades.sort()
            prov_localidades[prov_name] = nombres_localidades
        else:
            prov_localidades[prov_name] = []

    return provincias, prov_localidades

def seleccionar_provincia_y_localidad(key_prov, key_loc):
    _, prov_localidades = obtener_provincias_y_localidades()
    lista_provincias = list(prov_localidades.keys())

    provincia_seleccionada = st.selectbox("Provincia", lista_provincias, key=key_prov)
    localidades = prov_localidades.get(provincia_seleccionada, [])
    localidad_seleccionada = st.selectbox("Localidad", localidades, key=key_loc)

    return provincia_seleccionada, localidad_seleccionada

from PIL import Image
from pathlib import Path

# Ruta base: carpeta del script
base_path = Path(__file__).parent

# Imagen que debería estar junto al .py
img_path = base_path / "logo2QTM.png"

# Si existe, la mostramos
if img_path.exists():
    imagen = Image.open(img_path)
    st.image(imagen)
else:
    st.error("No se encuentra la imagen en la ruta esperada.")

tabs = st.tabs([
    "**Información General**",
    "**Deudas Bancarias y Financieras**",
    "**Ventas y Compras**",
    "**Manifestación de Bienes**",
    "**Adicional Empresas Agro.**"
])

# Diccionario para guardar respuestas
if "respuestas" not in st.session_state:
    st.session_state.respuestas = {}

# ---- TAB 1: Información General ----

with tabs[0]:
    
    # --- BLOQUE COMPLETO para IDENTIFICACION SOCIO/TERCERO PARTICIPE ---
    with st.expander("**Datos de Socio / Tercero Participe**"):

        st.session_state.respuestas["Razón Social / Nombre y apellido"] = st.text_input(
            "Razón Social / Nombre y apellido", key="Razón Social / Nombre y apellido")
        # --- NOTA ---
        st.caption("*(según Estatuto, Contrato Social o DNI)*")


        col1, col2, col3 = st.columns(3)
        with col1:
           # Cargar valor actual desde session_state o usar hoy
            valor_actual = st.session_state.get("Fecha de Inscripción en IGJ", datetime.date.today())
            if isinstance(valor_actual, str):
                try:
                    valor_actual = datetime.datetime.strptime(valor_actual, "%Y-%m-%d").date()
                except:
                    valor_actual = datetime.date.today()

            # Mostrar selector de fecha con valor controlado
            fecha_igj = st.date_input(
                "Fecha de Inscripción en IGJ",
                value=valor_actual,
                key="fecha_igj",
                format="YYYY-MM-DD"
            )

            # Guardar como string formateado
            st.session_state.respuestas["Fecha de Inscripción en IGJ"] = fecha_igj.strftime("%Y-%m-%d")
        with col2:
            st.session_state.respuestas["CUIT"] = st.text_input("CUIT",key="CUIT")
            # Validar CUIT
            if st.session_state.respuestas["CUIT"] and not re.match(r'^\d{11}$', st.session_state.respuestas["CUIT"]):
                st.warning("CUIT inválido. Debe tener 11 dígitos.")
        with col3:
            st.session_state.respuestas["Teléfono"] = st.text_input("Teléfono", key="Teléfono")
        st.markdown("---")

        st.markdown("### Declaración de Domicilios")

        provincias_dicts, localidades_por_provincia = obtener_provincias_y_localidades()
        nombres_provincias = [prov["nombre"] for prov in provincias_dicts]

        st.markdown("**Domicilio real y legal**")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.respuestas["Calle (real y legal)"] = st.text_input("Calle", key="real y legal1")
        with col2:
            st.session_state.respuestas["Número (real y legal)"] = st.text_input("Número", key="real y legal2")
        with col3:
            st.session_state.respuestas["CP (real y legal)"] = st.text_input("CP (8 Dígitos)", key="real y legal3")
        
        col4, col5 = st.columns(2)
        with col4:
            prov_real = st.selectbox("Provincia", nombres_provincias, key="prov_real")
        with col5:
            loc_real = st.selectbox("Localidad", localidades_por_provincia.get(prov_real, []), key="loc_real")

        st.session_state.respuestas["Provincia (real y legal)"] = prov_real
        st.session_state.respuestas["Localidad (real y legal)"] = loc_real

        st.markdown("---")

        # --- Domicilio Comercial ---
        st.markdown("**Domicilio comercial**")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.respuestas["Calle (comercial)"] = st.text_input("Calle", key="comercial1")
        with col2:
            st.session_state.respuestas["Número (comercial)"] = st.text_input("Número", key="comercial2")
        with col3:
            st.session_state.respuestas["CP (comercial)"] = st.text_input("CP (8 Dígitos)", key="comercial3")

        col4, col5 = st.columns(2)
        with col4:
            provincia_comercial = st.selectbox("Provincia", [prov["nombre"] for prov in provincias_dicts], key="comercial_prov")
        with col5:
            localidad_comercial = st.selectbox("Localidad", localidades_por_provincia.get(provincia_comercial, []), key="comercial_loc")

        st.session_state.respuestas["Provincia (comercial)"] = provincia_comercial
        st.session_state.respuestas["Localidad (comercial)"] = localidad_comercial

        st.markdown("---")

        # --- Domicilio Constituido ---
        st.markdown("**Domicilio constituido**")
        st.caption("*(Domicilio declarado para recibir notificaciones, en el ámbito de la capital de la provincia donde se encuentra radicada la empresa, y que será reflejado en el contrato de garantía y de fianza.*")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.respuestas["Calle (constituido)"] = st.text_input("Calle", key="constituido1")
        with col2:
            st.session_state.respuestas["Número (constituido)"] = st.text_input("Número", key="constituido2")
        with col3:
            st.session_state.respuestas["CP (constituido)"] = st.text_input("CP (8 Dígitos)", key="constituido3")

        col4, col5 = st.columns(2)
        with col4:
            provincia_constituido = st.selectbox("Provincia", [prov["nombre"] for prov in provincias_dicts], key="constituido_prov")
        with col5:
            localidad_constituido = st.selectbox("Localidad", localidades_por_provincia.get(provincia_constituido, []), key="constituido_loc")

        st.session_state.respuestas["Provincia (constituido)"] = provincia_constituido
        st.session_state.respuestas["Localidad (constituido)"] = localidad_constituido

        st.session_state.respuestas["Electrónico (constituido)"] = st.text_input(
            "Electrónico",
            help="Correo electrónico asociado a este domicilio constituido", key="constituido6"
        )

        st.markdown("---")

        # --- Otros campos ---

        col1, col2 = st.columns(2)
        with col1:
            st.session_state.respuestas["Página web empresarial"] = st.text_input("Página web empresarial", key="Página web empresarial")
        with col2:
            st.session_state.respuestas["E-mail"] = st.text_input("E-mail", key="E-mail")

        col3, col4 = st.columns(2)
        with col3:
            st.session_state.respuestas["Cantidad de empleados declarados al cierre del último ejercicio"] = st.text_input(
            "Cantidad de empleados  al cierre del último ejercicio", key="Cantidad de empleados declarados al cierre del último ejercicio"
        )
        with col4:
            # --- Actividad Principal ---
            st.session_state.respuestas["Código de la actividad principal (AFIP según CLAE)"] = st.text_input(
            "Código de la actividad principal (AFIP según CLAE)",key="Código de la actividad principal (AFIP según CLAE)"
        )
        st.session_state.respuestas["Descripción de la actividad principal (AFIP según CLAE)"] = st.text_input(
            "Descripción de la actividad principal (AFIP según CLAE)", key="Descripción de la actividad principal (AFIP según CLAE)"
        )

        # --- Condición de IIBB y Ganancias ---
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.respuestas["Condición de IIBB"] = st.text_input("Condición de IIBB", key="Condición de IIBB")
            st.session_state.respuestas["Condición de ganancias"] = st.text_input("Condición de ganancias",key="Condición de ganancias")
        with col2:
            st.session_state.respuestas["N° de IIBB"] = st.text_input("N° de IIBB", key="N° de IIBB")
            st.session_state.respuestas["Sede de IIBB"] = st.text_input("Sede de IIBB", key="Sede de IIBB")

        # --- Contacto ---
        st.markdown("**Contacto:**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.session_state.respuestas["Apellido y Nombre "] = st.text_input("Apellido y Nombre ", key="Apellido y Nombre ")
        with col2:
            st.session_state.respuestas["Cargo "] = st.text_input("Cargo ", key="Cargo ")
        with col3:
            st.session_state.respuestas["TEL / CEL "] = st.text_input("TEL / CEL ", key="TEL / CEL ")
        with col4:
            st.session_state.respuestas["Mail "] = st.text_input("Mail ", key="Mail ")
    
    with st.expander("**Breve Reseña de la Empresa**"):
        st.session_state.respuestas["Reseña Empresa"] = st.text_area("Describa la actividad de la empresa",
                                                    placeholder="Por favor explayarse un poco y completar en este recuadro, explicar el desarrollo de la actividad de la empresa, los productos que comercializa, sector y mercado en el que se desenvuelve, zona de influencia, ¡Ya que es muy importante para que la SGR tenga conocimiento sobre la empresa!",
                                                    key= "Describa la actividad de la empresa")
    
    # ------------------ TIPO DE AVAL Y CONTRAGARANTIA ------------------
    with st.expander("**Tipo de Aval y Contragarantía**"):
        st.write("Solicito la incorporación como socio/tercero partícipe y un aval para el/los siguientes productos y las contragarantías ofrecidas:")

        opciones_tipo_aval = [
            "Completar", "Descuento CPD Propios",
            "Descuento CPD Terceros", "Aval bancario",
            "Aval pagaré bursátil", "Aval leasing",
            "Aval ON Simplificada", "Otros"
        ]

        opciones_tipo_contragarantia = [
            "Completar", "Fianza de socios/accionistas",
            "Fianza de cónyuge", "Fianza de Terceros",
            "Hipoteca", "Prenda de Bonos", "Otras (detallar)"
        ]

        if "avales" not in st.session_state:
            st.session_state.avales = []
        

        with st.form(key="form_agregar_aval"):
            st.markdown("**Agregar nuevo aval y contragarantía**")

            col1, col2 = st.columns(2)
            tipo_aval = col1.selectbox("Tipo de Aval", opciones_tipo_aval, key="nuevo_tipo_aval")
            detalle_aval = col2.text_input("Detalle Aval (si corresponde)", key="nuevo_detalle_aval")

            col3, col4 = st.columns(2)
            monto = col3.number_input("Monto solicitado (ARS)", min_value=0, key="nuevo_monto")
            tipo_contragarantia = col4.selectbox("Tipo de Contragarantía", opciones_tipo_contragarantia, key="nuevo_tipo_contragarantia")

            detalle_contragarantia = st.text_input("Detalle Contragarantía (si corresponde)", key="nuevo_detalle_contragarantia")

            submit_aval = st.form_submit_button("Agregar Aval")

        if submit_aval:
            st.session_state.avales.append({
                "Tipo Aval": tipo_aval,
                "Detalle Aval": detalle_aval if tipo_aval == "Otros" else "",
                "Monto": monto,
                "Tipo Contragarantía": tipo_contragarantia,
                "Detalle Contragarantía": detalle_contragarantia if tipo_contragarantia == "Otras (detallar)" else ""
            })
            st.success("✅ Aval agregado correctamente.")
            st.rerun()

        # Mostrar resumen
        if st.session_state.avales:
            st.markdown("**Resumen de Avales cargados**")

            columnas_fijas = [
                "Tipo Aval", "Detalle Aval", "Monto",
                "Tipo Contragarantía", "Detalle Contragarantía"
            ]
            df_avales = pd.DataFrame(st.session_state.avales)

            for col in columnas_fijas:
                if col not in df_avales.columns:
                    df_avales[col] = ""

            df_avales = df_avales[columnas_fijas]

            # ✅ Cálculo del total con tu variable
            total_monto = sum([a.get("Monto", 0) for a in st.session_state.avales])
            df_avales["Total solicitado"] = total_monto

            st.dataframe(df_avales)
            st.markdown(f"**Total Solicitado:** ARS {total_monto:,}")

            cols_aval = st.columns(4)
            for i, fila in enumerate(st.session_state.avales):
                col = cols_aval[i % 4]
                with col:
                    if st.button(f"❌ {fila["Tipo Aval"]} - {fila["Tipo Contragarantía"]}", key=f"delete_aval_{i}"):
                        st.session_state.avales.pop(i)
                        st.rerun()

        

        if st.session_state.avales:
            df = pd.DataFrame(st.session_state.avales)
            df["Total solicitado"] = total_monto
            #st.write("Vista previa:", df)

        destino = st.text_area(
            "**Destino de los fondos**",
            key="Destino de los fondos",
            placeholder="Describa brevemente el destino de los fondos solicitados."
        )

        st.session_state.respuestas["Avales y Contragarantías"] = st.session_state.avales
        st.session_state.respuestas["Destino de los fondos"] = destino
        
    
    
    # ------------------ DATOS FILIATORIOS ------------------
    with st.expander("**Datos Filiatorios**"):
        st.caption("*Información de los miembros del Directorio/ Titulares/ Socios Gerentes*")

        # Listas de opciones basadas en tu imagen
        opciones_cargo = ["COMPLETAR", "SOCIO GERENTE", "DIRECTOR", "SOCIO", "ACCIONISTA","PRESIDENTE","VICEPRESIDENTE","APODERADO"]
        opciones_estado_civil = ["COMPLETAR", "SOLTERO", "CASADO", "DIVORCIADO"]
        opciones_fiador = ["SI", "NO"]

        if "filiatorios" not in st.session_state:
            st.session_state.filiatorios = []

        total_actual = sum(f.get("% Participación", 0) for f in st.session_state.filiatorios)

        with st.form(key="form_agregar_filiatorio"):
            st.markdown("**Agregar nuevo integrante**")
            st.caption(f"Suma actual: {total_actual}% (debe completar hasta llegar a **100%**)")

            col1, col2 = st.columns(2)
            nombre_apellido = col1.text_input("Nombre y Apellido", key="nuevo_nombre_apellido")
            cuit_cuil = col2.text_input("CUIT / CUIL (11 dígitos)", key="nuevo_cuit")

            col3, col4 = st.columns(2)
            cargo = col3.selectbox("Cargo", opciones_cargo, key="nuevo_cargo")
            participacion = col4.number_input("% Participación", min_value=0.0, max_value=100.0 - total_actual, key="nuevo_participacion")

            col5, col6 = st.columns(2)
            estado_civil = col5.selectbox("Estado Civil", opciones_estado_civil, key="nuevo_estado_civil")
            conyuge = col6.text_input("Nombre y Apellido del Cónyuge", key="nuevo_conyuge")

            fiador = st.selectbox("Fiador", opciones_fiador, key="nuevo_fiador")
            #fecha_nacimiento = st.date_input("Fecha de Nacimiento (opcional)", key="nuevo_fecha_nac")

            submit_filiatorio = st.form_submit_button("Agregar integrante")

        if submit_filiatorio:
            errores = []

            if not nombre_apellido.strip():
                errores.append("El campo 'Nombre y Apellido' es obligatorio.")

            if not re.match(r'^\d{11}$', cuit_cuil.strip()):
                errores.append("CUIT/CUIL inválido. Debe tener exactamente 11 dígitos numéricos.")

            if total_actual + participacion > 100:
                errores.append(f"La suma de participación no puede superar el 100%. Ya tenés {total_actual}%.")

            if errores:
                for err in errores:
                    st.error(f"❌ {err}")
            else:
                st.session_state.filiatorios.append({
                    "Nombre y Apellido": nombre_apellido.strip(),
                    "CUIT / CUIL": cuit_cuil.strip(),
                    "Cargo": cargo,
                    "% Participación": participacion,
                    "Estado Civil": estado_civil,
                    "Nombre Cónyuge": conyuge.strip(),
                    "Fiador": fiador
                })
                st.success("✅ Integrante agregado correctamente.")
                st.rerun()

        if st.session_state.filiatorios:
            st.markdown("### Integrantes cargados")
            df_filiarorio = pd.DataFrame(st.session_state.filiatorios)
            columnas_fijas = ["Nombre y Apellido", "CUIT / CUIL", "Cargo", "% Participación", "Estado Civil", "Nombre Cónyuge", "Fiador"]
            for col in columnas_fijas:
                if col not in df_filiarorio.columns:
                    df_filiarorio[col] = ""

            df_filiarorio = df_filiarorio[columnas_fijas]
            st.dataframe(df_filiarorio)

            cols_filiatorios = st.columns(4)
            for idx, fila in enumerate(st.session_state.filiatorios):
                col = cols_filiatorios[idx % 4]
                with col:
                    nombre = fila["Nombre y Apellido"]
                    if st.button(f"❌ Eliminar {nombre}", key=f"delete_filiatorio_{idx}"):
                        st.session_state.filiatorios.pop(idx)
                        st.rerun()

            total_final = df_filiarorio["% Participación"].sum()
            if total_final < 100:
                st.warning(f"⚠️ La suma actual es {total_final}%. Debe llegar exactamente a 100% para continuar.")
            elif total_final == 100:
                st.success("✅ Participación completada correctamente 100%. Podés continuar con el formulario.")
            else:
                st.error(f"❌ Error: la suma total es {total_final}%. Supera el 100%. Hay que corregir los valores.")
        else:
            df_filiarorio = pd.DataFrame([{
                "Nombre y Apellido": "",
                "CUIT / CUIL": "",
                "Cargo": "",
                "% Participación": 0,
                "Estado Civil": "",
                "Nombre Cónyuge": "",
                "Fiador": ""                
            }])

    # ------------------ DECLARACION DE EMPRESAS VINCULADAS ------------------
    with st.expander("**Declaración de Empresas Vinculadas**"):
        st.markdown("**Empresas Controlantes (50% Participación accionaria Ascendente)**")
        if "empresas_controlantes" not in st.session_state:
            st.session_state.empresas_controlantes = []

        with st.form("form_empresa_controlante"):
            col1, col2 = st.columns(2)
            razon_social_ctrl = col1.text_input("Razón Social", key="nuevo_ctrl_rs")
            cuit_ctrl = col2.text_input("CUIT (11 dígitos)", key="nuevo_ctrl_cuit")

            
            col3, col4 = st.columns(2)
            participacion_ctrl = col3.number_input("% de Participación", min_value=0.0, max_value=100.0, key="nuevo_ctrl_part")
            codigo_ctrl = col4.text_input("Código de la actividad principal", key="nuevo_ctrl_cod")

            submit_ctrl = st.form_submit_button("Agregar Empresa Controlante")

        if submit_ctrl:
            errores = []

            participacion_total = sum(e.get("% de Participación", 0) for e in st.session_state.empresas_controlantes)
            nueva_total = participacion_total + participacion_ctrl

            if not razon_social_ctrl.strip():
                errores.append("❌ La razón social es obligatoria.")
            if not re.match(r"^\d{11}$", cuit_ctrl.strip()):
                errores.append("❌ El CUIT debe tener exactamente 11 dígitos numéricos.")
            if nueva_total > 100:
                errores.append(f"❌ La suma total de participación excede el 100%. Ya tenés {participacion_total:.2f}%.")

            if errores:
                for err in errores:
                    st.error(err)
            else:
                st.session_state.empresas_controlantes.append({
                    "Razón Social": razon_social_ctrl.strip(),
                    "CUIT": cuit_ctrl.strip(),
                    "% de Participación": participacion_ctrl,
                    "Código de la actividad principal": codigo_ctrl.strip()
                })
                st.success("✅ Empresa controlante agregada.")
                st.rerun()

        if st.session_state.empresas_controlantes:
            df_empresas_controlantes = pd.DataFrame(st.session_state.empresas_controlantes)
            st.dataframe(df_empresas_controlantes)

            for i in range(0, len(st.session_state.empresas_controlantes), 4):
                cols = st.columns(4)
                for j, idx in enumerate(range(i, min(i+4, len(st.session_state.empresas_controlantes)))):
                    nombre = st.session_state.empresas_controlantes[idx]["Razón Social"]
                    with cols[j]:
                        if st.button(f"❌ Eliminar {nombre}", key=f"delete_emp_ctrl_{idx}"):
                            st.session_state.empresas_controlantes.pop(idx)
                            st.rerun()
        else:
            df_empresas_controlantes = pd.DataFrame([{
                "Razón Social": "",
                "CUIT": "",
                "% de Participación": 0,
                "Código de la actividad principal": ""
            }])

        st.markdown("---")
        st.markdown("### Empresas Vinculadas (> 20% participación accionaria)")

        if "empresas_vinculadas" not in st.session_state:
            st.session_state.empresas_vinculadas = []

        with st.form("form_empresa_vinculada"):
            col1, col2 = st.columns(2)
            razon_social_vinc = col1.text_input("Razón Social", key="nuevo_vinc_rs")
            cuit_vinc = col2.text_input("CUIT (11 dígitos)", key="nuevo_vinc_cuit")

            
            col3, col4 = st.columns(2)
            participacion_vinc = col3.number_input("% de Participación", min_value=0.0, max_value=100.0, key="nuevo_vinc_part")
            codigo_vinc = col4.text_input("Código de la actividad principal", key="nuevo_vinc_cod")

            submit_vinc = st.form_submit_button("Agregar Empresa Vinculada")

        if submit_vinc:
            errores = []
            
            participacion_total_v = sum(e.get("% de Participación", 0) for e in st.session_state.empresas_vinculadas)
            nueva_total_v = participacion_total_v + participacion_vinc
            
            if not razon_social_vinc.strip():
                errores.append("❌ La razón social es obligatoria.")
            if not re.match(r"^\d{11}$", cuit_vinc.strip()):
                errores.append("❌ El CUIT debe tener exactamente 11 dígitos numéricos.")
            if nueva_total_v > 100:
                errores.append(f"❌ La suma total de participación excede el 100%. Ya tenés {participacion_total:.2f}%.")

            if errores:
                for err in errores:
                    st.error(err)
            else:
                st.session_state.empresas_vinculadas.append({
                    "Razón Social": razon_social_vinc.strip(),
                    "CUIT": cuit_vinc.strip(),
                    "% de Participación": participacion_vinc,
                    "Código de la actividad principal": codigo_vinc.strip()
                })
                st.success("✅ Empresa vinculada agregada.")
                st.rerun()

        if st.session_state.empresas_vinculadas:
            df_empresas_vinculadas = pd.DataFrame(st.session_state.empresas_vinculadas)
            st.dataframe(df_empresas_vinculadas)

            for i in range(0, len(st.session_state.empresas_vinculadas), 4):
                cols = st.columns(4)
                for j, idx in enumerate(range(i, min(i+4, len(st.session_state.empresas_vinculadas)))):
                    nombre = st.session_state.empresas_vinculadas[idx]["Razón Social"]
                    with cols[j]:
                        if st.button(f"❌ Eliminar {nombre}", key=f"delete_emp_vinc_{idx}"):
                            st.session_state.empresas_vinculadas.pop(idx)
                            st.rerun()
        else:
            df_empresas_vinculadas = pd.DataFrame([{
                "Razón Social": "",
                "CUIT": "",
                "% de Participación": 0,
                "Código de la actividad principal": ""
            }])

    # ------------------ PRINCIPALES LIBRADORES A DESCONTAR ------------------
    with st.expander("**Principales Libradores a Descontar**"):
        st.caption("Aplicable para línea de descuento de Cheque de Pago Diferido (CPD) de Terceros")

        opciones_tipo = ["COMPLETAR", "PRINCIPAL CLIENTE", "LIBRADOR A DESCONTAR"]
        opciones_modalidad = ["COMPLETAR", "CONTADO", "30 DIAS", "45 DIAS", "60 DIAS", "90 DIAS", "120 DIAS", "180 DIAS", "MAS DE 180 DIAS", "365 DIAS"]
        opciones_descuenta = ["COMPLETAR", "SI", "NO"]

        if "clientes_descontar" not in st.session_state:
            st.session_state.clientes_descontar = []

        with st.form("form_cliente_librador"):
            st.markdown("**Agregar nuevo cliente / librador**")

            col1, col2 = st.columns(2)
            denominacion = col1.text_input("Denominación", key="nuevo_cl_deno")
            cuit = col2.text_input("CUIT (11 dígitos)", key="nuevo_cl_cuit")

            col3, col4, col5 = st.columns(3)
            tipo = col3.selectbox("Tipo", opciones_tipo, key="nuevo_cl_tipo")
            modalidad = col4.selectbox("Modalidad de Cobro", opciones_modalidad, key="nuevo_cl_modalidad")
            descuenta = col5.selectbox("Descuenta de Cheques", opciones_descuenta, key="nuevo_cl_desc")

            submit_cliente = st.form_submit_button("Agregar Cliente/Librador")

        if submit_cliente:
            errores = []
            if not denominacion.strip():
                errores.append("❌ La denominación es obligatoria.")
            if not re.match(r"^\d{11}$", cuit.strip()):
                errores.append("❌ El CUIT debe tener exactamente 11 dígitos numéricos.")

            if errores:
                for err in errores:
                    st.error(err)
            else:
                st.session_state.clientes_descontar.append({
                    "Denominación": denominacion.strip(),
                    "CUIT": cuit.strip(),
                    "Tipo": tipo,
                    "Modalidad de Cobro": modalidad,
                    "Descuenta de Cheques": descuenta
                })
                st.success("✅ Cliente/Librador agregado correctamente.")
                st.rerun()

        # Mostrar y gestionar tabla
        if st.session_state.clientes_descontar:
            st.markdown("### Clientes/Libradores cargados")
            df_clientes_descontar = pd.DataFrame(st.session_state.clientes_descontar)

            columnas_fijas = ["Denominación", "CUIT", "Tipo", "Modalidad de Cobro", "Descuenta de Cheques"]
            for col in columnas_fijas:
                if col not in df_clientes_descontar.columns:
                    df_clientes_descontar[col] = ""
            df_clientes_descontar = df_clientes_descontar[columnas_fijas]
            st.dataframe(df_clientes_descontar)

            filas_por_fila = 4
            botones = []
            for i, fila in enumerate(st.session_state.clientes_descontar):
                nombre = fila["Denominación"]
                botones.append((i, nombre))
            for i in range(0, len(botones), filas_por_fila):
                cols = st.columns(filas_por_fila)
                for j, (idx, nombre) in enumerate(botones[i:i + filas_por_fila]):
                    with cols[j]:
                        if st.button(f"❌ Eliminar {nombre}", key=f"delete_cl_desc_{idx}"):
                            st.session_state.clientes_descontar.pop(idx)
                            st.rerun()
        else:
            df_clientes_descontar = pd.DataFrame([{
                "Denominación": "",
                "CUIT": "",
                "Tipo": "",
                "Modalidad de Cobro": "",
                "Descuenta de Cheques": ""
            }])

    # ------------------ PRINCIPALES PROVEEDORES, CLIENTES Y COMPETIDORES ------------------
    with st.expander("**Principales Proveedores, Clientes y Competidores**"):

        # OPCIONES
        opciones_local_exterior = ["COMPLETAR", "LOCAL", "EXTERIOR"]
        opciones_modalidad_pago = ["COMPLETAR", "CONTADO", "A PLAZO"]
        opciones_modalidad_proveedor = ["COMPLETAR", "CONTADO", "30 DIAS", "45 DIAS", "60 DIAS", "90 DIAS", "120 DIAS", "180 DIAS", "MAS DE 180 DIAS", "365 DIAS"]

        # ------------------ PROVEEDORES ------------------
        st.markdown("**Principales Proveedores**")
        if "proveedores" not in st.session_state:
            st.session_state.proveedores = []

        with st.form("form_proveedor"):
            col1, col2 = st.columns(2)
            prov_deno = col1.text_input("Denominación", key="prov_deno_nuevo")
            prov_cuit = col2.text_input("CUIT (11 dígitos)", key="prov_cuit_nuevo")

            col3, col4, col5 = st.columns(3)
            prov_tel = col3.text_input("Teléfono", key="prov_tel_nuevo")
            prov_local = col4.selectbox("Local o Exterior", opciones_local_exterior, key="prov_local_nuevo")
            prov_modalidad = col5.selectbox("Modalidad de Pago", opciones_modalidad_pago, key="prov_modalidad_nuevo")

            col6, col7 = st.columns(2)
            prov_plazo = col6.selectbox("Plazo en Días", opciones_modalidad_proveedor, key="prov_plazo_nuevo")
            prov_pct = col7.number_input("% Compras", min_value=0.0, max_value=100.0, key="prov_pct_nuevo")

            submit_prov = st.form_submit_button("Agregar Proveedor")

        if submit_prov:
            errores = []
            if not prov_deno.strip():
                errores.append("❌ El nombre del proveedor es obligatorio.")
            if not re.match(r"^\d{11}$", prov_cuit.strip()):
                errores.append("❌ El CUIT debe tener exactamente 11 dígitos numéricos.")

            if errores:
                for e in errores:
                    st.error(e)
            else:
                st.session_state.proveedores.append({
                    "Denominación": prov_deno.strip(),
                    "CUIT": prov_cuit.strip(),
                    "Teléfono": prov_tel.strip(),
                    "Local o Exterior": prov_local,
                    "Modalidad de Pago": prov_modalidad,
                    "Plazo en Días": prov_plazo,
                    "% Compras": prov_pct
                })
                st.success("✅ Proveedor agregado correctamente.")
                st.rerun()

        if st.session_state.proveedores:
            st.markdown("**Proveedores cargados**")
            df_proveedores = pd.DataFrame(st.session_state.proveedores)
            st.dataframe(df_proveedores)
            
            cols_prov = st.columns(4)
            for i, fila in enumerate(st.session_state.proveedores):
                col = cols_prov[i % 4]  # Tomamos una de las 4 columnas en orden
                with col:
                    if st.button(f"❌ Eliminar {fila['Denominación']}", key=f"delete_prov_{i}"):
                        st.session_state.proveedores.pop(i)
                        st.rerun()
        else:
            df_proveedores = pd.DataFrame([{
                "Denominación": "", "CUIT": "", "Teléfono": "", "Local o Exterior": "",
                "Modalidad de Pago": "", "Plazo en Días": "COMPLETAR", "% Compras": 0
            }])

        # ------------------ CLIENTES ------------------
        st.markdown("**Principales Clientes**")
        if "clientes" not in st.session_state:
            st.session_state.clientes = []

        with st.form("form_cliente"):
            col1, col2 = st.columns(2)
            cl_deno = col1.text_input("Denominación", key="cl_deno_nuevo")
            cl_cuit = col2.text_input("CUIT (11 dígitos)", key="cl_cuit_nuevo")

            col3, col4, col5 = st.columns(3)
            cl_tel = col3.text_input("Teléfono", key="cl_tel_nuevo")
            cl_local = col4.selectbox("Local o Exterior", opciones_local_exterior, key="cl_local_nuevo")
            cl_modalidad = col5.selectbox("Modalidad de Pago", opciones_modalidad_pago, key="cl_modalidad_nuevo")

            col6, col7 = st.columns(2)
            cl_plazo = col6.selectbox("Plazo en Días", opciones_modalidad_proveedor, key="cl_plazo_nuevo")
            cl_pct = col7.number_input("% Ventas", min_value=0.0, max_value=100.0, key="cl_pct_nuevo")

            submit_cl = st.form_submit_button("Agregar Cliente")

        if submit_cl:
            errores = []
            if not cl_deno.strip():
                errores.append("❌ El nombre del cliente es obligatorio.")
            if not re.match(r"^\d{11}$", cl_cuit.strip()):
                errores.append("❌ El CUIT debe tener exactamente 11 dígitos numéricos.")

            if errores:
                for e in errores:
                    st.error(e)
            else:
                st.session_state.clientes.append({
                    "Denominación": cl_deno.strip(),
                    "CUIT": cl_cuit.strip(),
                    "Teléfono": cl_tel.strip(),
                    "Local o Exterior": cl_local,
                    "Modalidad de Pago": cl_modalidad,
                    "Plazo en Días": cl_plazo,
                    "% Ventas": cl_pct
                })
                st.success("✅ Cliente agregado correctamente.")
                st.rerun()

        if st.session_state.clientes:
            st.markdown("**Clientes cargados**")
            df_clientes = pd.DataFrame(st.session_state.clientes)
            st.dataframe(df_clientes)
            cols_client = st.columns(4)
            for i, fila in enumerate(st.session_state.proveedores):
                col = cols_client[i % 4]  # Tomamos una de las 4 columnas en orden
                with col:
                    if st.button(f"❌ Eliminar {fila['Denominación']}", key=f"delete_client_{i}"):
                        st.session_state.proveedores.pop(i)
                        st.rerun()
        else:
            df_clientes = pd.DataFrame([{
                "Denominación": "", "CUIT": "", "Teléfono": "", "Local o Exterior": "",
                "Modalidad de Pago": "", "Plazo en Días": "COMPLETAR", "% Ventas": 0
            }])

        # ------------------ COMPETIDORES ------------------
        st.markdown("**Principales Competidores**")
        if "competidores" not in st.session_state:
            st.session_state.competidores = []

        with st.form("form_competidor"):
            col1, col2, col3 = st.columns(3)
            comp_deno = col1.text_input("Denominación", key="comp_deno_nuevo")
            comp_cuit = col2.text_input("CUIT (11 dígitos)", key="comp_cuit_nuevo")
            comp_tel = col3.text_input("Teléfono", key="comp_tel_nuevo")

            col4, col5, col6 = st.columns(3)
            comp_seg = col4.text_input("Segmento", key="comp_seg_nuevo")
            comp_pct = col5.number_input("Participación del Mercado %", min_value=0.0, max_value=100.0, key="comp_pct_nuevo")
            comp_cond = col6.text_input("Condiciones de ventas", key="comp_cond_nuevo")

            submit_comp = st.form_submit_button("Agregar Competidor")

        if submit_comp:
            errores = []
            if not comp_deno.strip():
                errores.append("❌ El nombre del competidor es obligatorio.")
            if not re.match(r"^\d{11}$", comp_cuit.strip()):
                errores.append("❌ El CUIT debe tener exactamente 11 dígitos numéricos.")

            if errores:
                for e in errores:
                    st.error(e)
            else:
                st.session_state.competidores.append({
                    "Denominación": comp_deno.strip(),
                    "CUIT": comp_cuit.strip(),
                    "Teléfono": comp_tel.strip(),
                    "Segmento": comp_seg.strip(),
                    "Participacion del Mercado %": comp_pct,
                    "Condiciones de ventas": comp_cond.strip()
                })
                st.success("✅ Competidor agregado correctamente.")
                st.rerun()

        if st.session_state.competidores:
            st.markdown("**Competidores cargados**")
            df_competidores = pd.DataFrame(st.session_state.competidores)
            st.dataframe(df_competidores)
            cols_comp = st.columns(4)
            for i, fila in enumerate(st.session_state.proveedores):
                col = cols_comp[i % 4]  
                with col:
                    if st.button(f"❌ Eliminar {fila['Denominación']}", key=f"delete_comp_{i}"):
                        st.session_state.proveedores.pop(i)
                        st.rerun()
        else:
            df_competidores = pd.DataFrame([{
                "Denominación": "", "CUIT": "", "Teléfono": "",
                "Segmento": "", "Participacion del Mercado %": 0, "Condiciones de ventas": ""
            }])



    # ------------------ REFERENCIAS BANCARIAS ------------------
    with st.expander("**Referencias Bancarias**"):
        if "referencias_bancarias" not in st.session_state:
            st.session_state.referencias_bancarias = []

        with st.form("form_referencia_bancaria"):
            col1, col2 = st.columns(2)
            ref_entidad = col1.text_input("Entidad Financiera", key="ref_entidad_nueva")
            ref_contacto = col2.text_input("Contacto", key="ref_contacto_nuevo")

            col3, col4 = st.columns(2)
            ref_sucursal = col3.text_input("Sucursal", key="ref_sucursal_nueva")
            ref_tel = col4.text_input("Tel", key="ref_tel_nuevo")

            ref_mail = st.text_input("Mail", key="ref_mail_nuevo")

            submit_ref = st.form_submit_button("Agregar Referencia Bancaria")

        if submit_ref:
            errores = []
            if not ref_entidad.strip():
                errores.append("❌ La entidad financiera es obligatoria.")
            if not re.match(r"[^@]+@[^@]+\.[^@]+", ref_mail.strip()) and ref_mail.strip() != "":
                errores.append("❌ El mail no parece válido.")

            if errores:
                for e in errores:
                    st.error(e)
            else:
                st.session_state.referencias_bancarias.append({
                    "Entidad Financiera": ref_entidad.strip(),
                    "Contacto": ref_contacto.strip(),
                    "Sucursal": ref_sucursal.strip(),
                    "Tel": ref_tel.strip(),
                    "Mail": ref_mail.strip()
                })
                st.success("✅ Referencia bancaria agregada correctamente.")
                st.rerun()

        if st.session_state.referencias_bancarias:
            st.markdown("**Referencias cargadas**")
            df_referencias_bancarias = pd.DataFrame(st.session_state.referencias_bancarias)
            st.dataframe(df_referencias_bancarias)

            cols_ref = st.columns(4)
            for i, fila in enumerate(st.session_state.referencias_bancarias):
                col = cols_ref[i % 4]
                with col:
                    if st.button(f"❌ Eliminar {fila['Entidad Financiera']}", key=f"delete_ref_{i}"):
                        st.session_state.referencias_bancarias.pop(i)
                        st.rerun()
        else:
            df_referencias_bancarias = pd.DataFrame([{
                "Entidad Financiera": "",
                "Contacto": "",
                "Sucursal": "",
                "Tel": "",
                "Mail": ""
            }])

    # 6️⃣ PREVENCIÓN DE LAVADO DE ACTIVOS Y FINANCIAMIENTO DEL TERRORISMO
    with st.expander("**Prevención de Lavado de Activos y Financiamiento del Terrorismo**"):
        

        # ✅ LINKS A LOS ANEXOS (Google Drive o lo que uses)
        st.markdown("""Links para conocer la información de los ANEXOS:
                    **[ANEXO I](https://drive.google.com/file/d/1FN01xfIHEg30b_g3VKHHLgT0AD13fA57/view?usp=sharing)** , **[ANEXO II](https://drive.google.com/file/d/1ISEl0LCq3WO8OAikQjyBDLGFFFsPT2KH/view?usp=drive_link)** , **[ANEXO III](https://drive.google.com/file/d/1xU_uZyTq3c9FGDdQ-mgPsEYymsyp82wY/view?usp=drive_link)**
        """)
        st.write("Complete las declaraciones obligatorias.")
        declaracion_sujeto = st.radio("1) Declaración informativa de sujeto obligado. *Según lo dispuesto por la (Ley 25.246), informo que la empresa que represento se encuentra en el listado adjunto (ANEXO III)*", ["NO", "SI"], key="lavado_sujeto", horizontal=True)
        punto_listado = ""
        if declaracion_sujeto == "SI":
            punto_listado = st.text_input("Indique qué punto del Anexo III aplica")

        declaracion_transacciones = st.radio("2) Declaración informativa de transacciones. *Declaro que la empresa/persona que represento y/o sus integrantes realizan transacciones financieras con las jurisdicciones y los territorios que se detallan en el listado adjunto (ANEXO I)*", ["NO","SI"], key="lavado_transacciones", horizontal=True)
        declaracion_pep = st.radio("3) Declaración de Persona Expuesta Políticamente (PEP)(***). *Declaro bajo juramento que he leído la Nómina de Funciones de Personas Expuestas Políticamente (Anexo II), aprobada por la UIF, y al respecto declaro que soy PEP.*", ["NO","SI"], key="lavado_pep", horizontal=True)
        st.caption("(***) En caso de Persona Jurídica incluye a miembros del Directorio y Accionistas.")
        
        st.write("Datos del representante de la empresa:")
        nombre_rep = st.text_input("Nombre", key="Nombre Representante")
        apellido_rep = st.text_input("Apellido", key="Apellido Representante")
        cargo_rep = st.text_input("Cargo", key="Cargo Representante")
        dni_rep = st.text_input("DNI", key="DNI Representante")

        

        # Guardar todo en un diccionario para agregarlo a tu archivo final si querés
        st.session_state.respuestas["Prevención Lavado"] = {
            "Declaración Sujeto": declaracion_sujeto,
            "Punto Listado": punto_listado,
            "Declaración Transacciones": declaracion_transacciones,
            "Declaración PEP": declaracion_pep,
            "Representante": {
                "Nombre": nombre_rep,
                "Apellido": apellido_rep,
                "Cargo": cargo_rep,
                "DNI": dni_rep
            }
        }
# --- BLOQUE DE DEUDA BANCARIA Y FINANCIERAS ---
with tabs[1]:
    # --- OPCIONES FIJAS ---
    opciones_garantia = ["", "Fianza / Sola Firma (F)", "Prenda (P)", "Hipoteca (H)", "Warrant (W)", "Forward (FW)", "Cesión (C)", "Plazo Fijo (PF)"]
    opciones_regimen = ["", "Mensual", "Bimestral", "Trimestral", "Semestral", "Anual"]

    # --- FUNCIONES NUEVA FILA ---
    def new_banco_row():
        return {
            "Entidad": "",
            "Saldo Préstamos Amortizables": 0,
            "Garantía (*)": "",
            "Valor de la Cuota": 0,
            "Régimen de Amortización (**)": "",
            "Cantidad Cuotas Faltantes": 0,
            "Descuento de Cheques Utilizado": 0,
            "Adelanto en Cta Cte Utilizado": 0,
            "Avales SGR": 0,
            "Tarjeta de Crédito Utilizado": 0,
            "Leasing Utilizado": 0,
            "Impo/Expo Utilizado": 0,
            "Tasa Promedio $": 0.0,
            "Tasa Promedio USD": 0.0,
            "Tipo de Moneda": "ARS"
        }

    def new_mercado_row():
        return {
            "Obligaciones Negociables": 0,
            "Descuento de Cheques Propios": 0,
            "Pagaré Bursátil": 0,
            "Organismos Multilaterales (CFI)": 0,
            "Otros (1)": "",
            "Otros (2)": "",
            "Tasa Promedio $": 0.0,
            "Tasa Promedio USD": 0.0,
            "Tipo de Moneda": "ARS"
        }

    # --- INICIALIZAR ESTADO ---
    if "bancos" not in st.session_state:
        st.session_state.bancos = []
    if "mercado" not in st.session_state:
        st.session_state.mercado = []

    # ========================
    # BLOQUE 1 - BANCOS
    # ========================
    with st.expander("**Cargar Deuda Bancaria**"):
        with st.form("form_banco"):
            col1, col2, col3 = st.columns(3)
            ent = col1.text_input("Entidad", key="banco_ent_nuevo")
            saldo = col2.number_input("Monto en Saldo Préstamos Amortizables", key="banco_saldo_nuevo", min_value=0.0)
            garantia = col3.selectbox("Garantía (*)", opciones_garantia, key="banco_garantia_nuevo")

            col4, col5, col6 = st.columns(3)
            cuota = col4.number_input("Valor de la Cuota", key="banco_cuota_nuevo", min_value=0.0)
            regimen = col5.selectbox("Régimen de Amortización (**)", opciones_regimen, key="banco_regimen_nuevo")
            cuotas_falt = col6.number_input("Cantidad Cuotas Faltantes", key="banco_cuotas_falt_nuevo", min_value=0)

            col7, col8, col9 = st.columns(3)
            cheques = col7.number_input("Monto en Descuento de Cheques Utilizado", key="banco_cheques_nuevo", min_value=0.0)
            cta_cte = col8.number_input("Monto en Adelanto en Cta Cte Utilizado", key="banco_cta_nuevo", min_value=0.0)
            avales = col9.number_input("Monto en Avales SGR", key="banco_avales_nuevo", min_value=0.0)

            col10, col11, col12 = st.columns(3)
            tarjeta = col10.number_input("Monto en Tarjeta de Crédito Utilizado", key="banco_tarjeta_nuevo", min_value=0.0)
            leasing = col11.number_input("Monto en Leasing Utilizado", key="banco_leasing_nuevo", min_value=0.0)
            impoexpo = col12.number_input("Monto en Impo/Expo Utilizado", key="banco_impoexpo_nuevo", min_value=0.0)

            col13, col14 = st.columns(2)
            tasa_ars = col13.number_input("Tasa Promedio % en ARS", key="banco_tasa_ars_nuevo", min_value=0.0)
            tasa_usd = col14.number_input("Tasa Promedio % en USD", key="banco_tasa_usd_nuevo", min_value=0.0)

            moneda = st.selectbox("Tipo de Moneda", ["ARS", "USD"], key="banco_moneda_nuevo")

            submit_banco = st.form_submit_button("Agregar Deuda Bancaria")

        if submit_banco:
            errores = []
            if not ent.strip():
                errores.append("❌ El nombre de la entidad es obligatorio.")

            if errores:
                for e in errores:
                    st.error(e)
            else:
                st.session_state.bancos.append({
                    "Entidad": ent.strip(),
                    "Saldo Préstamos Amortizables": saldo,
                    "Garantía (*)": garantia,
                    "Valor de la Cuota": cuota,
                    "Régimen de Amortización (**)": regimen,
                    "Cantidad Cuotas Faltantes": cuotas_falt,
                    "Descuento de Cheques Utilizado": cheques,
                    "Adelanto en Cta Cte Utilizado": cta_cte,
                    "Avales SGR": avales,
                    "Tarjeta de Crédito Utilizado": tarjeta,
                    "Leasing Utilizado": leasing,
                    "Impo/Expo Utilizado": impoexpo,
                    "Tasa Promedio $": tasa_ars,
                    "Tasa Promedio USD": tasa_usd,
                    "Tipo de Moneda": moneda
                })
                st.success("✅ Deuda bancaria agregada correctamente.")
                st.rerun()

        if st.session_state.bancos:
            df_bancos = pd.DataFrame(st.session_state.bancos)
            df_bancos["Total por Banco"] = df_bancos[
                ["Saldo Préstamos Amortizables",
                 "Descuento de Cheques Utilizado",
                 "Adelanto en Cta Cte Utilizado",
                 "Avales SGR",
                 "Tarjeta de Crédito Utilizado",
                 "Leasing Utilizado",
                 "Impo/Expo Utilizado"]
            ].sum(axis=1)

            st.dataframe(df_bancos)

            cols_banco = st.columns(4)
            for i, fila in enumerate(st.session_state.bancos):
                col = cols_banco[i % 4]
                with col:
                    if st.button(f"❌ Eliminar {fila['Entidad']}", key=f"delete_banco_{i}"):
                        st.session_state.bancos.pop(i)
                        st.rerun()
        else:
            df_bancos = pd.DataFrame([{
                "Entidad": "", "Saldo Préstamos Amortizables": 0,
                "Garantía (*)": "", "Valor de la Cuota": 0, "Régimen de Amortización (**)": "",
                "Cantidad Cuotas Faltantes": 0, "Descuento de Cheques Utilizado": 0,
                "Adelanto en Cta Cte Utilizado": 0, "Avales SGR": 0,
                "Tarjeta de Crédito Utilizado": 0, "Leasing Utilizado": 0,
                "Impo/Expo Utilizado": 0, "Tasa Promedio $": 0.0,
                "Tasa Promedio USD": 0.0, "Tipo de Moneda": "ARS"
            }])


    # === FORMULARIO DEUDA EN MERCADO ===
    with st.expander("**Cargar Deuda en el Mercado de Capitales**"):
        with st.form("form_mercado"):
            col1, col2, col3, col4 = st.columns(4)
            on = col1.number_input("Monto en Obligaciones Negociables", key="mercado_on", min_value=0.0)
            cheques = col2.number_input("Monto en Cheques Propios", key="mercado_cheques", min_value=0.0)
            pagare = col3.number_input("Monto en Pagaré Bursátil", key="mercado_pagare", min_value=0.0)
            cfi = col4.number_input("Monto en Organismos Multilaterales (CFI)", key="mercado_cfi", min_value=0.0)

            col5, col6, col7, col8 = st.columns(4)
            otros1 = col5.text_input("Monto en Otros (1)", key="mercado_otros1")
            otros2 = col6.text_input("Monto en Otros (2)", key="mercado_otros2")
            tasa_ars = col7.number_input("Tasa Promedio % ARS", key="mercado_tasa_ars", min_value=0.0)
            tasa_usd = col8.number_input("Tasa Promedio % USD", key="mercado_tasa_usd", min_value=0.0)

            moneda = st.selectbox("Tipo de Moneda de la deuda a cargar", ["ARS", "USD"], key="mercado_moneda")
            submit_mercado = st.form_submit_button("Agregar Deuda del Mercado")

        if submit_mercado:
            st.session_state.mercado.append({
                "Obligaciones Negociables": on,
                "Descuento de Cheques Propios": cheques,
                "Pagaré Bursátil": pagare,
                "Organismos Multilaterales (CFI)": cfi,
                "Otros (1)": otros1,
                "Otros (2)": otros2,
                "Tasa Promedio $": tasa_ars,
                "Tasa Promedio USD": tasa_usd,
                "Tipo de Moneda": moneda
            })
            st.success("✅ Deuda del mercado agregada correctamente.")
            st.rerun()

        if st.session_state.mercado:
            df_mercado = pd.DataFrame(st.session_state.mercado)
            df_mercado["Total"] = df_mercado[["Obligaciones Negociables", "Descuento de Cheques Propios", "Pagaré Bursátil", "Organismos Multilaterales (CFI)"]].sum(axis=1)
            st.dataframe(df_mercado)

            cols_mercado = st.columns(4)
            for i, fila in enumerate(st.session_state.mercado):
                col = cols_mercado[i % 4]
                with col:
                    if st.button(f"❌ Eliminar Deuda Mercado #{i+1}", key=f"delete_mercado_{i}"):
                        st.session_state.mercado.pop(i)
                        st.rerun()
    
    
    # Inicializar si no existe
    if "deudas_comerciales" not in st.session_state:
        st.session_state.deudas_comerciales = []

    # === FORMULARIO DEUDA COMERCIAL ===
    with st.expander("**Cargar Deuda Comercial**"):
        with st.form("form_comercial"):
            col1, col2, col3, col4 = st.columns(4)
            afavor = col1.text_input("A favor de", key="com_afavor")
            moneda_com = col2.selectbox("Moneda", ["ARS", "USD"], key="com_moneda")
            monto = col3.number_input("Monto", key="com_monto", min_value=0.0)
            garantia = col4.text_input("Garantía", key="com_garantia")

            col5, col6 = st.columns(2)
            tasa = col5.number_input("Tasa (%)", key="com_tasa", min_value=0.0)
            plazo = col6.number_input("Plazo (días)", key="com_plazo", min_value=0)

            submit_com = st.form_submit_button("Agregar Deuda Comercial")

        if submit_com:
            st.session_state.deudas_comerciales.append({
                "A favor de": afavor,
                "Tipo de Moneda": moneda_com,
                "Monto": monto,
                "Garantía": garantia,
                "Tasa": tasa,
                "Plazo (días)": plazo
            })
            st.success("✅ Deuda comercial agregada correctamente.")
            st.rerun()

        if "deudas_comerciales" in st.session_state and st.session_state.deudas_comerciales:
            df_com = pd.DataFrame(st.session_state.deudas_comerciales)
            df_com["Total"] = df_com["Monto"]
            st.dataframe(df_com)

            cols_com = st.columns(4)
            for i, fila in enumerate(st.session_state.deudas_comerciales):
                col = cols_com[i % 4]
                with col:
                    if st.button(f"❌ Eliminar Deuda Comercial #{i+1}", key=f"delete_com_{i}"):
                        st.session_state.deudas_comerciales.pop(i)
                        st.rerun()
        else:
            df_com = pd.DataFrame([{ "A favor de": "", "Tipo de Moneda": "ARS", "Monto": 0.0, "Garantía": "", "Tasa": 0.0, "Plazo (días)": 0 }])

    
    # ========================
    # DATAFRAMES desde session_state (sin modificar nada)
    # ========================
    
    bancos_df = pd.DataFrame(st.session_state.bancos) if "bancos" in st.session_state else pd.DataFrame()
    
    # === BLOQUE RESUMEN DEUDA MERCADO DE CAPITALES ===
    mercado_df = pd.DataFrame(st.session_state.mercado) if "mercado" in st.session_state else pd.DataFrame()
    total_mercado_ars = 0
    total_mercado_usd = 0
    tasa_ponderada_ars_mercado = 0
    tasa_ponderada_usd_mercado = 0

    if not mercado_df.empty:
        columnas_montos = ["Obligaciones Negociables", "Descuento de Cheques Propios", "Pagaré Bursátil", "Organismos Multilaterales (CFI)", "Otros (1)", "Otros (2)"]
        columnas_presentes = [col for col in columnas_montos if col in mercado_df.columns]
        mercado_df["Total"] = mercado_df[columnas_presentes].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)

        ars = mercado_df[mercado_df["Tipo de Moneda"] == "ARS"]
        total_mercado_ars = ars["Total"].sum()
        if total_mercado_ars > 0 and "Tasa Promedio $" in ars.columns:
            tasas = ars["Tasa Promedio $"].fillna(0)
            montos = ars["Total"]
            tasa_ponderada_ars_mercado = (tasas * montos).sum() / total_mercado_ars

        usd = mercado_df[mercado_df["Tipo de Moneda"] == "USD"]
        total_mercado_usd = usd["Total"].sum()
        if total_mercado_usd > 0 and "Tasa Promedio USD" in usd.columns:
            tasas = usd["Tasa Promedio USD"].fillna(0)
            montos = usd["Total"]
            tasa_ponderada_usd_mercado = (tasas * montos).sum() / total_mercado_usd

    
    deudas_com_df = pd.DataFrame(st.session_state.deudas_comerciales) if "deudas_comerciales" in st.session_state else pd.DataFrame()
    
    # ========================
    # ENRIQUECER bancos_df CON "Total por Banco" SOLO PARA CÁLCULOS
    # ========================
    if not bancos_df.empty:
        bancos_df["Total por Banco"] = (
            bancos_df.get("Saldo Préstamos Amortizables", 0).fillna(0) +
            bancos_df.get("Valor de la Cuota", 0).fillna(0) * bancos_df.get("Cantidad Cuotas Faltantes", 0).fillna(0) +
            bancos_df.get("Descuento de Cheques Utilizado", 0).fillna(0) +
            bancos_df.get("Adelanto en Cta Cte Utilizado", 0).fillna(0) +
            bancos_df.get("Avales SGR", 0).fillna(0) +
            bancos_df.get("Tarjeta de Crédito Utilizado", 0).fillna(0) +
            bancos_df.get("Leasing Utilizado", 0).fillna(0) +
            bancos_df.get("Impo/Expo Utilizado", 0).fillna(0)
        )
    
    if not mercado_df.empty and "Total" not in mercado_df.columns:
        valor_nominal = mercado_df.get("Valor Nominal", pd.Series([0]*len(mercado_df), index=mercado_df.index)).fillna(0)
        monto = mercado_df.get("Monto", pd.Series([0]*len(mercado_df), index=mercado_df.index)).fillna(0)
        mercado_df["Total"] = valor_nominal + monto

    # ========================
    # RESUMEN GENERAL DE DEUDA
    # ========================
    with st.expander("**Resumen General de la Deuda Cargada**"):

        # === BLOQUE BANCOS ===
        try:
            if not bancos_df.empty:
                bancos_ars = bancos_df[bancos_df["Tipo de Moneda"] == "ARS"]
                bancos_usd = bancos_df[bancos_df["Tipo de Moneda"] == "USD"]

                total_bancos_ars = bancos_ars["Total por Banco"].sum()
                total_bancos_usd = bancos_usd["Total por Banco"].sum()

                tasa_bancos_ars = (
                    (bancos_ars["Total por Banco"] * bancos_ars["Tasa Promedio $"]).sum() / total_bancos_ars
                    if total_bancos_ars > 0 else 0
                )
                tasa_bancos_usd = (
                    (bancos_usd["Total por Banco"] * bancos_usd["Tasa Promedio USD"]).sum() / total_bancos_usd
                    if total_bancos_usd > 0 else 0
                )
            else:
                total_bancos_ars = total_bancos_usd = 0
                tasa_bancos_ars = tasa_bancos_usd = 0
        except Exception:
            total_bancos_ars = total_bancos_usd = 0
            tasa_bancos_ars = tasa_bancos_usd = 0

        # === BLOQUE MERCADO ===
        try:
            if not mercado_df.empty:
                columnas_valores = [
                    "Obligaciones Negociables", "Descuento de Cheques Propios",
                    "Pagaré Bursátil", "Organismos Multilaterales (CFI)"
                ]

                # Asegurar que las columnas están y convertirlas a numérico
                mercado_df[columnas_valores] = mercado_df[columnas_valores].apply(pd.to_numeric, errors="coerce").fillna(0)

                # Calcular total por fila
                mercado_df["Total"] = mercado_df[columnas_valores].sum(axis=1)

                # Separar por moneda
                mercado_ars = mercado_df[mercado_df["Tipo de Moneda"] == "ARS"]
                mercado_usd = mercado_df[mercado_df["Tipo de Moneda"] == "USD"]

                # Totales
                total_mercado_ars = mercado_ars["Total"].sum()
                total_mercado_usd = mercado_usd["Total"].sum()

                # Tasa ponderada
                tasa_mercado_ars = (
                    (mercado_ars["Total"] * mercado_ars["Tasa Promedio $"]).sum() / total_mercado_ars
                    if total_mercado_ars > 0 else 0
                )
                tasa_mercado_usd = (
                    (mercado_usd["Total"] * mercado_usd["Tasa Promedio USD"]).sum() / total_mercado_usd
                    if total_mercado_usd > 0 else 0
                )
            else:
                total_mercado_ars = total_mercado_usd = 0
                tasa_mercado_ars = tasa_mercado_usd = 0
        except Exception as e:
            st.error(f"Error en bloque Mercado: {e}")
            total_mercado_ars = total_mercado_usd = 0
            tasa_mercado_ars = tasa_mercado_usd = 0

        # === BLOQUE COMERCIAL ===
        try:
            if not deudas_com_df.empty:
                comercial_ars = deudas_com_df[deudas_com_df["Tipo de Moneda"] == "ARS"]
                comercial_usd = deudas_com_df[deudas_com_df["Tipo de Moneda"] == "USD"]

                total_comercial_ars = comercial_ars["Monto"].sum()
                total_comercial_usd = comercial_usd["Monto"].sum()

                tasa_comercial_ars = (
                    (comercial_ars["Monto"] * comercial_ars["Tasa"]).sum() / total_comercial_ars
                    if total_comercial_ars > 0 else 0
                )
                tasa_comercial_usd = (
                    (comercial_usd["Monto"] * comercial_usd["Tasa"]).sum() / total_comercial_usd
                    if total_comercial_usd > 0 else 0
                )
            else:
                total_comercial_ars = total_comercial_usd = 0
                tasa_comercial_ars = tasa_comercial_usd = 0
        except Exception:
            total_comercial_ars = total_comercial_usd = 0
            tasa_comercial_ars = tasa_comercial_usd = 0

        # === TOTAL GENERAL POR MONEDA ===
        total_general_ars = total_bancos_ars + total_mercado_ars + total_comercial_ars
        total_general_usd = total_bancos_usd + total_mercado_usd + total_comercial_usd
        total_general = total_general_ars + total_general_usd

        # === TASA PROMEDIO GENERAL PONDERADA ===
        suma_tasa_general_ars = (
            tasa_bancos_ars * total_bancos_ars +
            tasa_mercado_ars * total_mercado_ars +
            tasa_comercial_ars * total_comercial_ars
        )
        suma_tasa_general_usd = (
            tasa_bancos_usd * total_bancos_usd +
            tasa_mercado_usd * total_mercado_usd +
            tasa_comercial_usd * total_comercial_usd
        )

        tasa_general_ars = suma_tasa_general_ars / total_general_ars if total_general_ars > 0 else 0
        tasa_general_usd = suma_tasa_general_usd / total_general_usd if total_general_usd > 0 else 0

        # === TARJETA VISUAL ===
        st.markdown(
            f"""
            <div style="
                border: 2px solid #4CAF50;
                border-radius: 12px;
                padding: 30px;
                background-color: #f9f9f9;
                display: flex;
                justify-content: space-around;
                flex-wrap: wrap;
            ">
                <div style="flex: 1; margin: 20px; min-width: 240px;">
                    <h3 style="color:#4CAF50;"><b>Deuda Bancaria</b></h3>
                    <p><b>Total ARS:</b> ${total_bancos_ars:,.2f}</p>
                    <p><b>Total USD:</b> U$D {total_bancos_usd:,.2f}</p>
                    <p><b>Tasa Promedio ARS:</b> {tasa_bancos_ars:.2f} %</p>
                    <p><b>Tasa Promedio USD:</b> {tasa_bancos_usd:.2f} %</p>
                </div>
                <div style="flex: 1; margin: 20px; min-width: 240px;">
                    <h3 style="color:#2196F3;"><b>Mercado Capitales</b></h3>
                    <p><b>Total ARS:</b> ${total_mercado_ars:,.2f}</p>
                    <p><b>Total USD:</b> U$D {total_mercado_usd:,.2f}</p>
                    <p><b>Tasa Promedio ARS:</b> {tasa_mercado_ars:.2f} %</p>
                    <p><b>Tasa Promedio USD:</b> {tasa_mercado_usd:.2f} %</p>
                </div>
                <div style="flex: 1; margin: 20px; min-width: 240px;">
                    <h3 style="color:#9C27B0;"><b>Deuda Comercial</b></h3>
                    <p><b>Total ARS:</b> ${total_comercial_ars:,.2f}</p>
                    <p><b>Total USD:</b> U$D {total_comercial_usd:,.2f}</p>
                    <p><b>Tasa Promedio ARS:</b> {tasa_comercial_ars:.2f} %</p>
                    <p><b>Tasa Promedio USD:</b> {tasa_comercial_usd:.2f} %</p>
                </div>
                <div style="flex: 1; margin: 20px; min-width: 240px;">
                    <h3 style="color:#FF9800;"><b>Total General</b></h3>
                    <p><b>Total ARS:</b> ${total_general_ars:,.2f}</p>
                    <p><b>Total USD:</b> U$D {total_general_usd:,.2f}</p>
                    <p><b>Tasa Promedio ARS:</b> {tasa_general_ars:.2f} %</p>
                    <p><b>Tasa Promedio USD:</b> {tasa_general_usd:.2f} %</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

with tabs[2]:

    # Sanear listas si ya fueron definidas
    for key in ["ventas_interno", "ventas_externo", "compras"]:
        if key in st.session_state:
            # Eliminar meses repetidos por error (por ejemplo, dos "Enero")
            meses_vistos = set()
            sin_duplicados = []
            for fila in st.session_state[key]:
                mes = fila.get("Mes")
                if mes not in meses_vistos:
                    sin_duplicados.append(fila)
                    meses_vistos.add(mes)
            st.session_state[key] = sin_duplicados


    # === Opciones ===
    opciones_tipo = ["COMPLETAR", "AGROPECUARIO", "INDUSTRIA", "COMERCIO", "SERVICIOS", "CONSTRUCCION"]
    subcategorias_agro = ["AGRICULTURA", "GANADERIA", "TAMBO", "OTROS"]

    meses_largos = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    # === Estado inicial ===
    for key in ["ventas_interno", "ventas_externo", "compras"]:
        if key not in st.session_state:
            st.session_state[key] = [
                {
                    "Mes": mes,
                    "Tipo": "COMPLETAR",
                    "Subtipos": [],
                    "Valores": {},
                    "Año en curso": 0,
                    "Año 1": 0,
                    "Año 2": 0,
                    "Año 3": 0,
                    "Región": "" if key == "ventas_externo" else None
                } for mes in meses_largos
            ]

    # === BLOQUE 1 ===
    with st.expander("**Ventas - Mercado Interno (Netas de IVA)**"):
        interno_rows = []

        for i, fila in enumerate(st.session_state.ventas_interno):
            col1, col2 = st.columns([1, 5])
            col1.write(f"**{fila['Mes']}**")

            # Selectbox clásico de Tipo
            fila["Tipo"] = col2.selectbox("Tipo", opciones_tipo,
                                        index=opciones_tipo.index(fila["Tipo"]),
                                        key=f"int_tipo_{i}")

            if fila["Tipo"] == "AGROPECUARIO":
                # Mostrar cada subtipo como una fila horizontal con los valores a completar
                for j, subtipo in enumerate(subcategorias_agro):
                    row = st.columns([1.2, 0.9, 0.9, 0.9, 0.9])
                    row[0].markdown(f"{subtipo}")
                    fila[f"Año en curso {subtipo}"] = row[1].number_input("Año en curso", value=fila.get(f"Año en curso {subtipo}", 0), key=f"int_curso_{i}_{j}")
                    fila[f"Año 1 {subtipo}"] = row[2].number_input("Año 1", value=fila.get(f"Año 1 {subtipo}", 0), key=f"int_1_{i}_{j}")
                    fila[f"Año 2 {subtipo}"] = row[3].number_input("Año 2", value=fila.get(f"Año 2 {subtipo}", 0), key=f"int_2_{i}_{j}")
                    fila[f"Año 3 {subtipo}"] = row[4].number_input("Año 3", value=fila.get(f"Año 3 {subtipo}", 0), key=f"int_3_{i}_{j}")
            else:
                # Si no es agropecuario, seguimos con tu lógica original
                col3, col4, col5, col6 = st.columns([0.9, 0.9, 0.9, 0.9])
                fila["Año en curso"] = col3.number_input("Año en curso", value=fila["Año en curso"], key=f"int_curso_{i}")
                fila["Año 1"] = col4.number_input("Año 1", value=fila["Año 1"], key=f"int_1_{i}")
                fila["Año 2"] = col5.number_input("Año 2", value=fila["Año 2"], key=f"int_2_{i}")
                fila["Año 3"] = col6.number_input("Año 3", value=fila["Año 3"], key=f"int_3_{i}")

            st.markdown("<div style='height:1px; background-color:#e0e0e0; margin:8px 0;'></div>", unsafe_allow_html=True)
            fila_copia = fila.copy()
            interno_rows.append(fila_copia)

        # Crear df_interno para exportar (si es necesario)
        df_interno = pd.DataFrame(interno_rows)

        st.success(f"**Total Interno:** "
            f"Año en curso: ${df_interno.get('Año en curso', pd.Series(dtype=float)).sum():,.2f}  | "
            f"Año 1: ${df_interno.get('Año 1', pd.Series(dtype=float)).sum():,.2f}  |  "
            f"Año 2: ${df_interno.get('Año 2', pd.Series(dtype=float)).sum():,.2f}  |  "
            f"Año 3: ${df_interno.get('Año 3', pd.Series(dtype=float)).sum():,.2f}")

    # === BLOQUE 2 ===
    with st.expander("**Ventas Mercado Externo (Netas de IVA)**"):
        externo_rows = []
        for i, fila in enumerate(st.session_state.ventas_externo):
            col1, col2 = st.columns([1, 5])
            col1.write(f"**{fila['Mes']}**")

            fila["Tipo"] = col2.selectbox("Tipo", opciones_tipo,
                                        index=opciones_tipo.index(fila["Tipo"]),
                                        key=f"ext_tipo_{i}")

            if fila["Tipo"] == "AGROPECUARIO":
                for j, subt in enumerate(subcategorias_agro):
                    fila.setdefault(f"Año en curso {subt}", 0)
                    fila.setdefault(f"Año 1 {subt}", 0)
                    fila.setdefault(f"Año 2 {subt}", 0)
                    fila.setdefault(f"Año 3 {subt}", 0)
                    fila.setdefault(f"Región {subt}", "")

                    col_sub = st.columns([1.3, 0.9, 0.9, 0.9, 0.9, 1.2])
                    col_sub[0].markdown(f"{subt}")
                    fila[f"Año en curso {subt}"] = col_sub[1].number_input("Año en curso", value=fila[f"Año en curso {subt}"], key=f"ext_curso_{i}_{j}")
                    fila[f"Año 1 {subt}"] = col_sub[2].number_input("Año 1", value=fila[f"Año 1 {subt}"], key=f"ext_1_{i}_{j}")
                    fila[f"Año 2 {subt}"] = col_sub[3].number_input("Año 2", value=fila[f"Año 2 {subt}"], key=f"ext_2_{i}_{j}")
                    fila[f"Año 3 {subt}"] = col_sub[4].number_input("Año 3", value=fila[f"Año 3 {subt}"], key=f"ext_3_{i}_{j}")
                    fila[f"Región {subt}"] = col_sub[5].text_input("Región", value=fila[f"Región {subt}"], key=f"ext_region_{i}_{j}")
            else:
                col3, col4, col5, col6, col7 = st.columns([0.8, 0.8, 0.8, 0.8, 1])
                fila["Año en curso"] = col3.number_input("Año en curso", value=fila["Año en curso"], key=f"ext_curso_{i}")
                fila["Año 1"] = col4.number_input("Año 1", value=fila["Año 1"], key=f"ext_1_{i}")
                fila["Año 2"] = col5.number_input("Año 2", value=fila["Año 2"], key=f"ext_2_{i}")
                fila["Año 3"] = col6.number_input("Año 3", value=fila["Año 3"], key=f"ext_3_{i}")
                fila["Región"] = col7.text_input("Región", fila["Región"], key=f"ext_region_{i}")

            st.markdown("<div style='height:1px; background-color:#e0e0e0; margin:8px 0;'></div>", unsafe_allow_html=True)
            externo_rows.append(fila)

        df_externo = pd.DataFrame(externo_rows)
        st.success(f"**TOTAL Externo:** "
                f"Año en curso: ${df_externo.filter(like='Año en curso').sum(axis=1).sum():,.2f} | "
                f"Año 1: ${df_externo.filter(like='Año 1').sum(axis=1).sum():,.2f} | "
                f"Año 2: ${df_externo.filter(like='Año 2').sum(axis=1).sum():,.2f} | "
                f"Año 3: ${df_externo.filter(like='Año 3').sum(axis=1).sum():,.2f}")

    # === BLOQUE 3 ===
    with st.expander("**Compras Mensuales (Netas de IVA)**"):
        compras_rows = []
        for i, fila in enumerate(st.session_state.compras):
            col1, col2 = st.columns([1, 5])
            col1.write(f"**{fila['Mes']}**")

            fila["Tipo"] = col2.selectbox("Tipo", opciones_tipo,
                                        index=opciones_tipo.index(fila["Tipo"]),
                                        key=f"comp_tipo_{i}")

            if fila["Tipo"] == "AGROPECUARIO":
                for j, subt in enumerate(subcategorias_agro):
                    fila.setdefault(f"Año en curso {subt}", 0)
                    fila.setdefault(f"Año 1 {subt}", 0)
                    fila.setdefault(f"Año 2 {subt}", 0)
                    fila.setdefault(f"Año 3 {subt}", 0)

                    col_sub = st.columns([1.3, 0.9, 0.9, 0.9, 0.9])
                    col_sub[0].markdown(f"{subt}")
                    fila[f"Año en curso {subt}"] = col_sub[1].number_input("Año en curso", value=fila[f"Año en curso {subt}"], key=f"comp_curso_{i}_{j}")
                    fila[f"Año 1 {subt}"] = col_sub[2].number_input("Año 1", value=fila[f"Año 1 {subt}"], key=f"comp_1_{i}_{j}")
                    fila[f"Año 2 {subt}"] = col_sub[3].number_input("Año 2", value=fila[f"Año 2 {subt}"], key=f"comp_2_{i}_{j}")
                    fila[f"Año 3 {subt}"] = col_sub[4].number_input("Año 3", value=fila[f"Año 3 {subt}"], key=f"comp_3_{i}_{j}")
            else:
                col3, col4, col5, col6 = st.columns([0.9, 0.9, 0.9, 0.9])
                fila["Año en curso"] = col3.number_input("Año en curso", value=fila["Año en curso"], key=f"comp_curso_{i}")
                fila["Año 1"] = col4.number_input("Año 1", value=fila["Año 1"], key=f"comp_1_{i}")
                fila["Año 2"] = col5.number_input("Año 2", value=fila["Año 2"], key=f"comp_2_{i}")
                fila["Año 3"] = col6.number_input("Año 3", value=fila["Año 3"], key=f"comp_3_{i}")

            st.markdown("<div style='height:1px; background-color:#e0e0e0; margin:8px 0;'></div>", unsafe_allow_html=True)
            compras_rows.append(fila)

        df_compras = pd.DataFrame(compras_rows)
        st.success(f"**TOTAL Compras:** "
                    f"Año en curso: ${df_compras.filter(like='Año en curso').sum(axis=1).sum():,.2f} | "
                    f"Año 1: ${df_compras.filter(like='Año 1').sum(axis=1).sum():,.2f} | "
                    f"Año 2: ${df_compras.filter(like='Año 2').sum(axis=1).sum():,.2f} | "
                    f"Año 3: ${df_compras.filter(like='Año 3').sum(axis=1).sum():,.2f}")
        
    

    # === BLOQUE 4 ===
    # Función para convertir a DataFrame
    def convertir_plan(plan_dict, tipo):
        filas = []
        for rubro, meses in plan_dict.items():
            for mes, valor in meses.items():
                filas.append({
                    "Tipo": tipo,
                    "Producto o Categoría": rubro,
                    "Mes": mes,
                    "Valor": valor
                })
        return pd.DataFrame(filas)

    
    if "planes_guardados_por_actividad" not in st.session_state:
        st.session_state.planes_guardados_por_actividad = {}

    with st.expander("**Plan de Ventas y Detalles**"):
        st.subheader("Seleccionar actividades productivas")
        actividades_seleccionadas = st.multiselect(
            "**¿Qué actividades realiza?**",
            ["Agricultura", "Ganadería", "Tambo", "Otros"],
            default=["Agricultura", "Ganadería"]
        )

        respuestas = st.session_state.get("respuestas", {})  # ✅ no se borra nada

        st.markdown("**Con quién comercializa sus productos habitualmente**")
        comercializa = {}
        cols_com = st.columns(len(actividades_seleccionadas))
        for i, act in enumerate(actividades_seleccionadas):
            comercializa[act] = cols_com[i].text_input(f"{act}", key=f"com_{act.lower()}")

        st.markdown("**Principales Proveedores**")
        proveedores = {}
        cols_prov = st.columns(len(actividades_seleccionadas))
        for i, act in enumerate(actividades_seleccionadas):
            proveedores[act] = cols_prov[i].text_input(f"{act}", key=f"prov_{act.lower()}")

        meses_abrev = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
        # Inicializar variables para evitar NameError
        plan_agricultura, plan_ganaderia, plan_tambo, plan_otros = {}, {}, {}, {}
        # === Agricultura ===
        if "Agricultura" in actividades_seleccionadas:
            with st.form("form_agricultura"):
                st.markdown("##### Plan de Ventas en Agricultura (Tn/mes)")
                plan_agricultura = {}
                productos = ["Trigo", "Maíz", "Soja", "Girasol"]
                for producto in productos:
                    st.markdown(f"**{producto}**")
                    rows = []
                    cols = st.columns(6)
                    for i in range(6):
                        mes = meses_abrev[i]
                        valor = cols[i].number_input(f"{mes}", key=f"agro1_{producto}_{mes}", value=0)
                        rows.append((mes, valor))
                    cols = st.columns(6)
                    for i in range(6, 12):
                        mes = meses_abrev[i]
                        valor = cols[i - 6].number_input(f"{mes}", key=f"agro2_{producto}_{mes}", value=0)
                        rows.append((mes, valor))
                    plan_agricultura[producto] = dict(rows)
                if st.form_submit_button("Guardar Plan Agricultura"):
                    respuestas["Plan Agricultura"] = plan_agricultura
                    df_agro = convertir_plan(plan_agricultura, "Agricultura")
                    st.session_state.planes_guardados_por_actividad["Agricultura"] = df_agro
                    st.success("✅ Plan de Agricultura actualizado.")

        # === Ganadería ===
        if "Ganadería" in actividades_seleccionadas:
            with st.form("form_ganaderia"):
                st.markdown("##### Plan de Ventas de Ganadería (Cab/mes)")
                plan_ganaderia = {}
                categorias = ["Novillos", "Vaquillonas", "Terneros", "Vacas"]
                for categoria in categorias:
                    st.markdown(f"**{categoria}**")
                    rows = []
                    cols = st.columns(6)
                    for i in range(6):
                        mes = meses_abrev[i]
                        valor = cols[i].number_input(f"{mes}", key=f"gana1_{categoria}_{mes}", value=0)
                        rows.append((mes, valor))
                    cols = st.columns(6)
                    for i in range(6, 12):
                        mes = meses_abrev[i]
                        valor = cols[i - 6].number_input(f"{mes}", key=f"gana2_{categoria}_{mes}", value=0)
                        rows.append((mes, valor))
                    plan_ganaderia[categoria] = dict(rows)
                if st.form_submit_button("Guardar Plan Ganadería"):
                    respuestas["Plan Ganaderia"] = plan_ganaderia
                    df_gana = convertir_plan(plan_ganaderia, "Ganadería")
                    st.session_state.planes_guardados_por_actividad["Ganadería"] = df_gana
                    st.success("✅ Plan de Ganadería actualizado.")

        # === Tambo ===
        if "Tambo" in actividades_seleccionadas:
            with st.form("form_tambo"):
                st.markdown("##### Plan de Ventas Tambo (Kg GB/mes)")
                plan_tambo = {}
                cols = st.columns(6)
                for i in range(6):
                    mes = meses_abrev[i]
                    plan_tambo[mes] = cols[i].number_input(f"{mes}", key=f"tambo1_{mes}", value=0)
                cols = st.columns(6)
                for i in range(6, 12):
                    mes = meses_abrev[i]
                    plan_tambo[mes] = cols[i - 6].number_input(f"{mes}", key=f"tambo2_{mes}", value=0)
                if st.form_submit_button("Guardar Plan Tambo"):
                    respuestas["Plan Tambo"] = plan_tambo
                    df_tambo = convertir_plan({"Tambo": plan_tambo}, "Tambo")
                    st.session_state.planes_guardados_por_actividad["Tambo"] = df_tambo
                    st.success("✅ Plan de Tambo actualizado.")

        # === Otros ===
        if "Otros" in actividades_seleccionadas:
            with st.form("form_otros"):
                st.markdown("### Plan de Ventas Otros (detalle mensual)")
                plan_otros = {}
                nombre_otros = st.text_input("Nombre actividad", key="otros_nombre")
                if nombre_otros:
                    rows = []
                    cols = st.columns(6)
                    for i in range(6):
                        mes = meses_abrev[i]
                        valor = cols[i].number_input(f"{mes}", key=f"otros1_{mes}", value=0)
                        rows.append((mes, valor))
                    cols = st.columns(6)
                    for i in range(6, 12):
                        mes = meses_abrev[i]
                        valor = cols[i - 6].number_input(f"{mes}", key=f"otros2_{mes}", value=0)
                        rows.append((mes, valor))
                    plan_otros[nombre_otros] = dict(rows)
                if st.form_submit_button("Guardar Plan Otros"):
                    respuestas["Plan Otros"] = plan_otros
                    df_otros = convertir_plan(plan_otros, "Otros")
                    st.session_state.planes_guardados_por_actividad["Otros"] = df_otros
                    st.success("✅ Plan de Otros actualizado.")

        # === Guardar los datos en respuestas de forma segura ===
        st.session_state.respuestas["Plan Agricultura"] = plan_agricultura
        st.session_state.respuestas["Plan Ganaderia"] = plan_ganaderia
        st.session_state.respuestas["Plan Tambo"] = plan_tambo
        st.session_state.respuestas["Plan Otros"] = plan_otros
        st.session_state.respuestas["Comercializa"] = comercializa
        st.session_state.respuestas["Proveedores"] = proveedores
        
        # ✅ Guardar de nuevo en session_state
        #st.session_state.respuestas = respuestas

        # === Mostrar el plan actualizado
        if st.session_state.planes_guardados_por_actividad:
            st.success("Vista previa del Plan de Ventas")
            df_plan_general = pd.concat(st.session_state.planes_guardados_por_actividad.values(), ignore_index=True)
            st.dataframe(df_plan_general)
        else:
            st.info("Todavía no se han guardado planes.")

        # --- Conversión a DataFrame al final ---
        dfs_planes = []

        if "Plan Agricultura" in respuestas and respuestas["Plan Agricultura"]:
            df_agro = convertir_plan(respuestas["Plan Agricultura"], "Agricultura")
            dfs_planes.append(df_agro)

        if "Plan Ganaderia" in respuestas and respuestas["Plan Ganaderia"]:
            df_gana = convertir_plan(respuestas["Plan Ganaderia"], "Ganadería")
            dfs_planes.append(df_gana)

        if "Plan Tambo" in respuestas and respuestas["Plan Tambo"]:
            df_tambo = convertir_plan({"Tambo": respuestas["Plan Tambo"]}, "Tambo")
            dfs_planes.append(df_tambo)

        if "Plan Otros" in respuestas and respuestas["Plan Otros"]:
            df_otros = convertir_plan(respuestas["Plan Otros"], "Otros")
            dfs_planes.append(df_otros)

        
    ## --------- RESUMEN DEL TAB DE VENTAS Y COMPRAS ---------------
    with st.expander("**Resumen anual de Ventas, Compras y Resultado**"):
        def sumar_agro(row, año, subtipos):
            return sum(row.get(f"{año} {sub}", 0) for sub in subtipos)

        def totalizar(dataset, subtipos, origen):
            rows = []
            for fila in dataset:
                tipo = fila.get("Tipo", "SIN TIPO")
                if tipo == "AGROPECUARIO":
                    for año in ["Año en curso", "Año 1", "Año 2", "Año 3"]:
                        valor = sumar_agro(fila, año, subtipos)
                        rows.append({"Origen": origen, "Año": año, "Valor": valor})
                else:
                    for año in ["Año en curso", "Año 1", "Año 2", "Año 3"]:
                        valor = fila.get(año, 0)
                        rows.append({"Origen": origen, "Año": año, "Valor": valor})
            return pd.DataFrame(rows)

        df_int = totalizar(st.session_state.ventas_interno, subcategorias_agro, "Ventas Interno")
        df_ext = totalizar(st.session_state.ventas_externo, subcategorias_agro, "Ventas Externo")
        df_comp = totalizar(st.session_state.compras, subcategorias_agro, "Compras")

        df_total = pd.concat([df_int, df_ext, df_comp], ignore_index=True)

        # Normalizar nombres de años
        df_total["Año"] = df_total["Año"].replace({
            "Año en curso": "Año en curso",  
            "Año 1": "Año 1",
            "Año 2": "Año 2",
            "Año 3": "Año 3"
        })

        pivot = df_total.pivot_table(index="Año", columns="Origen", values="Valor", aggfunc="sum").fillna(0)
        pivot["Ventas"] = pivot.get("Ventas Interno", 0) + pivot.get("Ventas Externo", 0)
        pivot["Resultado"] = pivot["Ventas"] - pivot.get("Compras", 0)
        pivot = pivot[["Ventas Interno", "Ventas Externo", "Compras", "Ventas", "Resultado"]]
        pivot = pivot.reset_index().rename(columns={"Año": "Año calendario"})

        st.markdown("##### Ventas, Compras y Resultado por Año")
        st.dataframe(pivot, use_container_width=True)

        


# ---------------- TAB: Manifestación de Bienes ----------------
with tabs[3]:

    razon_social = respuestas.get("Razón Social / Nombre y apellido", "No definido")
    domicilio_real = (
        f"{respuestas.get('Calle (real y legal)', '')} "
        f"{respuestas.get('Número (real y legal)', '')}, "
        f"{respuestas.get('Localidad (real y legal)', '')}, "
        f"{respuestas.get('Provincia (real y legal)', '')}"
    )
    st.markdown(f"**Manifestación de Bienes de:** `{razon_social}`")
    st.markdown(f"**Domicilio Real:** `{domicilio_real}`")

    fecha_actual = st.date_input("**Manifestación de Bienes al:**", key="mani_fecha_tab4")

    with st.expander("**Activo**"):
        st.markdown("**Disponibilidades (cajas, bancos, etc.)**")
        col1, col2 = st.columns(2)
        disponibilidades_fiscal = col1.number_input("Valor Fiscal (Miles $)", min_value=0.0, step=1.0, key="activo_dispo_fiscal")
        disponibilidades_mercado = col2.number_input("Valor Mercado (Miles $)", min_value=0.0, step=1.0, key="activo_dispo_mercado")
        st.markdown("---")

        st.markdown("**Inversiones (títulos, acciones, plazos fijos, etc.)**")
        col1, col2 = st.columns(2)
        inversiones_fiscal = col1.number_input("Valor Fiscal (Miles $)", min_value=0.0, step=1.0, key="activo_inv_fiscal")
        inversiones_mercado = col2.number_input("Valor Mercado (Miles $)", min_value=0.0, step=1.0, key="activo_inv_mercado")
        st.markdown("---")

        st.markdown("**Créditos**")
        col1, col2 = st.columns(2)
        creditos_fiscal = col1.number_input("Valor Fiscal (Miles $)", min_value=0.0, step=1.0, key="activo_cred_fiscal")
        creditos_mercado = col2.number_input("Valor Mercado (Miles $)", min_value=0.0, step=1.0, key="activo_cred_mercado")
        st.markdown("---")

        st.markdown("**Bienes de Uso - Inmuebles**")
        if "inmuebles" not in st.session_state:
            st.session_state.inmuebles = []
        if st.button("➕ Agregar Inmueble"):
            st.session_state.inmuebles.append({"Tipo": "", "Dirección": "", "Provincia": "", "Destino": "", "m2/has": 0.0, "Valor Fiscal": 0.0, "Valor Mercado": 0.0})
        for idx, item in enumerate(st.session_state.inmuebles):
            st.write(f"**Inmueble {idx+1}**")
            col1, col2, col3 = st.columns(3)
            item["Tipo"] = col1.text_input("Tipo Inmueble", item["Tipo"], key=f"inm_tipo_{idx}")
            item["Dirección"] = col2.text_input("Dirección", item["Dirección"], key=f"inm_dir_{idx}")
            item["Provincia"] = col3.text_input("Provincia", item["Provincia"], key=f"inm_prov_{idx}")
            col1, col2, col3, col4 = st.columns(4)
            item["Destino"] = col1.text_input("Destino", item["Destino"], key=f"inm_dest_{idx}")
            item["m2/has"] = col2.number_input("m2 / has", value=item["m2/has"], key=f"inm_m2_{idx}")
            item["Valor Fiscal"] = col3.number_input("Valor Fiscal (Miles $)", value=item["Valor Fiscal"], key=f"inm_valf_{idx}")
            item["Valor Mercado"] = col4.number_input("Valor Mercado (Miles $)", value=item["Valor Mercado"], key=f"inm_valm_{idx}")
            if st.button(f"❌ Eliminar Inmueble {idx+1}"):
                st.session_state.inmuebles.pop(idx)
                st.rerun()
        st.markdown("---")

        st.markdown("**Rodados**")
        if "rodados" not in st.session_state:
            st.session_state.rodados = []
        if st.button("➕ Agregar Rodado"):
            st.session_state.rodados.append({"Tipo": "", "Marca": "", "Valor Fiscal": 0.0, "Valor Mercado": 0.0})
        for idx, item in enumerate(st.session_state.rodados):
            st.write(f"**Rodado {idx+1}**")
            col1, col2 = st.columns(2)
            item["Tipo"] = col1.text_input("Tipo", item["Tipo"], key=f"rod_tipo_{idx}")
            item["Marca"] = col2.text_input("Marca", item["Marca"], key=f"rod_marca_{idx}")
            col1, col2 = st.columns(2)
            item["Valor Fiscal"] = col1.number_input("Valor Fiscal (Miles $)", value=item["Valor Fiscal"], key=f"rod_valf_{idx}")
            item["Valor Mercado"] = col2.number_input("Valor Mercado (Miles $)", value=item["Valor Mercado"], key=f"rod_valm_{idx}")
            if st.button(f"❌ Eliminar Rodado {idx+1}"):
                st.session_state.rodados.pop(idx)
                st.rerun()
        st.markdown("---")

        st.markdown("**Otros Bienes**")
        col1, col2 = st.columns(2)
        otros_fiscal = col1.number_input("Valor Fiscal (Miles $)", min_value=0.0, step=1.0, key="activo_otros_fiscal")
        otros_mercado = col2.number_input("Valor Mercado (Miles $)", min_value=0.0, step=1.0, key="activo_otros_mercado")

    with st.expander("**Pasivo**"):
        deuda_bancos_total = (total_bancos_ars + total_bancos_usd) if 'total_bancos_ars' in locals() else 0.0
        deuda_mercado_total = (total_mercado_ars + total_mercado_usd) if 'total_mercado_ars' in locals() else 0.0
        deuda_comercial_total = (total_comercial_ars + total_comercial_usd) if 'total_comercial_ars' in locals() else 0.0
        st.number_input("Deuda Bancaria / Financiera (Miles $)", value=deuda_bancos_total, disabled=True, key="pasivo_bancos")
        st.number_input("Deuda Mercado de Capitales (Miles $)", value=deuda_mercado_total, disabled=True, key="pasivo_mercado")
        st.number_input("Deuda Comercial (Miles $)", value=deuda_comercial_total, disabled=True, key="pasivo_comercial")
        otras_deudas = st.number_input("Otras Deudas (Miles $)", min_value=0.0, step=1.0, key="pasivo_otras")
        pasivo_total = deuda_bancos_total + deuda_mercado_total + deuda_comercial_total + otras_deudas
        st.success(f"**Total del Pasivo:** ${pasivo_total:,.2f}")

    with st.expander("**Ingresos y Egresos Anuales**"):
        col1, col2 = st.columns(2)
        ingresos_honorarios = col1.number_input("Ingresos por Honorarios", min_value=0.0, step=1.0, key="mani_ing_honor")
        ingresos_rentas = col1.number_input("Ingresos por Rentas", min_value=0.0, step=1.0, key="mani_ing_rentas")
        ingresos_otros = col1.number_input("Ingresos por Otros", min_value=0.0, step=1.0, key="mani_ing_otros")
        ingresos_total = ingresos_honorarios + ingresos_rentas + ingresos_otros
        egresos_honorarios = col2.number_input("Egresos por Honorarios", min_value=0.0, step=1.0, key="mani_egr_honor")
        egresos_rentas = col2.number_input("Egresos por Rentas", min_value=0.0, step=1.0, key="mani_egr_rentas")
        egresos_otros = col2.number_input("Egresos por Otros", min_value=0.0, step=1.0, key="mani_egr_otros")
        egresos_total = egresos_honorarios + egresos_rentas + egresos_otros
        diferencia = ingresos_total - egresos_total

    # === GUARDAR TODOS LOS DATAFRAMES GENERADOS ===
    df_activo_resumen = pd.DataFrame([{
        "Disponibilidades - Fiscal": disponibilidades_fiscal,
        "Disponibilidades - Mercado": disponibilidades_mercado,
        "Inversiones - Fiscal": inversiones_fiscal,
        "Inversiones - Mercado": inversiones_mercado,
        "Créditos - Fiscal": creditos_fiscal,
        "Créditos - Mercado": creditos_mercado,
        "Otros Bienes - Fiscal": otros_fiscal,
        "Otros Bienes - Mercado": otros_mercado,
    }])
    st.session_state.df_activo_resumen = df_activo_resumen

    df_inmuebles = pd.DataFrame(st.session_state.inmuebles)
    st.session_state.df_inmuebles = df_inmuebles

    df_rodados = pd.DataFrame(st.session_state.rodados)
    st.session_state.df_rodados = df_rodados

    df_pasivo = pd.DataFrame([{
        "Deuda Bancaria / Financiera": deuda_bancos_total,
        "Deuda Mercado de Capitales": deuda_mercado_total,
        "Deuda Comercial": deuda_comercial_total,
        "Otras Deudas": otras_deudas,
        "Total Pasivo": pasivo_total
    }])
    st.session_state.df_pasivo = df_pasivo

    df_ingresos_egresos = pd.DataFrame([{
        "Ingresos Honorarios": ingresos_honorarios,
        "Ingresos Rentas": ingresos_rentas,
        "Ingresos Otros": ingresos_otros,
        "Total Ingresos": ingresos_total,
        "Egresos Honorarios": egresos_honorarios,
        "Egresos Rentas": egresos_rentas,
        "Egresos Otros": egresos_otros,
        "Total Egresos": egresos_total,
        "Diferencia": diferencia
    }])
    st.session_state.df_ingresos_egresos = df_ingresos_egresos

    


@st.cache_data(show_spinner=False)
def obtener_geodatos():
    url_prov = "https://apis.datos.gob.ar/georef/api/provincias"
    prov_resp = requests.get(url_prov).json()
    provincias = sorted([p["nombre"] for p in prov_resp["provincias"]])

    dict_departamentos = {}
    dict_localidades = {}

    for prov in provincias:
        url_dpto = f"https://apis.datos.gob.ar/georef/api/departamentos?provincia={prov}&max=500"
        dpto_resp = requests.get(url_dpto).json()
        departamentos = sorted([d["nombre"] for d in dpto_resp.get("departamentos", [])])
        dict_departamentos[prov] = departamentos

        url_loc = f"https://apis.datos.gob.ar/georef/api/localidades?provincia={prov}&max=5000"
        loc_resp = requests.get(url_loc).json()
        localidades = sorted([l["nombre"] for l in loc_resp.get("localidades", [])])
        dict_localidades[prov] = localidades

    return provincias, dict_departamentos, dict_localidades

provincias, departamentos_por_provincia, localidades_por_provincia = obtener_geodatos()

    #-----Agro-----
with tabs[4]:
    # ✅ Inicialización segura sin sobrescribir progreso
    if "campanias_agricolas" not in st.session_state:
        st.session_state.campanias_agricolas = {
            "23/24": {"nombre_editable": "23/24", "cultivos": []},
            "22/23": {"nombre_editable": "22/23", "cultivos": []},
            "21/22": {"nombre_editable": "21/22", "cultivos": []},
        }

    if "ganaderia_data" not in st.session_state:
        st.session_state.ganaderia_data = {
            "Tambo": [],
            "Base Forrajera": [],
            "Hacienda de terceros": [],
            "Otras Actividades": []
        }

    if "actividad" not in st.session_state:
        st.session_state.actividad = []

    # ✅ Solución definitiva al multiselect para restaurar selección
    seleccion = st.multiselect(
        "**Seleccioná la/las Actividad/es**",
        ["Agricultura", "Ganadería"],
        default=st.session_state.actividad,
        key="actividad_multiselect"
    )
    st.session_state.actividad = seleccion

    # 🔁 Limpiar los bloques si ya no están seleccionados
    if "Agricultura" not in st.session_state.actividad:
        st.session_state.df_agricultura_total = pd.DataFrame()
    if "Ganadería" not in st.session_state.actividad:
        st.session_state.df_ganaderia_total = pd.DataFrame()

   
    


    with st.expander("**Campos**"):
        st.subheader("Campos Propios")
        if "campos_propios" not in st.session_state:
            st.session_state.campos_propios = []

        if st.button("➕ Agregar Campo Propio"):
            st.session_state.campos_propios.append({
                "Nombre": "",
                "Titularidad": "",
                "Localidad": "",
                "Partido": "",
                "Provincia": "",
                "Has": 0.0,
                "Valor U$/ha": 0.0,
                "Has Hipotecadas": 0.0,
                "Estado Actual": ""
            })

        for idx, campo in enumerate(st.session_state.campos_propios):
            st.write(f"**Campo Propio Nro {idx+1}**")
            cols = st.columns(2)
            campo["Nombre"] = cols[0].text_input("Nombre del Campo", campo["Nombre"], key=f"campo_nombre_{idx}")
            campo["Titularidad"] = cols[1].text_input("Titularidad", campo["Titularidad"], key=f"campo_titular_{idx}")
            cols = st.columns(3)
            campo["Provincia"] = cols[0].selectbox("Provincia", provincias, index=provincias.index(campo["Provincia"]) if campo["Provincia"] in provincias else 0, key=f"campo_prov_{idx}")
            campo["Partido"] = cols[1].selectbox("Partido", departamentos_por_provincia.get(campo["Provincia"], []), index=departamentos_por_provincia.get(campo["Provincia"], []).index(campo["Partido"]) if campo["Partido"] in departamentos_por_provincia.get(campo["Provincia"], []) else 0, key=f"campo_partido_{idx}")
            campo["Localidad"] = cols[2].selectbox("Localidad", localidades_por_provincia.get(campo["Provincia"], []), index=localidades_por_provincia.get(campo["Provincia"], []).index(campo["Localidad"]) if campo["Localidad"] in localidades_por_provincia.get(campo["Provincia"], []) else 0, key=f"campo_localidad_{idx}")
            cols2 = st.columns(3)
            campo["Has"] = cols2[0].number_input("Has", value=campo["Has"], key=f"campo_has_{idx}")
            campo["Valor U$/ha"] = cols2[1].number_input("Valor U$/ha", value=campo["Valor U$/ha"], key=f"campo_valor_{idx}")
            campo["Has Hipotecadas"] = cols2[2].number_input("Has Hipotecadas", value=campo["Has Hipotecadas"], key=f"campo_hipoteca_{idx}")
            
            campo["Estado Actual"] = st.text_input("Estado Actual", campo["Estado Actual"], key=f"campo_estado_{idx}")

            if st.button(f"❌ Eliminar Campo Propio Nro {idx+1}"):
                st.session_state.campos_propios.pop(idx)
                st.rerun()
        
            df_campo_propio = pd.DataFrame(st.session_state.campos_propios)
        else:
            df_campo_propio = pd.DataFrame([{
                "Nombre": "",
                "Titularidad": "",
                "Localidad": "",
                "Partido": "",
                "Provincia": "",
                "Has": 0.0,
                "Valor U$/ha": 0.0,
                "Has Hipotecadas": 0.0,
                "Estado Actual": ""
            }])
            

        st.markdown("---")
        st.subheader("Campos Arrendados")
        if "campos_arrendados" not in st.session_state:
            st.session_state.campos_arrendados = []

        if st.button("➕ Agregar Campo Arrendado"):
            st.session_state.campos_arrendados.append({
                "Nombre": "",
                "Titularidad": "",
                "Localidad": "",
                "Partido": "",
                "Provincia": "",
                "Has": 0.0,
                "Precio US$/qq/kg": 0.0,
                "Plazo contratos (años)": 0,
                "Metodología Pago": ""
            })

        for idx, campo in enumerate(st.session_state.campos_arrendados):
            st.write(f"**Campo Arrendado Nro {idx+1}**")
            cols = st.columns(2)
            campo["Nombre"] = cols[0].text_input("Nombre del Campo", campo["Nombre"], key=f"arr_nombre_{idx}")
            campo["Titularidad"] = cols[1].text_input("Titularidad", campo["Titularidad"], key=f"arr_titular_{idx}")
            cols = st.columns(3)
            campo["Provincia"] = cols[0].selectbox("Provincia", provincias, index=provincias.index(campo["Provincia"]) if campo["Provincia"] in provincias else 0, key=f"arr_prov_{idx}")
            campo["Partido"] = cols[1].selectbox("Partido", departamentos_por_provincia.get(campo["Provincia"], []), index=departamentos_por_provincia.get(campo["Provincia"], []).index(campo["Partido"]) if campo["Partido"] in departamentos_por_provincia.get(campo["Provincia"], []) else 0, key=f"arr_partido_{idx}")
            campo["Localidad"] = cols[2].selectbox("Localidad", localidades_por_provincia.get(campo["Provincia"], []), index=localidades_por_provincia.get(campo["Provincia"], []).index(campo["Localidad"]) if campo["Localidad"] in localidades_por_provincia.get(campo["Provincia"], []) else 0, key=f"arr_localidad_{idx}")
            cols2 = st.columns(3)
            campo["Has"] = cols2[0].number_input("Has", value=campo["Has"], key=f"arr_has_{idx}")
            campo["Precio US$/qq/kg"] = cols2[1].number_input("Precio US$/qq/kg", value=campo["Precio US$/qq/kg"], key=f"arr_precio_{idx}")
            campo["Plazo contratos (años)"] = cols2[2].number_input("Plazo contratos (años)", value=campo["Plazo contratos (años)"], key=f"arr_plazo_{idx}")
            campo["Metodología Pago"] = st.text_input("Metodología Pago", campo["Metodología Pago"], key=f"arr_pago_{idx}")

            if st.button(f"❌ Eliminar Campo Arrendado Nro {idx+1}"):
                st.session_state.campos_arrendados.pop(idx)
                st.rerun()
            df_campo_arrendado = pd.DataFrame(st.session_state.campos_arrendados)
        else:
            df_campo_arrendado = pd.DataFrame([{
                "Nombre": "",
                "Titularidad": "",
                "Localidad": "",
                "Partido": "",
                "Provincia": "",
                "Has": 0.0,
                "Precio US$/qq/kg": 0.0,
                "Plazo contratos (años)": 0,
                "Metodología Pago": ""
            }])

    campanias_fijas = ["24/25", "23/24", "22/23"]

    # 🔒 Forzar estructura dict si viene corrupta (lista vieja o mal definida)
    if not isinstance(st.session_state.get("campanias_agricolas", None), dict):
        st.session_state.campanias_agricolas = {}

    # Inicializar campañas si faltan
    for c in campanias_fijas:
        if c not in st.session_state.campanias_agricolas:
            st.session_state.campanias_agricolas[c] = {
                "nombre_editable": c,
                "cultivos": []
            }

    # BLOQUE AGRICULTURA
    if "Agricultura" in st.session_state.actividad:
        with st.expander("**Agricultura**"):
            st.subheader("Campañas Agrícolas")
            opciones_cultivo = ["Maíz", "Soja", "Soja 2da", "Trigo", "Cebada", "Sorgo", "Girasol", "Poroto", "Otros Cultivos"]

            for i, clave in enumerate(campanias_fijas):
                campania = st.session_state.campanias_agricolas[clave]
                años_atras = len(campanias_fijas) - 1 - i

                cols = st.columns([0.5, 1, 0.5])
                titulo = f"##### ➕ **Agregar Indicativo de la Campaña actual:**\n **ej ({clave})**" if años_atras == 0 else f"##### ➕ **Agregar Indicativo de la Campaña {años_atras} año(s) atrás:**\n **ej ({clave})**"
                campania["nombre_editable"] = cols[1].text_input(titulo, value=campania["nombre_editable"], key=f"nombre_editable_{clave}")

                with st.form(key=f"form_agregar_cultivo_{clave}"):
                    st.markdown(f"**Agregar Cultivo para {campania['nombre_editable']}**")

                    columnas = st.columns(3)
                    cultivo_nuevo = columnas[0].selectbox("Cultivo", opciones_cultivo, key=f"nuevo_cultivo_{clave}")
                    otro_cultivo_nuevo = columnas[1].text_input("Otro (si corresponde)", key=f"nuevo_otro_{clave}")
                    has_padm_nuevo = columnas[2].number_input("Has p/adm", min_value=0.0, key=f"nuevo_haspadm_{clave}")

                    cols2 = st.columns(3)
                    has_porcentaje_nuevo = cols2[0].number_input("Has a %", min_value=0.0, key=f"nuevo_porcentaje_{clave}")
                    propio_nuevo = cols2[1].number_input("% Propio", min_value=0.0, max_value=100.0, key=f"nuevo_propio_{clave}")
                    rendimiento_nuevo = cols2[2].number_input("Rendimiento (tn/ha)", min_value=0.0, key=f"nuevo_rend_{clave}")

                    cols3 = st.columns(2)
                    gastos_comerc_nuevo = cols3[0].number_input("Gastos Comerc. y Cosecha (US$/ha)", min_value=0.0, key=f"nuevo_comerc_{clave}")
                    gastos_directos_nuevo = cols3[1].number_input("Gastos Directos (US$/ha)", min_value=0.0, key=f"nuevo_directos_{clave}")

                    cols4 = st.columns(2)
                    stock_nuevo = cols4[0].number_input("Stock actual (tn)", min_value=0.0, key=f"nuevo_stock_{clave}")
                    precio_nuevo = cols4[1].number_input("Precio Actual/Futuro (US$/tn)", min_value=0.0, key=f"nuevo_precio_{clave}")

                    submit = st.form_submit_button("Agregar Cultivo")

                if submit:
                    campania["cultivos"].append({
                        "Cultivo": cultivo_nuevo,
                        "Otro Cultivo": otro_cultivo_nuevo if cultivo_nuevo == "Otros Cultivos" else "",
                        "Has p/adm": has_padm_nuevo,
                        "Has a %": has_porcentaje_nuevo,
                        "% Propio": propio_nuevo,
                        "Rendimiento (tn/ha)": rendimiento_nuevo,
                        "Gastos Comerc. y Cosecha (US$/ha)": gastos_comerc_nuevo,
                        "Gastos Directos (US$/ha)": gastos_directos_nuevo,
                        "Stock actual (tn)": stock_nuevo,
                        "Precio Actual/Futuro (US$/tn)": precio_nuevo
                    })
                    st.success("✅ Cultivo agregado correctamente.")
                    st.rerun()

                if campania["cultivos"]:
                    st.markdown(f"**Resumen para la Campaña {campania['nombre_editable']}**")

                    columnas_fijas = [
                        "Cultivo", "Otro Cultivo", "Has p/adm", "Has a %", "% Propio",
                        "Rendimiento (tn/ha)", "Gastos Comerc. y Cosecha (US$/ha)",
                        "Gastos Directos (US$/ha)", "Stock actual (tn)", "Precio Actual/Futuro (US$/tn)"
                    ]

                    df = pd.DataFrame(campania["cultivos"])
                    for col in columnas_fijas:
                        if col not in df.columns:
                            df[col] = 0.0 if "Has" in col or "US$" in col or "tn" in col or "%" in col else ""
                    df = df[columnas_fijas]
                    st.dataframe(df)

                    cols_elim = st.columns(5)
                    for idx, cultivo in enumerate(campania["cultivos"]):
                        nombre = cultivo["Otro Cultivo"] if cultivo["Cultivo"] == "Otros Cultivos" else cultivo["Cultivo"]
                        col = cols_elim[idx % 3]
                        with col:
                            if st.button(f"❌ Eliminar {nombre}", key=f"delete_{clave}_{idx}"):
                                campania["cultivos"].pop(idx)
                                st.rerun()

            # Consolidar DataFrames para exportador general
            df_agricultura_suma_total = pd.concat([
                pd.DataFrame(st.session_state.campanias_agricolas[clave]["cultivos"]).assign(Campaña=st.session_state.campanias_agricolas[clave]["nombre_editable"])
                for clave in campanias_fijas if st.session_state.campanias_agricolas[clave]["cultivos"]
            ], ignore_index=True)

            columnas_finales = [
                "Campaña", "Cultivo", "Otro Cultivo", "Has p/adm", "Has a %", "% Propio",
                "Rendimiento (tn/ha)", "Gastos Comerc. y Cosecha (US$/ha)",
                "Gastos Directos (US$/ha)", "Stock actual (tn)", "Precio Actual/Futuro (US$/tn)"
            ]

            for col in columnas_finales:
                if col not in df_agricultura_suma_total.columns:
                    df_agricultura_suma_total[col] = 0.0 if "Has" in col or "US$" in col or "tn" in col or "%" in col else ""

            df_agricultura_suma_total = df_agricultura_suma_total[columnas_finales]
            st.session_state.df_agricultura_total = df_agricultura_suma_total
            
        
    pass
                
    
    # === ESTRUCTURA FIJA GANADERÍA (una sola vez al principio del bloque) ===
    actividades = {
        "cria": {
            "titulo": "Ganadería - Cría",
            "categorias": ["Vacas", "Vaquillonas", "Terneros/as", "Toros"],
            "indices": ["% Preñez", "% Parición", "% Destete"]
        },
        "invernada": {
            "titulo": "Ganadería - Invernada",
            "categorias": ["Novillos", "Novillitos", "Vacas descarte", "Vaquillonas"],
            "indices": ["Compras - Cabezas por año", "Compras - Peso Promedio", "Ventas - Cabezas por año", "Ventas - Peso Promedio"]
        },
        "feedlot": {
            "titulo": "Ganadería - Feedlot",
            "categorias": ["Novillos", "Novillitos", "Vacas descarte", "Vaquillonas"],
            "indices": ["Compras - Cabezas por año", "Compras - Peso Promedio", "Tiempo de engorde (meses)", "Ventas - Cabezas por año", "Ventas - Peso Promedio"]
        },
        "tambo": {
            "titulo": "Tambo",
            "categorias": ["Vacas (VO+VS)", "Vaquillonas", "Terneras", "Terneros", "Toros"],
            "indices": ["Lt/día", "Precio US$/Lt", "% VO", "% Grasa butirosa"]
        }
    }

    columnas_base = [
        "Actividad", "Categoría","Propias", "De Terceros", "Precio estimado (US$/cab)",
        "Stock total (Kg)", "Valor total (US$)","Gasto Directo (US$/cab)", "Gasto Comercial (US$/cab)",
        "% Preñez", "% Parición", "% Destete", "Compras - Cabezas por año", "Compras - Peso Promedio",
        "Tiempo de engorde (meses)", "Ventas - Cabezas por año", "Ventas - Peso Promedio",
        "Lt/día", "Precio US$/Lt", "% VO", "% Grasa butirosa"
    ]

    # ✅ Crear DataFrame completo con combinaciones únicas solo una vez
    if "df_ganaderia" not in st.session_state:
        datos_fijos = []
        for act_key, act in actividades.items():
            for cat in act["categorias"] + ["Totales"]:
                fila = {col: 0 for col in columnas_base}
                fila["Actividad"] = act["titulo"]
                fila["Categoría"] = cat
                datos_fijos.append(fila)
        df_base = pd.DataFrame(datos_fijos)
        st.session_state.df_ganaderia = df_base.copy()
    else:
        # Eliminar duplicados por seguridad
        st.session_state.df_ganaderia.drop_duplicates(subset=["Actividad", "Categoría"], inplace=True)

    # === UI y actualización del DataFrame ===
    if "Ganadería" in st.session_state.actividad:
        with st.expander("**Ganadería**"):
            secciones = actividades

            if "ganaderia_seleccionadas" not in st.session_state:
                st.session_state.ganaderia_seleccionadas = []

            seleccionadas = st.multiselect(
                "**Seleccioná la/las Actividad/es a completar:**",
                list(secciones.keys()),
                default=st.session_state.ganaderia_seleccionadas,
                format_func=lambda x: secciones[x]["titulo"],
                key="ganaderia_seleccionadas"
            )

            for clave in seleccionadas:
                info = actividades[clave]
                titulo = info["titulo"]
                categorias = info["categorias"]
                indices = info["indices"]

                st.markdown(f"### {titulo}")
                for cat in categorias:
                    st.markdown(f"**{cat}**")
                    cols = st.columns(4)
                    propias = cols[0].number_input("Propias", key=f"{clave}_{cat}_propias", value=0)
                    terceros = cols[1].number_input("De Terceros", key=f"{clave}_{cat}_terceros", value=0)
                    directo = cols[2].number_input("Gasto Directo (US$/cab)", key=f"{clave}_{cat}_directo", value=0.0)
                    comerc = cols[3].number_input("Gasto Comercial (US$/cab)", key=f"{clave}_{cat}_comerc", value=0.0)

                    st.session_state.df_ganaderia.loc[
                        (st.session_state.df_ganaderia["Actividad"] == titulo) & 
                        (st.session_state.df_ganaderia["Categoría"] == cat),
                        ["Propias", "De Terceros", "Gasto Directo (US$/cab)", "Gasto Comercial (US$/cab)"]
                    ] = [propias, terceros, directo, comerc]

                st.markdown("**Índices Generales**")
                indices_generales = {}
                if len(indices) <= 3:
                    cols = st.columns(len(indices))
                    for i, ind in enumerate(indices):
                        indices_generales[ind] = cols[i].number_input(ind, key=f"{clave}_{ind}", value=0.0)
                else:
                    mitad = (len(indices) + 1) // 2
                    col1, col2 = st.columns(2)
                    for i in range(mitad):
                        ind = indices[i]
                        indices_generales[ind] = col1.number_input(ind, key=f"{clave}_{ind}", value=0.0)
                    for i in range(mitad, len(indices)):
                        ind = indices[i]
                        indices_generales[ind] = col2.number_input(ind, key=f"{clave}_{ind}", value=0.0)

                st.session_state.df_ganaderia.loc[
                    (st.session_state.df_ganaderia["Actividad"] == titulo) & 
                    (st.session_state.df_ganaderia["Categoría"] == "Totales"),
                    list(indices_generales.keys())
                ] = list(indices_generales.values())

            # === Mostrar resumen ===
            st.markdown("##### Resumen Ganadería")
            # Asegurar que todas las columnas de columnas_base existan en el DataFrame
            for col in columnas_base:
                if col not in st.session_state.df_ganaderia.columns:
                    st.session_state.df_ganaderia[col] = 0  # o np.nan si preferís

            # Reordenar el DataFrame antes de mostrarlo
            df_ordenado = st.session_state.df_ganaderia[columnas_base]
            st.dataframe(df_ordenado)
                        
            st.markdown("---")
            st.markdown("## Base Forrajera")
            st.markdown("_Para todas las actividades ganaderas y tambo_")

            col1 = st.columns(1)
            
            pasturas = st.number_input("**Superficie de pasturas en producción (Has)**",min_value=0.0,
                step=0.1,key="pasturas")

            verdeos = st.number_input("**Superficie de verdeos (invierno y verano) (Has)**",min_value=0.0,
                step=0.1,key="verdeos")

            natural = st.number_input("**Superficie de campo natural (Has)**",min_value=0.0,
                step=0.1,key="natural")

            total_superficie = pasturas + verdeos + natural
            st.markdown(f"**Total de superficie ganadera:** {total_superficie:.2f} Has")

            # Guardamos en dataframe
            df_base_forrajera = pd.DataFrame({
                "Categoría": ["Pasturas en producción", "Verdeos (inv/ver)", "Campo natural", "Total"],
                "Has": [pasturas, verdeos, natural, total_superficie]
            })

            st.dataframe(df_base_forrajera)
            # Guardamos en dataframe
            df_base_forrajera = pd.DataFrame({
                "Categoría": ["Pasturas en producción", "Verdeos (inv/ver)", "Campo natural", "Total"],
                "Has": [pasturas, verdeos, natural, total_superficie]
            })

            

            # ✅ Guardar en session_state
            st.session_state.df_base_forrajera = df_base_forrajera

            st.markdown("---")

            st.markdown("## Hacienda de Terceros en Campo Propio")

            categorias = ["Novillos", "Vacas", "Vaquillonas", "Terneros", "Terneras"]
            datos_hacienda = []

            for categoria in categorias:
                col1, col2 = st.columns(2)
                with col1:
                    cantidad = st.number_input(f"{categoria} - Cantidad", min_value=0, step=1, key=f"{categoria}_cant")
                with col2:
                    capitalizacion = st.number_input(
                        f"{categoria} - Pastoreo o capitalización",
                        min_value=0.0,
                        step=0.1,
                        help="Indicar precio o % propio",
                        key=f"{categoria}_cap"
                    )
                datos_hacienda.append([categoria, cantidad, capitalizacion])

            # Creamos el DataFrame
            df_hacienda = pd.DataFrame(datos_hacienda, columns=["Categoría", "Cantidad", "Pastoreo o capitalización"])
            total_cabezas = df_hacienda["Cantidad"].sum()
            df_hacienda.loc[len(df_hacienda.index)] = ["Total", total_cabezas, ""]

            st.markdown(f"**Total:** {total_cabezas} cabezas")

            st.dataframe(df_hacienda)

            # Creamos el DataFrame
            df_hacienda = pd.DataFrame(datos_hacienda, columns=["Categoría", "Cantidad", "Pastoreo o capitalización"])
            total_cabezas = df_hacienda["Cantidad"].sum()
            df_hacienda.loc[len(df_hacienda.index)] = ["Total", total_cabezas, ""]

            st.markdown(f"**Total:** {total_cabezas} cabezas")

            

            # ✅ Guardar en session_state
            st.session_state.df_hacienda = df_hacienda

            st.markdown("---")

            st.markdown("## Otras Actividades")
            st.markdown("_Especificar ingresos anuales_")
            otros_ingresos = st.text_area("Ingresos anuales (descripción)", key="otros_ingresos")

            # Guardamos en DataFrame
            df_otros = pd.DataFrame({
                "Descripción": [otros_ingresos] if otros_ingresos else ["Sin especificar"]
            })

            st.dataframe(df_otros)

            # Guardamos en DataFrame
            df_otros = pd.DataFrame({
                "Descripción": [otros_ingresos] if otros_ingresos else ["Sin especificar"]
            })

            

            # ✅ Guardar en session_state
            st.session_state.df_otros = df_otros
    pass



# Intenta aplanar el diccionario, si hay errores se puede ajustar por sección
try:
    df_respuestas = json_normalize(respuestas, sep=".")
except Exception as e:
    df_respuestas = pd.DataFrame([{"Error al procesar 'respuestas'": str(e)}])
# ---- Exportar hoja: Información General ----
if respuestas:
    df_info_general = pd.DataFrame([respuestas])  # dict -> DataFrame de una fila
else:
    df_info_general = pd.DataFrame(columns=[
        "Razón Social / Nombre y apellido", "Fecha de Inscripción en IGJ", "CUIT", "Teléfono",
        "Calle (real y legal)", "Número (real y legal)", "CP (real y legal)",
        "Provincia (real y legal)", "Localidad (real y legal)",
        "Calle (comercial)", "Número (comercial)", "CP (comercial)",
        "Provincia (comercial)", "Localidad (comercial)",
        "Calle (constituido)", "Número (constituido)", "CP (constituido)",
        "Provincia (constituido)", "Localidad (constituido)", "Electrónico (constituido)",
        "Página web empresarial", "E-mail", 
        "Cantidad de empleados declarados al cierre del último ejercicio",
        "Código de la actividad principal (AFIP según CLAE)",
        "Descripción de la actividad principal (AFIP según CLAE)",
        "Condición de IIBB", "Condición de ganancias", "N° de IIBB", "Sede de IIBB",
        "Apellido y Nombre ", "Cargo ", "TEL / CEL ", "Mail ",
        "Reseña Empresa", "Destino de los fondos"
    ])


# ---- Exportar hoja: Avales y Contragarantías ----
if "avales" in st.session_state and st.session_state.avales:
    df_avales = pd.DataFrame(st.session_state.avales)
    df_avales["Total solicitado"] = sum([a.get("Monto", 0) for a in st.session_state.avales])
else:
    df_avales = pd.DataFrame(columns=[
        "Tipo Aval", "Detalle Aval", "Monto", "Tipo Contragarantía", "Detalle Contragarantía", "Total solicitado"
    ])

# Inmuebles y rodados
if "inmuebles" in st.session_state:
    st.session_state.df_inmuebles = pd.DataFrame(st.session_state.inmuebles)

if "rodados" in st.session_state:
    st.session_state.df_rodados = pd.DataFrame(st.session_state.rodados)

# Deudas
if "deudas_comerciales" in st.session_state:
    st.session_state.deudas_com_df = pd.DataFrame(st.session_state.deudas_comerciales)

if "mercado" in st.session_state:
    st.session_state.mercado_df = pd.DataFrame(st.session_state.mercado)

if "bancos" in st.session_state:
    st.session_state.bancos_df = pd.DataFrame(st.session_state.bancos)
    
# 🧪 Crear el archivo Excel en memoria
output = io.BytesIO()

if "bancos_df" in st.session_state and not st.session_state.bancos_df.empty:
    bancos_df = st.session_state.bancos_df
else:
    bancos_df = pd.DataFrame([{
        "Entidad": "",
        "Saldo Préstamos Amortizables": 0,
        "Garantía (*)": "",
        "Valor de la Cuota": 0,
        "Régimen de Amortización (**)": "",
        "Cantidad Cuotas Faltantes": 0,
        "Descuento de Cheques Utilizado": 0,
        "Adelanto en Cta Cte Utilizado": 0,
        "Avales SGR": 0,
        "Tarjeta de Crédito Utilizado": 0,
        "Leasing Utilizado": 0,
        "Impo/Expo Utilizado": 0,
        "Tasa Promedio $": 0.0,
        "Tasa Promedio USD": 0.0,
        "Tipo de Moneda": "",
        "Total por Banco": 0.0
    }])

if "mercado_df" in st.session_state and not st.session_state.mercado_df.empty:
    mercado_df = st.session_state.mercado_df
else:
    mercado_df = pd.DataFrame([{
        "Obligaciones Negociables": 0,
        "Descuento de Cheques Propios": 0,
        "Pagaré Bursátil": 0,
        "Organismos Multilaterales (CFI)": 0,
        "Otros (1)": 0,
        "Otros (2)": 0,
        "Tasa Promedio $": 0.0,
        "Tasa Promedio USD": 0.0,
        "Tipo de Moneda": "",
        "Total": 0.0
    }])

if "deudas_com_df" in st.session_state and not st.session_state.deudas_com_df.empty:
    deudas_com_df = st.session_state.deudas_com_df
else:
    deudas_com_df = pd.DataFrame([{
        "A favor de": "",
        "Tipo de Moneda": "",
        "Monto": 0.0,
        "Garantía": "",
        "Tasa": 0.0,
        "Plazo (días)": 0
    }])

planes_dict = st.session_state.get("planes_guardados_por_actividad", {})


if "df_inmuebles" in st.session_state and not st.session_state.df_inmuebles.empty:
    df_inmuebles = st.session_state.df_inmuebles
else:
    df_inmuebles = pd.DataFrame([{
        "Tipo": "", "Dirección": "", "Provincia": "", "Destino": "",
        "m2/has": 0, "Valor Fiscal": 0, "Valor Mercado": 0
    }])
if "df_rodados" in st.session_state and not st.session_state.df_rodados.empty:
    df_rodados = st.session_state.df_rodados
else:
    df_rodados = pd.DataFrame([{
        "Tipo": "", "Marca": "", "Valor Fiscal": 0, "Valor Mercado": 0
    }])
# Campos
if "campos_propios" in st.session_state and st.session_state.campos_propios:
    df_campo_propio = pd.DataFrame(st.session_state.campos_propios)
else:
    df_campo_propio = pd.DataFrame([{
        "Provincia": "", "Partido": "", "Localidad": "", "Nombre del Campo": "",
        "Superficie (has)": 0, "Titularidad": "", "Tipo de Tenencia": ""
    }])

if "campos_arrendados" in st.session_state and st.session_state.campos_arrendados:
    df_campo_arrendado = pd.DataFrame(st.session_state.campos_arrendados)
else:
    df_campo_arrendado = pd.DataFrame([{
        "Provincia": "", "Partido": "", "Localidad": "", "Nombre del Campo": "",
        "Superficie (has)": 0, "Titularidad": "", "Tipo de Tenencia": ""
    }])
if "df_agricultura_total" in st.session_state and not st.session_state.df_agricultura_total.empty:
    df_agricultura_suma_total = pd.DataFrame(st.session_state.df_agricultura_total)
else:
    df_agricultura_suma_total = pd.DataFrame([{
        "Campaña": "", "Cultivo": "", "Otro Cultivo": "",
        "Has p/adm": 0, "Has a %": 0, "% Propio": 0,
        "Rendimiento (tn/ha)": 0, "Gastos Comerc. y Cosecha (US$/ha)": 0,
        "Gastos Directos (US$/ha)": 0, "Stock actual (tn)": 0, "Precio Actual/Futuro (US$/tn)": 0
    }])


df_ganaderia = st.session_state.df_ganaderia
if "df_base_forrajera" in st.session_state:
    df_base_forrajera = pd.DataFrame(st.session_state.df_base_forrajera)
else:
    df_base_forrajera = pd.DataFrame([{
            "Categoria": "", "Has": 0
        }])
if "df_hacienda" in st.session_state:
    df_hacienda = pd.DataFrame(st.session_state.df_hacienda)
else:
    df_hacienda = pd.DataFrame([{
        "Categoria": "", "Cantidad de Cabezas": 0,
        "Pastoreo o capitalización": 0.0
    }])
if "df_otros" in st.session_state:
    df_otros = pd.DataFrame(st.session_state.df_otros)
else:
    df_otros = pd.DataFrame([{
            "Descripción": ""
        }])
    
# === BLOQUE DE ASIGNACIONES FALTANTES PARA EXPORTAR CORRECTAMENTE ===
if "filiatorios" in st.session_state:
    st.session_state.df_filiatorios = pd.DataFrame(st.session_state.filiatorios)

if "clientes_a_descontar" in st.session_state:
    st.session_state.df_clientes_a_descontar = pd.DataFrame(st.session_state.clientes_a_descontar)

if "ingresos_egresos" in st.session_state:
    st.session_state.df_ingresos_y_egresos = pd.DataFrame(st.session_state.ingresos_egresos)

if "ventas_interno" in st.session_state:
    st.session_state.df_ventas_interno = pd.DataFrame(st.session_state.ventas_interno)

if "ventas_externo" in st.session_state:
    st.session_state.df_ventas_externo = pd.DataFrame(st.session_state.ventas_externo)

if "campos_propios" in st.session_state:
    st.session_state.df_campos_propios = pd.DataFrame(st.session_state.campos_propios)

if "campos_arrendados" in st.session_state:
    st.session_state.df_campos_arrendados = pd.DataFrame(st.session_state.campos_arrendados)

#if "df_ganaderia" in st.session_state:
    #st.session_state.df_ganadería = st.session_state.df_ganaderia

if "df_hacienda" in st.session_state:
    st.session_state.df_hacienda_de_terceros = st.session_state.df_hacienda

if "df_otros" in st.session_state:
    st.session_state.df_otras_actividades = st.session_state.df_otros

with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_respuestas.to_excel(writer, sheet_name="Respuestas", index=False)
    df_info_general.to_excel(writer, sheet_name="Info General", index=False)
    df_avales.to_excel(writer, sheet_name="Avales", index=False)
    df_filiarorio.to_excel(writer, sheet_name="Filiatorios", index=False)
    df_empresas_controlantes.to_excel(writer, sheet_name="Empresas Controlantes", index=False)
    df_empresas_vinculadas.to_excel(writer, sheet_name="Empresas Vinculadas", index=False)
    df_clientes_descontar.to_excel(writer, sheet_name="Clientes a Descontar", index=False)
    df_proveedores.to_excel(writer, sheet_name="Proveedores", index=False)
    df_clientes.to_excel(writer, sheet_name="Clientes", index=False)
    df_competidores.to_excel(writer, sheet_name="Competidores", index=False)
    df_referencias_bancarias.to_excel(writer, sheet_name="Referencias Bancarias", index=False)

    
    
    bancos_df.to_excel(writer, sheet_name="Deuda Bancaria", index=False)
    mercado_df.to_excel(writer, sheet_name="Deuda Mercado", index=False)
    deudas_com_df.to_excel(writer, sheet_name="Deuda Comercial", index=False)

    df_interno.to_excel(writer, sheet_name="Ventas Interno", index=False)
    df_externo.to_excel(writer, sheet_name="Ventas Externo", index=False)
    df_compras.to_excel(writer, sheet_name="Compras", index=False)

    df_activo_resumen.to_excel(writer, sheet_name="Activo Resumen", index=False)
    df_inmuebles.to_excel(writer, sheet_name="Inmuebles", index=False)
    df_rodados.to_excel(writer, sheet_name="Rodados", index=False)
    df_pasivo.to_excel(writer, sheet_name="Pasivo", index=False)
    df_ingresos_egresos.to_excel(writer, sheet_name="Ingresos y Egresos", index=False)

    df_campo_propio.to_excel(writer, sheet_name="Campos Propios", index=False)
    df_campo_arrendado.to_excel(writer, sheet_name="Campos Arrendados", index=False)
    
    df_agricultura_suma_total.to_excel(writer, sheet_name="Agricultura", index=False)
    
    df_ganaderia.to_excel(writer, sheet_name="Ganadería", index=False)
    
    df_base_forrajera.to_excel(writer, sheet_name="Base Forrajera", index=False)
    
    df_hacienda.to_excel(writer, sheet_name="Hacienda de Terceros", index=False)
    
    df_otros.to_excel(writer, sheet_name="Otras Actividades", index=False)

output.seek(0)



col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("**💾 Guardar progreso para continuar luego**"):
        try:
            # Función para filtrar claves problemáticas
            def clave_permitida(k):
                return not (
                    k.startswith("delete_")
                    or k.startswith("eliminar_cultivo_")
                    or k.startswith("FormSubmitter:")
                    or "Agregar Cultivo" in k
                )

            estado_a_guardar = {
                k: v for k, v in st.session_state.items() if clave_permitida(k)
            }

            with open(PROGRESO_FILE, "wb") as f:
                pickle.dump(estado_a_guardar, f)

            st.success("✅ Progreso guardado correctamente.")
        except Exception as e:
            st.error(f"❌ Error al guardar el progreso: {e}")

with col2:
    # ⬇️ Botón para descargar
    st.download_button(
        label="**⬇️ Descargar Archivo para compartir a QTM Capital**",
        data=output,
        file_name="formulario_completo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ) 


with col3:
    if st.button("**❌ Borrar todo lo ya cargado**"):
        # Guardamos una copia del estado original por si cancela
        st.session_state.estado_anterior = copy.deepcopy(st.session_state)
        st.session_state.confirmar_borrado = True



# === Confirmación del borrado ===
if st.session_state.get("confirmar_borrado", False):
    st.warning("⚠️ ¿Estás seguro de que querés borrar todo lo cargado?")

    col_borrar, col_cancelar = st.columns(2)

    with col_borrar:
        if st.button("**❌ Confirmar Borrado**"):
            # Claves a preservar si necesitás mantener algo
            claves_a_preservar = ["autenticado"]
            claves_preservadas = {
                k: st.session_state[k]
                for k in claves_a_preservar if k in st.session_state
            }

            # Borrar archivo de progreso si existe
            if os.path.exists(PROGRESO_FILE):
                os.remove(PROGRESO_FILE)

            # Limpiar todo el session_state
            st.session_state.clear()

            # Restaurar claves preservadas
            for k, v in claves_preservadas.items():
                st.session_state[k] = v

            # Mostrar advertencia para refrescar
            st.markdown("#####¡Todo fue borrado!")
            st.warning("🚨 **IMPORTANTE:** Refrescá la página (F5 o Ctrl+R) para ver el formulario completamente vacío.")
            st.stop()  

    with col_cancelar:
        if st.button("**🚫 Volver al Inicio**"):
            # Restauramos estado anterior
            estado_restaurado = st.session_state.get("estado_anterior", {})
            preservar = {}
            for clave in ["autenticado"]:
                if clave in st.session_state:
                    preservar[clave] = st.session_state[clave]

            st.session_state.clear()
            for k, v in estado_restaurado.items():
                st.session_state[k] = v
            for k, v in preservar.items():
                st.session_state[k] = v

            st.session_state.confirmar_borrado = False
            st.rerun()
