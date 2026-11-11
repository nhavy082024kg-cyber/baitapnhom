from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceSettings:
    """Tunable business parameters (filled from config.py)."""
    heartbeat_online_seconds: int = 60       # <= 60s since last heartbeat -> ONLINE
    heartbeat_unstable_seconds: int = 180    # <= 180s -> UNSTABLE, else OFFLINE
    order_ttl_minutes: int = 10              # unpaid order expires after 10 minutes
    command_ttl_seconds: int = 120           # device must execute within 2 minutes
    token_ttl_minutes: int = 120
    step_up_minutes: int = 10
    max_failed_logins: int = 5
