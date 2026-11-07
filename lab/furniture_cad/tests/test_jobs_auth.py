"""WORKER_JOBS_TOKEN auth on the job HTTP API."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

from furniture_cad.jobs import server as jobs_server


def test_auth_open_when_no_token(monkeypatch) -> None:
    monkeypatch.delenv("WORKER_JOBS_TOKEN", raising=False)
    monkeypatch.delenv("JOBS_TOKEN", raising=False)
    h = MagicMock()
    h.headers = {}
    assert jobs_server._authorized(h) is True


def test_auth_bearer(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_JOBS_TOKEN", "s3cret")
    h = MagicMock()
    h.headers = {"authorization": "Bearer s3cret"}
    assert jobs_server._authorized(h) is True
    h.headers = {"authorization": "Bearer wrong"}
    assert jobs_server._authorized(h) is False
    h.headers = {"x-jobs-token": "s3cret"}
    assert jobs_server._authorized(h) is True
