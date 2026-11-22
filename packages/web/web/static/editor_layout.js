(function () {
  const STORAGE_KEY = "lifeFinances.panes";
  const root = document.documentElement;
  const button = document.getElementById("toggle-editor");
  if (!button) return;

  const chevron = button.querySelector(".pane-rail-chevron");

  // Shares the key and editorHidden meaning with the inline bootstrap in index.html.
  function readPanes() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      return parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? parsed
        : {};
    } catch (error) {
      /* storage may be blocked or corrupt; fall back to defaults */
      return {};
    }
  }

  function sync() {
    const hidden = root.classList.contains("editor-hidden");
    button.setAttribute("aria-expanded", String(!hidden));
    button.title = hidden ? "Expand editor pane" : "Collapse editor pane";
    if (chevron) chevron.textContent = hidden ? "›" : "‹";
  }

  function save() {
    try {
      const panes = readPanes();
      panes.editorHidden = root.classList.contains("editor-hidden");
      localStorage.setItem(STORAGE_KEY, JSON.stringify(panes));
    } catch (error) {
      /* storage may be blocked or full; the toggle still works for this page */
    }
  }

  function resizeChart() {
    window.requestAnimationFrame(function () {
      if (typeof Plotly === "undefined") return;
      const chart = document.getElementById("results-chart");
      if (!chart || !chart.classList.contains("js-plotly-plot")) return;
      Plotly.Plots.resize(chart);
    });
  }

  sync();

  button.addEventListener("click", function () {
    root.classList.toggle("editor-hidden");
    sync();
    save();
    resizeChart();
  });
})();
