import logging
from typing import Callable, Dict, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from content_queue.manager import get_next, update_status

logger = logging.getLogger(__name__)


class QueueScheduler:
    def __init__(self, pipeline_callback: Callable[[str, str], None]):
        """
        Initialize the queue scheduler.

        Args:
            pipeline_callback: A function that takes (channel: str, topic: str) and executes the pipeline.
                               It should raise an exception on failure.
        """
        self.pipeline_callback = pipeline_callback
        self.scheduler = BackgroundScheduler()
        # Store job IDs for each channel to manage them
        self.jobs: Dict[str, str] = {}  # channel -> job_id
        # Store interval hours for each channel
        self.intervals: Dict[str, int] = {}  # channel -> hours

    def _job_function(self, channel: str):
        """
        The job function that runs at the scheduled interval for a channel.
        """
        logger.info(f"Checking queue for channel: {channel}")
        try:
            # Get the next queued item for this channel
            item = get_next(channel)
            if item is None:
                logger.info(f"No queued items for channel {channel}")
                return

            logger.info(f"Processing item {item.id} for channel {channel}: {item.topic}")
            # Update status to in_progress
            if not update_status(item.id, "in_progress"):
                logger.error(f"Failed to update status to in_progress for item {item.id}")
                return

            # Execute the pipeline callback
            try:
                self.pipeline_callback(channel, item.topic)
                # If successful, mark as completed
                update_status(item.id, "completed")
                logger.info(f"Completed item {item.id} for channel {channel}")
            except Exception as e:
                # If failed, mark as failed and capture error
                error_msg = str(e)
                update_status(item.id, "failed", error=error_msg)
                logger.error(f"Failed item {item.id} for channel {channel}: {error_msg}")
        except Exception as e:
            logger.error(f"Unexpected error in job for channel {channel}: {e}")

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Queue scheduler started")
        else:
            logger.warning("Queue scheduler is already running")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Queue scheduler stopped")
        else:
            logger.warning("Queue scheduler is not running")

    def set_interval(self, channel: str, hours: int):
        """
        Set the interval for a channel.

        Args:
            channel: The channel name
            hours: The interval in hours
        """
        self.intervals[channel] = hours
        if channel in self.jobs:
            # Remove existing job
            self.scheduler.remove_job(self.jobs[channel])
            del self.jobs[channel]

        # Add new job
        job_id = f"queue_job_{channel}"
        trigger = IntervalTrigger(hours=hours)
        self.scheduler.add_job(
            func=self._job_function,
            trigger=trigger,
            args=[channel],
            id=job_id,
            name=f"Queue processor for {channel}",
            replace_existing=True,
        )
        self.jobs[channel] = job_id
        logger.info(f"Set interval for channel {channel} to {hours} hours")

    def trigger_now(self, channel: str):
        """
        Trigger an immediate pipeline run for a channel.

        Args:
            channel: The channel name
        """
        logger.info(f"Triggering immediate run for channel {channel}")
        self._job_function(channel)