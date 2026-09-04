# Руководство для контрибьюторов (Contributing Guide)

Спасибо за интерес к развитию проекта **Undoit**! 🎉  
Мы приветствуем идеи, исправления багов, улучшения интерфейса и документации.

---

## Архитектура проекта (v2)

Undoit v2 полностью переписан на современном стеке:
- **Ядро / Бэкенд**: Rust + [Tauri v2](https://v2.tauri.app/).
- **Фронтенд / UI**: [Svelte 5](https://svelte.dev/) (Runes reactivity) + TypeScript + Vite.
- **Хранилище**: Контентно-адресуемое хранилище BLAKE3 + потоковое сжатие Zstandard (zstd) + метаданные в SQLite (`rusqlite`).
- **Файловый монитор**: `notify-debouncer-mini` с фильтрацией системных и пользовательских масок.
- **Интеграция**: Нативная интеграция с Windows Explorer (контекстное меню реестра, Named Pipe IPC, динамический щит в системном трее).

---

## Требования к окружению

1. **Rust**: Актуальная стабильная версия (`rustup update`).
2. **Node.js**: v18 или новее (`node -v`).
3. **C++ Build Tools**: Visual Studio Build Tools (компоненты C++ / Windows SDK для компиляции Tauri на Windows).

---

## Запуск в режиме разработки

1. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/kobaltgit/Undoit.git
   cd Undoit
   ```

2. Установите зависимости фронтенда:
   ```bash
   npm install
   ```

3. Запустите dev-сервер с горячей перезагрузкой (HMR):
   ```bash
   npm run tauri dev
   ```

4. Проверьте код перед отправкой:
   ```bash
   npm run check
   cargo check --manifest-path src-tauri/Cargo.toml
   ```

---

## Правила создания Pull Request

1. Создайте отдельную ветку для вашей фичи или фикса:
   ```bash
   git checkout -b feature/awesome-feature
   ```
2. Пишите понятные и структурированные коммиты по стандарту Conventional Commits (например: `feat: add pdf export`, `fix: tray pause synchronization`).
3. Убедитесь, что TypeScript (`npm run check`) и Rust (`cargo check`) компилируются без ошибок и предупреждений.
4. Создайте Pull Request в ветку `main` с описанием изменений.
