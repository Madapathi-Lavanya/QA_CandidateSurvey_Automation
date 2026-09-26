from playwright.sync_api import Page, Locator, expect


class BasePage:

    DEFAULT_TIMEOUT = 15000  # ms

    # --- highlight controls ------------------------------------------- #
    HIGHLIGHT = True             # master on/off switch
    HIGHLIGHT_MS = 600           # how long each flash stays on (ms)
    HIGHLIGHT_COLOR = "#22c55e"  # outline colour (green)
    HIGHLIGHT_TINT = "rgba(34,197,94,0.18)"  # background tint (green)

    def __init__(self, page: Page):
        self.page = page

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #
    def navigate(self, url: str):
        self.page.goto(url, wait_until="networkidle")

    # ------------------------------------------------------------------ #
    # Locator helpers (all inputs are XPath strings)
    # ------------------------------------------------------------------ #
    def find(self, xpath: str) -> Locator:
        return self.page.locator(f"xpath={xpath}")

    def click(self, xpath: str):
        loc = self.find(xpath).first
        loc.wait_for(state="visible", timeout=self.DEFAULT_TIMEOUT)
        self._flash(loc)
        loc.click()

    def fill(self, xpath: str, value: str):
        loc = self.find(xpath).first
        loc.wait_for(state="visible", timeout=self.DEFAULT_TIMEOUT)
        self._flash(loc)
        loc.fill(value)

    def text_of(self, xpath: str) -> str:
        loc = self.find(xpath).first
        loc.wait_for(state="visible", timeout=self.DEFAULT_TIMEOUT)
        self._flash(loc)
        return loc.inner_text().strip()

    def is_visible(self, xpath: str) -> bool:
        return self.find(xpath).first.is_visible()

    def count(self, xpath: str) -> int:
        return self.find(xpath).count()

    def has_class(self, xpath: str, class_name: str) -> bool:
        cls = self.find(xpath).first.get_attribute("class") or ""
        return class_name in cls.split()

    def wait_for_visible(self, xpath: str, timeout: int = None):
        self.find(xpath).first.wait_for(
            state="visible", timeout=timeout or self.DEFAULT_TIMEOUT
        )

    # ------------------------------------------------------------------ #
    # Visual highlight
    # ------------------------------------------------------------------ #
    def _flash(self, locator: Locator):
        """Flash a single element: scroll into view, outline+tint, revert."""
        if not self.HIGHLIGHT:
            return
        try:
            locator.scroll_into_view_if_needed(timeout=self.DEFAULT_TIMEOUT)
            locator.evaluate(
                """(el, style) => {
                    el.__prevOutline = el.style.outline;
                    el.__prevBox = el.style.boxShadow;
                    el.__prevBg = el.style.backgroundColor;
                    el.style.outline = '3px solid ' + style.color;
                    el.style.boxShadow = '0 0 8px ' + style.color;
                    el.style.backgroundColor = style.tint;
                }""",
                {"color": self.HIGHLIGHT_COLOR, "tint": self.HIGHLIGHT_TINT},
            )
            self.page.wait_for_timeout(self.HIGHLIGHT_MS)
            locator.evaluate(
                """(el) => {
                    el.style.outline = el.__prevOutline || '';
                    el.style.boxShadow = el.__prevBox || '';
                    el.style.backgroundColor = el.__prevBg || '';
                }"""
            )
        except Exception:
            # Highlighting is cosmetic - never fail a test because of it.
            pass

    def highlight(self, xpath: str):
        """Public: flash the first element matching an XPath."""
        self._flash(self.find(xpath).first)

    def highlight_each(self, xpath: str):
        """Flash every element matching an XPath, one after another.

        Handy for walking through all questions / all error messages so
        each one lights up in turn during a headed run.
        """
        loc = self.find(xpath)
        for i in range(loc.count()):
            self._flash(loc.nth(i))