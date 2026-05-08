// =========================
// LIVE SEARCH FILTER
// =========================
document.addEventListener("DOMContentLoaded", function () {

    const searchInput = document.getElementById("search");

    searchInput.addEventListener("keyup", function () {

        let filter = searchInput.value.toLowerCase();

        let table = document.getElementById("diseaseTable");
        let rows = table.getElementsByTagName("tr");

        for (let i = 1; i < rows.length; i++) {

            let cell = rows[i].getElementsByTagName("td")[1];

            if (cell) {

                let text = cell.textContent || cell.innerText;

                if (text.toLowerCase().indexOf(filter) > -1) {
                    rows[i].style.display = "";
                } else {
                    rows[i].style.display = "none";
                }
            }
        }
    });

});