"""
Operation Sugar Research Pipeline Runner.

Run the complete local research workflow from monthly weather
aggregation to final analytics dashboards.

Usage
-----
Concise output:
python -m src.pipelines.run_pipeline

Full stage output:
python -m src.pipelines.run_pipeline --verbose
"""

import argparse
import io
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from time import perf_counter

from src.config.version import __version__
from src.etl.aggregate_monthly_weather import (
    main as aggregate_monthly_weather,
)
from src.etl.build_growing_season_features import (
    main as build_growing_season_features,
)
from src.visualization.build_comparison_dashboard import (
    main as build_comparison_dashboard,
)
from src.visualization.build_dashboard import (
    main as build_dashboard,
)
from src.visualization.build_weather_harvest_dataset import (
    main as build_weather_harvest_dataset,
)


SEPARATOR_WIDTH = 72
SUMMARY_NAME_WIDTH = 48


@dataclass(frozen=True)
class PipelineStage:
    """Represent one executable stage in the research pipeline."""

    name: str
    function: Callable[[], None]


PIPELINE_STAGES: tuple[PipelineStage, ...] = (
    PipelineStage(
        name="Aggregate Monthly Weather",
        function=aggregate_monthly_weather,
    ),
    PipelineStage(
        name="Build Growing-Season Features",
        function=build_growing_season_features,
    ),
    PipelineStage(
        name="Build Weather-Harvest Dataset",
        function=build_weather_harvest_dataset,
    ),
    PipelineStage(
        name="Build Single-Season Dashboard",
        function=build_dashboard,
    ),
    PipelineStage(
        name="Build Historical Comparison Dashboard",
        function=build_comparison_dashboard,
    ),
)

RESEARCH_ARTIFACTS: tuple[str, ...] = (
    "data/processed/dashboard/weather_harvest_dataset.csv",
    "docs/dashboard_v1.png",
    "docs/dashboard_season_comparison.png",
)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Run the Operation Sugar research pipeline.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Display the complete output produced by every pipeline stage.",
    )

    return parser.parse_args()


def format_elapsed_time(seconds: float) -> str:
    """Return elapsed time in a human-readable format."""

    if seconds < 60:
        return f"{seconds:.2f}s"

    minutes, remaining_seconds = divmod(seconds, 60)

    return f"{int(minutes)}m {remaining_seconds:.2f}s"


def print_pipeline_header(
    total_stages: int,
    verbose: bool,
) -> None:
    """Print the pipeline title, version, and execution mode."""

    output_mode = "Verbose" if verbose else "Concise"

    print("=" * SEPARATOR_WIDTH)
    print("Operation Sugar Research Pipeline")
    print(f"Version: v{__version__}")
    print(f"Output Mode: {output_mode}")
    print(f"Pipeline Stages: {total_stages}")
    print("=" * SEPARATOR_WIDTH)


def execute_stage(
    stage: PipelineStage,
    verbose: bool,
) -> str:
    """
    Execute a pipeline stage.

    In concise mode, stage output is captured rather than printed.
    The captured output is returned so it can be shown if the stage fails.
    """

    if verbose:
        stage.function()
        return ""

    captured_output = io.StringIO()

    with (
        redirect_stdout(captured_output),
        redirect_stderr(captured_output),
    ):
        stage.function()

    return captured_output.getvalue()


def run_stage(
    stage: PipelineStage,
    stage_number: int,
    total_stages: int,
    verbose: bool,
) -> float:
    """
    Run one pipeline stage and return its elapsed time.

    If a stage fails in concise mode, its captured output is displayed
    before the original exception is re-raised.
    """

    print()
    print(
        f"[{stage_number}/{total_stages}] "
        f"{stage.name}..."
    )

    start_time = perf_counter()
    captured_output = ""

    try:
        captured_output = execute_stage(
            stage=stage,
            verbose=verbose,
        )
    except Exception:
        elapsed_time = perf_counter() - start_time

        print(
            f"[FAILED] {stage.name} "
            f"({format_elapsed_time(elapsed_time)})"
        )

        if captured_output.strip():
            print()
            print("Stage output:")
            print("-" * SEPARATOR_WIDTH)
            print(captured_output.rstrip())
            print("-" * SEPARATOR_WIDTH)

        print("Pipeline stopped.")

        raise

    elapsed_time = perf_counter() - start_time

    print(
        f"[OK] {stage.name} "
        f"({format_elapsed_time(elapsed_time)})"
    )

    return elapsed_time


def print_pipeline_summary(
    stage_times: list[tuple[str, float]],
    total_elapsed_time: float,
) -> None:
    """Print the final pipeline execution summary."""

    print()
    print("=" * SEPARATOR_WIDTH)
    print("Research pipeline completed successfully")
    print("=" * SEPARATOR_WIDTH)

    for stage_name, elapsed_time in stage_times:
        dotted_name = f"{stage_name} ".ljust(
            SUMMARY_NAME_WIDTH,
            ".",
        )

        print(
            f"[OK] {dotted_name}"
            f"{format_elapsed_time(elapsed_time)}"
        )

    print("-" * SEPARATOR_WIDTH)

    print()
    print("Research Artifacts")
    print()

    for artifact in RESEARCH_ARTIFACTS:
        print(f"[✓] {artifact}")

    print()
    print("-" * SEPARATOR_WIDTH)

    print(
        "Total Runtime: "
        f"{format_elapsed_time(total_elapsed_time)}"
    )
    print("=" * SEPARATOR_WIDTH)


def main() -> None:
    """Run the complete Operation Sugar research pipeline."""

    arguments = parse_arguments()
    total_stages = len(PIPELINE_STAGES)

    print_pipeline_header(
        total_stages=total_stages,
        verbose=arguments.verbose,
    )

    pipeline_start_time = perf_counter()
    stage_times: list[tuple[str, float]] = []

    for stage_number, stage in enumerate(
        PIPELINE_STAGES,
        start=1,
    ):
        elapsed_time = run_stage(
            stage=stage,
            stage_number=stage_number,
            total_stages=total_stages,
            verbose=arguments.verbose,
        )

        stage_times.append(
            (
                stage.name,
                elapsed_time,
            )
        )

    total_elapsed_time = (
        perf_counter() - pipeline_start_time
    )

    print_pipeline_summary(
        stage_times=stage_times,
        total_elapsed_time=total_elapsed_time,
    )


if __name__ == "__main__":
    main()