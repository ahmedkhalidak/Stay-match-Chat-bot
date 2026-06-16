import os


DEBUG_LOGS_ENABLED = os.getenv("DEBUG_LOGS", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def debug_log(title, value):
    if not DEBUG_LOGS_ENABLED:
        return
    print("\n" + "=" * 40)
    print(title)
    print(value)
    print("=" * 40)
