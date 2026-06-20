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
let currentSubpathFilter = "";
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

document.addEventListener('click', () => {
  if (contextMenu) contextMenu.style.display = 'none';
});

if (romListEl) {
  romListEl.oncontextmenu = (e) => {
    e.preventDefault();
    if (e.target.closest('.rom-row')) return;
    
    document.getElementById('cm-tag-options').style.display = 'none';
    document.getElementById('cm-collection-options').style.display = 'none';
    document.getElementById('cm-folder-options').style.display = 'none';
    document.getElementById('cm-rom-options').style.display = 'none';
    document.getElementById('cm-subfolder-options').style.display = 'none';
    
    if (currentSystemFilter && !currentShowFavorites) {
      document.getElementById('cm-list-options').style.display = 'block';
      contextMenu.style.display = 'block';
      contextMenu.style.left = `${e.pageX}px`;
      contextMenu.style.top = `${e.pageY}px`;
      lucide.createIcons();
    }
  };
}

window.isProcessing = false;

window.addEventListener('focus', async () => {
  if (window.isProcessing) return;
  window.isProcessing = true;
  const changed = await window.pywebview.api.scan_folder();
  if (changed) {
    init();
  }
  window.isProcessing = false;
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
  const colData = await window.pywebview.api.get_collections();
  renderCollections(colData);

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
      document.getElementById('cm-collection-options').style.display = 'none';
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
      currentSubpathFilter = "";
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
      document.getElementById('cm-collection-options').style.display = 'none';
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

document.getElementById('cm-new-subfolder').onclick = async () => {
  contextMenu.style.display = 'none';
  if(currentContextFolder) {
    const newName = prompt(`Nova subpasta dentro de '${currentContextDisplay}':`);
    if (newName && newName.trim() !== "") {
      await window.pywebview.api.create_subfolder(currentContextFolder, newName.trim());
      init();
    }
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

document.getElementById('cm-subfolder-rename').onclick = async () => {
  contextMenu.style.display = 'none';
  if (currentContextFolder && currentContextDisplay) {
    window.isProcessing = true;
    const newName = prompt(`Digite o novo nome para a pasta '${currentContextDisplay}':`, currentContextDisplay);
    if (newName && newName.trim() !== "" && newName.trim() !== currentContextDisplay) {
      await window.pywebview.api.rename_subfolder(currentContextFolder, currentContextDisplay, newName.trim());
      init();
    }
    window.isProcessing = false;
  }
};

document.getElementById('cm-subfolder-delete').onclick = async () => {
  contextMenu.style.display = 'none';
  if (currentContextFolder && currentContextDisplay) {
    window.isProcessing = true;
    if (confirm(`Deseja excluir a pasta '${currentContextDisplay}'?\n\nOs arquivos dentro dela não serão excluídos, mas sim movidos para a pasta acima.`)) {
      await window.pywebview.api.delete_subfolder(currentContextFolder, currentContextDisplay);
      init();
    }
    window.isProcessing = false;
  }
};

document.getElementById('cm-rom-favorite').onclick = async () => {
  contextMenu.style.display = 'none';
  if(selectedIds.size > 0) {
      for (const id of selectedIds) {
          await window.pywebview.api.toggle_favorite(id);
      }
      init();
  }
};

document.getElementById('cm-rom-rename').onclick = async () => {
  contextMenu.style.display = 'none';
  if(selectedIds.size === 1) {
      window.isProcessing = true;
      const id = Array.from(selectedIds)[0];
      const rom = currentRoms.find(r => r.id === id);
      if(rom) {
          const newName = prompt("Digite o novo nome do jogo:", rom.name);
          if(newName !== null && newName.trim() !== "") {
              await window.pywebview.api.rename_rom(id, newName.trim());
              init();
          }
      }
      window.isProcessing = false;
  }
};

document.getElementById('cm-rom-zip-unzip').onclick = async () => {
  contextMenu.style.display = 'none';
  if(selectedIds.size > 0) {
      window.isProcessing = true;
      const firstRom = currentRoms.find(r => r.id === Array.from(selectedIds)[0]);
      if (firstRom) {
          const ext = firstRom.filename.split('.').pop().toLowerCase();
          const isZip = ext === 'zip' || ext === '7z';
          if (isZip) {
              await window.pywebview.api.unzip_roms(Array.from(selectedIds));
          } else {
              await window.pywebview.api.zip_roms(Array.from(selectedIds));
          }
          init();
      }
      window.isProcessing = false;
  }
};

document.getElementById('cm-rom-delete').onclick = async () => {
  contextMenu.style.display = 'none';
  if(selectedIds.size > 0) {
      window.isProcessing = true;
      if(confirm(`Deseja realmente deletar do disco ${selectedIds.size} arquivo(s)?`)) {
          const ids = Array.from(selectedIds);
          await window.pywebview.api.delete_roms(ids);
          selectedIds.clear();
          init();
      }
      window.isProcessing = false;
  }
};

document.getElementById('cm-list-new-folder').onclick = async () => {
  contextMenu.style.display = 'none';
  if(currentSystemFilter) {
      window.isProcessing = true;
      const newName = prompt(`Nova subpasta dentro de '${currentSystemFilter}${currentSubpathFilter ? '/' + currentSubpathFilter : ''}':`);
      if (newName && newName.trim() !== "") {
        const basePath = currentSystemFilter + (currentSubpathFilter ? '/' + currentSubpathFilter : '');
        await window.pywebview.api.create_subfolder(basePath, newName.trim());
        init();
      }
      window.isProcessing = false;
  }
};

const btnAddSystem = document.getElementById('btn-add-system');
if (btnAddSystem) {
  btnAddSystem.onclick = async () => {
    window.isProcessing = true;
    const name = prompt("Digite o nome da nova pasta (Sistema):");
    if (name && name.trim()) {
      await window.pywebview.api.create_system(name.trim());
      init();
    }
    window.isProcessing = false;
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

const btnAddCollection = document.getElementById('btn-add-collection');
if (btnAddCollection) {
  btnAddCollection.onclick = async () => {
    const name = prompt("Name for new Collection:");
    if (name && name.trim()) {
      const success = await window.pywebview.api.add_collection(name.trim());
      if (success) init();
    }
  };
}

document.getElementById('cm-delete-collection').onclick = async () => {
  contextMenu.style.display = 'none';
  if (currentContextFolder) {
    if (confirm("Remove this collection? (Files on disk won't be deleted)")) {
      await window.pywebview.api.remove_collection(currentContextFolder);
      init();
    }
  }
};

function renderCollections(data) {
  const listEl = document.getElementById('collections-list');
  if(!listEl) return;
  listEl.innerHTML = '';
  
  data.collections.forEach(col => {
    const item = document.createElement('div');
    const isActive = data.active_collection_id === col.id;
    item.className = `sidebar-item ${isActive ? 'active' : ''}`;
    
    item.innerHTML = `<i data-lucide="database" style="width:16px;height:16px;margin-right:8px;color:${isActive ? '#30D158' : '#8E8E93'}"></i> <span>${col.name}</span>`;
    
    item.onclick = async () => {
      if (!isActive) {
        await window.pywebview.api.set_active_collection(col.id);
        init();
      }
    };
    
    item.oncontextmenu = (e) => {
      e.preventDefault();
      currentContextFolder = col.id;
      
      document.getElementById('cm-folder-options').style.display = 'none';
      document.getElementById('cm-tag-options').style.display = 'none';
      document.getElementById('cm-collection-options').style.display = 'block';
      
      contextMenu.style.display = 'block';
      contextMenu.style.left = `${e.pageX}px`;
      contextMenu.style.top = `${e.pageY}px`;
      lucide.createIcons();
    };
    
    listEl.appendChild(item);
  });
  
  lucide.createIcons();
}

const settingsModal = document.getElementById('settings-modal');
const btnCloseSettings = document.getElementById('btn-close-settings');
const toggleShowAll = document.getElementById('toggle-show-all');

const btnSettings = document.getElementById('btn-settings');
if (btnSettings) {
  btnSettings.onclick = async () => {
    const settings = await window.pywebview.api.get_settings();
    toggleShowAll.checked = settings.show_all_files;
    const userEl = document.getElementById('ra-username');
    const keyEl = document.getElementById('ra-api-key');
    if (userEl) userEl.value = settings.ra_username || '';
    if (keyEl) keyEl.value = settings.ra_api_key || '';
    settingsModal.style.display = 'flex';
    lucide.createIcons();
  };
}

const btnSaveRa = document.getElementById('btn-save-ra');
if (btnSaveRa) {
  btnSaveRa.onclick = async () => {
    const user = document.getElementById('ra-username').value;
    const key = document.getElementById('ra-api-key').value;
    await window.pywebview.api.set_ra_credentials(user, key);
    alert('RetroAchievements credentials saved!');
  };
}

if (btnCloseSettings) {
  btnCloseSettings.onclick = () => {
    settingsModal.style.display = 'none';
  };
}

if (toggleShowAll) {
  toggleShowAll.onchange = async () => {
    await window.pywebview.api.toggle_show_all_files();
    init();
  };
}

async function renderRoms(roms) {
  if(!romListEl) return;
  romListEl.innerHTML = '';
  
  let isExplorerMode = currentSystemFilter && !currentShowFavorites && currentTagFilters.size === 0 && currentSearchQuery === "";
  let filesToShow = [];
  let foldersToShow = new Set();
  let displayedRoms = roms;
  
  if (isExplorerMode) {
      const basePath = currentSystemFilter === 'Uncategorized' ? (currentSubpathFilter ? 'Uncategorized/' + currentSubpathFilter + '/' : 'Uncategorized/') : (currentSystemFilter + (currentSubpathFilter ? '/' + currentSubpathFilter : '') + '/');
      
      const realDirs = await window.pywebview.api.get_subdirectories(basePath);
      realDirs.forEach(d => foldersToShow.add(d));
      
      roms.forEach(r => {
          if (r.folder_name === currentSystemFilter) {
              if (r.filename.startsWith(basePath)) {
                  const relPath = r.filename.substring(basePath.length);
                  if (relPath.includes('/')) {
                      foldersToShow.add(relPath.split('/')[0]);
                  } else {
                      filesToShow.push(r);
                  }
              }
          }
      });
      displayedRoms = filesToShow;
  } else {
      if (currentSystemFilter) displayedRoms = displayedRoms.filter(r => r.folder_name === currentSystemFilter);
      if (currentShowFavorites) displayedRoms = displayedRoms.filter(r => r.is_favorite);
      if (currentTagFilters.size > 0) displayedRoms = displayedRoms.filter(r => r.tags && Array.from(currentTagFilters).every(f => r.tags.includes(f)));
      if (currentSearchQuery !== "") displayedRoms = displayedRoms.filter(r => r.name.toLowerCase().includes(currentSearchQuery) || r.filename.toLowerCase().includes(currentSearchQuery));
  }
  
  const countEl = document.getElementById('total-roms-count');
  if (countEl) countEl.innerText = displayedRoms.length;
  
  const breadcrumbsEl = document.getElementById('breadcrumbs-container');
  if (breadcrumbsEl) {
    if (isExplorerMode) {
        breadcrumbsEl.style.display = 'flex';
        breadcrumbsEl.innerHTML = '';
        const parts = currentSubpathFilter ? currentSubpathFilter.split('/') : [];
        
        const createCrumb = (text, path, isLast) => {
            const span = document.createElement('span');
            span.innerText = text;
            if (!isLast) {
                span.style.cursor = 'pointer';
                span.style.color = '#0A84FF';
                span.onclick = () => {
                    currentSubpathFilter = path;
                    renderRoms(currentRoms);
                };
                const arrow = document.createElement('span');
                arrow.innerText = ' > ';
                arrow.style.color = '#48484A';
                
                breadcrumbsEl.appendChild(span);
                breadcrumbsEl.appendChild(arrow);
            } else {
                span.style.color = '#FFFFFF';
                span.style.fontWeight = '600';
                breadcrumbsEl.appendChild(span);
            }
        };
        
        createCrumb(currentSystemFilter, "", parts.length === 0);
        let accumPath = "";
        parts.forEach((p, i) => {
            accumPath = accumPath ? accumPath + '/' + p : p;
            createCrumb(p, accumPath, i === parts.length - 1);
        });
    } else {
        breadcrumbsEl.style.display = 'none';
    }
  }

  if (isExplorerMode) {
    Array.from(foldersToShow).sort().forEach(folderName => {
      const row = document.createElement('div');
      row.className = 'rom-row';
      row.style.cursor = 'pointer';
      
      row.innerHTML = `
        <div class="system-badge" style="background:transparent; display:flex; justify-content:center; align-items:center;"><i data-lucide="folder" style="color:#0A84FF;width:16px;height:16px;"></i></div>
        <div style="flex:1; display:flex; align-items:center;">
          <span class="rom-name" style="font-weight:600;">${folderName}</span>
        </div>
      `;
      
      row.ondblclick = () => {
        currentSubpathFilter = currentSubpathFilter ? currentSubpathFilter + '/' + folderName : folderName;
        renderRoms(currentRoms);
      };
      
      row.ondragover = (e) => {
        e.preventDefault();
        row.classList.add('drag-over');
      };
      
      row.ondragleave = (e) => {
        row.classList.remove('drag-over');
      };
      
      row.ondrop = async (e) => {
        e.preventDefault();
        row.classList.remove('drag-over');
        
        const data = e.dataTransfer.getData("text/plain");
        if (data) {
          const ids = JSON.parse(data);
          const targetSystem = currentSystemFilter + (currentSubpathFilter ? '/' + currentSubpathFilter : '') + '/' + folderName;
          const success = await window.pywebview.api.move_roms(ids, targetSystem);
          if (success) {
            selectedIds.clear();
            init();
          }
        }
      };
      
      row.oncontextmenu = (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        if (selectedIds.size > 0) {
          selectedIds.clear();
          renderRoms(currentRoms);
          updateDetailPanel();
        }
        
        document.getElementById('cm-folder-options').style.display = 'none';
        document.getElementById('cm-collection-options').style.display = 'none';
        document.getElementById('cm-tag-options').style.display = 'none';
        document.getElementById('cm-list-options').style.display = 'none';
        document.getElementById('cm-rom-options').style.display = 'none';
        
        const subMenu = document.getElementById('cm-subfolder-options');
        subMenu.style.display = 'block';
        
        currentContextFolder = currentSystemFilter + (currentSubpathFilter ? '/' + currentSubpathFilter : '');
        currentContextDisplay = folderName;
        
        contextMenu.style.display = 'block';
        contextMenu.style.left = `${e.pageX}px`;
        contextMenu.style.top = `${e.pageY}px`;
        lucide.createIcons();
      };
      
      romListEl.appendChild(row);
    });
  }
  
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
      
    const parts = rom.filename.split('/');
    let subfolderBadge = '';
    if (parts.length > 2) {
      const subpath = parts.slice(1, -1).join('/');
      subfolderBadge = `<span style="background:#48484A; color:#EBEBF5; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:6px; display:inline-flex; align-items:center;"><i data-lucide="folder" style="width:10px;height:10px;margin-right:4px;"></i>${subpath}</span>`;
    }

    row.innerHTML = `
      <div class="system-badge ${badgeClass}">${ext}</div>
      <div style="flex:1; display:flex; align-items:center;">
        ${heartHTML}
        <span class="rom-name">${rom.name}</span>
        ${subfolderBadge}
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
    
    row.oncontextmenu = (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      if (!selectedIds.has(rom.id)) {
        selectedIds.clear();
        selectedIds.add(rom.id);
        renderRoms(currentRoms);
        updateDetailPanel();
      }
      
      document.getElementById('cm-folder-options').style.display = 'none';
      document.getElementById('cm-collection-options').style.display = 'none';
      document.getElementById('cm-tag-options').style.display = 'none';
      document.getElementById('cm-list-options').style.display = 'none';
      document.getElementById('cm-subfolder-options').style.display = 'none';
      
      const romMenu = document.getElementById('cm-rom-options');
      romMenu.style.display = 'block';
      
      const ext = rom.filename.split('.').pop().toLowerCase();
      const isZip = ext === 'zip' || ext === '7z';
      const unzipBtn = document.getElementById('cm-rom-zip-unzip');
      if (isZip) {
          unzipBtn.innerHTML = '<i data-lucide="archive-restore" style="width:14px;height:14px;"></i> Unzip';
      } else {
          unzipBtn.innerHTML = '<i data-lucide="file-archive" style="width:14px;height:14px;"></i> Zip';
      }
      
      contextMenu.style.display = 'block';
      contextMenu.style.left = `${e.pageX}px`;
      contextMenu.style.top = `${e.pageY}px`;
      lucide.createIcons();
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
    const raContainer = document.getElementById('ra-container');
    if (raContainer) raContainer.style.display = 'none';
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
    const raContainer = document.getElementById('ra-container');
    if (raContainer) raContainer.style.display = 'none';
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
  
  const favoriteBtn = document.getElementById('btn-toggle-favorite');
  if (favoriteBtn) {
    favoriteBtn.onclick = async () => {
      await window.pywebview.api.toggle_favorite(rom.id);
      init();
    };
  }
  
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
    const baseName = rom.filename.split('/').pop().replace(/\.[^/.]+$/, ""); 
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

  const raContainer = document.getElementById('ra-container');
  const raLoading = document.getElementById('ra-loading');
  const raContent = document.getElementById('ra-content');
  if (raContainer) {
    raContainer.style.display = 'block';
    raLoading.style.display = 'block';
    raContent.style.display = 'none';
    
    window.pywebview.api.get_ra_game_info(rom.id).then(res => {
      if (selectedIds.size !== 1 || Array.from(selectedIds)[0] !== rom.id) return;
      
      raLoading.style.display = 'none';
      if (res.error) {
        if (res.error === "Credentials not configured") {
           raContainer.style.display = 'none';
        } else {
           raContent.innerHTML = `<div style="color:#FF453A; font-size:12px;">${res.error}</div>`;
           raContent.style.display = 'flex';
        }
      } else {
        const d = res.data;
        const achievementsHtml = (d.Achievements && Object.keys(d.Achievements).length > 0) ? 
           Object.values(d.Achievements).map(ach => `
             <div style="display:flex; align-items:center; gap:8px; background:#2C2C2E; padding:8px; border-radius:6px; margin-bottom:4px;">
               <img src="https://media.retroachievements.org/Badge/${ach.BadgeName}.png" style="width:32px; height:32px; border-radius:4px;" onerror="this.style.display='none'">
               <div style="flex:1;">
                 <div style="font-size:12px; font-weight:600; color:#fff; word-break:break-word;">${ach.Title}</div>
                 <div style="font-size:10px; color:#8E8E93; word-break:break-word;">${ach.Description}</div>
               </div>
               <div style="font-size:12px; font-weight:600; color:#0A84FF;">${ach.Points}</div>
             </div>
           `).join('') : '<div style="font-size:12px; color:#8E8E93;">No achievements found.</div>';
           
        const gameImage = d.ImageBoxArt || d.ImageIcon;
        const imageUrl = gameImage ? (gameImage.startsWith('http') ? gameImage : `https://media.retroachievements.org${gameImage.startsWith('/') ? '' : '/'}${gameImage}`) : null;
        raContent.innerHTML = `
          <div style="display:flex; gap:8px; margin-bottom:12px; align-items:center;">
             ${imageUrl ? `<img src="${imageUrl}" style="width:48px;height:48px;border-radius:4px;object-fit:cover;" onerror="this.style.display='none'">` : ''}
             <div style="flex:1;">
               <div style="font-size:14px; font-weight:600; color:#fff;">${d.Title || 'Game'}</div>
               <div style="font-size:12px; color:#8E8E93;">${d.ConsoleName || ''}</div>
             </div>
          </div>
          <div style="max-height: 250px; overflow-y:auto; padding-right:4px;">
             ${achievementsHtml}
          </div>
        `;
        raContent.style.display = 'flex';
      }
    }).catch(err => {
      if (selectedIds.size === 1 && Array.from(selectedIds)[0] === rom.id) {
         raLoading.style.display = 'none';
         raContent.innerHTML = `<div style="color:#FF453A; font-size:12px;">Error connecting to API.</div>`;
         raContent.style.display = 'flex';
      }
    });
  }
}

// Start
window.addEventListener('pywebviewready', function() {
  init();
});
