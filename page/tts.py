import streamlit as st
from utils.auth_decorator import require_auth

@require_auth
def main():

    st.title("功能即将上线")
    st.markdown("""
    <|cursor|>
    """)

    #  一个 loading  bar
    latest_iteration = st.empty()
    bar = st.progress(0)

    for i in range(100):
        latest_iteration.text(f'Loading {i+1}%')
        bar.progress(i + 1)


# Call the main function
main()