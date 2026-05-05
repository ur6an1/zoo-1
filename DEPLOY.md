# 🚀 Деплой ZooBuddy на VPS

Пошаговая инструкция заливки и запуска бота на Linux-сервере.

---

## 0. Автоматический доступ по SSH (без пароля)

Чтобы `deploy.sh` и команды `ssh`/`rsync` не спрашивали пароль при каждом запуске, настройте вход по ключу **один раз**.

### На вашем компьютере (Mac/Linux)

**Шаг 1.** Проверьте, есть ли уже ключ:
```bash
ls -la ~/.ssh/id_ed25519.pub   # или id_rsa.pub
```
Если файла нет — создайте ключ:
```bash
ssh-keygen -t ed25519 -C "zoo_bot_deploy" -f ~/.ssh/id_ed25519 -N ""
```

**Шаг 2.** Скопируйте ключ на VPS (подставьте свой IP и пользователя):
```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@ВАШ_IP
```
Введите пароль от сервера **последний раз** — дальше вход будет по ключу.

**Шаг 3.** Проверьте: подключение без пароля должно сработать:
```bash
ssh root@ВАШ_IP "echo OK"
```

Готово. Теперь `./deploy.sh` будет работать без запроса пароля.

---

## 1. Подготовка VPS

- Сервер: любой Linux (Ubuntu 22.04, Debian 12 и т.п.).
- Подключение: `ssh root@ВАШ_IP` (или пользователь с sudo).

Убедитесь, что установлен Python 3.11+:

```bash
python3 --version
# Если нет — Ubuntu/Debian:
sudo apt update && sudo apt install -y python3 python3-venv python3-pip
```

---

## 2. Заливка проекта на сервер

### Вариант A: через скрипт (с вашего компьютера)

Отредактируйте в файле `deploy.sh` переменные:
- `VPS_HOST` — IP или домен сервера
- `VPS_USER` — пользователь (например `root` или `deploy`)
- `APP_DIR` — каталог на сервере (например `/opt/zoo_bot`)

Запуск:

```bash
chmod +x deploy.sh
./deploy.sh
```

Скрипт зальёт файлы через `rsync` и при необходимости создаст venv и установит зависимости.

### Вариант B: вручную

На вашем компьютере (из папки ZOO_BOT):

```bash
rsync -avz --exclude 'venv' --exclude '.env' --exclude '*.db' --exclude '__pycache__' --exclude '*.log' \
  ./ USER@SERVER_IP:/opt/zoo_bot/
```

Или через `scp` архива:

```bash
tar --exclude='venv' --exclude='.env' --exclude='*.db' --exclude='__pycache__' -czvf zoo_bot.tar.gz .
scp zoo_bot.tar.gz USER@SERVER_IP:/opt/
# На сервере:
ssh USER@SERVER_IP "cd /opt && mkdir -p zoo_bot && tar -xzvf zoo_bot.tar.gz -C zoo_bot"
```

---

## 3. Настройка на сервере

Подключитесь к VPS и перейдите в каталог проекта:

```bash
ssh USER@SERVER_IP
cd /opt/zoo_bot   # или тот путь, куда залили
```

### Виртуальное окружение и зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Файл .env

```bash
cp .env.example .env
nano .env
```

Заполните (обязательно замените на свой токен):

```
BOT_TOKEN=123456789:ABCdefGHI...
DATABASE_URL=sqlite+aiosqlite:///./zoo_bot.db
```

Сохраните (Ctrl+O, Enter, Ctrl+X).

---

## 4. Запуск через systemd (рекомендуется)

Так бот будет автоматически стартовать после перезагрузки и перезапускаться при падении.

Скопируйте unit-файл (он уже в репозитории):

```bash
sudo cp zoo_bot.service /etc/systemd/system/
```

Отредактируйте пути, если проект лежит не в `/opt/zoo_bot`:

```bash
sudo nano /etc/systemd/system/zoo_bot.service
```

Проверьте строки `WorkingDirectory` и `ExecStart` (должны указывать на ваш каталог и `venv/bin/python`).

Включите и запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable zoo_bot
sudo systemctl start zoo_bot
sudo systemctl status zoo_bot
```

Полезные команды:

| Действие        | Команда                    |
|-----------------|----------------------------|
| Логи            | `sudo journalctl -u zoo_bot -f` |
| Перезапуск      | `sudo systemctl restart zoo_bot` |
| Остановка       | `sudo systemctl stop zoo_bot`   |

---

## 5. Проверка

- В Telegram откройте бота и отправьте `/start`.
- На сервере посмотрите логи: `sudo journalctl -u zoo_bot -f` — не должно быть ошибок.

---

## 6. Обновление бота (после изменений в коде)

С вашего компьютера снова запустите деплой:

```bash
./deploy.sh
```

На сервере перезапустите сервис:

```bash
sudo systemctl restart zoo_bot
```

Если заливаете вручную — после `rsync`/копирования на сервере:

```bash
cd /opt/zoo_bot && source venv/bin/activate && pip install -r requirements.txt
sudo systemctl restart zoo_bot
```

---

## Краткий чеклист

- [ ] VPS с Python 3.11+
- [ ] Файлы проекта залиты в `/opt/zoo_bot` (или свой путь)
- [ ] Создан `venv`, установлены `requirements.txt`
- [ ] Файл `.env` с реальным `BOT_TOKEN`
- [ ] Сервис `zoo_bot.service` установлен и включён
- [ ] `systemctl status zoo_bot` — active (running)
- [ ] Бот отвечает в Telegram на `/start`

Готово. Бот работает на VPS.
