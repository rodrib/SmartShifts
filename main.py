import streamlit as st


# --- PAGE SETUP ---
about_page = st.Page(
    "views/nosotros.py",
    title="Sobre Nosotros",
    icon=":material/account_circle:",
    default=True,
)


project_2_page = st.Page(
    "views/modelo1.py",
    title="Modelo 1",
    icon=":material/smart_toy:",
)

project_3_page = st.Page(
    "views/modelo2.py",
    title="Modelo 2",
    icon=":material/bar_chart:",
)

project_4_page = st.Page(
    "views/modelo3.py",
    title="Modelo 3",
    icon=":material/bar_chart:",
)

project_5_page = st.Page(
    "views/modelo4.py",
    title="Modelo 4",
    icon=":material/bar_chart:",
)

project_6_page = st.Page(
    "views/modelo5.py",
    title="Modelo 5",
    icon=":material/database:",
)


# --- NAVIGATION SETUP [WITHOUT SECTIONS] ---
# pg = st.navigation(pages=[about_page, project_1_page, project_2_page])

# --- NAVIGATION SETUP [WITH SECTIONS]---
pg = st.navigation(
    {
        "Info": [about_page],
        "Modelos": [ project_2_page, project_4_page,project_3_page],
        #"Citogenetica": [project_5_page],
        #"Base de Datos": [project_6_page]
    }
)


# --- SHARED ON ALL PAGES ---
st.logo("assets/codingisfun_logo.png")
st.sidebar.markdown("Made with ❤️ by [Rfeb](https://www.linkedin.com/in/rodrigo-bogado-a64b4925b/)")


# --- RUN NAVIGATION ---
pg.run()