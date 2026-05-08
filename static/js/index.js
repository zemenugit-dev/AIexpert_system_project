// ======================
// LOADER
// ======================

window.addEventListener("load", () => {

    setTimeout(() => {

        document.getElementById("loader").style.display = "none";

    }, 2500);

});


// ======================
// TYPING EFFECT
// ======================

const text =
    "Advanced AI Medical Diagnosis Platform";

let index = 0;

function typingEffect(){

    if(index < text.length){

        document.getElementById("typing-text").innerHTML +=
            text.charAt(index);

        index++;

        setTimeout(typingEffect, 80);
    }
}

typingEffect();


// ======================
// PARALLAX EFFECT
// ======================

document.addEventListener("mousemove", (e) => {

    const card =
        document.querySelector(".medical-card");

    let x =
        (window.innerWidth / 2 - e.pageX) / 30;

    let y =
        (window.innerHeight / 2 - e.pageY) / 30;

    card.style.transform =
        `rotateY(${x}deg) rotateX(${-y}deg)`;
});


// ======================
// BUTTON GLOW EFFECT
// ======================

const buttons =
    document.querySelectorAll(".btn");

buttons.forEach(btn => {

    btn.addEventListener("mouseenter", () => {

        btn.style.boxShadow =
            "0 0 30px rgba(0,255,213,0.8)";
    });

    btn.addEventListener("mouseleave", () => {

        btn.style.boxShadow = "none";
    });

});