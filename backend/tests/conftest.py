"""Test fixtures and configuration."""

from __future__ import annotations

import pytest

from src.simulation.power_grid import PowerGridSimulation


@pytest.fixture
def grid() -> PowerGridSimulation:
    """Fresh IEEE 30-bus power grid simulation."""
    return PowerGridSimulation()


@pytest.fixture
def grid_with_snapshot(grid: PowerGridSimulation) -> tuple[PowerGridSimulation, int]:
    """Grid with a saved snapshot for rollback tests."""
    idx = grid.save_snapshot()
    return grid, idx
