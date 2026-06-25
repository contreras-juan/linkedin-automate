from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from src.graph import run_workflow  # noqa: E402


DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "workflow_state.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LinkedIn multi-agent workflow locally.")
    parser.add_argument("--max-results", type=int, default=_get_int_env("WORKFLOW_MAX_RESULTS", 3))
    parser.add_argument("--categories", nargs="+", default=["cs.CL", "cs.AI", "cs.LG"])
    parser.add_argument(
        "--profile-path",
        default=str(_resolve_project_path(os.getenv("FILTER_PROFILE_PATH", "config/filter_profile.json"))),
    )
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


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError:
        return default


def _resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


if __name__ == "__main__":
    main()
