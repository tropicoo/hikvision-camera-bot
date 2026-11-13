# Hikvision Camera Bot на Raspberry Pi 4 (Docker)

Инструкция для Raspberry Pi 4 (4 ГБ ОЗУ, карта памяти/флешка на 64 ГБ). Также подходит для Pi 5.

## 1. Требования

- **64-битная** Raspberry Pi OS (Bookworm или новее). Проверка:
  ```bash
  uname -m
  ```
  Должно быть `aarch64`. На 32-битной системе (`armv7l`) часть Python-библиотек придётся
  компилировать, сборка будет долгой и может не пройти.
- Охлаждение (радиатор/вентилятор). При ~80°C Raspberry Pi начинает сбрасывать частоту,
  бот пришлёт предупреждение.
- Хорошее питание (официальный блок 5V/3A).

## 2. Установка Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

После этого перезайдите в систему (или перезагрузите Pi), чтобы `docker` работал без `sudo`.

## 3. Первая установка бота

```bash
git clone https://github.com/SA1D77/hikvision-camera-bot.git
cd hikvision-camera-bot
cp configs/config-template.json configs/config.json
cp configs/livestream_templates-template.json configs/livestream_templates.json
cp configs/encoding_templates-template.json configs/encoding_templates.json
nano configs/config.json   # токен бота, api_id/api_hash, камеры, chat_users
nano .env                  # часовой пояс, например TZ=Asia/Tashkent
sudo mkdir -p /data/dvr /data/timelapses
docker compose build && docker compose up -d
```

Первая сборка на Pi 4 занимает несколько минут.

## 4. Обновление

```bash
cd hikvision-camera-bot
./update.sh
```

Скрипт скачивает новую версию, пересобирает образ, перезапускает контейнеры и удаляет старые
образы, чтобы не занимать место на флешке. Конфиги `configs/*.json` не трогаются (их нет в git).
Если вы меняли `docker-compose.yml` или `.env`, скрипт сохранит и вернёт ваши изменения.

Если бот уже установлен из оригинального репозитория `tropicoo/hikvision-camera-bot`,
один раз переключите источник и обновитесь:

```bash
cd hikvision-camera-bot
git remote set-url origin https://github.com/SA1D77/hikvision-camera-bot.git
./update.sh   # если файла ещё нет: git pull && bash update.sh
```

## 5. Полезные команды

```bash
docker compose ps                                     # состояние (healthy / unhealthy)
docker compose logs -f --tail 200 hikvision-camera-bot   # логи бота
docker compose restart hikvision-camera-bot           # перезапуск бота
docker compose stop                                   # остановка
df -h                                                 # свободное место
vcgencmd measure_temp                                 # температура CPU
```

В Telegram:

- `/menu` или кнопка «📋 Меню» (появляется вместе с сообщением о запуске бота или после
  `/start`) — панель управления камерами:
  фото, видео, оповещения, ИК-режим. Панель — одно сообщение, которое обновляется на месте;
  в «⚙️ Настройки» включаются детекции, выбирается, что присылать при тревоге, и пауза между
  тревогами. Эти настройки сохраняются в `configs/config.json` (копия — `config.json.bak`);
- `/status` — время работы, температура CPU, ОЗУ, свободное место и запущенные сервисы;
- `/help` — справка: что умеет бот, основные команды и что делать при проблемах;
- `/version` — версия бота и есть ли обновление.

## 6. Что делать, если…

| Что видно | Что делать |
|-----------|------------|
| «📡 Камера не отвечает» | Проверьте питание камеры, кабель или Wi-Fi и IP-адрес камеры (`host`) в `configs/config.json`. |
| «🔑 Камера отклонила логин или пароль» | Исправьте `user` / `password` камеры в `configs/config.json` и перезапустите бота: `docker compose restart hikvision-camera-bot`. После нескольких неверных попыток камера может на время заблокировать пользователя. |
| «⚠️ Камера вернула ошибку» | Скорее всего, функция не поддерживается камерой или выключена в её веб-интерфейсе. |
| Пришло «📡 Нет связи с камерой» | Связи с камерой нет больше минуты, тревоги с неё не приходят. Бот переподключается сам и пришлёт «✅ Камера снова на связи». |
| Не приходят тревоги | Откройте `/menu`: оповещения и нужные детекции должны быть отмечены ✅. В `/status` видно, какие службы запущены. |
| Бот не отвечает | `docker compose ps` (должно быть `healthy`), затем `docker compose logs --tail 100 hikvision-camera-bot` и `docker compose restart hikvision-camera-bot`. Проверьте, что ваш Telegram ID есть в `chat_users`. |
| «⚠️ Мало места на диске» | Удалите старые записи DVR или перенесите хранилище на диск побольше. |
| «🔥 Процессор перегревается» | Проверьте охлаждение (радиатор, вентилятор), не перекодируйте видео без необходимости. |

При недоступной камере в логах одна строка на попытку. Полный traceback включается
параметром `"log_level": "DEBUG"` в `configs/config.json`.

## 7. Советы для Raspberry Pi

1. **Не перекодируйте видео без необходимости.** Перекодирование в x264/VP9 (стримы на YouTube,
   Telegram, Icecast, DVR с `encoding_template` не `direct`) сильно грузит CPU Pi 4. Шаблоны
   `direct.*` (`-c:v copy`) почти не нагружают процессор.
2. **DVR лучше писать на USB-SSD/HDD, а не на карту памяти.** Постоянная запись изнашивает
   SD-карту. Подключите диск и укажите его путь в `docker-compose.yml`, например
   `"/mnt/ssd/dvr:/data/dvr"`.
3. **Следите за местом.** Бот сам пришлёт предупреждение, если свободно меньше 10% или 2 ГБ.
   Для DVR включите `delete_after_upload` или периодически чистите старые записи.
4. **Таймлапсы:** оставьте в шаблоне `"threads": 1`, `"nice_value": 19` и
   `"custom_ffmpeg_args": "-preset ultrafast"`, тогда создание видео не мешает остальным задачам.
5. **Временные видео** (`video_gif.tmp_storage` = `/tmp`) хранятся в оперативной памяти
   (tmpfs 512 МБ), поэтому не изнашивают карту.
6. **Логи Docker** ограничены 3 файлами по 10 МБ на контейнер и не заполнят диск.
7. **SRS-сервер** нужен только для «видео с перемоткой» и ретрансляции. Если не пользуетесь,
   оставьте `"enabled": false` в секции `livestream.srs` конфига камеры.
8. **Автозапуск:** контейнеры запускаются с `restart: always`, поэтому бот поднимается после
   перезагрузки Pi, даже если до этого его останавливали командой `docker stop`.
