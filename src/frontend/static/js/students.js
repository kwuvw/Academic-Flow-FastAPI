function createStudentItem(student, actionsElement) {
  const article = document.createElement("article");
  article.className = "teacher-item";
  article.dataset.studentId = String(student.id);
  article.dataset.connectionId = String(student.connection_id || "");

  const fullName = [student.last_name, student.first_name, student.middle_name].filter(Boolean).join(" ");
  let subtitle = student.email;
  if (student.group_name) {
    subtitle = student.course_number
      ? `Группа: ${student.group_name} \u2022 ${student.course_number} курс`
      : `Группа: ${student.group_name}`;
  }

  const initials = ((student.last_name || "") + (student.first_name || "")).substring(0, 2).toUpperCase();

  article.innerHTML = `
    <span class="avatar" aria-hidden="true">${initials || student.email.charAt(0).toUpperCase()}</span>
    <div class="teacher-info">
      <span class="teacher-name">${fullName || student.email}</span>
      <span class="teacher-email">${subtitle}</span>
    </div>
  `;

  if (actionsElement) {
    article.appendChild(actionsElement);
  }

  return article;
}

function buildRequestActions(student) {
  const wrapper = document.createElement("div");
  wrapper.className = "connection-actions";

  const acceptButton = document.createElement("button");
  acceptButton.type = "button";
  acceptButton.className = "btn-primary small-btn";
  acceptButton.textContent = "Принять";
  acceptButton.addEventListener("click", () =>
    respondToRequest(student.connection_id, "accepted", acceptButton),
  );

  const rejectButton = document.createElement("button");
  rejectButton.type = "button";
  rejectButton.className = "btn-secondary small-btn btn-muted";
  rejectButton.textContent = "Отклонить";
  rejectButton.addEventListener("click", () =>
    respondToRequest(student.connection_id, "rejected", rejectButton),
  );

  wrapper.appendChild(acceptButton);
  wrapper.appendChild(rejectButton);
  return wrapper;
}

function renderEmpty(container, message) {
  container.innerHTML = `<p class="empty-state">${message}</p>`;
}

function renderRequests(container, students) {
  container.innerHTML = "";

  if (!students.length) {
    renderEmpty(container, "Новых заявок пока нет.");
    return;
  }

  students.forEach((student) => {
    container.appendChild(createStudentItem(student, buildRequestActions(student)));
  });
}

function renderAttached(container, students) {
  container.innerHTML = "";

  if (!students.length) {
    renderEmpty(container, "Пока нет прикреплённых студентов.");
    return;
  }

  students.forEach((student) => {
    const badge = document.createElement("span");
    badge.className = "connection-badge connection-badge--accepted";
    badge.textContent = "Активен";
    container.appendChild(createStudentItem(student, badge));
  });
}

async function respondToRequest(connectionId, status, button) {
  const card = button.closest(".teacher-item");
  if (card) {
    card.querySelectorAll("button").forEach((item) => {
      item.disabled = true;
    });
  }

  try {
    const response = await authFetch("/auth/connections/respond", {
      method: "POST",
      body: JSON.stringify({ connection_id: connectionId, status }),
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      alert(getErrorMessage(data, "Не удалось обработать заявку."));
      if (card) {
        card.querySelectorAll("button").forEach((item) => {
          item.disabled = false;
        });
      }
      return;
    }

    await loadStudentsPage();
  } catch {
    if (card) {
      card.querySelectorAll("button").forEach((item) => {
        item.disabled = false;
      });
    }
  }
}

async function loadStudentsPage() {
  const requestsContainer = document.getElementById("requests-container");
  const attachedContainer = document.getElementById("attached-students-list");

  try {
    const response = await authFetch("/auth/connections/my-students");
    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const message = getErrorMessage(data, "Не удалось загрузить студентов.");
      renderEmpty(requestsContainer, message);
      renderEmpty(attachedContainer, message);
      return;
    }

    renderRequests(requestsContainer, data.pending || []);
    renderAttached(attachedContainer, data.accepted || []);
  } catch {
    /* redirect handled in authFetch */
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) {
    return;
  }

  const role = localStorage.getItem("user_role");
  if (role && role !== "teacher") {
    window.location.href = "/dashboard/student";
    return;
  }

  await loadStudentsPage();
});
