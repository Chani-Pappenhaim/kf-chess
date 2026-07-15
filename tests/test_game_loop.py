from view.render_model import RenderModel

from ui.game_loop import GameLoop


class _FakeEngine:
    def __init__(self, model):
        self._model = model
        self.waited = []

    def wait(self, dt):
        self.waited.append(dt)

    def render_model(self):
        return self._model


class _FakeRenderer:
    def __init__(self):
        self.calls = []

    def render(self, model, base, clock_ms=0, selected=None, targets=()):
        self.calls.append((model, base, clock_ms, selected, targets))
        return "canvas"


class _FakeHud:
    def __init__(self):
        self.drawn = []

    def draw(self, canvas, model):
        self.drawn.append((canvas, model))


class _FakeWindow:
    def __init__(self, events):
        self._events = events
        self.shown = []
        self.closed = False

    def show(self, canvas):
        self.shown.append(canvas)

    def poll_events(self):
        return self._events

    def close(self):
        self.closed = True


class _FakeController:
    selected = (1, 2)
    legal_targets = ((3, 4), (5, 6))


class _FakeTranslator:
    def __init__(self):
        self.handled = []

    def handle(self, event):
        self.handled.append(event)


def _model():
    return RenderModel(pieces=(), width=8, height=8, clock=1234)


def _loop(events):
    engine = _FakeEngine(_model())
    renderer = _FakeRenderer()
    hud = _FakeHud()
    window = _FakeWindow(events)
    translator = _FakeTranslator()
    controller = _FakeController()
    loop = GameLoop(window, engine, controller, renderer, hud, translator, "base")
    return loop, engine, renderer, hud, window, translator


def test_tick_advances_renders_and_shows():
    loop, engine, renderer, hud, window, translator = _loop(events=[])
    keep_going = loop.tick(16)

    assert keep_going is True
    assert engine.waited == [16]                    # engine advanced by dt
    model, base, clock_ms, selected, targets = renderer.calls[0]
    assert base == "base"
    assert clock_ms == 1234                          # uses model.clock
    assert selected == (1, 2)                        # controller selection
    assert targets == ((3, 4), (5, 6))               # controller move hints
    assert hud.drawn == [("canvas", model)]          # hud drew the rendered canvas
    assert window.shown == ["canvas"]                # canvas presented


def test_tick_dispatches_non_quit_events_to_translator():
    loop, engine, renderer, hud, window, translator = _loop(
        events=[("left", 10, 20), ("right", 30, 40)]
    )
    keep_going = loop.tick(5)

    assert keep_going is True
    assert translator.handled == [("left", 10, 20), ("right", 30, 40)]


def test_tick_returns_false_on_quit_event():
    loop, engine, renderer, hud, window, translator = _loop(
        events=[("left", 1, 1), ("quit",)]
    )
    keep_going = loop.tick(8)

    assert keep_going is False                        # loop should stop
    assert ("left", 1, 1) in translator.handled       # non-quit still dispatched
    assert ("quit",) not in translator.handled        # quit not sent to translator
