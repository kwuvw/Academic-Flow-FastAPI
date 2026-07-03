# Academic Flow

**Academic Flow** — веб-приложение для управления учебными заданиями и взаимодействия студентов с преподавателями. Система обеспечивает полный цикл: регистрация пользователей с разделением по ролям, прикрепление студентов к преподавателям, создание и отслеживание заданий с файловыми вложениями, а также администрирование преподавательского состава.

---

## Возможности

- Регистрация и аутентификация с ролями *студент*, *преподаватель*, *администратор*
- JWT-аутентификация с поддержкой Bearer-токенов и httpOnly cookie
- Система заявок на прикрепление студента к преподавателю (pending → accepted / rejected)
- Создание заданий преподавателем: название, описание, дедлайн, привязка к группе и курсу, загрузка файлов (PDF, изображения, DOC/DOCX)
- Фильтрация заданий по статусу: активные (дедлайн не наступил) и завершённые (дедлайн прошёл, но не более 7 дней назад)
- **Горящие задания** — задания с дедлайном менее 7 дней от текущей даты
- Фоновая задача автоматической очистки заданий старше 7 дней после дедлайна
- Панель администратора: статистика, управление пользователями и группами, одобрение/отклонение преподавателей
- Профиль пользователя с редактированием имени, группы, курса, кафедры
- Серверный рендеринг (Jinja2) + ванильный JavaScript на клиенте

---

## Архитектура

```
Academic-flow/
├── alembic.ini                      # Конфигурация Alembic
├── migrations/                       # Миграции БД (Alembic)
│   ├── versions/                     # 10 версий миграций
│   ├── env.py                        # Асинхронная среда Alembic
│   └── script.py.mako               # Шаблон новых миграций
├── src/
│   ├── config.py                     # Pydantic Settings (.env)
│   ├── database.py                   # Асинхронный движок SQLAlchemy + Base
│   ├── main.py                       # Точка входа FastAPI + lifespan
│   ├── admin/
│   │   └── router.py                 # API админ-панели (/api/admin)
│   ├── auth/
│   │   ├── models.py                 # User, UserConnection (ORM)
│   │   ├── schemas.py                # Pydantic-схемы (регистрация, профиль, связи)
│   │   ├── service.py                # UserDAO — слой доступа к пользователям
│   │   ├── dependencies.py           # Зависимости: get_current_user, get_current_student, и т.д.
│   │   ├── utils.py                  # bcrypt, создание JWT
│   │   ├── router.py                 # Эндпоинты аутентификации (/auth)
│   │   ├── connection_service.py     # ConnectionDAO — слой доступа к связям
│   │   └── connections_router.py     # Эндпоинты связей (/auth/connections)
│   ├── tasks/
│   │   ├── models.py                 # Task (ORM)
│   │   ├── schemas.py                # Зарезервировано
│   │   └── router.py                 # API заданий (/api/tasks)
│   └── frontend/
│       ├── router.py                 # Маршруты страниц (Jinja2)
│       ├── templates/                # HTML-шаблоны (17 страниц)
│       └── static/
│           ├── css/style.css         # Единый файл стилей (1494 строки)
│           └── js/                   # Клиентская логика (auth, dashboard, profile, и т.д.)
└── .env.example                      # Пример конфигурации
```

### Компоненты

| Компонент | Назначение |
|-----------|------------|
| `main.py` | Инициализация FastAPI, монтирование статики, подключение роутеров, фоновая задача очистки |
| `config.py` | Загрузка конфигурации из переменных окружения и `.env` |
| `database.py` | Асинхронный движок SQLAlchemy, фабрика сессий, декларативная база |
| `auth/` | Регистрация, логин, профиль, JWT, связи студент-преподаватель |
| `tasks/` | CRUD заданий, загрузка файлов, фильтрация по статусу |
| `admin/` | Статистика, пользователи, группы, одобрение преподавателей |
| `frontend/` | Серверный рендеринг (Jinja2), статические файлы, клиентские скрипты |

---

## Стек технологий

| Технология | Назначение |
|------------|------------|
| Python 3.11+ | Язык программирования |
| FastAPI | Веб-фреймворк (асинхронный) |
| SQLAlchemy 2.x (asyncio) | ORM для работы с базой данных |
| asyncpg | Асинхронный драйвер PostgreSQL |
| Alembic | Управление миграциями БД |
| Pydantic v2 + pydantic-settings | Валидация данных и конфигурация |
| Jinja2 | Шаблонизатор (серверный рендеринг) |
| python-jose (JWT) | Создание и верификация JWT-токенов |
| bcrypt | Хеширование паролей |
| Vanilla JavaScript | Клиентская логика (без фреймворков) |
| CSS | Оформление (один файл, без препроцессоров) |

---

## Требования

- **Python** ≥ 3.11
- **PostgreSQL** ≥ 14
- **pip** (менеджер пакетов)

---

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/<пользователь>/Academic-flow.git
cd Academic-flow
```

### 2. Виртуальное окружение и зависимости

```bash
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows
```

Установите зависимости:

```bash
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic pydantic pydantic-settings pydantic[email] python-jose[cryptography] bcrypt jinja2 python-multipart aiofiles
```

### 3. Настройка базы данных

Создайте базу данных в PostgreSQL:

```sql
CREATE DATABASE "Academic-flow-FASTAPI";
```

Скопируйте файл конфигурации:

```bash
cp .env.example .env
```

Отредактируйте `.env`, указав актуальные параметры подключения:

```
DATABASE_URL=postgresql+asyncpg://postgres:your_password@127.0.0.1:5432/Academic-flow-FASTAPI
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 4. Применение миграций

```bash
alembic upgrade head
```

### 5. Запуск

```bash
uvicorn src.main:app --reload
```

Приложение будет доступно по адресу: **http://127.0.0.1:8000**

---

## Учётные записи по умолчанию

При первом входе администратор создаётся автоматически:

| Email | Пароль | Роль |
|-------|--------|------|
| `admin@mail.ru` | `1234567890` | Администратор |

---

## API-эндпоинты

### Аутентификация

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/auth/register` | Регистрация пользователя |
| POST | `/auth/login` | Вход в систему |
| GET | `/auth/me` | Информация о текущем пользователе |
| POST | `/auth/logout` | Выход |
| PUT | `/auth/profile/update` | Обновление профиля |

### Связи студент-преподаватель

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/auth/connections/request` | Отправить заявку преподавателю |
| POST | `/auth/connections/respond` | Ответить на заявку (accept/reject) |
| GET | `/auth/connections/my-teachers` | Мои преподаватели |
| GET | `/auth/connections/my-students` | Мои студенты |
| DELETE | `/auth/connections/detach/{id}` | Открепить студента |

### Задания

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/tasks/list` | Список заданий (active / completed) |
| POST | `/api/tasks/create` | Создать задание (multipart) |
| DELETE | `/api/tasks/{id}` | Удалить задание |
| POST | `/api/tasks/{id}/complete` | Принудительно завершить задание |
| GET | `/api/tasks/my-groups` | Группы преподавателя |
| POST | `/api/tasks/cleanup` | Ручная очистка просроченных заданий |

### Администрирование

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/admin/stats` | Статистика системы |
| GET | `/api/admin/users` | Список пользователей |
| DELETE | `/api/admin/users/{id}` | Удалить пользователя |
| GET | `/api/admin/groups` | Список групп |
| POST | `/auth/admin/approve/{id}` | Одобрить преподавателя |
| POST | `/auth/admin/reject/{id}` | Отклонить преподавателя |

---

## Страницы фронтенда

| Путь | Страница |
|------|----------|
| `/` | Главная |
| `/login` | Вход |
| `/register` | Регистрация |
| `/dashboard/student` | Кабинет студента |
| `/dashboard/teacher` | Кабинет преподавателя |
| `/profile` | Профиль пользователя |
| `/teachers` | Список преподавателей |
| `/students` | Список студентов |
| `/tasks/my` | Мои задания (студент) |
| `/teacher/tasks` | Выданные задания (преподаватель) |
| `/tasks/burning` | Горящие задания 🔥 |
| `/teacher/groups` | Группы преподавателя |
| `/admin/panel` | Панель администратора |
| `/waiting-approval` | Ожидание подтверждения |

---

## Модели данных

### User (`users`)

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer, PK | Идентификатор |
| email | String(320), unique, index | Электронная почта |
| hashed_password | String(1024) | Хеш пароля (bcrypt) |
| role | Enum(student/teacher) | Роль пользователя |
| is_active | Boolean | Активен ли аккаунт |
| is_verified | Boolean | Подтверждён ли email |
| is_admin | Boolean | Администратор |
| is_approved | Boolean | Одобрен ли преподаватель |
| first_name | String(100) | Имя |
| last_name | String(100) | Фамилия |
| patronymic | String(100) | Отчество |
| group_name | String(50) | Группа (для студентов) |
| course_number | Integer | Курс (для студентов) |
| department | String(200) | Кафедра (для преподавателей) |

### Task (`tasks`)

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer, PK | Идентификатор |
| teacher_id | Integer, FK → users.id | Преподаватель |
| course_number | Integer | Номер курса |
| group_name | String(50), index | Группа |
| title | String(300) | Название задания |
| description | Text | Описание |
| deadline | DateTime(tz) | Дедлайн |
| file_paths | Text | JSON-список путей к файлам |
| file_original_name | String(500) | JSON-список оригинальных имён |
| created_at | DateTime(tz) | Дата создания |

### UserConnection (`user_connections`)

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer, PK | Идентификатор |
| student_id | Integer, FK → users.id | Студент |
| teacher_id | Integer, FK → users.id | Преподаватель |
| status | Enum(pending/accepted/rejected) | Статус связи |
| *UniqueConstraint(student_id, teacher_id)* | | Уникальная пара |

---

## Фоновая задача

При старте приложения запускается асинхронная фоновая задача, которая каждый час удаляет задания, чей дедлайн наступил более 7 дней назад. Файлы таких заданий также удаляются с диска.

---

## Разработка

Проект не содержит `requirements.txt` или `pyproject.toml` — зависимости устанавливаются вручную через `pip`. Рекомендуется оформить файл зависимостей для воспроизводимости окружения (например, `requirements.txt` или `pyproject.toml` с Poetry).

Миграции создаются через Alembic:

```bash
alembic revision --autogenerate -m "описание_изменения"
alembic upgrade head
```

---

## Лицензия

Проект распространяется без указания лицензии. Все права принадлежат автору.
