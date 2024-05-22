
// Best Choice

document.addEventListener("DOMContentLoaded", function() {
    const questionDisplay = document.querySelector(".question-display");
    const pillBottle = document.querySelector(".pill-bottle");
    const pill = document.querySelector("#pill");
    const submitButton = document.querySelector("#toggle");

    let selectedAnswer = null;

    questionDisplay.addEventListener("click", (e) => {
        if (e.target.tagName === "INPUT") {
            const answer = e.target.nextElementSibling.textContent;
            selectedAnswer = answer;
            document.getElementById("next_answer").value = selectedAnswer
            document.getElementById("end_answer").value = selectedAnswer
            fillPillBottle();
        }
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