from __future__ import annotations

from dataclasses import dataclass
import os


def _csv(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("APP_ENV", "development")
    mantle_rpc_url: str = os.getenv("MANTLE_RPC_URL", "https://rpc.mantle.xyz")
    mantle_chain_id: int = int(os.getenv("MANTLE_CHAIN_ID", "5000"))
    mantle_explorer_url: str = os.getenv("MANTLE_EXPLORER_URL", "https://explorer.mantle.xyz")
    etherscan_api_url: str = os.getenv("ETHERSCAN_API_URL", "https://api.etherscan.io/v2/api")
    etherscan_api_key: str = os.getenv("ETHERSCAN_API_KEY", "")
    cors_origins: list[str] = None  # type: ignore[assignment]
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cors_origins",
            _csv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"),
        )


settings = Settings()
