from . import reddit_json  # noqa: F401

try:
    ADAPTERS  # type: ignore[name-defined]
except NameError:
    ADAPTERS = {}

ADAPTERS.update(
    {
        "reddit_json": reddit_json,
    }
)
