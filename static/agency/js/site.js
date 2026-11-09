const menuToggle = document.querySelector("[data-menu-toggle]");
const navigation = document.querySelector("[data-navigation]");

if (menuToggle && navigation) {
  document.documentElement.classList.add("js-menu");
  const closeMenu = () => {
    menuToggle.setAttribute("aria-expanded", "false");
    navigation.classList.remove("is-open");
  };
  menuToggle.addEventListener("click", () => {
    const expanded = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!expanded));
    navigation.classList.toggle("is-open", !expanded);
  });
  navigation.addEventListener("click", (event) => {
    if (event.target.closest("a")) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menuToggle.getAttribute("aria-expanded") === "true") {
      closeMenu();
      menuToggle.focus();
    }
  });
  window.matchMedia("(max-width: 900px)").addEventListener("change", closeMenu);
}

for (const [containerSelector, slideSelector] of [
  ["[data-model-slideshow]", "[data-model-slide]"],
  ["[data-entertainer-slideshow]", "[data-entertainer-slide]"],
]) {
  const slideshow = document.querySelector(containerSelector);
  if (!slideshow) continue;
  const slides = [...slideshow.querySelectorAll(slideSelector)];
  if (slides.length > 1 && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    let active = 0;
    window.setInterval(() => {
      slides[active].hidden = true;
      active = (active + 1) % slides.length;
      slides[active].hidden = false;
    }, 3000);
  }
}

const enquiryForm = document.querySelector("[data-enquiry-form]");
if (enquiryForm) {
  enquiryForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const name = enquiryForm.elements.name.value.trim();
    const message = enquiryForm.elements.message.value.trim();
    if (!name || !message) return;
    const text = `Name: ${name}\nEnquiry: ${message}`;
    window.open(`https://wa.me/27681946795?text=${encodeURIComponent(text)}`, "_blank", "noopener");
  });
}

document.addEventListener('input', function (event) {
  var input = event.target;
  if (input && input.hasAttribute && input.hasAttribute('data-digits-only')) {
    input.value = input.value.replace(/\D/g, '').slice(0, 10);
  }
});
