<script lang="ts">
  import { onMount } from "svelte";
  import { invoke } from "@tauri-apps/api/core";
  import { listen } from "@tauri-apps/api/event";
  import { open, save } from "@tauri-apps/plugin-dialog";
  import { enable as enableAutostart, disable as disableAutostart, isEnabled as isAutostartEnabled } from "@tauri-apps/plugin-autostart";
  import {
    isVisualDocument,
    isPdfOrAi,
    isDocx,
    renderPdfToDataUrl
  } from "$lib/pdfRenderer";

  interface TrackedFile {
    id: number;
    original_path: string;
    filename: string;
    folder_id: number | null;
    is_active: boolean;
    updated_at: string;
    version_count: number;
    latest_size: number;
  }

  interface FileVersion {
    id: number;
    file_id: number;
    timestamp: string;
    hash: string;
    file_size: number;
    compressed_size: number;
  }

  interface DiffLine {
    tag: "insert" | "delete" | "equal";
    old_line_num: number | null;
    new_line_num: number | null;
    text: string;
  }

  interface DiffResult {
    lines: DiffLine[];
    additions: number;
    deletions: number;
    is_binary: boolean;
  }

  interface StorageStats {
    total_versions: number;
    total_files: number;
    total_original_bytes: number;
    total_compressed_bytes: number;
    saved_ratio: number;
  }

  interface WatchedFolder {
    id: number;
    path: string;
    created_at: string;
  }

  interface AppSettings {
    retention_days: number;
    max_versions_per_file: number;
    max_storage_mb: number;
    ignore_patterns: string[];
    theme: string;
    autostart: boolean;
    minimize_to_tray: boolean;
  }

  let files = $state<TrackedFile[]>([]);
  let selectedFile = $state<TrackedFile | null>(null);
  let versions = $state<FileVersion[]>([]);
  let selectedVersionIndex = $state<number>(0);
  let diff = $state<DiffResult | null>(null);
  let textContent = $state<string>("");
  let activeTab = $state<"diff" | "content">("diff");
  let compareMode = $state<"current" | "previous">("current");
  let searchQuery = $state<string>("");
  let stats = $state<StorageStats | null>(null);
  let showSettings = $state<boolean>(false);
  let settingsTab = $state<"folders" | "retention" | "ignores" | "system">("folders");
  let watchedFolders = $state<WatchedFolder[]>([]);
  let newFolderPath = $state<string>("");
  let newIgnorePattern = $state<string>("");
  let isPaused = $state<boolean>(false);
  let toastMessage = $state<string | null>(null);
  let isRestoring = $state<boolean>(false);
  let isPruning = $state<boolean>(false);
  let explorerContextMenu = $state<boolean>(false);

  // Image & Binary visualizer state
  let versionImageDataUrl = $state<string | null>(null);
  let compareImageDataUrl = $state<string | null>(null);
  let imageDiffMode = $state<"slider" | "side-by-side">("slider");
  let sliderPos = $state<number>(50);
  let imageZoom = $state<number>(1);
  let isImageLoading = $state<boolean>(false);
  let pdfPage = $state<number>(1);
  let pdfTotalPages = $state<number>(1);

  function isImage(filename: string | undefined): boolean {
    return isVisualDocument(filename);
  }

  let settings = $state<AppSettings>({
    retention_days: 30,
    max_versions_per_file: 50,
    max_storage_mb: 2048,
    ignore_patterns: ["*.tmp", "*.log", "node_modules", "target", ".venv", ".git", "build", "dist"],
    theme: "dark",
    autostart: false,
    minimize_to_tray: true,
  });

  async function toggleExplorerContextMenu() {
    try {
      explorerContextMenu = await invoke<boolean>("set_explorer_context_menu", { enabled: explorerContextMenu });
      showToast(explorerContextMenu ? "Пункт в контекстном меню Проводника добавлен" : "Пункт удален из Проводника");
    } catch (e) {
      alert("Ошибка настройки контекстного меню: " + e);
    }
  }

  let filteredFiles = $derived(
    files.filter(f => 
      f.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.original_path.toLowerCase().includes(searchQuery.toLowerCase())
    )
  );

  let currentVersion = $derived(
    versions.length > 0 && selectedVersionIndex >= 0 && selectedVersionIndex < versions.length
      ? versions[selectedVersionIndex]
      : null
  );

  function showToast(msg: string) {
    toastMessage = msg;
    setTimeout(() => {
      if (toastMessage === msg) toastMessage = null;
    }, 3500);
  }

  function formatBytes(bytes: number): string {
    if (!bytes || bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  function formatRelativeDate(isoStr: string): string {
    try {
      const date = new Date(isoStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffSec = Math.floor(diffMs / 1000);
      const diffMin = Math.floor(diffSec / 60);
      const diffHours = Math.floor(diffMin / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffSec < 60) return "только что";
      if (diffMin < 60) return `${diffMin} мин. назад`;
      if (diffHours < 24) return `${diffHours} ч. назад`;
      if (diffDays === 1) return "вчера";
      if (diffDays < 7) return `${diffDays} дн. назад`;
      return date.toLocaleDateString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoStr;
    }
  }

  async function loadFiles() {
    try {
      files = await invoke<TrackedFile[]>("get_tracked_files");
    } catch (e) {
      console.error(e);
    }
  }

  async function loadStats() {
    try {
      stats = await invoke<StorageStats>("get_storage_stats");
    } catch (e) {
      console.error(e);
    }
  }

  async function loadWatchedFolders() {
    try {
      watchedFolders = await invoke<WatchedFolder[]>("get_watched_folders");
    } catch (e) {
      console.error(e);
    }
  }

  async function loadSettings() {
    try {
      settings = await invoke<AppSettings>("get_settings");
      // Check system autostart state
      try {
        const autostartActive = await isAutostartEnabled();
        settings.autostart = autostartActive;
      } catch (e) {
        console.warn("Autostart check failed:", e);
      }
      applyTheme(settings.theme);
    } catch (e) {
      console.error(e);
    }
  }

  async function saveAppSettings() {
    try {
      await invoke("save_settings", { settings });
      // Handle autostart plugin
      try {
        if (settings.autostart) {
          await enableAutostart();
        } else {
          await disableAutostart();
        }
      } catch (e) {
        console.warn("Autostart update failed:", e);
      }
      applyTheme(settings.theme);
      showToast("Настройки успешно сохранены");
    } catch (e) {
      alert("Ошибка сохранения настроек: " + e);
    }
  }

  function applyTheme(themeName: string) {
    if (themeName === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  }

  async function selectFile(file: TrackedFile) {
    selectedFile = file;
    selectedVersionIndex = 0;
    pdfPage = 1;
    pdfTotalPages = 1;
    try {
      versions = await invoke<FileVersion[]>("get_versions", { fileId: file.id });
      if (versions.length > 0) {
        await loadVersionPreview(0);
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function changePdfPage(newPage: number) {
    if (newPage < 1 || newPage > pdfTotalPages) return;
    pdfPage = newPage;
    await loadVersionPreview(selectedVersionIndex);
  }

  async function openInExternalApp() {
    if (!currentVersion || !selectedFile) return;
    try {
      await invoke("open_version_in_external_app", { versionId: currentVersion.id });
      showToast(`Открыто во внешнем приложении: ${selectedFile.filename}`);
    } catch (e) {
      alert("Ошибка открытия во внешнем приложении: " + e);
    }
  }

  async function loadVersionPreview(index: number) {
    selectedVersionIndex = index;
    const version = versions[index];
    if (!version || !selectedFile) return;

    if (isVisualDocument(selectedFile.filename)) {
      isImageLoading = true;
      try {
        if (isPdfOrAi(selectedFile.filename)) {
          // Render PDF or AI document with pdfjs-dist / XMP fallback
          const rawBytes = await invoke<number[]>("get_version_raw_bytes", {
            hash: version.hash,
          });
          const renderRes = await renderPdfToDataUrl(new Uint8Array(rawBytes), pdfPage, 1.5);
          versionImageDataUrl = renderRes.dataUrl;
          pdfTotalPages = renderRes.totalPages;

          if (activeTab === "diff") {
            if (compareMode === "current") {
              const curBytes = await invoke<number[] | null>("get_current_file_raw_bytes", {
                path: selectedFile.original_path,
              });
              if (curBytes) {
                const compRes = await renderPdfToDataUrl(new Uint8Array(curBytes), pdfPage, 1.5);
                compareImageDataUrl = compRes.dataUrl;
              } else {
                compareImageDataUrl = null;
              }
            } else {
              if (index + 1 < versions.length) {
                const prevVer = versions[index + 1];
                const prevBytes = await invoke<number[]>("get_version_raw_bytes", {
                  hash: prevVer.hash,
                });
                const compRes = await renderPdfToDataUrl(new Uint8Array(prevBytes), pdfPage, 1.5);
                compareImageDataUrl = compRes.dataUrl;
              } else {
                compareImageDataUrl = null;
              }
            }
          }
        } else {
          // Standard image file (PNG, JPG, SVG, WebP, etc.)
          versionImageDataUrl = await invoke<string>("get_version_data_url", {
            hash: version.hash,
            originalPath: selectedFile.original_path
          });

          if (activeTab === "diff") {
            if (compareMode === "current") {
              compareImageDataUrl = await invoke<string | null>("get_current_file_data_url", {
                path: selectedFile.original_path
              });
            } else {
              compareImageDataUrl = await invoke<string | null>("get_prev_version_data_url", {
                fileId: selectedFile.id,
                currentVersionId: version.id,
                originalPath: selectedFile.original_path
              });
            }
          }
        }
      } catch (e) {
        console.error("Ошибка загрузки визуального документа:", e);
      } finally {
        isImageLoading = false;
      }
    } else {
      versionImageDataUrl = null;
      compareImageDataUrl = null;
      try {
        if (activeTab === "diff") {
          diff = await invoke<DiffResult>("get_version_diff", {
            versionId: version.id,
            compareWithCurrent: compareMode === "current"
          });
        } else {
          textContent = await invoke<string>("get_version_text", { hash: version.hash });
        }
      } catch (e) {
        console.error(e);
      }
    }
  }

  async function restoreSelectedVersion() {
    if (!currentVersion || !selectedFile) return;
    if (!confirm(`Восстановить файл "${selectedFile.filename}" до состояния от ${formatRelativeDate(currentVersion.timestamp)}?\n\nТекущий файл перед заменой будет автоматически сохранен в историю.`)) {
      return;
    }

    isRestoring = true;
    try {
      await invoke("restore_version", { versionId: currentVersion.id });
      showToast(`Файл "${selectedFile.filename}" успешно восстановлен!`);
      await loadFiles();
      await loadStats();
      if (selectedFile) await selectFile(selectedFile);
    } catch (e) {
      alert("Ошибка восстановления: " + e);
    } finally {
      isRestoring = false;
    }
  }

  async function saveVersionAs() {
    if (!currentVersion || !selectedFile) return;

    try {
      const selectedPath = await save({
        defaultPath: selectedFile.filename,
        title: `Сохранить снимок "${selectedFile.filename}" как...`
      });

      if (selectedPath) {
        await invoke("save_version_as", {
          versionId: currentVersion.id,
          targetPath: selectedPath
        });
        showToast("Снимок успешно сохранен в файл");
      }
    } catch (e) {
      alert("Ошибка сохранения: " + e);
    }
  }

  async function openInExplorer() {
    if (!selectedFile) return;
    try {
      await invoke("open_in_explorer", { path: selectedFile.original_path });
    } catch (e) {
      alert("Не удалось открыть в проводнике: " + e);
    }
  }

  async function deleteCurrentFileFromTracking() {
    if (!selectedFile) return;
    if (!confirm(`Удалить файл "${selectedFile.filename}" и все его ${selectedFile.version_count} сохраненных версий из истории Undoit?`)) {
      return;
    }

    try {
      await invoke("delete_tracked_file", { fileId: selectedFile.id });
      selectedFile = null;
      versions = [];
      diff = null;
      textContent = "";
      await loadFiles();
      await loadStats();
      showToast("Файл удален из истории");
    } catch (e) {
      alert("Ошибка удаления: " + e);
    }
  }

  async function togglePause() {
    try {
      isPaused = await invoke<boolean>("toggle_pause_monitoring");
      showToast(isPaused ? "Мониторинг файлов приостановлен" : "Мониторинг возобновлен");
    } catch (e) {
      console.error(e);
    }
  }

  async function browseFolder() {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: "Выберите папку для отслеживания Undoit"
      });

      if (selected && typeof selected === "string") {
        newFolderPath = selected;
        await addFolder();
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function addFolder() {
    if (!newFolderPath.trim()) return;
    try {
      await invoke("add_watched_folder", { path: newFolderPath.trim() });
      newFolderPath = "";
      await loadWatchedFolders();
      await loadFiles();
      await loadStats();
      showToast("Папка добавлена в мониторинг");
    } catch (e) {
      alert("Ошибка добавления папки: " + e);
    }
  }

  async function removeFolder(id: number, path: string) {
    if (!confirm(`Перестать отслеживать изменения в папке "${path}"?`)) return;
    try {
      await invoke("remove_watched_folder", { id, path });
      await loadWatchedFolders();
      showToast("Папка удалена из списка мониторинга");
    } catch (e) {
      console.error(e);
    }
  }

  function addIgnorePattern() {
    const pat = newIgnorePattern.trim();
    if (!pat) return;
    if (!settings.ignore_patterns.includes(pat)) {
      settings.ignore_patterns = [...settings.ignore_patterns, pat];
      saveAppSettings();
    }
    newIgnorePattern = "";
  }

  function removeIgnorePattern(pattern: string) {
    settings.ignore_patterns = settings.ignore_patterns.filter(p => p !== pattern);
    saveAppSettings();
  }

  async function runStoragePrune() {
    isPruning = true;
    try {
      const res: any = await invoke("prune_storage");
      await loadStats();
      await loadFiles();
      showToast(`Очистка завершена: удалено ${res.deleted_versions} снимков и ${res.deleted_objects} файлов`);
    } catch (e) {
      alert("Ошибка очистки: " + e);
    } finally {
      isPruning = false;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape" && showSettings) {
      showSettings = false;
    }
  }

  onMount(() => {
    loadSettings();
    loadFiles();
    loadStats();
    loadWatchedFolders();

    // Check pause status
    invoke<boolean>("get_monitoring_status").then(active => {
      isPaused = !active;
    }).catch(() => {});

    // Check explorer context menu status
    invoke<boolean>("get_explorer_context_menu_status").then(enabled => {
      explorerContextMenu = enabled;
    }).catch(() => {});

    // Listen for real-time background file change events from Rust!
    const unlisten1 = listen("version-saved", (event: any) => {
      loadStats();
      loadFiles();
      if (selectedFile && selectedFile.id === event.payload.file_id) {
        selectFile(selectedFile);
      }
    });

    const unlisten2 = listen("tray-open-settings", () => {
      showSettings = true;
      settingsTab = "system";
    });

    const unlisten3 = listen("tray-open-add-folder", () => {
      showSettings = true;
      settingsTab = "folders";
      browseFolder();
    });

    const unlisten4 = listen<boolean>("monitoring-status-changed", (event) => {
      isPaused = Boolean(event.payload);
      showToast(isPaused ? "Мониторинг приостановлен" : "Мониторинг возобновлен");
    });

    const unlisten5 = listen("storage-pruned", () => {
      loadStats();
      loadFiles();
      showToast("Хранилище очищено из трея");
    });

    const unlisten6 = listen("open-file-path", async (event: any) => {
      const targetPath: string = event.payload;
      if (!targetPath) return;
      await loadFiles();
      const norm = targetPath.toLowerCase().replace(/\\/g, "/");
      const found = files.find(f => f.original_path.toLowerCase().replace(/\\/g, "/") === norm);
      if (found) {
        await selectFile(found);
      } else {
        searchQuery = targetPath.split(/[/\\]/).pop() || "";
      }
    });

    window.addEventListener("keydown", handleKeydown);

    return () => {
      window.removeEventListener("keydown", handleKeydown);
      unlisten1.then(u => u());
      unlisten2.then(u => u());
      unlisten3.then(u => u());
      unlisten4.then(u => u());
      unlisten5.then(u => u());
      unlisten6.then(u => u());
    };
  });
</script>

<div class="app-layout">
  <!-- Toast notification -->
  {#if toastMessage}
    <div class="toast">{toastMessage}</div>
  {/if}

  <!-- SIDEBAR: File explorer -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <svg class="logo-shield" viewBox="0 0 32 32">
          <!-- Outer U-shield outline matching original Undoit icon -->
          <path
            d="M6 5 v12 a10 10 0 0 0 20 0 v-12"
            fill="none"
            stroke="currentColor"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <clipPath id="shield-clip-sidebar">
            <path d="M7.5 5 v12 a8.5 8.5 0 0 0 17 0 v-12 z" />
          </clipPath>
          <rect
            x="7.5"
            y={27 - (22 * (stats ? Math.min(1, Math.max(0.1, stats.total_compressed_bytes / (settings.max_storage_mb * 1024 * 1024 || 1073741824))) : 0.15))}
            width="17"
            height="22"
            fill={isPaused ? '#808080' : ((stats?.total_compressed_bytes || 0) / (settings.max_storage_mb * 1024 * 1024 || 1073741824) <= 0.25 ? '#28a745' : ((stats?.total_compressed_bytes || 0) / (settings.max_storage_mb * 1024 * 1024 || 1073741824) <= 0.50 ? '#ffc107' : '#dc3545'))}
            clip-path="url(#shield-clip-sidebar)"
          />
        </svg>
        <div class="logo-text">
          <span class="logo-title">Undoit</span>
          <span class="logo-badge">v2.0</span>
        </div>
      </div>
      <div class="status-indicator" class:paused={isPaused} title={isPaused ? "Мониторинг на паузе" : "Мониторинг активен"}>
        <span class="status-dot"></span>
        <span class="status-label">{isPaused ? "Пауза" : "Активен"}</span>
      </div>
    </div>

    <!-- Search box -->
    <div class="search-container">
      <input
        type="text"
        placeholder="Поиск файлов..."
        bind:value={searchQuery}
        class="search-input"
      />
    </div>

    <!-- Files list -->
    <div class="files-list">
      {#if filteredFiles.length === 0}
        <div class="empty-files">
          <p>Нет отслеживаемых файлов</p>
          <small>Добавьте папку в Настройках ⚙</small>
        </div>
      {:else}
        {#each filteredFiles as file}
          <button
            class="file-item"
            class:active={selectedFile?.id === file.id}
            onclick={() => selectFile(file)}
          >
            <div class="file-icon" class:is-img={isImage(file.filename)}>
              {#if isImage(file.filename)}
                <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              {:else}
                <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              {/if}
            </div>
            <div class="file-info">
              <span class="file-name">{file.filename}</span>
              <span class="file-time">{formatRelativeDate(file.updated_at)}</span>
            </div>
            <div class="version-badge" title="Сохраненных снимков">
              {file.version_count}
            </div>
          </button>
        {/each}
      {/if}
    </div>

    <!-- Sidebar footer -->
    <div class="sidebar-footer">
      <button class="footer-btn" onclick={togglePause} title={isPaused ? "Возобновить" : "Приостановить"}>
        {isPaused ? "▶ Возобновить" : "⏸ Пауза"}
      </button>
      <button class="footer-btn settings-btn" onclick={() => showSettings = true} title="Настройки">
        ⚙ Настройки
      </button>
    </div>
  </aside>

  <!-- MAIN AREA -->
  <main class="main-content">
    {#if !selectedFile}
      <!-- Empty state dashboard -->
      <div class="empty-dashboard">
        <div class="empty-hero">
          <svg class="hero-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            <path d="M9 10a3 3 0 0 0 6 0V7" />
          </svg>
          <h2>Ваша локальная машина времени активна</h2>
          <p>Undoit в реальном времени сохраняет снимки при каждом изменении файлов, сжимает их алгоритмом Zstandard и строит наглядный Diff.</p>
          <div class="hero-actions">
            <button class="btn-primary" onclick={() => { showSettings = true; settingsTab = 'folders'; }}>
              + Добавить папку для отслеживания
            </button>
          </div>
        </div>

        {#if stats}
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-value">{stats.total_files}</div>
              <div class="stat-label">Отслеживаемых файлов</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{stats.total_versions}</div>
              <div class="stat-label">Сохраненных снимков</div>
            </div>
            <div class="stat-card highlight">
              <div class="stat-value">{stats.saved_ratio.toFixed(0)}%</div>
              <div class="stat-label">Экономия диска (Zstd)</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{formatBytes(stats.total_compressed_bytes)}</div>
              <div class="stat-label">Занято в хранилище</div>
            </div>
          </div>
        {/if}
      </div>
    {:else}
      <!-- FILE WORKSPACE -->
      <div class="workspace">
        <!-- Workspace header -->
        <header class="workspace-header">
          <div class="header-details">
            <h1 class="file-title">{selectedFile.filename}</h1>
            <p class="file-path" title={selectedFile.original_path}>{selectedFile.original_path}</p>
          </div>
          <div class="header-actions">
            <button class="btn-ghost" onclick={openInExplorer} title="Показать файл в проводнике Windows">
              📁 В проводнике
            </button>
            <button class="btn-ghost" onclick={openInExternalApp} disabled={!currentVersion} title="Открыть эту версию во внешней программе (Word, Acrobat, Illustrator...)">
              👁 В приложении
            </button>
            <button class="btn-ghost" onclick={saveVersionAs} disabled={!currentVersion} title="Экспортировать эту версию в новый файл">
              💾 Экспорт
            </button>
            <button class="btn-ghost danger" onclick={deleteCurrentFileFromTracking} title="Удалить файл и все версии из истории">
              🗑 Удалить
            </button>
            <button
              class="btn-primary"
              onclick={restoreSelectedVersion}
              disabled={isRestoring || !currentVersion}
            >
              {#if isRestoring}
                Восстановление...
              {:else}
                ⟲ Восстановить эту версию
              {/if}
            </button>
          </div>
        </header>

        <!-- TIMELINE SCRUBBER -->
        <section class="timeline-bar">
          <div class="timeline-meta">
            <span class="timeline-heading">
              Снимок #{versions.length - selectedVersionIndex} из {versions.length}
            </span>
            {#if currentVersion}
              <span class="timeline-date">
                {new Date(currentVersion.timestamp).toLocaleString("ru-RU")}
                <small>({formatRelativeDate(currentVersion.timestamp)})</small>
              </span>
              <span class="timeline-size">
                {formatBytes(currentVersion.file_size)}
                <span class="zstd-tag">Zstd: {formatBytes(currentVersion.compressed_size)}</span>
              </span>
            {/if}
          </div>

          <!-- Horizontal Time Scrubber Slider -->
          <div class="scrubber-track">
            <input
              type="range"
              min="0"
              max={Math.max(0, versions.length - 1)}
              bind:value={selectedVersionIndex}
              oninput={() => loadVersionPreview(selectedVersionIndex)}
              class="scrubber-slider"
            />
            <div class="scrubber-ticks">
              <span>← Новейшая</span>
              <span>Самая ранняя →</span>
            </div>
          </div>
        </section>

        <!-- PREVIEW & DIFF TABS -->
        <div class="tab-controls">
          <div class="tabs-group">
            <button
              class="tab-btn"
              class:active={activeTab === "diff"}
              onclick={() => { activeTab = "diff"; loadVersionPreview(selectedVersionIndex); }}
            >
              {#if isVisualDocument(selectedFile.filename)}
                🖼 Визуальное сравнение
              {:else if isDocx(selectedFile.filename)}
                📝 Изменения в Word (Diff)
              {:else}
                Diff (Изменения)
              {/if}
            </button>
            <button
              class="tab-btn"
              class:active={activeTab === "content"}
              onclick={() => { activeTab = "content"; loadVersionPreview(selectedVersionIndex); }}
            >
              {#if isVisualDocument(selectedFile.filename)}
                👁 Просмотр снимка
              {:else if isDocx(selectedFile.filename)}
                📄 Текст документа
              {:else}
                Полный текст версии
              {/if}
            </button>
          </div>

          {#if activeTab === "diff"}
            <div class="diff-controls-right">
              {#if isVisualDocument(selectedFile.filename)}
                {#if isPdfOrAi(selectedFile.filename) && pdfTotalPages > 1}
                  <div class="pdf-page-controls">
                    <button class="compare-btn" disabled={pdfPage <= 1} onclick={() => changePdfPage(pdfPage - 1)} title="Предыдущая страница">◀</button>
                    <span class="zoom-level">Стр. {pdfPage} / {pdfTotalPages}</span>
                    <button class="compare-btn" disabled={pdfPage >= pdfTotalPages} onclick={() => changePdfPage(pdfPage + 1)} title="Следующая страница">▶</button>
                  </div>
                {/if}

                <div class="image-mode-switch">
                  <button
                    class="compare-btn"
                    class:active={imageDiffMode === "slider"}
                    onclick={() => imageDiffMode = "slider"}
                    title="Интерактивная шторка сравнения"
                  >
                    ↔ Шторка
                  </button>
                  <button
                    class="compare-btn"
                    class:active={imageDiffMode === "side-by-side"}
                    onclick={() => imageDiffMode = "side-by-side"}
                    title="Сравнение рядом"
                  >
                    ◫ Рядом
                  </button>
                </div>
              {/if}

              <div class="compare-switch">
                <span class="compare-label">Сравнить с:</span>
                <button
                  class="compare-btn"
                  class:active={compareMode === "current"}
                  onclick={() => { compareMode = "current"; loadVersionPreview(selectedVersionIndex); }}
                >
                  Текущим файлом
                </button>
                <button
                  class="compare-btn"
                  class:active={compareMode === "previous"}
                  onclick={() => { compareMode = "previous"; loadVersionPreview(selectedVersionIndex); }}
                >
                  Предыдущей версией
                </button>
              </div>
            </div>
          {:else if isVisualDocument(selectedFile.filename)}
            <div class="zoom-controls">
              {#if isPdfOrAi(selectedFile.filename) && pdfTotalPages > 1}
                <div class="pdf-page-controls">
                  <button class="compare-btn" disabled={pdfPage <= 1} onclick={() => changePdfPage(pdfPage - 1)} title="Предыдущая страница">◀</button>
                  <span class="zoom-level">Стр. {pdfPage} / {pdfTotalPages}</span>
                  <button class="compare-btn" disabled={pdfPage >= pdfTotalPages} onclick={() => changePdfPage(pdfPage + 1)} title="Следующая страница">▶</button>
                </div>
              {/if}
              <button class="compare-btn" onclick={() => imageZoom = Math.max(0.25, parseFloat((imageZoom - 0.25).toFixed(2)))} title="Уменьшить">-</button>
              <span class="zoom-level">{Math.round(imageZoom * 100)}%</span>
              <button class="compare-btn" onclick={() => imageZoom = Math.min(3, parseFloat((imageZoom + 0.25).toFixed(2)))} title="Увеличить">+</button>
              <button class="compare-btn" onclick={() => imageZoom = 1} title="Масштаб 1:1">100%</button>
            </div>
          {/if}
        </div>

        <!-- VIEWER -->
        <div class="viewer-container">
          {#if isImage(selectedFile.filename)}
            <!-- IMAGE HANDLING -->
            {#if isImageLoading}
              <div class="image-loading-state">
                <div class="spinner"></div>
                <p>Загрузка изображения...</p>
              </div>
            {:else if activeTab === "diff"}
              <!-- IMAGE DIFF TAB -->
              {#if !compareImageDataUrl}
                <div class="image-notice-box">
                  <span class="notice-icon">ℹ️</span>
                  <div>
                    <strong>Нет версии для сравнения</strong>
                    <p>
                      {compareMode === "current"
                        ? "Текущий файл на диске отсутствует или недоступен."
                        : "Это самая ранняя сохраненная версия файла (предыдущих версий нет)."}
                    </p>
                  </div>
                </div>
                {#if versionImageDataUrl}
                  <div class="single-image-box">
                    <img src={versionImageDataUrl} alt={selectedFile.filename} class="preview-img" />
                  </div>
                {/if}
              {:else if imageDiffMode === "slider"}
                <!-- SPLIT SLIDER COMPARISON -->
                <div class="split-slider-wrapper">
                  <div class="split-slider-container">
                    <!-- Base image (Compare target: current file or previous version) -->
                    <img
                      src={compareImageDataUrl}
                      alt="Эталон"
                      class="split-img base"
                    />

                    <!-- Top image (Selected version) clipped by slider position -->
                    <div
                      class="split-overlay"
                      style="clip-path: polygon(0 0, {sliderPos}% 0, {sliderPos}% 100%, 0 100%);"
                    >
                      <img
                        src={versionImageDataUrl}
                        alt="Выбранная версия"
                        class="split-img overlay"
                      />
                    </div>

                    <!-- Divider handle line -->
                    <div class="split-divider" style="left: {sliderPos}%;">
                      <div class="split-handle">↔</div>
                    </div>

                    <!-- Floating tags -->
                    <div class="split-tag left">
                      ◀ Снимок #{versions.length - selectedVersionIndex} ({formatBytes(currentVersion?.file_size || 0)})
                    </div>
                    <div class="split-tag right">
                      {compareMode === "current" ? "Текущий на диске" : "Предыдущая версия"} ▶
                    </div>

                    <!-- Interactive range slider over entire image -->
                    <input
                      type="range"
                      min="0"
                      max="100"
                      bind:value={sliderPos}
                      class="split-input-range"
                      aria-label="Шторка сравнения"
                    />
                  </div>

                  <!-- Preset buttons bar -->
                  <div class="slider-presets-bar">
                    <span class="slider-val-badge">{sliderPos}%</span>
                    <button class="preset-btn" class:active={sliderPos === 0} onclick={() => sliderPos = 0}>
                      0% (Эталон)
                    </button>
                    <button class="preset-btn" class:active={sliderPos === 25} onclick={() => sliderPos = 25}>
                      25%
                    </button>
                    <button class="preset-btn" class:active={sliderPos === 50} onclick={() => sliderPos = 50}>
                      50% (Пополам)
                    </button>
                    <button class="preset-btn" class:active={sliderPos === 75} onclick={() => sliderPos = 75}>
                      75%
                    </button>
                    <button class="preset-btn" class:active={sliderPos === 100} onclick={() => sliderPos = 100}>
                      100% (Снимок)
                    </button>
                  </div>
                </div>
              {:else}
                <!-- SIDE-BY-SIDE COMPARISON -->
                <div class="side-by-side-grid">
                  <div class="side-card">
                    <div class="side-card-header">
                      <span class="side-card-title">
                        {compareMode === "current" ? "Текущий файл на диске" : "Предыдущая версия"}
                      </span>
                    </div>
                    <div class="side-image-box">
                      <img src={compareImageDataUrl} alt="Эталон" class="side-img" />
                    </div>
                  </div>

                  <div class="side-card">
                    <div class="side-card-header">
                      <span class="side-card-title">
                        Снимок #{versions.length - selectedVersionIndex} ({formatBytes(currentVersion?.file_size || 0)})
                      </span>
                      <span class="zstd-tag">Zstd: {formatBytes(currentVersion?.compressed_size || 0)}</span>
                    </div>
                    <div class="side-image-box">
                      <img src={versionImageDataUrl} alt="Выбранная версия" class="side-img" />
                    </div>
                  </div>
                </div>
              {/if}
            {:else}
              <!-- IMAGE SINGLE VIEW TAB -->
              <div class="image-single-view">
                <div class="image-viewport">
                  {#if versionImageDataUrl}
                    <img
                      src={versionImageDataUrl}
                      alt={selectedFile.filename}
                      class="zoomable-img"
                      style="transform: scale({imageZoom});"
                    />
                  {/if}
                </div>
                {#if currentVersion}
                  <div class="image-info-bar">
                    <span>Формат: <strong>{selectedFile.filename.split('.').pop()?.toUpperCase()}</strong></span>
                    <span>Размер: <strong>{formatBytes(currentVersion.file_size)}</strong></span>
                    <span>В архиве: <strong>{formatBytes(currentVersion.compressed_size)}</strong></span>
                    <span class="pill-green">
                      Сжатие: <strong>{(((currentVersion.file_size - currentVersion.compressed_size) / Math.max(1, currentVersion.file_size)) * 100).toFixed(1)}%</strong>
                    </span>
                  </div>
                {/if}
              </div>
            {/if}
          {:else if (diff && diff.is_binary) || (textContent && textContent.startsWith("[Бинарный"))}
            <!-- NON-IMAGE BINARY CARD -->
            <div class="binary-card">
              <div class="binary-icon">📦</div>
              <h3 class="binary-title">Бинарный файл ({selectedFile.filename.split('.').pop()?.toUpperCase() || 'BIN'})</h3>
              <p class="binary-desc">Данный файл является бинарным. Текстовый построчный diff отключен для предотвращения искажения данных и зависания интерфейса.</p>
              
              <div class="binary-meta-table">
                <div class="binary-row">
                  <span class="meta-label">Размер версии:</span>
                  <span class="meta-val">{formatBytes(currentVersion?.file_size || 0)}</span>
                </div>
                <div class="binary-row">
                  <span class="meta-label">Размер в хранилище (Zstd):</span>
                  <span class="meta-val">{formatBytes(currentVersion?.compressed_size || 0)}</span>
                </div>
                <div class="binary-row">
                  <span class="meta-label">Хэш содержимого (BLAKE3):</span>
                  <code class="meta-hash">{currentVersion?.hash}</code>
                </div>
                <div class="binary-row">
                  <span class="meta-label">Время создания:</span>
                  <span class="meta-val">{currentVersion ? new Date(currentVersion.timestamp).toLocaleString("ru-RU") : ""}</span>
                </div>
              </div>

              <div class="binary-actions">
                <button
                  class="btn-primary"
                  onclick={restoreSelectedVersion}
                  disabled={isRestoring || !currentVersion}
                >
                  ⟲ Восстановить эту версию
                </button>
                <button class="btn-secondary" onclick={openInExternalApp} disabled={!currentVersion}>
                  👁 Открыть в приложении...
                </button>
                <button class="btn-secondary" onclick={saveVersionAs} disabled={!currentVersion}>
                  💾 Экспортировать как...
                </button>
              </div>
            </div>
          {:else}
            <!-- NORMAL TEXT VIEWER / DIFF -->
            {#if activeTab === "diff"}
              {#if diff}
                <div class="diff-header-summary">
                  <span class="add-badge">+{diff.additions} строк</span>
                  <span class="del-badge">-{diff.deletions} строк</span>
                  {#if isDocx(selectedFile.filename)}
                    <div class="docx-info-banner">
                      <span class="docx-badge">DOCX</span>
                      <span>Документ Word: сравнение текста параграфов</span>
                    </div>
                  {/if}
                </div>
                <div class="diff-viewer">
                  {#each diff.lines as line}
                    <div class="diff-row {line.tag}">
                      <div class="line-num old">{line.old_line_num ?? ""}</div>
                      <div class="line-num new">{line.new_line_num ?? ""}</div>
                      <div class="line-sign">{line.tag === "insert" ? "+" : line.tag === "delete" ? "-" : " "}</div>
                      <pre class="line-code">{line.text}</pre>
                    </div>
                  {/each}
                </div>
              {/if}
            {:else}
              <div class="content-viewer">
                {#if isDocx(selectedFile.filename)}
                  <div class="docx-info-banner-content">
                    <span class="docx-badge">DOCX</span>
                    <span>Извлеченный текст документа Word</span>
                  </div>
                {/if}
                <pre class="code-block">{textContent}</pre>
              </div>
            {/if}
          {/if}
        </div>
      </div>
    {/if}
  </main>
</div>

<!-- SETTINGS MODAL -->
{#if showSettings}
  <div
    class="modal-backdrop"
    role="presentation"
    onclick={() => showSettings = false}
  >
    <!-- Modal Card -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
      class="modal-card"
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-heading"
      tabindex="-1"
      onclick={e => e.stopPropagation()}
    >
      <div class="modal-header">
        <h2 id="settings-heading">Настройки Undoit</h2>
        <button class="close-btn" onclick={() => showSettings = false} aria-label="Закрыть">✕</button>
      </div>

      <!-- Settings Tabs Navigation -->
      <div class="modal-nav">
        <button
          class="modal-nav-btn"
          class:active={settingsTab === 'folders'}
          onclick={() => settingsTab = 'folders'}
        >
          📁 Папки ({watchedFolders.length})
        </button>
        <button
          class="modal-nav-btn"
          class:active={settingsTab === 'retention'}
          onclick={() => settingsTab = 'retention'}
        >
          ⏳ Хранение и лимиты
        </button>
        <button
          class="modal-nav-btn"
          class:active={settingsTab === 'ignores'}
          onclick={() => settingsTab = 'ignores'}
        >
          🚫 Исключения ({settings.ignore_patterns.length})
        </button>
        <button
          class="modal-nav-btn"
          class:active={settingsTab === 'system'}
          onclick={() => settingsTab = 'system'}
        >
          ⚙️ Система
        </button>
      </div>

      <div class="modal-body">
        {#if settingsTab === 'folders'}
          <section class="settings-section">
            <h3>Отслеживаемые папки</h3>
            <p class="section-desc">Любые изменения файлов внутри этих папок будут автоматически и мгновенно сохраняться в историю.</p>

            <div class="add-folder-row">
              <input
                type="text"
                placeholder="Путь к папке..."
                bind:value={newFolderPath}
                class="settings-input"
              />
              <button class="btn-secondary" onclick={browseFolder}>Обзор...</button>
              <button class="btn-primary" onclick={addFolder}>+ Добавить</button>
            </div>

            <div class="folders-list">
              {#if watchedFolders.length === 0}
                <div class="empty-hint">Нет добавленных папок. Нажмите «Обзор...», чтобы выбрать папку проекта.</div>
              {:else}
                {#each watchedFolders as folder}
                  <div class="folder-row">
                    <span class="folder-path" title={folder.path}>📁 {folder.path}</span>
                    <button class="remove-btn" onclick={() => removeFolder(folder.id, folder.path)} title="Удалить из отслеживания">🗑</button>
                  </div>
                {/each}
              {/if}
            </div>
          </section>

        {:else if settingsTab === 'retention'}
          <section class="settings-section">
            <h3>Политика хранения снимков</h3>
            <p class="section-desc">Настройте автоматическую очистку старых версий для экономии дискового пространства.</p>

            <div class="form-grid">
              <label class="form-field">
                <span class="field-label">Срок хранения версий (дней):</span>
                <input
                  type="number"
                  min="0"
                  bind:value={settings.retention_days}
                  onchange={saveAppSettings}
                  class="settings-input number-input"
                />
                <small class="field-hint">0 = бессрочно (не удалять по возрасту)</small>
              </label>

              <label class="form-field">
                <span class="field-label">Макс. версий на один файл:</span>
                <input
                  type="number"
                  min="0"
                  bind:value={settings.max_versions_per_file}
                  onchange={saveAppSettings}
                  class="settings-input number-input"
                />
                <small class="field-hint">0 = без ограничений количества</small>
              </label>
            </div>

            <div class="prune-box">
              <div class="prune-info">
                <h4>Ручная очистка хранилища</h4>
                <p>Применяет правила очистки и удаляет неиспользуемые сжатые объекты с диска.</p>
              </div>
              <button class="btn-secondary" onclick={runStoragePrune} disabled={isPruning}>
                {isPruning ? "Очистка..." : "🧹 Очистить старые версии"}
              </button>
            </div>
          </section>

        {:else if settingsTab === 'ignores'}
          <section class="settings-section">
            <h3>Игнорируемые файлы и папки</h3>
            <p class="section-desc">Шаблоны путей и расширений, которые Undoit не будет сохранять в историю.</p>

            <div class="add-folder-row">
              <input
                type="text"
                placeholder="Шаблон, например: *.log или dist"
                bind:value={newIgnorePattern}
                class="settings-input"
              />
              <button class="btn-primary" onclick={addIgnorePattern}>Добавить правило</button>
            </div>

            <div class="tags-container">
              {#each settings.ignore_patterns as pattern}
                <span class="tag-pill">
                  {pattern}
                  <button class="tag-remove" onclick={() => removeIgnorePattern(pattern)} title="Удалить">✕</button>
                </span>
              {/each}
            </div>
          </section>

        {:else if settingsTab === 'system'}
          <section class="settings-section">
            <h3>Системные параметры</h3>

            <div class="toggle-row">
              <div class="toggle-info">
                <strong>Автозапуск при входе в Windows</strong>
                <p>Запускать Undoit автоматически в фоновом режиме (в трей) при включении компьютера.</p>
              </div>
              <input
                type="checkbox"
                bind:checked={settings.autostart}
                onchange={saveAppSettings}
                class="custom-toggle"
              />
            </div>

            <div class="toggle-row">
              <div class="toggle-info">
                <strong>Интеграция в контекстное меню Проводника Windows</strong>
                <p>Добавляет пункт «История версий Undoit» при нажатии правой кнопкой мыши на любой файл или папку в Проводнике.</p>
              </div>
              <input
                type="checkbox"
                bind:checked={explorerContextMenu}
                onchange={toggleExplorerContextMenu}
                class="custom-toggle"
              />
            </div>

            <div class="toggle-row">
              <div class="toggle-info">
                <strong>Тема оформления</strong>
                <p>Выберите цветовой стиль интерфейса.</p>
              </div>
              <select
                bind:value={settings.theme}
                onchange={saveAppSettings}
                class="settings-select"
              >
                <option value="dark">Тёмная (Dark Slate)</option>
                <option value="light">Светлая (Clean Light)</option>
              </select>
            </div>
          </section>
        {/if}

        {#if stats}
          <section class="settings-section stats-summary">
            <h3>Статистика хранилища</h3>
            <div class="stats-pills">
              <span>Снимков: <strong>{stats.total_versions}</strong></span>
              <span>Оригинал: <strong>{formatBytes(stats.total_original_bytes)}</strong></span>
              <span>Zstd: <strong>{formatBytes(stats.total_compressed_bytes)}</strong></span>
              <span class="pill-green">Экономия: <strong>{stats.saved_ratio.toFixed(1)}%</strong></span>
            </div>
          </section>
        {/if}
      </div>

      <div class="modal-footer">
        <button class="btn-primary" onclick={() => showSettings = false}>Закрыть</button>
      </div>
    </div>
  </div>
{/if}

<style>
  :global(:root) {
    --bg-main: #0b0f19;
    --bg-panel: #111827;
    --bg-subtle: #1f2937;
    --bg-hover: #283548;
    --border-color: #1f293d;
    --text-main: #f3f4f6;
    --text-muted: #9ca3af;
    --accent: #3b82f6;
    --accent-glow: rgba(59, 130, 246, 0.4);
    --diff-add-bg: rgba(34, 197, 94, 0.12);
    --diff-add-text: #4ade80;
    --diff-del-bg: rgba(239, 68, 68, 0.12);
    --diff-del-text: #f87171;
  }

  :global([data-theme="light"]) {
    --bg-main: #f8fafc;
    --bg-panel: #ffffff;
    --bg-subtle: #f1f5f9;
    --bg-hover: #e2e8f0;
    --border-color: #cbd5e1;
    --text-main: #0f172a;
    --text-muted: #64748b;
    --accent: #2563eb;
    --accent-glow: rgba(37, 99, 235, 0.3);
    --diff-add-bg: rgba(34, 197, 94, 0.15);
    --diff-add-text: #166534;
    --diff-del-bg: rgba(239, 68, 68, 0.15);
    --diff-del-text: #991b1b;
  }

  .app-layout {
    display: flex;
    width: 100vw;
    height: 100vh;
    background: var(--bg-main);
    color: var(--text-main);
    user-select: none;
  }

  /* TOAST */
  .toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #1f2937;
    color: #f3f4f6;
    border: 1px solid var(--accent);
    padding: 12px 20px;
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    z-index: 1000;
    font-size: 13px;
    font-weight: 500;
    animation: toast-in 0.2s ease-out;
  }

  @keyframes toast-in {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* SIDEBAR */
  .sidebar {
    width: 320px;
    min-width: 280px;
    background: var(--bg-panel);
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
  }

  .sidebar-header {
    padding: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border-color);
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .logo-shield {
    width: 28px;
    height: 28px;
    color: var(--accent);
    filter: drop-shadow(0 0 8px var(--accent-glow));
  }

  .logo-text {
    display: flex;
    align-items: baseline;
    gap: 6px;
  }

  .logo-title {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.5px;
  }

  .logo-badge {
    font-size: 11px;
    background: var(--bg-subtle);
    padding: 2px 6px;
    border-radius: 6px;
    color: var(--text-muted);
    font-weight: 600;
  }

  .status-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #22c55e;
  }

  .status-indicator.paused {
    color: #f59e0b;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 8px currentColor;
  }

  .search-container {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-color);
  }

  .search-input {
    width: 100%;
    padding: 8px 12px;
    background: var(--bg-main);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    color: var(--text-main);
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;
  }

  .search-input:focus {
    border-color: var(--accent);
  }

  .files-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  .empty-files {
    padding: 30px 16px;
    text-align: center;
    color: var(--text-muted);
    font-size: 13px;
  }

  .file-item {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border: none;
    background: transparent;
    border-radius: 8px;
    color: var(--text-main);
    cursor: pointer;
    text-align: left;
    transition: background 0.15s;
    margin-bottom: 4px;
  }

  .file-item:hover {
    background: var(--bg-hover);
  }

  .file-item.active {
    background: var(--bg-subtle);
    border: 1px solid var(--border-color);
  }

  .file-icon {
    color: var(--accent);
    display: flex;
    align-items: center;
  }

  .file-info {
    flex: 1;
    min-width: 0;
  }

  .file-name {
    display: block;
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .file-time {
    display: block;
    font-size: 11px;
    color: var(--text-muted);
  }

  .version-badge {
    background: var(--bg-main);
    font-size: 11px;
    padding: 2px 7px;
    border-radius: 10px;
    color: var(--text-muted);
    font-weight: 600;
  }

  .sidebar-footer {
    padding: 12px 16px;
    border-top: 1px solid var(--border-color);
    display: flex;
    gap: 8px;
  }

  .footer-btn {
    flex: 1;
    padding: 8px;
    background: var(--bg-subtle);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    color: var(--text-main);
    font-size: 12px;
    cursor: pointer;
    transition: background 0.2s;
  }

  .footer-btn:hover {
    background: var(--bg-hover);
  }

  /* MAIN CONTENT */
  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .empty-dashboard {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    text-align: center;
  }

  .hero-shield {
    width: 64px;
    height: 64px;
    color: var(--accent);
    margin-bottom: 20px;
    filter: drop-shadow(0 0 16px var(--accent-glow));
  }

  .empty-hero h2 {
    font-size: 22px;
    font-weight: 600;
    margin-bottom: 8px;
  }

  .empty-hero p {
    color: var(--text-muted);
    font-size: 14px;
    max-width: 540px;
    margin-bottom: 24px;
    line-height: 1.5;
  }

  .hero-actions {
    margin-bottom: 40px;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    width: 100%;
    max-width: 760px;
  }

  .stat-card {
    background: var(--bg-panel);
    border: 1px solid var(--border-color);
    padding: 20px;
    border-radius: 12px;
    text-align: center;
  }

  .stat-card.highlight .stat-value {
    color: #22c55e;
  }

  .stat-value {
    font-size: 26px;
    font-weight: 700;
    margin-bottom: 4px;
  }

  .stat-label {
    font-size: 12px;
    color: var(--text-muted);
  }

  /* WORKSPACE */
  .workspace {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .workspace-header {
    padding: 16px 24px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--bg-panel);
  }

  .file-title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 2px;
  }

  .file-path {
    font-size: 12px;
    color: var(--text-muted);
    max-width: 500px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .header-actions {
    display: flex;
    gap: 8px;
  }

  .btn-primary {
    background: var(--accent);
    color: #fff;
    border: none;
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 0 12px var(--accent-glow);
    transition: opacity 0.2s;
  }

  .btn-primary:hover:not(:disabled) {
    opacity: 0.9;
  }

  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: var(--bg-subtle);
    color: var(--text-main);
    border: 1px solid var(--border-color);
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
  }

  .btn-secondary:hover:not(:disabled) {
    background: var(--bg-hover);
  }

  .btn-ghost {
    background: transparent;
    color: var(--text-muted);
    border: 1px solid var(--border-color);
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 12px;
    cursor: pointer;
  }

  .btn-ghost:hover:not(:disabled) {
    color: var(--text-main);
    background: var(--bg-subtle);
  }

  .btn-ghost.danger:hover {
    color: #f87171;
    border-color: #ef4444;
  }

  /* TIMELINE */
  .timeline-bar {
    padding: 14px 24px;
    background: var(--bg-main);
    border-bottom: 1px solid var(--border-color);
  }

  .timeline-meta {
    display: flex;
    gap: 16px;
    font-size: 13px;
    margin-bottom: 10px;
    align-items: center;
  }

  .timeline-heading {
    font-weight: 600;
  }

  .timeline-date {
    color: var(--text-muted);
  }

  .timeline-size {
    margin-left: auto;
    font-size: 12px;
    color: var(--text-muted);
  }

  .zstd-tag {
    background: rgba(59, 130, 246, 0.15);
    color: var(--accent);
    padding: 2px 6px;
    border-radius: 4px;
    margin-left: 6px;
    font-weight: 500;
  }

  .scrubber-track {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .scrubber-slider {
    width: 100%;
    accent-color: var(--accent);
    cursor: pointer;
  }

  .scrubber-ticks {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--text-muted);
  }

  /* TAB CONTROLS */
  .tab-controls {
    padding: 8px 24px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--bg-panel);
  }

  .tabs-group {
    display: flex;
    gap: 4px;
  }

  .tab-btn {
    background: transparent;
    border: none;
    padding: 6px 12px;
    border-radius: 6px;
    color: var(--text-muted);
    font-size: 13px;
    cursor: pointer;
  }

  .tab-btn.active {
    background: var(--bg-subtle);
    color: var(--text-main);
    font-weight: 600;
  }

  .compare-switch {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
  }

  .compare-label {
    color: var(--text-muted);
  }

  .compare-btn {
    background: transparent;
    border: 1px solid var(--border-color);
    padding: 4px 10px;
    border-radius: 6px;
    color: var(--text-muted);
    font-size: 12px;
    cursor: pointer;
  }

  .compare-btn.active {
    background: var(--bg-subtle);
    border-color: var(--accent);
    color: var(--accent);
    font-weight: 600;
  }

  /* VIEWER */
  .viewer-container {
    flex: 1;
    overflow-y: auto;
    background: var(--bg-main);
    display: flex;
    flex-direction: column;
  }

  .diff-header-summary {
    padding: 8px 24px;
    font-size: 12px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    gap: 12px;
  }

  .add-badge {
    color: #22c55e;
    font-weight: 600;
  }

  .del-badge {
    color: #ef4444;
    font-weight: 600;
  }

  .diff-viewer {
    font-family: 'Consolas', 'Fira Code', monospace;
    font-size: 12px;
    line-height: 20px;
  }

  .diff-row {
    display: flex;
    width: 100%;
  }

  .diff-row.insert {
    background: var(--diff-add-bg);
    color: var(--diff-add-text);
  }

  .diff-row.delete {
    background: var(--diff-del-bg);
    color: var(--diff-del-text);
  }

  .line-num {
    width: 48px;
    padding: 0 8px;
    text-align: right;
    color: var(--text-muted);
    user-select: none;
    opacity: 0.6;
    border-right: 1px solid var(--border-color);
  }

  .line-sign {
    width: 24px;
    text-align: center;
    user-select: none;
    font-weight: bold;
  }

  .line-code {
    flex: 1;
    margin: 0;
    padding: 0 8px;
    white-space: pre-wrap;
    word-break: break-all;
    user-select: text;
  }

  .content-viewer {
    padding: 16px 24px;
  }

  .code-block {
    font-family: 'Consolas', 'Fira Code', monospace;
    font-size: 13px;
    line-height: 1.6;
    margin: 0;
    white-space: pre-wrap;
    user-select: text;
  }

  /* IMAGE & BINARY VISUALIZER */
  .diff-controls-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .image-mode-switch {
    display: flex;
    gap: 4px;
    background: var(--bg-subtle);
    padding: 2px;
    border-radius: 6px;
    border: 1px solid var(--border-color);
  }

  .zoom-controls {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .zoom-level {
    font-size: 12px;
    color: var(--text-muted);
    min-width: 42px;
    text-align: center;
    font-weight: 500;
  }

  .image-loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 300px;
    gap: 16px;
    color: var(--text-muted);
    font-size: 14px;
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border-color);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .image-notice-box {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin: 16px 24px;
    padding: 14px 18px;
    background: var(--bg-panel);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    font-size: 13px;
  }

  .image-notice-box p {
    margin: 4px 0 0 0;
    color: var(--text-muted);
    font-size: 12px;
  }

  .notice-icon {
    font-size: 18px;
  }

  .single-image-box {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    overflow: auto;
  }

  .preview-img {
    max-width: 90%;
    max-height: 70vh;
    object-fit: contain;
    border-radius: 8px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    border: 1px solid var(--border-color);
  }

  /* SPLIT SLIDER */
  .split-slider-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 20px;
    gap: 16px;
    overflow: hidden;
  }

  .split-slider-container {
    position: relative;
    max-width: 95%;
    max-height: 65vh;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6);
    border: 1px solid var(--border-color);
    background-color: #0d121f;
    background-image: 
      linear-gradient(45deg, #172033 25%, transparent 25%),
      linear-gradient(-45deg, #172033 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, #172033 75%),
      linear-gradient(-45deg, transparent 75%, #172033 75%);
    background-size: 20px 20px;
    background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
    display: flex;
    align-items: center;
    justify-content: center;
    user-select: none;
  }

  .split-img {
    display: block;
    max-width: 100%;
    max-height: 65vh;
    object-fit: contain;
  }

  .split-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
  }

  .split-overlay .split-img {
    width: 100%;
    height: 100%;
  }

  .split-divider {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 2px;
    background: #fff;
    box-shadow: 0 0 12px rgba(59, 130, 246, 0.8), 0 0 4px #fff;
    pointer-events: none;
    z-index: 10;
    transform: translateX(-50%);
  }

  .split-handle {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #1e293b;
    border: 2px solid #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 13px;
    font-weight: 700;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.6);
  }

  .split-tag {
    position: absolute;
    top: 12px;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.15);
    z-index: 12;
    pointer-events: none;
  }

  .split-tag.left {
    left: 12px;
    background: rgba(30, 41, 59, 0.85);
    color: #38bdf8;
  }

  .split-tag.right {
    right: 12px;
    background: rgba(30, 41, 59, 0.85);
    color: #a78bfa;
  }

  .split-input-range {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: ew-resize;
    z-index: 20;
    margin: 0;
  }

  .slider-presets-bar {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .slider-val-badge {
    font-size: 12px;
    font-weight: 700;
    color: var(--accent);
    min-width: 40px;
  }

  .preset-btn {
    background: var(--bg-panel);
    border: 1px solid var(--border-color);
    color: var(--text-muted);
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.15s;
  }

  .preset-btn:hover {
    color: var(--text-main);
    background: var(--bg-subtle);
  }

  .preset-btn.active {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
    font-weight: 600;
  }

  /* SIDE BY SIDE */
  .side-by-side-grid {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding: 20px;
    overflow: auto;
  }

  .side-card {
    background: var(--bg-panel);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .side-card-header {
    padding: 10px 16px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
    background: var(--bg-subtle);
  }

  .side-card-title {
    font-weight: 600;
  }

  .side-image-box {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    min-height: 280px;
    background-color: #0d121f;
    background-image: 
      linear-gradient(45deg, #172033 25%, transparent 25%),
      linear-gradient(-45deg, #172033 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, #172033 75%),
      linear-gradient(-45deg, transparent 75%, #172033 75%);
    background-size: 16px 16px;
    background-position: 0 0, 0 8px, 8px -8px, -8px 0px;
  }

  .side-img {
    max-width: 100%;
    max-height: 55vh;
    object-fit: contain;
    border-radius: 6px;
  }

  /* IMAGE SINGLE VIEW */
  .image-single-view {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .image-viewport {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    overflow: auto;
    background-color: #0d121f;
    background-image: 
      linear-gradient(45deg, #172033 25%, transparent 25%),
      linear-gradient(-45deg, #172033 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, #172033 75%),
      linear-gradient(-45deg, transparent 75%, #172033 75%);
    background-size: 20px 20px;
    background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
  }

  .zoomable-img {
    max-width: 90%;
    max-height: 70vh;
    object-fit: contain;
    border-radius: 8px;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6);
    border: 1px solid var(--border-color);
    transition: transform 0.15s ease-out;
    transform-origin: center center;
  }

  .image-info-bar {
    padding: 10px 24px;
    background: var(--bg-panel);
    border-top: 1px solid var(--border-color);
    display: flex;
    gap: 20px;
    font-size: 12px;
    color: var(--text-muted);
  }

  .image-info-bar strong {
    color: var(--text-main);
  }

  /* BINARY CARD */
  .binary-card {
    max-width: 540px;
    margin: 48px auto;
    background: var(--bg-panel);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 36px;
    text-align: center;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
  }

  .binary-icon {
    font-size: 48px;
    margin-bottom: 12px;
  }

  .binary-title {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .binary-desc {
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.5;
    margin-bottom: 24px;
  }

  .binary-meta-table {
    background: var(--bg-subtle);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 24px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    text-align: left;
    font-size: 12px;
  }

  .binary-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .meta-label {
    color: var(--text-muted);
  }

  .meta-val {
    font-weight: 600;
    color: var(--text-main);
  }

  .meta-hash {
    font-family: 'Consolas', monospace;
    font-size: 11px;
    color: var(--accent);
    max-width: 240px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .binary-actions {
    display: flex;
    justify-content: center;
    gap: 12px;
  }

  /* MODAL */
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 900;
  }

  .modal-card {
    background: var(--bg-panel);
    border: 1px solid var(--border-color);
    width: 650px;
    max-width: 90vw;
    max-height: 85vh;
    border-radius: 12px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .modal-header {
    padding: 16px 24px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .modal-header h2 {
    font-size: 18px;
    margin: 0;
  }

  .close-btn {
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 16px;
    cursor: pointer;
  }

  .modal-nav {
    display: flex;
    background: var(--bg-main);
    border-bottom: 1px solid var(--border-color);
    padding: 0 16px;
  }

  .modal-nav-btn {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 14px;
    color: var(--text-muted);
    font-size: 13px;
    cursor: pointer;
  }

  .modal-nav-btn.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
    font-weight: 600;
  }

  .modal-body {
    padding: 20px 24px;
    overflow-y: auto;
    flex: 1;
  }

  .settings-section {
    margin-bottom: 24px;
  }

  .settings-section h3 {
    font-size: 15px;
    margin-bottom: 4px;
  }

  .section-desc {
    font-size: 13px;
    color: var(--text-muted);
    margin-bottom: 16px;
    line-height: 1.4;
  }

  .add-folder-row {
    display: flex;
    gap: 8px;
    margin-bottom: 14px;
  }

  .settings-input {
    flex: 1;
    background: var(--bg-main);
    border: 1px solid var(--border-color);
    padding: 8px 12px;
    border-radius: 8px;
    color: var(--text-main);
    font-size: 13px;
    outline: none;
  }

  .settings-input:focus {
    border-color: var(--accent);
  }

  .number-input {
    max-width: 140px;
  }

  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 20px;
  }

  .form-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .field-label {
    font-size: 13px;
    font-weight: 500;
  }

  .field-hint {
    font-size: 11px;
    color: var(--text-muted);
  }

  .folders-list {
    background: var(--bg-main);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    max-height: 180px;
    overflow-y: auto;
  }

  .empty-hint {
    padding: 24px;
    text-align: center;
    color: var(--text-muted);
    font-size: 13px;
  }

  .folder-row {
    padding: 10px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border-color);
    font-size: 13px;
  }

  .folder-row:last-child {
    border-bottom: none;
  }

  .folder-path {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-right: 10px;
  }

  .remove-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 14px;
    opacity: 0.7;
    transition: opacity 0.2s;
  }

  .remove-btn:hover {
    opacity: 1;
  }

  .tags-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    background: var(--bg-main);
    padding: 12px;
    border-radius: 8px;
    border: 1px solid var(--border-color);
  }

  .tag-pill {
    background: var(--bg-subtle);
    border: 1px solid var(--border-color);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .tag-remove {
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 11px;
  }

  .toggle-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 0;
    border-bottom: 1px solid var(--border-color);
  }

  .toggle-info strong {
    font-size: 13px;
    display: block;
    margin-bottom: 2px;
  }

  .toggle-info p {
    font-size: 12px;
    color: var(--text-muted);
    margin: 0;
  }

  .custom-toggle {
    width: 20px;
    height: 20px;
    accent-color: var(--accent);
    cursor: pointer;
  }

  .settings-select {
    background: var(--bg-main);
    border: 1px solid var(--border-color);
    color: var(--text-main);
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 13px;
  }

  .prune-box {
    background: var(--bg-main);
    border: 1px solid var(--border-color);
    padding: 16px;
    border-radius: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .prune-info h4 {
    margin: 0 0 4px 0;
    font-size: 13px;
  }

  .prune-info p {
    margin: 0;
    font-size: 12px;
    color: var(--text-muted);
  }

  .stats-summary {
    background: var(--bg-main);
    border: 1px solid var(--border-color);
    padding: 14px 16px;
    border-radius: 8px;
  }

  .stats-pills {
    display: flex;
    gap: 16px;
    font-size: 12px;
    flex-wrap: wrap;
  }

  .pill-green {
    color: #22c55e;
  }

  .modal-footer {
    padding: 16px 24px;
    border-top: 1px solid var(--border-color);
    display: flex;
    justify-content: flex-end;
  }

  /* PDF & AI PAGE CONTROLS */
  .pdf-page-controls {
    display: flex;
    align-items: center;
    gap: 6px;
    background: var(--bg-subtle);
    border: 1px solid var(--border-color);
    padding: 2px 8px;
    border-radius: 6px;
  }

  /* DOCX INFO BANNER */
  .docx-info-banner {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-left: auto;
    font-size: 12px;
    color: var(--text-muted);
  }

  .docx-info-banner-content {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    background: var(--bg-subtle);
    border-bottom: 1px solid var(--border-color);
    font-size: 12px;
    color: var(--text-muted);
  }

  .docx-badge {
    background: #2563eb;
    color: #ffffff;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    letter-spacing: 0.5px;
  }
</style>
