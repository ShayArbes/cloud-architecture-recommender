"""Project-wide constants — no magic values in call sites (CLAUDE.md §3.3)."""

# --- Scraper: retry policy (CLAUDE.md §3.5) --------------------------------
# Max attempts per network call; delay doubles each retry: 1s, 2s, 4s.
SCRAPER_MAX_RETRIES = 3
SCRAPER_BACKOFF_BASE_SECONDS = 1.0

# HTTP statuses worth retrying — transient by definition. Anything else 4xx/5xx
# fails fast so a misconfigured URL does not burn the retry budget.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

# --- Scraper: AWS Architecture Center discovery -----------------------------
# The Architecture Center listing UI is client-rendered, so its HTML contains
# no article links; discovery uses the public JSON directory API that powers it.
AWS_DIRECTORY_API_URL = "https://aws.amazon.com/api/dirs/items/search"
AWS_DIRECTORY_ID = "alias#architecture-center"
AWS_DIRECTORY_LOCALE = "en_US"
AWS_DIRECTORY_PAGE_SIZE = 100
