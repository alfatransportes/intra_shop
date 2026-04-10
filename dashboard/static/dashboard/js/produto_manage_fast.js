(function () {
    "use strict";

    function qs(selector, root = document) {
        return root.querySelector(selector);
    }

    function qsa(selector, root = document) {
        return Array.from(root.querySelectorAll(selector));
    }

    function getManagementInput(prefix, fieldName) {
        return qs(`#id_${prefix}-${fieldName}`);
    }

    function getTotalForms(prefix) {
        const el = getManagementInput(prefix, "TOTAL_FORMS");
        return el ? parseInt(el.value || "0", 10) : 0;
    }

    function setTotalForms(prefix, value) {
        const el = getManagementInput(prefix, "TOTAL_FORMS");
        if (el) el.value = String(value);
    }

    function replacePrefix(html, prefix, index) {
        const re = new RegExp(`${prefix}-__prefix__`, "g");
        const reId = new RegExp(`id_${prefix}-__prefix__`, "g");
        return html
            .replace(re, `${prefix}-${index}`)
            .replace(reId, `id_${prefix}-${index}`);
    }

    function rowHasPersistedId(row) {
        const idInput = row.querySelector('input[type="hidden"][name$="-id"]');
        return !!(idInput && idInput.value);
    }

    function markRowDeleted(row) {
        const deleteInput = row.querySelector('input[name$="-DELETE"]');
        if (deleteInput) deleteInput.checked = true;

        row.classList.add("pm-removed");

        qsa("input, select, textarea", row).forEach((field) => {
            const isDeleteField = field.name && field.name.endsWith("-DELETE");
            const isIdField = field.name && field.name.endsWith("-id");

            if (!isDeleteField && !isIdField) {
                field.dataset.wasRequired = field.required ? "1" : "0";
                field.required = false;
                field.disabled = true;
            }
        });

        const removeBtn = qs(".js-remove-row", row);
        const undoBtn = qs(".js-undo-remove", row);

        if (removeBtn) removeBtn.classList.add("d-none");
        if (undoBtn) undoBtn.classList.remove("d-none");

        row.style.display = "none";
    }

    function unmarkRowDeleted(row) {
        const deleteInput = row.querySelector('input[name$="-DELETE"]');
        if (deleteInput) deleteInput.checked = false;

        row.classList.remove("pm-removed");

        qsa("input, select, textarea", row).forEach((field) => {
            const isDeleteField = field.name && field.name.endsWith("-DELETE");
            const isIdField = field.name && field.name.endsWith("-id");

            if (!isDeleteField && !isIdField) {
                field.disabled = false;
                if (field.dataset.wasRequired === "1") {
                    field.required = true;
                }
            }
        });

        const removeBtn = qs(".js-remove-row", row);
        const undoBtn = qs(".js-undo-remove", row);

        if (removeBtn) removeBtn.classList.remove("d-none");
        if (undoBtn) undoBtn.classList.add("d-none");

        row.style.display = "";
    }

    function reindexRows(containerSelector, prefix, rowSelector) {
        const container = qs(containerSelector);
        if (!container) return;

        const rows = qsa(rowSelector, container);

        rows.forEach((row, index) => {
            row.dataset.formIndex = String(index);

            qsa("input, select, textarea, label", row).forEach((el) => {
                ["name", "id", "for"].forEach((attr) => {
                    const value = el.getAttribute(attr);
                    if (!value) return;

                    const replaced = value.replace(
                        new RegExp(`${prefix}-(\\d+|__prefix__)`),
                        `${prefix}-${index}`
                    );
                    el.setAttribute(attr, replaced);
                });
            });
        });

        setTotalForms(prefix, rows.length);
    }

    function ensureEmptyState(containerSelector, rowSelector, emptyId, message) {
        const container = qs(containerSelector);
        if (!container) return;

        const visibleRows = qsa(rowSelector, container).filter((row) => row.style.display !== "none");

        let emptyState = qs(`#${emptyId}`);
        if (visibleRows.length === 0) {
            if (!emptyState) {
                emptyState = document.createElement("div");
                emptyState.id = emptyId;
                emptyState.className = "pm-empty-state";
                emptyState.textContent = message;
                container.appendChild(emptyState);
            }
        } else if (emptyState) {
            emptyState.remove();
        }
    }

    function createRowFromTemplate(templateId, prefix, containerSelector, rowSelector) {
        const template = qs(`#${templateId}`);
        const container = qs(containerSelector);
        if (!template || !container) return null;

        const currentTotal = getTotalForms(prefix);
        const html = replacePrefix(template.innerHTML, prefix, currentTotal);

        const temp = document.createElement("div");
        temp.innerHTML = html.trim();
        const row = temp.firstElementChild;

        if (!row) return null;

        container.appendChild(row);
        setTotalForms(prefix, currentTotal + 1);

        return row;
    }

    function handleRemoveClick(row, prefix, containerSelector, rowSelector, emptyId, emptyMessage) {
        if (rowHasPersistedId(row)) {
            markRowDeleted(row);
            ensureEmptyState(containerSelector, rowSelector, emptyId, emptyMessage);
            return;
        }

        row.remove();
        reindexRows(containerSelector, prefix, rowSelector);
        ensureEmptyState(containerSelector, rowSelector, emptyId, emptyMessage);
    }

    function bindRemoveUndo(scope) {
        qsa(".js-remove-row", scope).forEach((btn) => {
            if (btn.dataset.bound === "1") return;
            btn.dataset.bound = "1";

            btn.addEventListener("click", function () {
                const row = btn.closest(".js-variacao-row, .js-imagem-row");
                if (!row) return;

                if (row.classList.contains("js-variacao-row")) {
                    handleRemoveClick(
                        row,
                        window.produtoRapidoConfig.variacoesPrefix,
                        "#variacoes-container",
                        ".js-variacao-row",
                        "variacoes-empty-state",
                        "Nenhuma variação cadastrada."
                    );
                } else {
                    handleRemoveClick(
                        row,
                        window.produtoRapidoConfig.imagensPrefix,
                        "#imagens-container",
                        ".js-imagem-row",
                        "imagens-empty-state",
                        "Nenhuma imagem cadastrada."
                    );
                }
            });
        });

        qsa(".js-undo-remove", scope).forEach((btn) => {
            if (btn.dataset.bound === "1") return;
            btn.dataset.bound = "1";

            btn.addEventListener("click", function () {
                const row = btn.closest(".js-variacao-row, .js-imagem-row");
                if (!row) return;

                unmarkRowDeleted(row);

                if (row.classList.contains("js-variacao-row")) {
                    ensureEmptyState(
                        "#variacoes-container",
                        ".js-variacao-row",
                        "variacoes-empty-state",
                        "Nenhuma variação cadastrada."
                    );
                } else {
                    ensureEmptyState(
                        "#imagens-container",
                        ".js-imagem-row",
                        "imagens-empty-state",
                        "Nenhuma imagem cadastrada."
                    );
                }
            });
        });
    }

    function bindImagePreview(scope) {
    qsa('input[type="file"]', scope).forEach((input) => {
        if (input.dataset.previewBound === "1") return;
        input.dataset.previewBound = "1";

        input.addEventListener("change", function () {
            const row = input.closest(".js-imagem-row");
            if (!row) return;

            const preview = qs(".js-image-preview", row);
            const placeholder = qs(".js-image-placeholder", row);

            if (!preview) return;

            const file = input.files && input.files[0];
            if (!file) {
                preview.src = "";
                preview.classList.add("d-none");
                if (placeholder) placeholder.classList.remove("d-none");
                return;
            }

            const reader = new FileReader();
            reader.onload = function (e) {
                preview.src = e.target.result;
                preview.classList.remove("d-none");
                if (placeholder) placeholder.classList.add("d-none");
            };
            reader.readAsDataURL(file);
        });
    });
}

function updatePublishCheckboxState() {
    const ativoField = document.querySelector("#id_ativo");
    if (!ativoField) return;

    const usaVariacoes = document.querySelector("#id_usa_variacoes");
    const quantidadeField = document.querySelector("#id_quantidade");

    const imageRows = Array.from(document.querySelectorAll(".js-imagem-row"));
    const variationRows = Array.from(document.querySelectorAll(".js-variacao-row"));

    const hasImages = imageRows.some((row) => {
        if (row.style.display === "none") return false;

        const deleteInput = row.querySelector('input[name$="-DELETE"]');
        if (deleteInput && deleteInput.checked) return false;

        const fileInput = row.querySelector('input[type="file"]');
        const hiddenId = row.querySelector('input[name$="-id"]');

        const hasNewFile = fileInput && fileInput.files && fileInput.files.length > 0;
        const hasExisting = hiddenId && hiddenId.value;

        return !!(hasNewFile || hasExisting);
    });

    let canPublish = hasImages;

    if (usaVariacoes && usaVariacoes.checked) {
        const hasValidVariation = variationRows.some((row) => {
            if (row.style.display === "none") return false;

            const deleteInput = row.querySelector('input[name$="-DELETE"]');
            if (deleteInput && deleteInput.checked) return false;

            const ativo = row.querySelector('input[name$="-ativo"]');
            const qtd = row.querySelector('input[name$="-quantidade"]');

            return ativo && ativo.checked && qtd && parseInt(qtd.value || "0", 10) > 0;
        });

        canPublish = canPublish && hasValidVariation;
    } else {
        const qtd = quantidadeField ? parseInt(quantidadeField.value || "0", 10) : 0;
        canPublish = canPublish && qtd > 0;
    }

    if (!canPublish) {
        ativoField.checked = false;
    }
}


    function toggleVariacoes() {
        const usaVariacoes = qs(`#${window.produtoRapidoConfig.usaVariacoesFieldId}`);
        const variacoesCard = qs(".js-variacoes-card");
        const simpleStock = qs(".js-simple-stock");

        if (!usaVariacoes || !variacoesCard || !simpleStock) return;

        if (usaVariacoes.checked) {
            variacoesCard.style.display = "";
            simpleStock.style.display = "none";
        } else {
            variacoesCard.style.display = "none";
            simpleStock.style.display = "";
        }
    }

    function bindAddButtons() {
        const addVariacaoBtn = qs("#add-variacao-row");
        const addImagemBtn = qs("#add-imagem-row");

        if (addVariacaoBtn) {
            addVariacaoBtn.addEventListener("click", function () {
                const row = createRowFromTemplate(
                    "variacao-empty-row-template",
                    window.produtoRapidoConfig.variacoesPrefix,
                    "#variacoes-container",
                    ".js-variacao-row"
                );
                if (!row) return;

                bindRemoveUndo(row);
                ensureEmptyState(
                    "#variacoes-container",
                    ".js-variacao-row",
                    "variacoes-empty-state",
                    "Nenhuma variação cadastrada."
                );
            });
        }

        if (addImagemBtn) {
            addImagemBtn.addEventListener("click", function () {
                const row = createRowFromTemplate(
                    "imagem-empty-row-template",
                    window.produtoRapidoConfig.imagensPrefix,
                    "#imagens-container",
                    ".js-imagem-row"
                );
                if (!row) return;

                bindRemoveUndo(row);
                bindImagePreview(row);
                ensureEmptyState(
                    "#imagens-container",
                    ".js-imagem-row",
                    "imagens-empty-state",
                    "Nenhuma imagem cadastrada."
                );
            });
        }
    }

    function clearHiddenRequiredBeforeSubmit() {
        const form = qs("#produto-rapido-form");
        if (!form) return;

        form.addEventListener("submit", function () {
            qsa(".js-variacao-row, .js-imagem-row", form).forEach((row) => {
                if (row.style.display === "none") {
                    qsa("input, select, textarea", row).forEach((field) => {
                        const isDeleteField = field.name && field.name.endsWith("-DELETE");
                        const isIdField = field.name && field.name.endsWith("-id");

                        if (!isDeleteField && !isIdField) {
                            field.required = false;
                        }
                    });
                }
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
      document.addEventListener("input", updatePublishCheckboxState);
      document.addEventListener("change", updatePublishCheckboxState);
        updatePublishCheckboxState();
        bindRemoveUndo(document);
        bindImagePreview(document);
        bindAddButtons();
        clearHiddenRequiredBeforeSubmit();
        toggleVariacoes();

        const usaVariacoes = qs(`#${window.produtoRapidoConfig.usaVariacoesFieldId}`);
        if (usaVariacoes) {
            usaVariacoes.addEventListener("change", toggleVariacoes);
        }

        ensureEmptyState(
            "#variacoes-container",
            ".js-variacao-row",
            "variacoes-empty-state",
            "Nenhuma variação cadastrada."
        );

        ensureEmptyState(
            "#imagens-container",
            ".js-imagem-row",
            "imagens-empty-state",
            "Nenhuma imagem cadastrada."
        );
    });
})();