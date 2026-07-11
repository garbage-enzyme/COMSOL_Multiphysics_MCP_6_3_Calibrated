"""Thread-state tests for the asynchronous solver using fake studies."""

import threading

from src.async_handler.solver import AsyncSolver, SolverStatus


class FakeStudy:
    def __init__(self, error=None):
        self.error = error
        self.run_count = 0

    def run(self):
        self.run_count += 1
        if self.error:
            raise self.error


class FakeStudyList:
    def __init__(self, studies):
        self.studies = studies

    def tags(self):
        return list(self.studies)


class FakeJava:
    def __init__(self, study):
        self.study_node = study

    def study(self, tag=None):
        if tag is None:
            return FakeStudyList({"std1": self.study_node})
        return self.study_node


class FakeModel:
    def __init__(self, study):
        self.java = FakeJava(study)

    def name(self):
        return "fake"


def raising_callback(progress, message):
    raise RuntimeError("callback failed")


def test_callback_failure_does_not_change_completed_solve():
    study = FakeStudy()
    solver = AsyncSolver()

    assert solver.start_solve(
        FakeModel(study),
        "std1",
        progress_callback=raising_callback,
    )
    assert solver.wait(timeout=2)

    progress = solver.get_progress()
    assert progress["status"] == SolverStatus.COMPLETED.value
    assert progress["progress"] == 1.0
    assert study.run_count == 1


def test_progress_property_returns_snapshot():
    solver = AsyncSolver()

    snapshot = solver.progress
    snapshot.status = SolverStatus.FAILED

    assert solver.progress.status is SolverStatus.IDLE


def test_cancel_during_blocking_run_reports_completed_truthfully():
    started = threading.Event()
    release = threading.Event()

    class BlockingStudy(FakeStudy):
        def run(self):
            self.run_count += 1
            started.set()
            assert release.wait(timeout=2)

    study = BlockingStudy()
    solver = AsyncSolver()

    assert solver.start_solve(FakeModel(study), "std1")
    assert started.wait(timeout=2)
    assert solver.cancel() is True
    assert solver.get_progress()["status"] == SolverStatus.RUNNING.value

    release.set()
    assert solver.wait(timeout=2)

    progress = solver.get_progress()
    assert progress["status"] == SolverStatus.COMPLETED.value
    assert progress["progress"] == 1.0
    assert "could not interrupt" in progress["message"]
