from client.inbox import Inbox
from config import settings
from client.waiting import wait_for_state, waiting_canvas
from view.render_model import RenderModel


class _FakeWindow:
    """A window that reports the events it was given, one poll at a time."""

    def __init__(self, events=()):
        self.shown = 0
        self._events = list(events)

    def show(self, canvas):
        self.shown += 1

    def poll_events(self):
        return [self._events.pop(0)] if self._events else []


def test_the_waiting_screen_fills_the_window():
    canvas = waiting_canvas(settings, "connecting...")
    height, width = canvas.img.shape[:2]
    assert (width, height) == (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)


def test_a_state_already_in_hand_is_returned_without_drawing():
    inbox = Inbox()
    model = RenderModel(pieces=(), width=8, height=8)
    inbox.receive_state(model)
    window = _FakeWindow()

    assert wait_for_state(window, inbox, settings) is model
    assert window.shown == 0


def test_the_screen_is_held_until_a_state_arrives():
    class _ArrivingInbox(Inbox):
        """Receives its state on the third look, as a real one would."""

        def __init__(self):
            super().__init__()
            self.looks = 0

        def model(self):
            self.looks += 1
            if self.looks == 3:
                self.receive_state(RenderModel(pieces=(), width=8, height=8))
            return super().model()

    inbox, window = _ArrivingInbox(), _FakeWindow()
    assert wait_for_state(window, inbox, settings) is not None
    assert window.shown == 2  # drawn on each of the two empty looks


def test_closing_the_window_while_waiting_gives_up():
    # The one thing that can happen on this screen and has to be answered for.
    window = _FakeWindow(events=[("quit",)])
    assert wait_for_state(window, Inbox(), settings) is None
