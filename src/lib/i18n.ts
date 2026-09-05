import { writable, derived } from 'svelte/store';

export type Locale = 'ru' | 'en';

export const translations = {
  ru: {
    // App Header & Top Bar
    appTitle: 'Undoit',
    appSubtitle: 'Локальная машина времени для ваших файлов',
    monitoringActive: 'Отслеживание активно',
    monitoringPaused: 'Отслеживание приостановлено',
    pause: 'Пауза',
    resume: 'Возобновить',
    settings: 'Настройки',
    refresh: 'Обновить',

    // Relative Time
    timeAgoJustNow: 'только что',
    timeAgoMinutes: 'мин. назад',
    timeAgoHours: 'ч. назад',
    timeAgoYesterday: 'вчера',
    timeAgoDays: 'дн. назад',

    // Search and Sidebar
    sidebarTitle: 'Отслеживаемые файлы',
    searchPlaceholder: 'Поиск по имени или пути...',
    allFiles: 'Все файлы',
    today: 'Сегодня',
    yesterday: 'Вчера',
    thisWeek: 'На этой неделе',
    older: 'Ранее',
    noFilesFound: 'Файлы не найдены',
    noVersionsForFile: 'Нет сохраненных версий для этого файла',
    trackedFilesCount: 'файлов в наблюдении',
    totalVersionsCount: 'версий в БД',
    fileVersions: 'версий',
    never: 'никогда',
    treeView: 'Дерево',
    listView: 'Список',
    expandAll: 'Развернуть всё',
    collapseAll: 'Свернуть всё',
    otherFiles: 'Другие файлы',

    // File Details & Actions
    currentVersion: 'Текущий файл на диске',
    versionHistory: 'История изменений',
    restore: 'Восстановить эту версию',
    restoreShort: 'Восстановить',
    restoreConfirm: 'Вы уверены, что хотите восстановить эту версию? Текущий файл будет заменен версией из архива.',
    openExternal: 'В приложении',
    openExternalTooltip: 'Открыть историческую версию в системной программе без перезаписи',
    compare: 'Сравнить',
    diffWithCurrent: 'С текущим на диске',
    diffWithPrevious: 'С предыдущей версией',
    copyPath: 'Копировать путь',
    pathCopied: 'Путь скопирован в буфер обмена',
    fileSize: 'Размер',
    modifiedTime: 'Изменен',
    versionSaved: 'Сохранено',
    selectedSnapshot: 'Выбранный снимок',

    // Diff Viewer & Visualizer
    diffTitle: 'Сравнение версий',
    visualDiff: 'Визуальный просмотр',
    textDiff: 'Текстовый дифф',
    rawContent: 'Текст снимка',
    splitMode: 'Сплит-слайдер',
    sideBySideMode: 'Бок о бок',
    hideWhitespace: 'Игнорировать пробелы',
    page: 'Стр.',
    of: 'из',
    docxNotice: 'DOCX: Отображается читаемый текст документа',
    docxNoticeDesc: 'Форматирование и разметка упрощены для точного анализа правок.',
    linesAdded: 'добавлено',
    linesRemoved: 'удалено',
    noChangesDetected: 'Изменений между версиями не обнаружено',
    binaryFileDiffNotice: 'Бинарный файл. Визуальный просмотр недоступен для этого формата.',
    sliderNotice: 'Перемещайте разделитель для визуального сравнения до/после',

    // Settings Modal Tabs
    settingsHeading: 'Настройки Undoit',
    foldersTab: 'Папки',
    retentionTab: 'Хранение и лимиты',
    ignoresTab: 'Исключения',
    systemTab: 'Система',

    // Folders Tab
    watchedFoldersHeading: 'Отслеживаемые папки',
    watchedFoldersDesc: 'Любые изменения файлов внутри этих папок будут автоматически и мгновенно сохраняться в историю.',
    folderPathPlaceholder: 'Путь к папке...',
    browse: 'Обзор...',
    addFolder: '+ Добавить',
    noFoldersHint: 'Нет добавленных папок. Нажмите «Обзор...», чтобы выбрать папку проекта.',
    removeFromWatching: 'Удалить из отслеживания',

    // Retention Tab
    retentionHeading: 'Политика хранения снимков',
    retentionDesc: 'Настройте автоматическую очистку старых версий для экономии дискового пространства.',
    retentionDaysLabel: 'Срок хранения версий (дней):',
    retentionDaysHint: '0 = бессрочно (не удалять по возрасту)',
    maxVersionsLabel: 'Макс. версий на один файл:',
    maxVersionsHint: '0 = без ограничений количества',
    manualPruneHeading: 'Ручная очистка хранилища',
    manualPruneDesc: 'Применяет правила очистки и удаляет неиспользуемые сжатые объекты с диска.',
    cleanOldVersions: '🧹 Очистить старые версии',
    cleaning: 'Очистка...',

    // Ignores Tab
    ignoreHeading: 'Игнорируемые файлы и папки',
    ignoreDesc: 'Шаблоны путей и расширений, которые Undoit не будет сохранять в историю.',
    ignorePatternPlaceholder: 'Шаблон, например: *.log или dist',
    addRule: 'Добавить правило',

    // System Tab
    systemHeading: 'Системные параметры',
    autostartTitle: 'Автозапуск при входе в Windows',
    autostartDesc: 'Запускать Undoit автоматически в фоновом режиме (в трей) при включении компьютера.',
    explorerMenuTitle: 'Интеграция в контекстное меню Проводника Windows',
    explorerMenuDesc: 'Добавляет пункт «История версий Undoit» при нажатии правой кнопкой мыши на любой файл или папку в Проводнике.',
    themeTitle: 'Тема оформления',
    themeDesc: 'Выберите цветовой стиль интерфейса.',
    themeDark: 'Тёмная (Dark Slate)',
    themeLight: 'Светлая (Clean Light)',
    languageTitle: 'Язык интерфейса / Interface Language',
    languageDesc: 'Язык отображения приложения и системного трея.',

    // Stats
    storageStatsHeading: 'Статистика хранилища',
    statsVersions: 'Снимков',
    statsOriginal: 'Оригинал',
    statsCompressed: 'Zstd',
    statsSavings: 'Экономия',

    // Toasts & Alerts
    settingsSaved: 'Настройки успешно сохранены',
    settingsSaveError: 'Ошибка сохранения настроек',
    restoreSuccess: 'Версия успешно восстановлена!',
    restoreError: 'Ошибка при восстановлении версии',
    restoreFileLocked: 'Файл заблокирован другой программой',
    restoreFileLockedDesc: 'Файл открыт и заблокирован другой программой (например, Word, Excel или текстовым редактором).\n\nПожалуйста, закройте документ в редакторе и повторите восстановление.',
    openedInExternal: 'Открыто во внешнем приложении',
    contextMenuAdded: 'Пункт в контекстном меню Проводника добавлен',
    contextMenuRemoved: 'Пункт удален из Проводника',
    contextMenuError: 'Ошибка настройки контекстного меню',
    pruneSuccess: 'Очистка завершена',
    folderAdded: 'Папка добавлена в отслеживание',
    folderRemoved: 'Папка удалена из отслеживания',
  },
  en: {
    // App Header & Top Bar
    appTitle: 'Undoit',
    appSubtitle: 'Local time machine for your creative and project files',
    monitoringActive: 'Monitoring active',
    monitoringPaused: 'Monitoring paused',
    pause: 'Pause',
    resume: 'Resume',
    settings: 'Settings',
    refresh: 'Refresh',

    // Relative Time
    timeAgoJustNow: 'just now',
    timeAgoMinutes: 'min ago',
    timeAgoHours: 'hr ago',
    timeAgoYesterday: 'yesterday',
    timeAgoDays: 'days ago',

    // Search and Sidebar
    sidebarTitle: 'Tracked Files',
    searchPlaceholder: 'Search by filename or path...',
    allFiles: 'All files',
    today: 'Today',
    yesterday: 'Yesterday',
    thisWeek: 'This week',
    older: 'Older',
    noFilesFound: 'No files found',
    noVersionsForFile: 'No saved versions for this file',
    trackedFilesCount: 'tracked files',
    totalVersionsCount: 'versions in DB',
    fileVersions: 'versions',
    never: 'never',
    treeView: 'Tree',
    listView: 'List',
    expandAll: 'Expand all',
    collapseAll: 'Collapse all',
    otherFiles: 'Other files',

    // File Details & Actions
    currentVersion: 'Current file on disk',
    versionHistory: 'Version History',
    restore: 'Restore this version',
    restoreShort: 'Restore',
    restoreConfirm: 'Are you sure you want to restore this version? The current file will be replaced with this archived snapshot.',
    openExternal: 'In App',
    openExternalTooltip: 'Open this historical snapshot in your default app without overwriting current file',
    compare: 'Compare',
    diffWithCurrent: 'With current on disk',
    diffWithPrevious: 'With previous version',
    copyPath: 'Copy path',
    pathCopied: 'Path copied to clipboard',
    fileSize: 'Size',
    modifiedTime: 'Modified',
    versionSaved: 'Saved',
    selectedSnapshot: 'Selected snapshot',

    // Diff Viewer & Visualizer
    diffTitle: 'Version Comparison',
    visualDiff: 'Visual Diff',
    textDiff: 'Text Diff',
    rawContent: 'Snapshot Text',
    splitMode: 'Split Slider',
    sideBySideMode: 'Side by Side',
    hideWhitespace: 'Ignore whitespace',
    page: 'Page',
    of: 'of',
    docxNotice: 'DOCX: Displaying readable document text',
    docxNoticeDesc: 'Formatting is stripped for precise line-by-line editorial diff analysis.',
    linesAdded: 'added',
    linesRemoved: 'removed',
    noChangesDetected: 'No differences detected between versions',
    binaryFileDiffNotice: 'Binary file. Visual preview is not available for this format.',
    sliderNotice: 'Drag the divider to visually compare before & after',

    // Settings Modal Tabs
    settingsHeading: 'Undoit Preferences',
    foldersTab: 'Folders',
    retentionTab: 'Retention & Limits',
    ignoresTab: 'Exclusions',
    systemTab: 'System',

    // Folders Tab
    watchedFoldersHeading: 'Watched Folders',
    watchedFoldersDesc: 'Any file changes inside these folders are automatically and immediately saved into history.',
    folderPathPlaceholder: 'Folder path...',
    browse: 'Browse...',
    addFolder: '+ Add',
    noFoldersHint: 'No watched folders yet. Click "Browse..." to select a project directory.',
    removeFromWatching: 'Remove from watching',

    // Retention Tab
    retentionHeading: 'Snapshot Retention Policy',
    retentionDesc: 'Configure automatic cleanup of older versions to save disk space.',
    retentionDaysLabel: 'Version retention period (days):',
    retentionDaysHint: '0 = indefinite (never delete by age)',
    maxVersionsLabel: 'Max versions per file:',
    maxVersionsHint: '0 = unlimited versions',
    manualPruneHeading: 'Manual Storage Cleanup',
    manualPruneDesc: 'Applies pruning rules and removes unreferenced compressed blobs from disk.',
    cleanOldVersions: '🧹 Clean old versions',
    cleaning: 'Cleaning...',

    // Ignores Tab
    ignoreHeading: 'Ignored Files and Folders',
    ignoreDesc: 'Path and extension patterns that Undoit will skip from history.',
    ignorePatternPlaceholder: 'Pattern, e.g.: *.log or dist',
    addRule: 'Add rule',

    // System Tab
    systemHeading: 'System Parameters',
    autostartTitle: 'Autostart with Windows',
    autostartDesc: 'Start Undoit automatically in the background (system tray) on boot.',
    explorerMenuTitle: 'Windows Explorer Context Menu Integration',
    explorerMenuDesc: 'Adds "Undoit Version History" when right-clicking files or folders in Windows Explorer.',
    themeTitle: 'Appearance Theme',
    themeDesc: 'Choose user interface color palette.',
    themeDark: 'Dark (Dark Slate)',
    themeLight: 'Light (Clean Light)',
    languageTitle: 'Interface Language / Язык интерфейса',
    languageDesc: 'Display language for the app interface and system tray.',

    // Stats
    storageStatsHeading: 'Storage Statistics',
    statsVersions: 'Snapshots',
    statsOriginal: 'Original',
    statsCompressed: 'Zstd',
    statsSavings: 'Saved',

    // Toasts & Alerts
    settingsSaved: 'Preferences saved successfully',
    settingsSaveError: 'Failed to save preferences',
    restoreSuccess: 'Version restored successfully!',
    restoreError: 'Failed to restore version',
    restoreFileLocked: 'File is locked by another program',
    restoreFileLockedDesc: 'The file is currently open and locked by another program (e.g. Word, Excel, or a text editor).\n\nPlease close the document in your editor and try restoring again.',
    openedInExternal: 'Opened in external application',
    contextMenuAdded: 'Explorer context menu item added',
    contextMenuRemoved: 'Explorer context menu item removed',
    contextMenuError: 'Failed to configure context menu',
    pruneSuccess: 'Storage cleanup completed',
    folderAdded: 'Folder added to watch list',
    folderRemoved: 'Folder removed from watch list',
  },
} as const;

export type TranslationKey = keyof typeof translations.ru;

function getInitialLocale(): Locale {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('undoit_locale');
    if (saved === 'ru' || saved === 'en') {
      return saved;
    }
    const navLang = navigator.language?.toLowerCase() || '';
    if (navLang.startsWith('ru') || navLang.startsWith('be') || navLang.startsWith('uk')) {
      return 'ru';
    }
  }
  return 'en';
}

export const locale = writable<Locale>(getInitialLocale());

export function setLocale(newLocale: Locale) {
  locale.set(newLocale);
  if (typeof window !== 'undefined') {
    localStorage.setItem('undoit_locale', newLocale);
  }
}

export const t = derived(locale, ($locale) => {
  return (key: TranslationKey): string => {
    return translations[$locale]?.[key] ?? translations.en[key] ?? key;
  };
});
