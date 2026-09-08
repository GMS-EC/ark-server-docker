// ARK Server Manager Main Client Script
let ws = null;
let metricsChart = null;
let currentInstanceId = localStorage.getItem("ark_active_instance") || "main";
let clusterData = null;

// Inicialización
document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initWebSocket();
    initMetricsPolling();
    initChart();
    loadPlayers();
    loadBackups();
    loadSettings();
    loadTaskSettings();
    loadClusterInstances();
    loadClusterTributes();
    loadMods();
    loadActivityLogs();
    if (typeof Files !== "undefined" && Files.init) {
        Files.init();
    }
});

// --- Pestañas ---
function initTabs() {
    const navItems = document.querySelectorAll(".nav-btn, .nav-item");
    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const tabId = item.getAttribute("data-tab");
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    document.querySelectorAll(".nav-btn, .nav-item").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(el => el.classList.remove("active"));

    const navLink = document.querySelector(`.nav-btn[data-tab="${tabId}"], .nav-item[data-tab="${tabId}"]`);
    const targetPane = document.getElementById(`tab-${tabId}`);

    if (navLink) navLink.classList.add("active");
    if (targetPane) targetPane.classList.add("active");

    if (tabId === "metrics" && metricsChart) {
        metricsChart.resize();
    }

    if (tabId === "tasks") {
        loadTaskSettings();
    }

    if (tabId === "webhooks") {
        loadWebhookSettings();
    }

    if (tabId === "cluster") {
        loadClusterInstances();
        loadClusterTributes();
    }

    if (tabId === "mods") {
        loadMods();
    }

    if (tabId === "console") {
        loadActivityLogs();
    }

    if (tabId === "files") {
        if (typeof Files !== "undefined") {
            Files.loadDirectory(Files.currentPath || "");
        }
    } else {
        if (typeof Files !== "undefined" && Files.hideContextMenu) {
            Files.hideContextMenu();
        }
    }
}

// --- WebSocket de Consola ---
function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/console`;
    const consoleOutput = document.getElementById("console-output");

    ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        if (!consoleOutput) return;
        const line = document.createElement("div");
        line.textContent = event.data;
        consoleOutput.appendChild(line);

        // Optimización: Limitar el DOM a un máximo de 1.000 líneas visibles
        while (consoleOutput.children.length > 1000) {
            consoleOutput.removeChild(consoleOutput.firstChild);
        }

        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    };

    ws.onclose = () => {
        setTimeout(initWebSocket, 3000);
    };
}

function sendConsoleCommand() {
    const input = document.getElementById("console-input");
    if (!input || !input.value.trim()) return;
    const cmd = input.value.trim();
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(cmd);
    } else {
        fetch("/api/server/command", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ command: cmd })
        });
    }
    input.value = "";
}

// --- Controles de Servidor ---
async function startServer() {
    showToast("Iniciando servidor de ARK...", "info");
    const res = await fetch("/api/server/start", { method: "POST" });
    const data = await res.json();
    if (data.success) {
        showToast("Servidor de ARK arrancado.", "success");
    } else {
        showToast("No se pudo iniciar el servidor.", "error");
    }
}

async function stopServer() {
    const ok = await App.confirm({
        title: "Detener Servidor",
        message: "¿Deseas detener el servidor de ARK? Se guardará el estado del mundo (SaveWorld) antes de apagar.",
        confirmText: "Detener Servidor",
        danger: true
    });
    if (!ok) return;
    showToast("Deteniendo servidor...", "info");
    const res = await fetch("/api/server/stop", { method: "POST" });
    const data = await res.json();
    if (data.success) {
        showToast("Servidor detenido.", "success");
    }
}

async function restartServer() {
    const ok = await App.confirm({
        title: "Reiniciar Servidor",
        message: "¿Deseas reiniciar el servidor de ARK inmediatamente? Se guardará el progreso antes del reinicio.",
        confirmText: "Reiniciar Ahora",
        warning: true
    });
    if (!ok) return;
    showToast("Reiniciando servidor...", "info");
    await fetch("/api/server/restart", { method: "POST" });
}

// --- Acciones Rápidas de ARK ---
async function triggerDinoWipe() {
    const ok = await App.confirm({
        title: "Limpieza de Dinos (Dino Wipe)",
        message: "¿Ejecutar DestroyWildDinos? Todos los dinosaurios salvajes desaparecerán para regenerar nueva fauna.",
        confirmText: "Ejecutar Dino Wipe",
        warning: true
    });
    if (!ok) return;
    showToast("Ejecutando Dino Wipe...", "info");
    const res = await fetch("/api/server/dinowipe", { method: "POST" });
    const data = await res.json();
    if (data.success) {
        showToast("¡Dino Wipe completado con éxito!", "success");
    }
}

async function triggerSaveWorld() {
    showToast("Guardando estado del mundo...", "info");
    const res = await fetch("/api/server/saveworld", { method: "POST" });
    const data = await res.json();
    if (data.success) {
        showToast("Mundo guardado en disco.", "success");
    }
}

async function triggerBroadcast() {
    const msg = await App.prompt({
        title: "Anuncio Broadcast In-Game",
        message: "Escribe el mensaje flotante para enviar en vivo a todos los jugadores:",
        placeholder: "ej: Reinicio en 10 minutos por mantenimiento...",
        confirmText: "Enviar Anuncio"
    });
    if (!msg || !msg.trim()) return;
    const res = await fetch("/api/server/broadcast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    if (data.success) {
        showToast("Aviso enviado a los jugadores.", "success");
    }
}

// --- Métricas y Gráfico ---
function initChart() {
    const ctx = document.getElementById("metrics-chart");
    if (!ctx) return;

    metricsChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: [],
            datasets: [
                {
                    label: "CPU (%)",
                    borderColor: "#10b981",
                    backgroundColor: "rgba(16, 185, 129, 0.1)",
                    data: [],
                    tension: 0.3,
                    fill: true
                },
                {
                    label: "RAM Servidor (GB)",
                    borderColor: "#06b6d4",
                    backgroundColor: "rgba(6, 182, 212, 0.1)",
                    data: [],
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.05)" } },
                x: { grid: { display: false } }
            },
            plugins: {
                legend: { labels: { color: "#94a3b8" } }
            }
        }
    });
}

let metricsPollTimer = null;

async function fetchMetricsOnce() {
    try {
        const res = await fetch("/api/metrics");
        const data = await res.json();
        const curr = data.current;

        // Actualizar Tarjetas de Métricas
        if (document.getElementById("val-cpu")) document.getElementById("val-cpu").textContent = `${curr.cpu_percent}%`;
        if (document.getElementById("val-ram")) document.getElementById("val-ram").textContent = `${curr.ram_used_gb} / ${curr.ram_total_gb} GB`;
        if (document.getElementById("val-ark-ram")) document.getElementById("val-ark-ram").textContent = `${curr.ark_ram_gb} GB`;
        if (document.getElementById("val-disk")) document.getElementById("val-disk").textContent = `${curr.disk_used_gb} / ${curr.disk_total_gb} GB`;

        // Actualizar Tarjeta de Supervivientes en Métricas
        const metricPlayers = document.getElementById("val-players-metric");
        if (metricPlayers) {
            const pOnline = curr.players_online !== undefined ? curr.players_online : 0;
            const pMax = curr.max_players || 20;
            metricPlayers.textContent = `${pOnline} / ${pMax}`;
        }

        // Actualizar Banner Superior
        const topStatus = document.getElementById("top-server-status");
        if (topStatus) {
            topStatus.textContent = curr.status;
            topStatus.className = `overview-val status-text-inline ${curr.status.toLowerCase()}`;
        }
        const topUptime = document.getElementById("top-server-uptime");
        if (topUptime) topUptime.textContent = curr.uptime_formatted;
        const topCpu = document.getElementById("top-server-cpu");
        if (topCpu) topCpu.textContent = `${curr.cpu_percent} %`;
        const topArkMem = document.getElementById("top-server-ark-memory");
        if (topArkMem) topArkMem.textContent = `${curr.ark_ram_gb} GB`;
        const topDisk = document.getElementById("top-server-disk");
        if (topDisk) topDisk.textContent = `${curr.disk_used_gb} / ${curr.disk_total_gb} GB`;
        const topPlayers = document.getElementById("top-server-players");
        if (topPlayers) {
            const pOnline = curr.players_online !== undefined ? curr.players_online : 0;
            const pMax = curr.max_players || 20;
            topPlayers.textContent = `${pOnline} / ${pMax}`;
        }

        // Header Status Pill
        const statusPill = document.getElementById("status-pill");
        if (statusPill) statusPill.className = `status-pill ${curr.status.toLowerCase()}`;
        const statusText = document.getElementById("status-text");
        if (statusText) statusText.textContent = curr.status;

        // Stat Boxes de Consola
        const statCpuVal = document.getElementById("stat-cpu-val");
        if (statCpuVal) statCpuVal.textContent = `${curr.cpu_percent}%`;
        const statCpuBar = document.getElementById("stat-cpu-bar");
        if (statCpuBar) statCpuBar.style.width = `${curr.cpu_percent}%`;

        const statMemVal = document.getElementById("stat-mem-val");
        if (statMemVal) statMemVal.textContent = `${curr.ark_ram_gb} GB`;
        const statMemBar = document.getElementById("stat-mem-bar");
        if (statMemBar) statMemBar.style.width = `${curr.ram_percent}%`;

        const statDiskVal = document.getElementById("stat-disk-val");
        if (statDiskVal) statDiskVal.textContent = `${curr.disk_used_gb} / ${curr.disk_total_gb} GB`;
        const statDiskBar = document.getElementById("stat-disk-bar");
        if (statDiskBar) statDiskBar.style.width = `${curr.disk_percent}%`;

        // Actualizar Gráfico
        if (metricsChart && data.history) {
            metricsChart.data.labels = data.history.map(h => h.timestamp);
            metricsChart.data.datasets[0].data = data.history.map(h => h.cpu_percent);
            metricsChart.data.datasets[1].data = data.history.map(h => h.ark_ram_gb);
            metricsChart.update("none");
        }
    } catch (e) {}
}

function scheduleNextMetricsPoll() {
    clearTimeout(metricsPollTimer);
    // Page Visibility API: 2.5s activa, 10s en segundo plano o minimizada
    const delay = document.hidden ? 10000 : 2500;
    metricsPollTimer = setTimeout(async () => {
        await fetchMetricsOnce();
        scheduleNextMetricsPoll();
    }, delay);
}

function initMetricsPolling() {
    fetchMetricsOnce();
    scheduleNextMetricsPoll();

    // Reaccionar inmediatamente cuando la pestaña vuelve a ser visible
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) {
            fetchMetricsOnce();
            scheduleNextMetricsPoll();
        }
    });
}

// --- Jugadores ---
async function loadPlayers() {
    try {
        const res = await fetch("/api/players");
        const data = await res.json();
        const tbody = document.getElementById("players-table-body");
        if (!tbody) return;
        tbody.innerHTML = "";

        if (data.online.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-dim);">No hay supervivientes conectados actualmente.</td></tr>`;
            return;
        }

        data.online.forEach(p => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${p.name}</strong></td>
                <td><code style="color: var(--accent-cyan);">${p.steam_id}</code></td>
                <td><span class="status-pill online" style="padding: 2px 8px; font-size: 11px;">En línea</span></td>
                <td>
                    <button class="btn btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="kickPlayer('${p.steam_id}')">Expulsar</button>
                    <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="banPlayer('${p.steam_id}')">Banear</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {}
}

async function kickPlayer(steamId) {
    const ok = await App.confirm({
        title: "Expulsar Superviviente",
        message: `¿Expulsar del servidor al superviviente con SteamID ${steamId}?`,
        confirmText: "Expulsar",
        danger: true
    });
    if (!ok) return;
    await fetch("/api/players/kick", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ steam_id: steamId })
    });
    showToast("Superviviente expulsado.", "info");
    loadPlayers();
}

async function banPlayer(steamId) {
    const ok = await App.confirm({
        title: "Banear Superviviente",
        message: `¿Banear permanentemente al superviviente con SteamID ${steamId}?`,
        confirmText: "Banear",
        danger: true
    });
    if (!ok) return;
    await fetch("/api/players/ban", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ steam_id: steamId })
    });
    showToast("Superviviente baneado.", "error");
    loadPlayers();
}

// --- Backups ---
async function loadBackups() {
    try {
        const res = await fetch("/api/backups");
        const data = await res.json();
        const tbody = document.getElementById("backups-table-body");
        if (!tbody) return;
        tbody.innerHTML = "";

        if (data.backups.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color: var(--text-dim);">No existen copias de seguridad aún.</td></tr>`;
            return;
        }

        data.backups.forEach(b => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${b.filename}</strong></td>
                <td>${b.size_mb} MB</td>
                <td>${b.created_at}</td>
                <td>
                    <a href="/api/backups/download/${b.filename}" class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px; text-decoration: none;">Descargar</a>
                    <button class="btn btn-warning" style="padding: 4px 8px; font-size: 11px;" onclick="restoreBackup('${b.filename}')">Restaurar</button>
                    <button class="btn btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="deleteBackup('${b.filename}')">Eliminar</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {}
}

async function createBackupNow() {
    const name = await App.prompt({
        title: "Crear Copia de Seguridad",
        message: "Nombre descriptivo para identificar este respaldo (opcional):",
        placeholder: "ej: antes_del_boss",
        confirmText: "Crear Copia"
    });
    if (name === null) return;
    showToast("Comprimiendo mundo guardado...", "info");
    const res = await fetch("/api/backups/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name || null })
    });
    const data = await res.json();
    if (data.success) {
        showToast("Copia de seguridad generada con éxito.", "success");
        loadBackups();
    } else {
        showToast(`Error creando backup: ${data.error}`, "error");
    }
}

async function restoreBackup(filename) {
    const ok = await App.confirm({
        title: "Restaurar Copia de Seguridad",
        message: `¿Restaurar '${filename}'?\n\nLos datos actuales del mundo serán reemplazados (se creará una salvaguarda automática antes) y el servidor se reiniciará.`,
        confirmText: "Restaurar Respaldo",
        danger: true
    });
    if (!ok) return;
    showToast("Restaurando copia...", "info");
    const res = await fetch("/api/backups/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: filename })
    });
    const data = await res.json();
    if (data.success) {
        showToast("Mundo restaurado con éxito.", "success");
    } else {
        showToast(`Error al restaurar: ${data.error}`, "error");
    }
}

async function deleteBackup(filename) {
    const ok = await App.confirm({
        title: "Eliminar Copia de Seguridad",
        message: `¿Estás seguro de eliminar permanentemente la copia '${filename}'?`,
        confirmText: "Eliminar",
        danger: true
    });
    if (!ok) return;
    await fetch("/api/backups/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: filename })
    });
    showToast("Copia eliminada.", "info");
    loadBackups();
}

// --- Configuraciones ---
async function loadSettings() {
    try {
        const res = await fetch("/api/settings");
        const s = await res.json();
        
        // Servidor
        if (document.getElementById("cfg-session-name")) {
            document.getElementById("cfg-session-name").value = (s.server && s.server.session_name) || "";
            if (document.getElementById("cfg-world")) document.getElementById("cfg-world").value = (s.server && s.server.world) || "TheIsland";
            document.getElementById("cfg-server-pass").value = (s.server && s.server.server_password) || "";
            document.getElementById("cfg-admin-pass").value = (s.server && s.server.admin_password) || "";
            document.getElementById("cfg-max-players").value = (s.server && s.server.max_players) || "20";
            if (document.getElementById("cfg-cluster-id")) document.getElementById("cfg-cluster-id").value = (s.server && s.server.cluster_id) || "";
            if (document.getElementById("cfg-mods")) document.getElementById("cfg-mods").value = (s.server && s.server.mod_ids) || "";
            if (document.getElementById("cfg-additional-args")) document.getElementById("cfg-additional-args").value = (s.server && s.server.additional_args) || "";
            if (document.getElementById("cfg-battleeye")) document.getElementById("cfg-battleeye").value = String(!!(s.server && s.server.battleeye));
            if (document.getElementById("cfg-update-on-start")) document.getElementById("cfg-update-on-start").value = String(s.server && s.server.update_on_start !== false);
            if (document.getElementById("cfg-autostart-server")) document.getElementById("cfg-autostart-server").value = String(s.server && s.server.autostart_server !== false);
        }

        // Multiplicadores
        if (document.getElementById("cfg-xp")) {
            document.getElementById("cfg-xp").value = (s.multipliers && s.multipliers.xp) || "1.0";
            document.getElementById("cfg-taming").value = (s.multipliers && s.multipliers.taming) || "1.0";
            document.getElementById("cfg-harvest").value = (s.multipliers && s.multipliers.harvest) || "1.0";
            if (document.getElementById("cfg-mating")) document.getElementById("cfg-mating").value = (s.multipliers && s.multipliers.mating) || "1.0";
            document.getElementById("cfg-hatch").value = (s.multipliers && s.multipliers.hatch) || "1.0";
            document.getElementById("cfg-mature").value = (s.multipliers && s.multipliers.mature) || "1.0";
            if (document.getElementById("cfg-crafting")) document.getElementById("cfg-crafting").value = (s.multipliers && s.multipliers.crafting) || "1.0";
        }

        // Reglas
        if (document.getElementById("cfg-mode")) {
            document.getElementById("cfg-mode").value = (s.rules && s.rules.pve_mode) ? "pve" : "pvp";
        }
        if (document.getElementById("cfg-show-map-player")) {
            document.getElementById("cfg-show-map-player").value = String(s.rules && s.rules.show_map_player !== false);
        }
        if (document.getElementById("cfg-third-person")) {
            document.getElementById("cfg-third-person").value = String(s.rules && s.rules.third_person !== false);
        }
        if (document.getElementById("cfg-crosshair")) {
            document.getElementById("cfg-crosshair").value = String(s.rules && s.rules.crosshair !== false);
        }
        if (document.getElementById("cfg-pvp-gamma")) {
            document.getElementById("cfg-pvp-gamma").value = String(s.rules && s.rules.pvp_gamma !== false);
        }
    } catch (e) {
        console.error("Error al cargar configuraciones:", e);
    }
}

async function saveSettings(e) {
    if (e) e.preventDefault();
    const payload = {
        server: {
            session_name: document.getElementById("cfg-session-name")?.value || "",
            world: document.getElementById("cfg-world")?.value || "TheIsland",
            server_password: document.getElementById("cfg-server-pass")?.value || "",
            admin_password: document.getElementById("cfg-admin-pass")?.value || "",
            max_players: parseInt(document.getElementById("cfg-max-players")?.value) || 20,
            cluster_id: document.getElementById("cfg-cluster-id")?.value || "",
            mod_ids: document.getElementById("cfg-mods")?.value || "",
            additional_args: document.getElementById("cfg-additional-args")?.value || "",
            battleeye: document.getElementById("cfg-battleeye")?.value === "true",
            update_on_start: document.getElementById("cfg-update-on-start")?.value === "true",
            autostart_server: document.getElementById("cfg-autostart-server")?.value === "true"
        },
        multipliers: {
            xp: document.getElementById("cfg-xp")?.value || "1.0",
            taming: document.getElementById("cfg-taming")?.value || "1.0",
            harvest: document.getElementById("cfg-harvest")?.value || "1.0",
            mating: document.getElementById("cfg-mating")?.value || "1.0",
            hatch: document.getElementById("cfg-hatch")?.value || "1.0",
            mature: document.getElementById("cfg-mature")?.value || "1.0",
            crafting: document.getElementById("cfg-crafting")?.value || "1.0"
        },
        rules: {
            pve_mode: document.getElementById("cfg-mode")?.value === "pve",
            show_map_player: document.getElementById("cfg-show-map-player")?.value === "true",
            third_person: document.getElementById("cfg-third-person")?.value === "true",
            crosshair: document.getElementById("cfg-crosshair")?.value === "true",
            pvp_gamma: document.getElementById("cfg-pvp-gamma")?.value === "true"
        }
    };

    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast("Configuración guardada en GameUserSettings.ini y Game.ini", "success");
        } else {
            showToast("Error al guardar configuraciones.", "error");
        }
    } catch (err) {
        showToast("Error de conexión al guardar configuraciones.", "error");
    }
}

// --- Tareas Programadas y Automatizaciones ---
async function loadTaskSettings() {
    try {
        const res = await fetch("/api/tasks/config");
        const cfg = await res.json();

        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.value = val;
        };

        setVal("task-schedule-enabled", String(!!cfg.schedule_enabled));
        setVal("task-schedule-start", cfg.schedule_start || "20:00");
        setVal("task-schedule-stop", cfg.schedule_stop || "00:00");
        setVal("task-schedule-warn", cfg.schedule_warn_mins || 10);
        setVal("task-backup-enabled", String(cfg.auto_backup_enabled !== false));
        setVal("task-backup-hours", cfg.auto_backup_interval_hours || 6);
        setVal("task-backup-max-count", cfg.backup_max_count || 10);
        setVal("task-dino-wipe-enabled", String(!!cfg.auto_dino_wipe_enabled));
        setVal("task-restart-hours", cfg.auto_restart_hours || 0);
    } catch (e) {
        console.error("Error al cargar configuración de tareas:", e);
    }
}

async function saveTaskSettings() {
    const getVal = (id, fallback) => {
        const el = document.getElementById(id);
        return el ? el.value : fallback;
    };

    const payload = {
        schedule_enabled: getVal("task-schedule-enabled", "false") === "true",
        schedule_start: getVal("task-schedule-start", "20:00"),
        schedule_stop: getVal("task-schedule-stop", "00:00"),
        schedule_warn_mins: parseInt(getVal("task-schedule-warn", "10")) || 10,
        auto_backup_enabled: getVal("task-backup-enabled", "true") === "true",
        auto_backup_interval_hours: parseInt(getVal("task-backup-hours", "6")) || 6,
        backup_max_count: parseInt(getVal("task-backup-max-count", "10")) || 10,
        auto_dino_wipe_enabled: getVal("task-dino-wipe-enabled", "false") === "true",
        auto_restart_hours: parseInt(getVal("task-restart-hours", "0")) || 0
    };

    try {
        const res = await fetch("/api/tasks/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast("Horarios y automatizaciones guardados con éxito", "success");
        } else {
            showToast("Error al guardar tareas programadas.", "error");
        }
    } catch (e) {
        showToast("Error de conexión al guardar tareas.", "error");
    }
}

async function triggerRestartSafeModal() {
    const confirmed = await App.confirm({
        title: "Reinicio Seguro de Servidor",
        message: "¿Iniciar reinicio programado con cuenta regresiva de 5 minutos y avisos globales en el chat in-game?",
        confirmText: "Iniciar Reinicio",
        warning: true
    });
    if (!confirmed) return;

    try {
        showToast("Iniciando cuenta regresiva de reinicio (5 min)...", "info");
        const res = await fetch("/api/server/restart_safe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ minutes: 5 })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || "Reinicio seguro iniciado.", "success");
        } else {
            showToast("Error al iniciar reinicio seguro.", "error");
        }
    } catch (e) {
        showToast("Error de conexión al solicitar reinicio.", "error");
    }
}

// --- Sistema de Diálogos Modales y Notificaciones (Dockraft Style) ---
const App = {
  showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      container.style.cssText = 'position:fixed; bottom:20px; right:20px; z-index:9999; display:flex; flex-direction:column; gap:8px;';
      document.body.appendChild(container);
    }
    while (container.children.length >= 4) {
      container.removeChild(container.firstChild);
    }
    const typeStyles = {
      success: { bg: '#238636', border: '#2ea043' },
      danger:  { bg: '#da3633', border: '#f85149' },
      error:   { bg: '#da3633', border: '#f85149' },
      warning: { bg: '#9e6a03', border: '#d29922' },
      info:    { bg: '#1f6feb', border: '#388bfd' },
    };
    const style = typeStyles[type] || typeStyles.info;
    const toast = document.createElement('div');
    toast.style.cssText = `
      background: ${style.bg};
      border: 1px solid ${style.border};
      color: white;
      padding: 10px 16px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 500;
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
      animation: fadeIn 0.15s ease-out;
      max-width: 340px;
      word-break: break-word;
    `;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.25s ease';
      setTimeout(() => toast.remove(), 250);
    }, 3500);
  },

  ensureConfirmModal() {
    let modal = document.getElementById('modal-app-confirm');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.className = 'modal-backdrop modal-dialog-backdrop';
    modal.id = 'modal-app-confirm';
    modal.style.zIndex = '2200';
    modal.innerHTML = `
      <div class="modal-box modal-dialog-box" style="max-width: 480px;">
        <div class="modal-header" style="padding: 16px 20px; border-bottom: 1px solid #30363d;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div id="modal-confirm-icon" style="width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;"></div>
            <h3 id="modal-confirm-title-text" style="font-size: 1.05rem; font-weight: 600; color: #f0f6fc; margin: 0;">Confirmación</h3>
          </div>
          <button class="action-icon-btn" id="modal-confirm-btn-close" type="button" aria-label="Cerrar">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div class="modal-body" style="padding: 20px;">
          <div id="modal-confirm-message" style="font-size: 0.92rem; line-height: 1.6; color: #cbd5e1; white-space: pre-line; word-break: break-word;"></div>
        </div>
        <div class="modal-footer" style="padding: 14px 20px; border-top: 1px solid #30363d; display: flex; justify-content: flex-end; gap: 10px;">
          <button type="button" class="btn btn-outline" id="modal-confirm-btn-cancel">Cancelar</button>
          <button type="button" class="btn btn-danger" id="modal-confirm-btn-ok">Confirmar</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    return modal;
  },

  ensurePromptModal() {
    let modal = document.getElementById('modal-app-prompt');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.className = 'modal-backdrop modal-dialog-backdrop';
    modal.id = 'modal-app-prompt';
    modal.style.zIndex = '2200';
    modal.innerHTML = `
      <div class="modal-box modal-dialog-box" style="max-width: 480px;">
        <div class="modal-header" style="padding: 16px 20px; border-bottom: 1px solid #30363d;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div id="modal-prompt-icon" style="width: 36px; height: 36px; border-radius: 8px; background: rgba(56, 139, 253, 0.15); border: 1px solid rgba(56, 139, 253, 0.3); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#58a6ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </div>
            <h3 id="modal-prompt-title-text" style="font-size: 1.05rem; font-weight: 600; color: #f0f6fc; margin: 0;">Entrada Requerida</h3>
          </div>
          <button class="action-icon-btn" id="modal-prompt-btn-close" type="button" aria-label="Cerrar">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div class="modal-body" style="padding: 20px;">
          <div id="modal-prompt-message" style="font-size: 0.92rem; line-height: 1.5; color: #cbd5e1; margin-bottom: 14px; white-space: pre-line; word-break: break-word;"></div>
          <div class="form-group" style="margin-bottom: 0;">
            <input type="text" class="form-input" id="modal-prompt-input" autocomplete="off" spellcheck="false" style="font-size: 0.95rem; padding: 9px 12px;">
          </div>
        </div>
        <div class="modal-footer" style="padding: 14px 20px; border-top: 1px solid #30363d; display: flex; justify-content: flex-end; gap: 10px;">
          <button type="button" class="btn btn-outline" id="modal-prompt-btn-cancel">Cancelar</button>
          <button type="button" class="btn btn-primary" id="modal-prompt-btn-ok">Aceptar</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    return modal;
  },

  confirm(options) {
    return new Promise((resolve) => {
      const modal = this.ensureConfirmModal();
      const opts = typeof options === 'string' ? { message: options } : (options || {});
      const isDanger = Boolean(opts.danger || opts.type === 'danger');
      const isWarning = Boolean(opts.warning || opts.type === 'warning');

      const titleEl = document.getElementById('modal-confirm-title-text');
      const iconEl = document.getElementById('modal-confirm-icon');
      const msgEl = document.getElementById('modal-confirm-message');
      const btnOk = document.getElementById('modal-confirm-btn-ok');
      const btnCancel = document.getElementById('modal-confirm-btn-cancel');
      const btnClose = document.getElementById('modal-confirm-btn-close');

      if (titleEl) titleEl.textContent = opts.title || (isDanger ? 'Confirmación requerida' : 'Confirmar Acción');
      if (msgEl) msgEl.textContent = opts.message || '¿Estás seguro de continuar con esta acción?';

      if (btnOk) {
        btnOk.textContent = opts.confirmText || (isDanger ? 'Eliminar' : 'Confirmar');
        btnOk.className = isDanger ? 'btn btn-danger' : (isWarning ? 'btn btn-warning' : 'btn btn-primary');
      }
      if (btnCancel) {
        btnCancel.textContent = opts.cancelText || 'Cancelar';
      }

      if (iconEl) {
        if (isDanger) {
          iconEl.style.background = 'rgba(248, 81, 73, 0.15)';
          iconEl.style.border = '1px solid rgba(248, 81, 73, 0.3)';
          iconEl.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f85149" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
        } else if (isWarning) {
          iconEl.style.background = 'rgba(210, 153, 34, 0.15)';
          iconEl.style.border = '1px solid rgba(210, 153, 34, 0.3)';
          iconEl.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d29922" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
        } else {
          iconEl.style.background = 'rgba(56, 139, 253, 0.15)';
          iconEl.style.border = '1px solid rgba(56, 139, 253, 0.3)';
          iconEl.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#58a6ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';
        }
      }

      let resolved = false;
      const finish = (result) => {
        if (resolved) return;
        resolved = true;
        modal.classList.remove('open');
        window.removeEventListener('keydown', onKeyDown);
        resolve(result);
      };

      const onKeyDown = (e) => {
        if (e.key === 'Escape') {
          e.preventDefault();
          finish(false);
        } else if (e.key === 'Enter') {
          if (document.activeElement === btnCancel) {
            e.preventDefault();
            finish(false);
          } else {
            e.preventDefault();
            finish(true);
          }
        }
      };

      if (btnOk) btnOk.onclick = () => finish(true);
      if (btnCancel) btnCancel.onclick = () => finish(false);
      if (btnClose) btnClose.onclick = () => finish(false);
      modal.onclick = (e) => {
        if (e.target === modal) finish(false);
      };

      window.addEventListener('keydown', onKeyDown);
      modal.classList.add('open');

      if (isDanger && btnCancel) {
        btnCancel.focus();
      } else if (btnOk) {
        btnOk.focus();
      }
    });
  },

  prompt(options) {
    return new Promise((resolve) => {
      const modal = this.ensurePromptModal();
      const opts = typeof options === 'string' ? { message: options } : (options || {});
      const titleEl = document.getElementById('modal-prompt-title-text');
      const msgEl = document.getElementById('modal-prompt-message');
      const inputEl = document.getElementById('modal-prompt-input');
      const btnOk = document.getElementById('modal-prompt-btn-ok');
      const btnCancel = document.getElementById('modal-prompt-btn-cancel');
      const btnClose = document.getElementById('modal-prompt-btn-close');

      if (titleEl) titleEl.textContent = opts.title || 'Entrada Requerida';
      if (msgEl) msgEl.textContent = opts.message || '';
      if (inputEl) {
        inputEl.placeholder = opts.placeholder || '';
        inputEl.value = opts.defaultValue || '';
      }
      if (btnOk) btnOk.textContent = opts.confirmText || 'Aceptar';
      if (btnCancel) btnCancel.textContent = opts.cancelText || 'Cancelar';

      let resolved = false;
      const finish = (result) => {
        if (resolved) return;
        resolved = true;
        modal.classList.remove('open');
        window.removeEventListener('keydown', onKeyDown);
        resolve(result);
      };

      const onKeyDown = (e) => {
        if (e.key === 'Escape') {
          e.preventDefault();
          finish(null);
        } else if (e.key === 'Enter') {
          e.preventDefault();
          finish(inputEl ? inputEl.value : '');
        }
      };

      if (btnOk) btnOk.onclick = () => finish(inputEl ? inputEl.value : '');
      if (btnCancel) btnCancel.onclick = () => finish(null);
      if (btnClose) btnClose.onclick = () => finish(null);
      modal.onclick = (e) => {
        if (e.target === modal) finish(null);
      };

      window.addEventListener('keydown', onKeyDown);
      modal.classList.add('open');

      if (inputEl) {
        setTimeout(() => {
          inputEl.focus();
          inputEl.select();
        }, 50);
      }
    });
  }
};

window.App = App;
function showToast(message, type = "info") {
  App.showToast(message, type);
}

// --- Asistente de Configuración Inicial & Descarga ---
function selectMap(mapName, element) {
    const hiddenInput = document.getElementById("wizard-map");
    if (hiddenInput) hiddenInput.value = mapName;
    document.querySelectorAll(".map-card").forEach(c => c.classList.remove("selected"));
    if (element) element.classList.add("selected");
}

async function startServerInstallation(e) {
    if (e) e.preventDefault();
    const ok = await App.confirm({
        title: "Instalación del Servidor ARK",
        message: "¿Deseas guardar estas configuraciones e iniciar la descarga del servidor de ARK con SteamCMD?",
        confirmText: "Instalar Servidor"
    });
    if (!ok) return;

    const payload = {
        world: document.getElementById("wizard-map") ? document.getElementById("wizard-map").value : "TheIsland",
        session_name: document.getElementById("wizard-session-name") ? document.getElementById("wizard-session-name").value : "ARK Server",
        server_password: document.getElementById("wizard-server-pass") ? document.getElementById("wizard-server-pass").value : "",
        admin_password: document.getElementById("wizard-admin-pass") ? document.getElementById("wizard-admin-pass").value : "adminpass",
        max_players: document.getElementById("wizard-max-players") ? parseInt(document.getElementById("wizard-max-players").value) || 20 : 20,
        server_pve: document.getElementById("wizard-mode") ? document.getElementById("wizard-mode").value === "pve" : false,
        xp_multiplier: document.getElementById("wizard-xp") ? document.getElementById("wizard-xp").value : "1.0",
        taming_multiplier: document.getElementById("wizard-taming") ? document.getElementById("wizard-taming").value : "1.0",
        harvest_multiplier: document.getElementById("wizard-harvest") ? document.getElementById("wizard-harvest").value : "1.0",
        hatch_multiplier: document.getElementById("wizard-hatch") ? document.getElementById("wizard-hatch").value : "1.0",
        mature_multiplier: document.getElementById("wizard-mature") ? document.getElementById("wizard-mature").value : "1.0",
        mod_ids: document.getElementById("wizard-mods") ? document.getElementById("wizard-mods").value : ""
    };

    showToast("Iniciando descarga con SteamCMD...", "info");
    try {
        const res = await fetch("/api/server/install", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast("Descarga iniciada. Redirigiendo a la consola...", "success");
            switchTab("console");
        } else {
            showToast(data.error || "Error al iniciar la instalación.", "error");
        }
    } catch (err) {
        showToast("Error de conexión al iniciar instalación.", "error");
    }
}


// ==========================================
// --- Módulo de Clúster & Multi-Instancia ---
// ==========================================

async function loadClusterInstances() {
    try {
        const res = await fetch("/api/cluster/instances");
        clusterData = await res.json();
        const instances = clusterData.instances || [];

        // 1. Actualizar el selector en el Header (Condicional: badge si <= 1, selector si > 1)
        const singleBadge = document.getElementById("cluster-single-badge");
        const singleMapName = document.getElementById("cluster-single-map-name");
        const select = document.getElementById("cluster-server-select");

        if (instances.length <= 1) {
            if (singleBadge) {
                singleBadge.style.display = "inline-flex";
                if (singleMapName && instances[0]) {
                    singleMapName.textContent = instances[0].map || "The Island";
                }
            }
            if (select) select.style.display = "none";
        } else {
            if (singleBadge) singleBadge.style.display = "none";
            if (select) {
                select.style.display = "inline-block";
                select.innerHTML = "";
                instances.forEach(inst => {
                    const opt = document.createElement("option");
                    opt.value = inst.id;
                    const statusDot = inst.status === "RUNNING" ? "● " : "○ ";
                    let displayName = inst.name;
                    if (inst.is_primary && /servidor\s+prin/i.test(displayName)) {
                        displayName = displayName.replace(/Servidor\s+Prin[cd]ipal/i, "Principal").replace(/\(TheIsland\)/i, "(The Island)");
                        inst.name = displayName;
                    }
                    opt.textContent = `${statusDot}${displayName}`;
                    if (inst.id === currentInstanceId) opt.selected = true;
                    select.appendChild(opt);
                });
            }
        }

        // 2. Actualizar tarjetas de nodos en tab-cluster
        const grid = document.getElementById("cluster-instances-grid");
        if (grid) {
            grid.innerHTML = "";
            let onlineCount = 0;

            instances.forEach(inst => {
                const isOnline = inst.status === "RUNNING";
                if (isOnline) onlineCount++;
                const isSelected = inst.id === currentInstanceId;

                const card = document.createElement("div");
                card.className = "card";
                card.style.padding = "22px 24px";
                card.style.background = isSelected ? "rgba(56, 139, 253, 0.05)" : "var(--bg-subtle)";
                card.style.borderColor = isSelected ? "rgba(56, 139, 253, 0.4)" : "var(--border-color)";

                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; gap: 12px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px;">
                                <h4 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #f0f6fc;">${inst.name}</h4>
                                ${inst.is_primary ? '<span class="badge" style="font-size: 0.68rem; background: #238636; color: #fff; padding: 2px 7px; border-radius: 4px;">Principal</span>' : ''}
                                ${isSelected ? '<span class="badge" style="font-size: 0.68rem; background: #1f6feb; color: #fff; padding: 2px 7px; border-radius: 4px;">Activo en Panel</span>' : ''}
                            </div>
                            <div style="font-size: 0.8rem; color: #8b949e;">
                                Mapa oficial: <code style="color: #79c0ff; background: rgba(56, 139, 253, 0.1); padding: 2px 6px; border-radius: 4px;">${inst.map}</code>
                            </div>
                        </div>
                        <span class="status-pill ${isOnline ? 'running' : 'offline'}" style="font-size: 0.74rem; padding: 3px 10px; flex-shrink: 0;">
                            <span class="status-dot"></span>
                            <span>${isOnline ? 'En línea' : 'Detenido'}</span>
                        </span>
                    </div>

                    <div style="background: rgba(13, 17, 23, 0.8); border: 1px solid #30363d; border-radius: 8px; padding: 12px 16px; margin-bottom: 18px; font-size: 0.82rem; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                        <div><span style="color: #8b949e;">Puerto Juego:</span> <strong style="color: #f0f6fc;">${inst.server_port}/UDP</strong></div>
                        <div><span style="color: #8b949e;">Puerto Query:</span> <strong style="color: #f0f6fc;">${inst.query_port}/UDP</strong></div>
                        <div><span style="color: #8b949e;">Puerto RCON:</span> <strong style="color: #f0f6fc;">${inst.rcon_port}/TCP</strong></div>
                        <div><span style="color: #8b949e;">Límite Slots:</span> <strong style="color: #f0f6fc;">${inst.max_players} max</strong></div>
                    </div>

                    <div style="display: flex; gap: 10px; align-items: center; margin-top: 4px;">
                        ${isOnline ? `
                            <button class="btn btn-outline" onclick="stopClusterInstance('${inst.id}')" style="padding: 7px 14px; font-size: 0.82rem; color: #f85149; border-color: rgba(248, 81, 73, 0.4);">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
                                <span>Detener</span>
                            </button>
                            <button class="btn btn-secondary" onclick="restartClusterInstance('${inst.id}')" style="padding: 7px 14px; font-size: 0.82rem;">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                                <span>Reiniciar</span>
                            </button>
                        ` : `
                            <button class="btn btn-success" onclick="startClusterInstance('${inst.id}')" style="padding: 7px 16px; font-size: 0.82rem;">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                                <span>Iniciar</span>
                            </button>
                        `}
                        <button class="btn btn-primary" onclick="onSwitchClusterServer('${inst.id}')" style="padding: 7px 18px; font-size: 0.82rem;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>
                            <span>Administrar</span>
                        </button>
                        ${!inst.is_primary ? `
                            <button class="action-icon-btn" onclick="deleteClusterInstance('${inst.id}', '${inst.name}')" title="Eliminar del clúster" style="padding: 7px 10px; color: #f85149; border: 1px solid rgba(248, 81, 73, 0.3); border-radius: 6px; margin-left: auto;">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                            </button>
                        ` : ''}
                    </div>
                `;
                grid.appendChild(card);
            });

            // Resumen superior
            const summaryId = document.getElementById("cluster-summary-id");
            if (summaryId && clusterData.cluster_id) summaryId.textContent = clusterData.cluster_id;
            const summaryNodes = document.getElementById("cluster-summary-nodes");
            if (summaryNodes) summaryNodes.textContent = `${onlineCount} / ${instances.length} Online`;
        }

        // 3. Poblador de selector de mapas en el modal
        const mapSelect = document.getElementById("add-inst-map");
        if (mapSelect && clusterData.maps && mapSelect.children.length === 0) {
            clusterData.maps.forEach(m => {
                const opt = document.createElement("option");
                opt.value = m.id;
                opt.textContent = `${m.name} (${m.id})`;
                mapSelect.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Error cargando instancias del clúster:", e);
    }
}

async function loadClusterTributes() {
    try {
        const res = await fetch("/api/cluster/tributes");
        const data = await res.json();
        const tributes = data.tributes || [];

        const summaryTributes = document.getElementById("cluster-summary-tributes");
        if (summaryTributes) summaryTributes.textContent = `${tributes.length} elementos`;

        const tbody = document.getElementById("cluster-tributes-tbody");
        if (!tbody) return;
        tbody.innerHTML = "";

        if (tributes.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-dim); padding: 18px;">No hay supervivientes ni tributos en tránsito en la carpeta compartida /clusters.</td></tr>`;
            return;
        }

        tributes.forEach(t => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><code>${t.filename}</code></td>
                <td><span class="badge" style="font-size: 0.72rem;">${t.data_type}</span></td>
                <td>${t.steam_id ? `<code>${t.steam_id}</code>` : '<span style="color:var(--text-dim);">-</span>'}</td>
                <td>${t.size_kb} KB</td>
                <td>${t.updated_at}</td>
                <td style="text-align: right;">
                    <button class="btn btn-danger" style="padding: 3px 8px; font-size: 0.72rem;" onclick="deleteTribute('${t.filename}')" title="Eliminar si está corrupto o atascado">
                        Eliminar
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error cargando tributos de clúster:", e);
    }
}

function onSwitchClusterServer(instanceId) {
    currentInstanceId = instanceId;
    localStorage.setItem("ark_active_instance", instanceId);

    // Sincronizar el select del header
    const select = document.getElementById("cluster-server-select");
    if (select) select.value = instanceId;

    // Actualizar datos del mapa y puertos en banner superior
    if (clusterData && clusterData.instances) {
        const targetInst = clusterData.instances.find(i => i.id === instanceId);
        if (targetInst) {
            const topPort = document.getElementById("top-server-port");
            if (topPort && targetInst.game_port) topPort.textContent = `${targetInst.game_port} (UDP)`;
            const topRcon = document.getElementById("top-server-rcon");
            if (topRcon && targetInst.rcon_port) topRcon.textContent = `${targetInst.rcon_port} (Interno)`;
            const topMap = document.getElementById("top-server-map");
            if (topMap && targetInst.map) topMap.textContent = targetInst.map;
            const mobMap = document.getElementById("banner-mob-map");
            if (mobMap && targetInst.map) mobMap.textContent = targetInst.map;
            const singleMap = document.getElementById("cluster-single-map-name");
            if (singleMap && targetInst.map) singleMap.textContent = targetInst.map;
        }
    }

    showToast(`Cambiando contexto a nodo: ${instanceId}`, "info");

    // Recargar datos para el nuevo mapa activo
    loadSettings();
    loadPlayers();
    loadClusterInstances();
}

function openAddInstanceModal() {
    const modal = document.getElementById("modal-add-instance");
    if (!modal) return;

    const mapSelect = document.getElementById("add-inst-map");
    if (mapSelect && clusterData && clusterData.maps) {
        mapSelect.innerHTML = "";
        const existingMaps = (clusterData.instances || []).map(i => i.map);
        
        clusterData.maps.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m.id;
            const inUse = existingMaps.includes(m.id);
            opt.textContent = inUse ? `${m.name} (${m.id}) - [En uso]` : `${m.name} (${m.id})`;
            mapSelect.appendChild(opt);
        });

        // Seleccionar por defecto el primer mapa oficial no agregado
        const unadded = clusterData.maps.find(m => !existingMaps.includes(m.id));
        if (unadded) {
            mapSelect.value = unadded.id;
        } else if (clusterData.maps.length > 0) {
            mapSelect.value = clusterData.maps[0].id;
        }
    }

    if (mapSelect && mapSelect.value) {
        onMapSelectionChange(mapSelect.value);
    }

    modal.style.display = "flex";
}

function closeAddInstanceModal() {
    const modal = document.getElementById("modal-add-instance");
    if (modal) modal.style.display = "none";
}

function onMapSelectionChange(mapId) {
    const mapObj = clusterData && clusterData.maps ? clusterData.maps.find(m => m.id === mapId) : null;
    const nameInput = document.getElementById("add-inst-name");
    const portInput = document.getElementById("add-inst-port");
    const queryInput = document.getElementById("add-inst-query");
    const rconInput = document.getElementById("add-inst-rcon");
    const altSaveInput = document.getElementById("add-inst-altsave");

    if (mapObj) {
        if (nameInput) {
            nameInput.value = mapObj.name;
            nameInput.dataset.autofilled = "true";
        }
        if (portInput && mapObj.server_port) portInput.value = mapObj.server_port;
        if (queryInput && mapObj.query_port) queryInput.value = mapObj.query_port;
        if (rconInput && mapObj.rcon_port) rconInput.value = mapObj.rcon_port;
        if (altSaveInput) altSaveInput.value = mapObj.alt_save_dir || mapId.replace("_P", "");
    }
}

async function submitNewInstance() {
    const name = document.getElementById("add-inst-name").value.trim();
    const map = document.getElementById("add-inst-map").value;
    const server_port = parseInt(document.getElementById("add-inst-port").value);
    const query_port = parseInt(document.getElementById("add-inst-query").value);
    const rcon_port = parseInt(document.getElementById("add-inst-rcon").value);
    const max_players = parseInt(document.getElementById("add-inst-players").value) || 20;
    const alt_save_dir = document.getElementById("add-inst-altsave").value.trim() || map;

    if (!name) {
        showToast("Por favor ingresa un nombre para el servidor.", "error");
        return;
    }

    const payload = {
        name: name,
        map: map,
        server_port: server_port,
        query_port: query_port,
        rcon_port: rcon_port,
        max_players: max_players,
        alt_save_dir: alt_save_dir
    };

    try {
        const res = await fetch("/api/cluster/instances", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(`¡Mapa '${name}' añadido exitosamente al clúster!`, "success");
            closeAddInstanceModal();
            loadClusterInstances();
        } else {
            showToast(data.error || "Error al crear instancia en el clúster.", "error");
        }
    } catch (e) {
        showToast("Error de conexión al añadir mapa.", "error");
    }
}

async function startClusterInstance(instanceId) {
    showToast(`Iniciando mapa ${instanceId}...`, "info");
    const res = await fetch(`/api/cluster/instances/${instanceId}/start`, { method: "POST" });
    const data = await res.json();
    if (data.success) {
        showToast(`Servidor ${instanceId} iniciado.`, "success");
        loadClusterInstances();
    } else {
        showToast(`Error al iniciar ${instanceId}.`, "error");
    }
}

async function stopClusterInstance(instanceId) {
    const confirmed = await App.confirm({
        title: "Detener Servidor del Clúster",
        message: `¿Detener ${instanceId}? Se guardará el mundo antes de apagar.`,
        confirmText: "Detener Servidor",
        warning: true
    });
    if (!confirmed) return;

    showToast(`Deteniendo ${instanceId}...`, "info");
    const res = await fetch(`/api/cluster/instances/${instanceId}/stop`, { method: "POST" });
    const data = await res.json();
    if (data.success) {
        showToast(`Servidor ${instanceId} detenido.`, "success");
        loadClusterInstances();
    }
}

async function restartClusterInstance(instanceId) {
    const confirmed = await App.confirm({
        title: "Reiniciar Servidor del Clúster",
        message: `¿Reiniciar el mapa ${instanceId} ahora?`,
        confirmText: "Reiniciar",
        warning: true
    });
    if (!confirmed) return;

    showToast(`Reiniciando ${instanceId}...`, "info");
    await fetch(`/api/cluster/instances/${instanceId}/restart`, { method: "POST" });
    showToast(`Reinicio enviado a ${instanceId}.`, "success");
    loadClusterInstances();
}

async function deleteClusterInstance(instanceId, name) {
    const confirmed = await App.confirm({
        title: "Eliminar Mapa del Clúster",
        message: `¿Eliminar ${name || instanceId} del clúster? La configuración del nodo será removida.`,
        confirmText: "Eliminar Nodo",
        danger: true
    });
    if (!confirmed) return;

    const res = await fetch(`/api/cluster/instances/${instanceId}`, { method: "DELETE" });
    const data = await res.json();
    if (data.success) {
        showToast(`Mapa ${name || instanceId} eliminado del clúster.`, "info");
        if (currentInstanceId === instanceId) {
            onSwitchClusterServer("main");
        } else {
            loadClusterInstances();
        }
    } else {
        showToast(data.error || "No se pudo eliminar el mapa.", "error");
    }
}

async function startAllCluster() {
    const confirmed = await App.confirm({
        title: "Iniciar Todo el Clúster",
        message: "¿Deseas encender todos los mapas del clúster de forma escalonada?",
        confirmText: "Iniciar Clúster",
        warning: true
    });
    if (!confirmed) return;

    showToast("Iniciando todos los nodos del clúster...", "info");
    await fetch("/api/cluster/start_all", { method: "POST" });
    showToast("Comando de inicio global transmitido.", "success");
    setTimeout(loadClusterInstances, 2000);
}

async function stopAllCluster() {
    const confirmed = await App.confirm({
        title: "Detener Todo el Clúster",
        message: "¿Detener todos los servidores del clúster? Se guardará el progreso en todos los mapas.",
        confirmText: "Detener Todo",
        danger: true
    });
    if (!confirmed) return;

    showToast("Deteniendo todos los servidores...", "info");
    await fetch("/api/cluster/stop_all", { method: "POST" });
    showToast("Todos los mapas detenidos.", "info");
    setTimeout(loadClusterInstances, 2000);
}

async function syncClusterRatesModal() {
    try {
        // 1. Obtener las tasas reales actuales configuradas en el servidor principal
        let curRates = {};
        try {
            const settingsRes = await fetch("/api/server/settings");
            const settingsData = await settingsRes.json();
            curRates = settingsData.multipliers || {};
        } catch (_) {}

        const xp = curRates.xp || document.getElementById("cfg-xp")?.value || "2.0";
        const taming = curRates.taming || document.getElementById("cfg-taming")?.value || "3.0";
        const harvest = curRates.harvest || document.getElementById("cfg-harvest")?.value || "2.0";

        // 2. Pedir confirmación clara mostrando las tasas exactas a replicar
        const confirmed = await App.confirm({
            title: "Sincronizar Multiplicadores del Clúster",
            message: `¿Deseas replicar las tasas del servidor principal (XP: x${xp}, Tameo: x${taming}, Cosecha: x${harvest}) a TODOS los mapas vinculados del clúster?`,
            confirmText: "Sincronizar Todo",
            warning: true
        });
        if (!confirmed) return;

        showToast("Sincronizando tasas en todos los archivos de configuración...", "info");

        const ratesPayload = {
            xp: xp,
            taming: taming,
            harvest: harvest,
            mating: curRates.mating || document.getElementById("cfg-mating")?.value || "1.0",
            hatch: curRates.hatch || document.getElementById("cfg-hatch")?.value || "3.0",
            mature: curRates.mature || document.getElementById("cfg-mature")?.value || "3.0"
        };

        const res = await fetch("/api/cluster/sync_rates", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ rates: ratesPayload })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`¡Multiplicadores sincronizados exitosamente en ${data.synced_nodes} mapas del clúster!`, "success");
        } else {
            showToast(data.error || "Error al sincronizar multiplicadores.", "error");
        }
    } catch (e) {
        showToast("Error de conexión al sincronizar tasas.", "error");
    }
}

async function deleteTribute(filename) {
    const confirmed = await App.confirm({
        title: "Eliminar Archivo de Obelisco",
        message: `¿Eliminar ${filename} de la carpeta compartida del clúster? Usa esto solo si el dato está huérfano o corrupto.`,
        confirmText: "Eliminar Archivo",
        danger: true
    });
    if (!confirmed) return;

    const res = await fetch(`/api/cluster/tributes/${encodeURIComponent(filename)}`, { method: "DELETE" });
    const data = await res.json();
    if (data.success) {
        showToast("Archivo de obelisco eliminado.", "info");
        loadClusterTributes();
    } else {
        showToast("No se pudo eliminar el archivo.", "error");
    }
}



// --- GESTIÓN DE MODS DE STEAM WORKSHOP ---
let activeModsList = [];

async function loadMods() {
    try {
        const res = await fetch("/api/mods");
        const data = await res.json();
        activeModsList = data.mods || [];

        const countEl = document.getElementById("mods-count-val");
        if (countEl) countEl.textContent = activeModsList.length;

        const listContainer = document.getElementById("active-mods-list");
        if (!listContainer) return;

        if (activeModsList.length === 0) {
            listContainer.innerHTML = `
                <div style="text-align: center; padding: 24px; color: var(--text-dim); font-size: 0.85rem;">
                    No hay mods configurados en el servidor actualmente.<br>
                    Puedes añadir uno manualmente arriba o seleccionar uno del catálogo recomendado.
                </div>`;
            return;
        }

        listContainer.innerHTML = activeModsList.map((modId, index) => `
            <div class="mod-card" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--bg-subtle); border: 1px solid var(--border-color); border-radius: 6px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-dim); width: 20px;">#${index + 1}</span>
                    <div>
                        <div style="font-weight: 600; font-size: 0.9rem; color: #79c0ff; font-family: var(--font-mono);">
                            Mod ID: ${modId}
                        </div>
                        <a href="https://steamcommunity.com/sharedfiles/filedetails/?id=${modId}" target="_blank" rel="noopener noreferrer" style="font-size: 0.75rem; color: #58a6ff; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">
                            <span>Ver en Steam Workshop</span>
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                        </a>
                    </div>
                </div>
                <button type="button" class="btn btn-outline" onclick="removeMod('${modId}')" title="Quitar mod" style="padding: 4px 10px; font-size: 0.78rem; border-color: #f85149; color: #ff7b72;">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    <span>Quitar</span>
                </button>
            </div>
        `).join("");
    } catch (e) {
        console.error("Error cargando mods:", e);
    }
}

async function addModManual() {
    const input = document.getElementById("new-mod-id");
    if (!input) return;
    const modId = input.value.trim();
    if (!modId || !/^[0-9]+$/.test(modId)) {
        showToast("Por favor ingresa un Mod ID numérico válido de Steam.", "error");
        return;
    }
    if (activeModsList.includes(modId)) {
        showToast(`El mod ${modId} ya se encuentra en la lista.`, "warning");
        return;
    }
    activeModsList.push(modId);
    await saveModsList();
    input.value = "";
}

async function addPresetMod(modId, modName) {
    if (activeModsList.includes(modId)) {
        showToast(`El mod ${modName} ya está añadido.`, "warning");
        return;
    }
    activeModsList.push(modId);
    await saveModsList();
    showToast(`Mod "${modName}" añadido correctamente.`, "success");
}

async function removeMod(modId) {
    const ok = await App.confirm({
        title: "Quitar Mod",
        message: `¿Deseas quitar el Mod ID ${modId} de la lista activa del servidor?`,
        confirmText: "Quitar Mod",
        warning: true
    });
    if (!ok) return;
    activeModsList = activeModsList.filter(id => id !== modId);
    await saveModsList();
    showToast(`Mod ${modId} eliminado.`, "info");
}

async function saveModsList() {
    try {
        const raw_ids = activeModsList.join(",");
        const res = await fetch("/api/mods", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mod_ids: raw_ids })
        });
        const data = await res.json();
        if (data.success) {
            loadMods();
        } else {
            showToast("Error al guardar la lista de mods.", "error");
        }
    } catch (e) {
        showToast("Error de conexión al guardar mods.", "error");
    }
}

async function updateModsNow() {
    showToast("Iniciando actualización de mods en segundo plano...", "info");
    try {
        const res = await fetch("/api/mods/update", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("Comprobando actualizaciones de mods. Revisa la consola en vivo.", "success");
        } else {
            showToast("No se pudo iniciar la actualización de mods.", "error");
        }
    } catch (e) {
        showToast("Error de conexión al solicitar actualización.", "error");
    }
}

// --- COMANDOS RCON RÁPIDOS ---
async function sendQuickRcon(command) {
    showToast(`Ejecutando: ${command}...`, "info");
    try {
        const res = await fetch("/api/server/command", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ command })
        });
        const data = await res.json();
        const respText = data.response ? `[RCON] ${data.response}` : `[RCON] Comando '${command}' ejecutado.`;
        
        // Reflejar en la consola web
        const consoleOutput = document.getElementById("console-output");
        if (consoleOutput) {
            const line = document.createElement("div");
            line.style.color = "#58a6ff";
            line.textContent = respText;
            consoleOutput.appendChild(line);
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }
        showToast("Comando RCON ejecutado con éxito.", "success");
        loadActivityLogs();
    } catch (e) {
        showToast("Error al enviar comando RCON.", "error");
    }
}

// --- FILTRO DE CONSOLA EN VIVO ---
function filterConsoleLogs(term) {
    const consoleOutput = document.getElementById("console-output");
    if (!consoleOutput) return;
    const cleanTerm = (term || "").toLowerCase().trim();
    const lines = consoleOutput.children;
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (!cleanTerm) {
            line.style.display = "";
        } else {
            const matches = line.textContent.toLowerCase().includes(cleanTerm);
            line.style.display = matches ? "" : "none";
        }
    }
}

// --- HISTORIAL DE AUDITORÍA Y ACTIVIDAD ---
async function loadActivityLogs() {
    const tbody = document.getElementById("activity-log-body");
    if (!tbody) return;
    try {
        const res = await fetch("/api/activity");
        const data = await res.json();
        const activities = data.activities || [];

        if (activities.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 14px; color: var(--text-dim);">No hay registros de actividad recientes.</td></tr>`;
            return;
        }

        tbody.innerHTML = activities.slice(0, 30).map(act => `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                <td style="padding: 8px 14px; color: var(--text-dim); font-family: var(--font-mono); font-size: 0.78rem;">${act.timestamp}</td>
                <td style="padding: 8px 14px;">
                    <span class="badge" style="background: rgba(56, 139, 253, 0.15); color: #58a6ff; border: 1px solid rgba(56, 139, 253, 0.3); font-size: 0.72rem; padding: 2px 6px;">${act.category}</span>
                </td>
                <td style="padding: 8px 14px; font-weight: 600; color: #c9d1d9;">${act.user}</td>
                <td style="padding: 8px 14px; color: #8b949e;">${act.message}</td>
            </tr>
        `).join("");
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 14px; color: #ff7b72;">Error al cargar el historial de actividad.</td></tr>`;
    }
}

// --- Webhooks de Discord (Dockraft Style) ---
async function loadWebhookSettings() {
    try {
        const res = await fetch("/api/webhooks");
        const data = await res.json();
        
        const input = document.getElementById("webhook-url");
        if (input && data.url) input.value = data.url;

        const langSelect = document.getElementById("webhook-lang");
        if (langSelect && data.language) langSelect.value = data.language;

        const ev = data.events || {};
        const setCheck = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.checked = val !== false;
        };

        setCheck("wh-evt-start", ev.start);
        setCheck("wh-evt-starting", ev.starting);
        setCheck("wh-evt-shutdown", ev.shutdown);
        setCheck("wh-evt-shutdown-warn", ev.shutdown_warn);
        setCheck("wh-evt-backup", ev.backup);
        setCheck("wh-evt-dino-wipe", ev.dino_wipe);
        setCheck("wh-evt-restart", ev.restart);
        const elPlayers = document.getElementById("wh-evt-players");
        if (elPlayers) elPlayers.checked = !!ev.players;
    } catch (e) {
        console.error("Error al cargar webhook:", e);
    }
}

async function saveWebhookSettings() {
    const input = document.getElementById("webhook-url");
    const url = input ? input.value.trim() : "";
    const lang = document.getElementById("webhook-lang")?.value || "es";

    const getCheck = (id, fallback) => {
        const el = document.getElementById(id);
        return el ? el.checked : fallback;
    };

    const eventsPayload = {
        start: getCheck("wh-evt-start", true),
        starting: getCheck("wh-evt-starting", true),
        shutdown: getCheck("wh-evt-shutdown", true),
        shutdown_warn: getCheck("wh-evt-shutdown-warn", true),
        backup: getCheck("wh-evt-backup", true),
        dino_wipe: getCheck("wh-evt-dino-wipe", true),
        restart: getCheck("wh-evt-restart", true),
        players: getCheck("wh-evt-players", false)
    };

    try {
        const res = await fetch("/api/webhooks", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: url, language: lang, events: eventsPayload })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Configuración de Webhook guardada exitosamente.", "success");
        } else {
            showToast("Error al guardar webhook.", "error");
        }
    } catch (e) {
        showToast("Error de conexión al guardar webhook.", "error");
    }
}

async function testWebhookNotification() {
    const input = document.getElementById("webhook-url");
    const url = input ? input.value.trim() : "";
    if (!url) {
        showToast("Por favor ingresa primero la URL del Webhook.", "error");
        return;
    }
    showToast("Enviando notificación de prueba a Discord...", "info");
    try {
        const res = await fetch("/api/webhooks/test", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast("¡Notificación entregada con éxito a tu canal de Discord!", "success");
        } else {
            showToast(data.error || "No se pudo entregar la notificación a Discord.", "error");
        }
    } catch (e) {
        showToast("Error al probar notificación de Discord.", "error");
    }
}
