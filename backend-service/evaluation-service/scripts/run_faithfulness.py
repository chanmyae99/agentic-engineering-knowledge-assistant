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
from ragas.metrics import Faithfulness


load_dotenv()


BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8000",
)


def query_backend(question: str) -> dict:
    """
    Send one question to the backend evaluation endpoint.

    The endpoint returns both the generated answer and the exact
    retrieved text chunks used by the RAG pipeline.
    """

    response = requests.post(
        f"{BACKEND_URL}/evaluation/query",
        json={
            "question": question,
        },
        timeout=120,
    )

    response.raise_for_status()

    return response.json()


def main() -> None:
    """Run RAGAS Faithfulness on the sample evaluation set."""

    input_path = Path(
        "datasets/sample_questions.csv"
    )

    output_path = Path(
        "results/faithfulness_results.csv"
    )

    questions_df = pd.read_csv(
        input_path
    )

    samples: list[SingleTurnSample] = []

    routes: list[str] = []

    print("\nCollecting RAG responses...")
    print("=" * 60)

    for _, row in questions_df.iterrows():
        question = str(
            row["question"]
        )

        print(
            f"\nQuestion: {question}"
        )

        backend_result = query_backend(
            question
        )

        answer = backend_result.get(
            "answer",
            "",
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

        print(
            f"Route: {route}"
        )

        print(
            "Retrieved contexts:",
            len(retrieved_contexts),
        )

        samples.append(
            SingleTurnSample(
                user_input=question,
                retrieved_contexts=retrieved_contexts,
                response=answer,
            )
        )

        routes.append(route)

    evaluation_dataset = EvaluationDataset(
        samples=samples
    )

    # RAGAS uses an evaluator LLM to judge whether claims in the
    # generated response are supported by the retrieved contexts.
    evaluator_llm = LangchainLLMWrapper(
        ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
        )
    )

    faithfulness_metric = Faithfulness(
        llm=evaluator_llm
    )

    print("\nRunning RAGAS Faithfulness...")
    print("=" * 60)

    result = evaluate(
        dataset=evaluation_dataset,
        metrics=[
            faithfulness_metric,
        ],
    )

    result_df = result.to_pandas()

    # Preserve useful information from our application alongside
    # the RAGAS metric result.
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
    print(result_df)

    print(
        f"\nSaved results to: {output_path}"
    )


if __name__ == "__main__":
    main()