const navToggle = document.querySelector(".nav-toggle");
const topbarLinks = document.querySelector(".topbar-links");
const contactForm = document.querySelector("#contact-form");
const currentYear = document.querySelector("#current-year");

if (navToggle && topbarLinks) {
  navToggle.addEventListener("click", () => {
    const isOpen = topbarLinks.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });

  topbarLinks.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      topbarLinks.classList.remove("is-open");
      navToggle.setAttribute("aria-expanded", "false");
    });
  });
}

if (contactForm) {
  contactForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const data = new FormData(contactForm);
    const name = (data.get("name") || "").toString().trim();
    const email = (data.get("email") || "").toString().trim();
    const project = (data.get("project") || "").toString().trim();
    const message = (data.get("message") || "").toString().trim();

    const subject = encodeURIComponent("Apex Smart Automations Inquiry");
    const body = encodeURIComponent(
      [
        name ? `Name: ${name}` : "",
        email ? `Email: ${email}` : "",
        project ? `Project Type: ${project}` : "",
        "",
        message || "I would like to discuss a smart automation project.",
      ]
        .filter(Boolean)
        .join("\n")
    );

    window.location.href = `mailto:hello@apexsmartautomation.com?subject=${subject}&body=${body}`;
  });
}

if (currentYear) {
  currentYear.textContent = new Date().getFullYear().toString();
}
