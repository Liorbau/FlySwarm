"""Browser end-to-end tests for the demo-landing page.

These drive a real Chromium browser (Playwright) against a live uvicorn server
booted by the `live_server` fixture. They verify the three required features:
the interactive demo, the waitlist signup form, and that the page is responsive.

The server writes signups to a temporary FLYSWARM_EMAILS_FILE, so the real
apps/demo-landing/emails.json is never touched.
"""

import json
import re

import pytest
from playwright.sync_api import Page, expect


def test_demo_button_runs_simulation(live_server, page: Page):
    page.goto(live_server["base_url"])

    expect(page.locator("#demo-button")).to_be_visible()
    page.click("#demo-button")

    # The simulated swarm streams five agent log entries and chat messages.
    expect(page.locator("#agent-log .log-entry").first).to_be_visible(timeout=6000)
    expect(page.locator("#agent-log .log-entry")).to_have_count(5, timeout=6000)
    expect(page.locator("#chat-panel .chat-msg").first).to_be_visible(timeout=6000)


def test_waitlist_success_then_duplicate(live_server, page: Page):
    page.goto(live_server["base_url"])

    email = "e2e-playwright@example.com"
    page.fill("#email-input", email)
    page.click("#submit-button")

    status = page.locator("#form-status")
    expect(status).to_have_class(re.compile(r"\bsuccess\b"), timeout=6000)
    expect(status).to_contain_text("waitlist")

    # Submitting the same email again is handled gracefully as a duplicate.
    page.fill("#email-input", email)
    page.click("#submit-button")
    expect(status).to_contain_text("already", timeout=6000)

    # The signup landed in the temp emails file (NOT the real emails.json).
    stored = json.loads(live_server["emails_file"].read_text(encoding="utf-8"))
    assert any(record["email"] == email for record in stored)
    assert sum(1 for record in stored if record["email"] == email) == 1


def test_invalid_email_shows_error(live_server, page: Page):
    page.goto(live_server["base_url"])

    page.fill("#email-input", "not-an-email")
    page.click("#submit-button")

    status = page.locator("#form-status")
    expect(status).to_have_class(re.compile(r"\berror\b"), timeout=6000)


def test_mobile_viewport_renders_responsively(live_server, page: Page):
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(live_server["base_url"])

    expect(page.locator("h1.hero-title")).to_be_visible()
    expect(page.locator("#demo-button")).to_be_visible()
    expect(page.locator("#waitlist-form")).to_be_visible()

    # On a narrow viewport the demo grid collapses to a single column.
    columns = page.eval_on_selector(
        ".demo-grid",
        "el => getComputedStyle(el).gridTemplateColumns",
    )
    assert len(columns.split()) == 1
