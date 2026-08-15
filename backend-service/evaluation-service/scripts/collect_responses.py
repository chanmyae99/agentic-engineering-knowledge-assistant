from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests


BACKEND_URL = "http://127.0.0.1:8000"


def ask_backend(question: str) -> dict:
    """Send one evaluation question to the real backend."""
    response = requests.post(
        f"{BACKEND_URL}/chat",
        json={"question": question},
        timeout=120,
    )

    response.raise_for_status()

    return response.json()


def main() -> None:
    dataset_path = Path(
        "datasets/sample_questions.csv"
    )

    output_path = Path(
        "results/sample_backend_responses.json"
    )

    questions = pd.read_csv(dataset_path)

    results: list[dict] = []

    for _, row in questions.iterrows():
        question = str(row["question"])
        reference = str(row["reference"])

        print(f"Testing: {question}")

        response = ask_backend(question)

        results.append(
            {
                "question": question,
                "reference": reference,
                "answer": response.get("answer", ""),
                "route": response.get("route"),
                "sources": response.get("sources", []),
                "metadata": response.get(
                    "metadata",
                    {},
                ),
            }
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"\nSaved {len(results)} responses "
        f"to {output_path}"
    )


if __name__ == "__main__":
    main()