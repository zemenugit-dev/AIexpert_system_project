function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");

    if (sidebar.style.width === "0px") {
        sidebar.style.width = "220px";
    } else {
        sidebar.style.width = "0px";
    }
}