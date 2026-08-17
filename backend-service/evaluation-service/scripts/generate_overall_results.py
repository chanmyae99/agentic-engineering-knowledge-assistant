from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"


def mean_score(file_name: str, score_column: str) -> float:
    df = pd.read_csv(RESULTS_DIR / file_name)
    return df[score_column].mean()


def main():
    routing_df = pd.read_csv(
        RESULTS_DIR / "routing_accuracy_results.csv"
    )

    results = {
        "Routing Accuracy": routing_df["correct"].mean(),
        "Context Precision": mean_score(
            "context_precision_results.csv",
            "llm_context_precision_with_reference",
        ),
        "Context Recall": mean_score(
            "context_recall_results.csv",
            "context_recall",
        ),
        "Faithfulness": mean_score(
            "faithfulness_results.csv",
            "faithfulness",
        ),
    }

    overall_df = pd.DataFrame(
        [
            {
                "metric": metric,
                "score": round(score, 4),
            }
            for metric, score in results.items()
        ]
    )

    output_path = RESULTS_DIR / "overall_metrics_results.csv"
    overall_df.to_csv(output_path, index=False)

    print("\nOverall Evaluation Results")
    print("-" * 40)

    for metric, score in results.items():
        print(f"{metric:<20}: {score:.4f}")

    print("-" * 40)
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()