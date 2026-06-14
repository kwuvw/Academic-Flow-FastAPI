var selectedFiles = [];

function renderEmpty(container, message) {
  container.innerHTML = '<p class="empty-state">' + message + '</p>';
}

async function detachStudent(connectionId, button) {
  const card = button.closest('.teacher-item');
  if (!card) {
    return;
  }

  button.disabled = true;
  button.textContent = 'Удаление…';

  try {
    const response = await authFetch('/auth/connections/detach/' + connectionId, {
      method: 'DELETE',
    });

    const data = await response.json().catch(function () { return null; });

    if (!response.ok) {
      alert(getErrorMessage(data, 'Не удалось открепить студента.'));
      button.disabled = false;
      button.textContent = 'Удалить';
      return;
    }

    card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    card.style.opacity = '0';
    card.style.transform = 'translateX(30px)';

    card.addEventListener('transitionend', function () {
      card.remove();

      var list = document.getElementById('students-list');
      if (list && !list.querySelector('.teacher-item')) {
        renderEmpty(list, 'К вам пока не прикрепился ни один студент.');
      }

      updateStats();
    });
  } catch {
    button.disabled = false;
    button.textContent = 'Удалить';
  }
}

function updateStats() {
  var cards = document.querySelectorAll('#students-list .teacher-item');
  var count = cards.length;

  var statCards = document.querySelectorAll('.stat-card');
  if (statCards.length >= 1) {
    var countEl = statCards[0].querySelector('.stat-card__value');
    var labelEl = statCards[0].querySelector('.stat-card__label');
    if (countEl) {
      countEl.textContent = String(count);
    }
    if (labelEl) {
      if (count === 1) {
        labelEl.textContent = 'Студент';
      } else if (count >= 2 && count <= 4) {
        labelEl.textContent = 'Студента';
      } else {
        labelEl.textContent = 'Студентов';
      }
    }
  }

  var groups = new Set();
  cards.forEach(function (card) {
    var emailEl = card.querySelector('.teacher-email');
    if (emailEl) {
      var text = emailEl.textContent.trim();
      var parts = text.split('-');
      if (parts.length >= 2) {
        groups.add(parts.slice(1).join('-'));
      }
    }
  });

  if (statCards.length >= 2) {
    var groupsVal = statCards[1].querySelector('.stat-card__value');
    if (groupsVal) {
      groupsVal.textContent = String(groups.size);
    }
  }
}

function showToast(message) {
  var toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('is-visible');
  setTimeout(function () {
    toast.classList.remove('is-visible');
  }, 3000);
}

function openTaskModal(groupName, courseNumber) {
  var modal = document.getElementById('task-modal');
  var title = document.getElementById('task-modal-title');
  var groupInput = document.getElementById('task-group-name');
  var courseInput = document.getElementById('task-course-number');

  if (!modal || !title || !groupInput || !courseInput) return;

  var label = courseNumber ? courseNumber + '-' + groupName : groupName;
  title.textContent = 'Добавить задание для группы ' + label;
  groupInput.value = groupName;
  courseInput.value = courseNumber || '';

  modal.classList.add('is-open');
  document.body.style.overflow = 'hidden';

  var firstInput = document.getElementById('task-title');
  if (firstInput) {
    setTimeout(function () { firstInput.focus(); }, 100);
  }
}

function closeTaskModal() {
  var modal = document.getElementById('task-modal');
  if (!modal) return;

  modal.classList.remove('is-open');
  document.body.style.overflow = '';

  resetTaskForm();
}

function resetTaskForm() {
  var form = document.getElementById('task-form');
  if (form) form.reset();

  selectedFiles = [];
  renderFileList();

  document.querySelectorAll('.task-modal__input.error, .task-modal__textarea.error').forEach(function (el) {
    el.classList.remove('error');
  });
  document.querySelectorAll('.task-modal__field-error.visible').forEach(function (el) {
    el.classList.remove('visible');
    el.textContent = '';
  });
}

function validateTaskForm() {
  var valid = true;

  var titleInput = document.getElementById('task-title');
  var titleError = document.getElementById('error-title');
  if (titleInput && !titleInput.value.trim()) {
    titleInput.classList.add('error');
    titleError.textContent = 'Введите название задания';
    titleError.classList.add('visible');
    valid = false;
  } else if (titleInput) {
    titleInput.classList.remove('error');
    titleError.classList.remove('visible');
    titleError.textContent = '';
  }

  var descInput = document.getElementById('task-description');
  var descError = document.getElementById('error-description');
  if (descInput && !descInput.value.trim()) {
    descInput.classList.add('error');
    descError.textContent = 'Введите описание задания';
    descError.classList.add('visible');
    valid = false;
  } else if (descInput) {
    descInput.classList.remove('error');
    descError.classList.remove('visible');
    descError.textContent = '';
  }

  var deadlineInput = document.getElementById('task-deadline');
  var deadlineError = document.getElementById('error-deadline');
  if (deadlineInput && !deadlineInput.value) {
    deadlineInput.classList.add('error');
    deadlineError.textContent = 'Укажите срок сдачи';
    deadlineError.classList.add('visible');
    valid = false;
  } else if (deadlineInput) {
    deadlineInput.classList.remove('error');
    deadlineError.classList.remove('visible');
    deadlineError.textContent = '';
  }

  return valid;
}

function renderFileList() {
  var container = document.getElementById('task-file-list');
  if (!container) return;

  container.innerHTML = '';
  selectedFiles.forEach(function (file, index) {
    var item = document.createElement('div');
    item.className = 'task-modal__file-item';

    var name = document.createElement('span');
    name.className = 'task-modal__file-name';
    name.textContent = file.name;

    var removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'task-modal__file-remove';
    removeBtn.textContent = '\u00d7';
    removeBtn.setAttribute('aria-label', 'Удалить файл');
    removeBtn.addEventListener('click', function () {
      selectedFiles.splice(index, 1);
      renderFileList();
    });

    item.appendChild(name);
    item.appendChild(removeBtn);
    container.appendChild(item);
  });
}

async function submitTask() {
  if (!validateTaskForm()) return;

  var submitBtn = document.getElementById('task-modal-submit');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Публикация…';
  }

  var formData = new FormData();
  formData.append('title', document.getElementById('task-title').value.trim());
  formData.append('description', document.getElementById('task-description').value.trim());
  formData.append('deadline', document.getElementById('task-deadline').value);
  formData.append('group_name', document.getElementById('task-group-name').value);
  formData.append('course_number', document.getElementById('task-course-number').value || '0');

  selectedFiles.forEach(function (file) {
    formData.append('files', file);
  });

  try {
    var token = localStorage.getItem('access_token');
    var response = await fetch('/api/tasks/create', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + token,
      },
      body: formData,
    });

    var data = await response.json().catch(function () { return null; });

    if (!response.ok) {
      var msg = (data && data.detail) ? data.detail : 'Не удалось создать задание.';
      alert(msg);
      return;
    }

    closeTaskModal();
    showToast('Задание успешно опубликовано');
  } catch {
    alert('Сервер недоступен. Проверьте подключение.');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Опубликовать';
    }
  }
}

document.addEventListener('DOMContentLoaded', function () {
  var list = document.getElementById('students-list');
  if (list) {
    list.addEventListener('click', function (event) {
      var button = event.target.closest('.detach-btn');
      if (!button) return;
      var connectionId = button.dataset.connectionId;
      if (!connectionId) return;
      detachStudent(connectionId, button);
    });
  }

  var groupsList = document.getElementById('groups-list');
  if (groupsList) {
    groupsList.addEventListener('click', function (event) {
      var btn = event.target.closest('.open-task-modal');
      if (!btn) return;
      var group = btn.dataset.group;
      var course = btn.dataset.course;
      if (group) openTaskModal(group, course);
    });
  }

  var modalClose = document.getElementById('task-modal-close');
  if (modalClose) {
    modalClose.addEventListener('click', closeTaskModal);
  }

  var modalCancel = document.getElementById('task-modal-cancel');
  if (modalCancel) {
    modalCancel.addEventListener('click', closeTaskModal);
  }

  var modalOverlay = document.getElementById('task-modal');
  if (modalOverlay) {
    modalOverlay.addEventListener('click', function (e) {
      if (e.target === modalOverlay) closeTaskModal();
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      var modal = document.getElementById('task-modal');
      if (modal && modal.classList.contains('is-open')) {
        closeTaskModal();
      }
    }
  });

  var submitBtn = document.getElementById('task-modal-submit');
  if (submitBtn) {
    submitBtn.addEventListener('click', submitTask);
  }

  var dropzone = document.getElementById('task-dropzone');
  var fileInput = document.getElementById('task-files');

  if (dropzone && fileInput) {
    dropzone.addEventListener('dragover', function (e) {
      e.preventDefault();
      dropzone.classList.add('is-dragover');
    });

    dropzone.addEventListener('dragleave', function () {
      dropzone.classList.remove('is-dragover');
    });

    dropzone.addEventListener('drop', function (e) {
      e.preventDefault();
      dropzone.classList.remove('is-dragover');
      var files = Array.from(e.dataTransfer.files);
      files.forEach(function (file) {
        selectedFiles.push(file);
      });
      renderFileList();
      fileInput.value = '';
    });

    fileInput.addEventListener('change', function () {
      var files = Array.from(fileInput.files);
      files.forEach(function (file) {
        selectedFiles.push(file);
      });
      renderFileList();
      fileInput.value = '';
    });
  }

  document.querySelectorAll('#task-form .task-modal__input, #task-form .task-modal__textarea').forEach(function (input) {
    input.addEventListener('input', function () {
      input.classList.remove('error');
      var errorEl = document.getElementById('error-' + input.name);
      if (errorEl) {
        errorEl.classList.remove('visible');
        errorEl.textContent = '';
      }
    });
  });
});
