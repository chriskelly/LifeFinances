(function () {
  function syncController(controller) {
    const form = controller.closest("form");
    const controllerId = controller.dataset.conditionController;
    form
      .querySelectorAll(
        "[data-condition-group][data-condition-controller-id='" +
          controllerId +
          "']"
      )
      .forEach(function (group) {
        const values = (group.dataset.conditionValue || "").split(" ");
        const active = values.indexOf(controller.value) !== -1;
        group.hidden = !active;
        group.querySelectorAll("[data-condition-input]").forEach(function (input) {
          input.disabled = !active;
          input.required =
            active && input.hasAttribute("data-required-when-active");
        });
      });
  }

  function initConditionalFields(root) {
    root.querySelectorAll("[data-condition-controller]").forEach(function (controller) {
      if (!controller.dataset.conditionBound) {
        controller.addEventListener("change", function () {
          syncController(controller);
        });
        controller.dataset.conditionBound = "true";
      }
      syncController(controller);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initConditionalFields(document);
  });
  document.body.addEventListener("htmx:afterSettle", function (event) {
    initConditionalFields(event.detail.target || document);
  });
})();
