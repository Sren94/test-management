// Closes the user dropdown when clicking outside of it or pressing Escape.
(function () {
  const openMenus = () => document.querySelectorAll("details.menu[open]");

  document.addEventListener("click", (event) => {
    openMenus().forEach((menu) => {
      if (!menu.contains(event.target)) menu.removeAttribute("open");
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      openMenus().forEach((menu) => {
        menu.removeAttribute("open");
        menu.querySelector("summary").focus();
      });
    }
  });
})();