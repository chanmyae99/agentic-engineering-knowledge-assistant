import time
import uuid

import streamlit as st

from api_client import BackendError, ask_backend


st.set_page_config(
    page_title="Engineering Knowledge Assistant",
    page_icon="🛠️",
    layout="wide",
)


# =========================================================
# Session state
# =========================================================

if "chats" not in st.session_state:
    st.session_state.chats = {}

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None


def create_new_chat():
    """Create a new session-only chat."""

    chat_id = str(uuid.uuid4())

    st.session_state.chats[chat_id] = {
        "title": "New Chat",
        "messages": [],
    }

    st.session_state.active_chat_id = chat_id


if st.session_state.active_chat_id is None:
    create_new_chat()


current_chat = st.session_state.chats[
    st.session_state.active_chat_id
]

messages = current_chat["messages"]


# =========================================================
# Helpers
# =========================================================

def get_route_label(route: str | None) -> str:
    """Convert backend route into a simple user-facing label."""

    labels = {
        "internal": "📚 Internal Knowledge",
        "web": "🌐 Web Search",
        "unavailable": "⚠️ No Reliable Source Found",
    }

    return labels.get(route, "AI Response")


def render_sources(sources: list) -> None:
    """Display up to 3 supporting sources."""

    if not sources:
        return

    visible_sources = sources[:3]

    with st.expander(f"Sources ({len(visible_sources)})"):
        for index, source in enumerate(visible_sources):

            source_type = source.get(
                "source_type",
                "internal",
            )

            title = source.get(
                "title",
                "Unknown source",
            )

            location = source.get("location")
            url = source.get("url")

            if source_type == "web":

                st.markdown(
                    f"🌐 **{title}**"
                )

                if url:
                    st.link_button(
                        "Open source",
                        url,
                    )

            else:

                st.markdown(
                    f"📄 **{title}**"
                )

                if location:
                    st.caption(location)

            if index < len(visible_sources) - 1:
                st.divider()


# =========================================================
# Sidebar
# =========================================================

with st.sidebar:

    st.subheader("Engineering Knowledge Assistant")

    if st.button(
        "＋ New Chat",
        use_container_width=True,
        type="primary",
    ):
        create_new_chat()
        st.rerun()

    st.write("")

    st.caption("Chats")

    # Newest chats first
    chat_items = list(
        st.session_state.chats.items()
    )

    for chat_id, chat in reversed(chat_items):

        title = chat["title"]

        if len(title) > 35:
            title = title[:32] + "..."

        if st.button(
            title,
            key=f"chat_{chat_id}",
            use_container_width=True,
        ):
            st.session_state.active_chat_id = chat_id
            st.rerun()

    st.divider()

    if st.button(
        "Clear current chat",
        use_container_width=True,
    ):
        current_chat["messages"] = []
        current_chat["title"] = "New Chat"
        st.rerun()

    st.divider()

    st.caption(
        "AI-generated responses may contain errors. "
        "For safety-critical or engineering decisions, "
        "verify the answer using the cited source documents."
    )


# =========================================================
# Header
# =========================================================

st.title("Engineering Knowledge Assistant")

st.caption(
    "Ask questions about engineering standards, "
    "workplace safety, SOPs and technical documents."
)


# =========================================================
# Welcome state
# =========================================================

if not messages:

    st.markdown("### How can I help?")

    st.write(
        "Ask about workplace safety requirements, "
        "engineering standards, SOP procedures, "
        "manufacturing hazards and technical documents."
    )

    st.write("")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(
            "What is combustible dust?"
        )

    with col2:
        st.info(
            "What PPE should workers use?"
        )

    with col3:
        st.info(
            "What are the system architecture requirements?"
        )


# =========================================================
# Existing chat history
# =========================================================

for message in messages:

    with st.chat_message(message["role"]):

        if message["role"] == "assistant":

            route = message.get("route")

            if route:
                st.caption(
                    get_route_label(route)
                )

        st.markdown(
            message["content"]
        )

        if message["role"] == "assistant":

            render_sources(
                message.get(
                    "sources",
                    [],
                )
            )


# =========================================================
# Chat input
# =========================================================

prompt = st.chat_input(
    "Ask an engineering or safety question..."
)


if prompt:

    # -----------------------------------------
    # Rename chat using first question
    # -----------------------------------------

    if current_chat["title"] == "New Chat":

        current_chat["title"] = (
            prompt
            if len(prompt) <= 35
            else prompt[:32] + "..."
        )

    # -----------------------------------------
    # User message
    # -----------------------------------------

    user_message = {
        "role": "user",
        "content": prompt,
    }

    messages.append(
        user_message
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # -----------------------------------------
    # Backend answer
    # -----------------------------------------

    with st.chat_message("assistant"):

        try:

            with st.spinner(
                "Searching engineering knowledge..."
            ):

                result = ask_backend(prompt)

            answer = result.get(
                "answer",
                "I could not generate an answer.",
            )

            route = result.get("route")

            sources = result.get(
                "sources",
                [],
            )

            images = result.get(
                "images",
                [],
            )

            # ---------------------------------
            # Route indicator
            # ---------------------------------

            if route:
                st.caption(
                    get_route_label(route)
                )

            # ---------------------------------
            # Progressive answer
            # ---------------------------------

            placeholder = st.empty()

            words = answer.split()

            displayed_words = []

            delay = (
                0.015
                if len(words) < 250
                else 0.005
            )

            for word in words:

                displayed_words.append(word)

                placeholder.markdown(
                    " ".join(
                        displayed_words
                    )
                    + " ▌"
                )

                time.sleep(delay)

            placeholder.markdown(answer)

            # ---------------------------------
            # Sources
            # ---------------------------------

            render_sources(sources)

            # ---------------------------------
            # Save assistant message
            # ---------------------------------

            assistant_message = {
                "role": "assistant",
                "content": answer,
                "route": route,
                "sources": sources,
                "images": images,
            }

            messages.append(
                assistant_message
            )

        except BackendError as error:

            st.error(str(error))