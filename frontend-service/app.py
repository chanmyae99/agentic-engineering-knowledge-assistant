import streamlit as st

from api_client import BackendError, ask_backend


st.set_page_config(
    page_title="Engineering Knowledge Assistant",
    page_icon="🛠️",
    layout="wide",
)


# -----------------------------
# Session state
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.subheader("Engineering Knowledge Assistant")

    st.write(
        "Ask questions about engineering standards, workplace safety, "
        "SOPs and technical documents."
    )

    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.caption("Service configuration")
    st.info("Backend: http://127.0.0.1:8000")

    st.divider()

    st.caption(
        "AI-generated responses may contain errors. "
        "Verify important engineering and safety information "
        "against the cited source documents."
    )


# -----------------------------
# Main header
# -----------------------------
st.title("Engineering Knowledge Assistant")

st.caption(
    "Ask questions about engineering standards, workplace safety, "
    "SOPs and technical documents."
)


# -----------------------------
# Empty welcome state
# -----------------------------
if not st.session_state.messages:
    st.markdown("### How can I help?")

    st.write(
        """
Ask about:

- workplace safety requirements
- engineering standards
- combustible dust hazards
- SOP procedures
- manufacturing hazards
"""
    )

    st.caption("Example questions")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("What is combustible dust?")

    with col2:
        st.info("What PPE should workers use?")

    with col3:
        st.info("What are the system architecture requirements?")


# -----------------------------
# Render chat history
# -----------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# -----------------------------
# Chat input
# -----------------------------
prompt = st.chat_input("Ask an engineering or safety question...")

if prompt:
    # Save and display the user message
    user_message = {
        "role": "user",
        "content": prompt,
    }

    st.session_state.messages.append(user_message)

    with st.chat_message("user"):
        st.markdown(prompt)

    # Ask the existing FastAPI backend
    with st.chat_message("assistant"):
        with st.spinner("Searching engineering knowledge..."):
            try:
                result = ask_backend(prompt)

                answer = result.get(
                    "answer",
                    "I could not generate an answer.",
                )

                st.markdown(answer)

                assistant_message = {
                    "role": "assistant",
                    "content": answer,
                    "route": result.get("route"),
                    "sources": result.get("sources", []),
                    "images": result.get("images", []),
                }

                st.session_state.messages.append(
                    assistant_message
                )

            except BackendError as error:
                st.error(str(error))