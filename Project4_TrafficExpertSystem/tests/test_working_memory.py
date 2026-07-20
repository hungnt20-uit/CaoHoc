from traffic_es.engine.working_memory import WorkingMemory


def test_set_get_has():
    wm = WorkingMemory({"chiso.tocDo": 90})
    assert wm.has("chiso.tocDo")
    assert wm.get("chiso.tocDo") == 90
    assert not wm.has("chiso.tocDoGioiHan")


def test_set_records_source():
    wm = WorkingMemory()
    wm.set("chiso.vuot_pct", 80.0, source="FUNC:vuot_toc_do_pct")
    assert wm.get("chiso.vuot_pct") == 80.0
    assert wm.source_of("chiso.vuot_pct") == "FUNC:vuot_toc_do_pct"


def test_as_dict_is_copy():
    wm = WorkingMemory({"a": 1})
    d = wm.as_dict()
    d["a"] = 2
    assert wm.get("a") == 1
