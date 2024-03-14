import pytest
from app import valid_price, valid_quantity

def test_valid_price():
    # Test reference within margin
    assert valid_price(175.26, 171.3) == True
    # Test reference out of margin (smaller)
    assert valid_price(100.1, 89.0) == False
    # Test reference out of margin (bigger)
    assert valid_price(100.0, 112.0) == False
    # Test reference on edge
    assert valid_price(50.0, 50.0) == True


def test_valid_quantity():
    # Test zero quantity
    assert valid_quantity(0) == False
    # Test float quantity
    assert valid_quantity(10.1) == False
    # Test negative quantity
    assert valid_quantity(-100.0) == False
    # Test acceptable quantity
    assert valid_quantity(500) == True