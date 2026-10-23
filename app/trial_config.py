
import os

TRIAL_DEFAULT_DAYS = int(
    os.getenv("TRIAL_DEFAULT_DAYS", "7")
)

if TRIAL_DEFAULT_DAYS < 1:
    raise ValueError(
        "TRIAL_DEFAULT_DAYS deve ser maior que zero."
    )
