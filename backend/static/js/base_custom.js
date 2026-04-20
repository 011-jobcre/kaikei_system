/**
 * base_custom.js
 * Global JavaScript for the Kaikei (Accounting) System.
 * Manages HTMX integration, TomSelect searchable dropdowns, and UI state.
 */

// --- Global Constants & Helpers ---

const ACCOUNT_LABEL_REGEX = /^(\S+)\s+(.*?)(\s+\[.*\]|$)/;

/**
 * Parses a standard account label "CODE NAME [FURIGANA]" or "CODE NAME"
 * and extracts the displayable name part.
 */
function parseAccountLabel(text) {
    if (!text) return "";
    const trimmed = text.trim();
    const match = trimmed.match(ACCOUNT_LABEL_REGEX);
    return match ? match[2].trim() : trimmed;
}

/**
 * Updates Django's flash messages container by fetching latest messages via AJAX.
 */
function updateFlashMessages() {
    const flash = document.getElementById("flash-messages");
    if (!flash) return;

    fetch("/_messages/?format=inline")
        .then((r) => r.text())
        .then((html) => {
            flash.innerHTML = html;
        });
}

// --- HTMX Global Setup ---

document.addEventListener("DOMContentLoaded", () => {
    // 1. CSRF Token Injection
    // Attach CSRF token from cookies to all HTMX-driven non-GET requests.
    const csrfToken = document.cookie
        .split(";")
        .find((c) => c.trim().startsWith("csrftoken="))
        ?.split("=")[1];

    if (csrfToken) {
        document.body.setAttribute("hx-headers", JSON.stringify({ "X-CSRFToken": csrfToken }));
    }

    // 2. Modal Management (Success Auto-Close)
    // When a modal form succeeds (server sends HX-Trigger: refreshList), close it and refresh flash.
    document.addEventListener("htmx:afterRequest", (evt) => {
        if (evt.detail.xhr.status === 200) {
            const hxTrigger = evt.detail.xhr.getResponseHeader("HX-Trigger");
            if (hxTrigger && hxTrigger.includes("refreshList")) {
                const modal = document.getElementById("htmx-modal");
                if (modal) modal.remove();
                updateFlashMessages();
            }
        }
    });

    // 3. refreshList Custom Event
    // Centralized handler for clearing filters and refreshing the UI.
    document.addEventListener("refreshList", () => {
        const modal = document.getElementById("htmx-modal");
        if (modal) modal.remove();
        updateFlashMessages();

        // If query parameters exist, redirect to a clean URL (clear search/filter)
        if (window.location.search) {
            window.location.href = window.location.pathname;
        }
    });

    // 4. TomSelect Global HTMX Integration
    // Automatically initialize/re-initialize dropdowns whenever HTMX loads new content.
    if (typeof htmx !== "undefined") {
        htmx.onLoad((content) => {
            initTomSelects(content);
        });
    }

    // Initial load call
    initTomSelects();
});

// --- TomSelect Searchable Dropdowns ---

/**
 * Initializes TomSelect for all <select> elements with class .tomselect.
 * @param {HTMLElement} container - Optional scope to search for select elements.
 */
function initTomSelects(container) {
    const root = container || document;
    const selects = root.querySelectorAll("select.tomselect:not(.tomselected)");

    if (selects.length > 0) {
        console.debug(`[TomSelect] Initializing ${selects.length} elements in`, root);
    }

    selects.forEach((el) => {
        // Guard: Skip if inside hidden formset templates or dynamic __prefix__ elements
        if (el.closest(".empty-form") || (el.id && el.id.includes("__prefix__"))) return;

        // Determine placeholder text
        let placeholder = el.dataset.placeholder;
        if (!placeholder) {
            const emptyOpt = el.querySelector('option[value=""]');
            if (emptyOpt && emptyOpt.textContent.trim()) {
                placeholder = emptyOpt.textContent.trim();
            }
        }
        placeholder = placeholder || "選択...";

        // Initialize TomSelect instance
        const instance = new TomSelect(el, {
            create: false,
            maxItems: 1,
            allowEmptyOption: true,
            openOnFocus: true,
            closeAfterSelect: true,
            placeholder: placeholder,
            searchField: ["text"],
            dropdownClass: "ts-dropdown",
            optionClass: "option",
            dropdownParent: "body",
            plugins: ["dropdown_input"],
            render: {
                option: (data, escape) => {
                    const text = el.dataset.noParse === "true" ? data.text : parseAccountLabel(data.text);
                    return `<div class="px-2 py-1">${escape(text)}</div>`;
                },
                item: (data, escape) => {
                    const text = el.dataset.noParse === "true" ? data.text : parseAccountLabel(data.text);
                    return `<div>${escape(text)}</div>`;
                },
            },
        });

        // Event: Sync TomSelect changes back to original <select> for HTMX/Forms
        instance.on("change", () => {
            el.dispatchEvent(new Event("change", { bubbles: true }));
        });

        // Mark as initialized
        el.classList.add("tomselected");

        // Styling: Sync error borders level from Select to TomSelect control
        if (el.classList.contains("border-error") && instance.control) {
            instance.control.classList.add("border-error");
        }

        // Styling: Guard against DaisyUI base classes leaking into TomSelect components
        el.classList.remove("select");
        if (instance.wrapper) instance.wrapper.classList.remove("select");
        if (instance.control) instance.control.classList.remove("select");

        // UI: Dynamic Dropdown Positioning (Fixes overflow issues in modals/tables)
        const syncDropdownPosition = () => {
            if (!instance.dropdown || !instance.control) return;
            const controlRect = instance.control.getBoundingClientRect();
            Object.assign(instance.dropdown.style, {
                position: "fixed",
                left: `${controlRect.left}px`,
                top: `${controlRect.bottom + 4}px`,
                width: `${controlRect.width}px`,
                minWidth: `${controlRect.width}px`,
                zIndex: "9999",
            });
        };

        instance.on("dropdown_open", syncDropdownPosition);
        window.addEventListener("resize", syncDropdownPosition);
        window.addEventListener("scroll", syncDropdownPosition, true);

        // UI: Ensure single-click open behavior
        instance.control.addEventListener("click", () => {
            if (!instance.isOpen) instance.open();
        });

        // UI: Placeholder Management (Fixes CSS squishing in some themes)
        const updatePlaceholder = () => {
            if (!instance.control_input) return;
            if (instance.items.length > 0) {
                instance.control_input.removeAttribute("placeholder");
            } else {
                instance.control_input.setAttribute("placeholder", placeholder);
            }
        };

        instance.on("item_add", updatePlaceholder);
        instance.on("item_remove", updatePlaceholder);
        updatePlaceholder(); // Trigger initial state
    });
}

// Global exposure for specific manual triggers (rarely needed with htmx:onLoad)
window.initTomSelectsInModal = (container) => initTomSelects(container);
