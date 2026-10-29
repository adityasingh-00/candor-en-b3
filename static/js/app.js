document.addEventListener("DOMContentLoaded", () => {
  const search = document.getElementById("seatSearch");
  const listToggle = document.getElementById("listToggle");
  const mapPanel = document.getElementById("mapPanel");
  const listPanel = document.getElementById("listPanel");
  const statusFilter = document.getElementById("statusFilter");
  const emptyState = document.getElementById("emptyState");

  function filterSeats() {
    const query = (search?.value || "").trim().toLowerCase();
    const status = statusFilter?.value || "";
    document.querySelectorAll(".seat[data-search]").forEach((seat) => {
      seat.hidden = !(seat.dataset.search || "").includes(query);
    });
    let visible = 0;
    document.querySelectorAll(".employee-row").forEach((row) => {
      const matches = (row.dataset.search || "").includes(query) &&
        (!status || row.dataset.status === status);
      row.hidden = !matches;
      if (matches) visible += 1;
    });
    if (emptyState) emptyState.hidden = visible !== 0;
  }

  search?.addEventListener("input", filterSeats);
  statusFilter?.addEventListener("change", filterSeats);
  listToggle?.addEventListener("click", () => {
    const showList = listPanel.hidden;
    listPanel.hidden = !showList;
    mapPanel.hidden = showList;
    listToggle.textContent = showList ? "Floor plan" : "List view";
    listToggle.setAttribute("aria-pressed", String(showList));
    if (showList) filterSeats();
  });
});
