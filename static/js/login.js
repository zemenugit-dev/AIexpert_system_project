
// =========================
// EMAIL VALIDATION
// =========================
function validateEmail() {
    let email = document.getElementById("email").value;
    let msg = document.getElementById("emailMsg");

    let pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!pattern.test(email)) {
        msg.innerText = "Enter valid email address";
        return false;
    } else {
        msg.innerText = "";
        return true;
    }
}

// =========================
// PASSWORD VALIDATION
// =========================
function validatePassword() {
    let pass = document.getElementById("password").value;
    let msg = document.getElementById("passMsg");

    if (pass.length < 6) {
        msg.innerText = "Password must be at least 6 characters";
        return false;
    } else {
        msg.innerText = "";
        return true;
    }
}

// =========================
// TOGGLE PASSWORD
// =========================
function togglePassword() {
    let pass = document.getElementById("password");

    if (pass.type === "password") {
        pass.type = "text";
    } else {
        pass.type = "password";
    }
}

// =========================
// FORM VALIDATION
// =========================
function validateForm() {
    return validateEmail() && validatePassword();
}