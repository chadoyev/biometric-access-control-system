# Biometric Access Control System

Программно-аппаратный комплекс локальной биометрической идентификации на базе Raspberry Pi 5. Система обеспечивает контроль доступа в помещение с использованием распознавания лиц, RFID-карт и одноразовых кодов доступа. Управление осуществляется через Telegram-бота.

## Возможности

- **Распознавание лиц** — бесконтактная идентификация через IP-камеру с использованием библиотеки `face_recognition` (dlib)
- **Антиспуфинг** — защита от попыток обмана системы фотографиями, видео и масками на базе [Silent-Face-Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing)
- **RFID-идентификация** — вход по RFID-карте через модуль RC-522
- **Одноразовые коды доступа** — генерация временных кодов для гостевого доступа
- **Telegram-бот** — полноценный интерфейс управления: регистрация пользователей, настройка модификаторов доступа, просмотр статистики и истории посещений
- **Модификаторы доступа** — гибкое расписание доступа по дням недели и времени
- **Уведомления** — мгновенные уведомления в Telegram при каждой попытке входа с фото
- **Статистика и история** — формирование HTML-отчёта с фильтрацией по дате и пользователю
- **Сервисные функции** — настройка камеры, антиспуфинга, звуковых уведомлений, удалённая перезагрузка

## Архитектура системы

Система работает в 4 параллельных потока:

| Поток | Назначение |
|---|---|
| `CaptureFrames` | Непрерывный захват кадров с камеры |
| `FaceDetection` | Детекция лиц, антиспуфинг-проверка, распознавание |
| `RFIDListener` | Прослушивание RFID-считывателя и кнопки выхода |
| `MainLoop` | Telegram-бот (обработка команд и сообщений) |

## Аппаратные компоненты

| # | Компонент | Модель | Назначение |
|---|---|---|---|
| 1 | Микрокомпьютер | **Raspberry Pi 5 (8GB)** | Центральный узел обработки |
| 2 | RFID-считыватель | **RC-522** | Считывание RFID-карт/меток |
| 3 | Релейный модуль | **3.3V Relay Module** | Управление электромагнитным замком |
| 4 | Электромагнитный замок | **ST-ML60-1** | Запирающий механизм двери |
| 5 | IP-камера | **Procon IB4-PM** (или другая RTSP-камера) | Видеопоток для распознавания |
| 6 | Зелёный светодиод | — | Индикатор: доступ разрешён |
| 7 | Красный светодиод | — | Индикатор: дверь закрыта |
| 8 | Кнопка выхода | **ST-EXB-M02** | Открытие двери изнутри |
| 9 | Зуммер/динамик | — | Звуковое уведомление |
| 10 | Блок питания | **ST-12/2 (12V, 2A)** | Питание электромагнита |
| 11 | Резисторы | **1 кОм (x2)** | Для светодиодов |

## Схема подключения

![Схема подключения компонентов](connection_scheme.png)

### Распиновка GPIO (Raspberry Pi 5)

| Компонент | Пин | GPIO |
|---|---|---|
| **RFID RC-522** | | |
| 3.3V | 3.3V | — |
| GND | GND | — |
| SDA | GPIO 7 | SPI CE0 |
| SCK | GPIO 11 | SPI SCLK |
| MOSI | GPIO 10 | SPI MOSI |
| MISO | GPIO 9 | SPI MISO |
| **Релейный модуль** | | |
| DC+ | 3.3V | — |
| DC- | GND | — |
| IN | GPIO 4 | — |
| **Зелёный LED** | | |
| Анод (+) через 1кОм | GPIO 16 | — |
| Катод (-) | GND | — |
| **Красный LED** | | |
| Анод (+) через 1кОм | GPIO 26 | — |
| Катод (-) | GND | — |
| **Кнопка выхода** | | |
| COM | 3.3V | — |
| NO | GPIO 17 | — |
| **Зуммер** | | |
| + | GPIO 13 | — |
| - | GND | — |

## Развёртывание на Raspberry Pi 5

### Предварительные требования

- Raspberry Pi 5 (8GB RAM) с установленной **Raspberry Pi OS (64-bit, Bookworm)**
- microSD-карта минимум 32 ГБ (рекомендуется 64 ГБ)
- Ethernet-подключение к локальной сети
- IP-камера в той же сети или USB-камера
- Все аппаратные компоненты подключены согласно схеме

### Шаг 1. Начальная настройка Raspberry Pi OS

Запишите Raspberry Pi OS (64-bit) на microSD с помощью [Raspberry Pi Imager](https://www.raspberrypi.com/software/). При записи:

- Включите SSH
- Задайте имя пользователя и пароль
- Настройте Wi-Fi/Ethernet

### Шаг 2. Отключение графического рабочего стола

> **Важно!** Для установки `dlib` требуется максимум оперативной памяти. Графический рабочий стол потребляет ~300-500 МБ RAM. Рекомендуется отключить его и работать через SSH.

```bash
# Подключитесь к Raspberry Pi по SSH
ssh <username>@<ip-адрес>

# Переключитесь в режим CLI (без рабочего стола)
sudo raspi-config
# Выберите: System Options → Boot / Auto Login → Console Autologin
# Перезагрузите: Finish → Reboot

# Или одной командой:
sudo systemctl set-default multi-user.target
sudo reboot
```

Для восстановления рабочего стола после установки:
```bash
sudo systemctl set-default graphical.target
sudo reboot
```

### Шаг 3. Увеличение SWAP-файла

Компиляция `dlib` требует значительного объёма памяти. Увеличьте swap до 2 ГБ:

```bash
sudo dphys-swapfile swapoff

sudo nano /etc/dphys-swapfile
# Измените строку:
# CONF_SWAPSIZE=2048

sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Проверка:
free -h
```

### Шаг 4. Включение интерфейса SPI

SPI необходим для работы RFID-считывателя RC-522:

```bash
sudo raspi-config
# Выберите: Interface Options → SPI → Enable

# Или через редактирование конфига:
echo "dtparam=spi=on" | sudo tee -a /boot/firmware/config.txt
sudo reboot
```

Проверка:
```bash
ls /dev/spidev*
# Должно отобразиться: /dev/spidev0.0 /dev/spidev0.1
```

### Шаг 5. Установка системных зависимостей

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    cmake \
    gfortran \
    libatlas-base-dev \
    liblapack-dev \
    libopenblas-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libhdf5-dev \
    libhdf5-serial-dev \
    libhdf5-103 \
    libqt5gui5 \
    libqt5webkit5 \
    libqt5test5 \
    libboost-all-dev \
    git \
    pkg-config
```

### Шаг 6. Клонирование репозитория

```bash
cd ~
git clone https://github.com/chadoyev/biometric-access-control-system.git
cd biometric-access-control-system
```

### Шаг 7. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

### Шаг 8. Установка dlib

> **Это самый сложный и длительный этап.** Компиляция `dlib` на Raspberry Pi 5 занимает **20–40 минут**. Обязательно работайте через SSH с отключённым рабочим столом.

```bash
# Убедитесь, что swap увеличен (Шаг 3)
# Убедитесь, что рабочий стол отключён (Шаг 2)

pip install dlib
```

Если установка завершается с ошибкой нехватки памяти:

```bash
# Вариант 1: Установка с ограничением параллельных процессов сборки
CMAKE_BUILD_PARALLEL_LEVEL=2 pip install dlib

# Вариант 2: Сборка из исходников вручную
cd ~
git clone https://github.com/davisking/dlib.git
cd dlib
mkdir build && cd build
cmake .. -DDLIB_USE_CUDA=0 -DUSE_AVX_INSTRUCTIONS=0 -DUSE_SSE2_INSTRUCTIONS=0 -DUSE_SSE4_INSTRUCTIONS=0
cmake --build . --config Release -- -j2
cd ..
python setup.py install
cd ~/biometric-access-control-system
```

Проверка:
```bash
python3 -c "import dlib; print(dlib.DLIB_USE_CUDA)"
```

### Шаг 9. Установка остальных зависимостей

```bash
pip install face_recognition
pip install opencv-python-headless
pip install pyTelegramBotAPI
pip install numpy
pip install pandas
pip install Pillow
pip install spidev
pip install lgpio
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install easydict
pip install tqdm
pip install tensorboardX
pip install imutils
```

> **Примечание:** На Raspberry Pi используется `opencv-python-headless` вместо `opencv-python`, так как графический интерфейс не требуется. Для PyTorch берётся CPU-версия, так как на RPi 5 нет CUDA.

### Шаг 10. Создание Telegram-бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`, задайте имя и username
3. Скопируйте полученный API-токен
4. Узнайте свой Telegram ID — отправьте любое сообщение боту [@userinfobot](https://t.me/userinfobot)

### Шаг 11. Настройка конфигурации

Откройте `main.py` и укажите:

```python
ADMIN_ID = 123456789         # Ваш Telegram user ID
API_TOKEN = 'ваш_токен_бота' # Токен от BotFather
```

### Шаг 12. Настройка IP-камеры

В базе данных `db.db` таблица `config` содержит настройки камеры. По умолчанию камера настраивается через Telegram-бот после первого запуска.

Для IP-камеры укажите RTSP-адрес, например:
```
rtsp://admin:password@192.168.1.100:554/stream1
```

Для USB-камеры укажите индекс:
```
0
```

### Шаг 13. Запуск системы

```bash
cd ~/biometric-access-control-system
source venv/bin/activate
sudo venv/bin/python main.py
```

> **Примечание:** `sudo` необходим для доступа к GPIO и SPI.

### Шаг 14. Автозапуск при загрузке (systemd)

Создайте сервис для автоматического запуска при включении Raspberry Pi:

```bash
sudo nano /etc/systemd/system/biometric.service
```

Содержимое файла:
```ini
[Unit]
Description=Biometric Access Control System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/<username>/biometric-access-control-system
ExecStart=/home/<username>/biometric-access-control-system/venv/bin/python main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

> Замените `<username>` на имя вашего пользователя.

```bash
sudo systemctl daemon-reload
sudo systemctl enable biometric.service
sudo systemctl start biometric.service

# Проверка статуса:
sudo systemctl status biometric.service

# Просмотр логов:
sudo journalctl -u biometric.service -f
```

## Структура проекта

```
biometric-access-control-system/
├── main.py                          # Основной модуль системы
├── FaceRegister.py                  # Скрипт регистрации биометрии лиц
├── MFRC522.py                       # Драйвер RFID-считывателя RC-522 (SPI)
├── requirements.txt                 # Зависимости (AntiSpoofing)
├── db.db                            # SQLite база данных
├── connection_scheme.png            # Схема подключения компонентов
├── unknown.jpg                      # Изображение-заглушка
├── files/                           # Фотографии зарегистрированных пользователей
│   └── 123456/
│       └── unknown.jpg              # Заглушка для неизвестных лиц
├── photo_entry/                     # Фото при каждой попытке входа
├── AntiSpoofing/                    # Модуль антиспуфинга
│   ├── test.py                      # Тестирование антиспуфинга с камеры
│   ├── train.py                     # Обучение модели антиспуфинга
│   ├── resources/
│   │   ├── anti_spoof_models/       # Предобученные модели
│   │   │   ├── 2.7_80x80_MiniFASNetV2.pth
│   │   │   └── 4_0_0_80x80_MiniFASNetV1SE.pth
│   │   └── detection_model/         # Модель детектора лиц (RetinaFace)
│   │       ├── deploy.prototxt
│   │       └── Widerface-RetinaFace.caffemodel
│   └── src/
│       ├── anti_spoof_predict.py    # Предсказание (реальное/поддельное лицо)
│       ├── generate_patches.py      # Вырезание патчей лиц
│       ├── utility.py               # Утилиты
│       ├── default_config.py        # Конфигурация обучения
│       ├── train_main.py            # Логика обучения
│       ├── model_lib/
│       │   ├── MiniFASNet.py        # Архитектура MiniFASNet
│       │   └── MultiFTNet.py        # Архитектура MultiFTNet
│       └── data_io/
│           ├── dataset_folder.py    # Загрузка датасета
│           ├── dataset_loader.py    # DataLoader
│           ├── transform.py         # Аугментации
│           └── functional.py        # Функции трансформации
└── Отчёт/
    └── Выпускная квалификационная работа бакалавра Чадоев И.М. АВТ-013.pdf
```

## База данных

SQLite-база `db.db` содержит следующие таблицы:

| Таблица | Назначение |
|---|---|
| `users` | Пользователи Telegram-бота (ID, имя, статус верификации, телефон) |
| `visitors` | Зарегистрированные посетители (ФИО, должность, фото, UID RFID-карты) |
| `visit_history` | История всех попыток входа (дата, тип, успешность, спуфинг, фото) |
| `access_modifiers` | Расписание доступа (день недели, время начала/окончания) |
| `list_access_codes` | Одноразовые коды доступа (код, срок действия, статус) |
| `config` | Настройки системы (камера, уведомления, антиспуфинг и др.) |

## Способы входа в помещение

| Способ | Описание |
|---|---|
| **Биометрия лица** | Автоматическое распознавание при приближении к камере |
| **RFID-карта** | Поднесение зарегистрированной карты к считывателю |
| **Одноразовый код** | Ввод кода в Telegram-боте (для гостей) |
| **Telegram-бот** | Кнопка «Открыть дверь» в интерфейсе бота |
| **Кнопка выхода** | Физическая кнопка внутри помещения |

## Устранение неполадок

### dlib не компилируется / killed

- Отключите рабочий стол: `sudo systemctl set-default multi-user.target && sudo reboot`
- Увеличьте swap до 2048 МБ
- Ограничьте параллелизм: `CMAKE_BUILD_PARALLEL_LEVEL=2 pip install dlib`
- Закройте все лишние процессы перед установкой

### RFID-считыватель не работает

- Проверьте включён ли SPI: `ls /dev/spidev*`
- Проверьте подключение проводов к GPIO по таблице
- Убедитесь, что установлен `spidev`: `pip install spidev`

### Камера не подключается

- Для USB-камеры: `ls /dev/video*` — убедитесь, что устройство видно
- Для IP-камеры: проверьте, что RPi и камера в одной сети, RTSP-адрес корректен
- Тест: `python3 -c "import cv2; cap=cv2.VideoCapture(0); print(cap.isOpened())"`

### Бот не отвечает

- Проверьте, что `API_TOKEN` и `ADMIN_ID` заданы корректно в `main.py`
- Проверьте подключение к интернету: `ping api.telegram.org`
- Проверьте логи: `sudo journalctl -u biometric.service -f`

## Антиспуфинг

Модуль антиспуфинга основан на проекте [Silent-Face-Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing) от Minivision AI. Используется метод на основе анализа Фурье-спектрограмм для вспомогательного обучения, с архитектурой на базе MiniFASNet — облегчённой версии MobileFaceNet.

Модели в `AntiSpoofing/resources/anti_spoof_models/`:
- `2.7_80x80_MiniFASNetV2.pth` — MiniFASNetV2 (scale 2.7, 80x80)
- `4_0_0_80x80_MiniFASNetV1SE.pth` — MiniFASNetV1SE (scale 4.0, 80x80)

Система анализирует несколько кадров подряд и принимает решение по принципу большинства голосов. Количество кадров для проверки настраивается через Telegram-бот.

## Лицензия

Антиспуфинг-модуль — [Apache 2.0](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/blob/master/LICENSE) (Minivision AI).

