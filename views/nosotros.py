import streamlit as st



@st.experimental_dialog("Contact Me")
def show_contact_form():
    pass
    #contact_form()


# --- HERO SECTION ---
col1, col2 = st.columns(2, gap="small", vertical_alignment="center")
with col1:
    st.image("./assets/images (1).png", width=230)

with col2:
    st.title("Unidad de EPOF", anchor=False)
    st.write(
        "Estimular el compromiso y el esfuerzo coordinado en la atención integral de personas con EPF para lograr mejorar su calidad de vida y la de sus familias "
    )
    if st.button("✉️ Contact Me"):
        pass
        #show_contact_form()


# --- EXPERIENCE & QUALIFICATIONS ---
st.write("\n")
st.subheader("OBJETIVOS", anchor=False)

st.write("""
**Objetivos del Circuito Interdisciplinario:**

- Reducir el tiempo de atención de las interconsultas solicitadas por la médica genetista.
- Implementar consultas integradas en un mismo día y horario para atención interdisciplinaria.
- Asegurar una secuencialidad preestablecida en la atención.
- Facilitar el acceso a consultas y al diagnóstico temprano y preciso.
- Aplicar protocolos para diagnóstico oportuno, plan terapéutico y seguimiento.
- Formar equipos especializados según grupos de enfermedades poco frecuentes (neuromusculares, metabólicas, cardíacas, etc.).
- Crear redes internas y externas según la complejidad de cada caso, con enfoque bio-psico-social.
- Establecer estrategias de formación continua.
- Brindar apoyo psicológico y social a pacientes y familias para mitigar el impacto emocional y social de vivir con una enfermedad poco frecuente.
""")



# --- SKILLS ---
st.write("\n")
st.subheader("SERVICIOS", anchor=False)

st.write("""
**Servicios incluidos en la UNIDAD EPF**

**Consultorio Integrado – Hospital Madariaga**  
Servicios con horarios de atención disponibles:
1. Cardiología  
2. Clínica Médica  
3. Cuidados Paliativos  
4. Neurología  
5. Oftalmología  
6. Rehabilitación  
7. Reumatología  
8. Salud Mental  
9. Traumatología (columna, en general)  

*Otros servicios se incorporarán según demanda.*

**Instituto de Genética Humana**
- Genética Clínica (Área Adultos): Dra. Rossana Espíndola (coordinadora médica)  
- Trabajo Social (Área Adultos): Lic. Laura Guadalupe  
- Salud Mental: Mgter. Nicolás Mazal  
- Gestión de Pacientes: Estefanía Di Dio  

**Fuera del Consultorio Integrado**

**IGeHM**  
- Laboratorios: Citogenética, Citomolecular, Genética Molecular y Genómica  
- Bioinformática  
- TIC  
- Docencia, Investigación y Extensión  

**HEA**  
- Admisión Central  
- Servicio Social  
- Docencia e Investigación
""")
