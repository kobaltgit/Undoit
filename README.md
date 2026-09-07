<p align="center">
  <img src="src-tauri/icons/128x128.png" width="96" height="96" alt="Undoit Logo" />
  <h1 align="center">Undoit</h1>
  <strong>Локальная машина времени и версионирование файлов для Windows 10 & 11 на Rust и Tauri v2.</strong><br/>
  <em>Local Time Machine & continuous file versioning for Windows 10 & 11 built with Rust & Tauri v2.</em>
</p>

<p align="center">
  <a href="https://github.com/kobaltgit/undoit/releases/latest"><img src="https://img.shields.io/github/v/release/kobaltgit/undoit?color=38bdf8&label=Latest%20Release" alt="Latest Release" /></a>
  <a href="https://kobaltgit.github.io/Undoit/"><img src="https://img.shields.io/badge/Website-Flutter%20Web-02569B.svg?logo=flutter" alt="Live Website" /></a>
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg?logo=windows" alt="Windows 10/11" />
  <img src="https://img.shields.io/badge/Rust-2021%20Edition-DEA584.svg?logo=rust" alt="Rust 2021" />
  <img src="https://img.shields.io/badge/Tauri-v2.0-FFC131.svg?logo=tauri" alt="Tauri v2" />
  <img src="https://img.shields.io/badge/Frontend-Svelte%205%20(Runes)-FF3E00.svg?logo=svelte" alt="Svelte 5" />
  <img src="https://img.shields.io/badge/RAM-%3C%2025%20MB-34d399.svg" alt="Low RAM" />
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License" /></a>
</p>

<p align="center">
  <a href="#-о-проекте">🇷🇺 Русский</a> • <a href="#-about-the-project">🇬🇧 English</a> • <a href="#-экосистема-kobalt-tools">🌐 Экосистема</a>
</p>

---

## 🇷🇺 О проекте

**Undoit** — сверхлегковесная нативная утилита непрерывного сохранения версий (Time Machine) для Windows, входящая в экосистему системных инструментов **Kobalt Tools** ([StashIt](https://github.com/kobaltgit/StashIt), [MiniBin](https://github.com/kobaltgit/minibin), [PolyShift](https://github.com/kobaltgit/polyshift), [PeekIt](https://github.com/kobaltgit/peekit)).

При каждом изменении файла в отслеживаемых папках Undoit автоматически создает компактный моментальный снимок. Это позволяет в любой момент вернуться к любому состоянию, визуально изучить изменения или мгновенно восстановить случайно перезаписанный документ.

Версия **v2.1** полностью построена на **Rust** и **Svelte 5** с движком **Tauri v2**, потребляет **менее 25 МБ RAM** и работает на 100% локально.

> 📦 *Архивная версия v1.0 на Python сохранена в ветке [`v1-python`](https://github.com/kobaltgit/Undoit/tree/v1-python).*

### ⚡ Сравнение с аналогами

| Параметр | Undoit v2 | Windows File History | Облачные бэкапы (Dropbox/GDrive) |
| :--- | :--- | :--- | :--- |
| **Стек технологий** | **Rust + Tauri v2 + Svelte 5** | C++ Win32 Service | Electron / C# / Web |
| **ОЗУ в фоне** | **< 25 МБ** | Служба Windows | ~150–350 МБ |
| **Сжатие данных** | **Zstandard (zstd) + BLAKE3 CAS** | Обычное копирование | Проприетарное в облаке |
| **Визуальный Diff** | **Шторка До/После, PDF, AI, DOCX** | Только восстановление | Базовый веб-текст |
| **Приватность** | **100% локально (без интернета)** | Локально | Передача файлов в облако |
| **Права администратора** | **Не требуются (чистый HKCU)** | Требуются | Зависит от клиента |

### 🎯 Ключевые возможности

- 🚀 **Ядро на Rust:** Мгновенная реакция на события файловой системы с дебаунсингом и обработкой блокировок Windows (Sharing Violation).
- 🗜️ **Сжатие Zstandard + BLAKE3 CAS:** Контентно-адресуемая дедупликация и экономия дискового пространства до 70–80%.
- 🖼️ **Визуальный Diff изображений:** Интерактивная шторка-слайдер («До / После»), Side-by-side сравнение и плавный Zoom для PNG, JPG, SVG, WebP, GIF, BMP, TIFF, AVIF, ICO.
- 📄 **Рендеринг PDF и Adobe Illustrator:** Постраничное визуальное сравнение документов `.pdf` и векторных макетов `.ai`.
- 📝 **Умный Diff документов Word и кода:** Построчное выявление изменений в `.docx`, а также в `.txt`, `.json`, `.md`, `.rs`, `.py`, `.ts`, `.html`.
- 👁️ **«Открыть в приложении»:** Открытие любого исторического снимка во внешней ассоциированной программе во временном защищенном файле.
- 🪟 **Интеграция с Windows:** Пункт в контекстном меню Проводника, Single-Instance IPC через Named Pipe и системный трей с круговой диаграммой диска.
- 🔒 **100% Конфиденциальность:** База данных SQLite и все снимки хранятся только в `%APPDATA%\Undoit\`. Никакой телеметрии и учетных записей.

### 📥 Установка и загрузка

Скачайте актуальную версию со [страницы последнего релиза](https://github.com/kobaltgit/undoit/releases/latest):

- **Инсталлятор (`Undoit-setup.exe` или `.msi`):** Классическая быстрая установка без прав администратора.
- **Portable версия (`Undoit.exe`):** Запуск в один клик без установки.

---

## 🇬🇧 About the Project

**Undoit** is an ultra-lightweight, native continuous file versioning utility (Time Machine) for Windows and part of the **Kobalt Tools** desktop ecosystem ([StashIt](https://github.com/kobaltgit/StashIt), [MiniBin](https://github.com/kobaltgit/minibin), [PolyShift](https://github.com/kobaltgit/polyshift), [PeekIt](https://github.com/kobaltgit/peekit)).

Whenever a file changes in your watched folders, Undoit automatically creates a lightweight snapshot. You can travel back in time, inspect visual and textual differences, or restore overwritten documents with one click.

Version **v2.1** is built from scratch with **Rust** and **Svelte 5** under **Tauri v2**, consuming **under 25 MB RAM** and operating 100% locally.

> 📦 *Legacy Python v1.0 version is archived in the [`v1-python`](https://github.com/kobaltgit/Undoit/tree/v1-python) branch.*

### ⚡ Key Benchmarks

| Metric | Undoit v2 | Windows File History | Cloud Sync (Dropbox/GDrive) |
| :--- | :--- | :--- | :--- |
| **Tech Stack** | **Rust + Tauri v2 + Svelte 5** | C++ Win32 Service | Electron / C# / Web |
| **Idle RAM** | **< 25 MB** | Windows Service | ~150–350 MB |
| **Data Compression** | **Zstandard (zstd) + BLAKE3 CAS** | Plain copy | Proprietary cloud storage |
| **Visual Diff** | **Before/After curtain, PDF, AI, DOCX** | Restore only | Basic text web diff |
| **Privacy** | **100% Local (no network)** | Local | Uploads files to cloud servers |
| **Admin Rights** | **Zero Admin (pure HKCU)** | Required | Depends on installer |

### 🎯 Core Features

- 🚀 **Blazing-Fast Rust Core:** Low-latency file system monitoring with debouncing and Windows sharing-violation handling.
- 🗜️ **Zstandard + BLAKE3 CAS Storage:** Content-addressable deduplication saving up to 70–80% disk space.
- 🖼️ **Visual Diff for Images:** Interactive curtain slider (Before / After), side-by-side mode, and zoom for PNG, JPG, SVG, WebP, GIF, BMP, TIFF, AVIF, ICO.
- 📄 **PDF & Adobe Illustrator Diff:** Multi-page visual diff for `.pdf` files and vector `.ai` artwork.
- 📝 **Smart DOCX & Code Text Diff:** Line-by-line colored diff for Microsoft Word `.docx` paragraphs, code, and markdown.
- 👁️ **«Open in App»:** Launch any historical snapshot in its associated desktop app (Word, Illustrator, Photoshop) via safe temporary files.
- 🪟 **Deep Windows Shell Integration:** Explorer context menu, Single-Instance IPC via Named Pipe, and dynamic tray icon with storage dial.
- 🔒 **100% Private:** SQLite metadata and snapshots reside strictly in `%APPDATA%\Undoit\`. Zero telemetry, zero cloud dependencies.

### 📥 Installation & Download

Download the latest release from [GitHub Releases](https://github.com/kobaltgit/undoit/releases/latest):

- **Installer (`Undoit-setup.exe` / `.msi`):** User-mode installer with start menu shortcuts and auto-update support.
- **Portable (`Undoit.exe`):** Single executable, no installation needed.

---

## 🛠️ Сборка и разработка / Development

```bash
# 1. Установка зависимостей фронтенда
npm install

# 2. Запуск в режиме разработки (Hot Reload)
npm run tauri dev

# 3. Сборка релизного установщика
npm run tauri build
```

---

## 🌐 Экосистема Kobalt Tools

| Проект | Описание | Стек | Ссылки |
| :--- | :--- | :--- | :--- |
| 📥 **StashIt** | Плавающий карман Drag-and-Drop (Dropover / Yoink для Windows) | Rust + Tauri v2 + Svelte 5 | [Repo](https://github.com/kobaltgit/StashIt) • [Web](https://kobaltgit.github.io/StashIt/) |
| 🗑️ **MiniBin** | Умная корзина в системном трее с Flyout-интерфейсом | Rust + Tauri v2 + Svelte 5 | [Repo](https://github.com/kobaltgit/minibin) • [Web](https://kobaltgit.github.io/minibin/) |
| ⏱️ **Undoit** | Локальная машина времени и версионирование файлов (Ctrl+Z) | Rust + Tauri v2 + Svelte 5 | [Repo](https://github.com/kobaltgit/undoit) • [Web](https://kobaltgit.github.io/Undoit/) |
| 🌐 **PolyShift** | HUD-помощник и контекстный перевод у курсора с Gemini AI | Rust + Tauri v2 + Svelte 5 | [Repo](https://github.com/kobaltgit/polyshift) • [Web](https://kobaltgit.github.io/polyshift/) |
| 👁️ **PeekIt** | Мгновенный предпросмотр файлов по клавише Space | Rust + Tauri v2 + Svelte 5 | [Repo](https://github.com/kobaltgit/peekit) • [Web](https://kobaltgit.github.io/PeekIt/) |
| 🧩 **PeekIt Plugins** | Официальный реестр и SDK веб-плагинов для PeekIt | TypeScript + Web SDK | [Repo](https://github.com/kobaltgit/peekit-plugins) • [Web](https://kobaltgit.github.io/peekit-plugins/) |
| 🎨 **kobalt_ui** | Общая библиотека UI компонентов (шапка, футер, релизы) | Flutter Web (Dart) | [Repo](https://github.com/kobaltgit/kobalt_ui) |

---

## 📄 Лицензия / License

Распространяется под лицензией **MIT**. Подробнее в файле [LICENSE](LICENSE).  
Copyright (c) 2025–2026 Kobalt.
