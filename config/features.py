"""Runtime feature switches.

Voucher data remains mapped for historical reads, but the business flow is
disabled by default. Set ENABLE_VOUCHERS=true only after the complete voucher
workflow has been approved for reactivation.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _enabled(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


VOUCHERS_ENABLED = _enabled("ENABLE_VOUCHERS", default=False)
D1_BACKUP_ENABLED = _enabled("ENABLE_D1_BACKUP", default=False)
