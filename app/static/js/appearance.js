(function () {
    "use strict";

    const STORAGE_KEY = "smh_appearance";

    const DEFAULTS = {
        fontSize: "normal",
        contrast: "normal",
        font: "system",
        theme: "light"
    };

    const FONT_FAMILIES = {
        system: [
            "system-ui",
            "-apple-system",
            "BlinkMacSystemFont",
            "\"Segoe UI\"",
            "sans-serif"
        ].join(", "),
        serif: "Georgia, \"Times New Roman\", serif",
        readable: "\"Segoe UI\", Tahoma, Arial, sans-serif"
    };

    const FONT_SIZES = {
        small: "15px",
        normal: "16px",
        large: "18px"
    };

    function normalizeSettings(value) {
        const source =
            value && typeof value === "object"
                ? value
                : {};

        return {
            fontSize:
                Object.prototype.hasOwnProperty.call(
                    FONT_SIZES,
                    source.fontSize
                )
                    ? source.fontSize
                    : DEFAULTS.fontSize,

            contrast:
                source.contrast === "high"
                    ? "high"
                    : DEFAULTS.contrast,

            font:
                Object.prototype.hasOwnProperty.call(
                    FONT_FAMILIES,
                    source.font
                )
                    ? source.font
                    : DEFAULTS.font,

            theme:
                source.theme === "dark"
                    ? "dark"
                    : DEFAULTS.theme
        };
    }

    function loadSettings() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);

            if (!raw) {
                return { ...DEFAULTS };
            }

            return normalizeSettings(JSON.parse(raw));
        } catch (error) {
            return { ...DEFAULTS };
        }
    }

    function saveSettings(settings) {
        const normalized = normalizeSettings(settings);

        try {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify(normalized)
            );
        } catch (error) {
            // Appearance remains functional for the current page.
        }

        return normalized;
    }

    function applySettings(settings) {
        const normalized = normalizeSettings(settings);
        const root = document.documentElement;

        root.style.setProperty(
            "--font-size-base",
            FONT_SIZES[normalized.fontSize]
        );

        root.style.setProperty(
            "--font-family",
            FONT_FAMILIES[normalized.font]
        );

        root.style.setProperty(
            "--contrast-scale",
            normalized.contrast === "high" ? "1.15" : "1"
        );

        root.dataset.fontSize = normalized.fontSize;
        root.dataset.contrast = normalized.contrast;
        root.dataset.font = normalized.font;
        root.dataset.theme = normalized.theme;

        const themeColor = document.querySelector('meta[name="theme-color"]');
        if (themeColor) {
            themeColor.setAttribute(
                "content",
                normalized.theme === "dark" ? "#05080d" : "#ffffff"
            );
        }

        return normalized;
    }

    function init() {
        const settings = loadSettings();
        applySettings(settings);

        window.SMHAppearance = {
            get: function () {
                return loadSettings();
            },

            set: function (changes) {
                const current = loadSettings();

                const next = normalizeSettings({
                    ...current,
                    ...(changes || {})
                });

                saveSettings(next);
                applySettings(next);

                return next;
            },

            reset: function () {
                const next = saveSettings(DEFAULTS);
                applySettings(next);
                return next;
            }
        };
    }


    function initAppearanceUI() {
        const toggle = document.getElementById("smh-appearance-toggle");
        const panel = document.getElementById("smh-appearance-panel");
        const reset = document.getElementById("smh-appearance-reset");

        if (!toggle || !panel || !reset) {
            return;
        }

        function sync(settings) {
            document.querySelectorAll("[data-appearance-theme]").forEach(function (button) {
                button.setAttribute(
                    "aria-pressed",
                    button.dataset.appearanceTheme === settings.theme ? "true" : "false"
                );
            });

            document.querySelectorAll("[data-appearance-font-size]").forEach(function (button) {
                button.setAttribute(
                    "aria-pressed",
                    button.dataset.appearanceFontSize === settings.fontSize ? "true" : "false"
                );
            });

            document.querySelectorAll("[data-appearance-font]").forEach(function (button) {
                button.setAttribute(
                    "aria-pressed",
                    button.dataset.appearanceFont === settings.font ? "true" : "false"
                );
            });

            document.querySelectorAll("[data-appearance-contrast]").forEach(function (button) {
                button.setAttribute(
                    "aria-pressed",
                    button.dataset.appearanceContrast === settings.contrast ? "true" : "false"
                );
            });
        }

        toggle.addEventListener("click", function () {
            const opening = panel.hidden;

            panel.hidden = !opening;
            toggle.setAttribute("aria-expanded", opening ? "true" : "false");
        });

        document.querySelectorAll("[data-appearance-theme]").forEach(function (button) {
            button.addEventListener("click", function () {
                sync(window.SMHAppearance.set({
                    theme: button.dataset.appearanceTheme
                }));
            });
        });

        document.querySelectorAll("[data-appearance-font-size]").forEach(function (button) {
            button.addEventListener("click", function () {
                sync(window.SMHAppearance.set({
                    fontSize: button.dataset.appearanceFontSize
                }));
            });
        });

        document.querySelectorAll("[data-appearance-font]").forEach(function (button) {
            button.addEventListener("click", function () {
                sync(window.SMHAppearance.set({
                    font: button.dataset.appearanceFont
                }));
            });
        });

        document.querySelectorAll("[data-appearance-contrast]").forEach(function (button) {
            button.addEventListener("click", function () {
                sync(window.SMHAppearance.set({
                    contrast: button.dataset.appearanceContrast
                }));
            });
        });

        reset.addEventListener("click", function () {
            sync(window.SMHAppearance.reset());
        });

        sync(window.SMHAppearance.get());
    }

    init();
    initAppearanceUI();

})();
