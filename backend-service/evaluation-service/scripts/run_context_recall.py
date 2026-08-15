from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import requests

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from ragas import EvaluationDataset, evaluate
from ragas.dataset_schema import SingleTurnSample
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import LLMContextRecall


load_dotenv()


BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8000",
)


def query_backend(question: str) -> dict:
    """Run one question through the backend evaluation endpoint."""

    response = requests.post(
        f"{BACKEND_URL}/evaluation/query",
        json={"question": question},
        timeout=120,
    )

    response.raise_for_status()

    return response.json()


def main() -> None:
    """Evaluate retrieval coverage using RAGAS Context Recall."""

    input_path = Path(
        "datasets/sample_questions.csv"
    )

    output_path = Path(
        "results/context_recall_results.csv"
    )

    questions_df = pd.read_csv(
        input_path
    )

    samples: list[SingleTurnSample] = []
    routes: list[str] = []

    print("\nCollecting retrieval results...")
    print("=" * 60)

    for _, row in questions_df.iterrows():
        question = str(
            row["question"]
        )

        reference = str(
            row["reference"]
        )

        print(
            f"\nQuestion: {question}"
        )

        backend_result = query_backend(
            question
        )

        retrieved_contexts = (
            backend_result.get(
                "retrieved_contexts",
                [],
            )
        )

        route = backend_result.get(
            "route",
            "",
        )

        print(f"Route: {route}")
        print(
            "Retrieved contexts:",
            len(retrieved_contexts),
        )

        samples.append(
            SingleTurnSample(
                user_input=question,
                retrieved_contexts=retrieved_contexts,
                reference=reference,
            )
        )

        routes.append(route)

    evaluation_dataset = EvaluationDataset(
        samples=samples
    )

    evaluator_llm = LangchainLLMWrapper(
        ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
        )
    )

    context_recall_metric = LLMContextRecall(
        llm=evaluator_llm
    )

    print("\nRunning RAGAS Context Recall...")
    print("=" * 60)

    result = evaluate(
        dataset=evaluation_dataset,
        metrics=[
            context_recall_metric,
        ],
    )

    result_df = result.to_pandas()

    result_df["route"] = routes

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_df.to_csv(
        output_path,
        index=False,
    )

    print("\nEvaluation results")
    print("=" * 60)

    print(
       result_df[
              [
              "user_input",
              "context_recall",
              "route",
              ]
       ]
    )

    print(
        f"\nSaved results to: {output_path}"
    )


if __name__ == "__main__":
    main()