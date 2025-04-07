import streamlit as st
# Configuración de la página de Streamlit - DEBE SER LA PRIMERA LLAMADA A STREAMLIT


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

def optimizar_turnos(especialistas, pacientes, consultorios, horarios_disponibles):
    """Optimiza la asignación de turnos utilizando PuLP (Programación Lineal)"""
    # Crear el problema de optimización
    problema = pulp.LpProblem("Optimizacion_Turnos_Medicos", pulp.LpMaximize)
    
    # Crear variables de decisión: x[e, p, c, h] = 1 si el especialista e atiende al paciente p en el consultorio c en el horario h
    x = pulp.LpVariable.dicts("asignacion", 
                         [(e, p, c, h) for e in range(len(especialistas)) 
                                       for p in range(len(pacientes))
                                       for c in range(consultorios)
                                       for h in horarios_disponibles],
                         cat='Binary')
    
    # Función objetivo: maximizar la suma de prioridades atendidas y minimizar las distancias
    # Convertir prioridades a valores numéricos
    valores_prioridad = {"Alta": 10, "Media": 5, "Baja": 1}
    
    # Función objetivo
    problema += pulp.lpSum([x[(e, p, c, h)] * (valores_prioridad[pacientes[p]["prioridad"]] - 0.01 * pacientes[p]["distancia"])
                         for e in range(len(especialistas))
                         for p in range(len(pacientes))
                         for c in range(consultorios)
                         for h in horarios_disponibles])
    
    # Restricciones
    
    # 1. Un paciente solo puede ser atendido una vez
    for p in range(len(pacientes)):
        problema += pulp.lpSum([x[(e, p, c, h)] 
                           for e in range(len(especialistas))
                           for c in range(consultorios)
                           for h in horarios_disponibles]) <= 1
    
    # 2. Un especialista solo puede atender a un paciente en un horario específico
    for e in range(len(especialistas)):
        for h in horarios_disponibles:
            problema += pulp.lpSum([x[(e, p, c, h)]
                               for p in range(len(pacientes))
                               for c in range(consultorios)]) <= 1
    
    # 3. Un consultorio solo puede tener una atención en un horario específico
    for c in range(consultorios):
        for h in horarios_disponibles:
            problema += pulp.lpSum([x[(e, p, c, h)]
                               for e in range(len(especialistas))
                               for p in range(len(pacientes))]) <= 1
    
    # 4. Respetar horarios disponibles de especialistas
    for e in range(len(especialistas)):
        horarios_no_disponibles = [h for h in horarios_disponibles if h not in especialistas[e]["horarios_disponibles"]]
        for h in horarios_no_disponibles:
            problema += pulp.lpSum([x[(e, p, c, h)]
                               for p in range(len(pacientes))
                               for c in range(consultorios)]) == 0
    
    # 5. Considerar tiempo de atención (evitar superposiciones)
    for e in range(len(especialistas)):
        tiempo_atencion = especialistas[e]["tiempo_atencion"]  # en minutos
        slots_necesarios = tiempo_atencion // 15  # Asumiendo intervalos de 15 minutos
        
        for h_index in range(len(horarios_disponibles)):
            h = horarios_disponibles[h_index]
            # Para cada horario asignado, bloquear los siguientes 'slots_necesarios-1' slots
            for overlap in range(1, slots_necesarios):
                if h_index + overlap < len(horarios_disponibles):
                    h_overlap = horarios_disponibles[h_index + overlap]
                    for p in range(len(pacientes)):
                        for c in range(consultorios):
                            # Si se asigna un turno en h, no puede haber otro en h_overlap para el mismo especialista
                            for p2 in range(len(pacientes)):
                                problema += x[(e, p, c, h)] + x[(e, p2, c, h_overlap)] <= 1
    
    # Resolver el problema
    solver = pulp.PULP_CBC_CMD(msg=False)
    problema.solve(solver)
    
    # Verificar si se encontró una solución
    if problema.status != pulp.LpStatusOptimal:
        return None
    
    # Extraer la solución
    turnos_asignados = []
    for e in range(len(especialistas)):
        for p in range(len(pacientes)):
            for c in range(consultorios):
                for h in horarios_disponibles:
                    if pulp.value(x[(e, p, c, h)]) == 1:
                        # Calcular hora de fin según tiempo de atención
                        hora_inicio_dt = datetime.strptime(h, "%H:%M")
                        hora_fin_dt = hora_inicio_dt + timedelta(minutes=especialistas[e]["tiempo_atencion"])
                        hora_fin = hora_fin_dt.strftime("%H:%M")
                        
                        turnos_asignados.append({
                            "ID_Especialista": e,
                            "Especialidad": especialistas[e]["especialidad"],
                            "ID_Paciente": p,
                            "Nombre_Paciente": pacientes[p]["nombre"],
                            "Prioridad": pacientes[p]["prioridad"],
                            "Distancia": pacientes[p]["distancia"],
                            "Consultorio": c+1,  # Para mostrar consultorios como 1, 2, etc.
                            "Hora_Inicio": h,
                            "Hora_Fin": hora_fin
                        })
    
    return pd.DataFrame(turnos_asignados)

# Interfaz de usuario con Streamlit
st.sidebar.header("Configuración")

# Sección 1: Configuración de Especialistas
st.sidebar.subheader("Configuración de Especialistas")
num_especialistas = st.sidebar.number_input("Número de especialistas", min_value=1, max_value=10, value=3)

especialistas = []
with st.expander("Información de Especialistas", expanded=True):
    cols = st.columns(num_especialistas)
    
    for i in range(num_especialistas):
        with cols[i]:
            st.subheader(f"Especialista {i+1}")
            especialidad = st.text_input("Especialidad", value=f"Especialidad {i+1}", key=f"esp_{i}")
            tiempo_atencion = st.number_input("Tiempo de atención (minutos)", 
                                             min_value=15, max_value=120, value=30, step=15, key=f"tiempo_{i}")
            
            # Horarios disponibles
            st.write("Horarios disponibles:")
            todos_horarios = generar_horarios(8, 16, 15)
            horarios_seleccionados = []
            
            # Simplificar selección por bloques de horas
            for hora in range(8, 16):
                if st.checkbox(f"{hora}:00 - {hora+1}:00", value=True, key=f"h_{i}_{hora}"):
                    horarios_seleccionados.extend([h for h in todos_horarios if h.startswith(f"{hora:02d}")])
            
            especialistas.append({
                "especialidad": especialidad,
                "tiempo_atencion": tiempo_atencion,
                "horarios_disponibles": horarios_seleccionados
            })

# Sección 2: Configuración de Pacientes
st.sidebar.subheader("Configuración de Pacientes")
num_pacientes = st.sidebar.number_input("Número de pacientes", min_value=1, max_value=30, value=5)

pacientes = []
with st.expander("Información de Pacientes", expanded=True):
    # Crear una tabla editable para los pacientes
    pacientes_data = {
        "Nombre": [f"Paciente {i+1}" for i in range(num_pacientes)],
        "Prioridad": ["Media" for _ in range(num_pacientes)],
        "Distancia (km)": [5 for _ in range(num_pacientes)]
    }
    
    df_pacientes = pd.DataFrame(pacientes_data)
    edited_df = st.data_editor(
        df_pacientes,
        column_config={
            "Nombre": st.column_config.TextColumn("Nombre"),
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
            "prioridad": row["Prioridad"],
            "distancia": row["Distancia (km)"]
        })

# Sección 3: Configuración de Consultorios
st.sidebar.subheader("Configuración de Consultorios")
num_consultorios = st.sidebar.number_input("Número de consultorios", min_value=1, max_value=5, value=2)

# Horarios disponibles para asignación
horarios_disponibles = generar_horarios(8, 16, 15)

# Botón para ejecutar la optimización
if st.button("Optimizar Asignación de Turnos", type="primary"):
    with st.spinner("Optimizando asignación de turnos..."):
        resultado = optimizar_turnos(especialistas, pacientes, num_consultorios, horarios_disponibles)
        
        if resultado is None or resultado.empty:
            st.error("No se pudo encontrar una solución óptima con los parámetros proporcionados. Por favor, ajuste los parámetros e intente nuevamente.")
        else:
            st.success("¡Optimización completada con éxito!")
            
            # Mostrar tabla de resultados
            st.subheader("Turnos Asignados")
            st.dataframe(resultado.sort_values(by=["Consultorio", "Hora_Inicio"]), use_container_width=True)
            
            # Visualización de la programación
            st.subheader("Visualización de Turnos")
            
            # Preparar datos para el diagrama de Gantt
            df_gantt = resultado.copy()
            df_gantt["Resource"] = "Consultorio " + df_gantt["Consultorio"].astype(str) + " - " + df_gantt["Especialidad"]
            df_gantt["Task"] = df_gantt["Nombre_Paciente"] + " (P: " + df_gantt["Prioridad"] + ")"
            
            # Convertir hora inicio y fin a datetime para el gráfico
            fecha_base = datetime.today().date()
            df_gantt["Start"] = pd.to_datetime(fecha_base.strftime("%Y-%m-%d") + " " + df_gantt["Hora_Inicio"])
            df_gantt["Finish"] = pd.to_datetime(fecha_base.strftime("%Y-%m-%d") + " " + df_gantt["Hora_Fin"])
            
            # Colores según prioridad - CORREGIDO
            colores = {"Alta": "rgb(242, 72, 34)", "Media": "rgb(242, 183, 5)", "Baja": "rgb(45, 135, 187)"}
            
            # Crear un diccionario de colores que mapee cada tarea a su color correspondiente
            colors_dict = {}
            for _, row in df_gantt.iterrows():
                colors_dict[row["Task"]] = colores[row["Prioridad"]]
            
            try:
                # Crear el diagrama de Gantt
                fig = ff.create_gantt(
                    df_gantt,
                    colors=colors_dict,  # Mapeo corregido de colores
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
                # Pacientes por especialidad
                especialidad_counts = resultado["Especialidad"].value_counts().reset_index()
                especialidad_counts.columns = ["Especialidad", "Cantidad"]
                
                fig_especialidad = px.bar(
                    especialidad_counts,
                    x="Especialidad",
                    y="Cantidad",
                    title="Pacientes por Especialidad",
                    text_auto=True
                )
                st.plotly_chart(fig_especialidad, use_container_width=True)
                
            with col3:
                # Uso de consultorios
                consultorio_count = resultado["Consultorio"].value_counts().reset_index()
                consultorio_count.columns = ["Consultorio", "Cantidad"]
                consultorio_count["Consultorio"] = "Consultorio " + consultorio_count["Consultorio"].astype(str)
                
                fig_consultorios = px.bar(
                    consultorio_count,
                    x="Consultorio",
                    y="Cantidad",
                    title="Uso de Consultorios",
                    text_auto=True
                )
                st.plotly_chart(fig_consultorios, use_container_width=True)
            
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
    1. Configure el número de especialistas y sus detalles
    2. Ingrese la información de los pacientes
    3. Defina el número de consultorios disponibles
    4. Haga clic en "Optimizar Asignación de Turnos"
    5. Revise los resultados y la visualización
    6. Descargue la programación si es necesario
    
    **Notas importantes:**
    - La prioridad Alta da preferencia al paciente en la asignación
    - La distancia se considera como factor secundario (a menor distancia, mayor prioridad)
    - Los tiempos de atención deben ser múltiplos de 15 minutos
    """)