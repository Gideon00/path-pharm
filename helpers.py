from functools import wraps
from flask import abort, redirect, render_template, session


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("oauth_id") is None:
            return redirect("/signin")
        return f(*args, **kwargs)

    return decorated_function


def clear_selected_sessions():
    # List of session keys to be cleared
    keys_to_clear = [
        # Quiz-related
        "region",
        "score_tracker",
        "current_num",
        "score",
        "fails",
        "answers",
        "start",
        "current_question_index",
    ]

    # Loop through each key and remove it from the session
    for key in keys_to_clear:
        session.pop(
            key, None
        )  # Use pop to remove the key without throwing an error if it doesn't exist


# Define the custom Jinja2 filter function
def number_to_upper(num):
    return chr(ord("A") + num - 1) if 1 <= num <= 26 else ""


# Create list of regions
REGIONS = [
    "Pharmacology",
    "Anatomical Pathology",
    "Hematology",
    "Chemical Pathology",
    "Microbiology",
]
MCQ_REGIONS = [
    "First Posting PHARMACOLOGY",
    "First Posting ANATOMICAL",
    "First Posting HEMATOLOGY",
    "First Posting CHEMICAL",
    "First Posting MICROBIOLOGY",
    "Second Posting PHARMACOLOGY",
    "Second Posting ANATOMICAL",
    "Second Posting HEMATOLOGY",
    "Second Posting CHEMICAL",
    "Second Posting MICROBIOLOGY",
    "Third Posting PHARMACOLOGY",
    "Third Posting ANATOMICAL",
    "Third Posting HEMATOLOGY",
    "Third Posting CHEMICAL",
    "Third Posting MICROBIOLOGY",
]
triads = [
    "chemical",
    "anatomical",
]

# Query for inserting into streak_winner: Make sure score is at least 50% and above
query = """
    SELECT candidate_id, score, course, format, 
    (end_quest - (start_quest - 1)) AS total_questions, time 
    FROM scoresheet 
    WHERE candidate_id = ? 
    AND (end_quest - (start_quest - 1)) >= 20
    AND (score / (end_quest - (start_quest - 1))) * 100 > 50
    ORDER BY score DESC 
    LIMIT 1;
"""

mcq_query = """
    SELECT candidate_id, score, course, format, 
    (end_quest - (start_quest - 1)) AS total_questions, time 
    FROM scoresheet 
    WHERE candidate_id = ? 
    AND (end_quest - (start_quest - 1)) >= 50
    AND (score / (end_quest - (start_quest - 1))) * 100 > 50
    ORDER BY score DESC 
    LIMIT 1;
"""
