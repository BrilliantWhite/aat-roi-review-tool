const LANGUAGE_STORAGE_KEY = 'aat-review-language';

const TRANSLATIONS = {
    zh: {
        documentTitle: 'AAT 凝胶 ROI / 泳道复核工具',
        languageToggle: 'EN',
        appTitle: 'AAT 凝胶复核工具',
        loading: '加载中...',
        noImage: '暂无图像',
        headings: {
            imageList: '图像列表',
            status: '当前状态',
            display: '显示设置',
            annotation: '泳道标注',
            actions: '操作',
        },
        controls: {
            maskOpacity: 'Mask 透明度',
            exportCsv: '导出 CSV annotation',
            exportJsonl: '导出 JSONL annotation',
            prev: '上一张',
            next: '下一张',
            updateDataset: '更新数据集',
            importReviewRestore: '导入可复现分割CSV',
            importTrainingCsv: '导入标注CSV',
            exportReviewRestore: '导出可复现分割CSV',
            exportTrainingCsv: '导出训练CSV',
            reloadSaved: '从可复现CSV恢复',
            reset: '重置',
            save: '保存当前图 reviewed CSV',
        },
        workspace: {
            emptyTitle: 'ROI / lane visual review',
            emptySubtitle: '绿色区域表示共享 ROI；黄色边界可左右拖拽调整。',
            title: imageId => `${imageId} ROI / lane review`,
            subtitle: (qualityFlag, manualReviewRequired) => `quality=${qualityFlag || 'n/a'} · manual_review_required=${manualReviewRequired}`,
            legendRoi: 'ROI',
            legendBoundary: 'Lane boundary',
            legendCenter: 'Lane center',
        },
        imageList: {
            badgeImported: 'imported',
            badgeReviewed: 'reviewed',
            badgePending: 'pending',
            qualityAccepted: (qualityFlag, acceptedCount) => `quality=${qualityFlag || 'n/a'} · accepted=${acceptedCount}`,
            manualReviewRequired: 'manual review required',
        },
        status: {
            roiSource: 'ROI source',
            boundarySource: 'Boundary source',
            quality: 'Quality',
            detectionQuality: 'Detection quality',
            acceptedCount: 'Accepted count',
            reviewStatus: 'Review status',
            annotationLanes: 'Annotation lanes',
            roi: 'ROI',
            imageSize: 'Image size',
            importedSession: 'imported session',
            unreviewed: 'unreviewed',
        },
        annotation: {
            importedState: '当前显示的是导入训练CSV恢复出的临时编辑状态',
            hasFileState: '已有逐泳道训练 annotation 文件',
            noCategoryState: '未填写 category 的泳道不会导出 annotation',
            summary: (annotatedCount, totalCount) => `已标注 ${annotatedCount} / ${totalCount} 条泳道。点击主图中的泳道可放大并填写 category。`,
        },
        category: {
            inputPlaceholder: '输入该泳道 category',
            addSuggestion: '添加到常用项',
            deleteSuggestionTitle: '删除常用项',
            addEmpty: '请输入 category 后再添加常用项',
            addSuccess: '已添加常用 category',
        },
        laneModal: {
            closeAriaLabel: '关闭',
            title: candidateIndex => `Lane ${candidateIndex} category 标注`,
            placeholder: '后续功能预留区域',
            deleteLane: '删除该泳道',
            cancel: '取消',
            save: '保存',
            zoomLabel: '等比放大',
            previewMeta: (boundary, roi) => `导出坐标不含 padding：x=${boundary.left_x}-${boundary.right_x}, y=${roi.y_start}-${roi.y_end}`,
            minLaneToast: '至少需要保留一条泳道',
        },
        resetScope: {
            closeAriaLabel: '关闭',
            title: '选择重置范围',
            description: '请选择要恢复为自动结果的范围。',
            current: '重置当前图为自动结果',
            all: '重置所有图为自动结果',
            confirmCurrent: '这会将当前图片恢复为自动结果。是否继续？',
            confirmAll: '这会将所有图片恢复为自动结果，并清除当前导入的训练CSV会话。是否继续？',
            successCurrent: '已重置当前图片为自动结果',
            successAll: '已重置所有图片为自动结果',
        },
        confirm: {
            reloadSaved: 'This will restore Web/review_exports/review_restore_export.csv into the reviewed CSV files. Continue?',
            updateDataset: '更新数据集会重新扫描 dataset/Originial/ 并重跑自动分割；当前未保存修改会被丢弃。是否继续？',
            importReviewRestore: 'Importing review_restore_export.csv will overwrite saved reviewed CSV rows for the matching images. Continue?',
            importTrainingCsv: 'Current unsaved drafts will be discarded after import. Continue?',
            exportTrainingWithoutUnlabeled: 'Export unlabeled lanes as unknown? Click OK for yes, Cancel to skip unlabeled lanes.',
        },
        toast: {
            saveSuccess: '已保存当前图 reviewed CSV',
            reloadSavedSuccess: (imageCount, laneCount) => `已从可复现CSV恢复：${imageCount} 张图，${laneCount} 条泳道`,
            updateDatasetSuccess: (imageCount, addedQualityRows) => `已更新数据集：${imageCount} 张图，新增 ${addedQualityRows} 条质量报告占位行`,
            importReviewRestoreSuccess: (imageCount, laneCount) => `已导入可复现分割CSV：${imageCount} 张图，${laneCount} 条泳道`,
            importTrainingCsvSuccess: (imageCount, laneCount) => `已导入标注CSV：${imageCount} 张图，${laneCount} 条泳道`,
            exportReviewRestoreSuccess: (imageCount, laneCount) => `已导出可复现分割CSV：${imageCount} 张图，${laneCount} 条泳道`,
            exportTrainingCsvSuccess: (imageCount, laneCount, includeUnlabeled) => `已导出训练CSV：${imageCount} 张图，${laneCount} 条泳道${includeUnlabeled ? '（未标注=unknown）' : '（已跳过未标注）'}`,
            initFailed: '初始化失败',
        },
    },
    en: {
        documentTitle: 'AAT Gel ROI / Lane Review Tool',
        languageToggle: '中文',
        appTitle: 'AAT Gel Review Tool',
        loading: 'Loading...',
        noImage: 'No image',
        headings: {
            imageList: 'Image List',
            status: 'Current Status',
            display: 'Display Settings',
            annotation: 'Lane Annotation',
            actions: 'Actions',
        },
        controls: {
            maskOpacity: 'Mask Opacity',
            exportCsv: 'Export CSV annotation',
            exportJsonl: 'Export JSONL annotation',
            prev: 'Previous',
            next: 'Next',
            updateDataset: 'Update dataset',
            importReviewRestore: 'Import restore CSV',
            importTrainingCsv: 'Import annotation CSV',
            exportReviewRestore: 'Export restore CSV',
            exportTrainingCsv: 'Export training CSV',
            reloadSaved: 'Restore exported CSV',
            reset: 'Reset',
            save: 'Save current reviewed CSV',
        },
        workspace: {
            emptyTitle: 'ROI / lane visual review',
            emptySubtitle: 'Green overlays indicate the shared ROI; drag the yellow boundaries left or right to adjust lanes.',
            title: imageId => `${imageId} ROI / lane review`,
            subtitle: (qualityFlag, manualReviewRequired) => `quality=${qualityFlag || 'n/a'} · manual_review_required=${manualReviewRequired}`,
            legendRoi: 'ROI',
            legendBoundary: 'Lane boundary',
            legendCenter: 'Lane center',
        },
        imageList: {
            badgeImported: 'Imported',
            badgeReviewed: 'Reviewed',
            badgePending: 'Pending',
            qualityAccepted: (qualityFlag, acceptedCount) => `quality=${qualityFlag || 'n/a'} · accepted=${acceptedCount}`,
            manualReviewRequired: 'Manual review required',
        },
        status: {
            roiSource: 'ROI source',
            boundarySource: 'Boundary source',
            quality: 'Quality',
            detectionQuality: 'Detection quality',
            acceptedCount: 'Accepted count',
            reviewStatus: 'Review status',
            annotationLanes: 'Annotation lanes',
            roi: 'ROI',
            imageSize: 'Image size',
            importedSession: 'Imported session',
            unreviewed: 'Unreviewed',
        },
        annotation: {
            importedState: 'You are viewing a temporary edit state restored from an imported training CSV.',
            hasFileState: 'Per-lane training annotation file already exists.',
            noCategoryState: 'Lanes without a category will not be exported to annotation files.',
            summary: (annotatedCount, totalCount) => `${annotatedCount} / ${totalCount} lanes annotated. Click a lane in the main view to zoom in and fill in its category.`,
        },
        category: {
            inputPlaceholder: 'Enter the category for this lane',
            addSuggestion: 'Add to suggestions',
            deleteSuggestionTitle: 'Remove suggestion',
            addEmpty: 'Enter a category before adding it to suggestions',
            addSuccess: 'Category added to suggestions',
        },
        laneModal: {
            closeAriaLabel: 'Close',
            title: candidateIndex => `Annotate category for lane ${candidateIndex}`,
            placeholder: 'Reserved area for future features',
            deleteLane: 'Delete this lane',
            cancel: 'Cancel',
            save: 'Save',
            zoomLabel: 'Zoom',
            previewMeta: (boundary, roi) => `Export coordinates exclude padding: x=${boundary.left_x}-${boundary.right_x}, y=${roi.y_start}-${roi.y_end}`,
            minLaneToast: 'At least one lane must remain',
        },
        resetScope: {
            closeAriaLabel: 'Close',
            title: 'Choose reset scope',
            description: 'Select which scope should be restored to automatic results.',
            current: 'Reset current image to automatic results',
            all: 'Reset all images to automatic results',
            confirmCurrent: 'This will restore the current image to automatic results. Continue?',
            confirmAll: 'This will restore all images to automatic results and clear the imported training CSV session. Continue?',
            successCurrent: 'Current image reset to automatic results',
            successAll: 'All images reset to automatic results',
        },
        confirm: {
            reloadSaved: 'This will restore Web/review_exports/review_restore_export.csv into the reviewed CSV files. Continue?',
            updateDataset: 'Updating the dataset will rescan dataset/Originial/ and rerun automatic segmentation. Current unsaved drafts will be discarded. Continue?',
            importReviewRestore: 'Importing review_restore_export.csv will overwrite saved reviewed CSV rows for the matching images. Continue?',
            importTrainingCsv: 'Current unsaved drafts will be discarded after import. Continue?',
            exportTrainingWithoutUnlabeled: 'Export unlabeled lanes as unknown? Click OK for yes, Cancel to skip unlabeled lanes.',
        },
        toast: {
            saveSuccess: 'Current reviewed CSV saved',
            reloadSavedSuccess: (imageCount, laneCount) => `Restored exported CSV: ${imageCount} images, ${laneCount} lanes`,
            updateDatasetSuccess: (imageCount, addedQualityRows) => `Dataset updated: ${imageCount} images, ${addedQualityRows} new quality placeholder rows`,
            importReviewRestoreSuccess: (imageCount, laneCount) => `Imported restore CSV: ${imageCount} images, ${laneCount} lanes`,
            importTrainingCsvSuccess: (imageCount, laneCount) => `Imported annotation CSV: ${imageCount} images, ${laneCount} lanes`,
            exportReviewRestoreSuccess: (imageCount, laneCount) => `Exported restore CSV: ${imageCount} images, ${laneCount} lanes`,
            exportTrainingCsvSuccess: (imageCount, laneCount, includeUnlabeled) => `Exported training CSV: ${imageCount} images, ${laneCount} lanes${includeUnlabeled ? ' (unlabeled=unknown)' : ' (unlabeled skipped)'}`,
            initFailed: 'Initialization failed',
        },
    },
};

const state = {
    images: [],
    currentIndex: 0,
    payload: null,
    drag: null,
    stageWidth: 0,
    stageHeight: 0,
    displayWidth: 0,
    displayHeight: 0,
    displayOffsetX: 0,
    displayOffsetY: 0,
    maskOpacity: 16,
    selectedLaneIndex: null,
    hoveredLaneIndex: null,
    categorySuggestions: [],
    previewZoom: 100,
    isDirty: false,
    draftsByImageId: {},
    importedSessionActive: false,
    language: loadLanguage(),
};

const imageListEl = document.getElementById('image-list');
const currentImageLabelEl = document.getElementById('current-image-label');
const statusPanelEl = document.getElementById('status-panel');
const notesEl = document.getElementById('review-notes');
const targetImageEl = document.getElementById('target-image');
const overlayEl = document.getElementById('overlay');
const overlayLayerEl = document.getElementById('overlay-layer');
const toastContainerEl = document.getElementById('toast-container');
const workspaceTitleEl = document.getElementById('workspace-title');
const workspaceSubtitleEl = document.getElementById('workspace-subtitle');
const imageStageEl = document.getElementById('image-stage');
const maskOpacityEl = document.getElementById('mask-opacity');
const maskOpacityValueEl = document.getElementById('mask-opacity-value');
const annotationFileStateEl = document.getElementById('annotation-file-state');
const annotationFieldsEl = document.getElementById('annotation-fields');
const writeAnnotationCsvEl = document.getElementById('write-annotation-csv');
const writeAnnotationJsonlEl = document.getElementById('write-annotation-jsonl');
const laneModalEl = document.getElementById('lane-modal');
const laneModalBackdropEl = document.getElementById('lane-modal-backdrop');
const laneModalCloseEl = document.getElementById('lane-modal-close');
const laneModalTitleEl = document.getElementById('lane-modal-title');
const laneCategoryInputEl = document.getElementById('lane-category-input');
const categorySuggestionsEl = document.getElementById('category-suggestions');
const categoryChipListEl = document.getElementById('category-chip-list');
const lanePreviewCanvasEl = document.getElementById('lane-preview-canvas');
const lanePreviewZoomEl = document.getElementById('lane-preview-zoom');
const lanePreviewZoomValueEl = document.getElementById('lane-preview-zoom-value');
const lanePreviewMetaEl = document.getElementById('lane-preview-meta');
const addCategoryBtnEl = document.getElementById('btn-add-category');
const laneModalCancelEl = document.getElementById('btn-lane-modal-cancel');
const laneModalSaveEl = document.getElementById('btn-lane-modal-save');
const deleteLaneBtnEl = document.getElementById('btn-delete-lane');
const trainingCsvInputEl = document.getElementById('training-csv-input');
const restoreCsvInputEl = document.getElementById('restore-csv-input');
const updateDatasetBtnEl = document.getElementById('btn-update-dataset');
const importReviewRestoreBtnEl = document.getElementById('btn-import-review-restore');
const importTrainingCsvBtnEl = document.getElementById('btn-import-training-csv');
const exportReviewRestoreBtnEl = document.getElementById('btn-export-review-restore');
const exportTrainingCsvBtnEl = document.getElementById('btn-export-training-csv');
const reloadSavedBtnEl = document.getElementById('btn-reload-saved');
const resetBtnEl = document.getElementById('btn-reset');
const saveBtnEl = document.getElementById('btn-save');
const prevBtnEl = document.getElementById('btn-prev');
const nextBtnEl = document.getElementById('btn-next');
const resetScopeModalEl = document.getElementById('reset-scope-modal');
const resetScopeBackdropEl = document.getElementById('reset-scope-backdrop');
const resetScopeCloseEl = document.getElementById('reset-scope-close');
const resetCurrentBtnEl = document.getElementById('btn-reset-current');
const resetAllBtnEl = document.getElementById('btn-reset-all');
const languageToggleEl = document.getElementById('language-toggle');
const appTitleEl = document.getElementById('app-title');
const headingImageListEl = document.getElementById('heading-image-list');
const headingStatusEl = document.getElementById('heading-status');
const headingDisplayEl = document.getElementById('heading-display');
const headingAnnotationEl = document.getElementById('heading-annotation');
const headingActionsEl = document.getElementById('heading-actions');
const exportCsvLabelEl = document.getElementById('label-export-csv');
const exportJsonlLabelEl = document.getElementById('label-export-jsonl');
const legendRoiEl = document.getElementById('legend-roi');
const legendBoundaryEl = document.getElementById('legend-boundary');
const legendCenterEl = document.getElementById('legend-center');
const laneModalPlaceholderEl = document.getElementById('lane-modal-placeholder');
const lanePreviewZoomLabelEl = document.getElementById('lane-preview-zoom-label');
const resetScopeDescriptionEl = document.getElementById('reset-scope-description');

function t(path, ...args) {
    const value = path.split('.').reduce((current, key) => current?.[key], TRANSLATIONS[state.language]);
    if (typeof value === 'function') {
        return value(...args);
    }
    return value;
}

function loadLanguage() {
    const savedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return savedLanguage === 'en' ? 'en' : 'zh';
}

function setLanguage(language) {
    state.language = language === 'en' ? 'en' : 'zh';
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, state.language);
    applyLanguage();
}

function toggleLanguage() {
    setLanguage(state.language === 'zh' ? 'en' : 'zh');
}

function applyLanguage() {
    document.documentElement.lang = state.language;
    document.title = t('documentTitle');
    languageToggleEl.textContent = t('languageToggle');
    appTitleEl.textContent = t('appTitle');
    headingImageListEl.textContent = t('headings.imageList');
    headingStatusEl.textContent = t('headings.status');
    headingDisplayEl.textContent = t('headings.display');
    headingAnnotationEl.textContent = t('headings.annotation');
    headingActionsEl.textContent = t('headings.actions');
    document.getElementById('mask-opacity-label').textContent = t('controls.maskOpacity');
    exportCsvLabelEl.textContent = t('controls.exportCsv');
    exportJsonlLabelEl.textContent = t('controls.exportJsonl');
    prevBtnEl.textContent = t('controls.prev');
    nextBtnEl.textContent = t('controls.next');
    updateDatasetBtnEl.textContent = t('controls.updateDataset');
    importReviewRestoreBtnEl.textContent = t('controls.importReviewRestore');
    importTrainingCsvBtnEl.textContent = t('controls.importTrainingCsv');
    exportReviewRestoreBtnEl.textContent = t('controls.exportReviewRestore');
    exportTrainingCsvBtnEl.textContent = t('controls.exportTrainingCsv');
    reloadSavedBtnEl.textContent = t('controls.reloadSaved');
    resetBtnEl.textContent = t('controls.reset');
    saveBtnEl.textContent = t('controls.save');
    legendRoiEl.innerHTML = `<i class="legend-swatch roi"></i> ${t('workspace.legendRoi')}`;
    legendBoundaryEl.innerHTML = `<i class="legend-swatch boundary"></i> ${t('workspace.legendBoundary')}`;
    legendCenterEl.innerHTML = `<i class="legend-swatch center"></i> ${t('workspace.legendCenter')}`;
    laneModalCloseEl.setAttribute('aria-label', t('laneModal.closeAriaLabel'));
    laneCategoryInputEl.placeholder = t('category.inputPlaceholder');
    addCategoryBtnEl.textContent = t('category.addSuggestion');
    laneModalPlaceholderEl.textContent = t('laneModal.placeholder');
    deleteLaneBtnEl.textContent = t('laneModal.deleteLane');
    laneModalCancelEl.textContent = t('laneModal.cancel');
    laneModalSaveEl.textContent = t('laneModal.save');
    lanePreviewZoomLabelEl.textContent = t('laneModal.zoomLabel');
    resetScopeCloseEl.setAttribute('aria-label', t('resetScope.closeAriaLabel'));
    document.getElementById('reset-scope-title').textContent = t('resetScope.title');
    resetScopeDescriptionEl.textContent = t('resetScope.description');
    resetCurrentBtnEl.textContent = t('resetScope.current');
    resetAllBtnEl.textContent = t('resetScope.all');

    if (state.payload) {
        currentImageLabelEl.textContent = `${state.payload.image.image_id} · ${state.payload.image.source_filename}`;
        workspaceTitleEl.textContent = t('workspace.title', state.payload.image.image_id);
        workspaceSubtitleEl.textContent = t(
            'workspace.subtitle',
            state.payload.manifest.quality_flag,
            state.payload.manifest.manual_review_required,
        );
        if (!laneModalEl.classList.contains('hidden') && state.selectedLaneIndex !== null) {
            const boundary = getBoundaryByCandidateIndex(state.selectedLaneIndex);
            if (boundary) {
                laneModalTitleEl.textContent = t('laneModal.title', state.selectedLaneIndex);
                lanePreviewMetaEl.textContent = t('laneModal.previewMeta', boundary, state.payload.roi);
            }
        }
    } else {
        currentImageLabelEl.textContent = state.images.length > 0 ? t('loading') : t('noImage');
        workspaceTitleEl.textContent = t('workspace.emptyTitle');
        workspaceSubtitleEl.textContent = t('workspace.emptySubtitle');
    }

    renderImageList();
    renderStatusPanel();
    renderAnnotationFields();
    renderCategorySuggestions();
}

async function fetchJson(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) {
        const body = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(body.detail || 'Request failed');
    }
    return response.json();
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    toastContainerEl.appendChild(toast);
    toastContainerEl.className = 'toast-container';
    setTimeout(() => toast.remove(), 2800);
}

function hasAnyDrafts() {
    return Object.keys(state.draftsByImageId).length > 0;
}

function getCurrentImageId() {
    return state.payload?.image?.image_id || null;
}

function cloneJson(value) {
    return value == null ? value : JSON.parse(JSON.stringify(value));
}

function captureCurrentDraft() {
    if (!state.payload) {
        return null;
    }
    return {
        y_start: state.payload.roi.y_start,
        y_end: state.payload.roi.y_end,
        notes: notesEl.value.trim(),
        boundaries: cloneJson(state.payload.boundaries),
    };
}

function applyDraftToPayload(payload, draft) {
    if (!payload || !draft) {
        return;
    }
    payload.roi.y_start = draft.y_start;
    payload.roi.y_end = draft.y_end;
    payload.boundaries = cloneJson(draft.boundaries) || [];
    payload.review = { ...(payload.review || {}), notes: draft.notes || '' };
}

function syncDirtyState() {
    state.isDirty = hasAnyDrafts();
}

function saveCurrentDraft() {
    const imageId = getCurrentImageId();
    if (!imageId) {
        return;
    }
    state.draftsByImageId[imageId] = captureCurrentDraft();
    syncDirtyState();
}

function dropDraft(imageId) {
    if (!imageId || !state.draftsByImageId[imageId]) {
        return;
    }
    delete state.draftsByImageId[imageId];
    syncDirtyState();
}

function clearAllDrafts() {
    state.draftsByImageId = {};
    syncDirtyState();
}

function markDirty() {
    saveCurrentDraft();
}

function clearDirty() {
    syncDirtyState();
}

function ensureProceedWithDirty(message) {
    if (!hasAnyDrafts()) {
        return true;
    }
    return window.confirm(message);
}

function buildImageItem(item, index) {
    const div = document.createElement('div');
    div.className = `image-item ${index === state.currentIndex ? 'active' : ''}`;
    const badgeText = item.has_imported_session
        ? t('imageList.badgeImported')
        : (item.has_review ? t('imageList.badgeReviewed') : t('imageList.badgePending'));
    const badgeClass = item.has_imported_session ? 'imported' : (item.has_review ? 'reviewed' : 'pending');
    div.innerHTML = `
        <div class="top-row">
            <span class="image-id">${item.image_id}</span>
            <span class="badge ${badgeClass}">${badgeText}</span>
        </div>
        <div class="meta-row">${item.source_filename}</div>
        <div class="meta-row">${t('imageList.qualityAccepted', item.quality_flag, item.accepted_boundary_count)}</div>
    `;
    div.addEventListener('click', () => loadImageAt(index).catch(error => showToast(error.message)));
    return div;
}

function renderImageList() {
    imageListEl.innerHTML = '';
    state.images.forEach((item, index) => imageListEl.appendChild(buildImageItem(item, index)));
}

function renderStatusPanel() {
    const payload = state.payload;
    if (!payload) {
        statusPanelEl.innerHTML = '';
        return;
    }

    const annotatedCount = payload.boundaries.filter(hasLaneAnnotation).length;
    const cards = [
        [t('status.roiSource'), payload.roi.source],
        [t('status.boundarySource'), payload.boundary_source],
        [t('status.quality'), payload.manifest.quality_flag || 'n/a'],
        [t('status.detectionQuality'), payload.manifest.detection_quality_flag || 'n/a'],
        [t('status.acceptedCount'), String(payload.manifest.accepted_boundary_count)],
        [t('status.reviewStatus'), payload.review.has_imported_session ? t('status.importedSession') : (payload.review.review_status || t('status.unreviewed'))],
        [t('status.annotationLanes'), `${annotatedCount} / ${payload.boundaries.length}`],
        [t('status.roi'), `${payload.roi.y_start} - ${payload.roi.y_end}`],
        [t('status.imageSize'), `${payload.image.width} × ${payload.image.height}`],
    ];

    statusPanelEl.innerHTML = cards
        .map(([label, value]) => `<div class="info-card"><label>${label}</label><strong>${value}</strong></div>`)
        .join('');
}

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function getViewBoxRect() {
    return {
        width: state.payload.image.width,
        height: state.payload.image.height,
    };
}

function updateMaskOpacityLabel() {
    maskOpacityValueEl.textContent = `${state.maskOpacity}%`;
}

function updateLanePreviewZoom() {
    lanePreviewZoomValueEl.textContent = `${state.previewZoom}%`;
    lanePreviewCanvasEl.style.transform = `scale(${state.previewZoom / 100})`;
    lanePreviewCanvasEl.style.marginBottom = `${lanePreviewCanvasEl.height * (state.previewZoom / 100 - 1)}px`;
}

function getLaneCategory(boundary) {
    return String(boundary.annotation?.category || '').trim();
}

function setLaneCategory(boundary, category) {
    boundary.annotation = { ...(boundary.annotation || {}), category: category.trim() };
}

function hasLaneAnnotation(boundary) {
    return getLaneCategory(boundary).length > 0;
}

function renderAnnotationFields() {
    if (!state.payload) {
        annotationFieldsEl.innerHTML = '';
        annotationFileStateEl.textContent = '';
        return;
    }

    const annotatedCount = state.payload.boundaries.filter(hasLaneAnnotation).length;
    const totalCount = state.payload.boundaries.length;
    annotationFileStateEl.textContent = state.payload.review?.has_imported_session
        ? t('annotation.importedState')
        : (state.payload.annotation?.has_annotation_file
            ? t('annotation.hasFileState')
            : t('annotation.noCategoryState'));

    annotationFieldsEl.innerHTML = `
        <div class="annotation-summary">
            ${t('annotation.summary', annotatedCount, totalCount)}
        </div>
    `;
}

function collectAnnotationPayload() {
    const lanes = state.payload.boundaries
        .map(boundary => ({
            candidate_index: boundary.candidate_index,
            category: getLaneCategory(boundary),
        }))
        .filter(lane => lane.category.length > 0);

    return { enabled: lanes.length > 0, lanes };
}

async function loadCategorySuggestions() {
    const payload = await fetchJson('/api/categories');
    state.categorySuggestions = payload.categories || [];
    renderCategorySuggestions();
}

function renderCategorySuggestions() {
    categorySuggestionsEl.innerHTML = '';
    state.categorySuggestions.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        categorySuggestionsEl.appendChild(option);
    });

    categoryChipListEl.innerHTML = '';
    state.categorySuggestions.forEach(category => {
        const chip = document.createElement('span');
        chip.className = 'category-chip';
        const label = document.createElement('button');
        label.type = 'button';
        label.textContent = category;
        label.addEventListener('click', () => {
            laneCategoryInputEl.value = category;
            laneCategoryInputEl.focus();
        });
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.textContent = '×';
        remove.title = t('category.deleteSuggestionTitle');
        remove.setAttribute('aria-label', t('category.deleteSuggestionTitle'));
        remove.addEventListener('click', async event => {
            event.stopPropagation();
            await deleteCategorySuggestion(category);
        });
        chip.append(label, remove);
        categoryChipListEl.appendChild(chip);
    });
}

async function addCurrentCategorySuggestion() {
    const category = laneCategoryInputEl.value.trim();
    if (!category) {
        showToast(t('category.addEmpty'));
        return;
    }
    const payload = await fetchJson('/api/categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category }),
    });
    state.categorySuggestions = payload.categories || [];
    renderCategorySuggestions();
    showToast(t('category.addSuccess'));
}

async function deleteCategorySuggestion(category) {
    const payload = await fetchJson(`/api/categories/${encodeURIComponent(category)}`, { method: 'DELETE' });
    state.categorySuggestions = payload.categories || [];
    renderCategorySuggestions();
}

async function uploadTrainingCsv(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch('/api/import/training-annotations', {
        method: 'POST',
        body: formData,
    });
    if (!response.ok) {
        const body = await response.json().catch(() => ({ detail: 'Import failed' }));
        throw new Error(body.detail || 'Import failed');
    }
    return response.json();
}

async function uploadReviewRestoreCsv(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch('/api/import/review-restore', {
        method: 'POST',
        body: formData,
    });
    if (!response.ok) {
        const body = await response.json().catch(() => ({ detail: 'Import failed' }));
        throw new Error(body.detail || 'Import failed');
    }
    return response.json();
}

async function exportReviewRestoreCsv() {
    const payload = await fetchJson('/api/exports/review-restore', { method: 'POST' });
    showToast(t('toast.exportReviewRestoreSuccess', payload.image_count, payload.lane_count));
}

async function exportTrainingCsv() {
    const includeUnlabeled = window.confirm(t('confirm.exportTrainingWithoutUnlabeled'));
    const payload = await fetchJson('/api/exports/training-lanes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ include_unlabeled: includeUnlabeled }),
    });
    showToast(t('toast.exportTrainingCsvSuccess', payload.image_count, payload.lane_count, payload.include_unlabeled));
}

function recomputeBoundary(boundary) {
    boundary.center_x = Math.round((boundary.left_x + boundary.right_x) / 2);
    boundary.estimated_width = boundary.right_x - boundary.left_x;
}

function recomputeAllBoundaries() {
    if (!state.payload) return;
    state.payload.boundaries.forEach(recomputeBoundary);
}

function normalizeSharedBoundaries() {
    if (!state.payload || state.payload.boundaries.length < 2) {
        recomputeAllBoundaries();
        return;
    }

    const boundaries = state.payload.boundaries;
    for (let index = 0; index < boundaries.length - 1; index += 1) {
        const sharedX = Math.round((boundaries[index].right_x + boundaries[index + 1].left_x) / 2);
        boundaries[index].right_x = sharedX;
        boundaries[index + 1].left_x = sharedX;
    }

    recomputeAllBoundaries();
}

function buildSharedBoundarySpecs(boundaries) {
    if (boundaries.length === 0) return [];

    const specs = [{ boundaryRole: 'outer-left', x: boundaries[0].left_x, laneIndex: 0 }];
    for (let index = 0; index < boundaries.length - 1; index += 1) {
        specs.push({
            boundaryRole: 'shared',
            x: boundaries[index].right_x,
            leftIndex: index,
            rightIndex: index + 1,
        });
    }
    specs.push({ boundaryRole: 'outer-right', x: boundaries[boundaries.length - 1].right_x, laneIndex: boundaries.length - 1 });
    return specs;
}

function updateStageMetrics() {
    const rect = imageStageEl.getBoundingClientRect();
    state.stageWidth = rect.width;
    state.stageHeight = rect.height;

    if (!state.payload) {
        return;
    }

    const imageWidth = state.payload.image.width;
    const imageHeight = state.payload.image.height;
    const scale = Math.min(state.stageWidth / imageWidth, state.stageHeight / imageHeight);
    state.displayWidth = imageWidth * scale;
    state.displayHeight = imageHeight * scale;
    state.displayOffsetX = (state.stageWidth - state.displayWidth) / 2;
    state.displayOffsetY = (state.stageHeight - state.displayHeight) / 2;

    targetImageEl.style.width = `${state.displayWidth}px`;
    targetImageEl.style.height = `${state.displayHeight}px`;
    targetImageEl.style.left = `${state.displayOffsetX}px`;
    targetImageEl.style.top = `${state.displayOffsetY}px`;

    overlayEl.style.width = `${state.displayWidth}px`;
    overlayEl.style.height = `${state.displayHeight}px`;
    overlayEl.style.left = `${state.displayOffsetX}px`;
    overlayEl.style.top = `${state.displayOffsetY}px`;
}

function startDrag(kind, data) {
    state.drag = { kind, ...data };
}

function stopDrag() {
    state.drag = null;
}

function svgPoint(event) {
    const point = overlayEl.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    return point.matrixTransform(overlayEl.getScreenCTM().inverse());
}

function createSvgElement(name, attributes = {}) {
    const element = document.createElementNS('http://www.w3.org/2000/svg', name);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
    return element;
}

function getOverlayScale() {
    if (!state.payload || !state.displayWidth || !state.displayHeight) {
        return 1;
    }
    return Math.min(
        state.displayWidth / state.payload.image.width,
        state.displayHeight / state.payload.image.height,
    ) || 1;
}

function pxToSvgUnits(pixels) {
    return pixels / getOverlayScale();
}

function applyScreenSpaceStyles(element, styles = {}) {
    Object.entries(styles).forEach(([key, value]) => {
        if (value == null) return;
        const numericValue = typeof value === 'number' ? pxToSvgUnits(value) : value;
        element.style.setProperty(key, String(numericValue));
    });
    return element;
}

function createHitCircle(cx, cy, radiusPx, className = 'hit-circle') {
    return createSvgElement('circle', {
        cx,
        cy,
        r: pxToSvgUnits(radiusPx),
        class: className,
    });
}

function createHandleGroup(kind, x, y, orientation) {
    const scale = pxToSvgUnits(1);
    const group = createSvgElement('g', {
        class: 'handle-shape',
        transform: `translate(${x}, ${y}) scale(${scale})`,
    });

    let path = '';
    if (orientation === 'horizontal') {
        path = 'M -4,0 L -12,-6 L -12,6 Z M 4,0 L 12,-6 L 12,6 Z';
    } else {
        path = 'M 0,-4 L -6,-12 L 6,-12 Z M 0,4 L -6,12 L 6,12 Z';
    }

    group.appendChild(createSvgElement('path', {
        d: path,
        class: `handle-bg ${kind}`,
    }));
    return group;
}

function getBoundaryByCandidateIndex(candidateIndex) {
    if (!state.payload) return null;
    return state.payload.boundaries.find(boundary => boundary.candidate_index === candidateIndex) || null;
}

function activeLaneCandidateIndex() {
    return state.hoveredLaneIndex ?? state.selectedLaneIndex;
}

function openLaneModal(candidateIndex) {
    const boundary = getBoundaryByCandidateIndex(candidateIndex);
    if (!boundary || !state.payload) return;

    state.selectedLaneIndex = candidateIndex;
    laneModalTitleEl.textContent = t('laneModal.title', candidateIndex);
    laneCategoryInputEl.value = getLaneCategory(boundary);
    laneModalEl.classList.remove('hidden');
    renderLanePreview(boundary);
    renderCategorySuggestions();
    drawOverlay();
    setTimeout(() => laneCategoryInputEl.focus(), 0);
}

function closeLaneModal() {
    laneModalEl.classList.add('hidden');
}

function openResetScopeModal() {
    resetScopeModalEl.classList.remove('hidden');
}

function closeResetScopeModal() {
    resetScopeModalEl.classList.add('hidden');
}

function deleteSelectedLane() {
    if (state.selectedLaneIndex === null) {
        return;
    }
    const deleted = deleteLane(state.selectedLaneIndex);
    if (deleted) {
        markDirty();
        closeLaneModal();
    }
}

function saveLaneModalCategory() {
    const boundary = getBoundaryByCandidateIndex(state.selectedLaneIndex);
    if (!boundary) return;
    setLaneCategory(boundary, laneCategoryInputEl.value);
    markDirty();
    renderAnnotationFields();
    renderStatusPanel();
    drawOverlay();
    closeLaneModal();
}

function renderLanePreview(boundary) {
    const canvas = lanePreviewCanvasEl;
    const context = canvas.getContext('2d');
    const imageWidth = state.payload.image.width;
    const imageHeight = state.payload.image.height;
    const laneWidth = Math.max(1, boundary.right_x - boundary.left_x);
    const padding = Math.round(laneWidth * 0.1);
    const sx = clamp(boundary.left_x - padding, 0, imageWidth);
    const ex = clamp(boundary.right_x + padding, 0, imageWidth);
    const sy = clamp(state.payload.roi.y_start, 0, imageHeight);
    const ey = clamp(state.payload.roi.y_end, sy + 1, imageHeight);
    const sw = Math.max(1, ex - sx);
    const sh = Math.max(1, ey - sy);

    canvas.width = sw;
    canvas.height = sh;
    canvas.style.width = '';
    canvas.style.height = '';
    updateLanePreviewZoom();
    context.clearRect(0, 0, sw, sh);
    context.drawImage(targetImageEl, sx, sy, sw, sh, 0, 0, sw, sh);
    context.strokeStyle = '#2563eb';
    context.lineWidth = 2;
    context.strokeRect(boundary.left_x - sx, 0, laneWidth, sh);
    lanePreviewMetaEl.textContent = t('laneModal.previewMeta', boundary, state.payload.roi);
}

function findLaneAtPoint(point) {
    if (!state.payload) return null;
    const roiTop = state.payload.roi.y_start;
    const roiBottom = state.payload.roi.y_end;
    if (point.y < roiTop || point.y > roiBottom) return null;
    return state.payload.boundaries.find(boundary => point.x >= boundary.left_x && point.x <= boundary.right_x) || null;
}

function findBoundarySpecAtPoint(point) {
    if (!state.payload) return null;
    const roiTop = state.payload.roi.y_start;
    const roiBottom = state.payload.roi.y_end;
    if (point.y < roiTop - 32 || point.y > roiBottom + 32) return null;
    const specs = buildSharedBoundarySpecs(state.payload.boundaries);
    return specs.find(spec => Math.abs(point.x - spec.x) <= 10) || null;
}

function handleOverlayMouseDown(event) {
    if (!state.payload) return;
    const point = svgPoint(event);
    const boundarySpec = findBoundarySpecAtPoint(point);
    if (boundarySpec) {
        event.preventDefault();
        event.stopPropagation();
        startDrag('shared-boundary', { ...boundarySpec, offset: point.x - boundarySpec.x });
    }
}

function handleOverlayClick(event) {
    if (state.drag || !state.payload) return;
    const point = svgPoint(event);
    if (findBoundarySpecAtPoint(point)) return;
    const boundary = findLaneAtPoint(point);
    if (boundary) {
        openLaneModal(boundary.candidate_index);
    }
}

function handleOverlayMouseMove(event) {
    applyDrag(event);
    if (state.drag || !state.payload) return;
    const point = svgPoint(event);
    const boundary = findLaneAtPoint(point);
    const nextHoveredLaneIndex = boundary ? boundary.candidate_index : null;
    if (state.hoveredLaneIndex !== nextHoveredLaneIndex) {
        state.hoveredLaneIndex = nextHoveredLaneIndex;
        drawOverlay();
    }
}

function handleOverlayMouseLeave() {
    stopDrag();
    if (state.hoveredLaneIndex !== null) {
        state.hoveredLaneIndex = null;
        drawOverlay();
    }
}

function deleteLane(candidateIndex) {
    if (!state.payload || state.payload.boundaries.length <= 1) {
        showToast(t('laneModal.minLaneToast'));
        return false;
    }

    const deleteIndex = state.payload.boundaries.findIndex(boundary => boundary.candidate_index === candidateIndex);
    if (deleteIndex === -1) {
        return false;
    }

    state.payload.boundaries.splice(deleteIndex, 1);

    if (deleteIndex > 0 && deleteIndex < state.payload.boundaries.length) {
        const leftLane = state.payload.boundaries[deleteIndex - 1];
        const rightLane = state.payload.boundaries[deleteIndex];
        const sharedX = Math.round((leftLane.right_x + rightLane.left_x) / 2);
        leftLane.right_x = sharedX;
        rightLane.left_x = sharedX;
    }

    state.selectedLaneIndex = null;
    state.hoveredLaneIndex = null;
    normalizeSharedBoundaries();
    renderAnnotationFields();
    renderStatusPanel();
    drawOverlay();
    return true;
}

function drawOverlay() {
    const payload = state.payload;
    if (!payload) return;

    updateStageMetrics();

    const { width, height } = getViewBoxRect();
    overlayEl.setAttribute('viewBox', `0 0 ${width} ${height}`);
    overlayLayerEl.innerHTML = '';

    const roiTop = payload.roi.y_start;
    const roiBottom = payload.roi.y_end;
    const activeCandidateIndex = activeLaneCandidateIndex();
    const topHandleOffset = pxToSvgUnits(18);
    const annotationDotRadius = pxToSvgUnits(7);
    const annotationDotY = Math.max(pxToSvgUnits(12), roiTop - pxToSvgUnits(14));
    const resizeHandleRadius = pxToSvgUnits(5);
    const resizeHandleOffset = pxToSvgUnits(20);
    const edgePadding = pxToSvgUnits(10);

    const sharedBoundarySpecs = buildSharedBoundarySpecs(payload.boundaries);
    sharedBoundarySpecs.forEach(spec => {
        const boundaryLine = applyScreenSpaceStyles(createSvgElement('line', {
            x1: spec.x,
            y1: roiTop,
            x2: spec.x,
            y2: roiBottom,
            class: 'boundary-line',
        }), { 'stroke-width': 2 });

        const hitLine = applyScreenSpaceStyles(createSvgElement('line', {
            x1: spec.x,
            y1: roiTop,
            x2: spec.x,
            y2: roiBottom,
            class: 'hit-line',
        }), { 'stroke-width': 18 });
        hitLine.style.cursor = 'ew-resize';
        hitLine.addEventListener('mousedown', event => {
            event.stopPropagation();
            startDrag('shared-boundary', { ...spec, offset: svgPoint(event).x - spec.x });
        });
        hitLine.addEventListener('click', event => event.stopPropagation());

        overlayLayerEl.append(boundaryLine, hitLine);
    });

    payload.boundaries.forEach(boundary => {
        const isActive = boundary.candidate_index === activeCandidateIndex;
        const fill = applyScreenSpaceStyles(createSvgElement('rect', {
            x: boundary.left_x,
            y: roiTop,
            width: Math.max(1, boundary.right_x - boundary.left_x),
            height: Math.max(1, roiBottom - roiTop),
            class: `lane-fill${isActive ? ' selected' : ''}`,
            fill: `rgba(34, 197, 94, ${isActive ? Math.max(state.maskOpacity / 100, 0.32) : state.maskOpacity / 100})`,
        }), isActive ? { 'stroke-width': 2 } : {});
        fill.style.cursor = 'pointer';
        overlayLayerEl.appendChild(fill);
    });

    const topLine = applyScreenSpaceStyles(createSvgElement('line', { x1: 0, y1: roiTop, x2: width, y2: roiTop, class: 'roi-line' }), { 'stroke-width': 2 });
    const bottomLine = applyScreenSpaceStyles(createSvgElement('line', { x1: 0, y1: roiBottom, x2: width, y2: roiBottom, class: 'roi-line' }), { 'stroke-width': 2 });
    const topHit = applyScreenSpaceStyles(createSvgElement('line', { x1: 0, y1: roiTop, x2: width, y2: roiTop, class: 'hit-line' }), { 'stroke-width': 18 });
    const bottomHit = applyScreenSpaceStyles(createSvgElement('line', { x1: 0, y1: roiBottom, x2: width, y2: roiBottom, class: 'hit-line' }), { 'stroke-width': 18 });
    topHit.style.cursor = 'ns-resize';
    bottomHit.style.cursor = 'ns-resize';
    topHit.addEventListener('mousedown', event => {
        event.stopPropagation();
        startDrag('roi-top', { offset: svgPoint(event).y - payload.roi.y_start });
    });
    topHit.addEventListener('click', event => event.stopPropagation());
    bottomHit.addEventListener('mousedown', event => {
        event.stopPropagation();
        startDrag('roi-bottom', { offset: svgPoint(event).y - payload.roi.y_end });
    });
    bottomHit.addEventListener('click', event => event.stopPropagation());

    overlayLayerEl.append(topLine, bottomLine, topHit, bottomHit);
    overlayLayerEl.appendChild(createHandleGroup('roi', topHandleOffset, roiTop, 'horizontal'));
    overlayLayerEl.appendChild(createHandleGroup('roi', width - topHandleOffset, roiBottom, 'horizontal'));

    payload.boundaries.forEach(boundary => {
        overlayLayerEl.appendChild(applyScreenSpaceStyles(createSvgElement('line', {
            x1: boundary.center_x,
            y1: roiTop,
            x2: boundary.center_x,
            y2: roiBottom,
            class: 'center-line',
        }), {
            'stroke-width': 1.5,
            'stroke-dasharray': `${pxToSvgUnits(4)} ${pxToSvgUnits(4)}`,
        }));
    });

    payload.boundaries.forEach(boundary => {
        const cx = boundary.center_x;
        const dot = applyScreenSpaceStyles(createSvgElement('circle', {
            cx,
            cy: annotationDotY,
            r: annotationDotRadius,
            class: `lane-status-dot ${hasLaneAnnotation(boundary) ? 'annotated' : 'unannotated'}`,
        }), { 'stroke-width': 2 });
        const hitDot = createHitCircle(cx, annotationDotY, 12);
        hitDot.style.cursor = 'pointer';
        [dot, hitDot].forEach(element => {
            element.addEventListener('click', event => {
                event.stopPropagation();
                openLaneModal(boundary.candidate_index);
            });
        });
        overlayLayerEl.append(dot, hitDot);
    });

    sharedBoundarySpecs.forEach(spec => {
        overlayLayerEl.appendChild(createHandleGroup('boundary', spec.x, roiTop, 'vertical'));
        overlayLayerEl.appendChild(createHandleGroup('boundary', spec.x, roiBottom, 'vertical'));
        const topHandleY = Math.max(edgePadding, roiTop - resizeHandleOffset);
        const bottomHandleY = Math.min(height - edgePadding, roiBottom + resizeHandleOffset);
        const resizeTop = applyScreenSpaceStyles(createSvgElement('circle', {
            cx: spec.x,
            cy: topHandleY,
            r: resizeHandleRadius,
            class: 'lane-resize-handle',
        }), { 'stroke-width': 2 });
        const resizeBottom = applyScreenSpaceStyles(createSvgElement('circle', {
            cx: spec.x,
            cy: bottomHandleY,
            r: resizeHandleRadius,
            class: 'lane-resize-handle',
        }), { 'stroke-width': 2 });
        const topHitCircle = createHitCircle(spec.x, topHandleY, 11);
        const bottomHitCircle = createHitCircle(spec.x, bottomHandleY, 11);
        [resizeTop, resizeBottom, topHitCircle, bottomHitCircle].forEach(handle => {
            handle.style.cursor = 'ew-resize';
            handle.addEventListener('mousedown', event => {
                event.stopPropagation();
                startDrag('shared-boundary', { ...spec, offset: svgPoint(event).x - spec.x });
            });
            handle.addEventListener('click', event => event.stopPropagation());
        });
        overlayLayerEl.append(resizeTop, resizeBottom, topHitCircle, bottomHitCircle);
    });
}

function applyDrag(event) {
    if (!state.drag || !state.payload) return;
    const point = svgPoint(event);
    const payload = state.payload;
    const { width, height } = getViewBoxRect();

    if (state.drag.kind === 'roi-top') {
        payload.roi.y_start = clamp(Math.round(point.y - state.drag.offset), 0, payload.roi.y_end - 5);
    } else if (state.drag.kind === 'roi-bottom') {
        payload.roi.y_end = clamp(Math.round(point.y - state.drag.offset), payload.roi.y_start + 5, height);
    } else if (state.drag.kind === 'shared-boundary') {
        const newX = clamp(Math.round(point.x - state.drag.offset), 0, width);

        if (state.drag.leftIndex !== undefined && state.drag.rightIndex !== undefined) {
            const leftLane = payload.boundaries[state.drag.leftIndex];
            const rightLane = payload.boundaries[state.drag.rightIndex];
            const minX = leftLane.left_x + 2;
            const maxX = rightLane.right_x - 2;
            const sharedX = clamp(newX, minX, maxX);
            leftLane.right_x = sharedX;
            rightLane.left_x = sharedX;
            recomputeBoundary(leftLane);
            recomputeBoundary(rightLane);
        } else if (state.drag.laneIndex === 0) {
            const lane = payload.boundaries[0];
            lane.left_x = clamp(newX, 0, lane.right_x - 2);
            recomputeBoundary(lane);
        } else {
            const lane = payload.boundaries[payload.boundaries.length - 1];
            lane.right_x = clamp(newX, lane.left_x + 2, width);
            recomputeBoundary(lane);
        }
    }

    markDirty();
    drawOverlay();
    renderStatusPanel();
    renderAnnotationFields();
}

async function loadImageAt(index, options = {}) {
    if (index < 0 || index >= state.images.length) return;

    const { preserveCurrentDraft = true } = options;
    const currentImageId = getCurrentImageId();
    if (preserveCurrentDraft && currentImageId) {
        saveCurrentDraft();
    }

    const item = state.images[index];
    if (!item) return;

    const payload = await fetchJson(`/api/images/${item.image_id}`);
    const draft = state.draftsByImageId[item.image_id];
    if (draft) {
        applyDraftToPayload(payload, draft);
    }

    state.currentIndex = index;
    state.payload = payload;
    state.selectedLaneIndex = null;
    state.hoveredLaneIndex = null;
    state.importedSessionActive = Boolean(payload.review?.has_imported_session);
    normalizeSharedBoundaries();
    clearDirty();
    renderAnnotationFields();
    currentImageLabelEl.textContent = `${payload.image.image_id} · ${payload.image.source_filename}`;
    notesEl.value = payload.review.notes || '';
    workspaceTitleEl.textContent = t('workspace.title', payload.image.image_id);
    workspaceSubtitleEl.textContent = t('workspace.subtitle', payload.manifest.quality_flag, payload.manifest.manual_review_required);

    targetImageEl.onload = () => {
        updateStageMetrics();
        drawOverlay();
        renderStatusPanel();
    };
    targetImageEl.src = payload.image.image_url;
    renderImageList();
}

async function initializeData(preferredIndex = 0, preferredImageId = null) {
    state.images = await fetchJson('/api/images');
    if (preferredImageId) {
        const matchedIndex = state.images.findIndex(item => item.image_id === preferredImageId);
        state.currentIndex = matchedIndex >= 0 ? matchedIndex : clamp(preferredIndex, 0, Math.max(0, state.images.length - 1));
    } else {
        state.currentIndex = clamp(preferredIndex, 0, Math.max(0, state.images.length - 1));
    }
    renderImageList();
    await loadCategorySuggestions();
    if (state.images.length > 0) {
        await loadImageAt(state.currentIndex, { preserveCurrentDraft: false });
    } else {
        state.payload = null;
        clearDirty();
        renderStatusPanel();
        renderAnnotationFields();
        currentImageLabelEl.textContent = t('noImage');
        notesEl.value = '';
        workspaceTitleEl.textContent = t('workspace.emptyTitle');
        workspaceSubtitleEl.textContent = t('workspace.emptySubtitle');
    }
}

async function saveCurrentReview() {
    if (!state.payload) return;
    const imageId = state.payload.image.image_id;
    const payload = {
        y_start: state.payload.roi.y_start,
        y_end: state.payload.roi.y_end,
        review_status: 'reviewed',
        notes: notesEl.value.trim(),
        annotation: collectAnnotationPayload(),
        write_annotation_csv: writeAnnotationCsvEl.checked,
        write_annotation_jsonl: writeAnnotationJsonlEl.checked,
        boundaries: state.payload.boundaries.map(boundary => ({
            candidate_index: boundary.candidate_index,
            left_x: boundary.left_x,
            right_x: boundary.right_x,
            status: boundary.status,
            notes: boundary.notes || '',
            source: 'manual_review',
            confidence: 'manual',
            auto_left_x: boundary.auto_left_x,
            auto_right_x: boundary.auto_right_x,
            auto_center_x: boundary.auto_center_x,
            auto_estimated_width: boundary.auto_estimated_width,
            auto_status: boundary.auto_status,
            is_manual_added: boundary.is_manual_added,
        })),
    };

    await fetchJson(`/api/images/${imageId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    dropDraft(imageId);
    clearDirty();
    await initializeData(state.currentIndex);
    showToast(t('toast.saveSuccess'));
}

async function reloadSavedState() {
    if (!ensureProceedWithDirty(t('confirm.reloadSaved'))) {
        return;
    }
    const summary = await fetchJson('/api/restore/review-restore-export', { method: 'POST' });
    clearAllDrafts();
    await initializeData(state.currentIndex);
    clearDirty();
    showToast(t('toast.reloadSavedSuccess', summary.restored_image_count, summary.restored_lane_count));
}

async function updateDataset() {
    if (!ensureProceedWithDirty(t('confirm.updateDataset'))) {
        return;
    }
    const previousImageId = getCurrentImageId();
    updateDatasetBtnEl.disabled = true;
    updateDatasetBtnEl.textContent = `${t('controls.updateDataset')}...`;
    try {
        const summary = await fetchJson('/api/dataset/update', { method: 'POST' });
        clearAllDrafts();
        await initializeData(0, previousImageId);
        clearDirty();
        showToast(t('toast.updateDatasetSuccess', summary.image_count, summary.added_quality_rows));
    } finally {
        updateDatasetBtnEl.disabled = false;
        updateDatasetBtnEl.textContent = t('controls.updateDataset');
    }
}

async function importTrainingCsvFromPicker() {
    const [file] = trainingCsvInputEl.files || [];
    if (!file) {
        return;
    }
    if (!ensureProceedWithDirty(t('confirm.importTrainingCsv'))) {
        trainingCsvInputEl.value = '';
        return;
    }
    const summary = await uploadTrainingCsv(file);
    clearAllDrafts();
    await initializeData(0);
    clearDirty();
    showToast(t('toast.importTrainingCsvSuccess', summary.imported_image_count, summary.imported_lane_count));
    trainingCsvInputEl.value = '';
}

async function importReviewRestoreCsvFromPicker() {
    const [file] = restoreCsvInputEl.files || [];
    if (!file) {
        return;
    }
    if (!ensureProceedWithDirty(t('confirm.importReviewRestore'))) {
        restoreCsvInputEl.value = '';
        return;
    }
    const summary = await uploadReviewRestoreCsv(file);
    clearAllDrafts();
    await initializeData(0);
    clearDirty();
    showToast(t('toast.importReviewRestoreSuccess', summary.restored_image_count, summary.restored_lane_count));
    restoreCsvInputEl.value = '';
}

async function resetScope(scope) {
    if (!state.payload) return;
    const isAll = scope === 'all';
    const currentImageId = state.payload.image.image_id;
    const confirmMessage = isAll ? t('resetScope.confirmAll') : t('resetScope.confirmCurrent');
    if (!isAll && !ensureProceedWithDirty(confirmMessage)) {
        return;
    }
    if (isAll && !window.confirm(confirmMessage)) {
        return;
    }
    await fetchJson(`/api/images/${currentImageId}/reset-scope`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scope }),
    });
    if (isAll) {
        clearAllDrafts();
    } else {
        dropDraft(currentImageId);
    }
    closeResetScopeModal();
    await initializeData(scope === 'current' ? state.currentIndex : 0, isAll ? null : currentImageId);
    clearDirty();
    showToast(isAll ? t('resetScope.successAll') : t('resetScope.successCurrent'));
}

notesEl.addEventListener('input', () => {
    markDirty();
});

maskOpacityEl.addEventListener('input', event => {
    state.maskOpacity = Number(event.target.value);
    updateMaskOpacityLabel();
    if (state.payload) {
        drawOverlay();
    }
});

lanePreviewZoomEl.addEventListener('input', event => {
    state.previewZoom = Number(event.target.value);
    updateLanePreviewZoom();
});

writeAnnotationCsvEl.addEventListener('change', renderAnnotationFields);
writeAnnotationJsonlEl.addEventListener('change', renderAnnotationFields);
laneModalBackdropEl.addEventListener('click', closeLaneModal);
laneModalCloseEl.addEventListener('click', closeLaneModal);
laneModalCancelEl.addEventListener('click', closeLaneModal);
laneModalSaveEl.addEventListener('click', saveLaneModalCategory);
deleteLaneBtnEl.addEventListener('click', deleteSelectedLane);
addCategoryBtnEl.addEventListener('click', () => addCurrentCategorySuggestion().catch(error => showToast(error.message)));
languageToggleEl.addEventListener('click', toggleLanguage);
laneCategoryInputEl.addEventListener('keydown', event => {
    if (event.key === 'Enter') {
        event.preventDefault();
        saveLaneModalCategory();
    }
});
window.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !laneModalEl.classList.contains('hidden')) {
        closeLaneModal();
    }
    if (event.key === 'Escape' && !resetScopeModalEl.classList.contains('hidden')) {
        closeResetScopeModal();
    }
});
overlayEl.addEventListener('mousedown', handleOverlayMouseDown);
overlayEl.addEventListener('mousemove', handleOverlayMouseMove);
overlayEl.addEventListener('click', handleOverlayClick);
overlayEl.addEventListener('mouseup', stopDrag);
overlayEl.addEventListener('mouseleave', handleOverlayMouseLeave);
updateDatasetBtnEl.addEventListener('click', () => updateDataset().catch(error => showToast(error.message)));
importReviewRestoreBtnEl.addEventListener('click', () => restoreCsvInputEl.click());
restoreCsvInputEl.addEventListener('change', () => importReviewRestoreCsvFromPicker().catch(error => {
    restoreCsvInputEl.value = '';
    showToast(error.message);
}));
importTrainingCsvBtnEl.addEventListener('click', () => trainingCsvInputEl.click());
trainingCsvInputEl.addEventListener('change', () => importTrainingCsvFromPicker().catch(error => {
    trainingCsvInputEl.value = '';
    showToast(error.message);
}));
reloadSavedBtnEl.addEventListener('click', () => reloadSavedState().catch(error => showToast(error.message)));
exportReviewRestoreBtnEl.addEventListener('click', () => exportReviewRestoreCsv().catch(error => showToast(error.message)));
exportTrainingCsvBtnEl.addEventListener('click', () => exportTrainingCsv().catch(error => showToast(error.message)));
resetBtnEl.addEventListener('click', openResetScopeModal);
resetScopeBackdropEl.addEventListener('click', closeResetScopeModal);
resetScopeCloseEl.addEventListener('click', closeResetScopeModal);
resetCurrentBtnEl.addEventListener('click', () => resetScope('current').catch(error => showToast(error.message)));
resetAllBtnEl.addEventListener('click', () => resetScope('all').catch(error => showToast(error.message)));
saveBtnEl.addEventListener('click', () => saveCurrentReview().catch(error => showToast(error.message)));
prevBtnEl.addEventListener('click', () => loadImageAt(state.currentIndex - 1).catch(error => showToast(error.message)));
nextBtnEl.addEventListener('click', () => loadImageAt(state.currentIndex + 1).catch(error => showToast(error.message)));

window.addEventListener('beforeunload', event => {
    if (!state.isDirty) {
        return;
    }
    event.preventDefault();
    event.returnValue = '';
});

window.addEventListener('resize', () => {
    if (state.payload) {
        updateStageMetrics();
        drawOverlay();
    }
});

async function boot() {
    applyLanguage();
    await initializeData(0);
    updateMaskOpacityLabel();
    updateLanePreviewZoom();
}

(async function init() {
    try {
        await boot();
    } catch (error) {
        showToast(error.message || t('toast.initFailed'));
    }
})();
