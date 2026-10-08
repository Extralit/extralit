"""Tests for stopping a previous workflow run before a forced restart."""

from unittest.mock import MagicMock, patch

import pytest
from rq.job import Job, JobStatus

MODULE = "extralit_server.contexts.workflows"


def make_job(job_id, status):
    job = MagicMock(spec=Job)
    job.id = job_id
    job.get_status.return_value = status
    return job


@pytest.fixture
def group():
    with patch(f"{MODULE}.Group.fetch") as fetch:
        fetch.return_value = MagicMock(get_jobs=MagicMock(return_value=[]))
        yield fetch.return_value


class TestStopWorkflowJobs:
    def test_started_jobs_are_stopped_and_queued_jobs_cancelled(self, group):
        from extralit_server.contexts.workflows import stop_workflow_jobs

        started = make_job("started", JobStatus.STARTED)
        queued = make_job("queued", JobStatus.QUEUED)
        deferred = make_job("deferred", JobStatus.DEFERRED)
        group.get_jobs.return_value = [started, queued, deferred]

        with patch(f"{MODULE}.send_stop_job_command") as stop:
            stopped = stop_workflow_jobs("group-1")

        stop.assert_called_once()
        assert stop.call_args.kwargs["job_id"] == "started"
        started.cancel.assert_not_called()
        queued.cancel.assert_called_once()
        deferred.cancel.assert_called_once()
        assert set(stopped) == {"started", "queued", "deferred"}

    def test_finished_jobs_are_left_alone(self, group):
        from extralit_server.contexts.workflows import stop_workflow_jobs

        finished = make_job("finished", JobStatus.FINISHED)
        failed = make_job("failed", JobStatus.FAILED)
        group.get_jobs.return_value = [finished, failed]

        with patch(f"{MODULE}.send_stop_job_command") as stop:
            assert stop_workflow_jobs("group-1") == []

        stop.assert_not_called()
        finished.cancel.assert_not_called()
        failed.cancel.assert_not_called()

    def test_a_failing_job_does_not_abort_the_rest(self, group):
        from extralit_server.contexts.workflows import stop_workflow_jobs

        broken = make_job("broken", JobStatus.QUEUED)
        broken.cancel.side_effect = RuntimeError("gone")
        healthy = make_job("healthy", JobStatus.QUEUED)
        group.get_jobs.return_value = [broken, healthy]

        with patch(f"{MODULE}.send_stop_job_command"):
            assert stop_workflow_jobs("group-1") == ["healthy"]

    def test_missing_group_is_not_an_error(self):
        from extralit_server.contexts.workflows import stop_workflow_jobs

        with patch(f"{MODULE}.Group.fetch", side_effect=RuntimeError("expired")):
            assert stop_workflow_jobs("group-1") == []
