
import pytest
from pages.survey_pages import SurveyPage, ThankYouPage

# --------------------------------------------------------------------- #
# Real values from the live DOM
# --------------------------------------------------------------------- #
LOCATION = "Philippines"
ROLE = "Customer Service Associate"
FIRST_NAME = "Test"
LAST_NAME = "Candidate"
EMAIL = "test.candidate@example.com"
POSITIVE_TAG = "Friendly recruiter"
NEGATIVE_TAG = "Slow responses"


@pytest.fixture()
def survey(page):
    return SurveyPage(page)


@pytest.fixture()
def fresh_survey(fresh_page):
    """SurveyPage on a brand-new context (used by submitting tests)."""
    return SurveyPage(fresh_page)


# ===================================================================== #
# Section 1 - always-present fields
# ===================================================================== #
class TestSection1:

    def test_form_loads_with_three_stage_chips(self, survey):
        survey.goto()
        assert survey.count(survey.ANY_STAGE_CHIP) == 3

    def test_recruiter_disabled_until_location(self, survey):
        survey.page.reload()
        survey.goto()
        assert survey.is_recruiter_disabled() is True
        survey.select_location(LOCATION)
        assert survey.is_recruiter_disabled() is False

    def test_location_and_first_recruiter(self, survey):
        survey.page.reload()
        survey.goto()
        survey.select_location(LOCATION)
        survey.select_first_recruiter()
        assert survey.is_recruiter_disabled() is False

    def test_text_fields(self, survey):
        survey.page.reload()
        survey.goto()
        survey.fill_role(ROLE)
        survey.fill_first_name(FIRST_NAME)
        survey.fill_last_name(LAST_NAME)
        survey.fill_email(EMAIL)
        assert survey.find(survey.ROLE_INPUT).input_value() == ROLE
        assert survey.find(survey.FIRST_NAME_INPUT).input_value() == FIRST_NAME

    def test_base_emoji_statements(self, survey):
        survey.page.reload()
        survey.goto()
        survey.select_stage(survey.STAGE_BOTH)
        for frag in (survey.Q_APP_EASY, survey.Q_KEPT_INFORMED,
                     survey.Q_RESPECTFUL_PACE):
            survey.rate_emoji(frag, 4)
            assert survey.is_emoji_selected(frag, 4) is True


# ===================================================================== #
# Stage: Interview Experience -> Section 2 present, Section 3 absent
# ===================================================================== #
class TestStageInterviewExperience:

    def test_sections(self, survey):
        survey.page.reload()
        survey.goto()
        survey.select_stage(survey.STAGE_INTERVIEW)
        assert survey.is_stage_selected(survey.STAGE_INTERVIEW) is True
        survey.expect_recruiter_section(True)
        survey.expect_offer_section(False)

    def test_recruiter_statements_present_and_ratable(self, survey):
        for frag in survey.RECRUITER_STATEMENTS:
            assert survey.count(survey.question_block(frag)) == 1
            survey.rate_emoji(frag, 5)
            assert survey.is_emoji_selected(frag, 5) is True

    def test_offer_statement_absent(self, survey):
        assert survey.count(
            survey.question_block(survey.Q_OFFER_CONFIDENT)
        ) == 0


# ===================================================================== #
# Stage: Offer Experience -> Section 3 present, Section 2 absent
# ===================================================================== #
class TestStageOfferExperience:

    def test_sections(self, survey):
        survey.page.reload()
        survey.goto()
        survey.select_stage(survey.STAGE_OFFER)
        assert survey.is_stage_selected(survey.STAGE_OFFER) is True
        survey.expect_recruiter_section(False)
        survey.expect_offer_section(True)

    def test_offer_statement_present_and_ratable(self, survey):
        assert survey.count(
            survey.question_block(survey.Q_OFFER_CONFIDENT)
        ) == 1
        survey.rate_emoji(survey.Q_OFFER_CONFIDENT, 5)
        assert survey.is_emoji_selected(survey.Q_OFFER_CONFIDENT, 5) is True

    def test_recruiter_statements_absent(self, survey):
        for frag in survey.RECRUITER_STATEMENTS:
            assert survey.count(survey.question_block(frag)) == 0


# ===================================================================== #
# Stage: Interview + Offer -> both Section 2 and Section 3 present
# ===================================================================== #
class TestStageInterviewPlusOffer:

    def test_both_sections_present(self, survey):
        survey.page.reload()
        survey.goto()
        survey.select_stage(survey.STAGE_BOTH)
        survey.expect_recruiter_section(True)
        survey.expect_offer_section(True)

    def test_all_expected_sections_render(self, survey):
        for name in survey.expected_sections(survey.STAGE_BOTH):
            assert survey.section_count(name) == 1

    def test_all_visible_emojis_ratable(self, survey):
        survey.rate_all_visible_emojis(5)


# ===================================================================== #
# Overall Feeling - NPS
# ===================================================================== #
class TestNps:

    def test_nps_single_selection(self, survey):
        survey.page.reload()
        survey.goto()
        survey.select_stage(survey.STAGE_BOTH)
        survey.select_nps(9)
        assert survey.is_nps_selected(9) is True
        assert survey.selected_nps_count() == 1

    def test_nps_reselect_moves_selection(self, survey):
        survey.select_nps(7)
        assert survey.is_nps_selected(7) is True
        assert survey.is_nps_selected(9) is False
        assert survey.selected_nps_count() == 1


# ===================================================================== #
# Your Voice - tags
# ===================================================================== #
class TestTags:

    def test_tags_multi_select(self, survey):
        survey.page.reload()
        survey.goto()
        survey.select_stage(survey.STAGE_BOTH)
        survey.toggle_tag(POSITIVE_TAG)
        survey.toggle_tag(NEGATIVE_TAG)
        assert survey.is_tag_selected(POSITIVE_TAG) is True
        assert survey.is_tag_selected(NEGATIVE_TAG) is True

    def test_tag_deselect(self, survey):
        survey.toggle_tag(POSITIVE_TAG)   # toggle off
        assert survey.is_tag_selected(POSITIVE_TAG) is False


# ===================================================================== #
# Validation  (confirm cd-error / cd-form-error on first run)
# ===================================================================== #
class TestValidation:

    def test_submit_empty_shows_errors(self, survey):
        survey.page.reload()
        survey.goto()
        survey.submit()
        assert (
            survey.has_form_error_summary() or survey.field_error_count() >= 1
        )


# ===================================================================== #
# End-to-end: fill EVERY question (logged) then submit, one per stage.
# Run:  pytest tests/test_survey.py::TestSubmission -s
# If the Thank-You confirmation isn't found, the post-submit DOM is saved
# to reports/thankyou_dom_*.html for locking the locator.
# ===================================================================== #
class TestSubmission:

    @pytest.mark.parametrize("stage", [
        SurveyPage.STAGE_INTERVIEW,
        SurveyPage.STAGE_OFFER,
        SurveyPage.STAGE_BOTH,
    ])
    def test_submit_per_stage(self, survey, page, stage):
        survey.page.reload()
        survey.goto()
        html_path = survey.complete_and_submit(stage)

        thank_you = ThankYouPage(page)
        try:
            thank_you.wait_until_displayed()
        except Exception:
            pytest.fail(
                "Submitted, but the Thank-You confirmation wasn't found with "
                f"the current locator. Post-submit DOM saved to:\n  {html_path}\n"
                "Send that file to lock the ThankYouPage locator."
            )
        assert thank_you.is_displayed() is True
        print(f"Confirmation: {thank_you.get_message()[:120]}")


# ===================================================================== #
# Full run - answer EVERY question (randomised) and print the history
# Run:  pytest tests/test_survey.py::TestFullRun -s
# The -s flag shows the question/answer history in the console; a copy is
# also written to reports/answers_<stage>_<timestamp>.txt
# ===================================================================== #
class TestFullRun:

    @pytest.mark.parametrize("stage", [
        SurveyPage.STAGE_INTERVIEW,
        SurveyPage.STAGE_OFFER,
        SurveyPage.STAGE_BOTH,
    ])
    def test_answer_every_question(self, fresh_survey, fresh_page, stage):
        survey = fresh_survey
        survey.goto()
        survey.complete_full_survey(stage)   # name/email/comment use defaults

        # Nothing skipped: every emoji question answered, NPS set, >=1 tag,
        # and the required text fields populated.
        assert survey.selected_emoji_count() == survey.emoji_question_count()
        assert survey.selected_nps_count() == 1
        assert survey.selected_tag_count() >= 1
        assert survey.find(survey.ROLE_INPUT).input_value() in survey.ROLES
        assert survey.find(survey.FIRST_NAME_INPUT).input_value() == \
            survey.DEFAULT_FIRST_NAME
        assert survey.find(survey.EMAIL_INPUT).input_value() == \
            survey.DEFAULT_EMAIL

        # Submit and confirm the Thank-You page (highlight + verify + log).
        survey.submit()
        thank_you = ThankYouPage(fresh_page)
        thank_you.wait_until_displayed()
        subtitle, heading, _ = thank_you.verify(log=survey._log)
        assert thank_you.is_displayed() is True
        print(f"  [SUBMITTED] {subtitle} - {heading}")

        # Save the full history (header + answers + confirmation).
        survey.save_answer_log(stage)


# ===================================================================== #
# One run: verify header -> empty submit shows errors -> fill everything
# -> submit -> verify Thank-You page. Fresh context so the submit is clean.
# Run:  pytest tests/test_survey.py::TestValidationThenSubmit -s
# ===================================================================== #
class TestValidationThenSubmit:

    @pytest.mark.parametrize("stage", [
        SurveyPage.STAGE_INTERVIEW,
        SurveyPage.STAGE_OFFER,
        SurveyPage.STAGE_BOTH,
    ])
    def test_empty_submit_then_complete(self, fresh_survey, fresh_page, stage):
        survey = fresh_survey
        survey.goto()

        # header check + empty-submit error verification (incl. recruiter)
        # + fill every question
        survey.complete_with_validation(stage)

        # everything answered
        assert survey.selected_emoji_count() == survey.emoji_question_count()
        assert survey.selected_nps_count() == 1
        assert survey.selected_tag_count() >= 1

        # submit for real and verify the Thank-You page + its context
        survey.submit()
        thank_you = ThankYouPage(fresh_page)
        thank_you.wait_until_displayed()
        subtitle, heading, body = thank_you.verify(log=survey._log)
        assert "submitted" in subtitle.lower()
        assert "thanks" in heading.lower()
        assert "Talent Acquisition" in body
        print(f"  [SUBMITTED] {subtitle} - {heading}")

        survey.save_answer_log("ValidationThenSubmit_" + stage)


# ===================================================================== #
# Visual walkthrough
# Run:  pytest tests/test_survey.py::TestVisualWalkthrough -s
# ===================================================================== #
class TestVisualWalkthrough:

    def test_walkthrough(self, survey):
        survey.page.reload()
        survey.goto()
        survey.highlight_all_questions()

        survey.select_stage(survey.STAGE_BOTH)   # renders every section
        survey.highlight_all_questions()

        survey.select_location(LOCATION)
        survey.select_first_recruiter()
        survey.fill_role(ROLE)
        survey.rate_all_visible_emojis(5)
        survey.select_nps(9)
        survey.toggle_tag(POSITIVE_TAG)