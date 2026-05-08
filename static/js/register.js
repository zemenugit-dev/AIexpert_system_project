
// ==========================
// NAME VALIDATION
// ==========================
function validateName() {
    let name = document.getElementById("name").value;
    let msg = document.getElementById("nameMsg");

    if (name.length < 5) {
        msg.innerText = "Name must be at least 5 characters";
        return false;
    } else {
        msg.innerText = "";
        return true;
    }
}

// ==========================
// EMAIL VALIDATION
// ==========================
function validateEmail() {
    let email = document.getElementById("email").value;
    let msg = document.getElementById("emailMsg");

    let pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!pattern.test(email)) {
        msg.innerText = "Invalid email format";
        return false;
    } else {
        msg.innerText = "";
        return true;
    }
}

// ==========================
// PASSWORD VALIDATION
// ==========================
function validatePassword() {
    let password = document.getElementById("password").value;
    let msg = document.getElementById("passMsg");

    let pattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{10,}$/;

    if (!pattern.test(password)) {
        msg.innerText = "Min 10 chars, upper, lower, number & special char";
        return false;
    } else {
        msg.innerText = "";
        return true;
    }
}

// ==========================
// SHOW / HIDE PASSWORD
// ==========================
function togglePassword() {
    let pass = document.getElementById("password");

    if (pass.type === "password") {
        pass.type = "text";
    } else {
        pass.type = "password";
    }
}

// ==========================
// FORM VALIDATION ON SUBMIT
// ==========================
function validateForm() {
    return validateName() && validateEmail() && validatePassword();
}