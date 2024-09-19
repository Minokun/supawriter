import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
import page_settings
PAGES = page_settings.PAGES
import streamlit as st
st.logo(image='https://www.apuqi.com/uploads/logo.png')
pg = st.navigation(PAGES)
pg.run()