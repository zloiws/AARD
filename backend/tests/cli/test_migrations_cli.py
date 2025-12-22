import importlib


def test_build_parser_and_call_migrate(monkeypatch):
    m = importlib.import_module("backend.cli.migrations")
    parser = m.build_parser()
    # just ensure parser builds and help can be printed
    parser.format_help()
    # call help path
    rc = m.main(["--help"])
    assert rc == 2 or rc == 0


