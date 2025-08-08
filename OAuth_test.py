import streamlit as st
import json
import datetime

# Set page configuration
st.set_page_config(page_title="Google OAuth2 Login", page_icon="🔐", layout="centered")

# Main app
st.title("Google OAuth2 Login Example")

# Display login/logout buttons and user info
if not st.user.is_logged_in:
    st.write("Please log in with your Google account to continue.")
    if st.button("Login with Google", key="login"):
        st.login()
else:
    # User is logged in, display user info
    user = st.user
    
    st.success(f"Logged in as {user.name}")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        # Try to display user image if available
        try:
            if hasattr(user, "picture") and user.picture:
                st.image(user.picture, width=100)
            else:
                st.write("👤")
        except Exception as e:
            st.write("👤")
            st.caption(f"Could not load profile image: {str(e)}")
    
    with col2:
        st.subheader("Account Information")
        st.write(f"**Name:** {user.name}")
        st.write(f"**Email:** {user.email}")
        st.write(f"**Unique ID:** {user.sub}")
        
        # Display common OAuth attributes if available
        if hasattr(user, "given_name"):
            st.write(f"**First Name:** {user.given_name}")
        if hasattr(user, "family_name"):
            st.write(f"**Last Name:** {user.family_name}")
        if hasattr(user, "email_verified"):
            st.write(f"**Email Verified:** {'Yes' if user.email_verified else 'No'}")
        if hasattr(user, "exp"):
            timestamp = user.exp
            date = datetime.datetime.fromtimestamp(timestamp)
            st.write(f"**Expires At:** {date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if st.button("Logout"):
        st.logout()