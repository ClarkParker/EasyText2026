import json

from easytext_build import catalog, values


def test_catalog_renders_version_and_all_entries():
    text = catalog.render()
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    assert lines[0] == "VERSION 1"
    assert len(lines) == 1 + len(catalog.ALL)
    for cat in catalog.ALL:
        assert f"{cat.uuid}:{cat.path}:{cat.simple_name}" in lines


def test_catalog_uuids_are_unique():
    assert len({c.uuid for c in catalog.ALL}) == len(catalog.ALL)


def test_convert_rounds_and_normalizes_zero():
    assert values.convert(0.1234567) == 0.12346
    assert values.convert(-0.0) == 0.0
    assert values.convert([1.0, 2.5, True, "x"]) == [1.0, 2.5, True, "x"]
    json.dumps(values.convert((0.1, (1, 2))))
