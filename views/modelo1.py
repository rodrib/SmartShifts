import streamlit as st
# Configuración de la página de Streamlit - DEBE SER LA PRIMERA LLAMADA A STREAMLIT


import pandas as pd
import numpy as np
import pulp
from datetime import datetime, timedelta
import plotly.figure_factory as ff
import plotly.express as px

st.title("Sistema de Optimización de Turnos Médicos")
