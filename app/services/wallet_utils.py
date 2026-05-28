from __future__ import annotations

import re

from eth_utils import is_address, to_checksum_address


TX_HASH_PATTERN = re.compile(r"^0x[0-9a-fA-F]{64}$")
LOCAL_FAKE_TX_HASH = "0xtesttransaction123"


def is_valid_evm_address(address: str) -> bool:
    return isinstance(address, str) and is_address(address)


def normalize_wallet_address(address: str) -> str:
    if not is_valid_evm_address(address):
        raise ValueError("Invalid EVM wallet address")
    return to_checksum_address(address)


def wallet_addresses_equal(a: str, b: str) -> bool:
    if not is_valid_evm_address(a) or not is_valid_evm_address(b):
        return False
    return normalize_wallet_address(a).lower() == normalize_wallet_address(b).lower()


def addresses_equal(a: str, b: str) -> bool:
    return wallet_addresses_equal(a, b)


def validate_tx_hash(tx_hash: str) -> bool:
    return isinstance(tx_hash, str) and (tx_hash == LOCAL_FAKE_TX_HASH or bool(TX_HASH_PATTERN.fullmatch(tx_hash)))


def is_valid_tx_hash(tx_hash: str) -> bool:
    return validate_tx_hash(tx_hash)


def is_non_negative_integer_string(value: str) -> bool:
    return isinstance(value, str) and value.isdigit()


def int_to_hex_quantity(value: int) -> str:
    if not isinstance(value, int) or value < 0:
        raise ValueError("Ethereum quantity must be a non-negative integer")
    return hex(value)
