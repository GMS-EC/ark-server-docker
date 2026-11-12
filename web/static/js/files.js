// ARK Server Manager File Manager Script (Dockraft v1.4.0 Replicated Feature Suite)
const Files = {
  currentPath: sessionStorage.getItem('ark_files_path') || '',
  activeEditingPath: '',
  activeRenamePath: '',
  initialized: false,
  uploadQueue: [],
  uploadProcessing: false,
  uploadMinimized: false,

  init() {
    if (this.initialized) return;
    this.initialized = true;

    const savedPath = sessionStorage.getItem('ark_files_path');
    if (savedPath !== null) {
      this.currentPath = savedPath;
    }

    // Global listener: close context menu on click outside
    window.addEventListener('click', (e) => {
      if (!e.target.closest('#file-context-menu')) {
        this.hideContextMenu();
      }
    });

    // Close context menu and modals on Escape
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.hideContextMenu();
        this.closeRenameModal();
        this.closeCreateFileModal();
      }
      // Ctrl+S / Cmd+S inside editor
      if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
        const modal = document.getElementById('file-editor-modal');
        if (modal && (modal.classList.contains('open') || modal.style.display === 'block' || modal.style.display === 'flex')) {
          e.preventDefault();
          this.saveCurrentFile();
        }
      }
    });

    // Close context menu on page scroll
    window.addEventListener('scroll', () => {
      this.hideContextMenu();
    }, true);

    // Background right-click and drag & drop on the table / card
    const table = document.getElementById('file-manager-table');
    if (table) {
      table.addEventListener('contextmenu', (e) => {
        if (e.target.closest('.file-row')) return;
        this.showContextMenu(e, null);
      });
    }

    const dropCard = document.getElementById('files-dropzone-card') || table;
    const dropOverlay = document.getElementById('files-drop-overlay');
    const dropLabel = document.getElementById('files-drop-target-label');
    if (dropCard) {
      let dragDepth = 0;
      dropCard.addEventListener('dragenter', (e) => {
        if (!e.dataTransfer || !Array.from(e.dataTransfer.types || []).includes('Files')) return;
        e.preventDefault();
        dragDepth++;
        if (dropLabel) {
          dropLabel.textContent = `Destino: /ark-server${this.currentPath ? '/' + this.currentPath : ''}`;
        }
        if (dropOverlay) dropOverlay.style.display = 'flex';
      });
      dropCard.addEventListener('dragover', (e) => {
        e.preventDefault();
      });
      dropCard.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dragDepth = Math.max(0, dragDepth - 1);
        if (dragDepth === 0 && dropOverlay) {
          dropOverlay.style.display = 'none';
        }
      });
      dropCard.addEventListener('drop', (e) => {
        e.preventDefault();
        dragDepth = 0;
        if (dropOverlay) dropOverlay.style.display = 'none';
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          this.enqueueUploads(e.dataTransfer.files);
        }
      });
    }
  },

  notify(msg, type = 'info') {
    if (typeof App !== 'undefined' && App.showToast) {
      App.showToast(msg, type);
    } else if (typeof showToast === 'function') {
      showToast(msg, type);
    } else {
      console.log(`[${type}] ${msg}`);
    }
  },

  async confirmDialog(options) {
    if (typeof App !== 'undefined' && App.confirm) {
      return await App.confirm(options);
    }
    const message = typeof options === 'string' ? options : (options.message || '¿Confirmar?');
    return window.confirm(message);
  },

  async promptDialog(options) {
    if (typeof App !== 'undefined' && App.prompt) {
      return await App.prompt(options);
    }
    const message = typeof options === 'string' ? options : (options.message || 'Ingresa valor:');
    const defaultVal = typeof options === 'object' ? (options.defaultValue || '') : '';
    return window.prompt(message, defaultVal);
  },

  async loadDirectory(path = '', preserveScroll = false) {
    const isSameFolder = (path === this.currentPath);
    const scrollContainer = document.getElementById('files-scroll-container');
    const prevScrollTop = (preserveScroll || isSameFolder) && scrollContainer ? scrollContainer.scrollTop : 0;
    const prevWindowScroll = (preserveScroll || isSameFolder) ? window.scrollY : null;

    this.currentPath = path;
    try {
      sessionStorage.setItem('ark_files_path', path);
    } catch (_) {}

    const tbody = document.getElementById('files-table-body');
    if (!tbody) return;

    if (!preserveScroll && !isSameFolder) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px; color:var(--text-dim);">Cargando archivos...</td></tr>';
    }
    this.updateBreadcrumbs(path);
    this.hideContextMenu();

    try {
      const res = await fetch(`/api/files/list?path=${encodeURIComponent(path)}`);
      if (!res.ok) {
        let errMsg = "No se pudo cargar el directorio";
        try {
          const errJson = await res.json();
          if (errJson.detail) errMsg = errJson.detail;
        } catch (_) {}
        throw new Error(errMsg);
      }
      const data = await res.json();
      if (data.current_path !== undefined) {
        this.currentPath = data.current_path;
        try {
          sessionStorage.setItem('ark_files_path', this.currentPath);
        } catch (_) {}
        this.updateBreadcrumbs(this.currentPath);
      }
      this.renderFileList(data.items || []);

      // Re-aplicar filtro si hay texto en el buscador
      const filterInput = document.getElementById('files-filter-input');
      if (filterInput && filterInput.value.trim()) {
        this.filter(filterInput.value);
      }

      if (scrollContainer && prevScrollTop > 0) {
        scrollContainer.scrollTop = prevScrollTop;
      }
      if (prevWindowScroll !== null) {
        window.scrollTo({ top: prevWindowScroll, behavior: 'instant' });
      }
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:20px; color:var(--status-danger);">${this.escapeHtml(e.message)}</td></tr>`;
    }
  },

  updateBreadcrumbs(path) {
    const container = document.getElementById('file-breadcrumbs');
    if (!container) return;

    container.innerHTML = '';
    const rootCrumb = document.createElement('span');
    rootCrumb.className = 'crumb-item';
    rootCrumb.textContent = '/ark-server';
    rootCrumb.addEventListener('click', () => this.loadDirectory(''));
    container.appendChild(rootCrumb);

    if (!path) return;

    const parts = path.split('/').filter(p => p.length > 0);
    let accum = '';
    parts.forEach(p => {
      accum += (accum ? '/' : '') + p;
      const thisPath = accum;

      const sep = document.createElement('span');
      sep.className = 'crumb-sep';
      sep.textContent = ' / ';
      container.appendChild(sep);

      const item = document.createElement('span');
      item.className = 'crumb-item';
      item.textContent = p;
      item.addEventListener('click', () => this.loadDirectory(thisPath));
      container.appendChild(item);
    });
  },

  renderFileList(items) {
    const tbody = document.getElementById('files-table-body');
    if (!tbody) return;

    if (items.length === 0 && !this.currentPath) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:24px; color:var(--text-dim);">La carpeta está vacía. Haz clic derecho para crear archivos.</td></tr>';
      return;
    }

    tbody.innerHTML = '';

    // If inside a subfolder, add '..' parent directory row
    if (this.currentPath) {
      const parentRow = document.createElement('tr');
      parentRow.className = 'file-row parent-dir-row';
      parentRow.setAttribute('data-parent', 'true');
      parentRow.innerHTML = `
        <td colspan="4">
          <div class="file-name-cell">
            <span class="file-icon" style="display:inline-flex; align-items:center;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            </span>
            <span>.. (Subir un nivel)</span>
          </div>
        </td>
      `;
      parentRow.querySelector('.file-name-cell').addEventListener('click', () => {
        const parts = this.currentPath.split('/');
        parts.pop();
        this.loadDirectory(parts.join('/'));
      });
      parentRow.addEventListener('contextmenu', (e) => {
        this.showContextMenu(e, null);
      });
      tbody.appendChild(parentRow);
    }

    if (items.length === 0) {
      const emptyRow = document.createElement('tr');
      emptyRow.innerHTML = '<td colspan="4" style="text-align:center; padding:24px; color:var(--text-dim);">Esta carpeta está vacía.</td>';
      tbody.appendChild(emptyRow);
      return;
    }

    items.forEach(item => {
      const row = document.createElement('tr');
      row.className = 'file-row';
      row.setAttribute('data-name', (item.name || '').toLowerCase());

      const iconSvg = item.is_dir 
        ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`
        : this.getFileIcon(item.extension);
      const formattedSize = item.is_dir ? '-' : this.formatBytes(item.size);
      const formattedDate = new Date(item.modified * 1000).toLocaleString();
      const itemRelativePath = (this.currentPath ? this.currentPath + '/' : '') + item.name;

      row.innerHTML = `
        <td>
          <div class="file-name-cell">
            <span class="file-icon" style="display:inline-flex; align-items:center;">${iconSvg}</span>
            <span>${this.escapeHtml(item.name)}</span>
          </div>
        </td>
        <td style="color:var(--text-muted);">${formattedSize}</td>
        <td style="color:var(--text-dim); font-size:0.8rem;">${formattedDate}</td>
        <td>
          <div class="file-actions">
            ${!item.is_dir && this.isEditable(item.extension) ? 
              `<button class="action-icon-btn btn-edit" title="Editar archivo"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>` : ''}
            ${!item.is_dir && item.extension === 'zip' ? 
              `<button class="action-icon-btn btn-unzip" title="Extraer ZIP"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg></button>` : ''}
            ${!item.is_dir ? 
              `<button class="action-icon-btn btn-dl" title="Descargar"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg></button>` : ''}
            <button class="action-icon-btn danger btn-del" title="Eliminar"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button>
          </div>
        </td>
      `;

      const nameCell = row.querySelector('.file-name-cell');
      nameCell.addEventListener('click', () => {
        if (item.is_dir) {
          this.loadDirectory(itemRelativePath);
        } else if (this.isEditable(item.extension)) {
          this.openEditor(itemRelativePath);
        }
      });

      const editBtn = row.querySelector('.btn-edit');
      if (editBtn) editBtn.addEventListener('click', () => this.openEditor(itemRelativePath));

      const unzipBtn = row.querySelector('.btn-unzip');
      if (unzipBtn) unzipBtn.addEventListener('click', () => this.unzipFile(itemRelativePath));

      const dlBtn = row.querySelector('.btn-dl');
      if (dlBtn) dlBtn.addEventListener('click', () => this.downloadFile(itemRelativePath));

      const delBtn = row.querySelector('.btn-del');
      if (delBtn) delBtn.addEventListener('click', () => this.deleteItem(itemRelativePath, item.name));

      row.addEventListener('contextmenu', (e) => {
        this.showContextMenu(e, item, itemRelativePath, row);
      });

      tbody.appendChild(row);
    });
  },

  showContextMenu(e, item = null, itemRelativePath = '', targetRow = null) {
    e.preventDefault();
    e.stopPropagation();

    document.querySelectorAll('.file-row.context-selected').forEach(r => r.classList.remove('context-selected'));
    if (targetRow) {
      targetRow.classList.add('context-selected');
    }

    const menu = document.getElementById('file-context-menu');
    if (!menu) return;

    menu.innerHTML = '';
    const safePath = this.attrJsStr(itemRelativePath);
    const safeName = item ? this.attrJsStr(item.name) : '';

    if (!item) {
      menu.innerHTML = `
        <button type="button" class="context-menu-item" onclick="Files.openCreateFileModal()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
          <span>Nuevo Archivo</span>
        </button>
        <button type="button" class="context-menu-item" onclick="Files.createNewFolder()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/></svg>
          <span>Nueva Carpeta</span>
        </button>
        <button type="button" class="context-menu-item" onclick="document.getElementById('file-upload-input').click(); Files.hideContextMenu();">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          <span>Subir Archivos</span>
        </button>
        <div class="context-menu-divider"></div>
        <button type="button" class="context-menu-item" onclick="Files.loadDirectory(Files.currentPath, true)">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
          <span>Refrescar</span>
        </button>
      `;
    } else if (item.is_dir) {
      menu.innerHTML = `
        <button type="button" class="context-menu-item" onclick="Files.loadDirectory('${safePath}')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
          <span>Abrir Carpeta</span>
        </button>
        <button type="button" class="context-menu-item" onclick="Files.openRenameModal('${safePath}', '${safeName}')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          <span>Renombrar</span>
        </button>
        <button type="button" class="context-menu-item" onclick="Files.compressItem('${safePath}', '${safeName}')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#eab308" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
          <span>Comprimir a .ZIP</span>
        </button>
        <button type="button" class="context-menu-item" onclick="Files.duplicateItem('${safePath}', '${safeName}')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          <span>Duplicar</span>
        </button>
        <button type="button" class="context-menu-item" onclick="Files.copyPath('${safePath}')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          <span>Copiar ruta</span>
        </button>
        <div class="context-menu-divider"></div>
        <button type="button" class="context-menu-item danger" onclick="Files.deleteItem('${safePath}', '${safeName}')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          <span>Eliminar Carpeta</span>
        </button>
      `;
    } else {
      const canEdit = this.isEditable(item.extension);
      const isZip = item.extension === 'zip';

      let itemsHtml = '';
      if (canEdit) {
        itemsHtml += `
          <button type="button" class="context-menu-item" onclick="Files.openEditor('${safePath}')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            <span>Editar Archivo</span>
          </button>
        `;
      }
      if (isZip) {
        itemsHtml += `
          <button type="button" class="context-menu-item" onclick="Files.unzipFile('${safePath}')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#eab308" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
            <span>Extraer aquí</span>
          </button>
        `;
      }

      itemsHtml += `
        <button type="button" class="context-menu-item" onclick="Files.downloadFile('${safePath}')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          <span>Descargar</span>
        </button>
        <button type="button" class="context-menu-item" onclick="Files.openRenameModal('${safePath}', '${safeName}')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          <span>Renombrar</span>
        </button>
        <button type="button" class="context-menu-item" onclick="Files.compressItem('${safePath}', '${safeName}')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#eab308" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
          <span>Comprimir a .ZIP</span>
        </button>
        <button type="button" class="context-menu-item" onclick="Files.duplicateItem('${safePath}', '${safeName}')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          <span>Duplicar</span>
        </button>
        <button type="button" class="context-menu-item" onclick="Files.copyPath('${safePath}')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          <span>Copiar ruta</span>
        </button>
        <div class="context-menu-divider"></div>
        <button type="button" class="context-menu-item danger" onclick="Files.deleteItem('${safePath}', '${safeName}')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          <span>Eliminar</span>
        </button>
      `;
      menu.innerHTML = itemsHtml;
    }

    menu.style.display = 'flex';
    menu.classList.add('open');

    const rect = menu.getBoundingClientRect();
    let x = e.clientX;
    let y = e.clientY;

    if (x + rect.width > window.innerWidth) {
      x = window.innerWidth - rect.width - 12;
    }
    if (y + rect.height > window.innerHeight) {
      y = window.innerHeight - rect.height - 12;
    }

    menu.style.left = `${Math.max(10, x)}px`;
    menu.style.top = `${Math.max(10, y)}px`;
  },

  hideContextMenu() {
    const menu = document.getElementById('file-context-menu');
    if (menu) {
      menu.classList.remove('open');
      menu.style.display = 'none';
    }
    document.querySelectorAll('.file-row.context-selected').forEach(r => r.classList.remove('context-selected'));
  },

  downloadFile(filePath) {
    this.hideContextMenu();
    window.open(`/api/files/download?path=${encodeURIComponent(filePath)}`);
  },

  async copyPath(filePath) {
    this.hideContextMenu();
    const fullRel = `/ark-server/${filePath}`;
    try {
      await navigator.clipboard.writeText(fullRel);
      this.notify(`Ruta copiada: ${fullRel}`, 'success');
    } catch (e) {
      await this.promptDialog({
        title: 'Ruta del elemento',
        message: 'Copia la siguiente ruta:',
        defaultValue: fullRel,
        confirmText: 'Aceptar'
      });
    }
  },

  openRenameModal(filePath, currentName) {
    this.hideContextMenu();
    this.activeRenamePath = filePath;
    const modal = document.getElementById('modal-file-rename');
    const input = document.getElementById('input-file-rename');
    if (input) input.value = currentName;
    if (modal) modal.classList.add('open');
    if (input) setTimeout(() => {
      input.focus();
      const dotIdx = currentName.lastIndexOf('.');
      if (dotIdx > 0) {
        input.setSelectionRange(0, dotIdx);
      } else {
        input.select();
      }
    }, 60);
  },

  closeRenameModal() {
    const modal = document.getElementById('modal-file-rename');
    if (modal) modal.classList.remove('open');
    this.activeRenamePath = '';
  },

  async submitRename() {
    const input = document.getElementById('input-file-rename');
    const newName = input ? input.value.trim() : '';
    if (!newName || !this.activeRenamePath) return;

    try {
      const res = await fetch('/api/files/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: this.activeRenamePath, new_name: newName })
      });
      const data = await res.json();
      if (res.ok) {
        this.closeRenameModal();
        this.notify(`Renombrado a "${data.name}"`, 'success');
        this.loadDirectory(this.currentPath, true);
      } else {
        this.notify(data.detail || "Error al renombrar", 'danger');
      }
    } catch (e) {
      this.notify(e.message, 'danger');
    }
  },

  openCreateFileModal() {
    this.hideContextMenu();
    const modal = document.getElementById('modal-file-create');
    const input = document.getElementById('input-file-create-name');
    if (input) input.value = '';
    if (modal) modal.classList.add('open');
    if (input) setTimeout(() => input.focus(), 60);
  },

  closeCreateFileModal() {
    const modal = document.getElementById('modal-file-create');
    if (modal) modal.classList.remove('open');
  },

  async submitCreateFile() {
    const input = document.getElementById('input-file-create-name');
    const fileName = input ? input.value.trim() : '';
    if (!fileName) return;

    const newPath = (this.currentPath ? this.currentPath + '/' : '') + fileName;
    try {
      const res = await fetch('/api/files/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: newPath })
      });
      const data = await res.json();
      if (res.ok) {
        this.closeCreateFileModal();
        this.notify(`Archivo "${fileName}" creado`, 'success');
        await this.loadDirectory(this.currentPath, true);
        const ext = fileName.split('.').pop().toLowerCase();
        if (this.isEditable(ext)) {
          this.openEditor(newPath);
        }
      } else {
        this.notify(data.detail || "Error al crear archivo", 'danger');
      }
    } catch (e) {
      this.notify(e.message, 'danger');
    }
  },

  async duplicateItem(filePath, name) {
    this.hideContextMenu();
    this.notify(`Duplicando "${name}"...`, 'info');
    try {
      const res = await fetch('/api/files/duplicate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: filePath })
      });
      const data = await res.json();
      if (res.ok) {
        this.notify(`Copia creada: "${data.new_name}"`, 'success');
        this.loadDirectory(this.currentPath, true);
      } else {
        this.notify(data.detail || "Error al duplicar", 'danger');
      }
    } catch (e) {
      this.notify(e.message, 'danger');
    }
  },

  async compressItem(filePath, name) {
    this.hideContextMenu();
    this.notify(`Comprimiendo "${name}" a .zip...`, 'info');
    try {
      const res = await fetch('/api/files/compress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: filePath })
      });
      const data = await res.json();
      if (res.ok) {
        this.notify(`Archivo comprimido: "${data.archive_name}"`, 'success');
        this.loadDirectory(this.currentPath, true);
      } else {
        this.notify(data.detail || "Error al comprimir", 'danger');
      }
    } catch (e) {
      this.notify(e.message, 'danger');
    }
  },

  getFileIcon(ext) {
    switch ((ext || '').toLowerCase()) {
      case 'ini':
      case 'cfg':
      case 'conf':
      case 'properties':
      case 'json':
      case 'yml':
      case 'yaml':
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>`;
      case 'zip':
      case 'tar':
      case 'gz':
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#eab308" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>`;
      case 'txt':
      case 'log':
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
      case 'sh':
      case 'bat':
      case 'cmd':
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>`;
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'webp':
      case 'ico':
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`;
      case 'ark':
      case 'arkprofile':
      case 'arktribe':
      case 'bak':
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ec4899" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>`;
      default:
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
    }
  },

  isEditable(ext) {
    const BINARY_EXTENSIONS = new Set([
      'ark', 'arkprofile', 'arktribe', 'bak',
      'zip', 'gz', 'tar', 'rar', '7z', 'bz2', 'xz',
      'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'ico',
      'mp3', 'wav', 'ogg', 'mp4', 'mkv',
      'exe', 'dll', 'so', 'bin', 'elf',
      'db', 'sqlite', 'sqlite3',
      'pdf'
    ]);
    return !BINARY_EXTENSIONS.has((ext || '').toLowerCase());
  },

  formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  },

  async openEditor(filePath, fallbackPath = '') {
    this.hideContextMenu();
    this.activeEditingPath = filePath;
    const modal = document.getElementById('file-editor-modal');
    const title = document.getElementById('editor-file-title');
    const textarea = document.getElementById('editor-textarea');
    const saveBtn = document.getElementById('btn-editor-save');

    if (title) title.textContent = filePath;
    if (textarea) { textarea.value = 'Cargando archivo...'; textarea.disabled = false; }
    if (saveBtn) saveBtn.disabled = false;
    if (modal) modal.classList.add('open');

    try {
      let res = await fetch(`/api/files/content?path=${encodeURIComponent(filePath)}`);
      if (!res.ok && fallbackPath) {
        const fbRes = await fetch(`/api/files/content?path=${encodeURIComponent(fallbackPath)}`);
        if (fbRes.ok) {
          res = fbRes;
          this.activeEditingPath = fallbackPath;
          if (title) title.textContent = fallbackPath;
        }
      }
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Error al cargar archivo");
      if (textarea) {
        textarea.value = data.content;
        textarea.focus();
      }
    } catch (e) {
      if (textarea) {
        textarea.value = `No se puede abrir el archivo:\n${e.message}\n\nSi el archivo aún no existe o es binario, créalo o descárgalo para editarlo localmente.`;
        textarea.disabled = true;
      }
      if (saveBtn) saveBtn.disabled = true;
      this.notify(e.message, 'danger');
    }
  },

  async saveCurrentFile() {
    if (!this.activeEditingPath) return;
    const textarea = document.getElementById('editor-textarea');
    if (!textarea) return;
    const content = textarea.value;

    try {
      const res = await fetch('/api/files/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: this.activeEditingPath, content })
      });
      if (res.ok) {
        this.notify("Archivo guardado (Ctrl+S)", 'success');
      } else {
        const data = await res.json();
        this.notify(data.detail || "Error al guardar archivo", 'danger');
      }
    } catch (e) {
      this.notify(e.message, 'danger');
    }
  },

  closeEditor() {
    const modal = document.getElementById('file-editor-modal');
    if (modal) modal.classList.remove('open');
    this.activeEditingPath = '';
  },

  async deleteItem(filePath, name) {
    this.hideContextMenu();
    const ok = await this.confirmDialog({
      title: 'Eliminar Elemento',
      message: `¿Confirmas la eliminación permanente de "${name}"?`,
      confirmText: 'Eliminar',
      danger: true
    });
    if (!ok) return;

    try {
      const res = await fetch(`/api/files/delete?path=${encodeURIComponent(filePath)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        this.notify(`"${name}" eliminado`, 'success');
        this.loadDirectory(this.currentPath, true);
      } else {
        const err = await res.json().catch(() => ({}));
        this.notify(err.detail || "Error al eliminar", 'danger');
      }
    } catch (e) {
      this.notify(e.message, 'danger');
    }
  },

  async unzipFile(filePath) {
    this.hideContextMenu();
    try {
      this.notify("Extrayendo archivo zip...", 'info');
      const res = await fetch('/api/files/unzip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: filePath, target_dir: this.currentPath })
      });
      if (res.ok) {
        this.notify("Extracción completada", 'success');
        this.loadDirectory(this.currentPath, true);
      } else {
        const data = await res.json();
        this.notify(data.detail || "Error en la extracción", 'danger');
      }
    } catch (e) {
      this.notify(e.message, 'danger');
    }
  },

  async createNewFolder() {
    this.hideContextMenu();
    const folderName = await this.promptDialog({
      title: 'Nueva Carpeta',
      message: 'Ingresa el nombre de la nueva carpeta:',
      placeholder: 'ej: SavedArksBackup, Configs',
      confirmText: 'Crear Carpeta'
    });
    if (!folderName || !folderName.trim()) return;

    const newPath = (this.currentPath ? this.currentPath + '/' : '') + folderName.trim();
    try {
      const res = await fetch('/api/files/folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: newPath })
      });
      if (res.ok) {
        this.notify("Carpeta creada", 'success');
        this.loadDirectory(this.currentPath, true);
      } else {
        const err = await res.json();
        this.notify(err.detail || "Error al crear carpeta", 'danger');
      }
    } catch (e) {
      this.notify(e.message, 'danger');
    }
  },

  // --- Administrador de Subidas Flotante (Cola Múltiple + MB/s + Cancelación) ---
  enqueueUploads(fileList) {
    this.hideContextMenu();
    const files = Array.from(fileList || []);
    if (!files.length) return;

    files.forEach((f) => {
      const id = 'up_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7);
      this.uploadQueue.push({
        id,
        file: f,
        targetPath: this.currentPath,
        status: 'pending', // pending, uploading, done, error, canceled
        progress: 0,
        speedText: 'En cola...',
        xhr: null
      });
    });

    this.renderUploadManager();
    if (!this.uploadProcessing) {
      this.processUploadQueue();
    }
  },

  uploadFile(file) {
    if (file) this.enqueueUploads([file]);
  },

  uploadFiles(fileList) {
    if (fileList && fileList.length) this.enqueueUploads(fileList);
  },

  renderUploadManager() {
    const mgr = document.getElementById('upload-manager-widget') || document.getElementById('floating-upload-manager');
    const body = document.getElementById('upload-widget-body') || document.getElementById('upload-mgr-body');
    const title = document.getElementById('upload-widget-title') || document.getElementById('upload-mgr-title');
    if (!mgr || !body) return;

    if (this.uploadQueue.length === 0) {
      mgr.style.display = 'none';
      return;
    }

    mgr.style.display = 'block';
    body.style.display = this.uploadMinimized ? 'none' : 'flex';

    const doneCount = this.uploadQueue.filter(u => u.status === 'done').length;
    if (title) {
      title.textContent = `Subidas (${doneCount}/${this.uploadQueue.length})`;
    }

    body.innerHTML = this.uploadQueue.map(u => {
      const barColor = u.status === 'done' ? '#3fb950' : (u.status === 'error' || u.status === 'canceled' ? '#f85149' : '#58a6ff');
      const canCancel = u.status === 'pending' || u.status === 'uploading';
      return `
        <div style="background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 8px 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 4px;">
            <span style="font-size: 0.78rem; font-weight: 600; color: #e6edf3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(u.file.name)}</span>
            <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
              <span style="font-size: 0.72rem; color: #8b949e; font-family: var(--font-mono);">${this.escapeHtml(u.speedText)}</span>
              ${canCancel ? `<button type="button" class="action-icon-btn danger" style="padding: 2px;" onclick="Files.cancelUpload('${u.id}')" title="Cancelar"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>` : ''}
            </div>
          </div>
          <div style="height: 5px; width: 100%; background: #21262d; border-radius: 3px; overflow: hidden;">
            <div style="height: 100%; width: ${u.progress}%; background: ${barColor}; transition: width 0.15s ease;"></div>
          </div>
        </div>
      `;
    }).join('');
  },

  toggleUploadManagerMinimize() {
    this.uploadMinimized = !this.uploadMinimized;
    this.renderUploadManager();
  },

  toggleUploadWidgetBody() {
    this.toggleUploadManagerMinimize();
  },

  closeUploadManager() {
    this.uploadQueue = this.uploadQueue.filter(u => u.status === 'uploading' || u.status === 'pending');
    if (this.uploadQueue.length === 0) {
      const mgr = document.getElementById('upload-manager-widget') || document.getElementById('floating-upload-manager');
      if (mgr) mgr.style.display = 'none';
    } else {
      this.renderUploadManager();
    }
  },

  closeUploadWidget() {
    this.closeUploadManager();
  },

  cancelUpload(id) {
    const item = this.uploadQueue.find(u => u.id === id);
    if (!item) return;
    if (item.status === 'uploading' && item.xhr) {
      item.xhr.abort();
    }
    item.status = 'canceled';
    item.speedText = 'Cancelado';
    this.renderUploadManager();
  },

  async processUploadQueue() {
    this.uploadProcessing = true;
    while (true) {
      const next = this.uploadQueue.find(u => u.status === 'pending');
      if (!next) break;
      await this.runSingleUpload(next);
    }
    this.uploadProcessing = false;
    this.loadDirectory(this.currentPath, true);
  },

  runSingleUpload(item) {
    return new Promise((resolve) => {
      item.status = 'uploading';
      item.progress = 1;
      item.speedText = '0.0 MB/s';
      this.renderUploadManager();

      const formData = new FormData();
      formData.append('path', item.targetPath);
      formData.append('file', item.file);

      const xhr = new XMLHttpRequest();
      item.xhr = xhr;
      const startedAt = performance.now();

      xhr.upload.onprogress = (ev) => {
        if (ev.lengthComputable) {
          item.progress = Math.round((ev.loaded / ev.total) * 100);
          const elapsedSec = Math.max(0.1, (performance.now() - startedAt) / 1000);
          const mbPerSec = (ev.loaded / (1024 * 1024)) / elapsedSec;
          item.speedText = `${mbPerSec.toFixed(1)} MB/s (${item.progress}%)`;
          this.renderUploadManager();
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          item.status = 'done';
          item.progress = 100;
          item.speedText = 'Completado';
        } else {
          item.status = 'error';
          let detail = 'Error';
          try {
            const resp = JSON.parse(xhr.responseText);
            if (resp.detail) detail = resp.detail;
          } catch (_) {}
          item.speedText = detail;
          this.notify(`Error subiendo ${item.file.name}: ${detail}`, 'danger');
        }
        this.renderUploadManager();
        resolve();
      };

      xhr.onerror = () => {
        item.status = 'error';
        item.speedText = 'Error de red';
        this.renderUploadManager();
        resolve();
      };

      xhr.onabort = () => {
        item.status = 'canceled';
        item.speedText = 'Cancelado';
        this.renderUploadManager();
        resolve();
      };

      xhr.open('POST', '/api/files/upload', true);
      xhr.send(formData);
    });
  },

  filter(query) {
    const q = (query || "").toLowerCase().trim();
    const rows = document.querySelectorAll("#files-table-body .file-row");
    rows.forEach(row => {
      if (row.getAttribute("data-parent") === "true") {
        row.style.display = "";
        return;
      }
      const name = row.getAttribute("data-name") || "";
      if (!q || name.toLowerCase().includes(q)) {
        row.style.display = "";
      } else {
        row.style.display = "none";
      }
    });
  },

  openDirectConfig(filename) {
    if (filename === 'arkmanager.cfg') {
      if (typeof switchTab === 'function') {
        switchTab('settings');
      }
      this.notify("Los parámetros de arkmanager.cfg se gestionan de forma segura desde la pestaña Configuración.", 'info');
      return;
    }

    const primaryPaths = {
      'GameUserSettings.ini': 'ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini',
      'Game.ini': 'ShooterGame/Saved/Config/LinuxServer/Game.ini',
      'ShooterGame.log': 'ShooterGame/Saved/Logs/ShooterGame.log'
    };
    const fallbackPaths = {
      'GameUserSettings.ini': 'ShooterGame/Saved/Config/CleanConfig/GameUserSettings.ini',
      'Game.ini': 'ShooterGame/Saved/Config/CleanConfig/Game.ini'
    };
    const target = primaryPaths[filename] || filename;
    const fallback = fallbackPaths[filename] || '';
    this.openEditor(target, fallback);
  },

  escapeHtml(str) {
    if (typeof window.escapeHtml === 'function') {
      return window.escapeHtml(str);
    }
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  },

  attrJsStr(str) {
    if (typeof window.attrJsStr === 'function') {
      return window.attrJsStr(str);
    }
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/\\/g, '\\\\')
      .replace(/'/g, "\\'")
      .replace(/\r/g, '\\r')
      .replace(/\n/g, '\\n');
  }
};
