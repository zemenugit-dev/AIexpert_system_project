const form = document.getElementById("diagnosisForm");

form.addEventListener("submit", function(e){

    const questions = document.querySelectorAll(".question-card");

    let valid = true;

    questions.forEach(question => {

        const checked = question.querySelector("input[type='radio']:checked");

        if(!checked){
            valid = false;

            question.style.border = "2px solid red";
        }
        else{
            question.style.border = "2px solid #22c55e";
        }

    });

    if(!valid){

        e.preventDefault();

        alert("Please answer all questions.");
    }

});