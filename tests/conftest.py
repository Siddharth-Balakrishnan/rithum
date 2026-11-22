"""Readable section separators for pytest output."""


def pytest_runtest_logstart(nodeid, location):
    terminal = getattr(pytest_runtest_logstart, "_terminal", None)
    if terminal is None:
        return
    path = nodeid.split("::", 1)[0]
    section = path.replace("/", " ").replace("_", " ").upper()
    previous = getattr(pytest_runtest_logstart, "_last_section", None)
    if section != previous:
        terminal.write_sep("=", section)
        pytest_runtest_logstart._last_section = section


def pytest_configure(config):
    pytest_runtest_logstart._terminal = config.pluginmanager.get_plugin("terminalreporter")
