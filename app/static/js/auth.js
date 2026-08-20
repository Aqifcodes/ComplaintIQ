document.addEventListener("DOMContentLoaded", () => {
  // Passwords Visibility Toggle
  const initPasswordToggles = () => {
    const toggles = document.querySelectorAll(".password-toggle");
    
    toggles.forEach(toggle => {
      toggle.addEventListener("click", (e) => {
        e.preventDefault();
        const inputId = toggle.getAttribute("data-target");
        const input = document.getElementById(inputId);
        const icon = toggle.querySelector("i");
        
        if (input && icon) {
          if (input.type === "password") {
            input.type = "text";
            icon.classList.remove("fa-eye");
            icon.classList.add("fa-eye-slash");
          } else {
            input.type = "password";
            icon.classList.remove("fa-eye-slash");
            icon.classList.add("fa-eye");
          }
        }
      });
    });
  };

  // Toast System
  const showToast = (message, type = "success") => {
    // Create container if it doesn't exist
    let container = document.querySelector(".toast-container");
    if (!container) {
      container = document.createElement("div");
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    // Create toast
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    const iconClass = type === "success" ? "fa-circle-check" : "fa-circle-exclamation";
    toast.innerHTML = `
      <i class="fa-solid ${iconClass}"></i>
      <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    // Remove toast after duration
    setTimeout(() => {
      toast.style.animation = "fadeInUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse both";
      setTimeout(() => {
        toast.remove();
        if (container.children.length === 0) {
          container.remove();
        }
      }, 300);
    }, 4000);
  };

  // Live Error Clearing
  const initErrorClearing = () => {
    const inputs = document.querySelectorAll(".form-input");
    inputs.forEach(input => {
      input.addEventListener("input", () => {
        const group = input.closest(".form-group");
        if (group && group.classList.contains("has-error")) {
          group.classList.remove("has-error");
        }
      });
    });
  };

  // Show errors helper
  const showError = (inputId, message) => {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    const group = input.closest(".form-group");
    if (!group) return;
    
    group.classList.add("has-error");
    const feedback = group.querySelector(".invalid-feedback");
    if (feedback) {
      feedback.innerHTML = `<i class="fa-solid fa-circle-info"></i> ${message}`;
    }
  };

  // Form Shaker
  const shakeCard = () => {
    const card = document.querySelector(".auth-card");
    if (card) {
      card.classList.remove("shake");
      // Trigger reflow
      void card.offsetWidth;
      card.classList.add("shake");
      setTimeout(() => {
        card.classList.remove("shake");
      }, 500);
    }
  };

  // Validation Logic
  const validateEmail = (email) => {
    const re = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return re.test(String(email).toLowerCase());
  };

  const validatePasswordStrength = (password) => {
    // Requires min 8 chars, at least 1 number, and 1 letter
    if (password.length < 8) return { valid: false, msg: "Password must be at least 8 characters long." };
    if (!/[A-Za-z]/.test(password)) return { valid: false, msg: "Password must contain at least one letter." };
    if (!/[0-9]/.test(password)) return { valid: false, msg: "Password must contain at least one number." };
    return { valid: true };
  };

  // Forms Submissions
  const loginForm = document.getElementById("login-form");
  const signupForm = document.getElementById("signup-form");

  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      
      const emailInput = document.getElementById("email");
      const passwordInput = document.getElementById("password");
      
      let isValid = true;
      
      // Clean previous errors
      document.querySelectorAll(".form-group").forEach(g => g.classList.remove("has-error"));

      // Validations
      if (!emailInput.value.trim()) {
        showError("email", "Email address is required.");
        isValid = false;
      } else if (!validateEmail(emailInput.value.trim())) {
        showError("email", "Please enter a valid email address.");
        isValid = false;
      }

      if (!passwordInput.value) {
        showError("password", "Password is required.");
        isValid = false;
      }

      if (!isValid) {
        shakeCard();
        return;
      }

      // Submit form via Ajax
      const submitBtn = loginForm.querySelector(".btn-submit");
      submitBtn.classList.add("is-loading");

      try {
        const response = await fetch("/api/auth/login", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            email: emailInput.value.trim(),
            password: passwordInput.value
          })
        });

        const result = await response.json();

        if (response.ok && result.success) {
          showToast(result.message, "success");
          // Store dummy user session
          localStorage.setItem("complaintiq_user", JSON.stringify(result.user));
          
          // Smooth redirect simulation
          setTimeout(() => {
            window.location.href = "/";
          }, 1500);
        } else {
          showToast(result.message || "Login failed.", "error");
          if (result.message && result.message.toLowerCase().includes("password")) {
            showError("password", result.message);
          } else {
            showError("email", result.message);
          }
          shakeCard();
        }
      } catch (err) {
        showToast("Server connection error. Please try again.", "error");
      } finally {
        submitBtn.classList.remove("is-loading");
      }
    });
  }

  if (signupForm) {
    signupForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      
      const nameInput = document.getElementById("name");
      const emailInput = document.getElementById("email");
      const passwordInput = document.getElementById("password");
      const confirmPasswordInput = document.getElementById("confirmPassword");
      const termsCheck = document.getElementById("terms");
      
      let isValid = true;

      // Clean previous errors
      document.querySelectorAll(".form-group").forEach(g => g.classList.remove("has-error"));

      // Validations
      if (!nameInput.value.trim()) {
        showError("name", "Full Name is required.");
        isValid = false;
      }

      if (!emailInput.value.trim()) {
        showError("email", "Email address is required.");
        isValid = false;
      } else if (!validateEmail(emailInput.value.trim())) {
        showError("email", "Please enter a valid email address.");
        isValid = false;
      }

      if (!passwordInput.value) {
        showError("password", "Password is required.");
        isValid = false;
      } else {
        const strength = validatePasswordStrength(passwordInput.value);
        if (!strength.valid) {
          showError("password", strength.msg);
          isValid = false;
        }
      }

      if (!confirmPasswordInput.value) {
        showError("confirmPassword", "Please confirm your password.");
        isValid = false;
      } else if (passwordInput.value !== confirmPasswordInput.value) {
        showError("confirmPassword", "Passwords do not match.");
        isValid = false;
      }

      if (termsCheck && !termsCheck.checked) {
        showToast("You must accept the Terms of Service and Privacy Policy.", "error");
        isValid = false;
      }

      if (!isValid) {
        shakeCard();
        return;
      }

      // Submit signup form via Ajax
      const submitBtn = signupForm.querySelector(".btn-submit");
      submitBtn.classList.add("is-loading");

      try {
        const response = await fetch("/api/auth/signup", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            name: nameInput.value.trim(),
            email: emailInput.value.trim(),
            password: passwordInput.value,
            confirmPassword: confirmPasswordInput.value
          })
        });

        const result = await response.json();

        if (response.ok && result.success) {
          showToast(result.message, "success");
          
          // Simulated redirection to login screen after account creation
          setTimeout(() => {
            window.location.href = "/login";
          }, 2000);
        } else {
          showToast(result.message || "Signup failed.", "error");
          shakeCard();
        }
      } catch (err) {
        showToast("Server connection error. Please try again.", "error");
      } finally {
        submitBtn.classList.remove("is-loading");
      }
    });
  }

  // Animation visual updates (e.g. chart mock animation)
  const initChartAnimation = () => {
    const bars = document.querySelectorAll(".chart-bar");
    if (bars.length === 0) return;
    
    // Periodically change height of bars randomly to simulate real time complaint analytics processing
    setInterval(() => {
      bars.forEach(bar => {
        const active = Math.random() > 0.3;
        if (active) {
          bar.classList.add("active");
          const height = Math.floor(Math.random() * 25) + 10; // 10px to 35px
          bar.style.height = `${height}px`;
        } else {
          bar.classList.remove("active");
          bar.style.height = `6px`;
        }
      });
    }, 1800);
  };

  // Initialize all functions
  initPasswordToggles();
  initErrorClearing();
  initChartAnimation();
});
