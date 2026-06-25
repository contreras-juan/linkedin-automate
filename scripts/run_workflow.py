from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.graph import run_workflow  # noqa: E402


DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "workflow_state.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LinkedIn multi-agent workflow locally.")
    parser.add_argument("--max-results", type=int, default=3)
    parser.add_argument("--categories", nargs="+", default=["cs.CL", "cs.AI", "cs.LG"])
    parser.add_argument("--profile-path", default=str(PROJECT_ROOT / "config" / "filter_profile.json"))
    parser.add_argument("--output-path", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()

    final_state = run_workflow(
        categories=args.categories,
        max_results=args.max_results,
        profile_path=args.profile_path,
    )

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(final_state.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote workflow state to {output_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
