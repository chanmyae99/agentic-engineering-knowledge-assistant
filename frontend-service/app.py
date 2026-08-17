import time
import uuid

import streamlit as st

from api_client import BackendError, ask_backend


# =========================================================
# Page configuration
# =========================================================

st.set_page_config(
    page_title="Automation Knowledge Assistant",
    page_icon="⚙️",
    layout="wide",
)


# =========================================================
# UI styling
# =========================================================

st.markdown(
    """
    <style>

    /* -----------------------------------------------------
       Main page spacing
    ----------------------------------------------------- */

    .block-container {
        padding-top: 4rem;
        max-width: 1200px;
    }


    /* -----------------------------------------------------
       Small application brand
    ----------------------------------------------------- */

    .app-brand {
        position: fixed;
        top: 1rem;
        left: 24rem;
        z-index: 999;

        display: flex;
        align-items: center;
        gap: 0.45rem;

        padding: 0.3rem 0.65rem;

        font-size: 0.95rem;
        font-weight: 600;

        background: var(--background-color);
        border-radius: 0.5rem;
    }

    .app-brand-icon {
        font-size: 1.05rem;
    }


    /* -----------------------------------------------------
       Clear chat interaction
    ----------------------------------------------------- */

    .st-key-clear_chat button {
        transition:
            color 0.15s ease,
            border-color 0.15s ease,
            background-color 0.15s ease;
    }

    .st-key-clear_chat button:hover {
        color: #f59e0b;
        border-color: #f59e0b;
        background-color: rgba(245, 158, 11, 0.06);
    }


    /* -----------------------------------------------------
       Delete chat interaction
    ----------------------------------------------------- */

    .st-key-delete_chat button {
        transition:
            color 0.15s ease,
            border-color 0.15s ease,
            background-color 0.15s ease;
    }

    .st-key-delete_chat button:hover {
        color: #ef4444;
        border-color: #ef4444;
        background-color: rgba(239, 68, 68, 0.06);
    }


    /* -----------------------------------------------------
       Responsive behaviour
    ----------------------------------------------------- */

    @media (max-width: 768px) {

        .app-brand {
            left: 1rem;
        }

        .block-container {
            padding-top: 4rem;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Session state
# =========================================================

if "chats" not in st.session_state:
    st.session_state.chats = {}

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None


# =========================================================
# Chat management
# =========================================================

def create_new_chat():
    """Create a new session-only conversation."""

    # Do not create another blank chat if the current one is empty.
    current_id = st.session_state.active_chat_id

    if current_id in st.session_state.chats:

        current_chat = st.session_state.chats[current_id]

        if not current_chat.get("messages"):
            return

    chat_id = str(uuid.uuid4())

    st.session_state.chats[chat_id] = {
        "title": "New Chat",
        "messages": [],
    }

    st.session_state.active_chat_id = chat_id


def get_active_chat():
    """Return the currently selected conversation."""

    chat_id = st.session_state.active_chat_id

    if chat_id not in st.session_state.chats:

        chat_id = str(uuid.uuid4())

        st.session_state.chats[chat_id] = {
            "title": "New Chat",
            "messages": [],
        }

        st.session_state.active_chat_id = chat_id

    return st.session_state.chats[chat_id]


def get_active_messages():
    """Return messages belonging to the active conversation."""

    return get_active_chat()["messages"]


def clear_current_chat():
    """Remove messages while keeping the conversation."""

    chat = get_active_chat()

    chat["messages"] = []
    chat["title"] = "New Chat"


def delete_current_chat():
    """Delete the selected conversation."""

    current_id = st.session_state.active_chat_id

    if current_id in st.session_state.chats:
        del st.session_state.chats[current_id]

    # Select another existing chat
    if st.session_state.chats:

        st.session_state.active_chat_id = next(
            reversed(st.session_state.chats)
        )

    # Create fresh chat when none remain
    else:

        chat_id = str(uuid.uuid4())

        st.session_state.chats[chat_id] = {
            "title": "New Chat",
            "messages": [],
        }

        st.session_state.active_chat_id = chat_id

def render_response_disclaimer() -> None:
    """Display a short disclaimer below each assistant response."""

    st.markdown(
        """
        <div style="
            text-align: center;
            font-size: 0.82rem;
            font-weight: 500;
            opacity: 0.75;
            margin-top: 1.2rem;
            margin-bottom: 0.5rem;
        ">
            ⚠️ AI-generated response. Verify important information with the cited sources.
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# Create initial conversation
# =========================================================

if st.session_state.active_chat_id is None:

    chat_id = str(uuid.uuid4())

    st.session_state.chats[chat_id] = {
        "title": "New Chat",
        "messages": [],
    }

    st.session_state.active_chat_id = chat_id


# =========================================================
# Display helpers
# =========================================================

def get_route_label(route: str | None) -> str:
    """Return a readable label for the backend route."""

    labels = {
        "internal": "📚 Internal Knowledge",
        "web": "🌐 Web Search",
        "unavailable": "⚠️ No Reliable Source Found",
    }

    return labels.get(
        route,
        "🤖 AI Response",
    )


# =========================================================
# Source rendering
# =========================================================

def render_sources(sources: list) -> None:
    """Display up to 3 clean, grouped supporting sources."""

    if not sources:
        return

    grouped_internal = {}
    web_sources = []

    for source in sources:
        source_type = source.get("source_type", "internal")

        if source_type == "web":
            web_sources.append(source)
            continue

        title = source.get("title", "Unknown source")
        location = source.get("location")

        if title not in grouped_internal:
            grouped_internal[title] = []

        if location and location not in grouped_internal[title]:
            grouped_internal[title].append(location)

    display_items = []

    # Internal grouped documents
    for title, locations in grouped_internal.items():
        display_items.append(
            {
                "type": "internal",
                "title": title,
                "locations": locations,
            }
        )

    # Web results remain individual links
    for source in web_sources:
        display_items.append(
            {
                "type": "web",
                "title": source.get("title", "Web source"),
                "url": source.get("url"),
            }
        )

    # Keep UI concise
    display_items = display_items[:3]

    if not display_items:
        return

    with st.expander(f"Sources ({len(display_items)})"):

        for index, item in enumerate(display_items):

            if item["type"] == "web":

                st.markdown(
                    f"🌐 **{item['title']}**"
                )

                if item.get("url"):
                    st.link_button(
                        "Open source ↗",
                        item["url"],
                    )

            else:

                st.markdown(
                    f"📄 **{item['title']}**"
                )

                locations = item.get(
                    "locations",
                    [],
                )

                if locations:
                    st.caption(
                        " • ".join(locations)
                    )

            if index < len(display_items) - 1:
                st.divider()

# =========================================================
# Image rendering
# =========================================================

def render_images(images: list) -> None:
    """Display a maximum of two relevant retrieved images."""

    if not images:
        return

    visible_images = images[:2]

    for image in visible_images:

        image_url = image.get(
            "image_url"
        )

        document_name = image.get(
            "document_name",
            "Source document",
        )

        page = image.get("page")

        image_caption = image.get(
            "caption"
        )

        # ---------------------------------------------
        # Source caption
        # ---------------------------------------------

        if page:

            source_caption = (
                f"Source: {document_name} — Page {page}"
            )

        else:

            source_caption = (
                f"Source: {document_name}"
            )

        # ---------------------------------------------
        # Render image
        # ---------------------------------------------

        if image_url:

            try:

                st.image(
                    image_url,
                    caption=source_caption,
                    width="stretch",
                )

            except Exception:

                st.caption(
                    "Image currently unavailable."
                )

        else:

            st.caption(
                "Image currently unavailable."
            )

        # ---------------------------------------------
        # Optional image description
        # ---------------------------------------------

        if image_caption:

            with st.expander(
                "Image details"
            ):

                st.write(
                    image_caption
                )


# =========================================================
# Sidebar
# =========================================================

# =========================================================
# Sidebar
# =========================================================

with st.sidebar:

    # -----------------------------------------------------
    # App identity
    # -----------------------------------------------------

    st.markdown("### ⚙️ Automation Assistant")

    st.caption(
        "Engineering knowledge, safety, SOPs and standards."
    )

    # -----------------------------------------------------
    # New chat
    # -----------------------------------------------------

    if st.button(
        "＋ New Chat",
        use_container_width=True,
        type="primary",
    ):
        create_new_chat()
        st.rerun()

    st.write("")

    # -----------------------------------------------------
    # Recent chat history
    # -----------------------------------------------------

    st.caption("Recent chats")

    # Do not show completely empty chats in history
    chat_items = [
        (chat_id, chat)
        for chat_id, chat in st.session_state.chats.items()
        if chat.get("messages")
    ]

    if not chat_items:
        st.caption("Your conversations will appear here.")

    else:
        # Newest chats first
        for chat_id, chat in reversed(chat_items):

            title = chat.get(
                "title",
                "New Chat",
            )

            # Keep history titles compact
            if len(title) > 30:
                display_title = title[:27] + "..."
            else:
                display_title = title

            is_active = (
                chat_id
                == st.session_state.active_chat_id
            )

            # Simple active-chat indicator
            if is_active:
                display_title = f"› {display_title}"

            if st.button(
                display_title,
                key=f"chat_{chat_id}",
                use_container_width=True,
                help=title,
            ):
                st.session_state.active_chat_id = chat_id
                st.rerun()

    # -----------------------------------------------------
    # Current chat actions
    # -----------------------------------------------------

    st.write("")
    st.divider()

    st.caption("Current chat")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "↻ Clear",
            key="clear_chat",
            use_container_width=True,
            help="Remove all messages from this chat",
        ):
            clear_current_chat()
            st.rerun()

    with col2:
        if st.button(
            "✕ Delete",
            key="delete_chat",
            use_container_width=True,
            help="Delete this conversation",
        ):
            delete_current_chat()
            st.rerun()

    # -----------------------------------------------------
    # Short disclaimer
    # -----------------------------------------------------

    st.write("")
    st.divider()

    st.caption(
        "AI may make mistakes. Verify safety-critical "
        "information with cited sources."
    )

    # -----------------------------------------------------
    # Disclaimer
    # -----------------------------------------------------

    st.write("")
    st.divider()

    st.caption(
        "AI responses may contain errors. "
        "Verify safety-critical and engineering information "
        "using the cited source documents."
    )


# =========================================================
# Small top brand
# =========================================================

st.markdown(
    """
    <div class="app-brand">
        <span class="app-brand-icon">⚙️</span>
        <span>Automation Knowledge Assistant</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Active conversation
# =========================================================

messages = get_active_messages()


# =========================================================
# Empty state
# =========================================================

if not messages:

    st.markdown(
        "### How can I help?"
    )

    st.caption(
        "Ask about automation engineering, workplace safety, "
        "SOPs, standards or technical documents."
    )


# =========================================================
# Render existing conversation
# =========================================================

for message in messages:

    role = message.get(
        "role",
        "assistant",
    )

    with st.chat_message(role):

        # ---------------------------------------------
        # Route
        # ---------------------------------------------

        if role == "assistant":

            route = message.get(
                "route"
            )

            if route:

                st.caption(
                    get_route_label(
                        route
                    )
                )

        # ---------------------------------------------
        # Message
        # ---------------------------------------------

        st.markdown(
            message.get(
                "content",
                "",
            )
        )

        # ---------------------------------------------
        # Assistant supporting information
        # ---------------------------------------------

        if role == "assistant":

            render_images(
                message.get(
                    "images",
                    [],
                )
            )

            render_sources(
                message.get(
                    "sources",
                    [],
                )
            )

            render_response_disclaimer()


# =========================================================
# Chat input
# =========================================================

prompt = st.chat_input(
    "Ask about automation, engineering or safety..."
)


# =========================================================
# Process new question
# =========================================================

if prompt:

    active_chat = get_active_chat()

    # -----------------------------------------------------
    # Generate title from first question
    # -----------------------------------------------------

    if active_chat["title"] == "New Chat":

        if len(prompt) <= 35:

            active_chat["title"] = prompt

        else:

            active_chat["title"] = (
                prompt[:32] + "..."
            )

    # -----------------------------------------------------
    # Save user message
    # -----------------------------------------------------

    user_message = {
        "role": "user",
        "content": prompt,
    }

    active_chat["messages"].append(
        user_message
    )

    # -----------------------------------------------------
    # Show user message immediately
    # -----------------------------------------------------

    with st.chat_message(
        "user"
    ):

        st.markdown(
            prompt
        )

    # -----------------------------------------------------
    # Assistant
    # -----------------------------------------------------

    with st.chat_message(
        "assistant"
    ):

        try:

            # ---------------------------------------------
            # Backend request
            # ---------------------------------------------

            with st.spinner(
                "Searching knowledge..."
            ):

                result = ask_backend(
                    prompt
                )

            # ---------------------------------------------
            # Safely retrieve response fields
            # ---------------------------------------------

            answer = result.get(
                "answer",
                "I could not generate an answer.",
            )

            route = result.get(
                "route"
            )

            sources = result.get(
                "sources",
                [],
            ) or []

            images = result.get(
                "images",
                [],
            ) or []

            # ---------------------------------------------
            # Route indicator
            # ---------------------------------------------

            if route:

                st.caption(
                    get_route_label(
                        route
                    )
                )

            # ---------------------------------------------
            # Progressive answer rendering
            # ---------------------------------------------

            placeholder = st.empty()

            words = answer.split()

            displayed_words = []

            # Long answers should not take too long
            if len(words) < 250:

                delay = 0.015

            else:

                delay = 0.005

            for word in words:

                displayed_words.append(
                    word
                )

                placeholder.markdown(
                    " ".join(
                        displayed_words
                    )
                    + " ▌"
                )

                time.sleep(
                    delay
                )

            # Final answer without cursor
            placeholder.markdown(
                answer
            )

            # ---------------------------------------------
            # Images
            # ---------------------------------------------

            render_images(
                images
            )

            # ---------------------------------------------
            # Sources
            # ---------------------------------------------

            render_sources(
                sources
            )

            # Short AI disclaimer
            render_response_disclaimer()

            # ---------------------------------------------
            # Save complete assistant response
            # ---------------------------------------------

            assistant_message = {
                "role": "assistant",
                "content": answer,
                "route": route,
                "sources": sources,
                "images": images,
            }

            st.session_state.chats[
                st.session_state.active_chat_id
            ]["messages"].append(
                assistant_message
            )

        # =================================================
        # Friendly error
        # =================================================

        except BackendError:

            error_message = (
                "The knowledge service is currently unavailable. "
                "Please try again shortly."
            )

            st.error(
                error_message
            )

            st.session_state.chats[
                st.session_state.active_chat_id
            ]["messages"].append(
                {
                    "role": "assistant",
                    "content": error_message,
                    "route": "unavailable",
                    "sources": [],
                    "images": [],
                }
            )