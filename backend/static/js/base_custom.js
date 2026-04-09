document.addEventListener("DOMContentLoaded", () => {
    // ── CSRF token ───────────────────────────────────────────────────────
    // Read the CSRF token from Django's cookie and attach it to every
    // HTMX POST/PUT/DELETE request via the hx-headers attribute on <body>.
    const csrfToken = document.cookie
        .split(";")
        .find((c) => c.trim().startsWith("csrftoken="))
        ?.split("=")[1];
    if (csrfToken) {
        document.body.setAttribute(
            "hx-headers",
            JSON.stringify({
                "X-CSRFToken": csrfToken,
            }),
        );
    }

    // ── Modal auto-close on success ──────────────────────────────────────
    // When a modal form POSTs successfully and the server responds with
    // the header HX-Trigger: refreshList, close the open modal.
    document.addEventListener("htmx:afterRequest", (evt) => {
        if (evt.detail.xhr.status === 200) {
            const hxTrigger = evt.detail.xhr.getResponseHeader("HX-Trigger");
            if (hxTrigger && hxTrigger.includes("refreshList")) {
                const modal = document.getElementById("htmx-modal");
                if (modal) modal.remove();
                try {
                    updateMessages();
                } catch (e) {
                    console.error("Failed to update messages after modal submission:", e);
                }
            }
        }
    });

    // ── Flash message refresher ──────────────────────────────────────────
    // After a modal save succeeds, refetch Django's flash messages and
    // inject them into the page without a full reload.
    function updateMessages() {
        // Inline messages panel (persistent, inside page content)
        fetch("/_messages/?format=inline")
            .then((r) => r.text())
            .then((html) => {
                const flash = document.getElementById("flash-messages");
                if (flash) flash.innerHTML = html;
            });
        // Transient toast notifications (appended to <body>)
        fetch("/_messages/?format=toast")
            .then((r) => r.text())
            .then((html) => {
                if (html && html.trim()) {
                    document.body.insertAdjacentHTML("beforeend", html);
                }
            });
    }

    // ── refreshList custom event ─────────────────────────────────────────
    // Fired by HTMX when the server sends HX-Trigger: refreshList.
    // Closes any open modal and refreshes flash messages.
    document.addEventListener("refreshList", () => {
        const modal = document.getElementById("htmx-modal");
        if (modal) modal.remove();
        updateMessages();

        // Clear search/filter by redirecting to clean URL (no query params)
        if (window.location.search) {
            window.location.href = window.location.pathname;
        }
    });
});

// ── TomSelect Searchable Dropdown Initializer ────────────────────────
function initTomSelects() {
    // Select all elements with class .tomselect that haven't been initialized yet
    // Exclude empty form templates used for dynamic formsets
    document.querySelectorAll("select.tomselect:not(.tomselected)").forEach((el) => {
        // Skip if inside hidden formset template
        if (el.closest(".empty-form") || (el.id && el.id.includes("__prefix__"))) return;

        let pText = el.dataset.placeholder;
        if (!pText) {
            const emptyOpt = el.querySelector('option[value=""]');
            if (emptyOpt && emptyOpt.textContent.trim()) {
                pText = emptyOpt.textContent.trim();
            }
        }
        pText = pText || "選択...";

        const instance = new TomSelect(el, {
            create: false,
            maxItems: 1,
            allowEmptyOption: true,
            openOnFocus: true,
            closeAfterSelect: true,
            placeholder: pText,
            searchField: ["text"],
            dropdownClass: "ts-dropdown",
            optionClass: "option",
            dropdownParent: "body",
            plugins: ["dropdown_input"],
            render: {
                option: function (data, escape) {
                    return "<div>" + escape(data.text) + "</div>";
                },
            },
        });

        instance.on("change", () => {
            el.dispatchEvent(new Event("change", { bubbles: true }));
        });

        // Guard against DaisyUI select class leaking into TomSelect wrapper/control.
        el.classList.remove("select");
        if (instance.wrapper) {
            instance.wrapper.classList.remove("select");
        }
        if (instance.control) {
            instance.control.classList.remove("select");
        }

        const syncDropdownPosition = () => {
            if (!instance.dropdown || !instance.control) return;

            const controlRect = instance.control.getBoundingClientRect();
            instance.dropdown.style.position = "fixed";
            instance.dropdown.style.left = `${controlRect.left}px`;
            instance.dropdown.style.top = `${controlRect.bottom + 4}px`;
            instance.dropdown.style.width = `${controlRect.width}px`;
            instance.dropdown.style.zIndex = "9999";
        };

        instance.on("dropdown_open", syncDropdownPosition);

        window.addEventListener("resize", syncDropdownPosition);
        window.addEventListener("scroll", syncDropdownPosition, true);

        instance.control.addEventListener("click", () => {
            if (!instance.isOpen) {
                instance.open();
            }
        });

        // Foolproof fix: completely remove placeholder from control input when an item is selected
        // to prevent any CSS edge cases from squishing the text.
        instance.on("item_add", () => {
            if (instance.control_input) {
                instance.control_input.removeAttribute("placeholder");
            }
        });
        instance.on("item_remove", () => {
            if (instance.control_input && instance.items.length === 0) {
                instance.control_input.setAttribute("placeholder", el.dataset.placeholder || "選択...");
            }
        });

        // Trigger initial state
        if (instance.items.length > 0 && instance.control_input) {
            instance.control_input.removeAttribute("placeholder");
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initTomSelects();
});

// For HTMX modals, we expose this globally
window.initTomSelectsInModal = function () {
    initTomSelects();
};
