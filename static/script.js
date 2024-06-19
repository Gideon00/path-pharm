
// Best Choice

document.addEventListener("DOMContentLoaded", function() {
    const questionDisplay = document.querySelector(".question-display");
    const pillBottle = document.querySelector(".pill-bottle");
    const pill = document.querySelector("#pill");
    const submitButton = document.querySelector("#toggle");
    const examButton = document.querySelector("#exam_mode");
    let exam_mode = "Off";

    let selectedAnswer = null;

    
    examButton.addEventListener("click", () => {
        if (examButton.innerHTML === "Off") {
            examButton.innerHTML = "On";
            exam_mode = "On";
            examButton.style.backgroundColor = "red";
        } else {
            examButton.innerHTML = "Off";
            exam_mode = "Off";
            examButton.style.backgroundColor = "#4c77af";
        }
        console.log(`Exam Mode: ${exam_mode}`);
        document.getElementById("mode_choice1").value = exam_mode;
        document.getElementById("mode_choice2").value = exam_mode;
    });

    submitButton.addEventListener("click", () => {
        let score = document.getElementById("score");
        if (score.style.visibility == "hidden")
        {
            score.style.visibility = "visible";
            submitButton.innerHTML = "Hide Score";
        }
        else
        {
            score.style.visibility = "hidden"
            submitButton.innerHTML = "See Score";
        }
        console.log(`Answer submitted: ${selectedAnswer}`);
        
    });
    
    questionDisplay.addEventListener("click", (e) => {
        if (e.target.tagName === "INPUT") {
            const answer = e.target.nextElementSibling.textContent;
            selectedAnswer = answer;
            document.getElementById("next_answer").value = selectedAnswer
            document.getElementById("end_answer").value = selectedAnswer
            fillPillBottle();
        }
    });
    

    function fillPillBottle() {
        if (selectedAnswer.length > 0) {
          pill.style.opacity = 1;
          pillBottle.classList.add("filled");
        } else {
          pill.style.opacity = 0;
          pillBottle.classList.remove("filled");
        }
    }

});
