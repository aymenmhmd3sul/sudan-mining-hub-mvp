(function () {
    "use strict";

    function getLanguage() {
        const match = document.cookie.match(
            /(?:^|;\s*)language=([^;]+)/
        );

        const value = match
            ? decodeURIComponent(match[1])
            : "ar";

        return value === "en" ? "en" : "ar";
    }

    function setLanguage(lang) {
        const normalized = lang === "en" ? "en" : "ar";

        document.cookie =
            "language=" +
            encodeURIComponent(normalized) +
            "; Path=/; SameSite=Lax";

        window.location.reload();
    }

    function bindLanguageToggle() {
        const languageToggle =
            document.getElementById("languageToggle");

        if (!languageToggle) {
            return;
        }

        languageToggle.addEventListener("click", function () {
            const current = getLanguage();
            setLanguage(current === "ar" ? "en" : "ar");
        });
    }

    function bindExploreButton() {
        const exploreBtn =
            document.getElementById("exploreBtn");

        if (!exploreBtn) {
            return;
        }

        exploreBtn.addEventListener("click", function () {
            document
                .getElementById("gatewayModules")
                ?.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
        });
    }

    function bindLoginButton() {
        const loginBtn =
            document.getElementById("loginBtn");

        if (!loginBtn) {
            return;
        }

        loginBtn.addEventListener("click", function () {
            window.location.href = "/login";
        });
    }

    function bindModuleCards() {
        const moduleRoutes = {
            marketplace: "/marketplace",
            requests: "/requests",
            negotiation: "/negotiation",
            services: "/services"
        };

        document
            .querySelectorAll(".module-card")
            .forEach(function (card) {
                card.addEventListener("click", function () {
                    const module = card.dataset.module;
                    const route = moduleRoutes[module];

                    if (route) {
                        window.location.href = route;
                    }
                });
            });
    }

    function bindInteractions() {
        bindLanguageToggle();
        bindExploreButton();
        bindLoginButton();
        bindModuleCards();
    }

    document.addEventListener("DOMContentLoaded", function () {
        bindInteractions();
    });
})();
