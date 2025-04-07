import streamlit as st
import datetime
import pandas as pd

def time_to_minutes(t):
    return (t.hour - 8) * 60 + t.minute

def minutes_to_time(m):
    hours = 8 + m // 60
    minutes = m % 60
    return f"{hours:02d}:{minutes:02d}"

def is_overlapping(start, end, intervals):
    for s, e in intervals:
        if not (end <= s or start >= e):
            return True
    return False

# Inicializar estado de sesión
if 'specialists' not in st.session_state:
    st.session_state.specialists = []
if 'patients' not in st.session_state:
    st.session_state.patients = []

st.title("Optimización de Asignación de Turnos Médicos")

# Ingreso de especialidades
especialidades = st.text_input("Ingrese las especialidades médicas, separadas por comas (ej: Cardiología, Pediatría)")
specialties = [s.strip() for s in especialidades.split(',')] if especialidades else []

if not specialties:
    st.warning("Por favor, ingrese al menos una especialidad médica.")
    st.stop()

# Agregar especialistas
st.subheader("Registro de Especialistas")
with st.form("add_specialist_form"):
    col1, col2 = st.columns(2)
    with col1:
        specialty = st.selectbox("Especialidad", options=specialties)
        start_time = st.time_input("Horario inicio", value=datetime.time(8, 0))
    with col2:
        time_per_patient = st.number_input("Duración por paciente (min)", min_value=15, step=15, value=30)
        end_time = st.time_input("Horario fin", value=datetime.time(16, 0))
    
    submitted = st.form_submit_button("Agregar Especialista")
    if submitted:
        start_min = time_to_minutes(start_time)
        end_min = time_to_minutes(end_time)
        
        if start_min < 0 or end_min > 480 or start_min >= end_min:
            st.error("Error: Horario fuera de rango (8:00 - 16:00) o inicio mayor que fin")
        else:
            st.session_state.specialists.append({
                'especialidad': specialty,
                'disponibilidad': [(start_min, end_min)],
                'ocupado': [],
                'duracion': time_per_patient
            })
            st.success("Especialista agregado!")

# Agregar pacientes
st.subheader("Registro de Pacientes")
with st.form("add_patient_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        priority = st.selectbox("Prioridad", options=["Alta", "Media", "Baja"])
    with col2:
        distance = st.number_input("Distancia (km)", min_value=0, value=5)
    with col3:
        required_specialty = st.selectbox("Especialidad requerida", options=specialties)
    
    submitted_patient = st.form_submit_button("Agregar Paciente")
    if submitted_patient:
        st.session_state.patients.append({
            'prioridad': {"Alta": 3, "Media": 2, "Baja": 1}[priority],
            'distancia': distance,
            'especialidad': required_specialty,
            'datos': f"Prioridad {priority}, Distancia {distance}km"
        })
        st.success("Paciente agregado!")

# Mostrar datos registrados
st.subheader("Datos Ingresados")
col1, col2 = st.columns(2)
with col1:
    st.write("**Especialistas:**")
    st.json(st.session_state.specialists)
with col2:
    st.write("**Pacientes:**")
    st.json(st.session_state.patients)

# Algoritmo de asignación
if st.button("Generar Asignación Óptima"):
    if not st.session_state.specialists or not st.session_state.patients:
        st.error("Error: Faltan datos de especialistas o pacientes")
        st.stop()
    
    # Ordenar pacientes por prioridad y distancia
    pacientes_ordenados = sorted(st.session_state.patients, 
                                key=lambda x: (-x['prioridad'], x['distancia']))
    
    # Inicializar consultorios
    consultorios = [{'ocupado': []}, {'ocupado': []}]
    asignaciones = []
    no_asignados = []

    for paciente in pacientes_ordenados:
        especialidad_pac = paciente['especialidad']
        posibles_especialistas = [e for e in st.session_state.specialists 
                                if e['especialidad'] == especialidad_pac]
        
        mejor_hora = None
        mejor_especialista = None
        mejor_consultorio = None

        for especialista in posibles_especialistas:
            duracion = especialista['duracion']
            
            for disp_inicio, disp_fin in especialista['disponibilidad']:
                # Buscar en intervalos de 1 minuto
                for hora_actual in range(disp_inicio, disp_fin - duracion + 1):
                    fin = hora_actual + duracion
                    
                    # Verificar disponibilidad del especialista
                    if is_overlapping(hora_actual, fin, especialista['ocupado']):
                        continue
                    
                    # Verificar disponibilidad de consultorios
                    for c_idx, consultorio in enumerate(consultorios):
                        if not is_overlapping(hora_actual, fin, consultorio['ocupado']):
                            if mejor_hora is None or hora_actual < mejor_hora:
                                mejor_hora = hora_actual
                                mejor_especialista = especialista
                                mejor_consultorio = c_idx
                            break
                    
                    if mejor_hora is not None:
                        break
                if mejor_hora is not None:
                    break
            if mejor_hora is not None:
                break

        if mejor_hora is not None:
            # Registrar asignación
            especialista['ocupado'].append((mejor_hora, mejor_hora + duracion))
            consultorios[mejor_consultorio]['ocupado'].append((mejor_hora, mejor_hora + duracion))
            
            asignaciones.append({
                'Paciente': paciente['datos'],
                'Especialidad': especialidad_pac,
                'Especialista': f"Especialista {st.session_state.specialists.index(mejor_especialista) + 1}",
                'Consultorio': mejor_consultorio + 1,
                'Inicio': minutes_to_time(mejor_hora),
                'Fin': minutes_to_time(mejor_hora + duracion)
            })
        else:
            no_asignados.append(paciente)

    # Mostrar resultados
    st.subheader("Resultados de la Asignación")
    
    if asignaciones:
        df = pd.DataFrame(asignaciones)
        st.dataframe(df[['Paciente', 'Especialidad', 'Consultorio', 'Inicio', 'Fin']])
    else:
        st.warning("No se pudieron realizar asignaciones")
    
    if no_asignados:
        st.subheader("Pacientes no asignados")
        for p in no_asignados:
            st.error(p['datos'])