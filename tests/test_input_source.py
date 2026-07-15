from ui.input_source import InputTranslator


class _RecordingController:
    def __init__(self):
        self.calls = []

    def click(self, x, y):
        self.calls.append(("click", x, y))

    def jump(self, x, y):
        self.calls.append(("jump", x, y))


def test_left_click_becomes_a_controller_click():
    controller = _RecordingController()
    InputTranslator(controller).handle(("left", 30, 40))
    assert controller.calls == [("click", 30, 40)]


def test_double_click_becomes_a_controller_jump():
    controller = _RecordingController()
    InputTranslator(controller).handle(("double", 10, 20))
    assert controller.calls == [("jump", 10, 20)]


def test_quit_event_is_ignored():
    controller = _RecordingController()
    InputTranslator(controller).handle(("quit",))
    assert controller.calls == []
