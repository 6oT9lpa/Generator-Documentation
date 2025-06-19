

## Part 1
# Документация к `__init__.py`

## Содержание
- [Класс Users](#класс-users)
  - [Методы Users](#методы-users)
- [Класс OrderVegetable](#класс-ordervegetable)
- [Класс Dish](#класс-dish)
- [Используемые библиотеки](#используемые-библиотеки)

---

## Класс Users

Модель пользователя системы с аутентификацией и ролями. Хранит данные для входа и связи с заказами.

**Атрибуты:**
- `id` - уникальный идентификатор (Integer, PK)
- `login` - логин пользователя (String(45), уникальный)
- `password` - хэш пароля (String(255))
- `role` - роль пользователя (String(25))

### Методы Users

#### `set_password(password: str) -> None`
Устанавливает хэшированный пароль для пользователя.

**Сложность:** O(1)  
**Параметры:**
- `password` - пароль в открытом виде

**Использует:**  
`werkzeug.security.generate_password_hash`

---

#### `check_password(password: str) -> bool`
Проверяет соответствие введенного пароля хэшу.

**Сложность:** O(1)  
**Параметры:**
- `password` - пароль для проверки

**Возвращает:**  
`True` если пароль верный, иначе `False`

**Использует:**  
`werkzeug.security.check_password_hash`

---

**Связи:**
- `authored_orders` - заказы, созданные пользователем (One-to-Many)
- `cooked_orders` - заказы, приготовленные пользователем (One-to-Many)

---

## Класс OrderVegetable

Модель заказа овощей с отслеживанием статуса.

**Атрибуты:**
- `id` - уникальный идентификатор (Integer, PK)
- `author_id` - ID автора заказа (FK к Users.id)
- `cooker` - ID повара (FK к Users.id, nullable)
- `list_product` - список продуктов (String)
- `action` - действие с заказом (String(25))
- `status` - статус заказа (String(20), default="в ожидании")
- `created_at` - дата создания (DateTime, auto-now)
- `completed_at` - дата завершения (DateTime, nullable)

**Связи:**
- `author` - связь с автором заказа (Many-to-One)
- `cooker_user` - связь с поваром (Many-to-One)

---

## Класс Dish

Модель блюда в системе.

**Атрибуты:**
- `id` - уникальный идентификатор (Integer, PK)
- `name` - название блюда (String)

**Метод:**
- `__repr__()` - строковое представление объекта

---

## Используемые библиотеки

1. **SQLAlchemy** - ORM для работы с БД
   - `create_engine` - создание подключения
   - `declarative_base` - базовый класс для моделей
   - `sessionmaker` - управление сессиями

2. **Werkzeug Security** - хэширование паролей
   - `generate_password_hash`
   - `check_password_hash`

3. **Datetime** - работа с датами
   - `datetime.now` - текущая дата/время