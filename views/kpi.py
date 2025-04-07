import streamlit as st
# Configuración de la página de Streamlit - DEBE SER LA PRIMERA LLAMADA A STREAMLIT


import pandas as pd
import numpy as np
import pulp
from datetime import datetime, timedelta
import plotly.figure_factory as ff
import plotly.express as px

st.write("""
**KPI's (Indicadores Clave de Desempeño)**

---

### 🔧 Operativos
- **Tiempo promedio por paciente en completar todas las consultas**  
  *Meta:* ≤ 7 horas. (1)

- **% de pacientes que completan todas las consultas asignadas durante el día**  
  *Meta:* ≥ 90%. (1)

- **% de cumplimiento de las agendas de los especialistas**  
  *Meta:* ≥ 95%. (3)  
  - Se medirá por especialidad (promedio)  
  - Se medirá por especialista (promedio)

---

### 😊 Experiencia del paciente
*(Diseñar encuesta no orientada)*

- **Nivel de satisfacción con el acompañamiento social**  
  *Meta:* ≥ 85% de satisfacción (2) – *PSP*

- **Nivel de satisfacción general con el proceso**  
  *Meta:* ≥ 85% de satisfacción. (4)

---

### 💰 Económicos y logísticos (5)
- **Costo promedio por paciente del proyecto piloto**  
  (Costo prorrateado incluyendo traslado, permanencia y alimentación del paciente y acompañante/s)

- **Comparación del costo total del proyecto piloto frente al modelo tradicional**  
  *Meta:* Reducción de ≥ 10%.

---

### ✅ Factibilidad y viabilidad (5)
- **Evaluación cualitativa de los especialistas y la secretaria sobre la logística y viabilidad del modelo**  
  Se establecerán 3 categorías para ambos aspectos:  
  - ALTO  
  - MEDIO  
  - BAJO
""")
