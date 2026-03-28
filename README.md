<div align="center">

# 🔐 Biometric Access Control System

**[🇬🇧 English](#english) · [🇷🇺 Русский](#russian)**

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%205-red?logo=raspberrypi)
![License](https://img.shields.io/badge/AntiSpoofing%20License-Apache%202.0-green)
![Telegram](https://img.shields.io/badge/Control-Telegram%20Bot-blue?logo=telegram)

</div>

---

<a name="english"></a>

# 🇬🇧 English

A local hardware-software biometric identification system based on **Raspberry Pi 5**. The system provides access control using face recognition, RFID cards, and one-time access codes. Management is performed via a **Telegram bot**.

## Table of Contents

- [Features](#features-en)
- [System Architecture](#architecture-en)
- [Hardware Components](#hardware-en)
- [GPIO Pinout](#gpio-en)
- [Deployment](#deployment-en)
- [Project Structure](#structure-en)
- [Database](#database-en)
- [Entry Methods](#entry-en)
- [Anti-Spoofing](#antispoofing-en)
- [Troubleshooting](#troubleshooting-en)
- [License](#license-en)

---

<a name="features-en"></a>
## ✨ Features

- **Face Recognition** — contactless identification via IP camera using the `face_recognition` library (dlib)
- **Anti-Spoofing** — protection against spoofing with photos, videos and masks based on [Silent-Face-Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing)
- **RFID Identification** — entry via RFID card using the RC-522 module
- **One-Time Access Codes** — generation of temporary codes for guest access
- **Telegram Bot** — full management interface: user registration, access modifier configuration, statistics and visit history
- **Access Modifiers** — flexible access schedule by day of the week and time
- **Notifications** — instant Telegram notifications with a photo on every entry attempt
- **Statistics & History** — HTML report generation with filtering by date and user
- **Service Functions** — camera setup, anti-spoofing tuning, audio notifications, remote reboot

---

<a name="architecture-en"></a>
## 🏗 System Architecture

The system runs in **4 parallel threads**:

| Thread | Purpose |
|---|---|
| `CaptureFrames` | Continuous frame capture from camera |
| `FaceDetection` | Face detection, anti-spoofing check, recognition |
| `RFIDListener` | Listening to RFID reader and exit button |
| `MainLoop` | Telegram bot (command and message handling) |

---

<a name="hardware-en"></a>
## 🔧 Hardware Components

| # | Component | Model | Purpose |
|---|---|---|---|
| 1 | Microcomputer | **Raspberry Pi 5 (8GB)** | Central processing node |
| 2 | RFID Reader | **RC-522** | Reading RFID cards/tags |
| 3 | Relay Module | **3.3V Relay Module** | Controlling the electromagnetic lock |
| 4 | Electromagnetic Lock | **ST-ML60-1** | Door locking mechanism |
| 5 | IP Camera | **Procon IB4-PM** (or any RTSP camera) | Video stream for recognition |
| 6 | Green LED | — | Indicator: access granted |
| 7 | Red LED | — | Indicator: door closed |
| 8 | Exit Button | **ST-EXB-M02** | Opening the door from inside |
| 9 | Buzzer/Speaker | — | Audio notification |
| 10 | Power Supply | **ST-12/2 (12V, 2A)** | Power for electromagnet |
| 11 | Resistors | **1 kΩ (×2)** | For LEDs |

---

<a name="gpio-en"></a>
## 📌 GPIO Pinout (Raspberry Pi 5)

| Component | Pin | GPIO |
|---|---|---|
| **RFID RC-522** | | |
| 3.3V | 3.3V | — |
| GND | GND | — |
| SDA | GPIO 7 | SPI CE0 |
| SCK | GPIO 11 | SPI SCLK |
| MOSI | GPIO 10 | SPI MOSI |
| MISO | GPIO 9 | SPI MISO |
| **Relay Module** | | |
| DC+ | 3.3V | — |
| DC- | GND | — |
| IN | GPIO 4 | — |
| **Green LED** | | |
| Anode (+) via 1kΩ | GPIO 16 | — |
| Cathode (−) | GND | — |
| **Red LED** | | |
| Anode (+) via 1kΩ | GPIO 26 | — |
| Cathode (−) | GND | — |
| **Exit Button** | | |
| COM | 3.3V | — |
| NO | GPIO 17 | — |
| **Buzzer** | | |
| + | GPIO 13 | — |
| − | GND | — |

---

<a name="deployment-en"></a>
## 🚀 Deployment on Raspberry Pi 5

### Prerequisites

- Raspberry Pi 5 (8GB RAM) with **Raspberry Pi OS (64-bit, Bookworm)**
- microSD card minimum 32 GB (64 GB recommended)
- Ethernet connection to local network
- IP camera on the same network, or USB camera
- All hardware components connected according to the wiring diagram

---

### Step 1. Initial Raspberry Pi OS Setup

Flash Raspberry Pi OS (64-bit) to microSD using [Raspberry Pi Imager](https://www.raspberrypi.com/software/). During setup:

- Enable SSH
- Set username and password
- Configure Wi-Fi/Ethernet

---

### Step 2. Disable Graphical Desktop

> **Important!** Installing `dlib` requires maximum available RAM. The graphical desktop consumes ~300–500 MB RAM. It is recommended to disable it and work via SSH.

```bash
# Connect to Raspberry Pi via SSH
ssh <username>@<ip-address>

# Switch to CLI mode (without desktop)
sudo raspi-config
# Select: System Options → Boot / Auto Login → Console Autologin
# Reboot: Finish → Reboot

# Or with a single command:
sudo systemctl set-default multi-user.target
sudo reboot
```

To restore the desktop after installation:
```bash
sudo systemctl set-default graphical.target
sudo reboot
```

---

### Step 3. Increase SWAP Size

Compiling `dlib` requires significant memory. Increase swap to 2 GB:

```bash
sudo dphys-swapfile swapoff

sudo nano /etc/dphys-swapfile
# Change the line to:
# CONF_SWAPSIZE=2048

sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Verify:
free -h
```

---

### Step 4. Enable SPI Interface

SPI is required for the RC-522 RFID reader:

```bash
sudo raspi-config
# Select: Interface Options → SPI → Enable

# Or via config file:
echo "dtparam=spi=on" | sudo tee -a /boot/firmware/config.txt
sudo reboot
```

Verify:
```bash
ls /dev/spidev*
# Should display: /dev/spidev0.0 /dev/spidev0.1
```

---

### Step 5. Install System Dependencies

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

---

### Step 6. Clone the Repository

```bash
cd ~
git clone https://github.com/chadoyev/biometric-access-control-system.git
cd biometric-access-control-system
```

---

### Step 7. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

---

### Step 8. Install dlib

> **This is the most complex and time-consuming step.** Compiling `dlib` on Raspberry Pi 5 takes **20–40 minutes**. Make sure to work via SSH with the desktop disabled.

```bash
# Ensure swap is increased (Step 3)
# Ensure desktop is disabled (Step 2)

pip install dlib
```

If installation fails due to insufficient memory:

```bash
# Option 1: Install with limited parallel build jobs
CMAKE_BUILD_PARALLEL_LEVEL=2 pip install dlib

# Option 2: Build from source manually
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

Verify:
```bash
python3 -c "import dlib; print(dlib.DLIB_USE_CUDA)"
```

---

### Step 9. Install Remaining Dependencies

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

> **Note:** `opencv-python-headless` is used instead of `opencv-python` since no GUI is needed. PyTorch is installed as a CPU-only build since Raspberry Pi 5 has no CUDA.

---

### Step 10. Create a Telegram Bot

1. Open Telegram and find [@BotFather](https://t.me/BotFather)
2. Send `/newbot`, set a name and username
3. Copy the received API token
4. Get your Telegram ID by sending any message to [@userinfobot](https://t.me/userinfobot)

---

### Step 11. Configure the System

Open `main.py` and set:

```python
ADMIN_ID = 123456789         # Your Telegram user ID
API_TOKEN = 'your_bot_token' # Token from BotFather
```

---

### Step 12. Configure the Camera

The `config` table in `db.db` stores camera settings. By default, the camera is configured through the Telegram bot after the first launch.

For an IP camera, provide the RTSP address:
```
rtsp://admin:password@192.168.1.100:554/stream1
```

For a USB camera, provide the device index:
```
0
```

---

### Step 13. Run the System

```bash
cd ~/biometric-access-control-system
source venv/bin/activate
sudo venv/bin/python main.py
```

> **Note:** `sudo` is required for GPIO and SPI access.

---

### Step 14. Autostart on Boot (systemd)

Create a service for automatic startup when Raspberry Pi powers on:

```bash
sudo nano /etc/systemd/system/biometric.service
```

Service file contents:

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

> Replace `<username>` with your actual username.

```bash
sudo systemctl daemon-reload
sudo systemctl enable biometric.service
sudo systemctl start biometric.service

# Check status:
sudo systemctl status biometric.service

# View logs:
sudo journalctl -u biometric.service -f
```

---

<a name="structure-en"></a>
## 📁 Project Structure

```
biometric-access-control-system/
├── main.py                          # Main system module
├── FaceRegister.py                  # Face biometrics registration script
├── MFRC522.py                       # RC-522 RFID reader driver (SPI)
├── requirements.txt                 # Dependencies (AntiSpoofing)
├── db.db                            # SQLite database
├── connection_scheme.png            # Component wiring diagram
├── unknown.jpg                      # Placeholder image
├── files/                           # Registered user photos
│   └── 123456/
│       └── unknown.jpg              # Placeholder for unknown faces
├── photo_entry/                     # Photos on each entry attempt
├── AntiSpoofing/                    # Anti-spoofing module
│   ├── test.py                      # Anti-spoofing camera test
│   ├── train.py                     # Anti-spoofing model training
│   ├── resources/
│   │   ├── anti_spoof_models/       # Pre-trained models
│   │   │   ├── 2.7_80x80_MiniFASNetV2.pth
│   │   │   └── 4_0_0_80x80_MiniFASNetV1SE.pth
│   │   └── detection_model/         # Face detector model (RetinaFace)
│   │       ├── deploy.prototxt
│   │       └── Widerface-RetinaFace.caffemodel
│   └── src/
│       ├── anti_spoof_predict.py    # Prediction (real/fake face)
│       ├── generate_patches.py      # Face patch extraction
│       ├── utility.py               # Utilities
│       ├── default_config.py        # Training configuration
│       ├── train_main.py            # Training logic
│       ├── model_lib/
│       │   ├── MiniFASNet.py        # MiniFASNet architecture
│       │   └── MultiFTNet.py        # MultiFTNet architecture
│       └── data_io/
│           ├── dataset_folder.py    # Dataset loading
│           ├── dataset_loader.py    # DataLoader
│           ├── transform.py         # Augmentations
│           └── functional.py        # Transformation functions
└── Report/
    └── Bachelor_Thesis_Chadoev_I.M._AVT-013.pdf
```

---

<a name="database-en"></a>
## 🗄 Database

The SQLite database `db.db` contains the following tables:

| Table | Purpose |
|---|---|
| `users` | Telegram bot users (ID, name, verification status, phone) |
| `visitors` | Registered visitors (full name, position, photo, RFID card UID) |
| `visit_history` | History of all entry attempts (date, type, success, spoofing flag, photo) |
| `access_modifiers` | Access schedule (day of week, start/end time) |
| `list_access_codes` | One-time access codes (code, expiry, status) |
| `config` | System settings (camera, notifications, anti-spoofing, etc.) |

---

<a name="entry-en"></a>
## 🚪 Entry Methods

| Method | Description |
|---|---|
| **Face Biometrics** | Automatic recognition when approaching the camera |
| **RFID Card** | Presenting a registered card to the reader |
| **One-Time Code** | Entering a code in the Telegram bot (for guests) |
| **Telegram Bot** | "Open Door" button in the bot interface |
| **Exit Button** | Physical button inside the room |

---

<a name="antispoofing-en"></a>
## 🛡 Anti-Spoofing

The anti-spoofing module is based on the [Silent-Face-Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing) project by Minivision AI. It uses a Fourier spectrogram analysis method for auxiliary supervision, with an architecture based on **MiniFASNet** — a lightweight version of MobileFaceNet.

Models in `AntiSpoofing/resources/anti_spoof_models/`:
- `2.7_80x80_MiniFASNetV2.pth` — MiniFASNetV2 (scale 2.7, 80×80)
- `4_0_0_80x80_MiniFASNetV1SE.pth` — MiniFASNetV1SE (scale 4.0, 80×80)

The system analyzes several consecutive frames and makes a decision by **majority vote**. The number of frames to check is configurable via the Telegram bot.

---

<a name="troubleshooting-en"></a>
## 🔧 Troubleshooting

### dlib fails to compile / "Killed"

- Disable desktop: `sudo systemctl set-default multi-user.target && sudo reboot`
- Increase swap to 2048 MB
- Limit parallelism: `CMAKE_BUILD_PARALLEL_LEVEL=2 pip install dlib`
- Close all unnecessary processes before installation

### RFID reader not working

- Check SPI is enabled: `ls /dev/spidev*`
- Verify wire connections to GPIO according to the pinout table
- Ensure `spidev` is installed: `pip install spidev`

### Camera not connecting

- For USB camera: `ls /dev/video*` — make sure the device is visible
- For IP camera: verify RPi and camera are on the same network, and RTSP address is correct
- Test: `python3 -c "import cv2; cap=cv2.VideoCapture(0); print(cap.isOpened())"`

### Bot not responding

- Verify `API_TOKEN` and `ADMIN_ID` are set correctly in `main.py`
- Check internet connectivity: `ping api.telegram.org`
- Check logs: `sudo journalctl -u biometric.service -f`

---

<a name="license-en"></a>
## 📄 License

The anti-spoofing module is licensed under [Apache 2.0](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/blob/master/LICENSE) (Minivision AI).

---
---

<a name="russian"></a>

# 🇷🇺 Русский

Программно-аппаратный комплекс локальной биометрической идентификации на базе **Raspberry Pi 5**. Система обеспечивает контроль доступа в помещение с использованием распознавания лиц, RFID-карт и одноразовых кодов доступа. Управление осуществляется через **Telegram-бота**.

## Содержание

- [Возможности](#features-ru)
- [Архитектура системы](#architecture-ru)
- [Аппаратные компоненты](#hardware-ru)
- [Распиновка GPIO](#gpio-ru)
- [Развёртывание](#deployment-ru)
- [Структура проекта](#structure-ru)
- [База данных](#database-ru)
- [Способы входа](#entry-ru)
- [Антиспуфинг](#antispoofing-ru)
- [Устранение неполадок](#troubleshooting-ru)
- [Лицензия](#license-ru)

---

<a name="features-ru"></a>
## ✨ Возможности

- **Распознавание лиц** — бесконтактная идентификация через IP-камеру с использованием библиотеки `face_recognition` (dlib)
- **Антиспуфинг** — защита от попыток обмана системы фотографиями, видео и масками на базе [Silent-Face-Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing)
- **RFID-идентификация** — вход по RFID-карте через модуль RC-522
- **Одноразовые коды доступа** — генерация временных кодов для гостевого доступа
- **Telegram-бот** — полноценный интерфейс управления: регистрация пользователей, настройка модификаторов доступа, просмотр статистики и истории посещений
- **Модификаторы доступа** — гибкое расписание доступа по дням недели и времени
- **Уведомления** — мгновенные уведомления в Telegram при каждой попытке входа с фото
- **Статистика и история** — формирование HTML-отчёта с фильтрацией по дате и пользователю
- **Сервисные функции** — настройка камеры, антиспуфинга, звуковых уведомлений, удалённая перезагрузка

---

<a name="architecture-ru"></a>
## 🏗 Архитектура системы

Система работает в **4 параллельных потока**:

| Поток | Назначение |
|---|---|
| `CaptureFrames` | Непрерывный захват кадров с камеры |
| `FaceDetection` | Детекция лиц, антиспуфинг-проверка, распознавание |
| `RFIDListener` | Прослушивание RFID-считывателя и кнопки выхода |
| `MainLoop` | Telegram-бот (обработка команд и сообщений) |

---

<a name="hardware-ru"></a>
## 🔧 Аппаратные компоненты

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
| 11 | Резисторы | **1 кОм (×2)** | Для светодиодов |

---

<a name="gpio-ru"></a>
## 📌 Распиновка GPIO (Raspberry Pi 5)

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
| Катод (−) | GND | — |
| **Красный LED** | | |
| Анод (+) через 1кОм | GPIO 26 | — |
| Катод (−) | GND | — |
| **Кнопка выхода** | | |
| COM | 3.3V | — |
| NO | GPIO 17 | — |
| **Зуммер** | | |
| + | GPIO 13 | — |
| − | GND | — |

---

<a name="deployment-ru"></a>
## 🚀 Развёртывание на Raspberry Pi 5

### Предварительные требования

- Raspberry Pi 5 (8GB RAM) с установленной **Raspberry Pi OS (64-bit, Bookworm)**
- microSD-карта минимум 32 ГБ (рекомендуется 64 ГБ)
- Ethernet-подключение к локальной сети
- IP-камера в той же сети или USB-камера
- Все аппаратные компоненты подключены согласно схеме

---

### Шаг 1. Начальная настройка Raspberry Pi OS

Запишите Raspberry Pi OS (64-bit) на microSD с помощью [Raspberry Pi Imager](https://www.raspberrypi.com/software/). При записи:

- Включите SSH
- Задайте имя пользователя и пароль
- Настройте Wi-Fi/Ethernet

---

### Шаг 2. Отключение графического рабочего стола

> **Важно!** Для установки `dlib` требуется максимум оперативной памяти. Графический рабочий стол потребляет ~300–500 МБ RAM. Рекомендуется отключить его и работать через SSH.

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

---

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

---

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

---

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

---

### Шаг 6. Клонирование репозитория

```bash
cd ~
git clone https://github.com/chadoyev/biometric-access-control-system.git
cd biometric-access-control-system
```

---

### Шаг 7. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

---

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

---

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

---

### Шаг 10. Создание Telegram-бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`, задайте имя и username
3. Скопируйте полученный API-токен
4. Узнайте свой Telegram ID — отправьте любое сообщение боту [@userinfobot](https://t.me/userinfobot)

---

### Шаг 11. Настройка конфигурации

Откройте `main.py` и укажите:

```python
ADMIN_ID = 123456789         # Ваш Telegram user ID
API_TOKEN = 'ваш_токен_бота' # Токен от BotFather
```

---

### Шаг 12. Настройка IP-камеры

В базе данных `db.db` таблица `config` содержит настройки камеры. По умолчанию камера настраивается через Telegram-бот после первого запуска.

Для IP-камеры укажите RTSP-адрес:
```
rtsp://admin:password@192.168.1.100:554/stream1
```

Для USB-камеры укажите индекс:
```
0
```

---

### Шаг 13. Запуск системы

```bash
cd ~/biometric-access-control-system
source venv/bin/activate
sudo venv/bin/python main.py
```

> **Примечание:** `sudo` необходим для доступа к GPIO и SPI.

---

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

---

<a name="structure-ru"></a>
## 📁 Структура проекта

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

---

<a name="database-ru"></a>
## 🗄 База данных

SQLite-база `db.db` содержит следующие таблицы:

| Таблица | Назначение |
|---|---|
| `users` | Пользователи Telegram-бота (ID, имя, статус верификации, телефон) |
| `visitors` | Зарегистрированные посетители (ФИО, должность, фото, UID RFID-карты) |
| `visit_history` | История всех попыток входа (дата, тип, успешность, спуфинг, фото) |
| `access_modifiers` | Расписание доступа (день недели, время начала/окончания) |
| `list_access_codes` | Одноразовые коды доступа (код, срок действия, статус) |
| `config` | Настройки системы (камера, уведомления, антиспуфинг и др.) |

---

<a name="entry-ru"></a>
## 🚪 Способы входа в помещение

| Способ | Описание |
|---|---|
| **Биометрия лица** | Автоматическое распознавание при приближении к камере |
| **RFID-карта** | Поднесение зарегистрированной карты к считывателю |
| **Одноразовый код** | Ввод кода в Telegram-боте (для гостей) |
| **Telegram-бот** | Кнопка «Открыть дверь» в интерфейсе бота |
| **Кнопка выхода** | Физическая кнопка внутри помещения |

---

<a name="antispoofing-ru"></a>
## 🛡 Антиспуфинг

Модуль антиспуфинга основан на проекте [Silent-Face-Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing) от Minivision AI. Используется метод на основе анализа Фурье-спектрограмм для вспомогательного обучения, с архитектурой на базе **MiniFASNet** — облегчённой версии MobileFaceNet.

Модели в `AntiSpoofing/resources/anti_spoof_models/`:
- `2.7_80x80_MiniFASNetV2.pth` — MiniFASNetV2 (scale 2.7, 80×80)
- `4_0_0_80x80_MiniFASNetV1SE.pth` — MiniFASNetV1SE (scale 4.0, 80×80)

Система анализирует несколько кадров подряд и принимает решение по принципу **большинства голосов**. Количество кадров для проверки настраивается через Telegram-бот.

---

<a name="troubleshooting-ru"></a>
## 🔧 Устранение неполадок

### dlib не компилируется / «Killed»

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

---

<a name="license-ru"></a>
## 📄 Лицензия

Антиспуфинг-модуль — [Apache 2.0](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/blob/master/LICENSE) (Minivision AI).
