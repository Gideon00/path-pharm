
document.addEventListener("DOMContentLoaded", () => {
    const examButton = document.querySelector(".myBtn");
    let examMode = "Off";

    examButton.addEventListener("click", () => {
        examMode = examMode === "Off" ? "On" : "Off";
        examButton.innerHTML = examMode;
        examButton.style.backgroundColor = examMode === "On" ? "rgb(151, 87, 2)" : "rgb(245, 204, 150)";
        console.log(`Exam Mode: ${examMode}`);
        document.getElementById("mode_choice1").value = examMode;
        document.getElementById("mode_choice2").value = examMode;
    });

});
