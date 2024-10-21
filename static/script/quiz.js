document.addEventListener("DOMContentLoaded", function() {
    const radioButtons = document.querySelectorAll('input[name="answer"]');
    selectedAnswer = "";

    radioButtons.forEach(radio => {
        radio.addEventListener("change", function() {
            const selectedAnswer = this.value;
            document.getElementById("next_answer").value = selectedAnswer;
            document.getElementById("end_answer").value = selectedAnswer;
            console.log(`Answer ${selectedAnswer}`);
        });
    });


});