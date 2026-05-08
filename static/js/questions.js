// =========================
// LIVE SEARCH FUNCTION
// =========================
document.getElementById("searchBox").addEventListener("keyup", function () {

    let value = this.value.toLowerCase();

    let rows = document.querySelectorAll("#questionTable tbody tr");

    rows.forEach(row => {

        let question = row.cells[1].innerText.toLowerCase();

        if (question.includes(value)) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }

    });

});