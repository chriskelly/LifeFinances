(function () {
  function syncBoundary(control) {
    const kind = control.querySelector(".boundary-kind").value;
    control.querySelectorAll(".boundary-part").forEach(function (part) {
      const kinds = (part.dataset.kinds || "").split(" ");
      part.hidden = kinds.indexOf(kind) === -1;
    });
  }

  function rowChildren(container) {
    return Array.prototype.filter.call(container.children, function (child) {
      return child.classList.contains("row");
    });
  }

  function reindex(container) {
    const prefix = container.dataset.prefix;
    const pattern = new RegExp(prefix + "\\[\\d+\\]");
    rowChildren(container).forEach(function (row, index) {
      row.querySelectorAll("[name]").forEach(function (field) {
        field.name = field.name.replace(pattern, prefix + "[" + index + "]");
      });
      row.querySelectorAll(".rows").forEach(reindex);
    });
  }

  function initAll() {
    document.querySelectorAll(".boundary-control").forEach(syncBoundary);
    document.querySelectorAll(".rows").forEach(reindex);
  }

  document.addEventListener("change", function (event) {
    if (event.target.classList.contains("boundary-kind")) {
      syncBoundary(event.target.closest(".boundary-control"));
    }
  });

  document.addEventListener("click", function (event) {
    const addButton = event.target.closest("[data-add-row]");
    if (addButton) {
      event.preventDefault();
      const container = addButton.closest(".rows");
      const template = container.querySelector(":scope > .row-template");
      const clone = template.content.firstElementChild.cloneNode(true);
      container.insertBefore(clone, template);
      reindex(container);
      clone.querySelectorAll(".boundary-control").forEach(syncBoundary);
      container
        .closest("form")
        .dispatchEvent(new Event("change", { bubbles: true }));
      return;
    }
    const removeButton = event.target.closest("[data-remove-row]");
    if (removeButton) {
      event.preventDefault();
      const row = removeButton.closest(".row");
      const container = row.parentElement;
      const form = row.closest("form");
      row.remove();
      reindex(container);
      form.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });

  document.addEventListener("DOMContentLoaded", initAll);
  document.body.addEventListener("htmx:afterSettle", initAll);
})();
