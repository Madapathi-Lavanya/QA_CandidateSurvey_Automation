import json
import os
from playwright.sync_api import sync_playwright

URL = "https://candidate-survey-dev.ttec.com/"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_STATE = os.path.join(BASE_DIR, "auth.json")
OUT_FILE = os.path.join(BASE_DIR, "dom_snapshot.json")

# JS that walks the DOM and returns a compact, JSON-serialisable snapshot.
EXTRACT_JS = r"""
() => {
    const txt = (el) => (el ? (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ') : '');

    // Nearest descriptive text for a control: an associated <label>, an
    // aria-label, a preceding sibling's text, or the parent field's text.
    const nearLabel = (el) => {
        if (el.id) {
            const l = document.querySelector(`label[for="${el.id}"]`);
            if (l) return txt(l);
        }
        if (el.getAttribute && el.getAttribute('aria-label')) return el.getAttribute('aria-label');
        let sib = el.previousElementSibling;
        while (sib) {
            const t = txt(sib);
            if (t) return t;
            sib = sib.previousElementSibling;
        }
        let p = el.parentElement;
        for (let i = 0; i < 3 && p; i++) {
            const lbl = p.querySelector('label, legend, .cd-question, .cd-label');
            if (lbl && !lbl.contains(el)) { const t = txt(lbl); if (t) return t; }
            p = p.parentElement;
        }
        return '';
    };

    const attrs = (el) => ({
        tag: el.tagName.toLowerCase(),
        id: el.id || null,
        class: el.getAttribute('class') || null,
        name: el.getAttribute('name') || null,
        type: el.getAttribute('type') || null,
        placeholder: el.getAttribute('placeholder') || null,
        role: el.getAttribute('role') || null,
        data: Object.fromEntries(
            [...el.attributes].filter(a => a.name.startsWith('data-'))
                              .map(a => [a.name, a.value])
        ),
    });

    const dropdowns = [...document.querySelectorAll('.p-dropdown, [role="combobox"], select')]
        .map(el => ({
            ...attrs(el),
            label: nearLabel(el),
            display: txt(el.querySelector('.p-dropdown-label')) || null,
        }));

    const inputs = [...document.querySelectorAll('input, textarea')]
        .map(el => ({ ...attrs(el), label: nearLabel(el) }));

    const buttons = [...document.querySelectorAll('button, [role="button"], input[type="submit"]')]
        .map(el => ({ ...attrs(el), text: txt(el) }));

    const headings = [...document.querySelectorAll('h1, h2, h3, h4, legend')]
        .map(el => ({ tag: el.tagName.toLowerCase(), text: txt(el) }))
        .filter(h => h.text);

    const labels = [...document.querySelectorAll('label, legend')]
        .map(el => txt(el)).filter(Boolean);

    // Any element whose class mentions cd- (survey-specific styling hooks).
    const cdElements = [...document.querySelectorAll('[class*="cd-"]')]
        .slice(0, 400)
        .map(el => ({ tag: el.tagName.toLowerCase(), class: el.getAttribute('class'), text: txt(el).slice(0, 80) }));

    return {
        url: location.href,
        title: document.title,
        headings, labels, dropdowns, inputs, buttons,
        cdElements,
    };
}
"""


def main():
    if not os.path.exists(AUTH_STATE):
        raise SystemExit(
            "auth.json not found. Capture the IAP session first:\n"
            "  playwright codegen --channel msedge "
            "--save-storage=auth.json " + URL
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="msedge")
        context = browser.new_context(storage_state=AUTH_STATE)
        page = context.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(2500)  # let React finish rendering

        snapshot = page.evaluate(EXTRACT_JS)

        # Second pass: open the first dropdown to capture the overlay panel's
        # option markup (it appends to <body>, so it isn't in the first pass).
        try:
            first_dd = page.locator(".p-dropdown, [role='combobox'], select").first
            if first_dd.count():
                first_dd.click()
                page.wait_for_timeout(600)
                panel = page.evaluate(r"""
                    () => {
                        const panel = document.querySelector('.p-dropdown-panel, .p-dropdown-items-wrapper, [role="listbox"]');
                        if (!panel) return null;
                        const items = [...panel.querySelectorAll('li, [role="option"]')].slice(0, 8)
                            .map(li => ({ class: li.getAttribute('class'), role: li.getAttribute('role'),
                                          text: (li.innerText||'').trim().slice(0,60) }));
                        return { panelClass: panel.getAttribute('class'), sampleItems: items };
                    }
                """)
                snapshot["dropdownPanel"] = panel
                page.keyboard.press("Escape")
        except Exception as e:
            snapshot["dropdownPanel"] = f"could not capture: {e}"

        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

        print(f"\nSaved DOM snapshot -> {OUT_FILE}")
        print(f"  dropdowns: {len(snapshot['dropdowns'])}, "
              f"inputs: {len(snapshot['inputs'])}, "
              f"buttons: {len(snapshot['buttons'])}, "
              f"headings: {len(snapshot['headings'])}")
        print("\nDropdowns found:")
        for d in snapshot["dropdowns"]:
            print(f"  label={d['label']!r:30} class={d['class']!r} display={d['display']!r}")

        browser.close()


if __name__ == "__main__":
    main()