# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Aproxy controller."""

from pydantic import BaseModel, Field, validator

class ProxyConfig(BaseModel):
