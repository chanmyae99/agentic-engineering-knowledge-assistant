import os

import requests
from dotenv import load_dotenv


load_dotenv()


BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8000",
)

REQUEST_TIMEOUT = int(
    os.getenv("REQUEST_TIMEOUT", "60")
)


class BackendError(Exception):
    """Friendly exception raised when the backend cannot answer a request."""


def ask_backend(question: str) -> dict:
    """
    Send a user question to the FastAPI /chat endpoint.

    The frontend does not perform retrieval or RAG logic.
    It only sends the question and returns the backend response.
    """

    try:
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={"question": question},
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except requests.exceptions.Timeout as exc:
        raise BackendError(
            "The knowledge service took too long to respond. Please try again."
        ) from exc

    except requests.exceptions.ConnectionError as exc:
        raise BackendError(
            "The knowledge service is currently unavailable. Please try again shortly."
        ) from exc

    except requests.exceptions.HTTPError as exc:
        raise BackendError(
            "The knowledge service encountered an error while processing your request."
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise BackendError(
            "Unable to communicate with the knowledge service."
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise BackendError(
            "The knowledge service returned an invalid response."
        ) from exc

    if not isinstance(data, dict):
        raise BackendError(
            "The knowledge service returned an unexpected response."
        )

    return data