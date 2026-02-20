"""
Maritime News Intelligence - Scheduling Configuration

Defines scheduling patterns for daily vs weekly graph analysis modes.
"""

from datetime import datetime, time
from typing import Dict, List, Literal
from pydantic import BaseModel
import structlog

logger = structlog.get_logger(__name__)

AnalysisMode = Literal["daily", "weekly", "full"]


class ScheduleConfig(BaseModel):
    """Configuration for scheduled news analysis runs."""

    # Daily run configuration
    daily_schedule: Dict = {
        "enabled": True,
        "run_time": "06:00",  # 6 AM UTC
        "analysis_mode": "daily",
        "temporal_window_days": 7,
        "max_execution_time_minutes": 15,
        "retry_attempts": 3,
        "features": {
            "quick_deduplication": True,
            "basic_clustering": True,
            "timeline_reconstruction": False,
            "deep_graph_analysis": False
        }
    }

    # Weekly run configuration
    weekly_schedule: Dict = {
        "enabled": True,
        "run_day": "monday",  # Monday 2 AM UTC
        "run_time": "02:00",
        "analysis_mode": "weekly",
        "temporal_window_days": 30,
        "max_execution_time_minutes": 60,
        "retry_attempts": 2,
        "features": {
            "comprehensive_deduplication": True,
            "full_clustering_analysis": True,
            "timeline_reconstruction": True,
            "trend_analysis": True,
            "graph_optimization": True,
            "network_metrics": True
        }
    }

    # Special full analysis runs (monthly/on-demand)
    full_schedule: Dict = {
        "enabled": False,  # Only run on-demand
        "analysis_mode": "full",
        "temporal_window_days": 90,
        "max_execution_time_minutes": 120,
        "retry_attempts": 1,
        "features": {
            "maximum_depth_analysis": True,
            "predictive_modeling": True,
            "network_evolution_tracking": True,
            "comprehensive_graph_cleanup": True,
            "health_reporting": True
        }
    }


def get_current_analysis_mode() -> AnalysisMode:
    """
    Determine the appropriate analysis mode based on current time and schedule.

    Returns:
        Analysis mode for current execution
    """
    now = datetime.now()

    # Check if it's Monday (weekly run day)
    if now.weekday() == 0:  # Monday = 0
        schedule_time = time(2, 0)  # 2 AM
        current_time = now.time()

        # Check if current time is within weekly run window (2-3 AM Monday)
        if schedule_time <= current_time <= time(3, 0):
            logger.info("Weekly analysis mode selected", day="Monday", time=str(current_time))
            return "weekly"

    # Default to daily mode
    logger.info("Daily analysis mode selected", day=now.strftime("%A"), time=str(now.time()))
    return "daily"


def should_run_analysis(analysis_mode: AnalysisMode) -> bool:
    """
    Check if analysis should run based on schedule and current time.

    Args:
        analysis_mode: Mode to check schedule for

    Returns:
        True if analysis should run now
    """
    schedule_config = ScheduleConfig()
    now = datetime.now()

    if analysis_mode == "daily":
        if not schedule_config.daily_schedule["enabled"]:
            return False

        target_time = time(*map(int, schedule_config.daily_schedule["run_time"].split(":")))
        current_time = now.time()

        # Allow 1-hour window around scheduled time
        return abs((datetime.combine(now.date(), current_time) -
                   datetime.combine(now.date(), target_time)).seconds) <= 3600

    elif analysis_mode == "weekly":
        if not schedule_config.weekly_schedule["enabled"]:
            return False

        # Check day and time
        target_day = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(
            schedule_config.weekly_schedule["run_day"].lower()
        )
        target_time = time(*map(int, schedule_config.weekly_schedule["run_time"].split(":")))

        return (now.weekday() == target_day and
                abs((datetime.combine(now.date(), now.time()) -
                    datetime.combine(now.date(), target_time)).seconds) <= 3600)

    return False  # Full mode only runs on-demand


def get_analysis_config(analysis_mode: AnalysisMode) -> Dict:
    """
    Get configuration for specific analysis mode.

    Args:
        analysis_mode: Mode to get config for

    Returns:
        Configuration dictionary for the mode
    """
    schedule_config = ScheduleConfig()

    config_map = {
        "daily": schedule_config.daily_schedule,
        "weekly": schedule_config.weekly_schedule,
        "full": schedule_config.full_schedule
    }

    return config_map.get(analysis_mode, schedule_config.daily_schedule)


def generate_cron_expressions() -> Dict[str, str]:
    """
    Generate cron expressions for scheduling.

    Returns:
        Dictionary of cron expressions for different analysis modes
    """
    schedule_config = ScheduleConfig()

    # Daily cron (6 AM UTC every day)
    daily_time = schedule_config.daily_schedule["run_time"]
    daily_hour, daily_minute = daily_time.split(":")
    daily_cron = f"{daily_minute} {daily_hour} * * *"

    # Weekly cron (Monday 2 AM UTC)
    weekly_time = schedule_config.weekly_schedule["run_time"]
    weekly_hour, weekly_minute = weekly_time.split(":")
    weekly_day = 1  # Monday = 1 in cron
    weekly_cron = f"{weekly_minute} {weekly_hour} * * {weekly_day}"

    return {
        "daily": daily_cron,
        "weekly": weekly_cron,
        "daily_description": f"Daily at {daily_time} UTC",
        "weekly_description": f"Weekly on Monday at {weekly_time} UTC"
    }


def get_execution_timeout(analysis_mode: AnalysisMode) -> int:
    """
    Get execution timeout for analysis mode in minutes.

    Args:
        analysis_mode: Analysis mode

    Returns:
        Timeout in minutes
    """
    timeouts = {
        "daily": 15,    # 15 minutes for daily runs
        "weekly": 60,   # 60 minutes for weekly runs
        "full": 120     # 120 minutes for full analysis
    }

    return timeouts.get(analysis_mode, 15)


def validate_schedule_configuration() -> List[str]:
    """
    Validate scheduling configuration and return any issues.

    Returns:
        List of validation issues (empty if valid)
    """
    issues = []
    schedule_config = ScheduleConfig()

    # Check daily schedule
    daily = schedule_config.daily_schedule
    if daily["enabled"]:
        try:
            time_parts = daily["run_time"].split(":")
            if len(time_parts) != 2 or not all(part.isdigit() for part in time_parts):
                issues.append("Invalid daily run_time format. Use HH:MM")

            hour, minute = int(time_parts[0]), int(time_parts[1])
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                issues.append("Daily run_time hours/minutes out of valid range")

        except Exception as e:
            issues.append(f"Daily schedule validation error: {e}")

    # Check weekly schedule
    weekly = schedule_config.weekly_schedule
    if weekly["enabled"]:
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if weekly["run_day"].lower() not in valid_days:
            issues.append(f"Invalid weekly run_day. Must be one of: {valid_days}")

        try:
            time_parts = weekly["run_time"].split(":")
            if len(time_parts) != 2 or not all(part.isdigit() for part in time_parts):
                issues.append("Invalid weekly run_time format. Use HH:MM")

        except Exception as e:
            issues.append(f"Weekly schedule validation error: {e}")

    # Check temporal windows make sense
    if (daily["enabled"] and weekly["enabled"] and
        daily["temporal_window_days"] >= weekly["temporal_window_days"]):
        issues.append("Weekly temporal window should be larger than daily window")

    return issues


# Example usage and validation
if __name__ == "__main__":
    # Validate configuration
    issues = validate_schedule_configuration()
    if issues:
        print("Schedule configuration issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Schedule configuration is valid")

    # Show cron expressions
    crons = generate_cron_expressions()
    print(f"\nCron expressions:")
    print(f"  Daily: {crons['daily']} ({crons['daily_description']})")
    print(f"  Weekly: {crons['weekly']} ({crons['weekly_description']})")

    # Show current mode
    current_mode = get_current_analysis_mode()
    print(f"\nCurrent analysis mode: {current_mode}")
    print(f"Should run now: {should_run_analysis(current_mode)}")