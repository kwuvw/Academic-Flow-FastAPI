function showMessage(element, text, type) {
  element.textContent = text;
  element.className = "form-message " + type;
}

function setText(id, value) {
  document.getElementById(id).textContent = value || "—";
}

function setInputValue(id, value) {
  var el = document.getElementById(id);
  if (!el) return;
  el.value = value || "";
}

function showRoleFields(role) {
  var isStudent = role === "student";
  var isTeacher = role === "teacher";

  document.querySelectorAll(".student-field").forEach(function (el) {
    el.style.display = isStudent ? "" : "none";
  });
  document.querySelectorAll(".teacher-field").forEach(function (el) {
    el.style.display = isTeacher ? "" : "none";
  });
}

function showFieldError(fieldId, message) {
  var input = document.getElementById(fieldId);
  var error = document.getElementById("error-" + fieldId);
  if (input) input.classList.add("error");
  if (error) {
    error.textContent = message;
    error.classList.add("visible");
  }
}

function clearFieldError(fieldId) {
  var input = document.getElementById(fieldId);
  var error = document.getElementById("error-" + fieldId);
  if (input) input.classList.remove("error");
  if (error) {
    error.textContent = "";
    error.classList.remove("visible");
  }
}

function clearAllErrors() {
  document.querySelectorAll(".input-field.error").forEach(function (el) {
    el.classList.remove("error");
  });
  document.querySelectorAll(".field-error.visible").forEach(function (el) {
    el.textContent = "";
    el.classList.remove("visible");
  });
}

var CYRILLIC_RE = /^[а-яёА-ЯЁ\s\-]+$/;

function validateForm(form) {
  clearAllErrors();
  var valid = true;

  var nameFields = [
    { inputId: "last-name", label: "Фамилия" },
    { inputId: "first-name", label: "Имя" },
    { inputId: "middle-name", label: "Отчество" },
  ];

  nameFields.forEach(function (field) {
    var input = document.getElementById(field.inputId);
    if (!input || input.offsetParent === null) return;
    var val = input.value.trim();
    if (val && !CYRILLIC_RE.test(val)) {
      showFieldError(field.inputId, field.label + ": допустимы только буквы (кириллица)");
      valid = false;
    }
  });

  var courseSelect = document.getElementById("course-number");
  if (courseSelect && courseSelect.offsetParent !== null) {
    var courseVal = courseSelect.value;
    if (courseVal) {
      var num = parseInt(courseVal, 10);
      if (num < 1 || num > 4) {
        showFieldError("course-number", "Курс: допустимы значения от 1 до 4");
        valid = false;
      }
    }
  }

  var groupSelect = document.getElementById("group-name");
  if (groupSelect && groupSelect.offsetParent !== null) {
    var groupVal = groupSelect.value;
    if (groupVal) {
      var allowed = ["ГД", "Д", "ИЗ", "ИС", "КМ", "Т", "СА", "Р", "ПП", "ОН", "БУХ", "МС"];
      if (allowed.indexOf(groupVal) === -1) {
        showFieldError("group-name", "Выберите группу из списка");
        valid = false;
      }
    }
  }

  return valid;
}

function populateProfile(user) {
  setText("info-email", user.email);
  setText("info-role", user.role === "student" ? "Студент" : "Преподаватель");
  setText("info-first-name", user.first_name);
  setText("info-last-name", user.last_name);
  setText("info-middle-name", user.middle_name);
  setText("info-group-name", user.group_name);
  setText("info-course-number", user.course_number != null ? String(user.course_number) : null);
  setText("info-department", user.department);

  setInputValue("first-name", user.first_name);
  setInputValue("last-name", user.last_name);
  setInputValue("middle-name", user.middle_name);
  setInputValue("group-name", user.group_name);
  setInputValue("course-number", user.course_number != null ? String(user.course_number) : "");
  setInputValue("department", user.department);

  showRoleFields(user.role);
}

document.addEventListener("DOMContentLoaded", async function () {
  if (!requireAuth()) {
    return;
  }

  var messageEl = document.getElementById("form-message");

  try {
    var response = await authFetch("/auth/me");
    var user = await response.json().catch(function () { return null; });

    if (!response.ok) {
      showMessage(messageEl, "Не удалось загрузить профиль.", "error");
      return;
    }

    populateProfile(user);
  } catch (e) {
    /* redirect handled in authFetch */
  }

  var form = document.getElementById("profile-form");

  form.querySelectorAll(".input-field").forEach(function (input) {
    input.addEventListener("input", function () {
      clearFieldError(input.id);
    });
  });

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    messageEl.className = "form-message";
    messageEl.textContent = "";

    if (!validateForm(form)) {
      showMessage(messageEl, "Исправьте ошибки в полях формы.", "error");
      return;
    }

    var payload = {};
    var fields = ["first_name", "last_name", "middle_name", "group_name", "department"];
    fields.forEach(function (name) {
      var input = form.querySelector("[name='" + name + "']");
      var val = input ? input.value.trim() : "";
      if (val) {
        payload[name] = val;
      } else {
        payload[name] = null;
      }
    });

    var courseSelect = form.querySelector("[name='course_number']");
    if (courseSelect) {
      var courseVal = courseSelect.value;
      payload.course_number = courseVal ? parseInt(courseVal, 10) : null;
    }

    var submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;

    try {
      var saveResponse = await authFetch("/auth/profile/update", {
        method: "PUT",
        body: JSON.stringify(payload),
      });

      var result = await saveResponse.json().catch(function () { return null; });

      if (!saveResponse.ok) {
        showMessage(messageEl, getErrorMessage(result, "Не удалось сохранить профиль."), "error");
        return;
      }

      populateProfile(result);
      var nameEl = document.getElementById("user-display-name");
      if (nameEl) {
        nameEl.textContent = result.first_name || "";
      }
      showMessage(messageEl, "Профиль успешно обновлён.", "success");
    } catch (e) {
      showMessage(messageEl, "Сервер недоступен. Проверьте подключение.", "error");
    } finally {
      submitBtn.disabled = false;
    }
  });

  var logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async function () {
      try {
        await authFetch("/auth/logout", { method: "POST" });
      } catch (e) {
        /* continue to redirect even if request fails */
      }
      localStorage.clear();
      sessionStorage.clear();
      window.location.href = "/login";
    });
  }
});
