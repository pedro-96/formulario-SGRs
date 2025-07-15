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
USUARIO = "QTM"
CLAVE = "capital"

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


# === BLOQUE DE IDENTIFICACIÓN DE FORMULARIO ===
if "formulario_identificado" not in st.session_state:
    st.session_state.formulario_identificado = False

if not st.session_state.formulario_identificado:
    st.markdown("### Crear o usar clave para empezar formulario")

    codigo_usuario = st.text_input(
        "Escriba su CUIT/CUIL este será usado como ID para que su formulario sea único",
        max_chars=11,
        placeholder="Ej: 30888888885"
    )

    if not codigo_usuario:
        st.warning("🔑 Ingresá tu CUIT/CUIL para continuar.")
        st.stop()

    st.session_state.codigo_usuario = codigo_usuario
    PROGRESO_FILE = f"progreso_{codigo_usuario}.pkl"

    if os.path.exists(PROGRESO_FILE):
        try:
            with open(PROGRESO_FILE, "rb") as f:
                progreso_guardado = pickle.load(f)
            for k, v in progreso_guardado.items():
                if (
                    not k.startswith("editor_")
                    and not k.startswith("FormSubmitter:")
                    and not k.startswith("delete_")
                    and not k.startswith("guardar_")
                    and not k.startswith("_")
                    and "Agregar" not in k
                ):
                    if k not in st.session_state:
                        st.session_state[k] = v
            st.success(f"✅ Progreso cargado para el CUIT/CUIL'{PROGRESO_FILE}'.")
        except Exception as e:
            st.warning(f"⚠️ No se pudo cargar el progreso anterior: {e}")

    # ⚠️ Clave para ocultar el bloque y refrescar
    st.session_state.formulario_identificado = True
    st.rerun()

else:
    codigo_usuario = st.session_state.get("codigo_usuario", "default")
    PROGRESO_FILE = f"progreso_{codigo_usuario}.pkl"

# Mostrar cartel post-descarga antes del resto del formulario
if st.session_state.get("descarga_confirmada", False):
    st.success("##### ✅ Archivo descargado correctamente")
    st.markdown("**¿Deseás eliminar el progreso guardado y cerrar sesión o continuar completando el formulario?**")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("**❌ Borrar progreso para cerrar la sesión**"):
            try:
                os.remove(PROGRESO_FILE)
                st.session_state.clear()
                st.success("**Progreso eliminado. Podés cerrar esta ventana o recargar para comenzar de nuevo.**")
                st.stop()
            except Exception as e:
                st.error(f"❌ Error al borrar el archivo: {e}")
    with col2:
        if st.button("**⬅️ Seguir cargando el formulario**"):
            # 🔁 Al volver a cargar, marcamos como no identificado para forzar la recarga del pkl
            st.session_state["descarga_confirmada"] = False
            st.session_state["formulario_identificado"] = False 
            st.rerun()

    st.stop()

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
                min_value=datetime.date(1880, 1, 1),
                max_value=datetime.date.today(),
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
            st.session_state.respuestas["CP (real y legal)"] = st.text_input("CP", key="real y legal3")
        
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
            st.session_state.respuestas["CP (comercial)"] = st.text_input("CP", key="comercial3")

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
            st.session_state.respuestas["CP (constituido)"] = st.text_input("CP", key="constituido3")

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



with tabs[1]:
    opciones_garantia = ["", "Fianza / Sola Firma (F)", "Prenda (P)", "Hipoteca (H)", "Warrant (W)", "Forward (FW)", "Cesión (C)", "Plazo Fijo (PF)"]
    opciones_regimen = ["", "Mensual", "Bimestral", "Trimestral", "Semestral", "Anual"]
    monedas = ["ARS", "USD"]

    # Inicialización de dataframes en session_state si no existen
    if "bancos" not in st.session_state:
        st.session_state.bancos = pd.DataFrame([{
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
        }] * 2)

    if "mercado" not in st.session_state:
        st.session_state.mercado = pd.DataFrame([{
            "Obligaciones Negociables": 0,
            "Descuento de Cheques Propios": 0,
            "Pagaré Bursátil": 0,
            "Organismos Multilaterales (CFI)": 0,
            "Otros (1)": "",
            "Otros (2)": "",
            "Tasa Promedio $": 0.0,
            "Tasa Promedio USD": 0.0,
            "Tipo de Moneda": "ARS"
        }] * 2)

    if "deudas_comerciales" not in st.session_state:
        st.session_state.deudas_comerciales = pd.DataFrame([{
            "A favor de": "",
            "Tipo de Moneda": "ARS",
            "Monto": 0.0,
            "Garantía": "",
            "Tasa": 0.0,
            "Plazo (días)": 0
        }] * 2)

    # ============ BLOQUE DEUDA BANCARIA ============
    with st.expander(" **Deuda Bancaria y Financieras**"):
        bancos_df = st.session_state.bancos.copy()
        bancos_editado = st.data_editor(
            bancos_df,
            key="editor_bancos",
            num_rows="dynamic",
            column_config={
                "Garantía (*)": st.column_config.SelectboxColumn("Garantía (*)", options=opciones_garantia),
                "Régimen de Amortización (**)": st.column_config.SelectboxColumn("Régimen de Amortización (**)", options=opciones_regimen),
                "Tipo de Moneda": st.column_config.SelectboxColumn("Tipo de Moneda", options=monedas)
            },
            use_container_width=True
        )
        if st.button("Guardar Deuda Bancaria", key="guardar_bancos_btn"):
            st.session_state.bancos = bancos_editado
            st.success("✅ Deuda bancaria actualizada.")

    # ============ BLOQUE DEUDA MERCADO ============
    with st.expander(" **Deuda Mercado de Capitales**"):
        mercado_df = st.session_state.mercado.copy()
        mercado_editado = st.data_editor(
            mercado_df,
            key="editor_mercado",
            num_rows="dynamic",
            column_config={
                "Tipo de Moneda": st.column_config.SelectboxColumn("Tipo de Moneda", options=monedas)
            },
            use_container_width=True
        )
        if st.button("Guardar Deuda Mercado", key="guardar_mercado_btn"):
            st.session_state.mercado = mercado_editado
            st.success("✅ Deuda del mercado actualizada.")

    # ============ BLOQUE DEUDA COMERCIAL ============
    with st.expander(" **Deuda Comercial**"):
        comercial_df = st.session_state.deudas_comerciales.copy()
        comercial_editado = st.data_editor(
            comercial_df,
            key="editor_comercial",
            num_rows="dynamic",
            column_config={
                "Tipo de Moneda": st.column_config.SelectboxColumn("Tipo de Moneda", options=monedas)
            },
            use_container_width=True
        )
        if st.button("Guardar Deuda Comercial", key="guardar_comercial_btn"):
            st.session_state.deudas_comerciales = comercial_editado
            st.success("✅ Deuda comercial actualizada.")



with tabs[2]:
    # === CONFIGURACIONES INICIALES ===
    opciones_tipo = ["COMPLETAR", "AGROPECUARIO", "INDUSTRIA", "COMERCIO", "SERVICIOS", "CONSTRUCCION"]
    subcategorias_agro = ["COMPLETAR", "AGRICULTURA", "GANADERIA", "TAMBO", "OTROS"]
    meses_largos = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    # Inicialización si no existen
    for key in ["ventas_interno", "ventas_externo", "compras"]:
        if key not in st.session_state:
            filas_iniciales = []
            for mes in meses_largos:
                fila = {
                    "Mes": mes,
                    "Tipo": "COMPLETAR",
                    "Subtipo": "COMPLETAR",
                    "Año en curso": 0.0,
                    "Año 1": 0.0,
                    "Año 2": 0.0,
                    "Año 3": 0.0
                }
                if key == "ventas_externo":
                    fila["Región"] = ""
                filas_iniciales.append(fila)
            st.session_state[key] = pd.DataFrame(filas_iniciales)

    def agregar_fila(df_name, mes_seleccionado):
        df = st.session_state[df_name]
        nueva_fila = {
            "Mes": mes_seleccionado,
            "Tipo": "COMPLETAR",
            "Subtipo": "COMPLETAR",
            "Año en curso": 0.0,
            "Año 1": 0.0,
            "Año 2": 0.0,
            "Año 3": 0.0,
        }
        if df_name == "ventas_externo":
            nueva_fila["Región"] = ""

        idxs = df.index[df["Mes"] == mes_seleccionado].tolist()
        insertar_idx = idxs[-1] + 1 if idxs else len(df)

        nuevo_df = pd.concat([
            df.iloc[:insertar_idx],
            pd.DataFrame([nueva_fila]),
            df.iloc[insertar_idx:]
        ]).reset_index(drop=True)

        st.session_state[df_name] = nuevo_df

    def mostrar_bloque_data_editor(nombre_bloque, df_name, incluir_region=False):
        st.markdown(f"#### {nombre_bloque}")
        df = st.session_state[df_name].copy()

        columnas_editor = {
            "Mes": st.column_config.SelectboxColumn("Mes", options=meses_largos),
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=opciones_tipo),
            "Subtipo": st.column_config.SelectboxColumn("Subtipo", options=subcategorias_agro),
            "Año en curso": st.column_config.NumberColumn("Año en curso", step=100.0, format="%.3f"),
            "Año 1": st.column_config.NumberColumn("Año 1", step=100.0, format="%.3f"),
            "Año 2": st.column_config.NumberColumn("Año 2", step=100.0, format="%.3f"),
            "Año 3": st.column_config.NumberColumn("Año 3", step=100.0, format="%.3f"),
        }
        if incluir_region:
            columnas_editor["Región"] = st.column_config.TextColumn("Región")

        df_editado = st.data_editor(
            df,
            key=f"editor_{df_name}",
            use_container_width=True,
            num_rows="dynamic",
            column_config=columnas_editor,
            hide_index=True
        )

        if st.button(f"💾 Guardar cambios en {nombre_bloque}", key=f"guardar_{df_name}"):
            st.session_state[df_name] = df_editado
            st.success("✅ Cambios guardados.")

        if not st.session_state[df_name].empty:
            resumen = st.session_state[df_name].groupby("Tipo")[["Año en curso", "Año 1", "Año 2", "Año 3"]].sum()
            st.markdown("##### Resumen por tipo")
            st.dataframe(resumen.style.format("${:,.3f}"))
        else:
            st.info("Todavía no hay datos cargados.")

    with st.expander("**Ventas Mercado Interno (Netas de IVA)**", expanded=False):
        mostrar_bloque_data_editor("Ventas - Mercado Interno (Netas de IVA)", "ventas_interno")

    with st.expander("**Ventas Mercado Externo (Netas de IVA)**", expanded=False):
        mostrar_bloque_data_editor("Ventas - Mercado Externo (Netas de IVA)", "ventas_externo", incluir_region=True)

    with st.expander("**Compras (Netas de IVA)**", expanded=False):
        mostrar_bloque_data_editor("Compras Mensuales (Netas de IVA)", "compras")

   # === PLAN DE VENTAS POR ACTIVIDAD ===
    PRODUCTOS_AGRICULTURA = ["Trigo", "Maíz", "Soja", "Girasol"]
    CATEGORIAS_GANADERIA = ["Novillos", "Vaquillonas", "Terneros", "Vacas"]

    def crear_df_ventas(meses, columnas):
        data = {"Mes": meses}
        for col in columnas:
            data[col] = [0.0] * len(meses)
        return pd.DataFrame(data)

    if "planes_guardados_por_actividad" not in st.session_state:
        st.session_state.planes_guardados_por_actividad = {}

    with st.expander("**Plan de Ventas por Actividad**", expanded=False):
        st.markdown("##### Seleccioná las actividades que realizás:")
        actividades = st.multiselect(
            "Actividades productivas",
            ["Agricultura", "Ganadería", "Tambo", "Otros"],
            default=["Agricultura"]
        )

        st.markdown("#### Comercialización y proveedores")
        comercializa = {}
        proveedores = {}
        cols_com, cols_prov = st.columns(2)

        for act in actividades:
            comercializa[act] = cols_com.text_input(f"¿Con quién comercializa en {act}?", key=f"com_{act}")
            proveedores[act] = cols_prov.text_input(f"Principales proveedores en {act}", key=f"prov_{act}")

        st.session_state.respuestas.update({
            "Comercializa": comercializa,
            "Proveedores": proveedores
        })

        st.divider()
        st.markdown("##### Plan de ventas mensual por actividad")

        for act in actividades:
            st.markdown(f"##### {act}")
            if act == "Agricultura":
                columnas = PRODUCTOS_AGRICULTURA
            elif act == "Ganadería":
                columnas = CATEGORIAS_GANADERIA
            elif act == "Tambo":
                columnas = ["Litros"]
            elif act == "Otros":
                nombre_actividad = st.text_input("Nombre de la actividad", key="otros_nombre")
                if nombre_actividad:
                    columnas = [nombre_actividad]
                else:
                    continue
            else:
                continue

            # Usamos la clave dentro de planes_guardados_por_actividad
            if act in st.session_state.planes_guardados_por_actividad:
                df_temp = st.session_state.planes_guardados_por_actividad[act].copy()
            else:
                df_temp = crear_df_ventas(meses_largos, columnas)

            column_config = {
                col: st.column_config.NumberColumn(col, format="%.3f")
                for col in columnas
            }
            column_config["Mes"] = st.column_config.SelectboxColumn("Mes", options=meses_largos)

            # Usamos una clave de widget distinta para evitar conflictos
            widget_key = f"editor_actividad_{act}"

            edited_df = st.data_editor(
                df_temp,
                key=widget_key,
                use_container_width=True,
                num_rows="fixed",
                column_config=column_config
            )

            # Solo guardamos en planes_guardados_por_actividad
            st.session_state.planes_guardados_por_actividad[act] = edited_df

      
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

        



# ================== CAMPOS PROPIOS ==================
with tabs[3]:
    # ================== CONFIGURACIÓN GENERAL ==================
    cultivos = ["Maíz", "Soja", "Soja 2da", "Trigo", "Cebada", "Sorgo", "Girasol", "Poroto", "Otros Cultivos"]
    metodologias_pago = ["Porcentaje de rinde", "Precio fijo", "Mixto"]

    with st.expander("**Campos**"):
        st.subheader("Campos Propios")

        # Inicialización
        if "df_campos" not in st.session_state:
            st.session_state.df_campos = pd.DataFrame({
                "Nombre del Campo": [f"Ejemplo {i+1}" for i in range(8)],
                "Provincia": ["" for _ in range(8)],
                "Partido": ["" for _ in range(8)],
                "Localidad": ["" for _ in range(8)],
                "Titularidad": ["" for _ in range(8)],
                "Has": [0.0 for _ in range(8)],
                "Valor U$/ha": [0.0 for _ in range(8)],
                "Has Hipotecadas": [0.0 for _ in range(8)],
                "Estado Actual": ["" for _ in range(8)],
            })

        df_campos_tmp = st.data_editor(
            st.session_state.df_campos.copy(),
            key="editor_df_campos",
            num_rows="dynamic",
            use_container_width=True
        )

        if st.button("💾 Guardar Campos Propios"):
            st.session_state.df_campos = df_campos_tmp
            st.success("✅ Campos propios actualizados.")

        st.divider()
        st.subheader("Campos Arrendados")

        # Inicialización
        if "df_campos_arrendados" not in st.session_state:
            st.session_state.df_campos_arrendados = pd.DataFrame({
                "Nombre del Campo": [f"Ejemplo Arrendado {i+1}" for i in range(8)],
                "Provincia": ["" for _ in range(8)],
                "Partido": ["" for _ in range(8)],
                "Localidad": ["" for _ in range(8)],
                "Arrendador": ["" for _ in range(8)],
                "Has Arrendadas": [0.0 for _ in range(8)],
                "Valor U$/ha": [0.0 for _ in range(8)],
                "Metodología de Pago": ["" for _ in range(8)],
                "Duración del Contrato": ["" for _ in range(8)],
            })

        df_arrendados_tmp = st.data_editor(
            st.session_state.df_campos_arrendados.copy(),
            key="editor_df_campos_arrendados",
            column_config={
                "Metodología de Pago": st.column_config.SelectboxColumn("Metodología de Pago", options=metodologias_pago)
            },
            num_rows="dynamic",
            use_container_width=True
        )

        if st.button("💾 Guardar Campos Arrendados"):
            st.session_state.df_campos_arrendados = df_arrendados_tmp
            st.success("✅ Campos arrendados actualizados.")

    # ================== AGRICULTURA ==================

    with st.expander("**Agricultura**"):
        cultivos = ["Maíz", "Soja", "Soja 2da", "Trigo", "Cebada", "Sorgo", "Girasol", "Poroto", "Otros Cultivos"]
        indicadores = [
            "Has p/adm", "Has a %", "% Propio", "Rendimiento (tn/ha)",
            "Gastos Comerc. y Cosecha (US$/ha)", "Gastos Directos (US$/ha)",
            "Stock actual (tn)", "Precio Actual/Futuro (US$/tn)"
        ]
        campanias_fijas = {
            "actual": "ej 24/25",
            "hace_1": "ej 23/24",
            "hace_2": "ej 22/23"
        }

        # Inicialización si no existe
        if "agricultura_por_campania" not in st.session_state:
            st.session_state.agricultura_por_campania = {}
            for clave in campanias_fijas.values():
                st.session_state.agricultura_por_campania[clave] = pd.DataFrame(
                    0.0, index=indicadores, columns=cultivos
                )

        if "nombres_visibles_campanias" not in st.session_state:
            st.session_state.nombres_visibles_campanias = {
                "actual": "Campaña Actual",
                "hace_1": "Campaña hace 1 año",
                "hace_2": "Campaña hace 2 años"
            }

        for clave_logica, clave_real in campanias_fijas.items():
            st.divider()

            # Editar nombre visible de la campaña
            nombre_visible = st.text_input(
                f"📝 Nombre de la campaña {clave_logica.replace('_', ' ')} ({clave_real})",
                value=st.session_state.nombres_visibles_campanias.get(clave_logica, f"Campaña {clave_real}"),
                key=f"nombre_editable_{clave_logica}"
            )
            st.session_state.nombres_visibles_campanias[clave_logica] = nombre_visible
            st.subheader(nombre_visible)

            # Obtener copia para edición
            df_agro = st.session_state.agricultura_por_campania.get(clave_real, pd.DataFrame(
                0.0, index=indicadores, columns=cultivos
            )).copy()

            df_agro_editado = st.data_editor(
                df_agro,
                key=f"editor_agro_{clave_real}",
                num_rows="fixed",
                use_container_width=True
            )

            if st.button(f"💾 Guardar {nombre_visible}", key=f"guardar_agro_{clave_real}"):
                st.session_state.agricultura_por_campania[clave_real] = df_agro_editado
                st.success(f"✅ {nombre_visible} actualizada.")

    # === GANADERÍA (CORREGIDO) ===
    with st.expander("**Ganadería**"):

        def mostrar_editor_dataframe(nombre_df, key_widget, default_df):
            # Evitar conflicto: eliminar key del widget
            st.session_state.pop(key_widget, None)

            # Inicializar si no existe o viene mal del .pkl
            if nombre_df not in st.session_state or not isinstance(st.session_state[nombre_df], pd.DataFrame):
                try:
                    st.session_state[nombre_df] = pd.DataFrame(st.session_state[nombre_df])
                except:
                    st.session_state[nombre_df] = default_df

            # Editor
            df_editado = st.data_editor(
                st.session_state[nombre_df],
                key=key_widget,
                use_container_width=True,
                num_rows="fixed"
            )

            # Guardar si cambió
            if not df_editado.equals(st.session_state[nombre_df]):
                st.session_state[nombre_df] = df_editado

        # Cría
        st.subheader("Cría")
        mostrar_editor_dataframe(
            "df_cria", "df_cria_editor",
            pd.DataFrame(0.0, index=["Propias", "De Terceros", "Gasto Directo (US$/cab)", "Gasto Comercial (US$/cab)"],
                        columns=["Vacas", "Vaquillonas", "Terneros/as", "Toros"])
        )
        mostrar_editor_dataframe(
            "indices_cria", "indices_cria_editor",
            pd.DataFrame({"\u00cdtem": ["% Preñez", "% Parición", "% Destete"], "Valor": [0.0, 0.0, 0.0]})
        )

        st.markdown("---")

        # Invernada
        st.subheader("Invernada")
        mostrar_editor_dataframe(
            "df_invernada", "df_invernada_editor",
            pd.DataFrame(0.0, index=["Propias", "De Terceros", "Gasto Directo (US$/cab)", "Gasto Comercial (US$/cab)"],
                        columns=["Novillos", "Novillitos", "Vacas Descarte", "Vaquillonas"])
        )
        mostrar_editor_dataframe(
            "indices_invernada", "indices_invernada_editor",
            pd.DataFrame({"\u00cdtem": ["Compras (cabezas/año)", "Ventas (cabezas/año)", "Peso Promedio Compras", "Peso Promedio Ventas"],
                        "Valor": [0.0, 0.0, 0.0, 0.0]})
        )

        st.markdown("---")

        # Feedlot
        st.subheader("Feedlot")
        mostrar_editor_dataframe(
            "df_feedlot", "df_feedlot_editor",
            pd.DataFrame(0.0, index=["Propias", "De Terceros", "Gasto Directo (US$/cab)", "Gasto Comercial (US$/cab)"],
                        columns=["Novillos", "Novillitos", "Vacas Descarte", "Vaquillonas"])
        )
        mostrar_editor_dataframe(
            "indices_feedlot", "indices_feedlot_editor",
            pd.DataFrame({"\u00cdtem": ["Compras (cabezas/año)", "Ventas (cabezas/año)", "Peso Promedio Compras", "Peso Promedio Ventas"],
                        "Valor": [0.0, 0.0, 0.0, 0.0]})
        )

        st.markdown("---")

        # Tambo
        st.subheader("Tambo")
        mostrar_editor_dataframe(
            "df_tambo", "df_tambo_editor",
            pd.DataFrame(0.0, index=["Propias", "De Terceros", "Gasto Directo (US$/cab)", "Gasto Comercial (US$/cab)"],
                        columns=["Vacas (VO+VS)", "Vaquillonas", "Terneras", "Terneros", "Toros"])
        )
        mostrar_editor_dataframe(
            "indices_tambo", "indices_tambo_editor",
            pd.DataFrame({"\u00cdtem": ["Lt/día", "Precio US$/Lt", "% VO", "% Grasa Butirosa"], "Valor": [0.0, 0.0, 0.0, 0.0]})
        )

        st.markdown("---")

        # Base Forrajera
        st.subheader("Base Forrajera")
        mostrar_editor_dataframe(
            "df_base_forrajera", "base_forrajera_editor",
            pd.DataFrame({"Categoria": ["Alfalfa", "Sorgo", "Maíz", "Pastura Natural"], "Has": [0.0]*4})
        )

        st.markdown("---")

        # Hacienda de terceros
        st.subheader("Hacienda de terceros")
        mostrar_editor_dataframe(
            "df_hacienda", "df_hacienda_editor",
            pd.DataFrame({
                "Categoría": ["Novillos", "Vacas", "Vaquillonas", "Terneros", "Terneras", "Total"],
                "Cantidad": [0]*6,
                "Pastoreo o capitalización (Precio o % Propio)": [0.0]*6
            })
        )

        st.markdown("---")

        # Otras Actividades
        st.subheader("Otras Actividades")
        mostrar_editor_dataframe(
            "df_otros", "df_otros_editor",
            pd.DataFrame({"Descripción": ["Sin especificar"]})
        )

        st.markdown("---")

        # Botón para confirmar guardado del bloque completo de Ganadería
        if st.button("💾 Guardar todo el bloque de Ganadería", key="guardar_bloque_ganaderia"):
            st.success("✅ Todo el bloque de Ganadería fue guardado correctamente.")


        








# === BLOQUE EXPORTACIÓN COMPLETA ===
output = io.BytesIO()

# Convertir Agricultura por campaña en único DataFrame usando los nombres personalizados
campanias_fijas = {
    "actual": "ej 24/25",
    "hace_1": "ej 23/24",
    "hace_2": "ej 22/23"
}
nombres_visibles = st.session_state.get("nombres_visibles_campanias", {})

df_agricultura_total = []

for clave_logica, clave_real in campanias_fijas.items():
    df = st.session_state.get("agricultura_por_campania", {}).get(clave_real)
    if isinstance(df, pd.DataFrame) and not df.empty:
        nombre_visible = nombres_visibles.get(clave_logica, clave_real)
        df_temp = df.copy()
        df_temp.insert(0, "Campaña", nombre_visible)
        df_agricultura_total.append(df_temp)

df_agricultura = pd.concat(df_agricultura_total, ignore_index=True) if df_agricultura_total else pd.DataFrame()

# Convertir planes de ventas por actividad en Ganadería a un DataFrame
df_ganaderia = pd.DataFrame()
if "planes_guardados_por_actividad" in st.session_state and "Ganadería" in st.session_state.planes_guardados_por_actividad:
    df_ganaderia = st.session_state.planes_guardados_por_actividad["Ganadería"]

# Crear helper
def crear_df(contenido, columnas):
    if isinstance(contenido, pd.DataFrame):
        return contenido if not contenido.empty else pd.DataFrame(columns=columnas)
    elif contenido:
        return pd.DataFrame(contenido)
    else:
        return pd.DataFrame(columns=columnas)

# Respuestas
respuestas = st.session_state.get("respuestas", {})
df_respuestas = pd.json_normalize(respuestas, sep=".") if respuestas else pd.DataFrame()
df_info_general = pd.DataFrame([respuestas]) if respuestas else pd.DataFrame()


# Hojas reales
df_avales = crear_df(st.session_state.get("avales", []), ["Tipo Aval", "Detalle Aval", "Monto", "Tipo Contragarantía", "Detalle Contragarantía"])
if not df_avales.empty:
    df_avales["Total solicitado"] = df_avales["Monto"].sum()

df_filiatorios = crear_df(st.session_state.get("filiatorios", []), ["Nombre y Apellido", "CUIT / CUIL", "Cargo", "% Participación", "Estado Civil", "Nombre Cónyuge", "Fiador"])
df_empresas_controlantes = crear_df(st.session_state.get("empresas_controlantes", []), ["Razón Social", "CUIT", "% de Participación", "Código de la actividad principal"])
df_empresas_vinculadas = crear_df(st.session_state.get("empresas_vinculadas", []), ["Razón Social", "CUIT", "% de Participación", "Código de la actividad principal"])
df_clientes_descontar = crear_df(st.session_state.get("clientes_descontar", []), ["Denominación", "CUIT", "Tipo", "Modalidad de Cobro", "Descuenta de Cheques"])
df_proveedores = crear_df(st.session_state.get("proveedores", []), ["Denominación", "CUIT", "Teléfono", "Local o Exterior", "Modalidad de Pago", "Plazo en Días", "% Compras"])
df_clientes = crear_df(st.session_state.get("clientes", []), ["Denominación", "CUIT", "Teléfono", "Local o Exterior", "Modalidad de Pago", "Plazo en Días", "% Ventas"])
df_competidores = crear_df(st.session_state.get("competidores", []), ["Denominación", "CUIT", "Teléfono", "Segmento", "Participacion del Mercado %", "Condiciones de ventas"])
df_referencias_bancarias = crear_df(st.session_state.get("referencias_bancarias", []), ["Entidad Financiera", "Contacto", "Sucursal", "Tel", "Mail"])
df_bancos = crear_df(st.session_state.get("bancos", []), [
    "Entidad", "Saldo Préstamos Amortizables", "Garantía (*)", "Valor de la Cuota",
    "Régimen de Amortización (**)", "Cantidad Cuotas Faltantes", "Descuento de Cheques Utilizado",
    "Adelanto en Cta Cte Utilizado", "Avales SGR", "Tarjeta de Crédito Utilizado", "Leasing Utilizado",
    "Impo/Expo Utilizado", "Tasa Promedio $", "Tasa Promedio USD", "Tipo de Moneda"
])
df_mercado = crear_df(st.session_state.get("mercado", []), [
    "Obligaciones Negociables", "Descuento de Cheques Propios", "Pagaré Bursátil",
    "Organismos Multilaterales (CFI)", "Otros (1)", "Otros (2)", "Tasa Promedio $",
    "Tasa Promedio USD", "Tipo de Moneda"
])
df_deudas_com = crear_df(st.session_state.get("deudas_comerciales", []), ["A favor de", "Tipo de Moneda", "Monto", "Garantía", "Tasa", "Plazo (días)"])
df_ventas_interno = crear_df(st.session_state.get("ventas_interno", []), ["Mes", "Tipo", "Subtipo", "Año en curso", "Año 1", "Año 2", "Año 3"])
df_ventas_externo = crear_df(st.session_state.get("ventas_externo", []), ["Mes", "Tipo", "Subtipo", "Año en curso", "Año 1", "Año 2", "Año 3", "Región"])
df_compras = crear_df(st.session_state.get("compras", []), ["Mes", "Tipo", "Subtipo", "Año en curso", "Año 1", "Año 2", "Año 3"])
df_campos_propios = crear_df(st.session_state.get("df_campos", []), ["Nombre del Campo", "Provincia", "Partido", "Localidad", "Titularidad", "Has", "Valor U$/ha", "Has Hipotecadas", "Estado Actual"])
df_campos_arrendados = crear_df(st.session_state.get("df_campos_arrendados", []), ["Nombre del Campo", "Provincia", "Partido", "Localidad", "Arrendador", "Has Arrendadas", "Valor U$/ha", "Metodología de Pago", "Duración del Contrato"])

df_base_forrajera = crear_df(st.session_state.get("df_base_forrajera", []), ["Categoria", "Has"])

df_hacienda = crear_df(st.session_state.get("df_hacienda", []), ["Categoria", "Cantidad de Cabezas", "Pastoreo o capitalización"])
df_otros = crear_df(st.session_state.get("df_otros", []), ["Descripción"])

def dict_a_texto(tabla):
    """Convierte una lista de dicts en texto concatenado por filas"""
    if isinstance(tabla, list) and tabla:
        return "\n".join([", ".join([f"{k}: {v}" for k, v in fila.items()]) for fila in tabla])
    return ""

dict_final_tab0 = st.session_state.get("respuestas", {}).copy()

# Agregar las tablas resumidas como texto (una sola celda por tabla)
dict_final_tab0["Resumen Avales"] = dict_a_texto(st.session_state.get("avales", []))
dict_final_tab0["Resumen Filiatorios"] = dict_a_texto(st.session_state.get("filiatorios", []))
dict_final_tab0["Resumen Empresas Controlantes"] = dict_a_texto(st.session_state.get("empresas_controlantes", []))
dict_final_tab0["Resumen Empresas Vinculadas"] = dict_a_texto(st.session_state.get("empresas_vinculadas", []))
dict_final_tab0["Resumen Clientes a Descontar"] = dict_a_texto(st.session_state.get("clientes_descontar", []))
dict_final_tab0["Resumen Proveedores"] = dict_a_texto(st.session_state.get("proveedores", []))
dict_final_tab0["Resumen Clientes"] = dict_a_texto(st.session_state.get("clientes", []))
dict_final_tab0["Resumen Competidores"] = dict_a_texto(st.session_state.get("competidores", []))
dict_final_tab0["Resumen Referencias Bancarias"] = dict_a_texto(st.session_state.get("referencias_bancarias", []))

# Convertir en DataFrame de una sola fila
df_info_general_unificado = json_normalize(dict_final_tab0, sep=".")


# --- Plan de Ventas por Actividad ---
df_planes_ventas_actividad = []

for actividad, df in st.session_state.get("planes_guardados_por_actividad", {}).items():
    if isinstance(df, pd.DataFrame):
        df_temp = df.copy()
        df_temp.insert(0, "Actividad", actividad)
        df_planes_ventas_actividad.append(df_temp)

df_planes_ventas = pd.concat(df_planes_ventas_actividad, ignore_index=True) if df_planes_ventas_actividad else pd.DataFrame()



# === Exportar Índices de Ganadería con chequeo robusto ===
def exportar_indices(nombre_df, nombre_hoja, columnas=["Ítem", "Valor"]):
    df = st.session_state.get(nombre_df)
    if isinstance(df, pd.DataFrame) and not df.dropna(how="all").empty:
        df = df.reset_index(drop=True)
        df.to_excel(writer, sheet_name=nombre_hoja, index=False)
    else:
        pd.DataFrame(columns=columnas).to_excel(writer, sheet_name=nombre_hoja, index=False)
# Nuevos bloques que faltan exportar
df_cria = crear_df(st.session_state.get("df_cria", []), ["Vacas", "Vaquillonas", "Terneros/as", "Toros"])
df_indices_cria = crear_df(st.session_state.get("df_indices_cria", []), ["Índice", "Valor"])
df_invernada = crear_df(st.session_state.get("df_invernada", []), ["Novillos", "Novillitos", "Vacas Descarte", "Vaquillonas"])
df_indices_invernada = crear_df(st.session_state.get("df_indices_invernada", []), ["Ítem", "Valor"])
df_feedlot = crear_df(st.session_state.get("df_feedlot", []), ["Novillos", "Novillitos", "Vacas Descarte", "Vaquillonas"])
df_indices_feedlot = crear_df(st.session_state.get("df_indices_feedlot", []), ["Ítem", "Valor"])
df_tambo = crear_df(st.session_state.get("df_tambo", []), ["Vacas (VO+VS)", "Vaquillonas", "Terneras", "Terneros", "Toros"])
df_indices_tambo = crear_df(st.session_state.get("df_indices_tambo", []), ["Ítem", "Valor"])

# Guardar a Excel
with pd.ExcelWriter(output, engine="openpyxl") as writer:
    #df_respuestas.to_excel(writer, sheet_name="Respuestas", index=False)
    #df_info_general.to_excel(writer, sheet_name="Respuestas Simples", index=False)
    df_info_general_unificado.to_excel(writer, sheet_name="Resumen Info General", index=False)
    df_avales.to_excel(writer, sheet_name="Avales", index=False)
    df_filiatorios.to_excel(writer, sheet_name="Filiatorios", index=False)
    df_empresas_controlantes.to_excel(writer, sheet_name="Empresas Controlantes", index=False)
    df_empresas_vinculadas.to_excel(writer, sheet_name="Empresas Vinculadas", index=False)
    df_clientes_descontar.to_excel(writer, sheet_name="Clientes a Descontar", index=False)
    df_proveedores.to_excel(writer, sheet_name="Proveedores", index=False)
    df_clientes.to_excel(writer, sheet_name="Clientes", index=False)
    df_competidores.to_excel(writer, sheet_name="Competidores", index=False)
    df_referencias_bancarias.to_excel(writer, sheet_name="Referencias Bancarias", index=False)

    df_bancos.to_excel(writer, sheet_name="Deuda Bancaria", index=False)
    df_mercado.to_excel(writer, sheet_name="Deuda Mercado", index=False)
    df_deudas_com.to_excel(writer, sheet_name="Deuda Comercial", index=False)

    df_ventas_interno.to_excel(writer, sheet_name="Ventas Interno", index=False)
    df_ventas_externo.to_excel(writer, sheet_name="Ventas Externo", index=False)
    df_compras.to_excel(writer, sheet_name="Compras", index=False)
    df_planes_ventas.to_excel(writer, sheet_name="Plan Ventas Actividad", index=False)

    df_campos_propios.to_excel(writer, sheet_name="Campos Propios", index=False)
    df_campos_arrendados.to_excel(writer, sheet_name="Campos Arrendados", index=False)
    df_agricultura.to_excel(writer, sheet_name="Agricultura", index=False)
    df_ganaderia.to_excel(writer, sheet_name="Ganadería", index=False)
    df_base_forrajera.to_excel(writer, sheet_name="Base Forrajera", index=False)
    df_hacienda.to_excel(writer, sheet_name="Hacienda de Terceros", index=False)
    df_otros.to_excel(writer, sheet_name="Otras Actividades", index=False)

    # === En bloque de exportación de Excel ===
    df_cria.to_excel(writer, sheet_name="Cría", index=True)
    df_invernada.to_excel(writer, sheet_name="Invernada", index=True)
    df_feedlot.to_excel(writer, sheet_name="Feedlot", index=True)
    df_tambo.to_excel(writer, sheet_name="Tambo", index=True)

    exportar_indices("indices_cria", "Índices Cría")
    exportar_indices("indices_invernada", "Índices Invernada")
    exportar_indices("indices_feedlot", "Índices Feedlot")
    exportar_indices("indices_tambo", "Índices Tambo")

    
output.seek(0)

with st.sidebar:
    if st.button("💾 Guardar progreso para continuar luego"):
        try:
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

    descargado = st.download_button(
        label="📥 Descargar archivo para compartir a QTM",
        data=output,
        file_name=f"formulario_{codigo_usuario}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if descargado:
        st.session_state["descarga_confirmada"] = True
        st.rerun()  # <<--- ESTA LÍNEA ES LA CLAVE

    # Opción para borrar el progreso actual
    if os.path.exists(PROGRESO_FILE):
        if st.button(f"❌ Borrar progreso guardado para {codigo_usuario}"):
            try:
                os.remove(PROGRESO_FILE)
                st.success("✅ Progreso eliminado. Refrescá la página para comenzar desde cero.")
                st.stop()
            except Exception as e:
                st.error(f"❌ Error al intentar borrar el progreso: {e}")
