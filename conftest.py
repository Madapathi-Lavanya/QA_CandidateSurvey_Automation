import os
from datetime import datetime

import pytest
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(__file__)
AUTH_STATE = os.path.join(BASE_DIR, "auth.json")
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


# --------------------------------------------------------------------- #
# Shared session (browser -> context -> page), all session-scoped
# --------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance):
    # Edge channel mirrors how the IAP session is captured via codegen.
    # headless=False + slow_mo makes the highlight flashes easy to follow.
    browser = playwright_instance.chromium.launch(
        headless=False, channel="msedge", slow_mo=150
    )
    yield browser
    browser.close()


@pytest.fixture(scope="session")
def context(browser):
    kwargs = {}
    if os.path.exists(AUTH_STATE):
        kwargs["storage_state"] = AUTH_STATE
    else:
        pytest.skip(
            "auth.json not found. Capture the IAP session first:\n"
            "  playwright codegen --channel msedge "
            "--save-storage=auth.json https://candidate-survey-dev.ttec.com/"
        )
    context = browser.new_context(**kwargs)
    yield context
    context.close()


@pytest.fixture(scope="session")
def page(context):
    """Single page reused by every test in the run."""
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture()
def fresh_page(browser):
    """A brand-new context + page per test (function scope).

    Used by tests that submit the survey: a fresh context clears cookies
    and localStorage so each submission is treated as a new session and
    the dev backend doesn't reject the 2nd/3rd submit in one run.
    """
    kwargs = {}
    if os.path.exists(AUTH_STATE):
        kwargs["storage_state"] = AUTH_STATE
    ctx = browser.new_context(**kwargs)
    pg = ctx.new_page()
    yield pg
    pg.close()
    ctx.close()


# --------------------------------------------------------------------- #
# Screenshot on failure (carried over from Empower_WebAutomation)
# --------------------------------------------------------------------- #
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        page = item.funcargs.get("page")
        if page:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe = "".join(
                c if c.isalnum() or c in "-_" else "_" for c in item.name
            )[:50]
            path = os.path.join(SCREENSHOTS_DIR, f"{safe}_{timestamp}.png")
            try:
                page.screenshot(path=path)
                print(f"Screenshot saved to {path}")
            except Exception as e:  # pragma: no cover
                print(f"Could not capture screenshot: {e}")