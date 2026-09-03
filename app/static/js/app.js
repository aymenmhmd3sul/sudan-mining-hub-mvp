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

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatPrice(price, currency) {
        if (price === null || price === undefined || price === "") {
            return "—";
        }

        const numeric = Number(price);

        if (!Number.isFinite(numeric)) {
            return "—";
        }

        try {
            return new Intl.NumberFormat(
                getLanguage() === "ar" ? "ar" : "en",
                {
                    maximumFractionDigits: 2
                }
            ).format(numeric) + " " + escapeHtml(currency || "");
        } catch (error) {
            return numeric + " " + escapeHtml(currency || "");
        }
    }

    function listingTypeLabel(type) {
        const labels = {
            ASSET: getLanguage() === "ar" ? "أصل" : "Asset",
            EQUIPMENT: getLanguage() === "ar" ? "معدات" : "Equipment",
            SERVICE: getLanguage() === "ar" ? "خدمة" : "Service",
            OPPORTUNITY: getLanguage() === "ar" ? "فرصة" : "Opportunity"
        };

        return labels[type] || type || "";
    }

    function createListingCard(listing) {
        const article = document.createElement("article");
        article.className = "marketplace-card";

        const negotiable =
            listing.is_negotiable
                ? (
                    getLanguage() === "ar"
                        ? "قابل للتفاوض"
                        : "Negotiable"
                )
                : "";

        article.innerHTML = `
            <div class="marketplace-card-top">
                <span class="marketplace-card-type">
                    ${escapeHtml(listingTypeLabel(listing.listing_type))}
                </span>

                ${
                    negotiable
                        ? `<span class="marketplace-card-badge">${escapeHtml(negotiable)}</span>`
                        : ""
                }
            </div>

            <h2 class="marketplace-card-title">
                ${escapeHtml(listing.title)}
            </h2>

            ${
                listing.description
                    ? `
                        <p class="marketplace-card-description">
                            ${escapeHtml(listing.description)}
                        </p>
                    `
                    : ""
            }

            <div class="marketplace-card-footer">
                <strong class="marketplace-card-price">
                    ${formatPrice(listing.price, listing.currency)}
                </strong>

                <span class="marketplace-card-id">
                    #${escapeHtml(listing.id)}
                </span>
            </div>
        `;

        article.addEventListener("click", function () {
            window.location.href =
                "/marketplace/listing/" + encodeURIComponent(listing.id);
        });

        article.setAttribute("role", "link");
        article.setAttribute("tabindex", "0");

        article.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                article.click();
            }
        });

        return article;
    }

    function bindMarketplace() {
        const listingsContainer =
            document.getElementById("marketplaceListings");

        const searchInput =
            document.getElementById("marketplaceSearch");

        const typeFilter =
            document.getElementById("marketplaceType");

        const status =
            document.getElementById("marketplaceStatus");

        const empty =
            document.getElementById("marketplaceEmpty");

        const error =
            document.getElementById("marketplaceError");

        const retry =
            document.getElementById("marketplaceRetry");

        if (
            !listingsContainer ||
            !searchInput ||
            !typeFilter ||
            !status ||
            !empty ||
            !error
        ) {
            return;
        }

        let listings = [];

        function setStatus(text) {
            status.textContent = text;
        }

        function render() {
            const query =
                searchInput.value.trim().toLowerCase();

            const selectedType =
                typeFilter.value;

            const filtered = listings.filter(function (listing) {
                const searchable = [
                    listing.title,
                    listing.description,
                    listing.listing_type,
                    listing.currency
                ]
                    .filter(Boolean)
                    .join(" ")
                    .toLowerCase();

                const matchesSearch =
                    !query || searchable.includes(query);

                const matchesType =
                    selectedType === "ALL" ||
                    listing.listing_type === selectedType;

                return matchesSearch && matchesType;
            });

            listingsContainer.innerHTML = "";

            filtered.forEach(function (listing) {
                listingsContainer.appendChild(
                    createListingCard(listing)
                );
            });

            empty.hidden = filtered.length !== 0;
            error.hidden = true;

            const countText =
                filtered.length === 1
                    ? status.dataset.countSingular
                    : status.dataset.countPlural;

            setStatus(
                filtered.length + " " + countText
            );
        }

        async function loadListings() {
            error.hidden = true;
            empty.hidden = true;
            listingsContainer.innerHTML = "";

            setStatus(status.dataset.loading);

            try {
                const response = await fetch(
                    "/api/v1/listings?limit=100",
                    {
                        method: "GET",
                        headers: {
                            "Accept": "application/json"
                        },
                        credentials: "same-origin"
                    }
                );

                if (!response.ok) {
                    throw new Error(
                        "HTTP " + response.status
                    );
                }

                const data = await response.json();

                if (!Array.isArray(data)) {
                    throw new Error("Invalid listings response");
                }

                listings = data;
                render();

            } catch (requestError) {
                listings = [];
                listingsContainer.innerHTML = "";
                empty.hidden = true;
                error.hidden = false;
                setStatus(status.dataset.error);

                console.error(
                    "Marketplace listings load failed:",
                    requestError
                );
            }
        }

        searchInput.addEventListener("input", render);
        typeFilter.addEventListener("change", render);
        retry?.addEventListener("click", loadListings);

        loadListings();
    }

    function bindInteractions() {
        bindLanguageToggle();
        bindExploreButton();
        bindLoginButton();
        bindModuleCards();
        bindMarketplace();
    }

    document.addEventListener(
        "DOMContentLoaded",
        function () {
            bindInteractions();
        }
    );
})();
