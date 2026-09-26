import os
import random
from datetime import datetime

from playwright.sync_api import Page, expect
from pages.base_page import BasePage


# Token-safe class match: ' cd-foo ' inside a normalised, space-padded class
def _cls(token: str) -> str:
    return f"contains(concat(' ',normalize-space(@class),' '),' {token} ')"


class SurveyPage(BasePage):

    URL = "https://candidate-survey-dev.ttec.com/"

    # ---- Stage chips (Q1) -------------------------------------------- #
    STAGE_INTERVIEW = "Interview Experience"
    STAGE_OFFER = "Offer Experience"
    STAGE_BOTH = "Interview + Offer"

    # ---- Section titles ---------------------------------------------- #
    SEC_APPLICATION = "Application and Communication"
    SEC_RECRUITER = "Recruiter and Interview Experience"   # conditional (interview)
    SEC_OFFER = "Offer Process"                            # conditional (offer)
    SEC_OVERALL = "Overall Feeling"
    SEC_VOICE = "Your Voice"

    # ---- Question text fragments (anchor by text, not number) -------- #
    # Section 1 (always)
    Q_APP_EASY = "application process was easy"
    Q_KEPT_INFORMED = "kept informed throughout"
    Q_RESPECTFUL_PACE = "respectful of my time"
    # Section 2 - Recruiter & Interview (interview stages)
    Q_REC_ANSWERED = "recruiter was able to answer"
    Q_REC_SUCCESS = "success looks like in this role"
    Q_REC_PICTURE = "clear and accurate picture of the role"
    Q_REC_RESPECT = "treated me with respect and professionalism"
    Q_REC_KNOWLEDGE = "strong knowledge of the role and hiring process"
    # Section 3 - Offer Process (offer stages)
    Q_OFFER_CONFIDENT = "confident decision about the offer"
    # Section 4 (always)
    Q_FELT_VALUED = "felt valued throughout"
    Q_NPS = "recommend us to a friend"

    # Non-emoji question fragments (for logging the real question text)
    Q_STAGE = "stage of the hiring process"
    Q_LOCATION = "Location and recruiter"
    Q_ROLE = "role did you apply"
    Q_NAME = "Your name"
    Q_EMAIL = "Email Address"
    Q_POSITIVE = "stood out positively"
    Q_NEGATIVE = "could have been better"
    Q_COMMENT = "one thing we could have done"

    # Randomised role pool + fixed identity
    ROLES = ["AI Developer", "Backend Developer", "QA Engineer"]
    DEFAULT_FIRST_NAME = "Lavanya"
    DEFAULT_LAST_NAME = "Madapathi"
    DEFAULT_EMAIL = "lavanyamadapathi@gmail.com"
    DEFAULT_COMMENT = "Overall a smooth and respectful process - thank you!"

    # Expected header / hero text (for the top-of-page verification)
    TITLE_TEXT = "TTEC Candidate Interview and Offer Experience Survey"
    SUBTITLE_TEXT = "Your feedback shapes how we hire"
    HERO_HEADING_TEXT = "Thanks for coming in today!"
    HERO_PARAGRAPH_TEXT = "We care deeply"

    RECRUITER_STATEMENTS = [
        Q_REC_ANSWERED, Q_REC_SUCCESS, Q_REC_PICTURE,
        Q_REC_RESPECT, Q_REC_KNOWLEDGE,
    ]

    POSITIVE_TAGS = [
        "Friendly recruiter", "Clear communication", "Fast response",
        "Well-prepared interviewer", "Respectful of my time",
        "Great role clarity", "Smooth scheduling",
    ]
    NEGATIVE_TAGS = [
        "Slow responses", "Unclear role expectations", "Long process",
        "Scheduling issues", "Lack of follow-up", "Vague feedback",
        "Confusing offer terms",
    ]

    # ---- Static locators --------------------------------------------- #
    ANY_STAGE_CHIP = f"//button[{_cls('cd-chip-opt')}]"

    # Header / hero / intro (top of the survey page)
    HEADER_TITLE = f"//p[{_cls('cd-title')}]"
    HEADER_SUBTITLE = f"//p[{_cls('cd-title-sub')}]"
    LANG_TOGGLE = f"//div[{_cls('cd-lang')}]"
    HERO_EYEBROW = f"//p[{_cls('cd-hero-eyebrow')}]"
    HERO_HEADING = f"//h1[{_cls('cd-hero-h')}]"
    HERO_PARAGRAPH = f"//p[{_cls('cd-hero-p')}]"
    INTRO = f"//div[{_cls('cd-intro')}]"
    REQUIRED_NOTE = f"//div[{_cls('cd-req')}]"

    LOCATION_DROPDOWN = f"(//div[{_cls('p-dropdown')}])[1]"
    RECRUITER_DROPDOWN = f"(//div[{_cls('p-dropdown')}])[2]"

    ROLE_INPUT = "//input[@placeholder='e.g. Customer Service Associate']"
    FIRST_NAME_INPUT = "//input[@id='firstName']"
    LAST_NAME_INPUT = "//input[@id='lastName']"
    EMAIL_INPUT = "//input[@type='email']"
    COMMENT_TEXTAREA = f"//textarea[{_cls('p-inputtextarea')}]"

    ALL_EMOJI_ROWS = f"//div[{_cls('cd-emoji-row')}]"
    ALL_EMOJI_ITEMS = f"//button[{_cls('cd-emoji-item')}]"
    ALL_TAGS = f"//button[{_cls('cd-tag')}]"
    ALL_NPS_ITEMS = f"//button[{_cls('cd-nps-item')}]"
    SUBMIT_BUTTON = f"//button[{_cls('cd-submit-btn')}]"

    QUESTION_TITLES = "//*[contains(@class,'cd-qt-body')]"
    SECTION_TITLES = "//*[contains(@class,'cd-sec-title')]"

    # Validation (verified from the empty-submit DOM)
    #   per-field:  div.cd-error  (with an icon + <span> message)
    #   summary:    div.cd-form-error[role=alert]
    FIELD_ERRORS = f"//div[{_cls('cd-error')}]"
    FORM_ERROR_SUMMARY = f"//div[@role='alert' and {_cls('cd-form-error')}]"
    ANY_ERROR = (
        f"//div[{_cls('cd-error')} or {_cls('cd-form-error')}]"
    )

    # Expected validation messages on an empty submit
    ERR_STAGE = "Please select a stage"
    ERR_LOCATION = "Please select your location"
    ERR_ROLE = "Please enter the role you applied for"
    ERR_SUMMARY = "Please fill in the required fields highlighted above."
    ERR_RECRUITER_WORD = "recruiter"   # appears once Location is chosen

    _SELECTED_TOKENS = ("sel", "active", "selected", "p-highlight", "is-selected")

    def __init__(self, page: Page):
        super().__init__(page)
        self.answers = []   # list of (question_text, answer) for the run

    # ================================================================== #
    # Parametrized locator builders
    # ================================================================== #
    def stage_chip(self, text: str) -> str:
        return f"//button[{_cls('cd-chip-opt')} and normalize-space()='{text}']"

    def section_title(self, name: str) -> str:
        return (
            "//h2[contains(@class,'cd-sec-title') and "
            f"normalize-space()='{name}']"
        )

    def dropdown_option(self, option_text: str) -> str:
        return (
            "//li[contains(@class,'p-dropdown-item') and "
            f"normalize-space()='{option_text}']"
        )

    def first_dropdown_option(self) -> str:
        return "(//li[contains(@class,'p-dropdown-item')])[1]"

    def question_block(self, text_fragment: str) -> str:
        # token-safe 'cd-q' so it matches the .cd-q wrapper only, not the
        # nested .cd-qt / .cd-qt-body (contains() would match those too).
        return (
            f"//div[{_cls('cd-q')}]"
            f"[.//*[contains(@class,'cd-qt-body') and "
            f"contains(normalize-space(),'{text_fragment}')]]"
        )

    def emoji_item(self, question_fragment: str, rating: int) -> str:
        return (
            f"{self.question_block(question_fragment)}"
            f"//button[{_cls('cd-emoji-item')} and "
            f"starts-with(@aria-label,'{rating} ')]"
        )

    def nps_item(self, value) -> str:
        return f"//button[{_cls('cd-nps-item')} and normalize-space()='{value}']"

    def tag_button(self, text: str) -> str:
        return f"//button[{_cls('cd-tag')} and normalize-space()='{text}']"

    def field_error(self, question_fragment: str) -> str:
        """The cd-error message inside a specific question block."""
        return (
            f"{self.question_block(question_fragment)}"
            f"//div[{_cls('cd-error')}]"
        )

    # ================================================================== #
    # Selected-state helper (handles sel class + aria-checked/pressed)
    # ================================================================== #
    def _is_selected(self, xpath: str) -> bool:
        loc = self.find(xpath).first
        cls = (loc.get_attribute("class") or "").split()
        if any(tok in cls for tok in self._SELECTED_TOKENS):
            return True
        return (loc.get_attribute("aria-checked") == "true"
                or loc.get_attribute("aria-pressed") == "true")

    # ================================================================== #
    # Navigation
    # ================================================================== #
    def goto(self):
        self.navigate(self.URL)
        self.wait_for_visible(self.ANY_STAGE_CHIP)

    # ================================================================== #
    # Q1 - Stage
    # ================================================================== #
    def select_stage(self, stage: str):
        self.click(self.stage_chip(stage))

    def is_stage_selected(self, stage: str) -> bool:
        return self._is_selected(self.stage_chip(stage))

    # ================================================================== #
    # Conditional sections
    # ================================================================== #
    def section_count(self, name: str) -> int:
        return self.count(self.section_title(name))

    def recruiter_section_count(self) -> int:
        return self.section_count(self.SEC_RECRUITER)

    def offer_section_count(self) -> int:
        return self.section_count(self.SEC_OFFER)

    def expect_recruiter_section(self, present: bool):
        expect(self.find(self.section_title(self.SEC_RECRUITER))).to_have_count(
            1 if present else 0
        )

    def expect_offer_section(self, present: bool):
        expect(self.find(self.section_title(self.SEC_OFFER))).to_have_count(
            1 if present else 0
        )

    @staticmethod
    def expected_sections(stage: str):
        """Which section titles should be present for a given stage."""
        secs = [SurveyPage.SEC_APPLICATION, SurveyPage.SEC_OVERALL,
                SurveyPage.SEC_VOICE]
        if stage in (SurveyPage.STAGE_INTERVIEW, SurveyPage.STAGE_BOTH):
            secs.insert(1, SurveyPage.SEC_RECRUITER)
        if stage in (SurveyPage.STAGE_OFFER, SurveyPage.STAGE_BOTH):
            secs.insert(-2, SurveyPage.SEC_OFFER)
        return secs

    # ================================================================== #
    # Q2 - Location + Recruiter
    # ================================================================== #
    def select_location(self, country: str):
        self.click(self.LOCATION_DROPDOWN)
        self.click(self.dropdown_option(country))

    def select_recruiter(self, recruiter: str):
        self.click(self.RECRUITER_DROPDOWN)
        self.click(self.dropdown_option(recruiter))

    def select_first_recruiter(self):
        """Recruiter options depend on the chosen Location; pick the first."""
        self.click(self.RECRUITER_DROPDOWN)
        self.click(self.first_dropdown_option())

    def is_recruiter_disabled(self) -> bool:
        return self.has_class(self.RECRUITER_DROPDOWN, "p-disabled")

    # ================================================================== #
    # Q3 / Q4 / Q5 / free-text - inputs
    # ================================================================== #
    def fill_role(self, role: str):
        self.fill(self.ROLE_INPUT, role)

    def fill_first_name(self, value: str):
        self.fill(self.FIRST_NAME_INPUT, value)

    def fill_last_name(self, value: str):
        self.fill(self.LAST_NAME_INPUT, value)

    def fill_email(self, value: str):
        self.fill(self.EMAIL_INPUT, value)

    def fill_comment(self, value: str):
        self.fill(self.COMMENT_TEXTAREA, value)

    # ================================================================== #
    # Emoji ratings
    # ================================================================== #
    def rate_emoji(self, question_fragment: str, rating: int):
        self.click(self.emoji_item(question_fragment, rating))

    def is_emoji_selected(self, question_fragment: str, rating: int) -> bool:
        return self._is_selected(self.emoji_item(question_fragment, rating))

    # ================================================================== #
    # NPS
    # ================================================================== #
    def select_nps(self, value):
        self.click(self.nps_item(value))

    def is_nps_selected(self, value) -> bool:
        return self._is_selected(self.nps_item(value))

    def selected_nps_count(self) -> int:
        n = 0
        loc = self.find(self.ALL_NPS_ITEMS)
        for i in range(loc.count()):
            cls = (loc.nth(i).get_attribute("class") or "").split()
            aria = loc.nth(i).get_attribute("aria-checked")
            if any(t in cls for t in self._SELECTED_TOKENS) or aria == "true":
                n += 1
        return n

    # ================================================================== #
    # Tags (multi-select)
    # ================================================================== #
    def toggle_tag(self, text: str):
        self.click(self.tag_button(text))

    def is_tag_selected(self, text: str) -> bool:
        return self._is_selected(self.tag_button(text))

    # ================================================================== #
    # Submit + validation
    # ================================================================== #
    def submit(self):
        self.click(self.SUBMIT_BUTTON)

    def field_error_count(self) -> int:
        return self.count(self.FIELD_ERRORS)

    def has_form_error_summary(self) -> bool:
        return self.count(self.FORM_ERROR_SUMMARY) >= 1

    def get_form_error_summary(self) -> str:
        return self.text_of(self.FORM_ERROR_SUMMARY)

    # ================================================================== #
    # Convenience
    # ================================================================== #
    def fill_required_fields(self, stage, location, role, recruiter=None):
        """Stage -> Location -> Recruiter -> Role (Location gates Recruiter)."""
        self.select_stage(stage)
        self.select_location(location)
        if recruiter:
            self.select_recruiter(recruiter)
        else:
            self.select_first_recruiter()
        self.fill_role(role)

    def rate_all_visible_emojis(self, rating: int = 5):
        """Rate every emoji question on the page, in top-to-bottom order.

        Iterates the emoji rows as they appear in the DOM (rather than a
        fixed list) so every visible statement for the current stage is
        answered in sequence.
        """
        rows = self.find(self.ALL_EMOJI_ROWS)
        for i in range(rows.count()):
            btn = rows.nth(i).locator(
                f"xpath=.//button[{_cls('cd-emoji-item')} and "
                f"starts-with(@aria-label,'{rating} ')]"
            ).first
            btn.wait_for(state="visible", timeout=self.DEFAULT_TIMEOUT)
            self._flash(btn)
            btn.click()

    # ================================================================== #
    # Answer history (question text + chosen answer), printed + stored
    # ================================================================== #
    def _log(self, question: str, answer):
        question = " ".join(str(question).split())
        self.answers.append((question, str(answer)))
        print(f"  [Q] {question}\n      -> {answer}")

    def get_question_text(self, fragment: str) -> str:
        loc = self.find(
            "//*[contains(@class,'cd-qt-body') and "
            f"contains(normalize-space(),'{fragment}')]"
        ).first
        loc.wait_for(state="visible", timeout=self.DEFAULT_TIMEOUT)
        self._flash(loc)                      # highlight the question text
        return " ".join(loc.inner_text().split())

    def verify_and_log_header(self):
        """Highlight + verify the survey header/hero/intro at the top of the
        page, logging each into the run history."""
        title = self.text_of(self.HEADER_TITLE)
        self._log("[Survey title]", title)
        subtitle = self.text_of(self.HEADER_SUBTITLE)
        self._log("[Survey subtitle]", subtitle)
        eyebrow = self.text_of(self.HERO_EYEBROW)
        self._log("[Hero eyebrow]", eyebrow)
        hero = self.text_of(self.HERO_HEADING)
        self._log("[Hero heading]", hero)
        hero_p = self.text_of(self.HERO_PARAGRAPH)
        self._log("[Hero paragraph]", hero_p)
        intro = self.text_of(self.INTRO)
        self._log("[Intro]", intro)
        required = self.text_of(self.REQUIRED_NOTE)
        self._log("[Required note]", required)

        assert self.TITLE_TEXT in title, f"unexpected title: {title!r}"
        assert self.SUBTITLE_TEXT in subtitle, f"unexpected subtitle: {subtitle!r}"
        assert self.HERO_HEADING_TEXT in hero, f"unexpected hero: {hero!r}"
        assert self.HERO_PARAGRAPH_TEXT in hero_p, f"unexpected hero p: {hero_p!r}"
        return title

    def save_answer_log(self, stage: str) -> str:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out_dir = os.path.join(base, "reports")
        os.makedirs(out_dir, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in stage)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(out_dir, f"answers_{safe}_{ts}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Survey run - stage: {stage}\n{'=' * 50}\n\n")
            for i, (q, a) in enumerate(self.answers, 1):
                f.write(f"{i}. {q}\n   -> {a}\n\n")
        print(f"\nAnswer history saved to {path}")
        return path

    # ================================================================== #
    # Randomised pickers (non-static per run)
    # ================================================================== #
    def _pick_random_open_option(self):
        """From an already-open dropdown panel: flash + click a random item,
        returning its visible text. Clicks by index to avoid XPath escaping."""
        items = self.find("//li[contains(@class,'p-dropdown-item')]")
        n = items.count()
        idx = random.randrange(n)
        item = items.nth(idx)
        text = " ".join(item.inner_text().split())
        item.scroll_into_view_if_needed(timeout=self.DEFAULT_TIMEOUT)
        self._flash(item)
        item.click()
        return text

    def select_random_location(self) -> str:
        q = self.get_question_text(self.Q_LOCATION)
        self.click(self.LOCATION_DROPDOWN)
        choice = self._pick_random_open_option()
        self._log(f"{q} (Location)", choice)
        return choice

    def select_random_recruiter(self) -> str:
        self.click(self.RECRUITER_DROPDOWN)
        choice = self._pick_random_open_option()
        self._log("Your Recruiter", choice)
        return choice

    def fill_role_random(self) -> str:
        q = self.get_question_text(self.Q_ROLE)
        role = random.choice(self.ROLES)
        self.fill_role(role)
        self._log(q, role)
        return role

    def fill_name(self, first=None, last=None):
        q = self.get_question_text(self.Q_NAME)
        first = first or self.DEFAULT_FIRST_NAME
        last = last or self.DEFAULT_LAST_NAME
        self.fill_first_name(first)
        self.fill_last_name(last)
        self._log(q, f"{first} {last}")

    def fill_email_default(self, email=None):
        q = self.get_question_text(self.Q_EMAIL)
        email = email or self.DEFAULT_EMAIL
        self.fill_email(email)
        self._log(q, email)

    def answer_all_emojis_random(self, low: int = 1, high: int = 5):
        """Rate every emoji question in DOM order with a random face; logs
        each question's text and the rating chosen. Rows are re-fetched each
        iteration so a re-render never produces stale/duplicated clicks."""
        n = self.count(self.ALL_EMOJI_ROWS)
        for i in range(n):
            row = self.find(self.ALL_EMOJI_ROWS).nth(i)
            qloc = row.locator(
                f"xpath=ancestor::div[{_cls('cd-q')}][1]"
                "//*[contains(@class,'cd-qt-body')]"
            ).first
            qtext = " ".join(qloc.inner_text().split())
            self._flash(qloc)
            rating = random.randint(low, high)
            btn = row.locator(
                f"xpath=.//button[{_cls('cd-emoji-item')} and "
                f"starts-with(@aria-label,'{rating} ')]"
            ).first
            btn.scroll_into_view_if_needed(timeout=self.DEFAULT_TIMEOUT)
            self._flash(btn)
            btn.click()
            self._log(qtext, f"{rating} (emoji)")

    def select_random_nps(self):
        q = self.get_question_text(self.Q_NPS)
        val = random.randint(1, 10)
        self.select_nps(val)
        self._log(q, f"{val} / 10")
        return val

    def select_random_tags(self):
        for frag in (self.Q_POSITIVE, self.Q_NEGATIVE):
            q = self.get_question_text(frag)
            btns = self.find(
                f"{self.question_block(frag)}//button[{_cls('cd-tag')}]"
            )
            n = btns.count()
            if n == 0:
                continue
            k = random.randint(1, n)
            chosen = []
            for idx in sorted(random.sample(range(n), k)):
                b = btns.nth(idx)
                chosen.append(" ".join(b.inner_text().split()))
                b.scroll_into_view_if_needed(timeout=self.DEFAULT_TIMEOUT)
                self._flash(b)
                b.click()
            self._log(q, ", ".join(chosen))

    def fill_comment_default(self, text=None):
        q = self.get_question_text(self.Q_COMMENT)
        text = text or self.DEFAULT_COMMENT
        self.fill_comment(text)
        self._log(q, text)

    # ================================================================== #
    # Validation - empty submit then verify the error messages
    # ================================================================== #
    def collect_errors(self):
        """Highlight + log every visible error message (field + summary),
        returning the list of message texts."""
        self.page.wait_for_timeout(600)   # let validation render
        seen = []
        for xp in (self.FIELD_ERRORS, self.FORM_ERROR_SUMMARY):
            loc = self.find(xp)
            for i in range(loc.count()):
                el = loc.nth(i)
                try:
                    if not el.is_visible():
                        continue
                    txt = " ".join(el.inner_text().split())
                except Exception:
                    continue
                if txt and txt not in seen:
                    seen.append(txt)
                    self._flash(el)
                    self._log("[Error]", txt)
        return seen

    def verify_empty_submit_errors(self):
        """Submit the empty form and verify the mandatory-field errors +
        the form-level summary, highlighting and logging each."""
        self.submit()
        messages = self.collect_errors()
        joined = " | ".join(messages)

        assert any(self.ERR_STAGE in m for m in messages), \
            f"missing stage error; got: {joined}"
        assert any(self.ERR_LOCATION in m for m in messages), \
            f"missing location error; got: {joined}"
        assert any(self.ERR_ROLE in m for m in messages), \
            f"missing role error; got: {joined}"
        assert any(self.ERR_SUMMARY in m for m in messages), \
            f"missing form-error summary; got: {joined}"
        self._log("[Validation]",
                  f"{len(messages)} error message(s) verified on empty submit")
        return messages

    def verify_recruiter_error(self):
        """The recruiter error only appears once a Location is chosen (the
        field is disabled until then). Select a location, submit, and verify
        the recruiter validation message appears."""
        self.select_random_location()
        self.submit()
        self.page.wait_for_timeout(600)
        loc = self.find(self.field_error(self.Q_LOCATION)).first
        loc.wait_for(state="visible", timeout=self.DEFAULT_TIMEOUT)
        txt = " ".join(loc.inner_text().split())
        self._flash(loc)
        self._log("[Error]", txt)
        assert self.ERR_RECRUITER_WORD in txt.lower(), \
            f"expected a recruiter error after choosing location; got: {txt!r}"
        return txt

    # ================================================================== #
    # Full run - answer EVERY question top-to-bottom, nothing skipped
    # ================================================================== #
    def _fill_all_questions(self, stage, first=None, last=None, email=None,
                            comment=None, skip_location=False):
        # Q1 stage
        qstage = self.get_question_text(self.Q_STAGE)
        self.select_stage(stage)
        self._log(qstage, stage)

        # Q2 location + recruiter (random each run; location may already be set)
        if not skip_location:
            self.select_random_location()
        self.select_random_recruiter()

        # Q3 role (random), Q4 name, Q5 email
        self.fill_role_random()
        self.fill_name(first, last)
        self.fill_email_default(email)

        # Q6..N emoji ratings (random), then NPS, tags, free-text comment
        self.answer_all_emojis_random()
        self.select_random_nps()
        self.select_random_tags()
        self.fill_comment_default(comment)

    def complete_full_survey(self, stage, first=None, last=None, email=None,
                             comment=None):
        self.answers = []
        print(f"\n===== Filling survey - stage: '{stage}' =====")
        self.verify_and_log_header()
        self._fill_all_questions(stage, first, last, email, comment)
        return self.answers

    def complete_with_validation(self, stage, first=None, last=None,
                                 email=None, comment=None):
        """One run: verify header -> empty submit -> verify error messages ->
        fill every question -> (caller submits + verifies Thank-You)."""
        self.answers = []
        print(f"\n===== Validation + full run - stage: '{stage}' =====")
        self.verify_and_log_header()

        # 1) Submit with nothing filled -> stage/location/role + summary errors.
        print("  -- submitting empty form to trigger validation --")
        self.verify_empty_submit_errors()

        # 2) Choose a location, submit again -> the recruiter error appears
        #    (recruiter is disabled until Location is chosen).
        print("  -- verifying recruiter error after choosing location --")
        self.verify_recruiter_error()

        # 3) Answer every remaining question (location already set) and submit.
        self._fill_all_questions(stage, first, last, email, comment,
                                 skip_location=True)
        return self.answers

    def submit_and_capture(self, stage: str) -> str:
        """Click Submit, wait for the result, and save the post-submit page
        HTML to reports/ so the Thank-You markup can be locked down. Returns
        the saved HTML path."""
        self._log("Submit survey", "clicked")
        self.click(self.SUBMIT_BUTTON)
        try:
            self.page.wait_for_load_state("networkidle",
                                          timeout=self.DEFAULT_TIMEOUT)
        except Exception:
            pass
        self.page.wait_for_timeout(1500)   # let the confirmation render

        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out_dir = os.path.join(base, "reports")
        os.makedirs(out_dir, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in stage)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(out_dir, f"thankyou_dom_{safe}_{ts}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.page.content())
        print(f"Post-submit DOM saved to {path}")
        return path

    def complete_and_submit(self, stage, first=None, last=None, email=None,
                            comment=None) -> str:
        """Fill every question (logged) then submit. Returns post-submit HTML
        path for confirmation-locator verification."""
        self.complete_full_survey(stage, first, last, email, comment)
        return self.submit_and_capture(stage)

    # ================================================================== #
    # Selected-item counters (completeness checks)
    # ================================================================== #
    def _count_selected(self, all_xpath: str) -> int:
        loc = self.find(all_xpath)
        n = 0
        for i in range(loc.count()):
            el = loc.nth(i)
            cls = (el.get_attribute("class") or "").split()
            if (any(t in cls for t in self._SELECTED_TOKENS)
                    or el.get_attribute("aria-checked") == "true"
                    or el.get_attribute("aria-pressed") == "true"):
                n += 1
        return n

    def selected_emoji_count(self) -> int:
        return self._count_selected(self.ALL_EMOJI_ITEMS)

    def selected_tag_count(self) -> int:
        return self._count_selected(self.ALL_TAGS)

    def emoji_question_count(self) -> int:
        return self.count(self.ALL_EMOJI_ROWS)

    # ================================================================== #
    # Highlight helpers (visual walkthrough)
    # ================================================================== #
    def highlight_all_questions(self):
        self.highlight_each(self.QUESTION_TITLES)

    def highlight_field_errors(self):
        self.highlight_each(self.FIELD_ERRORS)

    def highlight_form_error(self):
        self.highlight(self.FORM_ERROR_SUMMARY)

    def highlight_submit(self):
        self.highlight(self.SUBMIT_BUTTON)


class ThankYouPage(BasePage):
    

    CONTAINER = f"//div[{_cls('tky')}]"
    BADGE = f"//div[{_cls('tky-badge')}]"
    SUBTITLE = f"//p[{_cls('tky-sub')}]"          # "Survey submitted successfully"
    HEADING = f"//h2[{_cls('tky-h')}]"            # "Thanks for sharing your thoughts!"
    BODY = f"//div[{_cls('tky-body')}]"

    def __init__(self, page: Page):
        super().__init__(page)

    def is_displayed(self) -> bool:
        return self.count(self.SUBTITLE) >= 1

    def wait_until_displayed(self):
        self.wait_for_visible(self.SUBTITLE)

    def get_subtitle(self) -> str:
        return self.text_of(self.SUBTITLE)

    def get_heading(self) -> str:
        return self.text_of(self.HEADING)

    def get_message(self) -> str:
        return self.text_of(self.BODY)

    def verify(self, log=None):
        """Highlight + read the confirmation title/subtitle/body, optionally
        logging each via the given callback (e.g. SurveyPage._log)."""
        subtitle = self.get_subtitle()
        heading = self.get_heading()
        body = self.get_message()
        if log:
            log("[Thank-You subtitle]", subtitle)
            log("[Thank-You heading]", heading)
            log("[Thank-You body]", body)
        assert "submitted" in subtitle.lower(), \
            f"unexpected confirmation subtitle: {subtitle!r}"
        return subtitle, heading, body