from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import requests

from dotenv import load_dotenv


load_dotenv()


BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8000",
)


def query_backend(question: str) -> dict:
    """Send one evaluation question to the real chat endpoint."""

    response = requests.post(
        f"{BACKEND_URL}/chat",
        json={
            "question": question,
        },
        timeout=120,
    )

    response.raise_for_status()

    return response.json()


def main() -> None:
    """Measure internal-versus-web routing accuracy."""

    input_path = Path(
        "datasets/sample_questions.csv"
    )

    output_path = Path(
        "results/routing_accuracy_results.csv"
    )

    questions_df = pd.read_csv(
        input_path
    )

    results: list[dict] = []

    print("\nRunning Routing Accuracy Evaluation...")
    print("=" * 60)

    for _, row in questions_df.iterrows():
        question = str(
            row["question"]
        )

        expected_route = str(
            row["expected_route"]
        ).strip().lower()

        print(
            f"\nQuestion: {question}"
        )

        backend_result = query_backend(
            question
        )

        actual_route = str(
            backend_result.get(
                "route",
                "",
            )
        ).strip().lower()

        is_correct = (
            actual_route == expected_route
        )

        metadata = backend_result.get(
            "metadata",
            {},
        )

        print(
            f"Expected: {expected_route}"
        )
        print(
            f"Actual:   {actual_route}"
        )
        print(
            f"Correct:  {is_correct}"
        )

        results.append(
            {
                "id": row["id"],
                "question": question,
                "expected_route": expected_route,
                "actual_route": actual_route,
                "correct": is_correct,
                "highest_retrieval_score": (
                    metadata.get(
                        "highest_retrieval_score"
                    )
                ),
                "route_reason": (
                    metadata.get(
                        "route_reason"
                    )
                ),
            }
        )

    result_df = pd.DataFrame(
        results
    )

    total = len(result_df)

    correct_count = int(
        result_df["correct"].sum()
    )

    routing_accuracy = (
        correct_count / total
        if total > 0
        else 0.0
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_df.to_csv(
        output_path,
        index=False,
    )

    print("\nRouting Evaluation Results")
    print("=" * 60)

    print(
        result_df[
            [
                "question",
                "expected_route",
                "actual_route",
                "correct",
            ]
        ]
    )

    print("\nSummary")
    print("=" * 60)

    print(
        f"Correct routes: {correct_count}/{total}"
    )

    print(
        f"Routing Accuracy: "
        f"{routing_accuracy * 100:.2f}%"
    )

    print(
        f"\nSaved results to: {output_path}"
    )


if __name__ == "__main__":
    main()