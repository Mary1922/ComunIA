import random

from app.core.enums import IncidentOperationalStatus
from scripts.generate_demo_incidents import demo_statuses


def test_demo_generator_uses_closed_as_only_final_status():
    statuses = demo_statuses(random.Random(42))

    assert IncidentOperationalStatus.CLOSED in statuses
    assert IncidentOperationalStatus.RESOLVED not in statuses
    assert len(statuses) == 5
