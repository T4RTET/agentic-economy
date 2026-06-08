import pytest

from app.services.wallet_utils import (
    int_to_hex_quantity,
    is_valid_evm_address,
    normalize_wallet_address,
    validate_tx_hash,
    wallet_addresses_equal,
)


VALID_ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"
CHECKSUM_ADDRESS = "0x1234567890AbcdEF1234567890aBcdef12345678"


def test_valid_address_accepted() -> None:
    assert is_valid_evm_address(VALID_ADDRESS) is True


def test_invalid_address_rejected() -> None:
    assert is_valid_evm_address("0x123") is False
    with pytest.raises(ValueError):
        normalize_wallet_address("0x123")


def test_lowercase_normalized_to_checksum() -> None:
    assert normalize_wallet_address(VALID_ADDRESS) == CHECKSUM_ADDRESS


def test_checksum_preserved() -> None:
    assert normalize_wallet_address(CHECKSUM_ADDRESS) == CHECKSUM_ADDRESS


def test_address_comparison_is_case_insensitive() -> None:
    assert wallet_addresses_equal(VALID_ADDRESS, CHECKSUM_ADDRESS) is True


def test_tx_hash_validation_works() -> None:
    assert validate_tx_hash("0x" + "a" * 64) is True
    assert validate_tx_hash("0xabc") is False


def test_int_to_hex_quantity() -> None:
    assert int_to_hex_quantity(5000) == "0x1388"
    assert int_to_hex_quantity(0) == "0x0"
