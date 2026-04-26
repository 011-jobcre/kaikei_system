/**
 * base_custom.js
 * Global JavaScript for the Kaikei (Accounting) System.
 * Manages HTMX integration, TomSelect searchable dropdowns, and UI state.
 */

// --- Global Constants & Helpers ---

const ACCOUNT_LABEL_REGEX = /^(\S+)\s+(.*?)(\s+\[.*\]|$)/;
const SEARCH_META_SEPARATOR = "|||";

/**
 * Parses a standard account label "CODE NAME [FURIGANA]" or "CODE NAME"
 * and extracts the displayable name part.
 */
function parseAccountLabel(text) {
    if (!text) return "";
    const trimmed = text.trim();
    if (trimmed.includes(SEARCH_META_SEPARATOR)) {
        return trimmed.split(SEARCH_META_SEPARATOR)[0].trim();
    }
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

    initTomSelects();

    // 5. Sync TomSelect on HTMX Swaps
    // If HTMX updates the content of a select (e.g., dependent dropdowns),
    // we must tell TomSelect to refresh its internal option list.
    document.addEventListener("htmx:afterSwap", (event) => {
        const target = event.detail.target;
        // Check if the target itself is a select or contains selects
        const selects = target.tagName === "SELECT" ? [target] : target.querySelectorAll("select.tomselected");

        selects.forEach((select) => {
            if (select.tomselect) {
                const instance = select.tomselect;
                const currentValue = select.value;
                instance.clearOptions();
                instance.sync(); // Reads new <option> tags from the real select
                if (currentValue) {
                    instance.setValue(currentValue, true);
                }
                // Preserve data-row and data-col for grid navigation
                if (instance.control_input) {
                    if (select.dataset.row !== undefined) instance.control_input.dataset.row = select.dataset.row;
                    if (select.dataset.col !== undefined) instance.control_input.dataset.col = select.dataset.col;
                }
            }
        });
    });
});

function initTomSelects(container) {
    const root = container || document;
    const selects = root.querySelectorAll("select.tomselect");

    selects.forEach((el) => {
        if (el.closest(".empty-form") || (el.id && el.id.includes("__prefix__"))) return;
        if (el.tomselect) return;
        if (el.classList.contains("tomselected")) return;

        const emptyOptionText = el.querySelector('option[value=""]')?.textContent?.trim() || "";
        const placeholder = el.dataset.placeholder || emptyOptionText || "---------";

        const instance = new TomSelect(el, {
            create: false,
            maxItems: 1,
            allowEmptyOption: true,
            openOnFocus: true,
            closeAfterSelect: true,
            selectOnTab: true,
            placeholder: placeholder,
            searchField: ["text"],
            dropdownClass: "ts-dropdown",
            optionClass: "option",
            dropdownParent: "body",
            plugins: ["dropdown_input", "clear_button"],
            render: {
                option: (data, escape) => {
                    if (!data.value) {
                        return `<div class="hidden" aria-hidden="true"></div>`;
                    }
                    const text = el.dataset.noParse === "true" ? data.text : parseAccountLabel(data.text);
                    return `<div class="px-2 py-1">${escape(text)}</div>`;
                },
                item: (data, escape) => {
                    if (!data.value) {
                        return `<div></div>`;
                    }
                    const text = el.dataset.noParse === "true" ? data.text : parseAccountLabel(data.text);
                    return `<div>${escape(text)}</div>`;
                },
            },
        });

        instance.on("change", (val) => {
            el.value = val;
            el.dispatchEvent(new Event("change", { bubbles: true }));
        });

        el.classList.add("tomselected");
        el.classList.remove("select");
        if (el.classList.contains("border-error") && instance.control) {
            instance.control.classList.add("border-error");
        }
        if (instance.wrapper) instance.wrapper.classList.remove("select");
        if (instance.control) instance.control.classList.remove("select");
        if (instance.control_input) {
            if (el.dataset.row !== undefined) instance.control_input.dataset.row = el.dataset.row;
            if (el.dataset.col !== undefined) instance.control_input.dataset.col = el.dataset.col;
        }

        const syncDropdownPosition = () => {
            if (!instance.dropdown || !instance.control) return;
            const controlRect = instance.control.getBoundingClientRect();
            if (controlRect.width === 0) return;

            Object.assign(instance.dropdown.style, {
                position: "fixed",
                left: `${controlRect.left}px`,
                top: `${controlRect.bottom + 2}px`,
                width: `${controlRect.width}px`,
                minWidth: `${controlRect.width}px`,
                zIndex: "9999",
            });
        };

        instance.on("dropdown_open", syncDropdownPosition);
        window.addEventListener("resize", syncDropdownPosition);
        window.addEventListener("scroll", syncDropdownPosition, true);

        if (instance.control) {
            instance.control.addEventListener("click", () => {
                if (!instance.isOpen) instance.open();
            });
        }

        const updatePlaceholder = () => {
            if (!instance.control_input) return;
            if (instance.items.length > 0) {
                instance.control_input.removeAttribute("placeholder");
            } else {
                instance.control_input.setAttribute("placeholder", el.dataset.placeholder || placeholder);
            }
        };

        instance.on("item_add", updatePlaceholder);
        instance.on("item_remove", updatePlaceholder);
        if (!el.value) {
            instance.clear(true);
        }
        updatePlaceholder();
    });
}

window.initTomSelectsInModal = (container) => initTomSelects(container);

// --- Alpine.js Date Range Picker Component ---
document.addEventListener("alpine:init", () => {
    Alpine.data("dateRangePicker", (initialFrom, initialTo) => ({
        dateFrom: initialFrom || "",
        dateTo: initialTo || "",
        fiscalYear: 0,
        selectionState: 0,
        years: [],

        init() {
            // Generate year list (Current year + 1 down to 15 years ago)
            const currentYear = new Date().getFullYear();
            for (let i = currentYear; i >= currentYear - 15; i--) this.years.push(i);
            const d = this.dateFrom ? new Date(this.dateFrom) : new Date();
            const year = d.getFullYear();
            const month = d.getMonth() + 1;
            this.fiscalYear = month >= 4 ? year : year - 1;
        },

        /**
         * Updates the base fiscal year and resets to full year for that period.
         */
        setYear(year) {
            this.fiscalYear = parseInt(year);
            this.setFullYear();
        },

        setMonth(monthIdx) {
            const range = this.calcMonthRange(monthIdx);
            if (this.selectionState === 0) {
                this.dateFrom = range.from;
                this.dateTo = range.to;
                this.selectionState = 1;
            } else {
                const start = new Date(this.dateFrom);
                const target = new Date(range.from);
                if (target >= start) {
                    this.dateTo = range.to;
                } else {
                    this.dateFrom = range.from;
                }
                this.selectionState = 0;
            }
        },

        resetAll() {
            // 1. Reset Alpine state
            const now = new Date();
            const year = now.getFullYear();
            const currentMonth = now.getMonth() + 1;
            this.fiscalYear = currentMonth >= 4 ? year : year - 1;
            this.dateFrom = "";
            this.dateTo = "";
            this.selectionState = 0;

            // 2. Reset parent form inputs (Keyword, etc.)
            const form = this.$el.closest("form");
            if (form) {
                form.reset();
                // Manually clear all text inputs just in case
                form.querySelectorAll('input[type="text"]').forEach((i) => (i.value = ""));
                // Handle standard selects
                form.querySelectorAll("select").forEach((s) => (s.selectedIndex = 0));

                // 3. Handle TomSelect if present
                form.querySelectorAll(".tomselected").forEach((s) => {
                    if (s.tomselect) s.tomselect.clear();
                });
            }
        },

        resetAndReload() {
            // Reset form and reload page to refresh table data
            this.resetAll();
            window.location.href = window.location.pathname;
        },

        calcMonthRange(monthIdx) {
            let targetMonth = monthIdx + 4; // Index 0 is April
            let targetYear = parseInt(this.fiscalYear); // Ensure fiscalYear is a number

            if (targetMonth > 12) {
                targetMonth -= 12;
                targetYear += 1;
            }

            const firstDay = new Date(targetYear, targetMonth - 1, 1);
            const lastDay = new Date(targetYear, targetMonth, 0);
            return {
                from: this.formatDate(firstDay),
                to: this.formatDate(lastDay),
            };
        },

        setFullYear() {
            const year = parseInt(this.fiscalYear);
            this.dateFrom = `${year}-04-01`;
            this.dateTo = `${year + 1}-03-31`;
            this.selectionState = 0;
        },

        formatDate(date) {
            const y = date.getFullYear();
            const m = String(date.getMonth() + 1).padStart(2, "0");
            const d = String(date.getDate()).padStart(2, "0");
            return `${y}-${m}-${d}`;
        },

        isMonthActive(monthIdx) {
            if (!this.dateFrom || !this.dateTo) return false;
            const range = this.calcMonthRange(monthIdx);
            const start = new Date(this.dateFrom);
            const end = new Date(this.dateTo);
            const targetStart = new Date(range.from);
            const targetEnd = new Date(range.to);
            return targetStart >= start && targetEnd <= end;
        },
    }));
});
