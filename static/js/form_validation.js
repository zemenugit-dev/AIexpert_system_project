// =========================
// PASSWORD SHOW / HIDE TOGGLE
// =========================
function togglePassword(inputId, iconId) {

    const passwordInput = document.getElementById(inputId);
    const icon = document.getElementById(iconId);

    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
    } else {
        passwordInput.type = "password";
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
    }
}


// =========================
// NAME VALIDATION
// =========================
function validateName(inputId, msgId) {

    const name = document.getElementById(inputId).value.trim();
    const msg = document.getElementById(msgId);

    if (name.length < 5) {
        msg.innerText = "❌ Name must be at least 5 characters";
        msg.style.color = "red";
        return false;
    }

    msg.innerText = "✅ Valid name";
    msg.style.color = "green";
    return true;
}


// =========================
// EMAIL VALIDATION
// =========================
function validateEmail(inputId, msgId) {

    const email = document.getElementById(inputId).value.trim();
    const msg = document.getElementById(msgId);

    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!pattern.test(email)) {
        msg.innerText = "❌ Invalid email format";
        msg.style.color = "red";
        return false;
    }

    msg.innerText = "✅ Valid email";
    msg.style.color = "green";
    return true;
}


// =========================
// STRONG PASSWORD VALIDATION
// =========================
function validatePassword(inputId, msgId) {

    const password = document.getElementById(inputId).value;
    const msg = document.getElementById(msgId);

    const rules = [
        { test: password.length >= 10, msg: "❌ At least 10 characters" },
        { test: /[A-Z]/.test(password), msg: "❌ Add uppercase letter (A-Z)" },
        { test: /[a-z]/.test(password), msg: "❌ Add lowercase letter (a-z)" },
        { test: /[0-9]/.test(password), msg: "❌ Add number (0-9)" },
        { test: /[!@#$%^&*(),.?\":{}|<>]/.test(password), msg: "❌ Add special character" }
    ];

    for (let rule of rules) {
        if (!rule.test) {
            msg.innerText = rule.msg;
            msg.style.color = "red";
            return false;
        }
    }

    msg.innerText = "✅ Strong password";
    msg.style.color = "green";
    return true;
}


// =========================
// FORM SUBMIT VALIDATION (IMPORTANT FIX)
// =========================
function validateForm() {

    const nameOk = validateName("name", "nameMsg");
    const emailOk = validateEmail("email", "emailMsg");
    const passOk = validatePassword("password", "passMsg");

    if (!nameOk || !emailOk || !passOk) {
        alert("Please fix errors before submitting!");
        return false;
    }

    return true;
}