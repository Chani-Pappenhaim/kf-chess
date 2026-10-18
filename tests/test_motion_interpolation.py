from events.bus import EventBus
from game.events import JumpStarted, MoveStepStarted
from ui.motion_interpolation import MotionInterpolator


class FakeClock:
    def __init__(self, start=0.0):
        self.now = start

    def __call__(self):
        return self.now


def test_a_cell_with_no_motion_falls_back_to_the_default():
    interpolator = MotionInterpolator(EventBus())
    assert interpolator.progress((0, 0), 0.42) == 0.42


def test_progress_rises_linearly_over_the_steps_duration():
    clock = FakeClock()
    bus = EventBus()
    interpolator = MotionInterpolator(bus, clock=clock)
    bus.publish(MoveStepStarted("wP", (0, 0), (0, 1), start_ms=0, duration_ms=1000))

    assert interpolator.progress((0, 0), 0.0) == 0.0
    clock.now = 0.25  # 250ms of 1000ms elapsed, clock() is in seconds
    assert interpolator.progress((0, 0), 0.0) == 0.25
    clock.now = 1.0
    assert interpolator.progress((0, 0), 0.0) == 1.0


def test_progress_never_exceeds_one_past_the_duration():
    clock = FakeClock()
    bus = EventBus()
    interpolator = MotionInterpolator(bus, clock=clock)
    bus.publish(MoveStepStarted("wP", (0, 0), (0, 1), start_ms=0, duration_ms=500))
    clock.now = 10.0  # long past the step's duration
    assert interpolator.progress((0, 0), 0.0) == 1.0


def test_a_zero_duration_step_is_immediately_complete():
    bus = EventBus()
    interpolator = MotionInterpolator(bus)
    bus.publish(MoveStepStarted("wP", (0, 0), (0, 1), start_ms=0, duration_ms=0))
    assert interpolator.progress((0, 0), 0.0) == 1.0


def test_a_jump_started_event_is_tracked_by_its_own_cell():
    clock = FakeClock()
    bus = EventBus()
    interpolator = MotionInterpolator(bus, clock=clock)
    bus.publish(JumpStarted("wN", (2, 2), at_ms=0, duration_ms=400))
    clock.now = 0.2
    assert interpolator.progress((2, 2), 0.0) == 0.5


def test_a_new_motion_on_the_same_cell_replaces_the_old_one():
    # The piece that was on this cell moved on, and a different piece (or the
    # same one starting a new step) now occupies it - the old timer must not
    # linger and produce a stale progress.
    clock = FakeClock()
    bus = EventBus()
    interpolator = MotionInterpolator(bus, clock=clock)
    bus.publish(MoveStepStarted("wP", (0, 0), (0, 1), start_ms=0, duration_ms=1000))
    clock.now = 0.9  # nearly done with the first step
    bus.publish(MoveStepStarted("wR", (0, 0), (0, 1), start_ms=900, duration_ms=1000))
    assert interpolator.progress((0, 0), 0.0) == 0.0  # restarted, not 0.9


def test_a_different_cell_is_unaffected_by_another_cells_motion():
    bus = EventBus()
    interpolator = MotionInterpolator(bus)
    bus.publish(MoveStepStarted("wP", (0, 0), (0, 1), start_ms=0, duration_ms=1000))
    assert interpolator.progress((5, 5), 0.77) == 0.77
