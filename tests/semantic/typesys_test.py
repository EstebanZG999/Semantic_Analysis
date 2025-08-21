from program.semantic.typesys import (
    INTEGER, STRING, BOOLEAN, NULL, VOID,
    make_array, make_fn, can_assign,
    arithmetic_type, logical_type, comparison_type
)

def test_assign_equal_types():
    assert can_assign(INTEGER, INTEGER)
    assert can_assign(STRING, STRING)
    assert not can_assign(INTEGER, STRING)

def test_assign_null_to_refs():
    arr = make_array(INTEGER, 2)
    assert can_assign(arr, NULL)
    assert can_assign(STRING, NULL)
    assert not can_assign(INTEGER, NULL)

def test_arithmetic():
    assert arithmetic_type(INTEGER, INTEGER).name == "integer"
    assert arithmetic_type(INTEGER, STRING) is None

def test_logical():
    assert logical_type(BOOLEAN, BOOLEAN).name == "boolean"
    assert logical_type(BOOLEAN, STRING) is None

def test_comparison():
    assert comparison_type(INTEGER, INTEGER).name == "boolean"
    assert comparison_type(STRING, STRING).name == "boolean"
    # orden solo numérico
    assert comparison_type(INTEGER, STRING) is None
