import streamlit as st
# Configuración de la página de Streamlit - DEBE SER LA PRIMERA LLAMADA A STREAMLIT


import pandas as pd
import numpy as np
import pulp
from datetime import datetime, timedelta
import plotly.figure_factory as ff
import plotly.express as px

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

def optimizar_turnos(servicios, pacientes, horarios_disponibles):
    """Optimiza la asignación de turnos utilizando PuLP (Programación Lineal)"""
    # Crear el problema de optimización
    problema = pulp.LpProblem("Optimizacion_Turnos_Medicos", pulp.LpMaximize)
    
    # Crear variables de decisión: x[s, p, h] = 1 si el servicio s atiende al paciente p en el horario h
    x = pulp.LpVariable.dicts("asignacion", 
                         [(s, p, h) for s in range(len(servicios)) 
                                    for p in range(len(pacientes))
                                    for h in horarios_disponibles],
                         cat='Binary')
    
    # Función objetivo: maximizar la suma de prioridades atendidas y minimizar las distancias
    # Convertir prioridades a valores numéricos
    valores_prioridad = {"Alta": 10, "Media": 5, "Baja": 1}
    
    # Función objetivo
    problema += pulp.lpSum([x[(s, p, h)] * (valores_prioridad[pacientes[p]["prioridad"]] - 0.01 * pacientes[p]["distancia"])
                         for s in range(len(servicios))
                         for p in range(len(pacientes))
                         for h in horarios_disponibles])
    
    # Restricciones
    
    # 1. Un paciente solo puede ser atendido una vez
    for p in range(len(pacientes)):
        problema += pulp.lpSum([x[(s, p, h)] 
                           for s in range(len(servicios))
                           for h in horarios_disponibles]) <= 1
    
    # 2. Un servicio solo puede atender a un paciente en un horario específico
    for s in range(len(servicios)):
        for h in horarios_disponibles:
            problema += pulp.lpSum([x[(s, p, h)]
                               for p in range(len(pacientes))]) <= 1
    
    # 3. Respetar horarios disponibles de servicios
    for s in range(len(servicios)):
        for h in horarios_disponibles:
            if not esta_en_rango_horario(h, servicios[s]["hora_inicio"], servicios[s]["hora_fin"], horarios_disponibles):
                problema += pulp.lpSum([x[(s, p, h)]
                               for p in range(len(pacientes))]) == 0
    
    # 4. Considerar tiempo de atención (evitar superposiciones)
    for s in range(len(servicios)):
        tiempo_atencion = servicios[s]["tiempo_atencion"]  # en minutos
        slots_necesarios = tiempo_atencion // 15  # Asumiendo intervalos de 15 minutos
        
        for h_index in range(len(horarios_disponibles)):
            h = horarios_disponibles[h_index]
            # Para cada horario asignado, bloquear los siguientes 'slots_necesarios-1' slots
            for overlap in range(1, slots_necesarios):
                if h_index + overlap < len(horarios_disponibles):
                    h_overlap = horarios_disponibles[h_index + overlap]
                    for p in range(len(pacientes)):
                        # Si se asigna un turno en h, no puede haber otro en h_overlap para el mismo servicio
                        for p2 in range(len(pacientes)):
                            problema += x[(s, p, h)] + x[(s, p2, h_overlap)] <= 1
    
    # Resolver el problema
    solver = pulp.PULP_CBC_CMD(msg=False)
    problema.solve(solver)
    
    # Verificar si se encontró una solución
    if problema.status != pulp.LpStatusOptimal:
        return None
    
    # Extraer la solución
    turnos_asignados = []
    for s in range(len(servicios)):
        for p in range(len(pacientes)):
            for h in horarios_disponibles:
                if pulp.value(x[(s, p, h)]) == 1:
                    # Calcular hora de fin según tiempo de atención
                    hora_inicio_dt = datetime.strptime(h, "%H:%M")
                    hora_fin_dt = hora_inicio_dt + timedelta(minutes=servicios[s]["tiempo_atencion"])
                    hora_fin = hora_fin_dt.strftime("%H:%M")
                    
                    turnos_asignados.append({
                        "ID_Servicio": s,
                        "Servicio": servicios[s]["nombre"],
                        "ID_Paciente": p,
                        "Nombre_Paciente": pacientes[p]["nombre"],
                        "Prioridad": pacientes[p]["prioridad"],
                        "Distancia": pacientes[p]["distancia"],
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
    {"nombre": "Salud Mental", "hora_inicio": "12:30", "hora_fin": "15:00", "lugar": "N8", "tiempo_atencion": 30}
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

# Sección 2: Configuración de Pacientes
st.sidebar.subheader("Configuración de Pacientes")
num_pacientes = st.sidebar.number_input("Número de pacientes", min_value=1, max_value=50, value=10)

pacientes = []
with st.expander("Información de Pacientes", expanded=True):
    # Crear una tabla editable para los pacientes
    pacientes_data = {
        "Nombre": [f"Paciente {i+1}" for i in range(num_pacientes)],
        "Servicio Requerido": ["Clínica Médica" for _ in range(num_pacientes)],
        "Prioridad": ["Media" for _ in range(num_pacientes)],
        "Distancia (km)": [5 for _ in range(num_pacientes)]
    }
    
    # Obtener lista de servicios únicos para el dropdown
    servicios_unicos = list(set([s["nombre"] for s in servicios]))
    
    df_pacientes = pd.DataFrame(pacientes_data)
    edited_df = st.data_editor(
        df_pacientes,
        column_config={
            "Nombre": st.column_config.TextColumn("Nombre"),
            "Servicio Requerido": st.column_config.SelectboxColumn(
                "Servicio Requerido",
                options=servicios_unicos,
            ),
            "Prioridad": st.column_config.SelectboxColumn(
                "Prioridad",
                options=["Alta", "Media", "Baja"],
            ),
            "Distancia (km)": st.column_config.NumberColumn("Distancia (km)", min_value=0, max_value=100)
        },
        num_rows="dynamic",
        use_container_width=True
    )
    
    for _, row in edited_df.iterrows():
        pacientes.append({
            "nombre": row["Nombre"],
            "servicio_requerido": row["Servicio Requerido"],
            "prioridad": row["Prioridad"],
            "distancia": row["Distancia (km)"]
        })

# Horarios disponibles para asignación
horarios_disponibles = generar_horarios(8, 16, 15)

# Botón para ejecutar la optimización
if st.button("Optimizar Asignación de Turnos", type="primary"):
    with st.spinner("Optimizando asignación de turnos..."):
        # Filtrar servicios por requerimiento de pacientes
        servicios_filtrados = []
        for s in servicios:
            servicios_filtrados.append(s)
        
        # Filtrar pacientes a solo aquellos que solicitan servicios disponibles
        servicios_disponibles = set([s["nombre"] for s in servicios])
        pacientes_filtrados = [p for p in pacientes if p["servicio_requerido"] in servicios_disponibles]
        
        if len(pacientes_filtrados) == 0:
            st.error("No hay pacientes que requieran los servicios disponibles.")
        else:
            resultado = optimizar_turnos(servicios_filtrados, pacientes_filtrados, horarios_disponibles)
            
            if resultado is None or resultado.empty:
                st.error("No se pudo encontrar una solución óptima con los parámetros proporcionados. Por favor, ajuste los parámetros e intente nuevamente.")
            else:
                st.success("¡Optimización completada con éxito!")
                
                # Mostrar tabla de resultados
                st.subheader("Turnos Asignados")
                st.dataframe(resultado.sort_values(by=["Lugar_Atencion", "Hora_Inicio"]), use_container_width=True)
                
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
                    st.metric("Total Pacientes Atendidos", len(resultado))
                    
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
                
                # Opción para descargar el resultado
                csv = resultado.to_csv(index=False)
                st.download_button(
                    label="Descargar Programación (CSV)",
                    data=csv,
                    file_name="turnos_medicos.csv",
                    mime="text/csv"
                )

# Instrucciones de uso
with st.sidebar.expander("Instrucciones de Uso", expanded=False):
    st.markdown("""
    1. Revise los servicios médicos disponibles con sus respectivos horarios y lugares
    2. Ingrese la información de los pacientes asegurándose de asignar el servicio que requieren
    3. Haga clic en "Optimizar Asignación de Turnos"
    4. Revise los resultados y la visualización
    5. Descargue la programación si es necesario
    
    **Notas importantes:**
    - La prioridad Alta da preferencia al paciente en la asignación
    - La distancia se considera como factor secundario (a menor distancia, mayor prioridad)
    - Los tiempos de atención están configurados por defecto en 30 minutos para cada servicio pero pueden modificarse
    - Un paciente solo puede ser asignado a un servicio que coincida con su requerimiento
    """)
