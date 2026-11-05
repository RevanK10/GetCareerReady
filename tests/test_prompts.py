import prompts


def test_every_prompt_formats_with_its_placeholders():
    """A stray { or } in a template breaks .format(). Catch it here, not in the app."""
    prompts.FIT_PROMPT.format(resume_text="r", job_description="j")
    prompts.REVIEW_PROMPT.format(original="o", tailored="t")
    prompts.INTERVIEWER_SYSTEM.format(kind="k", style="s", title="t", company="c", job="j", resume="r")
    prompts.FEEDBACK_PROMPT.format(title="t", company="c", job="j", transcript="x")
    prompts.RESUME_TAILOR_PROMPT.format(resume_text="r", job_description="j")
    prompts.COVER_LETTER_PROMPT.format(name="n", resume_text="r", title="t", company="c", job_description="j")


def test_prompts_treat_job_text_as_untrusted():
    for prompt in (prompts.FIT_PROMPT, prompts.RESUME_TAILOR_PROMPT, prompts.COVER_LETTER_PROMPT):
        assert "untrusted" in prompt
