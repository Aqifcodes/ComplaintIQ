const THEME_STORAGE_KEY = "complaintiq-theme";

const SUCCESS_MESSAGES = new Set([
  "Complaint submitted successfully.",
  "Complaint status updated successfully.",
]);

const dismissTemporarySuccessBanners = () => {
  document.querySelectorAll(".alert-banner").forEach((banner) => {
    const messageText = banner.querySelector("strong")?.textContent?.trim();
    if (!messageText || !SUCCESS_MESSAGES.has(messageText)) return;

    banner.style.maxHeight = `${banner.scrollHeight}px`;

    window.setTimeout(() => {
      banner.classList.add("is-dismissing");
    }, 3500);

    banner.addEventListener(
      "transitionend",
      (event) => {
        if (event.propertyName === "max-height") {
          banner.remove();
        }
      },
      { once: true }
    );
  });
};

const getStoredTheme = () => {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  return stored === "dark" || stored === "light" ? stored : "light";
};

const applyTheme = (theme) => {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(THEME_STORAGE_KEY, theme);
};

applyTheme(getStoredTheme());

document.addEventListener("DOMContentLoaded", () => {
  const themeToggle = document.getElementById("themeToggle");

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
      applyTheme(currentTheme === "light" ? "dark" : "light");
    });
  }

  const dashboardShell = document.getElementById("dashboardShell");
  const navLinks = Array.from(document.querySelectorAll(".nav-link[data-section]"));
  const sectionTriggers = Array.from(document.querySelectorAll("[data-section]:not(.nav-link)"));
  const sections = Array.from(document.querySelectorAll(".page-section"));
  const complaintCards = Array.from(document.querySelectorAll(".js-complaint-card"));
  const backToComplaints = document.getElementById("backToComplaints");
  const sidebarToggle = document.getElementById("sidebarToggle");
  const detailTitle = document.getElementById("detailTitle");
  const detailDescription = document.getElementById("detailDescription");
  const detailStatus = document.getElementById("detailStatus");
  const detailDate = document.getElementById("detailDate");
  const detailAdminResponse = document.getElementById("detailAdminResponse");
  const hasSubmitMessage = !!document.querySelector("#submit-section .alert-banner");

  const setActiveSection = (sectionId, persist = true) => {
    sections.forEach((section) => {
      section.classList.toggle("active", section.id === sectionId);
    });

    navLinks.forEach((link) => {
      link.classList.toggle("active", link.dataset.section === sectionId);
    });

    if (persist) {
      localStorage.setItem("customerDashboardSection", sectionId);
    }
  };

  const openComplaintDetail = (card) => {
    const title = card.dataset.complaintTitle || "";
    const description = card.dataset.complaintDescription || "";
    const status = card.dataset.complaintStatus || "";
    const date = card.dataset.complaintDate || "";
    const adminResponse = card.dataset.complaintAdminResponse || "";

    detailTitle.textContent = title;
    detailDescription.textContent = description;
    
    // Status text and style configuration
    detailStatus.textContent = status;
    detailStatus.className = "status-chip status-chip--" + (status || "").toLowerCase();
    
    detailDate.textContent = date;
    if (detailAdminResponse) {
      detailAdminResponse.textContent = adminResponse && adminResponse.trim() !== "" ? adminResponse : "Awaiting response";
    }

    sections.forEach((section) => {
      section.classList.toggle("active", section.id === "complaint-detail-section");
    });

    navLinks.forEach((link) => {
      link.classList.toggle("active", link.dataset.section === "complaints-section");
    });
  };

  navLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const sectionId = link.dataset.section;
      if (!sectionId) return;
      setActiveSection(sectionId);
    });
  });

  sectionTriggers.forEach((trigger) => {
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      const sectionId = trigger.dataset.section;
      if (!sectionId) return;
      setActiveSection(sectionId);
    });
  });

  complaintCards.forEach((card) => {
    card.addEventListener("click", () => openComplaintDetail(card));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openComplaintDetail(card);
      }
    });
  });

  if (backToComplaints) {
    backToComplaints.addEventListener("click", () => {
      setActiveSection("complaints-section");
    });
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", () => {
      dashboardShell.classList.toggle("open");
    });
  }

  const storedSection = localStorage.getItem("customerDashboardSection");
  const sectionExists = (id) => sections.some((section) => section.id === id);
  const defaultSection = sectionExists("dashboard-section") ? "dashboard-section" : (sections[0] ? sections[0].id : null);
  const startupSection = sectionExists(storedSection)
    ? storedSection
    : (hasSubmitMessage && sectionExists("submit-section") ? "submit-section" : defaultSection);

  if (startupSection) {
    setActiveSection(startupSection, false);
  }

  // --- Admin Dashboard Filtering ---
  const filterCategory = document.getElementById("filterCategory");
  const filterPriority = document.getElementById("filterPriority");
  const filterStatus = document.getElementById("filterStatus");
  const btnClearFilters = document.getElementById("btnClearFilters");
  const complaintRows = Array.from(document.querySelectorAll(".complaint-row"));
  const noMatchState = document.getElementById("noMatchState");

  if (filterCategory || filterPriority || filterStatus || btnClearFilters) {
    const applyTableFilters = () => {
      const selectedCat = filterCategory ? filterCategory.value : "";
      const selectedPrio = filterPriority ? filterPriority.value.toLowerCase() : "";
      const selectedStatus = filterStatus ? filterStatus.value : "";

      let visibleCount = 0;

      complaintRows.forEach((row) => {
        const rowCat = row.dataset.category || "";
        const rowPrio = (row.dataset.priority || "").toLowerCase();
        const rowStatus = row.dataset.status || "";

        const catMatch = !selectedCat || rowCat === selectedCat;
        const prioMatch = !selectedPrio || rowPrio === selectedPrio;
        const statusMatch = !selectedStatus || rowStatus === selectedStatus;

        if (catMatch && prioMatch && statusMatch) {
          row.style.display = "";
          visibleCount++;
        } else {
          row.style.display = "none";
        }
      });

      if (noMatchState) {
        noMatchState.style.display = visibleCount === 0 ? "block" : "none";
      }
    };

    if (filterCategory) filterCategory.addEventListener("change", applyTableFilters);
    if (filterPriority) filterPriority.addEventListener("change", applyTableFilters);
    if (filterStatus) filterStatus.addEventListener("change", applyTableFilters);

    if (btnClearFilters) {
      btnClearFilters.addEventListener("click", () => {
        if (filterCategory) filterCategory.value = "";
        if (filterPriority) filterPriority.value = "";
        if (filterStatus) filterStatus.value = "";
        applyTableFilters();
      });
    }
  }

  dismissTemporarySuccessBanners();
});
