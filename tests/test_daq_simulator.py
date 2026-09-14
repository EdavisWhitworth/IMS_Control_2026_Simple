import numpy as np

from ims_control.daq.simulator import SimulatedDAQBackend


def test_simulator_configure_and_acquire_shape():
    backend = SimulatedDAQBackend(seed=1)
    backend.configure(
        device_name="Dev1",
        ai_channel="ai0",
        co_channel="ctr0",
        sample_rate_hz=4000 / (50 / 1000),
        num_points=4000,
        pulse_width_ms=0.2,
    )
    trace = backend.acquire_one()
    assert trace.shape == (4000,)
    assert np.isfinite(trace).all()


def test_simulator_requires_configure_first():
    backend = SimulatedDAQBackend()
    try:
        backend.acquire_one()
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
