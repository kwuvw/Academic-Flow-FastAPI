function showMessage(element, text, type) {
  element.textContent = text;
  element.className = `form-message ${type}`;
}

function getErrorMessage(payload) {
  if (!payload) {
    return "Не удалось выполнить запрос. Попробуйте позже.";
  }

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  if (Array.isArray(payload.detail) && payload.detail.length > 0) {
    return payload.detail[0].msg || "Проверьте введённые данные.";
  }

  return "Проверьте введённые данные.";
}

document.getElementById("register-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const form = event.currentTarget;
  const message = document.getElementById("form-message");
  const roleError = document.getElementById("role-error");
  const submitButton = form.querySelector('button[type="submit"]');

  message.className = "form-message";
  message.textContent = "";
  roleError.textContent = "";

  const email = form.email.value.trim();
  const password = form.password.value;
  const selectedRole = form.querySelector('input[name="role"]:checked');

  if (!selectedRole) {
    roleError.textContent = "Выберите роль: студент или преподаватель.";
    return;
  }

  submitButton.disabled = true;

  try {
    const response = await fetch("/auth/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        password,
        role: selectedRole.value,
      }),
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      showMessage(message, getErrorMessage(data), "error");
      return;
    }

    window.location.href = "/login";
  } catch (error) {
    showMessage(message, "Сервер недоступен. Проверьте подключение.", "error");
  } finally {
    submitButton.disabled = false;
  }
});
