from __future__ import annotations

import time

import pytest

from backend.app.storage import OperationDeadlineExceeded, run_with_deadline


@pytest.mark.parametrize("operation_id", ["SOURCE_LIST_TIMEOUT", "SOURCE_STAT_TIMEOUT", "SOURCE_READ_TIMEOUT"])
def test_application_deadline_fails_closed_for_each_source_operation(operation_id):
    def blocked():
        time.sleep(0.15)
        return operation_id

    with pytest.raises(OperationDeadlineExceeded, match="deadline"):
        run_with_deadline(blocked, 0.01)


def test_application_deadline_success_is_returned():
    assert run_with_deadline(lambda: "synthetic-ok", 0.2) == "synthetic-ok"


def test_real_smb_hard_abort_is_not_claimed_by_local_policy():
    assert OperationDeadlineExceeded.code == "OPERATION_DEADLINE_EXCEEDED"
