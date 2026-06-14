function getAccessToken() {
  return localStorage.getItem("access_token");
}

function requireAuth() {
  if (!getAccessToken()) {
    window.location.href = "/login";
    return false;
  }
  return true;
}

async function authFetch(url, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const token = getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_role");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  return response;
}

async function loadCurrentUserName() {
  const element = document.getElementById("user-display-name");
  if (!element) {
    return;
  }

  try {
    const response = await authFetch("/auth/me");
    if (!response.ok) {
      return;
    }

    const user = await response.json();
    element.textContent = user.first_name || "";
  } catch {
    /* redirect handled in authFetch */
  }
}

function getErrorMessage(payload, fallback = "Не удалось выполнить запрос.") {
  if (!payload) {
    return fallback;
  }

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  return fallback;
}
