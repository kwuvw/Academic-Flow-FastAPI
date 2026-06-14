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

  return "Неверная почта или пароль.";
}

function redirectByRole(role) {
  if (role === "teacher") {
    window.location.href = "/dashboard/teacher";
    return;
  }

  window.location.href = "/dashboard/student";
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const form = event.currentTarget;
  const message = document.getElementById("form-message");
  const submitButton = form.querySelector('button[type="submit"]');

  message.className = "form-message";
  message.textContent = "";

  const email = form.email.value.trim();
  const password = form.password.value;

  submitButton.disabled = true;

  try {
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json().catch(() => null);

    if (response.status !== 200 || !data?.access_token) {
      showMessage(
        message,
        response.ok
          ? "Сервер не вернул токен авторизации."
          : getErrorMessage(data),
        "error",
      );
      return;
    }

    localStorage.setItem("access_token", data.access_token);

    const role = data.role || null;

    if (role) {
      localStorage.setItem("user_role", role);
      redirectByRole(role);
      return;
    }

    const meResponse = await fetch("/auth/me", {
      headers: {
        Authorization: `Bearer ${data.access_token}`,
      },
    });

    const meData = await meResponse.json().catch(() => null);

    if (!meResponse.ok) {
      showMessage(message, getErrorMessage(meData), "error");
      return;
    }

    localStorage.setItem("user_role", meData.role);
    redirectByRole(meData.role);
  } catch (error) {
    showMessage(message, "Сервер недоступен. Проверьте подключение.", "error");
  } finally {
    submitButton.disabled = false;
  }
});
