
document.addEventListener("DOMContentLoaded", () => {
    const examButton = document.querySelector("#exam_mode");
    let examMode = "Off";

    examButton.addEventListener("click", () => {
        examMode = examMode === "Off" ? "On" : "Off";
        examButton.innerHTML = examMode;
        examButton.style.backgroundColor = examMode === "On" ? "red" : "#4c77af";
        console.log(`Exam Mode: ${examMode}`);
        document.getElementById("mode_choice1").value = examMode;
        document.getElementById("mode_choice2").value = examMode;
    });

});