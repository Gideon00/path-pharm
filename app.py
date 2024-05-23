from flask import Flask, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
import json

from helpers import apology

app = Flask(__name__)

# Config sessions
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

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

question_bank = []

# Define the custom Jinja2 filter function
def number_to_upper(num):
    return chr(ord("A") + num - 1) if 1 <= num <= 26 else ""

# Register the filter function with Jinja2 environment
app.jinja_env.filters["number_to_upper"] = number_to_upper

@app.route("/", methods=["GET", "POST"])
def index():
    # Make variable writeable
    global question_bank

    # Clear old sessions if any
    session.clear()

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
            # TODO populate second posting at least
            if posting != "first":
                return apology("Sorry Only first posting available", 400)  #Acept only first posting for now
            with open(f"bank/{posting}_{subject}.json", encoding="utf-8") as f:
                question_bank = json.load(f)
            if start not in range(len(question_bank)):
                return apology("Start number out of range", 403)
            if subject in triads:
                session["region"] = f"{session["region"]} PATHOLOGY"
            return render_template("mcquiz.html", 
                                   questions=question_bank[session["current_question_index"]], 
                                   current_question_index=session["current_question_index"],
                                   score=session["score"],
                                   disable_next=False, 
                                   disable_previous=True, 
                                   region=session["region"].title())

        else:
            # Load the question bank from the JSON file
            with open(f"bank/{session['region']}.json") as f:
                question_bank = json.load(f)
            if start not in range(len(question_bank)):
                return apology("Start number out of range", 403)
            return render_template("quiz.html", 
                                   questions=question_bank[session["current_question_index"]], 
                                   disable_next=False,
                                   disable_previous=True, 
                                   current_question_index=session["current_question_index"], 
                                   current_num=session["current_num"], score=session["score"], 
                                   region=session["region"])
   
    question_bank.clear()
    return render_template("index.html", regions=REGIONS, mcq_regions=MCQ_REGIONS)

    
@app.route("/next", methods=["POST"])
def next_question():
    # Get Users answer
    answer = request.form.get("proceed")
    _, user_answer = answer.split(".")
    user_answer = user_answer.strip()

    # Check answer, if correct add score else pass
    Current_answer = question_bank[session["current_question_index"]]["answer"]
    if user_answer == Current_answer:
        session["score"] += 1
        session["score_tracker"].append(1)
    else:
        session["fails"].append({"Question_failed": session["current_question_index"], "answer": Current_answer})
        session["score_tracker"].append(0)

    # Update question index and move to next question
    session["current_question_index"] += 1
    session["current_num"] = session["current_num"] + 5
    return render_template("quiz.html", questions=question_bank[session["current_question_index"]], 
                           disable_next=session["current_question_index"] == len(question_bank) - 1, 
                           disable_previous=False,
                           current_question_index=session["current_question_index"], 
                           current_num=session["current_num"], score=session["score"], region=session["region"])

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
        if session["answers"][n] == question_bank[session["current_question_index"]]["answer"][n]:
            session["score"] += 1
            session["score_tracker"].append(1)
        elif session["answers"][n] == "Z":
            session["score_tracker"].append(0)
            track_fails.append(n)
        else:
            session["score_tracker"].append(0)
            track_fails.append(n)
    if track_fails:
        session["fails"].append({"Question_failed": session["current_question_index"], "position": track_fails})
    session["current_question_index"] += 1

    return render_template("mcquiz.html", 
                           questions=question_bank[session["current_question_index"]],
                           current_question_index=session["current_question_index"],
                           score=session["score"], 
                           region=session["region"],
                           disable_previous=False, 
                           disable_next=session["current_question_index"] == len(question_bank) - 1)


@app.route("/previous", methods=["POST"])
def previous_question():
    if session["score_tracker"][-1] == 1:
        session["score"] -= 1
        session["score_tracker"].pop()

    session["current_question_index"] -= 1
    session["current_num"] = session["current_num"] - 5
    return render_template("quiz.html", 
                           questions=question_bank[session["current_question_index"]], 
                           disable_next=False, 
                           disable_previous=session["current_question_index"] == session["start"], 
                           current_question_index=session["current_question_index"], 
                           current_num=session["current_num"], 
                           score=session["score"], 
                           region=session["region"])

@app.route("/previous_mcq", methods=["POST"])
def previous_mcq_question():
    prevNum = session["current_question_index"] - 1
    
    for n in range(len(question_bank[prevNum]["answer"])):
        if session["score_tracker"][n] == 1:
            session["score"] -= 1
    for _ in range(len(question_bank[prevNum]["answer"])):
        session["score_tracker"].pop()
    
    session["current_question_index"] -= 1
    
    return render_template("mcquiz.html", 
                           questions=question_bank[session["current_question_index"]], 
                           disable_next=False,
                           disable_previous=session["current_question_index"] == session["start"], 
                           current_question_index=session["current_question_index"],
                           score=session["score"], 
                           region=session["region"])

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
        if session["answers"][n] == question_bank[session["current_question_index"]]["answer"][n]:
            session["score"] += 1
            session["score_tracker"].append(1)
        elif session["answers"][n] == "Z":
            session["score_tracker"].append(0)
            track_fails.append(n)
        else:
            session["score_tracker"].append(0)
            track_fails.append(n)
    if track_fails:
        session["fails"].append({"Question_failed": session["current_question_index"], "position": track_fails}) 
    
    session["answers"].clear()
    # Get the question failed and corrections, remove question passed
    for quest in session["fails"]:
        new_question = question_bank[quest["Question_failed"]]
        new_question["Question_number"] = quest["Question_failed"]+1
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
    return render_template("end.html",
                           totalFails=totalFails,
                           score=session["score"],
                           scoreN=current_medical_score, per=per,
                           totalQ=totalQ,
                           region=session["region"])


@app.route("/end", methods=["POST"])
def end():

    """ This route will displays users Score and percentage Over a 100% """
    
    # Get Users answer
    answer = request.form.get("endquiz")
    _, user_answer = answer.split(".")
    user_answer = user_answer.strip()

    # Check answer, if correct add score else pass
    Current_answer = question_bank[session["current_question_index"]]["answer"]
    if user_answer == Current_answer:
        session["score"] += 1
        session["score_tracker"].append(1)
    else:
        session["fails"].append({"Question_failed": session["current_question_index"], "answer": Current_answer})
        session["score_tracker"].append(0)

    # Update question index and move to next question
    session["current_question_index"] += 1
    session["current_num"] = session["current_num"] + 5

    totalQ = len(session["score_tracker"])

    current_medical_score = session["score"] - (len(session["fails"]) / 2)

    per = current_medical_score / len(session["score_tracker"]) * 100

    return render_template("end.html", fails=session["fails"],
                           score=session["score"],
                           scoreN=current_medical_score, per=per,
                           totalQ=totalQ,
                           region=session["region"])


