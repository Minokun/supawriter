import page_settings
import streamlit as st
from utils.auth_decorator import require_auth

@require_auth
def main():

    st.page_link(page_settings.PAGE_GPTS_AUTOWITER)


# Call the main function
main()