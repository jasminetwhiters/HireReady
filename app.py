"""
app.py

Minimal Flask web app around resume_matcher.py's run_pipeline() function.
This file has almost no logic of its own on purpose - it just:
  1. Shows a form with two text boxes (resume, job posting)
  2. Calls run_pipeline() with whatever the user pasted in
  3. Renders the same dict of results the CLI already prints

Keeping ALL the actual logic in resume_matcher.py (not duplicated here)
means any bugfix or feature you add there automatically shows up on the
webpage too, with nothing to keep in sync.

Run with:  python3 app.py
Then open: http://127.0.0.1:5000 in your browser
Requires:  pip install flask anthropic
           export ANTHROPIC_API_KEY="your-key-here" (or use a .env file, see README)
"""

from flask import Flask, render_template, request
from HireReady import run_pipeline

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    # On a fresh page load (GET), there's no result yet - just show the form.
    result = None
    error = None
    resume_text = ""
    job_text = ""

    if request.method == "POST":
        # .get() with a default of "" avoids a crash if a field is somehow
        # missing from the form submission.
        resume_text = request.form.get("resume_text", "").strip()
        job_text = request.form.get("job_text", "").strip()

        if not resume_text or not job_text:
            # Don't even call the API if one box is empty - that's a wasted
            # API call for a result we already know will be useless.
            error = "Please paste both a resume and a job posting before submitting."
        else:
            try:
                result = run_pipeline(resume_text, job_text)
            except Exception as e:
                # Catches API errors, JSON parsing failures from Claude's
                # response, etc. Show the user something readable instead of
                # a raw Flask error page (which is confusing and not
                # appropriate to show to non-developer end users).
                error = f"Something went wrong while analyzing: {e}"

    return render_template(
        "index.html",
        result=result,
        error=error,
        resume_text=resume_text,
        job_text=job_text,
    )


@app.after_request
def add_no_cache_headers(response):
    # Prevents the browser from ever caching this page. This is what was
    # causing the old-project confusion earlier - without this, browsers
    # can silently reuse a previously cached response for a URL/port
    # they've seen before, even after a hard refresh in some cases.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


if __name__ == "__main__":
    # New port, never used by any previous project on this machine -
    # guarantees no stale cache or leftover server can collide with it.
    app.run(debug=True, port=9034, host="0.0.0.0")
