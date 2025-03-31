import streamlit as st
from settings import client, openai_model
from utils.auth_decorator import require_auth

@require_auth
def main():


    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)
    
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model=openai_model,
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True
            )
            response = st.write_stream(stream)

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
    


# Call the main function
main()