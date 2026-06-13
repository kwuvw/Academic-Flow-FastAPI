function createTeacherItem(teacher, actionElement) {
  const article = document.createElement("article");
  article.className = "teacher-item";
  article.dataset.teacherId = String(teacher.id);

  article.innerHTML = `
    <span class="avatar" aria-hidden="true">${teacher.email.charAt(0).toUpperCase()}</span>
    <div class="teacher-info">
      <span class="teacher-name">${teacher.first_name || ""}</span>
      <span class="teacher-email">${teacher.email}</span>
    </div>
  `;

  if (actionElement) {
    article.appendChild(actionElement);
  }

  return article;
}

function buildActionButton(teacher) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn-primary small-btn connection-action";

  if (!teacher.status) {
    button.textContent = "Отправить запрос";
    button.addEventListener("click", () => sendRequest(teacher.id, button));
    return button;
  }

  if (teacher.status === "pending") {
    button.textContent = "Запрос отправлен";
    button.className = "btn-secondary small-btn connection-action is-disabled";
    button.disabled = true;
    return button;
  }

  if (teacher.status === "accepted") {
    button.textContent = "Ваш преподаватель";
    button.className = "btn-secondary small-btn connection-action is-status";
    button.disabled = true;
    return button;
  }

  button.textContent = "Отправить запрос";
  button.addEventListener("click", () => sendRequest(teacher.id, button));
  return button;
}

function renderEmpty(container, message) {
  container.innerHTML = `<p class="empty-state">${message}</p>`;
}

function renderAttachedList(container, teachers) {
  container.innerHTML = "";

  if (!teachers.length) {
    renderEmpty(container, "Пока нет прикреплённых преподавателей.");
    return;
  }

  teachers.forEach((teacher) => {
    const status = document.createElement("span");
    status.className = "connection-badge connection-badge--accepted";
    status.textContent = "Прикреплён";
    container.appendChild(createTeacherItem(teacher, status));
  });
}

function renderCatalog(container, teachers) {
  container.innerHTML = "";

  if (!teachers.length) {
    renderEmpty(container, "В системе пока нет преподавателей.");
    return;
  }

  teachers.forEach((teacher) => {
    container.appendChild(createTeacherItem(teacher, buildActionButton(teacher)));
  });
}

async function sendRequest(teacherId, button) {
  button.disabled = true;

  try {
    const response = await authFetch("/auth/connections/request", {
      method: "POST",
      body: JSON.stringify({ teacher_id: teacherId }),
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      alert(getErrorMessage(data, "Не удалось отправить заявку."));
      button.disabled = false;
      return;
    }

    await loadTeachersPage();
  } catch {
    button.disabled = false;
  }
}

async function loadTeachersPage() {
  const attachedContainer = document.getElementById("attached-teachers-list");
  const catalogContainer = document.getElementById("teachers-container");

  try {
    const response = await authFetch("/auth/connections/my-teachers");
    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const message = getErrorMessage(data, "Не удалось загрузить преподавателей.");
      renderEmpty(attachedContainer, message);
      renderEmpty(catalogContainer, message);
      return;
    }

    renderAttachedList(attachedContainer, data.accepted || []);

    const catalog = (data.all_teachers || []).filter(
      (teacher) => teacher.status !== "accepted",
    );
    renderCatalog(catalogContainer, catalog);
  } catch {
    /* redirect handled in authFetch */
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) {
    return;
  }

  const role = localStorage.getItem("user_role");
  if (role && role !== "student") {
    window.location.href = "/dashboard/teacher";
    return;
  }

  await loadTeachersPage();
});
