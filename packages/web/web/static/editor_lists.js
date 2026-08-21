(function () {
  const REMOVE_ROW_MESSAGE = "Remove this item? This cannot be undone.";
  const CLEAR_PENSION_MESSAGE =
    "Clear this pension? Service dates, claim age, and related settings will be removed.";
  const OVERWRITE_PENSION_MESSAGE =
    "Replace the custom pension table with CalSTRS 2% at 62? The existing age-factor table will be overwritten.";

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

  function maxSiblingIndex(container) {
    const prefix = container.dataset.prefix;
    const pattern = new RegExp(prefix + "\\[(\\d+)\\]");
    let max = -1;
    rowChildren(container).forEach(function (row) {
      row.querySelectorAll("[name]").forEach(function (field) {
        const match = field.name.match(pattern);
        if (match) {
          max = Math.max(max, parseInt(match[1], 10));
        }
      });
    });
    return max;
  }

  function setRowIndex(row, prefix, index) {
    const pattern = new RegExp(prefix + "\\[\\d+\\]");
    const replacement = prefix + "[" + index + "]";
    function rewrite(root) {
      root.querySelectorAll("[name]").forEach(function (field) {
        field.name = field.name.replace(pattern, replacement);
      });
    }
    rewrite(row);
    row.querySelectorAll("template").forEach(function (tpl) {
      rewrite(tpl.content);
    });
  }

  function initAll() {
    document.querySelectorAll(".boundary-control").forEach(syncBoundary);
  }

  document.addEventListener("change", function (event) {
    const target = event.target;
    if (target.classList.contains("boundary-kind")) {
      syncBoundary(target.closest(".boundary-control"));
      return;
    }
    if (target.matches("[data-confirm-partner-remove]")) {
      if (!target.checked) {
        const message = target.dataset.confirmMessage;
        if (!message || !window.confirm(message)) {
          target.checked = true;
          event.stopImmediatePropagation();
          return;
        }
      }
      const form = target.closest("form");
      if (form) {
        form
          .querySelectorAll(".partner-fields input, .partner-fields select")
          .forEach(function (el) {
            el.disabled = !target.checked;
          });
      }
      return;
    }
    if (target.matches("[data-pension-select]")) {
      const previous = target.dataset.previousValue || "";
      const next = target.value;
      const noneValue = target.dataset.pensionNone || "none";
      const calstrsValue = target.dataset.pensionCalstrs || "";
      const isCustom = target.dataset.pensionIsCustom === "true";
      if (previous !== noneValue && next === noneValue) {
        if (!window.confirm(CLEAR_PENSION_MESSAGE)) {
          target.value = previous;
          event.stopImmediatePropagation();
          return;
        }
      } else if (isCustom && next === calstrsValue) {
        if (!window.confirm(OVERWRITE_PENSION_MESSAGE)) {
          target.value = previous;
          event.stopImmediatePropagation();
          return;
        }
        target.dataset.pensionIsCustom = "false";
      }
      target.dataset.previousValue = target.value;
    }
  });

  document.addEventListener("click", function (event) {
    const addButton = event.target.closest("[data-add-row]");
    if (addButton) {
      event.preventDefault();
      const container = addButton.closest(".rows");
      const template = container.querySelector(":scope > .row-template");
      const nextIndex = maxSiblingIndex(container) + 1;
      const clone = template.content.firstElementChild.cloneNode(true);
      setRowIndex(clone, container.dataset.prefix, nextIndex);
      container.insertBefore(clone, template);
      clone.querySelectorAll(".boundary-control").forEach(syncBoundary);
      // No save here: a fresh row has blank required boundary fields, so
      // submitting it would fail validation and block the whole section from
      // saving until the user fills it in. The user's first edit saves it.
      return;
    }
    const removeButton = event.target.closest("[data-remove-row]");
    if (removeButton) {
      event.preventDefault();
      if (!window.confirm(REMOVE_ROW_MESSAGE)) {
        return;
      }
      const row = removeButton.closest(".row");
      const form = row.closest("form");
      row.remove();
      // Leave sparse gaps; the server orders by numeric index.
      form.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });

  function remintExistingIndices(form) {
    form.querySelectorAll(".rows[data-prefix]").forEach(function (container) {
      const prefix = container.dataset.prefix;
      rowChildren(container).forEach(function (row, position) {
        const pattern = new RegExp("^" + prefix + "\\[(\\d+)\\]");
        let wireIndex = null;
        row.querySelectorAll("[name]").forEach(function (field) {
          if (wireIndex !== null) return;
          const match = field.name.match(pattern);
          if (match) wireIndex = parseInt(match[1], 10);
        });
        if (wireIndex === null) return;
        let input = null;
        row.querySelectorAll("input[type='hidden']").forEach(function (el) {
          if (el.name.indexOf("." + "existing_index") !== -1) {
            // Only the row's own existing_index, not nested lists (none today).
            const own = el.name.match(pattern);
            if (own && parseInt(own[1], 10) === wireIndex) input = el;
          }
        });
        if (!input) {
          input = document.createElement("input");
          input.type = "hidden";
          input.name = prefix + "[" + wireIndex + "].existing_index";
          row.insertBefore(input, row.firstChild);
        }
        input.value = String(position);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", initAll);
  document.body.addEventListener("htmx:afterSettle", initAll);
  document.body.addEventListener("htmx:afterRequest", function (event) {
    if (!event.detail.successful) return;
    const form = event.detail.elt;
    if (!form || form.tagName !== "FORM") return;
    remintExistingIndices(form);
  });
})();
