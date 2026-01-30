"""
Log parser for extracting metrics from worker logs.

Parses worker.log to extract job activity, error counts, and execution times.
"""

import re
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class LogParser:
    """
    Parses worker log files to extract metrics.
    
    Supports filtering by time window and extracting:
    - Job activity (received, completed, failed)
    - Error codes and counts
    - Last completion timestamp
    - Running jobs (started but not completed)
    """
    
    # Log format: 2026-01-30 10:15:23 | INFO | worker | [SBS] Recibido job: SOL-001
    LOG_PATTERN = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\|\s+(\w+)\s+\|\s+\w+\s+\|\s+(.+)'
    )
    
    # Patterns for extracting job events
    JOB_RECEIVED_PATTERN = re.compile(r'\[(\w+)\] Recibido job:\s+(\S+)')
    JOB_COMPLETED_PATTERN = re.compile(r'\[(\w+)\] Job (\S+) completado exitosamente')
    JOB_FAILED_PATTERN = re.compile(r'\[(\w+)\] Job (\S+) completado con errores')
    ERROR_PATTERN = re.compile(r'ERROR.*\[(\w+)\].*Job (\S+).*:?\s+(\w+)')
    DLQ_PATTERN = re.compile(r'\[(\w+)\] Job (\S+).*DLQ')
    
    def __init__(self, log_path: str | Path):
        """
        Initialize log parser.
        
        Args:
            log_path: Path to worker.log file
        """
        self.log_path = Path(log_path)
    
    def parse_activity(self, hours: int = 24) -> dict:
        """
        Parse log file for job activity in last N hours.
        
        Args:
            hours: Number of hours to look back (default: 24)
        
        Returns:
            Dictionary with activity metrics:
            {
                "jobs_received": int,
                "jobs_completed": int,
                "jobs_failed": int,
                "success_rate": float,
                "by_aseguradora": {
                    "sbs": {"received": int, "completed": int, "failed": int},
                    ...
                }
            }
        """
        if not self.log_path.exists():
            logger.warning(f"Log file not found: {self.log_path}")
            return self._empty_activity_metrics()
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        jobs_received = 0
        jobs_completed = 0
        jobs_failed = 0
        by_aseguradora = defaultdict(lambda: {"received": 0, "completed": 0, "failed": 0})
        
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # Parse timestamp
                    match = self.LOG_PATTERN.match(line)
                    if not match:
                        continue
                    
                    timestamp_str, level, message = match.groups()
                    
                    try:
                        log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue
                    
                    # Skip if outside time window
                    if log_time < cutoff_time:
                        continue
                    
                    # Extract job events
                    if "Recibido job:" in message:
                        match_job = self.JOB_RECEIVED_PATTERN.search(message)
                        if match_job:
                            aseguradora = match_job.group(1).lower()
                            jobs_received += 1
                            by_aseguradora[aseguradora]["received"] += 1
                    
                    elif "completado exitosamente" in message:
                        match_job = self.JOB_COMPLETED_PATTERN.search(message)
                        if match_job:
                            aseguradora = match_job.group(1).lower()
                            jobs_completed += 1
                            by_aseguradora[aseguradora]["completed"] += 1
                    
                    elif "completado con errores" in message:
                        match_job = self.JOB_FAILED_PATTERN.search(message)
                        if match_job:
                            aseguradora = match_job.group(1).lower()
                            jobs_failed += 1
                            by_aseguradora[aseguradora]["failed"] += 1
        
        except Exception as e:
            logger.error(f"Error parsing log file: {e}")
            return self._empty_activity_metrics()
        
        # Calculate success rate
        total_jobs = jobs_completed + jobs_failed
        success_rate = (jobs_completed / total_jobs * 100) if total_jobs > 0 else 0.0
        
        return {
            "jobs_received": jobs_received,
            "jobs_completed": jobs_completed,
            "jobs_failed": jobs_failed,
            "success_rate": round(success_rate, 2),
            "by_aseguradora": dict(by_aseguradora)
        }
    
    def parse_errors(self, hours: int = 24) -> dict:
        """
        Parse log file for error codes in last N hours.
        
        Args:
            hours: Number of hours to look back (default: 24)
        
        Returns:
            Dictionary mapping error codes to counts:
            {"CAPTCHA_001": 5, "AUTH_001": 2, ...}
        """
        if not self.log_path.exists():
            logger.warning(f"Log file not found: {self.log_path}")
            return {}
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        error_counts = defaultdict(int)
        
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # Parse timestamp
                    match = self.LOG_PATTERN.match(line)
                    if not match:
                        continue
                    
                    timestamp_str, level, message = match.groups()
                    
                    # Only process ERROR level logs
                    if level != "ERROR":
                        continue
                    
                    try:
                        log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue
                    
                    # Skip if outside time window
                    if log_time < cutoff_time:
                        continue
                    
                    # Extract error code
                    # Look for patterns like "CAPTCHA_001", "AUTH_001", etc.
                    error_code_match = re.search(r'\b([A-Z_]+_\d{3})\b', message)
                    if error_code_match:
                        error_code = error_code_match.group(1)
                        error_counts[error_code] += 1
        
        except Exception as e:
            logger.error(f"Error parsing log file for errors: {e}")
            return {}
        
        return dict(error_counts)
    
    def get_last_completion_time(self) -> Optional[datetime]:
        """
        Get timestamp of most recent job completion.
        
        Returns:
            datetime of last completion, or None if no completions found
        """
        if not self.log_path.exists():
            return None
        
        last_completion = None
        
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if "completado exitosamente" in line:
                        match = self.LOG_PATTERN.match(line)
                        if match:
                            timestamp_str = match.group(1)
                            try:
                                last_completion = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                continue
        
        except Exception as e:
            logger.error(f"Error getting last completion time: {e}")
            return None
        
        return last_completion
    
    def get_running_jobs(self) -> list[dict]:
        """
        Get jobs that started but haven't completed.
        
        Returns:
            List of running jobs:
            [
                {
                    "job_id": str,
                    "aseguradora": str,
                    "started_at": datetime,
                    "duration_minutes": int
                },
                ...
            ]
        """
        if not self.log_path.exists():
            return []
        
        # Track job starts and completions
        job_starts = {}  # job_id -> (aseguradora, start_time)
        job_completions = set()  # job_ids that completed
        
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    match = self.LOG_PATTERN.match(line)
                    if not match:
                        continue
                    
                    timestamp_str, level, message = match.groups()
                    
                    try:
                        log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue
                    
                    # Track job starts
                    if "Recibido job:" in message:
                        match_job = self.JOB_RECEIVED_PATTERN.search(message)
                        if match_job:
                            aseguradora = match_job.group(1).lower()
                            job_id = match_job.group(2)
                            job_starts[job_id] = (aseguradora, log_time)
                    
                    # Track job completions
                    elif "completado exitosamente" in message or "completado con errores" in message:
                        match_job = self.JOB_COMPLETED_PATTERN.search(message)
                        if not match_job:
                            match_job = self.JOB_FAILED_PATTERN.search(message)
                        if match_job:
                            job_id = match_job.group(2)
                            job_completions.add(job_id)
                    
                    # Track DLQ sends (also considered "completed")
                    elif "DLQ" in message:
                        match_job = self.DLQ_PATTERN.search(message)
                        if match_job:
                            job_id = match_job.group(2)
                            job_completions.add(job_id)
        
        except Exception as e:
            logger.error(f"Error getting running jobs: {e}")
            return []
        
        # Find jobs that started but didn't complete
        running_jobs = []
        now = datetime.now()
        
        for job_id, (aseguradora, start_time) in job_starts.items():
            if job_id not in job_completions:
                duration = (now - start_time).total_seconds() / 60  # minutes
                running_jobs.append({
                    "job_id": job_id,
                    "aseguradora": aseguradora,
                    "started_at": start_time.isoformat(),
                    "duration_minutes": int(duration)
                })
        
        return running_jobs
    
    def _empty_activity_metrics(self) -> dict:
        """Return empty activity metrics structure."""
        return {
            "jobs_received": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "success_rate": 0.0,
            "by_aseguradora": {}
        }
