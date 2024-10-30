import os
import json
import pathlib
import requests
import psycopg2
from cs50 import SQL
from tempfile import mkdtemp
from dotenv import load_dotenv
from flask_session import Session
from google.oauth2 import id_token
from pip._vendor import cachecontrol
import google.auth.transport.requests
from google_auth_oauthlib.flow import Flow
from flask import Flask, abort, redirect, render_template, request, session, url_for
from helpers import (
    MCQ_REGIONS,
    REGIONS,
    apology,
    clear_selected_sessions,
    login_required,
    number_to_upper,
    query,
    mcq_query,
    triads
)


load_dotenv()

app = Flask(__name__)
# csrf = CSRFProtect(app)

app.secret_key = os.getenv("SECRETE_KEY")

# Config sessions
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure CS50 Library to use PostgreSQL database
db = SQL(os.getenv("POSTGRESQL"))

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = os.getenv("NUM")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
# Path for Development environment
# client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

# Path for Production
client_secrets_file = "/etc/secrets/client_secret.json"

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ],
    redirect_uri="https://path-pharm.onrender.com/callback",
)

# GitHub OAuth details
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com/user"

question_bank = []
default_profile_img = ""


# Register the filter function with Jinja2 environment
app.jinja_env.filters["number_to_upper"] = number_to_upper


# Byepass OAuth login
@app.route("/byepas", methods=["GET", "POST"])
def byepas():
    if request.method == "POST":

        user_id = int(request.form.get("bypass"))

        # Check if the user exists
        user = db.execute("SELECT * FROM users WHERE id = ?;", user_id)[0]

        # Store the user's info in session for tracking the login
        session["admin"] = user["is_admin"]
        session["user_id"] = user["id"]
        session["oauth_id"] = user["oauth_id"]
        session["name"] = user["name"]
        session["email"] = user["email"]
        session["picture"] = user.get("picture") or None
        return redirect("/") # EndBye Pass


# We begin Auth here
@app.route("/signin", methods=["GET", "POST"])
def signin():
    return render_template("login.html")


@app.route("/login")
def login():
    # Dynamically generate the redirect URI
    redirect_uri = url_for('callback', _external=True)
    print("\n")
    print(f'Redirect URI: {redirect_uri}')  # This will print the URI to your console/logs
    print("\n")
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token, request=token_request, audience=GOOGLE_CLIENT_ID
    )

    # Store the user's info in session for tracking the login
    session["oauth_id"] = id_info["sub"]
    session["name"] = id_info["name"]
    session["email"] = id_info["email"]
    session["picture"] = id_info.get("picture") or None

    # Check if the user exists
    existing_user = db.execute(
        "SELECT id, is_admin FROM users WHERE oauth_id = ?;", session["oauth_id"]
    )

    # If the user exists, store the user_id in the session
    if existing_user:
        session["user_id"] = existing_user[0]["id"]
        session["admin"] = existing_user[0]["is_admin"]
    else:
        # Insert new user into the database
        make_admin = db.execute(
            "INSERT INTO users (oauth_id, name, email, picture, oauth_provider) VALUES (?, ?, ?, ?, ?);",
            session["oauth_id"],
            session["name"],
            session["email"],
            session["picture"],
            "Google",
        )

        # Make first user admin
        if make_admin[0]["id"] == 1:
            db.execute("UPDATE users SET is_admin = TRUE WHERE id = ?;", make_admin)
            session["admin"] = True

        # Retrieve the last inserted id and store in session
        session["user_id"] = make_admin[0]["id"]

    # Redirect the user
    return redirect("/")


#  Add Github OAuth here ///////////
@app.route("/github-login")
def github_oauth():
    # Redirect to GitHub's OAuth page
    github_auth_url = (
        f"{GITHUB_AUTHORIZE_URL}?client_id={GITHUB_CLIENT_ID}&scope=read:user"
    )
    return redirect(github_auth_url)

@app.route("/github-callback")
def githubCallback():
    # Retrieve the code from GitHub's response
    code = request.args.get("code")
    if not code:
        return "Error: no code returned by GitHub", 400

    # Exchange the code for an access token
    token_response = requests.post(
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
        },
    )
    token_json = token_response.json()
    access_token = token_json.get("access_token")

    if not access_token:
        return "Error: no access token received from GitHub", 400

    # Use the access token to get user information
    user_response = requests.get(
        GITHUB_API_URL, headers={"Authorization": f"token {access_token}"}
    )
    user_json = user_response.json()

    # Store user info in session
    session["oauth_id"] = user_json.get("id")
    session["name"] = user_json.get("name")
    session["email"] = user_json.get("email")
    session["picture"] = user_json.get("avatar_url")

    # Check if user exists in the database
    existing_user = db.execute(
        "SELECT id, is_admin FROM users WHERE oauth_id = ? AND oauth_provider = 'GitHub';",
        session["oauth_id"]
    )

    # If the user exists, store user_id in session
    if existing_user:
        session["user_id"] = existing_user[0]["id"]
        session["admin"] = existing_user[0]["is_admin"]
    else:
        # Insert new user into the database
        try:
            new_user = db.execute(
                "INSERT INTO users (oauth_id, name, email, picture, oauth_provider) VALUES (?, ?, ?, ?, ?);",
                session["oauth_id"],
                session["name"],
                session["email"],
                session["picture"],
                "GitHub",
            )
        except Exception as e:
            error_message = str(e)
            if "duplicate key value violates unique constraint" in error_message:
                error_message = "Email already exists. Please login with your existing account."
            # Handle the error, e.g., render an error page or redirect
            return render_template("error.html", error_message=error_message), 400
        
        # Make the first user admin
        if new_user[0]["id"] == 1:
            db.execute("UPDATE users SET is_admin = TRUE WHERE id = ?;", new_user[0]["id"])
            session["admin"] = True

        # Retrieve last inserted user_id and store in session
        session["user_id"] = new_user[0]["id"]

    # Redirect to the index page
    return redirect(url_for("index"))

# End Github OAuth//////////////////////


# Logout route
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# Index route
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    # Make variable writeable
    global question_bank

    # Clear old sessions if any
    clear_selected_sessions()

    if request.method == "POST":

        question_bank.clear()

        # Validate users input
        if not request.form.get("region"):
            return apology("must provide region", 403)
        session["region"] = request.form.get("region")
        if not request.form.get("start"):
            return apology("must provide Start Number", 403)
        start = int(request.form.get("start"))

        # Initialize app to use Sessions
        session["score_tracker"] = []
        session["current_num"] = 0
        session["score"] = 0
        session["fails"] = []
        session["answers"] = []
        session["start"] = start - 1
        session["current_question_index"] = start - 1

        if request.form.get("region") in MCQ_REGIONS:
            # Load the question bank from the JSON file
            posting, _, subject = session["region"].lower().split(" ")
            # populate second posting at least
            if posting != "first":
                return apology(
                    "Sorry Only first posting available yet", 400
                )  # Acept only first posting for now
            with open(f"bank/{posting}_{subject}.json", encoding="utf-8") as f:
                question_bank = json.load(f)

            if not (1 <= start <= len(question_bank)):
                return apology("Start number out of range", 403)

            if subject in triads:
                session["region"] = f"{session['region']} PATHOLOGY"
            disable_next = True if start == len(question_bank) else False

            # Check if User is in exam mode
            if request.form.get("exam_mode") == "On":
                return render_template(
                    "exam_mcq.html",
                    questions=question_bank[session["current_question_index"]],
                    current_question_index=session["current_question_index"],
                    total_quiz=len(question_bank),
                    zip=zip,
                    disable_next=disable_next,
                    disable_previous=True,
                    region=session["region"].title(),
                )
            return render_template(
                "mcquiz.html",
                questions=question_bank[session["current_question_index"]],
                current_question_index=session["current_question_index"],
                current_score=session["score"],
                total_quiz=len(question_bank),
                disable_next=disable_next,
                disable_previous=True,
                region=session["region"].title(),
            )

        else:
            # Load the question bank from the JSON file
            with open(f"bank/{session['region']}.json") as f:
                question_bank = json.load(f)
            disable_next = True if start == len(question_bank) else False
            if not (1 <= start <= len(question_bank)):
                return apology("Start number out of range", 403)

            # Check if User is in exam mode
            if request.form.get("exam_mode") == "On":
                return render_template(
                    "exam_quiz.html",
                    questions=question_bank[session["current_question_index"]],
                    disable_next=disable_next,
                    disable_previous=True,
                    total_quiz=len(question_bank),
                    current_question_index=session["current_question_index"],
                    region=session["region"],
                )
            return render_template(
                "quiz.html",
                questions=question_bank[session["current_question_index"]],
                disable_next=disable_next,
                disable_previous=True,
                total_quiz=len(question_bank),
                current_question_index=session["current_question_index"],
                current_num=session["current_num"],
                current_score=session["score"],
                region=session["region"],
            )

    question_bank.clear()
    return render_template("index.html", regions=REGIONS, mcq_regions=MCQ_REGIONS)


@app.route("/next", methods=["POST"])
def next_question():
    # Get Users answer
    user_answer = request.form.get("proceed").strip()

    # Check answer, if correct add score else pass
    Current_answer = question_bank[session["current_question_index"]]["answer"]

    if user_answer == Current_answer:
        session["score"] += 1
        session["score_tracker"].append(1)
    else:
        session["fails"].append(
            {
                "Question_failed": session["current_question_index"],
                "answer": Current_answer,
            }
        )
        session["score_tracker"].append(0)

    # Update question index and move to next question
    session["current_question_index"] += 1
    session["current_num"] = session["current_num"] + 5
    return render_template(
        "quiz.html",
        questions=question_bank[session["current_question_index"]],
        disable_next=session["current_question_index"] == len(question_bank) - 1,
        disable_previous=False,
        total_quiz=len(question_bank),
        current_question_index=session["current_question_index"],
        current_num=session["current_num"],
        current_score=session["score"],
        region=session["region"],
    )


@app.route("/previous", methods=["POST"])
def previous_question():
    if session["score_tracker"][-1] == 1:
        session["score"] -= 1
    session["score_tracker"].pop()

    session["current_question_index"] -= 1
    session["current_num"] = session["current_num"] - 5
    return render_template(
        "quiz.html",
        questions=question_bank[session["current_question_index"]],
        disable_next=False,
        total_quiz=len(question_bank),
        disable_previous=session["current_question_index"] == session["start"],
        current_question_index=session["current_question_index"],
        current_num=session["current_num"],
        current_score=session["score"],
        region=session["region"],
    )


@app.route("/next_mcq", methods=["POST"])
def next_mcq_question():
    session["answers"].clear()
    track_fails = []

    # Append users answers to list
    for n in range(len(question_bank[session["current_question_index"]]["answer"])):
        if not request.form.get(f"group{n+1}"):
            session["answers"].append("Z")
        elif request.form.get(f"group{n+1}"):
            session["answers"].append(request.form.get(f"group{n+1}"))

    for n in range(len(question_bank[session["current_question_index"]]["answer"])):
        if (
            session["answers"][n]
            == question_bank[session["current_question_index"]]["answer"][n]
        ):
            session["score"] += 1
            session["score_tracker"].append(1)
        elif session["answers"][n] == "Z":
            session["score_tracker"].append(0)
            track_fails.append(n)
        else:
            session["score_tracker"].append(0)
            track_fails.append(n)
    if track_fails:
        session["fails"].append(
            {
                "Question_failed": session["current_question_index"],
                "position": track_fails,
            }
        )
    session["current_question_index"] += 1

    return render_template(
        "mcquiz.html",
        questions=question_bank[session["current_question_index"]],
        current_question_index=session["current_question_index"],
        current_score=session["score"],
        total_quiz=len(question_bank),
        region=session["region"],
        disable_previous=False,
        disable_next=session["current_question_index"] == len(question_bank) - 1,
    )


@app.route("/previous_mcq", methods=["POST"])
def previous_mcq_question():
    prevNum = session["current_question_index"] - 1
    for n in range(-1, -len(question_bank[prevNum]["answer"]) - 1, -1):
        if session["score_tracker"][n] == 1:
            session["score"] -= 1
    for _ in range(len(question_bank[prevNum]["answer"])):
        session["score_tracker"].pop()

    session["current_question_index"] -= 1

    return render_template(
        "mcquiz.html",
        questions=question_bank[session["current_question_index"]],
        disable_next=False,
        total_quiz=len(question_bank),
        disable_previous=session["current_question_index"] == session["start"],
        current_question_index=session["current_question_index"],
        current_score=session["score"],
        region=session["region"],
    )


""" Exam Mode Starts here, this mode allows User to see questions and answers without answering anything """


@app.route("/next_exam_mcq", methods=["POST"])
def next_exam_mcq():
    session["current_question_index"] += 1
    return render_template(
        "exam_mcq.html",
        questions=question_bank[session["current_question_index"]],
        current_question_index=session["current_question_index"],
        total_quiz=len(question_bank),
        zip=zip,
        region=session["region"],
        disable_previous=False,
        disable_next=session["current_question_index"] == len(question_bank) - 1,
    )


@app.route("/next_exam_quiz", methods=["POST"])
def next_exam_quiz():
    # Update question index and move to next question
    session["current_question_index"] += 1
    session["current_num"] = session["current_num"] + 5
    return render_template(
        "exam_quiz.html",
        questions=question_bank[session["current_question_index"]],
        disable_next=session["current_question_index"] == len(question_bank) - 1,
        disable_previous=False,
        total_quiz=len(question_bank),
        current_question_index=session["current_question_index"],
        current_num=session["current_num"],
        current_score=session["score"],
        region=session["region"],
    )


@app.route("/previous_exam_mcq", methods=["POST"])
def previous_exam_mcq():

    session["current_question_index"] -= 1

    return render_template(
        "exam_mcq.html",
        questions=question_bank[session["current_question_index"]],
        disable_next=False,
        disable_previous=session["current_question_index"] == session["start"],
        current_question_index=session["current_question_index"],
        total_quiz=len(question_bank),
        zip=zip,
        region=session["region"],
    )


@app.route("/previous_exam_quiz", methods=["POST"])
def previous_exam_quiz():
    session["current_question_index"] -= 1
    session["current_num"] = session["current_num"] - 5
    return render_template(
        "exam_quiz.html",
        questions=question_bank[session["current_question_index"]],
        disable_next=False,
        total_quiz=len(question_bank),
        disable_previous=session["current_question_index"] == session["start"],
        current_question_index=session["current_question_index"],
        current_num=session["current_num"],
        region=session["region"],
    )


@app.route("/end_of_mcq", methods=["POST"])
def end_mcq():
    """This route will displays users Score and percentage Over a 100% for the MCQs Done"""

    session["answers"].clear()
    track_fails = []
    totalFails = []

    # Append users answers to list
    for n in range(len(question_bank[session["current_question_index"]]["answer"])):
        if not request.form.get(f"group{n+1}"):
            session["answers"].append("Z")
        elif request.form.get(f"group{n+1}"):
            session["answers"].append(request.form.get(f"group{n+1}"))

    for n in range(len(question_bank[session["current_question_index"]]["answer"])):
        if (
            session["answers"][n]
            == question_bank[session["current_question_index"]]["answer"][n]
        ):
            session["score"] += 1
            session["score_tracker"].append(1)
        elif session["answers"][n] == "Z":
            session["score_tracker"].append(0)
            track_fails.append(n)
        else:
            session["score_tracker"].append(0)
            track_fails.append(n)
    if track_fails:
        session["fails"].append(
            {
                "Question_failed": session["current_question_index"],
                "position": track_fails,
            }
        )

    session["answers"].clear()
    # Get the question failed and corrections, remove question passed
    for quest in session["fails"]:
        new_question = question_bank[quest["Question_failed"]]
        new_question["Question_number"] = quest["Question_failed"] + 1
        indices_to_keep = quest["position"]
        kept_options = [new_question["options"][i] for i in indices_to_keep]
        kept_answers = [new_question["answer"][i] for i in indices_to_keep]
        new_question["options"] = kept_options
        new_question["answer"] = kept_answers

        totalFails.append(new_question)

    # Get the medical score
    totalQ = len(session["score_tracker"])
    medScore = 0
    for question in session["fails"]:
        medScore = medScore + len(question["position"])
    current_medical_score = session["score"] - (medScore / 2)

    per = round(current_medical_score / len(session["score_tracker"]) * 100, 2)

    session["answers"].clear()

    score = session["score"]
    region = session["region"]

    # Save users atempt in database~
    start_question = session["start"] + 1
    end_question = session["current_question_index"] + 1

    db.execute(
        """
        INSERT INTO scoresheet (candidate_id, score, course, format, start_quest, end_quest) VALUES (?, ?, ?, ?, ?, ?);""",
        session["user_id"],
        current_medical_score,
        region,
        "MCQ",
        start_question,
        end_question,
    )

    # Insert into the streak_winner table if Highest Score else ignore
    try:
        # Check if user score is worthy: Must have answered at least 20 MCQ questions from any course in one go and scored above 50%
        if candidate_rows := db.execute(mcq_query, (session["user_id"],)):
            # Process worthy candidate_row
            candidate_row = candidate_rows[0]
            streak = db.execute(
                "SELECT COUNT(DISTINCT DATE(time)) AS num_days FROM scoresheet WHERE candidate_id = ?;",
                candidate_row["candidate_id"],
            )
            # TODO avoid redundancy ON CONFLICT not yet understood, i only want this to ignore if all unique constrains conflicts but if so much as one doesn't conflict then insert
            db.execute(
                """
                INSERT INTO streak_winner (user_id, highest_score, course, format, total_quests, streak) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (course, format, highest_score, total_quests) DO NOTHING;""",
                candidate_row["candidate_id"],
                candidate_row["score"],
                candidate_row["course"],
                candidate_row["format"],
                candidate_row["total_questions"],
                streak[0]["num_days"],
            )
    except sqlite3.Error as e:
        return f"{e}"

    # Clear sessions relevant to test but keep user login in
    clear_selected_sessions()

    return render_template(
        "end.html",
        totalFails=totalFails,
        score=score,
        scoreN=current_medical_score,
        per=per,
        totalQ=totalQ,
        region=region,
    )


@app.route("/end", methods=["POST"])
def end():
    """This route will displays users Score and percentage Over a 100%"""

    # Get Users answer
    user_answer = request.form.get("endquiz").strip()

    # Check answer, if correct add score else pass
    Current_answer = question_bank[session["current_question_index"]]["answer"]
    if user_answer == Current_answer:
        session["score"] += 1
        session["score_tracker"].append(1)
    else:
        session["fails"].append(
            {
                "Question_failed": session["current_question_index"],
                "answer": Current_answer,
            }
        )
        session["score_tracker"].append(0)

    totalQ = len(session["score_tracker"])

    current_medical_score = session["score"] - (len(session["fails"]) / 2)

    per = current_medical_score / len(session["score_tracker"]) * 100

    score = session["score"]
    region = session["region"]
    fails = session["fails"]

    #  Save users atempt in database
    start_question = session["start"] + 1
    end_question = session["current_question_index"] + 1

    db.execute(
        """
        INSERT INTO scoresheet (candidate_id, score, course, format, start_quest, end_quest) VALUES (?, ?, ?, ?, ?, ?);""",
        session["user_id"],
        current_medical_score,
        region,
        "Best Option",
        start_question,
        end_question,
    )

    # Insert into the streak_winner table if Highest Score else ignore
    try:
        # Check if user score is worthy: Must have answered at least 50 Best Option questions from any course in one go and scored above 50%
        if candidate_rows := db.execute(query, (session["user_id"],)):
            # Process worthy candidate_row
            candidate_row = candidate_rows[0]
            streak = db.execute(
                "SELECT COUNT(DISTINCT DATE(time)) AS num_days FROM scoresheet WHERE candidate_id = ?;",
                candidate_row["candidate_id"],
            )
            # TODO avoid redundancy ON CONFLICT not yet understood, i only want this to ignore if all unique constrains conflicts but if so much as one doesn't conflict then insert
            db.execute(
                """
                INSERT INTO streak_winner (user_id, highest_score, course, format, total_quests, streak) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (course, format, highest_score, total_quests) DO NOTHING;""",
                candidate_row["candidate_id"],
                candidate_row["score"],
                candidate_row["course"],
                candidate_row["format"],
                candidate_row["total_questions"],
                streak[0]["num_days"],
            )
    except sqlite3.Error as e:
        return f"{e}"

    # Clear sessions relevant to test but keep user login in
    clear_selected_sessions()

    return render_template(
        "end.html",
        fails=fails,
        score=score,
        scoreN=current_medical_score,
        per=per,
        totalQ=totalQ,
        region=region,
    )


@app.route("/add_admin", methods=["GET", "POST"])
def make_admin():

    # Check if the admin status is already True for the first user ONLY
    if session["user_id"] == 1 and session["admin"] is False:
        db.execute("UPDATE users SET is_admin = TRUE WHERE id = 1;")
        session["admin"] = True
    print(session["admin"])
    # Make people admin
    if request.method == "POST":
        id = int(request.form.get("id"))
        name = request.form.get("name")
        print(id)
        print(name)
        db.execute("UPDATE users SET is_admin = TRUE WHERE id = ?;", id)
        session["admin"] = True

        return f"{name} is now an Admin"

    # Get page for user
    users = db.execute("SELECT * FROM users;")

    return render_template("change_admin.html", users=users)


@app.route("/de_admin", methods=["POST"])
def de_admin():
    if request.method == "POST":
        id = int(request.form.get("id"))
        name = request.form.get("name")
        db.execute("UPDATE users SET is_admin = False WHERE id = ?;", id)
        session["admin"] = False
        return f"{name} is no longer an Admin"


@app.route("/profile")
def user_profile():
    print(session["user_id"])
    students = db.execute(
        "SELECT * FROM scoresheet WHERE candidate_id = ?;", session["user_id"]
    )
    return render_template("profile.html", students=students)


@app.route("/tower")
def tower():
    """Display candidates information"""
    print(session["user_id"])
    # Get the data from streak_winner table
    db.execute("BEGIN TRANSACTION")
    candidates = db.execute("SELECT * FROM tower;")
    db.execute("COMMIT")

    # Cruise and self hype
    king = {
        "name": "rabboni",
        "rank": "King of the tower",
        "course": "All",
        "format": "MCQs and Best Choice",
        "total_quests": "All",
        "score": 1000,
        "streak": "365 days",
    }
    # Return Page of winners in ranks
    return render_template("tower.html", candidates=candidates, king=king)
