from ai import _coerce_to_dict


def test_dict_passes_through():
    payload = {"is_relevant": True, "translations": [{"language": "en"}]}
    assert _coerce_to_dict(payload) is payload


def test_list_with_single_dict_unwraps():
    inner = {"is_relevant": True}
    assert _coerce_to_dict([inner]) is inner


def test_list_with_multiple_items_rejected():
    assert _coerce_to_dict([{"a": 1}, {"b": 2}]) is None


def test_list_of_non_dict_rejected():
    assert _coerce_to_dict([1, 2, 3]) is None


def test_string_rejected():
    assert _coerce_to_dict("hello") is None


def test_none_rejected():
    assert _coerce_to_dict(None) is None
