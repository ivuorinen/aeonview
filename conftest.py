# conftest.py
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def no_network_requests(monkeypatch):
    monkeypatch.setattr('subprocess.run', mock.Mock())
