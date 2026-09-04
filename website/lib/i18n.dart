import 'package:flutter/foundation.dart';

enum AppLang { ru, en }

final ValueNotifier<AppLang> currentLang = ValueNotifier<AppLang>(AppLang.ru);

void setAppLanguage(AppLang lang) {
  currentLang.value = lang;
}

class S {
  static AppLang get lang => currentLang.value;
  static bool get isRu => lang == AppLang.ru;

  // Navbar
  static String get navFeatures => isRu ? 'Возможности' : 'Features';
  static String get navDiffDemo => isRu ? 'Сплит-дифф' : 'Live Diff';
  static String get navComparison => isRu ? 'Сравнение' : 'Comparison';
  static String get navFaq => isRu ? 'FAQ' : 'FAQ';
  static String get navDownload => isRu ? 'Скачать' : 'Download';

  // Hero Section
  static String get heroBadge => isRu
      ? 'Undoit 2.1.0 Релиз доступен — Полная поддержка RU/EN, Rust & Tauri'
      : 'Undoit 2.1.0 Release Available — Bilingual RU/EN, Rust & Tauri';
  static String get heroTitle => isRu
      ? 'Локальная машина времени\nдля ваших файлов на Windows'
      : 'Local Time Machine\nfor your Windows files';
  static String get heroSubtitle => isRu
      ? 'Невидимо сохраняет историю каждого изменения в реальном времени. Возвращайтесь к любой секунде работы, сравнивайте текст документов Word, код и находите визуальные отличия в PDF и макетах Illustrator прямо на экране.'
      : 'Silently preserves the history of every change in real time. Jump back to any second, compare Word doc text, code diffs, and visually inspect PDF pages and Illustrator layouts right on your screen.';
  static String get heroDownloadBtn => isRu ? 'Скачать бесплатно' : 'Download Free';
  static String get heroGithubBtn => isRu ? 'GitHub' : 'GitHub';
  static String get heroStatSpeed => isRu ? '< 1 мс' : '< 1 ms';
  static String get heroStatSpeedLabel => isRu ? 'Задержка фиксации' : 'Snapshot latency';
  static String get heroStatRam => isRu ? '< 25 МБ' : '< 25 MB';
  static String get heroStatRamLabel => isRu ? 'ОЗУ в трее Windows' : 'Background RAM usage';
  static String get heroStatZstd => isRu ? 'до 85%' : 'up to 85%';
  static String get heroStatZstdLabel => isRu ? 'Сжатие Zstandard' : 'Zstandard compression';
  static String get heroStatPrivacy => isRu ? '100%' : '100%';
  static String get heroStatPrivacyLabel => isRu ? 'Офлайн & Приватно' : 'Offline & Private';

  // Diff Demo
  static String get diffBadge => isRu ? 'ИНТЕРАКТИВНОЕ СРАВНЕНИЕ' : 'INTERACTIVE COMPARISON';
  static String get diffTitle => isRu ? 'Попробуйте сплит-дифф в действии' : 'Experience the Split Diff in action';
  static String get diffSubtitle => isRu
      ? 'Двигайте курсор по экрану или тяните шторку, чтобы мгновенно увидеть изменения между версиями.'
      : 'Move your cursor across the canvas or drag the divider to inspect changes between versions.';
  static String get diffTabCode => isRu ? 'Код (Rust / TS)' : 'Code (Rust / TS)';
  static String get diffTabImage => isRu ? 'Дизайн (UI Mockup)' : 'Design (UI Mockup)';
  static String get diffTabDocx => isRu ? 'Документ (Word .docx)' : 'Document (Word .docx)';
  static String get diffBefore => isRu ? 'До изменений' : 'Before';
  static String get diffAfter => isRu ? 'После изменений' : 'After';
  static String get diffSensitivityHint => isRu
      ? '⚡ Чувствительный сплит: двигайте курсор в любом месте или используйте кнопки быстрого перехода'
      : '⚡ High sensitivity: move cursor anywhere across canvas or use quick preset buttons';
  static String get diffWas => isRu ? 'Было (0%)' : 'Before (0%)';
  static String get diffNow => isRu ? 'Стало (100%)' : 'After (100%)';

  // Features Grid
  static String get featuresBadge => isRu ? 'ВОЗМОЖНОСТИ' : 'FEATURES';
  static String get featuresTitle => isRu ? 'Всё необходимое для спокойной работы' : 'Everything you need to work with peace of mind';
  static String get featuresSubtitle => isRu
      ? 'Undoit работает абсолютно автономно и незаметно, защищая каждый ваш проект от случайного удаления, поломки макета или сбоя софта.'
      : 'Undoit works quietly in the background, protecting every project from accidental deletion, broken layouts, or software crashes.';

  static String get feat1Title => isRu ? 'Визуальный дифф PDF и .AI' : 'Visual Diff for PDF & .AI';
  static String get feat1Desc => isRu
      ? 'Сравнивайте макеты Illustrator и многостраничные PDF в реальном времени. Интерактивный ползунок наглядно показывает мельчайшие сдвиги слоев и текста.'
      : 'Compare Illustrator designs and multi-page PDFs in real time. The interactive split slider highlights layer shifts and layout tweaks.';

  static String get feat2Title => isRu ? 'Полноценная поддержка DOCX' : 'Full DOCX Word Support';
  static String get feat2Desc => isRu
      ? 'Автоматически распаковывает файлы Microsoft Word, извлекает чистый текст и подсвечивает добавленные и удаленные фрагменты построчно.'
      : 'Automatically unpacks Microsoft Word files, extracts clean text, and shows line-by-line editorial additions and removals.';

  static String get feat3Title => isRu ? '100% Офлайн & Приватность' : '100% Offline & Private';
  static String get feat3Desc => isRu
      ? 'Ноль обращений в облако, никаких подписок или регистрации. Ваши конфиденциальные файлы, коммерческие договоры и код остаются строго на вашем диске.'
      : 'Zero cloud pings, zero telemetry, no subscriptions. Your confidential documents, contracts, and code stay strictly on your local disk.';

  static String get feat4Title => isRu ? 'Zstandard + Хеши BLAKE3' : 'Zstandard + BLAKE3 Hashes';
  static String get feat4Desc => isRu
      ? 'Высокоскоростное сжатие Zstd уменьшает объем хранилища в разы, а криптографический хеш BLAKE3 исключает дублирование идентичных копий.'
      : 'Blazing-fast Zstd compression cuts storage footprints drastically, while BLAKE3 content hashes eliminate duplicate snapshots.';

  static String get feat5Title => isRu ? 'Открытие в один клик' : 'One-Click App Launch';
  static String get feat5Desc => isRu
      ? 'Кнопка «В приложении» открывает выбранную историческую версию в вашем обычном софте (Word, Photoshop, Acrobat) без риска повредить текущий файл.'
      : 'The "In App" action launches the historical snapshot in your default application (Word, Photoshop, Acrobat) without overwriting working files.';

  static String get feat6Title => isRu ? 'Контекстное меню Windows' : 'Windows Context Menu';
  static String get feat6Desc => isRu
      ? 'Щелкните правой кнопкой мыши по любому файлу в Проводнике Windows и выберите «История версий Undoit» для мгновенного доступа к таймлайну.'
      : 'Right-click any file in Windows Explorer and select "Undoit Version History" for instant timeline access.';

  static String get feat7Title => isRu ? '< 25 МБ оперативной памяти' : '< 25 MB RAM Footprint';
  static String get feat7Desc => isRu
      ? 'Ядро на Rust и легковесный движок Tauri v2 потребляют в 8 раз меньше RAM, чем аналоги на Electron, тихо работая в системном трее.'
      : 'A lean Rust core and Tauri v2 consume 8x less RAM than Electron alternatives while idling quietly in your system tray.';

  static String get feat8Title => isRu ? 'Восстановление без потерь' : 'Lossless Snapshot Restore';
  static String get feat8Desc => isRu
      ? 'Откатите файл к любому моменту или экспортируйте снимок как отдельную копию. Программа всегда делает страховочный бекап перед перезаписью.'
      : 'Roll back files to any previous state or export snapshots as new copies. A safety backup is always performed before replacing current files.';

  // Comparison Table
  static String get compBadge => isRu ? 'ЭВОЛЮЦИЯ ПРОЕКТА' : 'PROJECT EVOLUTION';
  static String get compTitle => isRu ? 'Перезапуск 2.x на Rust против версии 1.x' : 'Version 2.x (Rust) vs Legacy 1.x';
  static String get compSubtitle => isRu
      ? 'Полный рефакторинг архитектуры: от тяжелого Python/Qt к компактному высокоскоростному системному стеку на Rust и Tauri.'
      : 'A complete architectural rewrite: transitioning from heavy Python/Qt to a lean, blazing-fast native Rust and Tauri stack.';

  static String get compMetric => isRu ? 'Параметр' : 'Metric';
  static String get compLegacy => isRu ? 'Undoit v1.x (Python / Qt)' : 'Undoit v1.x (Python / Qt)';
  static String get compCurrent => isRu ? 'Undoit v2.x (Rust / Tauri)' : 'Undoit v2.x (Rust / Tauri)';

  static String get compRow1Metric => isRu ? 'Технологический стек' : 'Technology Stack';
  static String get compRow1V1 => 'Python 3 + PySide6 (Qt)';
  static String get compRow1V2 => 'Rust + Tauri v2 + SvelteKit';

  static String get compRow2Metric => isRu ? 'Потребление ОЗУ в фоне' : 'Background RAM usage';
  static String get compRow2V1 => '~150 – 200 MB';
  static String get compRow2V2 => isRu ? '15 – 25 МБ (в 8 раз меньше)' : '15 – 25 MB (8x lighter)';

  static String get compRow3Metric => isRu ? 'Размер установщика' : 'Installer Download Size';
  static String get compRow3V1 => '~80 MB';
  static String get compRow3V2 => '3.86 MB (NSIS setup)';

  static String get compRow4Metric => isRu ? 'Сжатие версий на диске' : 'On-disk Version Compression';
  static String get compRow4V1 => isRu ? 'Стандартный zip' : 'Standard zip';
  static String get compRow4V2 => isRu ? 'Zstandard (Zstd) ультра-скоростной' : 'Zstandard (Zstd) ultra-fast';

  static String get compRow5Metric => isRu ? 'Дедупликация файлов' : 'File Deduplication';
  static String get compRow5V1 => isRu ? 'Базовая проверка размера' : 'Basic size check';
  static String get compRow5V2 => isRu ? 'Криптографический хеш BLAKE3' : 'BLAKE3 cryptographic hash';

  static String get compRow6Metric => isRu ? 'Визуальный дифф PDF и .AI' : 'Visual Diff for PDF & .AI';
  static String get compRow6V1 => isRu ? '❌ Отсутствует' : '❌ Unavailable';
  static String get compRow6V2 => isRu ? '✅ Сплит-слайдер и страницы' : '✅ Split slider & page navigation';

  static String get compRow7Metric => isRu ? 'Сравнение документов DOCX' : 'DOCX Document Comparison';
  static String get compRow7V1 => isRu ? '❌ Бинарный файл' : '❌ Treated as raw binary';
  static String get compRow7V2 => isRu ? '✅ Извлечение текста и дифф' : '✅ Text extraction & line diff';

  static String get compRow8Metric => isRu ? 'Открытие во внешнем софте' : 'External App Launch';
  static String get compRow8V1 => isRu ? '❌ Только восстановить' : '❌ Restore only';
  static String get compRow8V2 => isRu ? '✅ Кнопка «В приложении»' : '✅ Dedicated "In App" action';

  static String get compRow9Metric => isRu ? 'Холодный старт приложения' : 'Cold Application Launch';
  static String get compRow9V1 => isRu ? '3 – 5 секунд' : '3 – 5 seconds';
  static String get compRow9V2 => isRu ? '< 400 миллисекунд' : '< 400 milliseconds';

  // Supported Formats
  static String get formatsTitle => isRu ? 'Поддерживает любые ваши файлы' : 'Supports Any File Extension';
  static String get formatsSubtitle => isRu
      ? 'Undoit сохраняет историю любых расширений, а для ключевых форматов предлагает интеллектуальный просмотр.'
      : 'Undoit version-controls all file types byte-for-byte, with dedicated intelligent viewers for key formats.';
  static String get fmtPdf => isRu ? 'PDF Документы' : 'PDF Documents';
  static String get fmtAi => 'Adobe Illustrator';
  static String get fmtDocx => 'Microsoft Word';
  static String get fmtCode => isRu ? 'Исходный код' : 'Source Code';
  static String get fmtImages => isRu ? 'Изображения' : 'Raster & Vector Graphics';
  static String get fmtAny => isRu ? 'Любые файлы' : 'Any File Format';
  static String get fmtAnyExts => isRu ? 'Любые бинарные форматы' : 'All binary file formats';

  // FAQ Section
  static String get faqBadge => isRu ? 'ВОПРОСЫ И ОТВЕТЫ' : 'FAQ';
  static String get faqTitle => isRu ? 'Часто задаваемые вопросы' : 'Frequently Asked Questions';

  static String get faq1Q => isRu ? 'Как Undoit отслеживает файлы?' : 'How does Undoit monitor files?';
  static String get faq1A => isRu
      ? 'Приложение использует системный перехват событий файловой системы Windows на базе легковесного движка на Rust. В момент, когда вы нажимаете Ctrl+S в любой программе (Word, VS Code, Illustrator), Undoit фиксирует изменение, проверяет хеш BLAKE3 и сжимает снимок в локальную базу данных.'
      : 'The app hooks into Windows filesystem events using a lightweight native Rust engine. Whenever you press Ctrl+S in any software (Word, VS Code, Illustrator), Undoit detects the write, verifies the BLAKE3 hash, and stores the compressed snapshot in a local SQLite database.';

  static String get faq2Q => isRu ? 'Где хранятся мои данные и есть ли облачная синхронизация?' : 'Where is my data stored and is there cloud sync?';
  static String get faq2A => isRu
      ? 'Все данные хранятся исключительно на вашем жестком диске в локальной базе данных SQLite. Undoit на 100% автономен, работает без подключения к интернету и принципиально не отправляет ваши конфиденциальные документы ни на какие сторонние серверы.'
      : 'All data is stored strictly on your local disk in a local SQLite database. Undoit is 100% autonomous, requires no internet connection, and never sends your sensitive documents to third-party servers.';

  static String get faq3Q => isRu ? 'Не заполнит ли история версий весь свободный диск?' : 'Will file history consume all my free disk space?';
  static String get faq3A => isRu
      ? 'Нет. Во-первых, файлы сжимаются эффективным алгоритмом Zstandard (Zstd). Во-вторых, встроенный механизм дедупликации хешей BLAKE3 гарантирует, что если файл не изменился по содержимому, новая копия на диск не запишется. Также в настройках можно задать автоочистку версий старше N дней.'
      : 'No. First, snapshots are compressed with Zstandard (Zstd). Second, BLAKE3 content hashing guarantees duplicate snapshots are never saved. Additionally, you can configure automatic pruning of versions older than N days in Preferences.';

  static String get faq4Q => isRu ? 'Чем отличаются установщик (.exe setup) и портабельная версия?' : 'What is the difference between Setup (.exe) and Portable?';
  static String get faq4A => isRu
      ? 'Установщик автоматически прописывает приложение в автозагрузку Windows, создает ярлыки в меню «Пуск» и регистрирует пункт «История версий Undoit» в контекстном меню Проводника. Портабельная версия запускается в один клик без инсталляции и прав администратора — идеально для запуска с флешки.'
      : 'The installer sets up optional Windows autostart, creates Start Menu shortcuts, and adds "Undoit Version History" to the Explorer context menu. The portable build runs immediately with zero installation or admin privileges — ideal for USB drives.';

  static String get faq5Q => isRu ? 'Что произойдет, если я закрою окно программы?' : 'What happens when I close the main window?';
  static String get faq5A => isRu
      ? 'При закрытии окна Undoit не прекращает работу, а бесшумно сворачивается в системный трей возле часов, продолжая защищать ваши документы. Из меню трея можно в один клик временно приостановить отслеживание или снова развернуть окно истории.'
      : 'Closing the window minimizes Undoit silently into the Windows system tray beside the clock, keeping file monitoring alive. From the tray menu, you can pause monitoring or reopen the history window anytime.';

  // Download CTA
  static String get ctaTitle => isRu ? 'Начните сохранять историю прямо сейчас' : 'Start Protecting Your File History Today';
  static String get ctaSubtitle => isRu
      ? 'Скачайте Undoit для Windows. Никаких аккаунтов, рекламы или подписок. Полностью бесплатный и открытый исходный код под лицензией MIT.'
      : 'Download Undoit for Windows. No accounts, no ads, no paywalls. Completely free and open-source under the MIT license.';
  static String get ctaSetupBtn => isRu ? 'Установщик (Setup .exe)' : 'Installer (Setup .exe)';
  static String get ctaPortableBtn => isRu ? 'Портативная (.exe)' : 'Portable (.exe)';
  static String get ctaMsiBtn => isRu ? 'Пакет MSI (.msi)' : 'MSI Package (.msi)';
  static String get ctaPlatformNote => isRu
      ? 'Windows 10 / 11 (64-bit) • Открытый исходный код • Без регистрации'
      : 'Windows 10 / 11 (64-bit) • Open Source • No Registration Required';

  // Footer
  static String get footerTagline => isRu
      ? 'Локальная машина времени для ваших файлов. Быстро. Надёжно. Приватно.'
      : 'Local time machine for your files. Fast. Reliable. Private.';
  static String get footerReleases => isRu ? 'Релизы' : 'Releases';
  static String get footerIssues => isRu ? 'Сообщить об ошибке' : 'Report Issue';
  static String get footerLicense => isRu ? 'Лицензия MIT' : 'MIT License';
  static String get footerBackToTop => isRu ? 'Наверх ↑' : 'Back to top ↑';
  static String get footerCopyright => isRu
      ? '© 2026 Undoit Project. Распространяется свободно под лицензией MIT.'
      : '© 2026 Undoit Project. Released freely under the MIT License.';
}
