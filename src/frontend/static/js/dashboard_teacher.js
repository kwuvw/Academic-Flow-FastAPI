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

document.addEventListener('DOMContentLoaded', function () {
  var list = document.getElementById('students-list');
  if (!list) {
    return;
  }

  list.addEventListener('click', function (event) {
    var button = event.target.closest('.detach-btn');
    if (!button) {
      return;
    }

    var connectionId = button.dataset.connectionId;
    if (!connectionId) {
      return;
    }

    detachStudent(connectionId, button);
  });
});
