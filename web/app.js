const romListEl = document.getElementById('rom-list');
const librarySummaryEl = document.getElementById('library-summary');
const systemsListEl = document.getElementById('systems-list');
const tagsListEl = document.getElementById('tags-list');

const detailTitle = document.getElementById('detail-title');
const detailSystem = document.getElementById('detail-system');
const detailSize = document.getElementById('detail-size');
const detailRegion = document.getElementById('detail-region');

let currentRoms = [];
let selectedIds = new Set();
let lastSelectedIndex = -1;
let currentSystemFilter = null; 
let currentTagFilters = new Set();
let currentAllTags = [];
let currentTagColors = {};
let currentShowFavorites = false;
let currentSearchQuery = "";

// Context Menu State
const contextMenu = document.getElementById('context-menu');
let currentContextFolder = null;
let currentContextDisplay = null;
let currentContextTag = null;

// Tag Modal State
const tagModal = document.getElementById('tag-modal');
const existingTagsList = document.getElementById('existing-tags-list');
const newTagInput = document.getElementById('new-tag-input');
const btnCancelTag = document.getElementById('btn-cancel-tag');
const btnSaveTag = document.getElementById('btn-save-tag');
let pendingTagIds = [];

// Settings Modal State
const settingsModal = document.getElementById('settings-modal');
const toggleShowFiles = document.getElementById('toggle-show-files');
const btnCloseSettings = document.getElementById('btn-close-settings');
const btnOpenSettingsSidebar = document.getElementById('btn-open-settings-sidebar');

document.addEventListener('click', () => {
  if (contextMenu) contextMenu.style.display = 'none';
});

window.addEventListener('focus', async () => {
  const changed = await window.pywebview.api.scan_folder();
  if (changed) {
    init();
  }
});

btnCancelTag.onclick = () => {
  tagModal.style.display = 'none';
};

btnSaveTag.onclick = async () => {
  const tag = newTagInput.value.trim();
  if (tag !== "" && pendingTagIds.length > 0) {
    tagModal.style.display = 'none';
    await window.pywebview.api.add_tag(pendingTagIds, tag);
    init();
  }
};

function openTagModal(ids) {
  pendingTagIds = ids;
  newTagInput.value = '';
  existingTagsList.innerHTML = '';
  
  if (currentAllTags.length === 0) {
    existingTagsList.innerHTML = '<span style="color:#8E8E93; font-size:12px;">No tags yet.</span>';
  } else {
    currentAllTags.forEach(t => {
      const span = document.createElement('span');
      span.className = 'tag';
      span.style.background = currentTagColors[t] || '#48484A';
      span.innerText = t;
      span.onclick = () => {
        newTagInput.value = t;
      };
      existingTagsList.appendChild(span);
    });
  }
  
  tagModal.style.display = 'flex';
  newTagInput.focus();
}

async function init() {
  const summary = await window.pywebview.api.get_library_summary();
  if(librarySummaryEl) librarySummaryEl.innerText = summary;
  
  const systems = await window.pywebview.api.get_systems();
  renderSystems(systems);
  
  currentAllTags = await window.pywebview.api.get_all_tags();
  currentTagColors = await window.pywebview.api.get_tag_colors();
  renderSidebarTags(currentAllTags);
  
  currentRoms = await window.pywebview.api.get_roms();
  renderRoms(currentRoms);
  updateDetailPanel();
}

function renderSidebarTags(tags) {
  if(!tagsListEl) return;
  tagsListEl.innerHTML = '';
  tags.forEach(tag => {
    const span = document.createElement('span');
    span.className = 'tag';
    
    const bgColor = currentTagColors[tag] || 'var(--tag-bg)';
    span.style.background = bgColor;
    
    if (currentTagFilters.has(tag)) {
      span.style.border = '1px solid #FFFFFF';
    } else {
      span.style.border = '1px solid transparent';
    }
    
    span.innerText = tag;
    span.onclick = () => {
      if (currentTagFilters.has(tag)) {
        currentTagFilters.delete(tag);
        span.style.border = '1px solid transparent';
      } else {
        currentTagFilters.add(tag);
        span.style.border = '1px solid #FFFFFF';
      }
      renderRoms(currentRoms);
    };
    
    // Right Click Context Menu for Tags
    span.oncontextmenu = (e) => {
      e.preventDefault();
      currentContextTag = tag;
      currentContextFolder = null;
      
      document.getElementById('cm-folder-options').style.display = 'none';
      document.getElementById('cm-tag-options').style.display = 'block';
      
      contextMenu.style.display = 'block';
      contextMenu.style.left = `${e.pageX}px`;
      contextMenu.style.top = `${e.pageY}px`;
      lucide.createIcons();
    };
    
    tagsListEl.appendChild(span);
  });
}

function renderSystems(systems) {
  if(!systemsListEl) return;
  systemsListEl.innerHTML = '';
  
  systems.forEach(sys => {
    const item = document.createElement('div');
    const isActive = currentSystemFilter === sys.folder_name && !currentShowFavorites;
    item.className = `sidebar-item ${isActive ? 'active' : ''}`;
    
    item.innerHTML = `
      <div style="display:flex;align-items:center;gap:6px;">
        <span>${sys.display_name}</span>
      </div>
      <span class="sidebar-count">${sys.rom_count}</span>
    `;
    
    item.onclick = () => {
      currentSystemFilter = sys.folder_name;
      currentShowFavorites = false;
      document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
      item.classList.add('active');
      selectedIds.clear();
      renderRoms(currentRoms);
      updateDetailPanel();
    };
    
    // Right Click Context Menu
    item.oncontextmenu = (e) => {
      e.preventDefault();
      currentContextFolder = sys.folder_name;
      currentContextDisplay = sys.display_name;
      currentContextTag = null;
      
      document.getElementById('cm-tag-options').style.display = 'none';
      document.getElementById('cm-folder-options').style.display = 'block';
      
      const deleteBtn = document.getElementById('cm-delete');
      if(sys.folder_name === 'Uncategorized') {
        deleteBtn.style.display = 'none';
      } else {
        deleteBtn.style.display = 'flex';
      }
      
      contextMenu.style.display = 'block';
      contextMenu.style.left = `${e.pageX}px`;
      contextMenu.style.top = `${e.pageY}px`;
      lucide.createIcons();
    };
    
    // Drag & Drop Handlers
    item.ondragover = (e) => {
      e.preventDefault();
      item.classList.add('drag-over');
    };
    
    item.ondragleave = (e) => {
      item.classList.remove('drag-over');
    };
    
    item.ondrop = async (e) => {
      e.preventDefault();
      item.classList.remove('drag-over');
      
      const data = e.dataTransfer.getData("text/plain");
      if (data) {
        const ids = JSON.parse(data);
        const targetSystem = sys.folder_name;
        const success = await window.pywebview.api.move_roms(ids, targetSystem);
        if (success) {
          selectedIds.clear();
          init();
        }
      }
    };
    
    systemsListEl.appendChild(item);
  });
  
  lucide.createIcons();
}

// Bind Context Menu Actions
document.getElementById('cm-open').onclick = async () => {
  contextMenu.style.display = 'none';
  if(currentContextFolder) {
    await window.pywebview.api.open_system_folder(currentContextFolder);
  }
};

document.getElementById('cm-rename').onclick = async () => {
  contextMenu.style.display = 'none';
  if(currentContextFolder) {
    const newName = prompt("Digite o novo nome para o sistema:", currentContextDisplay);
    if (newName && newName.trim() !== "") {
      await window.pywebview.api.rename_system(currentContextFolder, newName.trim());
      init();
    }
  }
};

document.getElementById('cm-delete').onclick = async () => {
  contextMenu.style.display = 'none';
  if(currentContextFolder) {
    if (confirm(`Deseja excluir a pasta ${currentContextFolder} e mover todas as ROMs de volta para a raiz?`)) {
      await window.pywebview.api.delete_system(currentContextFolder);
      if (currentSystemFilter === currentContextFolder) {
          currentSystemFilter = null;
      }
      selectedIds.clear();
      init();
    }
  }
};

document.getElementById('cm-tag-color').onclick = async () => {
  contextMenu.style.display = 'none';
  if(currentContextTag) {
    const colorInput = document.createElement('input');
    colorInput.type = 'color';
    colorInput.value = currentTagColors[currentContextTag] || '#48484A';
    colorInput.style.display = 'none';
    document.body.appendChild(colorInput);
    
    colorInput.onchange = async () => {
        await window.pywebview.api.set_tag_color(currentContextTag, colorInput.value);
        document.body.removeChild(colorInput);
        init();
    };
    colorInput.click();
  }
};

document.getElementById('cm-tag-delete').onclick = async () => {
  contextMenu.style.display = 'none';
  if(currentContextTag) {
    if(confirm(`Tem certeza que deseja excluir a tag '${currentContextTag}' de todos os jogos?`)) {
      await window.pywebview.api.delete_tag_globally(currentContextTag);
      currentTagFilters.delete(currentContextTag);
      selectedIds.clear();
      init();
    }
  }
};

const btnAddSystem = document.getElementById('btn-add-system');
if (btnAddSystem) {
  btnAddSystem.onclick = async () => {
    const name = prompt("Digite o nome da nova pasta (Sistema):");
    if (name && name.trim()) {
      await window.pywebview.api.create_system(name.trim());
      init();
    }
  };
}

const btnLibrary = document.getElementById('btn-library');
if (btnLibrary) {
  btnLibrary.onclick = () => {
    currentSystemFilter = null;
    currentShowFavorites = false;
    document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
    btnLibrary.classList.add('active');
    selectedIds.clear();
    renderRoms(currentRoms);
    updateDetailPanel();
  };
}

const btnFavorites = document.getElementById('btn-favorites');
if (btnFavorites) {
  btnFavorites.onclick = () => {
    currentSystemFilter = null;
    currentShowFavorites = true;
    document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
    btnFavorites.classList.add('active');
    selectedIds.clear();
    renderRoms(currentRoms);
    updateDetailPanel();
  };
}

const searchInput = document.getElementById('search-input');
if (searchInput) {
  searchInput.oninput = (e) => {
    currentSearchQuery = e.target.value.toLowerCase();
    renderRoms(currentRoms);
  };
}

const btnImport = document.getElementById('btn-import');
if (btnImport) {
  btnImport.onclick = async () => {
    const success = await window.pywebview.api.choose_folder();
    if (success) {
      init();
    }
  };
}

if (btnOpenSettingsSidebar) {
  btnOpenSettingsSidebar.onclick = async () => {
    const settings = await window.pywebview.api.get_settings();
    toggleShowFiles.checked = settings.show_all_files;
    settingsModal.style.display = 'flex';
  };
}

if (btnCloseSettings) {
  btnCloseSettings.onclick = () => {
    settingsModal.style.display = 'none';
  };
}

if (toggleShowFiles) {
  toggleShowFiles.onchange = async () => {
    await window.pywebview.api.toggle_show_all_files();
    init();
  };
}

function renderRoms(roms) {
  if(!romListEl) return;
  romListEl.innerHTML = '';
  
  let displayedRoms = roms;
  if (currentSystemFilter) {
      displayedRoms = displayedRoms.filter(r => r.folder_name === currentSystemFilter);
  }
  if (currentShowFavorites) {
      displayedRoms = displayedRoms.filter(r => r.is_favorite);
  }
  if (currentTagFilters.size > 0) {
      displayedRoms = displayedRoms.filter(r => {
        if (!r.tags) return false;
        return Array.from(currentTagFilters).every(filter => r.tags.includes(filter));
      });
  }
  if (currentSearchQuery !== "") {
      displayedRoms = displayedRoms.filter(r => r.name.toLowerCase().includes(currentSearchQuery) || r.filename.toLowerCase().includes(currentSearchQuery));
  }
  
  // Need an element to update count, wait index.html no longer has total-roms-count there. 
  // Wait, I removed the count from the top of the sidebar. Let's gracefully handle if it's missing.
  const countEl = document.getElementById('total-roms-count');
  if (countEl) countEl.innerText = displayedRoms.length;
  
  displayedRoms.forEach((rom, index) => {
    const row = document.createElement('div');
    row.className = 'rom-row';
    if (selectedIds.has(rom.id)) row.classList.add('selected');
    
    row.setAttribute('draggable', 'true');
    row.ondragstart = (e) => {
      if (!selectedIds.has(rom.id)) {
        selectedIds.clear();
        selectedIds.add(rom.id);
        renderRoms(currentRoms);
        updateDetailPanel();
      }
      e.dataTransfer.setData("text/plain", JSON.stringify(Array.from(selectedIds)));
    };
    
    let ext = rom.filename.split('.').pop().toUpperCase();
    let badgeClass = `badge-${ext}`;
    
    const heartHTML = rom.is_favorite 
      ? `<i data-lucide="heart" style="width:14px;height:14px;color:#FF453A;fill:#FF453A;margin-right:6px;"></i>` 
      : '';
      
    let tagsHTML = '';
    if (rom.tags && rom.tags.length > 0) {
      tagsHTML = '<div style="display:flex; gap:4px; margin-left:12px;">' + 
                 rom.tags.map(t => {
                   const c = currentTagColors[t] || '#2C2C2E';
                   return `<span style="background:${c}; color:#EBEBF5; font-size:10px; padding:2px 6px; border-radius:12px; border:1px solid rgba(255,255,255,0.1);">${t}</span>`;
                 }).join('') +
                 '</div>';
    }
      
    row.innerHTML = `
      <div class="system-badge ${badgeClass}">${ext}</div>
      <div style="flex:1; display:flex; align-items:center;">
        ${heartHTML}
        <span class="rom-name">${rom.name}</span>
        ${rom.region !== 'Unknown' ? `<span class="rom-region">${rom.region}</span>` : ''}
        ${tagsHTML}
      </div>
    `;
    
    row.onclick = (e) => {
      if (e.shiftKey && lastSelectedIndex !== -1) {
        const start = Math.min(lastSelectedIndex, index);
        const end = Math.max(lastSelectedIndex, index);
        selectedIds.clear();
        for(let i = start; i <= end; i++) {
          selectedIds.add(displayedRoms[i].id);
        }
      } else if (e.ctrlKey || e.metaKey) {
        if (selectedIds.has(rom.id)) {
          selectedIds.delete(rom.id);
        } else {
          selectedIds.add(rom.id);
        }
        lastSelectedIndex = index;
      } else {
        selectedIds.clear();
        selectedIds.add(rom.id);
        lastSelectedIndex = index;
      }
      renderRoms(currentRoms);
      updateDetailPanel();
    };
    
    romListEl.appendChild(row);
  });
  
  lucide.createIcons();
}

function updateDetailPanel() {
  const heartIcon = document.querySelector('.heart-icon');
  const actionsContainer = document.getElementById('detail-actions');
  const tagsContainer = document.getElementById('detail-tags-container');
  if(!actionsContainer) return;
  
  if (selectedIds.size === 0) {
    detailTitle.innerText = "Select a ROM";
    detailSystem.innerText = "-";
    detailSize.innerText = "-";
    detailRegion.innerText = "-";
    heartIcon.style.color = '#8E8E93';
    heartIcon.setAttribute('fill', 'none');
    heartIcon.onclick = null;
    actionsContainer.innerHTML = '';
    tagsContainer.innerHTML = '<button class="btn-add-tag" id="btn-add-tag"><i data-lucide="plus" style="width:14px;height:14px;"></i> Add tag</button>';
    lucide.createIcons();
    return;
  }
  
  if (selectedIds.size > 1) {
    detailTitle.innerText = `${selectedIds.size} ROMs Selected`;
    detailSystem.innerText = "Multiple Systems";
    detailSize.innerText = "-";
    detailRegion.innerText = "-";
    heartIcon.style.color = '#8E8E93';
    heartIcon.setAttribute('fill', 'none');
    heartIcon.onclick = null;
    
    const selectedRoms = currentRoms.filter(r => selectedIds.has(r.id));
    const hasZip = selectedRoms.some(r => {
      const ext = r.filename.split('.').pop().toLowerCase();
      return ext === 'zip' || ext === '7z';
    });
    
    let unzipBtnHTML = hasZip ? `<button class="action-btn" id="btn-batch-unzip" style="background:#0A84FF; color:#fff; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:600;"><i data-lucide="archive-restore" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"></i>Unzip All</button>` : '';
    
    actionsContainer.innerHTML = `
      <button class="action-btn" id="btn-batch-zip" style="background:#30D158; color:#fff; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:600;"><i data-lucide="file-archive" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"></i>Zip All</button>
      ${unzipBtnHTML}
      <button class="action-btn" id="btn-batch-delete" style="background:#FF453A; color:#fff; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:600;"><i data-lucide="trash-2" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"></i>Delete All</button>
    `;
    
    tagsContainer.innerHTML = '<button class="btn-add-tag" id="btn-add-tag"><i data-lucide="plus" style="width:14px;height:14px;"></i> Add tag to all</button>';
    lucide.createIcons();
    
    document.getElementById('btn-add-tag').onclick = () => {
      openTagModal(Array.from(selectedIds));
    };
    
    document.getElementById('btn-batch-zip').onclick = async () => {
      await window.pywebview.api.zip_roms(Array.from(selectedIds));
      init();
    };
    
    if (hasZip) {
      document.getElementById('btn-batch-unzip').onclick = async () => {
        await window.pywebview.api.unzip_roms(Array.from(selectedIds));
        init();
      };
    }
    
    document.getElementById('btn-batch-delete').onclick = async () => {
      if(confirm(`Tem certeza que deseja excluir ${selectedIds.size} jogos fisicamente do disco?`)) {
        await window.pywebview.api.delete_roms(Array.from(selectedIds));
        selectedIds.clear();
        init();
      }
    };
    
    return;
  }
  
  const singleId = Array.from(selectedIds)[0];
  const rom = currentRoms.find(r => r.id === singleId);
  if (!rom) return;
  
  detailTitle.innerText = rom.name;
  detailSystem.innerText = rom.system;
  detailSize.innerText = rom.size;
  detailRegion.innerText = rom.region;
  
  heartIcon.style.color = rom.is_favorite ? '#FF453A' : '#8E8E93';
  heartIcon.setAttribute('fill', rom.is_favorite ? '#FF453A' : 'none');
  
  heartIcon.onclick = async () => {
    await window.pywebview.api.toggle_favorite(rom.id);
    init();
  };
  
  const ext = rom.filename.split('.').pop().toLowerCase();
  const isZip = ext === 'zip' || ext === '7z';
  
  let archiveBtnHTML = isZip 
    ? `<button class="action-btn" id="btn-unzip" style="background:#0A84FF; color:#fff; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:600;"><i data-lucide="archive-restore" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"></i>Unzip</button>`
    : `<button class="action-btn" id="btn-zip" style="background:#30D158; color:#fff; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:600;"><i data-lucide="file-archive" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"></i>Zip File</button>`;
  
  actionsContainer.innerHTML = `
    <button class="action-btn" id="btn-rename" style="background:#0A84FF; color:#fff; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:600;"><i data-lucide="pencil" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"></i>Rename</button>
    ${archiveBtnHTML}
    <button class="action-btn" id="btn-delete" style="background:#FF453A; color:#fff; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:600;"><i data-lucide="trash-2" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"></i>Delete</button>
  `;
  
  // Render Tags
  tagsContainer.innerHTML = '';
  if (rom.tags && rom.tags.length > 0) {
    rom.tags.forEach(t => {
      const tSpan = document.createElement('span');
      tSpan.className = 'tag';
      tSpan.style.background = currentTagColors[t] || '#2C2C2E';
      tSpan.innerHTML = `${t} <i data-lucide="x" style="width:12px;height:12px;margin-left:4px;cursor:pointer;" class="remove-tag" data-tag="${t}"></i>`;
      tagsContainer.appendChild(tSpan);
    });
  }
  const addTagBtn = document.createElement('button');
  addTagBtn.className = 'btn-add-tag';
  addTagBtn.id = 'btn-add-tag';
  addTagBtn.innerHTML = '<i data-lucide="plus" style="width:14px;height:14px;"></i> Add tag';
  tagsContainer.appendChild(addTagBtn);
  
  lucide.createIcons();
  
  document.querySelectorAll('.remove-tag').forEach(icon => {
    icon.onclick = async (e) => {
      const tag = e.target.getAttribute('data-tag');
      await window.pywebview.api.remove_tag(rom.id, tag);
      init();
    };
  });
  
  document.getElementById('btn-add-tag').onclick = () => {
    openTagModal([rom.id]);
  };
  
  document.getElementById('btn-rename').onclick = async () => {
    const baseName = rom.filename.replace(/\.[^/.]+$/, ""); 
    const newName = prompt("Digite o novo nome para o arquivo (sem extensão):", baseName);
    if (newName && newName.trim() !== "" && newName.trim() !== baseName) {
      await window.pywebview.api.rename_rom(rom.id, newName.trim());
      init();
    }
  };
  
  if (isZip) {
    document.getElementById('btn-unzip').onclick = async () => {
      await window.pywebview.api.unzip_roms([rom.id]);
      init();
    };
  } else {
    document.getElementById('btn-zip').onclick = async () => {
      await window.pywebview.api.zip_roms([rom.id]);
      init();
    };
  }
  
  document.getElementById('btn-delete').onclick = async () => {
    if(confirm(`Tem certeza que deseja excluir ${rom.filename} fisicamente do disco?`)) {
      await window.pywebview.api.delete_roms([rom.id]);
      selectedIds.clear();
      init();
    }
  };
}

// Start
window.addEventListener('pywebviewready', function() {
  init();
});
