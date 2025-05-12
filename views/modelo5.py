import streamlit as st
import pandas as pd
import numpy as np
import pulp
from datetime import datetime, timedelta
import plotly.figure_factory as ff
import plotly.express as px

st.title("Sistema de Optimización de Turnos Médicos")

# Definición de funciones de utilidad
def generar_horarios(hora_inicio=8, hora_fin=16, intervalo_minutos=15):
    """Genera una lista de horarios posibles en el formato HH:MM"""
    horarios = []
    hora_actual = datetime.strptime(f"{hora_inicio}:00", "%H:%M")
    hora_final = datetime.strptime(f"{hora_fin}:00", "%H:%M")
    
    while hora_actual <= hora_final:
        horarios.append(hora_actual.strftime("%H:%M"))
        hora_actual += timedelta(minutes=intervalo_minutos)
    
    return horarios

def convertir_hora_a_index(hora_str, todos_horarios):
    """Convierte una hora en formato HH:MM a su índice en la lista de horarios"""
    try:
        return todos_horarios.index(hora_str)
    except ValueError:
        return -1

def esta_en_rango_horario(hora, inicio, fin, todos_horarios):
    """Verifica si una hora está dentro del rango de inicio y fin"""
    idx_hora = convertir_hora_a_index(hora, todos_horarios)
    idx_inicio = convertir_hora_a_index(inicio, todos_horarios)
    idx_fin = convertir_hora_a_index(fin, todos_horarios)
    
    if idx_hora == -1 or idx_inicio == -1 or idx_fin == -1:
        return False
    
    return idx_inicio <= idx_hora < idx_fin

def optimizar_turnos(servicios, pacientes_con_servicios, horarios_disponibles):
    """Optimiza la asignación de turnos utilizando PuLP (Programación Lineal)"""
    # Crear el problema de optimización
    problema = pulp.LpProblem("Optimizacion_Turnos_Medicos", pulp.LpMaximize)
    
    # Extraer servicios y pacientes para la optimización
    indices_pacientes = [p["id"] for p in pacientes_con_servicios]
    todos_pacientes_servicios = []
    
    # Crear lista expandida de pacientes con sus servicios requeridos
    for p in pacientes_con_servicios:
        for serv_req in p["servicios_requeridos"]:
            todos_pacientes_servicios.append({
                "id_paciente": p["id"],
                "nombre_paciente": p["nombre"],
                "prioridad": p["prioridad"],
                "distancia": p["distancia"],
                "servicio_requerido": serv_req
            })
    
    # Crear variables de decisión: x[s, p, h] = 1 si el servicio s atiende al paciente p en el horario h
    x = pulp.LpVariable.dicts("asignacion", 
                         [(s, p["id"], serv_req, h) for s in range(len(servicios)) 
                                                   for p in pacientes_con_servicios
                                                   for serv_req in p["servicios_requeridos"]
                                                   for h in horarios_disponibles
                                                   if servicios[s]["nombre"] == serv_req],
                         cat='Binary')
    
    # Función objetivo: maximizar la suma de prioridades atendidas y minimizar las distancias
    valores_prioridad = {"Alta": 10, "Media": 5, "Baja": 1}
    
    # Función objetivo - maximizar atención por prioridad, minimizar distancia
    problema += pulp.lpSum([x[(s, p["id"], servicios[s]["nombre"], h)] * 
                         (valores_prioridad[p["prioridad"]] - 0.01 * p["distancia"])
                         for s in range(len(servicios))
                         for p in pacientes_con_servicios
                         for h in horarios_disponibles
                         if servicios[s]["nombre"] in p["servicios_requeridos"]])
    
    # Restricciones
    
    # 1. Un paciente solo puede ser atendido una vez por cada servicio requerido
    for p in pacientes_con_servicios:
        for serv_req in p["servicios_requeridos"]:
            problema += pulp.lpSum([x[(s, p["id"], serv_req, h)] 
                               for s in range(len(servicios))
                               for h in horarios_disponibles
                               if servicios[s]["nombre"] == serv_req]) <= 1
    
    # 2. Un servicio solo puede atender a un paciente en un horario específico
    for s in range(len(servicios)):
        for h in horarios_disponibles:
            problema += pulp.lpSum([x[(s, p["id"], servicios[s]["nombre"], h)]
                               for p in pacientes_con_servicios
                               if servicios[s]["nombre"] in p["servicios_requeridos"]]) <= 1
    
    # 3. Respetar horarios disponibles de servicios
    for s in range(len(servicios)):
        nombre_servicio = servicios[s]["nombre"]
        for h in horarios_disponibles:
            if not esta_en_rango_horario(h, servicios[s]["hora_inicio"], servicios[s]["hora_fin"], horarios_disponibles):
                problema += pulp.lpSum([x[(s, p["id"], nombre_servicio, h)]
                               for p in pacientes_con_servicios
                               if nombre_servicio in p["servicios_requeridos"]]) == 0
    
    # 4. Considerar tiempo de atención (evitar superposiciones)
    for s in range(len(servicios)):
        tiempo_atencion = servicios[s]["tiempo_atencion"]  # en minutos
        slots_necesarios = tiempo_atencion // 15  # Asumiendo intervalos de 15 minutos
        nombre_servicio = servicios[s]["nombre"]
        
        for h_index in range(len(horarios_disponibles)):
            h = horarios_disponibles[h_index]
            # Para cada horario asignado, bloquear los siguientes 'slots_necesarios-1' slots
            for overlap in range(1, slots_necesarios):
                if h_index + overlap < len(horarios_disponibles):
                    h_overlap = horarios_disponibles[h_index + overlap]
                    for p1 in pacientes_con_servicios:
                        if nombre_servicio in p1["servicios_requeridos"]:
                            for p2 in pacientes_con_servicios:
                                if nombre_servicio in p2["servicios_requeridos"]:
                                    # Si se asigna un turno en h, no puede haber otro en h_overlap para el mismo servicio
                                    problema += x[(s, p1["id"], nombre_servicio, h)] + x[(s, p2["id"], nombre_servicio, h_overlap)] <= 1
    
    # 5. Evitar superposiciones de turnos para un mismo paciente (no puede estar en dos lugares al mismo tiempo)
    for p in pacientes_con_servicios:
        for h_index in range(len(horarios_disponibles)):
            h = horarios_disponibles[h_index]
            for s1 in range(len(servicios)):
                if servicios[s1]["nombre"] in p["servicios_requeridos"]:
                    tiempo_atencion1 = servicios[s1]["tiempo_atencion"]
                    slots_necesarios1 = tiempo_atencion1 // 15
                    
                    # Comprobar todos los slots que se solaparían
                    for offset in range(slots_necesarios1):
                        if h_index + offset < len(horarios_disponibles):
                            h_check = horarios_disponibles[h_index + offset]
                            
                            # Para todos los demás servicios
                            for s2 in range(len(servicios)):
                                if s1 != s2 and servicios[s2]["nombre"] in p["servicios_requeridos"]:
                                    if h_index + offset < len(horarios_disponibles):
                                        problema += x[(s1, p["id"], servicios[s1]["nombre"], h)] + x[(s2, p["id"], servicios[s2]["nombre"], h_check)] <= 1
    
    # Resolver el problema
    solver = pulp.PULP_CBC_CMD(msg=False)
    problema.solve(solver)
    
    # Verificar si se encontró una solución
    if problema.status != pulp.LpStatusOptimal:
        return None
    
    # Extraer la solución
    turnos_asignados = []
    for s in range(len(servicios)):
        nombre_servicio = servicios[s]["nombre"]
        for p in pacientes_con_servicios:
            if nombre_servicio in p["servicios_requeridos"]:
                for h in horarios_disponibles:
                    if (s, p["id"], nombre_servicio, h) in x and pulp.value(x[(s, p["id"], nombre_servicio, h)]) == 1:
                        # Calcular hora de fin según tiempo de atención
                        hora_inicio_dt = datetime.strptime(h, "%H:%M")
                        hora_fin_dt = hora_inicio_dt + timedelta(minutes=servicios[s]["tiempo_atencion"])
                        hora_fin = hora_fin_dt.strftime("%H:%M")
                        
                        turnos_asignados.append({
                            "ID_Servicio": s,
                            "Servicio": servicios[s]["nombre"],
                            "ID_Paciente": p["id"],
                            "Nombre_Paciente": p["nombre"],
                            "Prioridad": p["prioridad"],
                            "Distancia": p["distancia"],
                            "Lugar_Atencion": servicios[s]["lugar"],
                            "Hora_Inicio": h,
                            "Hora_Fin": hora_fin
                        })
    
    return pd.DataFrame(turnos_asignados)

# Interfaz de usuario con Streamlit
st.sidebar.header("Configuración")

# Sección 1: Configuración de Servicios Médicos
st.sidebar.subheader("Servicios Médicos Disponibles")

# Datos predefinidos de servicios
servicios_predefinidos = [
    {"nombre": "Clínica Médica", "hora_inicio": "12:00", "hora_fin": "14:30", "lugar": "N7", "tiempo_atencion": 30},
    {"nombre": "Neurología", "hora_inicio": "09:00", "hora_fin": "10:00", "lugar": "N7", "tiempo_atencion": 30},
    {"nombre": "Neurología", "hora_inicio": "13:30", "hora_fin": "13:50", "lugar": "N7", "tiempo_atencion": 20},
    {"nombre": "Reumatología", "hora_inicio": "09:00", "hora_fin": "11:00", "lugar": "N7", "tiempo_atencion": 30},
    {"nombre": "Traumatología", "hora_inicio": "08:00", "hora_fin": "10:30", "lugar": "N7", "tiempo_atencion": 30},
    {"nombre": "Cardiología", "hora_inicio": "10:00", "hora_fin": "12:00", "lugar": "N1", "tiempo_atencion": 30},
    {"nombre": "Cuidados Paliativos", "hora_inicio": "12:30", "hora_fin": "15:00", "lugar": "N3", "tiempo_atencion": 30},
    {"nombre": "Oftalmología", "hora_inicio": "11:00", "hora_fin": "13:30", "lugar": "N5", "tiempo_atencion": 30},
    {"nombre": "Rehabilitación", "hora_inicio": "08:00", "hora_fin": "10:30", "lugar": "N6", "tiempo_atencion": 30},
    {"nombre": "Salud Mental", "hora_inicio": "12:30", "hora_fin": "15:00", "lugar": "N8", "tiempo_atencion": 30},
    {"nombre": "Neumologia", "hora_inicio": "10:00", "hora_fin":"11:00","lugar": "Hdia", "tiempo_atencion":30},
    {"nombre": "IGeHM-TS", "hora_inicio": "8:00", "hora_fin": "15:00","lugar": "N7", "tiempo_atencion":30},
    {"nombre": "Gastroenterologia", "hora_inicio":"8:00", "hora_fin":"9:30","lugar":"Hdia2","tiempo_atencion":30},
    {"nombre": "IGeHM-SM", "hora_inicio":"12:00","hora_fin":"17:00","lugar":"N8","tiempo_atencion":30},
    {"nombre": "IGeHM-MA", "hora_inicio":"7:00","hora_fin":"13:00","lugar":"N8","tiempo_atencion":30}
]

use_predefined = st.sidebar.checkbox("Usar servicios predefinidos", value=True)

if use_predefined:
    servicios = servicios_predefinidos
    
    # Mostrar tabla de servicios para referencia
    with st.expander("Servicios Médicos Disponibles", expanded=True):
        df_servicios = pd.DataFrame([{
            "Servicio": s["nombre"],
            "Horario": f"{s['hora_inicio']} - {s['hora_fin']}",
            "Lugar": s["lugar"],
            "Tiempo (min)": s["tiempo_atencion"]
        } for s in servicios])
        
        st.dataframe(df_servicios, use_container_width=True)
else:
    # Opción para personalizar servicios
    num_servicios = st.sidebar.number_input("Número de servicios", min_value=1, max_value=15, value=len(servicios_predefinidos))
    servicios = []
    
    with st.expander("Configuración de Servicios", expanded=True):
        for i in range(num_servicios):
            col1, col2, col3 = st.columns(3)
            with col1:
                nombre = st.text_input(f"Nombre del servicio {i+1}", value=servicios_predefinidos[i]["nombre"] if i < len(servicios_predefinidos) else f"Servicio {i+1}", key=f"serv_nombre_{i}")
                lugar = st.text_input(f"Lugar de atención {i+1}", value=servicios_predefinidos[i]["lugar"] if i < len(servicios_predefinidos) else f"N{i+1}", key=f"serv_lugar_{i}")
            
            with col2:
                hora_inicio = st.text_input(f"Hora inicio {i+1}", value=servicios_predefinidos[i]["hora_inicio"] if i < len(servicios_predefinidos) else "08:00", key=f"serv_inicio_{i}")
                hora_fin = st.text_input(f"Hora fin {i+1}", value=servicios_predefinidos[i]["hora_fin"] if i < len(servicios_predefinidos) else "12:00", key=f"serv_fin_{i}")
            
            with col3:
                tiempo_atencion = st.number_input(f"Tiempo de atención (min) {i+1}", min_value=15, max_value=120, value=servicios_predefinidos[i]["tiempo_atencion"] if i < len(servicios_predefinidos) else 30, step=5, key=f"serv_tiempo_{i}")
            
            servicios.append({
                "nombre": nombre,
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin,
                "lugar": lugar,
                "tiempo_atencion": tiempo_atencion
            })
            
            st.divider()

# Obtener lista de servicios únicos para la interfaz de selección múltiple
servicios_unicos = sorted(list(set([s["nombre"] for s in servicios])))

# Sección 2: Configuración de Pacientes
st.sidebar.subheader("Configuración de Pacientes")
num_pacientes = st.sidebar.number_input("Número de pacientes", min_value=1, max_value=50, value=10)

pacientes = []
with st.expander("Información de Pacientes", expanded=True):
    # Crear formulario para cada paciente
    for i in range(num_pacientes):
        st.subheader(f"Paciente {i+1}")
        
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input(f"Nombre", value=f"Paciente {i+1}", key=f"pac_nombre_{i}")
            prioridad = st.selectbox(f"Prioridad", options=["Alta", "Media", "Baja"], index=1, key=f"pac_prioridad_{i}")
        
        with col2:
            distancia = st.number_input(f"Distancia (km)", min_value=0, max_value=100, value=5, key=f"pac_distancia_{i}")
            # Selección múltiple de servicios
            servicios_seleccionados = st.multiselect(
                f"Servicios Requeridos",
                options=servicios_unicos,
                default=[servicios_unicos[0]],
                key=f"pac_servicios_{i}"
            )
        
        pacientes.append({
            "id": i,
            "nombre": nombre,
            "servicios_requeridos": servicios_seleccionados,
            "prioridad": prioridad,
            "distancia": distancia
        })
        
        st.divider()

# Horarios disponibles para asignación
horarios_disponibles = generar_horarios(8, 16, 15)

# Botón para ejecutar la optimización
if st.button("Optimizar Asignación de Turnos", type="primary"):
    with st.spinner("Optimizando asignación de turnos..."):
        # Verificar que todos los pacientes tengan al menos un servicio seleccionado
        pacientes_sin_servicio = [p["nombre"] for p in pacientes if not p["servicios_requeridos"]]
        
        if pacientes_sin_servicio:
            st.error(f"Los siguientes pacientes no tienen servicios seleccionados: {', '.join(pacientes_sin_servicio)}")
        else:
            # Filtrar servicios por requerimiento de pacientes
            servicios_filtrados = []
            for s in servicios:
                servicios_filtrados.append(s)
            
            # Filtrar pacientes a solo aquellos que solicitan servicios disponibles
            servicios_disponibles = set([s["nombre"] for s in servicios])
            pacientes_filtrados = []
            
            for p in pacientes:
                # Comprobar cuáles de los servicios requeridos están disponibles
                servicios_req_disponibles = [s for s in p["servicios_requeridos"] if s in servicios_disponibles]
                
                if servicios_req_disponibles:
                    p_filtrado = p.copy()
                    p_filtrado["servicios_requeridos"] = servicios_req_disponibles
                    pacientes_filtrados.append(p_filtrado)
            
            if len(pacientes_filtrados) == 0:
                st.error("No hay pacientes que requieran los servicios disponibles.")
            else:
                resultado = optimizar_turnos(servicios_filtrados, pacientes_filtrados, horarios_disponibles)
                
                if resultado is None or resultado.empty:
                    st.error("No se pudo encontrar una solución óptima con los parámetros proporcionados. Por favor, ajuste los parámetros e intente nuevamente.")
                else:
                    st.success("¡Optimización completada con éxito!")
                    
                    # Identificar pacientes que no recibieron todos sus servicios requeridos
                    asignaciones_por_paciente = {}
                    
                    for _, row in resultado.iterrows():
                        pac_id = row["ID_Paciente"]
                        if pac_id not in asignaciones_por_paciente:
                            asignaciones_por_paciente[pac_id] = []
                        asignaciones_por_paciente[pac_id].append(row["Servicio"])
                    
                    # Crear columna para indicar servicios incompletos
                    resultado["Servicios_Completos"] = "Sí"
                    
                    for p in pacientes_filtrados:
                        if p["id"] in asignaciones_por_paciente:
                            servicios_asignados = set(asignaciones_por_paciente[p["id"]])
                            servicios_requeridos = set(p["servicios_requeridos"])
                            
                            if servicios_asignados != servicios_requeridos:
                                # Marcar filas correspondientes a este paciente
                                resultado.loc[resultado["ID_Paciente"] == p["id"], "Servicios_Completos"] = "No"
                    
                    # Mostrar tabla de resultados
                    st.subheader("Turnos Asignados")
                    st.dataframe(resultado.sort_values(by=["Nombre_Paciente", "Hora_Inicio"]), use_container_width=True)
                    
                    # Mostrar servicios faltantes por paciente
                    st.subheader("Análisis de Servicios Requeridos")
                    
                    analisis_servicios = []
                    for p in pacientes_filtrados:
                        servicios_requeridos = set(p["servicios_requeridos"])
                        servicios_asignados = set(asignaciones_por_paciente.get(p["id"], []))
                        servicios_faltantes = servicios_requeridos - servicios_asignados
                        
                        analisis_servicios.append({
                            "Paciente": p["nombre"],
                            "Servicios Requeridos": ", ".join(servicios_requeridos),
                            "Servicios Asignados": ", ".join(servicios_asignados),
                            "Servicios Faltantes": ", ".join(servicios_faltantes) if servicios_faltantes else "Ninguno",
                            "Estado": "Completo" if not servicios_faltantes else "Incompleto"
                        })
                    
                    df_analisis = pd.DataFrame(analisis_servicios)
                    st.dataframe(df_analisis, use_container_width=True)
                    
                    # Visualización de la programación
                    st.subheader("Visualización de Turnos")
                    
                    # Preparar datos para el diagrama de Gantt
                    df_gantt = resultado.copy()
                    df_gantt["Resource"] = df_gantt["Lugar_Atencion"] + " - " + df_gantt["Servicio"]
                    df_gantt["Task"] = df_gantt["Nombre_Paciente"] + " (P: " + df_gantt["Prioridad"] + ")"
                    
                    # Convertir hora inicio y fin a datetime para el gráfico
                    fecha_base = datetime.today().date()
                    df_gantt["Start"] = pd.to_datetime(fecha_base.strftime("%Y-%m-%d") + " " + df_gantt["Hora_Inicio"])
                    df_gantt["Finish"] = pd.to_datetime(fecha_base.strftime("%Y-%m-%d") + " " + df_gantt["Hora_Fin"])
                    
                    # Colores según prioridad
                    colores = {"Alta": "rgb(242, 72, 34)", "Media": "rgb(242, 183, 5)", "Baja": "rgb(45, 135, 187)"}
                    
                    # Crear un diccionario de colores que mapee cada tarea a su color correspondiente
                    colors_dict = {}
                    for _, row in df_gantt.iterrows():
                        colors_dict[row["Task"]] = colores[row["Prioridad"]]
                    
                    try:
                        # Crear el diagrama de Gantt
                        fig = ff.create_gantt(
                            df_gantt,
                            colors=colors_dict,
                            index_col="Resource",
                            group_tasks=True,
                            showgrid_x=True,
                            title="Programación de Turnos Médicos"
                        )
                        
                        # Actualizar el diseño para mostrar horas en el eje x
                        fig.update_xaxes(
                            tickformat="%H:%M",
                            tickvals=pd.date_range(
                                start=pd.to_datetime(fecha_base.strftime("%Y-%m-%d") + " 08:00"),
                                end=pd.to_datetime(fecha_base.strftime("%Y-%m-%d") + " 16:00"),
                                freq="1H"
                            )
                        )
                        
                        # Mostrar el diagrama
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error al crear el diagrama de Gantt: {str(e)}")
                        st.info("Mostrando visualización alternativa...")
                        
                        # Visualización alternativa sin usar ff.create_gantt
                        fig = px.timeline(
                            df_gantt, 
                            x_start="Start", 
                            x_end="Finish", 
                            y="Resource",
                            color="Prioridad",
                            hover_name="Nombre_Paciente",
                            color_discrete_map=colores,
                            title="Programación de Turnos Médicos"
                        )
                        
                        fig.update_yaxes(autorange="reversed")
                        fig.update_xaxes(
                            tickformat="%H:%M",
                            tickvals=pd.date_range(
                                start=pd.to_datetime(fecha_base.strftime("%Y-%m-%d") + " 08:00"),
                                end=pd.to_datetime(fecha_base.strftime("%Y-%m-%d") + " 16:00"),
                                freq="1H"
                            )
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Estadísticas adicionales
                    st.subheader("Estadísticas")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Pacientes Atendidos", resultado["Nombre_Paciente"].nunique())
                        
                        # Distribución por prioridad
                        prioridad_counts = resultado["Prioridad"].value_counts().reset_index()
                        prioridad_counts.columns = ["Prioridad", "Cantidad"]
                        
                        fig_prioridad = px.pie(
                            prioridad_counts, 
                            values="Cantidad", 
                            names="Prioridad",
                            title="Distribución por Prioridad",
                            color="Prioridad",
                            color_discrete_map={"Alta": "#f24822", "Media": "#f2b705", "Baja": "#2d87bb"}
                        )
                        st.plotly_chart(fig_prioridad, use_container_width=True)
                        
                    with col2:
                        # Pacientes por servicio
                        servicio_counts = resultado["Servicio"].value_counts().reset_index()
                        servicio_counts.columns = ["Servicio", "Cantidad"]
                        
                        fig_servicio = px.bar(
                            servicio_counts,
                            x="Servicio",
                            y="Cantidad",
                            title="Pacientes por Servicio",
                            text_auto=True
                        )
                        st.plotly_chart(fig_servicio, use_container_width=True)
                        
                    with col3:
                        # Uso de lugares de atención
                        lugar_count = resultado["Lugar_Atencion"].value_counts().reset_index()
                        lugar_count.columns = ["Lugar de Atención", "Cantidad"]
                        
                        fig_lugares = px.bar(
                            lugar_count,
                            x="Lugar de Atención",
                            y="Cantidad",
                            title="Uso de Lugares de Atención",
                            text_auto=True
                        )
                        st.plotly_chart(fig_lugares, use_container_width=True)
                    
                    # Estadísticas de servicios completos vs incompletos
                    st.subheader("Análisis de Completitud de Servicios")
                    total_pacientes = len(pacientes_filtrados)
                    pacientes_completos = sum(1 for p in analisis_servicios if p["Estado"] == "Completo")
                    pacientes_incompletos = total_pacientes - pacientes_completos
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        completitud_data = pd.DataFrame({
                            "Estado": ["Completo", "Incompleto"],
                            "Cantidad": [pacientes_completos, pacientes_incompletos]
                        })
                        
                        fig_completitud = px.pie(
                            completitud_data,
                            values="Cantidad",
                            names="Estado",
                            title="Pacientes con Todos los Servicios vs. Servicios Incompletos",
                            color="Estado",
                            color_discrete_map={"Completo": "#4CAF50", "Incompleto": "#FF9800"}
                        )
                        st.plotly_chart(fig_completitud, use_container_width=True)
                    
                    with col2:
                        # Calcular estadísticas de servicios asignados vs faltantes
                        total_servicios_requeridos = sum(len(p["servicios_requeridos"]) for p in pacientes_filtrados)
                        total_servicios_asignados = sum(len(asignaciones_por_paciente.get(p["id"], [])) for p in pacientes_filtrados)
                        tasa_asignacion = total_servicios_asignados / total_servicios_requeridos * 100
                        
                        st.metric("Tasa de Asignación de Servicios", f"{tasa_asignacion:.1f}%")
                        st.metric("Total Servicios Requeridos", total_servicios_requeridos)
                        st.metric("Total Servicios Asignados", total_servicios_asignados)
                        st.metric("Servicios No Asignados", total_servicios_requeridos - total_servicios_asignados)
                    
                    # Opción para descargar el resultado
                    csv = resultado.to_csv(index=False)
                    st.download_button(
                        label="Descargar Programación (CSV)",
                        data=csv,
                        file_name="turnos_medicos.csv",
                        mime="text/csv"
                    )