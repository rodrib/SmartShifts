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
        "Fomentar, organizar y regular la investigación en bioinformática como herramienta clave para mejorar la toma de decisiones en las políticas de salud a través del análisis de datos científicos."
    )
    if st.button("✉️ Contact Me"):
        pass
        #show_contact_form()


# --- EXPERIENCE & QUALIFICATIONS ---
st.write("\n")
st.subheader("FUNCIONES", anchor=False)
st.write(
    """
    - Análisis genómico para la identificación de biomarcadores en cáncer y EPOF: Utilizando herramientas bioinformáticas para analizar datos genómicos y transcriptómicos con el fin de identificar biomarcadores específicos que puedan predecir la susceptibilidad al cáncer y enfermedades de origen funcional.

- Estudio de proteínas y análisis de sus interacciones: Emplear técnicas de modelado molecular y análisis de redes para comprender las interacciones proteicas en el cáncer y EPOF, lo que ayuda a identificar dianas terapéuticas potenciales y nuevos enfoques para el tratamiento.

- Desarrollo de bases de datos clínicas y genómicas: Crear y gestionar bases de datos estructuradas que integren información clínica, molecular y genómica para facilitar la investigación sobre cáncer y EPOF, promoviendo el acceso eficiente a grandes volúmenes de datos.

- Generación de tablas y visualización de datos: Utilizar herramientas de bioinformática para organizar y generar tablas que resuman información clave sobre el cáncer, EPOF y análisis molecular de proteínas, permitiendo la interpretación y toma de decisiones basadas en datos.

- Predicción de respuestas a tratamientos y terapia personalizada: Aplicar modelos bioinformáticos para analizar perfiles genómicos y moleculares de tumores y enfermedades, con el fin de predecir la respuesta de los pacientes a tratamientos específicos y facilitar la medicina personalizada en el ámbito oncológico y de EPOF.
    """
)


# --- SKILLS ---
st.write("\n")
st.subheader("MIEMBROS", anchor=False)
st.write(
    """
    - Rodrigo Bogado (Rfeb)
    - Belen Brizuela
    - Jose Luis Cribb (Jl)
    - Marcelo Gamarra (Chelo)
    """
)