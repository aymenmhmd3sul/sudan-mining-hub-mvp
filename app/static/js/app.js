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
    const guidance =
        document.getElementById("gatewayInformation");

    if (!exploreBtn || !guidance) {
        return;
    }

    exploreBtn.addEventListener("click", function () {
        guidance.hidden = false;
        guidance.scrollIntoView({
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

    function bindRegisterButton() {
    const registerBtn =
        document.getElementById("registerBtn");

    if (!registerBtn) {
        return;
    }

    registerBtn.addEventListener("click", function () {
        window.location.href = "/register";
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

    window.escapeHtml = function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    };

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

        const images = Array.isArray(listing.images)
            ? listing.images
                .filter(function (image) {
                    return image &&
                        image.media_type === "IMAGE" &&
                        image.url;
                })
                .sort(function (a, b) {
                    return (a.sort_order || 0) - (b.sort_order || 0);
                })
            : [];

        const imageMarkup = images.length
            ? `
                <div class="marketplace-card-media">
                    <img
                        src="${escapeHtml(images[0].url)}"
                        alt="${escapeHtml(listing.title)}"
                        loading="lazy"
                    >
                </div>
            `
            : `
                <div class="marketplace-card-media marketplace-card-media-empty" aria-hidden="true">
                    <span>SMH</span>
                </div>
            `;

        article.innerHTML = `
            ${imageMarkup}

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

    function bindRequestsPage() {
        const list = document.getElementById("requestsList");
        const status = document.getElementById("requestsStatus");
        const refresh = document.getElementById("requestsRefresh");

        if (!list || !status) {
            return;
        }

        const isEnglish = getLanguage() === "en";

        const labels = isEnglish
            ? {
                loading: "Loading requests...",
                refresh: "Refresh",
                empty: "No open buyer requests are available.",
                error: "Unable to load buyer requests.",
                login: "Please sign in with a merchant or admin account.",
                location: "Target location",
                currency: "Currency",
                status: "Status",
                buyer: "Buyer",
                items: "Requested items"
            }
            : {
                loading: "جاري تحميل الطلبات...",
                refresh: "تحديث",
                empty: "لا توجد طلبات مشترين مفتوحة حاليًا.",
                error: "تعذر تحميل طلبات المشترين.",
                login: "يرجى تسجيل الدخول بحساب تاجر أو مشرف.",
                location: "موقع الاستهداف",
                currency: "العملة",
                status: "الحالة",
                buyer: "المشتري",
                items: "العناصر المطلوبة"
            };

        if (refresh) {
            refresh.textContent = labels.refresh;
        }

        function escape(value) {
            return window.escapeHtml
                ? window.escapeHtml(String(value ?? ""))
                : String(value ?? "")
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
        }

        function render(requests) {
            list.innerHTML = "";

            if (!requests.length) {
                list.innerHTML =
                    '<div class="requests-empty">' +
                    escape(labels.empty) +
                    "</div>";
                status.textContent = labels.empty;
                return;
            }

            status.textContent = isEnglish
                ? requests.length + " open request(s)"
                : requests.length + " طلب مفتوح";

            requests.forEach(function (item) {
                const card = document.createElement("article");
                card.className = "requests-card";

                const items = Array.isArray(item.items)
                    ? item.items
                    : [];

                const itemsHtml = items.length
                    ? '<ul class="requests-items">' +
                      items.map(function (entry) {
                          return (
                              "<li><strong>" +
                              escape(entry.title) +
                              "</strong>" +
                              (entry.quantity
                                  ? " — " + escape(entry.quantity)
                                  : "") +
                              (entry.unit
                                  ? " " + escape(entry.unit)
                                  : "") +
                              "</li>"
                          );
                      }).join("") +
                      "</ul>"
                    : "";

                card.innerHTML =
                    "<h2>" + escape(item.title) + "</h2>" +
                    "<p>" + escape(item.description || "") + "</p>" +
                    '<div class="requests-card-meta">' +
                    "<div><span>" + escape(labels.buyer) +
                    "</span><strong>#" +
                    escape(item.buyer_id) + "</strong></div>" +
                    "<div><span>" + escape(labels.status) +
                    "</span><strong>" +
                    escape(item.status) + "</strong></div>" +
                    "<div><span>" + escape(labels.currency) +
                    "</span><strong>" +
                    escape(item.currency) + "</strong></div>" +
                    "<div><span>" + escape(labels.location) +
                    "</span><strong>" +
                    escape(item.target_location || "—") +
                    "</strong></div>" +
                    "</div>" +
                    (items.length
                        ? "<strong>" + escape(labels.items) +
                          "</strong>" + itemsHtml
                        : "");

                list.appendChild(card);
            });
        }

        async function loadRequests() {
            status.textContent = labels.loading;
            list.innerHTML = "";

            try {
                let response = await fetch(
                    "/api/v1/requests/mine?limit=100",
                    {
                        method: "GET",
                        credentials: "same-origin",
                        headers: {
                            "Accept": "application/json"
                        }
                    }
                );

                if (response.status === 403) {
                    response = await fetch(
                        "/api/v1/requests?limit=100",
                        {
                            method: "GET",
                            credentials: "same-origin",
                            headers: {
                                "Accept": "application/json"
                            }
                        }
                    );
                }

                if (response.status === 401 || response.status === 403) {
                    list.innerHTML =
                        '<div class="requests-error">' +
                        escape(labels.login) +
                        "</div>";
                    status.textContent = labels.login;
                    return;
                }

                if (!response.ok) {
                    throw new Error("HTTP " + response.status);
                }

                const data = await response.json();

                if (!Array.isArray(data)) {
                    throw new Error("Invalid requests response");
                }

                render(data);
            } catch (error) {
                console.error("REQUESTS_LOAD_ERROR", error);
                list.innerHTML =
                    '<div class="requests-error">' +
                    escape(labels.error) +
                    "</div>";
                status.textContent = labels.error;
            }
        }

        if (refresh) {
            refresh.addEventListener("click", loadRequests);
        }

        loadRequests();
    }

    function bindGoldPrice() {
        const card = document.getElementById("goldPriceCard");
        const value = document.getElementById("goldPriceValue");
        const status = document.getElementById("goldPriceStatus");
        const updated = document.getElementById("goldPriceUpdated");

        if (!card || !value || !status || !updated) {
            return;
        }

        if (card.dataset.goldPriceBound === "true") {
            return;
        }

        card.dataset.goldPriceBound = "true";

        const loadingText = card.dataset.statusLoading || "Loading";
        const errorText = card.dataset.statusError || "Unable to load";

        async function loadGoldPrice() {
            status.textContent = loadingText;

            try {
                const response = await fetch(
                    "https://api.gold-api.com/price/XAU",
                    {
                        method: "GET",
                        cache: "no-store"
                    }
                );

                if (!response.ok) {
                    throw new Error("HTTP " + response.status);
                }

                const data = await response.json();
                const price = Number(data.price);

                if (!Number.isFinite(price) || price <= 0) {
                    throw new Error("Invalid gold price");
                }

                const locale =
                    document.documentElement.lang === "ar"
                        ? "ar"
                        : "en-US";

                value.textContent = new Intl.NumberFormat(locale, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                }).format(price);

                status.textContent = data.updatedAtReadable || "";

                if (data.updatedAt) {
                    const date = new Date(data.updatedAt);

                    if (!Number.isNaN(date.getTime())) {
                        updated.textContent =
                            new Intl.DateTimeFormat(locale, {
                                dateStyle: "medium",
                                timeStyle: "short"
                            }).format(date);
                    } else {
                        updated.textContent = "";
                    }
                } else {
                    updated.textContent = "";
                }
            } catch (error) {
                console.error("Gold price load failed:", error);
                value.textContent = "—";
                status.textContent = errorText;
                updated.textContent = "";
            }
        }

        loadGoldPrice();
        window.setInterval(loadGoldPrice, 300000);
    }

    function bindInteractions() {
        bindGoldPrice();
        bindLanguageToggle();
        bindExploreButton();
        bindLoginButton();
    bindRegisterButton();
        bindModuleCards();
        bindMarketplace();
        bindRequestsPage();
    }

    document.addEventListener(
        "DOMContentLoaded",
        function () {
            bindInteractions();
        }
    );
})();

/* MERCHANT LISTING CREATE */
function bindListingCreate() {
    const form = document.getElementById("listingCreateForm");
    const categorySelect = document.getElementById("listingCategory");
    const status = document.getElementById("listingCreateStatus");
    const imageInput = document.getElementById("listingImages");
    const imagePreview = document.getElementById("listingImagePreview");

    if (!form || !categorySelect || !status) {
        return;
    }

    async function loadCategories() {
        try {
            const response = await fetch("/api/v1/listings/categories");

            if (!response.ok) {
                throw new Error("Categories request failed");
            }

            const categories = await response.json();

            categorySelect.innerHTML =
                '<option value="">اختر التصنيف</option>';

            categories.forEach(function (category) {
                const option = document.createElement("option");
                option.value = category.category_id;
                option.textContent = category.name;
                categorySelect.appendChild(option);
            });
        } catch (error) {
            console.error("Listing categories load failed:", error);
            status.textContent = "تعذر تحميل التصنيفات.";
        }
    }

    function renderImagePreview() {
        if (!imageInput || !imagePreview) {
            return;
        }

        imagePreview.innerHTML = "";

        Array.from(imageInput.files || []).forEach(function (file) {
            if (!file.type.startsWith("image/")) {
                return;
            }

            const item = document.createElement("div");
            item.className = "listing-image-preview-item";

            const image = document.createElement("img");
            image.className = "listing-image-preview";
            image.alt = file.name;

            const label = document.createElement("span");
            label.className = "listing-image-preview-name";
            label.textContent = file.name;

            item.appendChild(image);
            item.appendChild(label);
            imagePreview.appendChild(item);

            const reader = new FileReader();
            reader.onload = function (event) {
                image.src = event.target.result;
            };
            reader.readAsDataURL(file);
        });
    }

    async function uploadImages(listingId) {
        if (!imageInput || !imageInput.files.length) {
            return { uploaded: 0, failed: 0 };
        }

        let uploaded = 0;
        let failed = 0;

        for (const file of Array.from(imageInput.files)) {
            const formData = new FormData();
            formData.append("file", file);

            const response = await fetch(
                "/api/v1/listings/" + listingId + "/images",
                {
                    method: "POST",
                    body: formData
                }
            );

            if (response.ok) {
                uploaded += 1;
            } else {
                failed += 1;
                console.error(
                    "Listing image upload failed:",
                    file.name,
                    await response.text()
                );
            }
        }

        return { uploaded, failed };
    }

    if (imageInput) {
        imageInput.addEventListener("change", renderImagePreview);
    }

    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        const submitButton = form.querySelector(
            'button[type="submit"]'
        );

        if (submitButton) {
            submitButton.disabled = true;
        }

        status.textContent = "جارٍ إنشاء الإعلان...";

        const priceValue =
            document.getElementById("listingPrice").value;

        const payload = {
            title: document.getElementById("listingTitle").value.trim(),
            description:
                document.getElementById("listingDescription").value.trim() ||
                null,
            category_id: Number(categorySelect.value),
            listing_type:
                document.getElementById("listingType").value,
            price:
                priceValue === "" ? null : Number(priceValue),
            currency:
                document.getElementById("listingCurrency").value,
            is_negotiable:
                document.getElementById("listingNegotiable").checked,
            state_province:
                document.getElementById("listingState").value.trim() || null,
            locality:
                document.getElementById("listingLocality").value.trim() || null,
            address:
                document.getElementById("listingAddress").value.trim() || null,
            specs:
                document.getElementById("listingSpecs").value.trim() || null
        };

        try {
            const response = await fetch("/api/v1/listings", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Listing creation failed"
                );
            }

            status.textContent =
                "تم إنشاء الإعلان كمسودة. جارٍ رفع الصور...";

            const uploadResult = await uploadImages(data.id);

            if (uploadResult.failed > 0) {
                status.textContent =
                    "تم إنشاء الإعلان كـ DRAFT، لكن تعذر رفع " +
                    uploadResult.failed +
                    " صورة. الصور المرفوعة: " +
                    uploadResult.uploaded +
                    ".";
            } else {
                status.textContent =
                    "تم إنشاء الإعلان بنجاح كـ DRAFT" +
                    (uploadResult.uploaded
                        ? " مع رفع " +
                          uploadResult.uploaded +
                          " صورة."
                        : ".");
            }

            form.reset();

            const negotiable =
                document.getElementById("listingNegotiable");

            if (negotiable) {
                negotiable.checked = true;
            }

            if (imagePreview) {
                imagePreview.innerHTML = "";
            }
        } catch (error) {
            console.error("Listing creation failed:", error);
            status.textContent =
                "تعذر إنشاء الإعلان: " + error.message;
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
            }
        }
    });

    loadCategories();
}

document.addEventListener("DOMContentLoaded", function () {
    bindListingCreate();
});

/* ADMIN PAYMENT SETTINGS */
function bindAdminPaymentSettings() {
    const container = document.getElementById("adminPaymentSettings");
    const status = document.getElementById("adminPaymentSettingsStatus");

    if (!container || !status) {
        return;
    }

    function renderSettings(settings) {
        container.innerHTML = "";

        if (!settings.length) {
            status.textContent = "لا توجد إعدادات تحويل مفعلة.";
            return;
        }

        status.textContent = "إعدادات التحويل المفعلة.";

        settings.forEach(function (item) {
            const card = document.createElement("article");
            card.className = "admin-listing-review-card";

            card.innerHTML = `
                <div class="admin-listing-review-header">
                    <div>
                        <span class="admin-listing-review-eyebrow">PAYMENT SETTINGS</span>
                        <h3>${escapeHtml(item.currency)}</h3>
                    </div>
                    <span class="admin-listing-review-id">
                        #${escapeHtml(String(item.id))}
                    </span>
                </div>

                <form class="admin-payment-settings-form"
                      data-currency="${escapeHtml(item.currency)}">

                    <div class="admin-listing-review-grid">
                        <div>
                            <label for="payment-account-${escapeHtml(item.currency)}">
                                رقم الحساب
                            </label>
                            <input
                                id="payment-account-${escapeHtml(item.currency)}"
                                name="account_number"
                                type="text"
                                maxlength="255"
                                value="${escapeHtml(item.account_number || "")}"
                                placeholder="أدخل رقم الحساب"
                            >
                        </div>

                        <div>
                            <label for="payment-name-${escapeHtml(item.currency)}">
                                اسم الحساب
                            </label>
                            <input
                                id="payment-name-${escapeHtml(item.currency)}"
                                name="account_name"
                                type="text"
                                maxlength="255"
                                value="${escapeHtml(item.account_name || "")}"
                                placeholder="أدخل اسم الحساب"
                            >
                        </div>
                    </div>

                    <div class="admin-listing-review-description">
                        <label for="payment-instructions-${escapeHtml(item.currency)}">
                            تعليمات التحويل
                        </label>
                        <textarea
                            id="payment-instructions-${escapeHtml(item.currency)}"
                            name="payment_instructions"
                            maxlength="2000"
                            rows="4"
                            placeholder="اكتب تعليمات التحويل للتاجر"
                        >${escapeHtml(item.payment_instructions || "")}</textarea>
                    </div>

                    <div class="admin-listing-review-actions">
                        <button
                            class="btn btn-primary admin-save-payment-settings"
                            type="submit"
                        >
                            حفظ إعدادات ${escapeHtml(item.currency)}
                        </button>
                    </div>
                </form>
            `;

            container.appendChild(card);
        });

        container.querySelectorAll(".admin-payment-settings-form")
            .forEach(function (form) {
                form.addEventListener("submit", function (event) {
                    event.preventDefault();
                    savePaymentSettings(form);
                });
            });
    }

    async function loadPaymentSettings() {
        try {
            const response = await fetch(
                "/admin/commission-payment-settings"
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "فشل تحميل إعدادات التحويل"
                );
            }

            renderSettings(data);
        } catch (error) {
            console.error(
                "Admin payment settings load failed:",
                error
            );
            status.textContent =
                "تعذر تحميل إعدادات التحويل: " + error.message;
        }
    }

    async function savePaymentSettings(form) {
        const currency = form.dataset.currency;
        const button = form.querySelector(
            ".admin-save-payment-settings"
        );

        button.disabled = true;
        button.textContent = "جارٍ الحفظ...";

        const payload = {
            currency: currency,
            account_number:
                form.elements.account_number.value.trim() || null,
            account_name:
                form.elements.account_name.value.trim() || null,
            payment_instructions:
                form.elements.payment_instructions.value.trim() || null,
            is_active: true,
        };

        try {
            const response = await fetch(
                "/admin/commission-payment-settings",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(payload),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "فشل حفظ إعدادات التحويل"
                );
            }

            button.textContent = "تم الحفظ";
            status.textContent =
                "تم حفظ إعدادات التحويل لعملة " + currency + ".";

            await loadPaymentSettings();
        } catch (error) {
            console.error(
                "Admin payment settings save failed:",
                error
            );
            button.disabled = false;
            button.textContent = "حفظ إعدادات " + currency;
            status.textContent =
                "تعذر حفظ إعدادات التحويل: " + error.message;
        }
    }

    loadPaymentSettings();
}

/* ADMIN LISTING REVIEW */
function bindAdminListingReview() {
    const container = document.getElementById("adminPendingListings");
    const status = document.getElementById("adminPendingListingsStatus");

    if (!container || !status) {
        return;
    }

    function renderListings(listings) {
        container.innerHTML = "";

        if (!listings.length) {
            status.textContent = "لا توجد إعلانات قيد المراجعة.";
            return;
        }

        status.textContent =
            "عدد الإعلانات قيد المراجعة: " + listings.length;

        listings.forEach(function (listing) {
            const card = document.createElement("article");
            card.className = "admin-listing-review-card";

            const ownerName =
                listing.owner_name || listing.owner_email || "غير مسجل";

            const phoneHtml = listing.owner_phone
                ? `<a href="tel:${escapeHtml(listing.owner_phone)}">${escapeHtml(listing.owner_phone)}</a>`
                : "غير مسجل";

            const emailHtml = listing.owner_email
                ? `<a href="mailto:${escapeHtml(listing.owner_email)}">${escapeHtml(listing.owner_email)}</a>`
                : "غير مسجل";

            const priceHtml =
                listing.price === null
                    ? "غير محدد"
                    : escapeHtml(
                        String(listing.price) +
                        " " +
                        String(listing.currency || "")
                    );

            card.innerHTML = `
                <div class="admin-listing-review-header">
                    <div>
                        <span class="admin-listing-review-eyebrow">LISTING REVIEW</span>
                        <h3>${escapeHtml(listing.title)}</h3>
                    </div>
                    <span class="admin-listing-review-id">
                        #${escapeHtml(String(listing.id))}
                    </span>
                </div>

                <div class="admin-listing-review-owner">
                    <strong>المالك</strong>
                    <span>${escapeHtml(ownerName)}</span>
                </div>

                <div class="admin-listing-review-contact">
                    <div class="admin-listing-review-contact-item">
                        <span>الهاتف</span>
                        <span>${phoneHtml}</span>
                    </div>
                    <div class="admin-listing-review-contact-item">
                        <span>البريد الإلكتروني</span>
                        <span>${emailHtml}</span>
                    </div>
                </div>

                <div class="admin-listing-review-grid">
                    <div>
                        <span>التصنيف</span>
                        <strong>${escapeHtml(String(listing.category_id))}</strong>
                    </div>
                    <div>
                        <span>النوع</span>
                        <strong>${escapeHtml(listing.listing_type)}</strong>
                    </div>
                    <div>
                        <span>السعر</span>
                        <strong>${priceHtml}</strong>
                    </div>
                    <div>
                        <span>الحالة</span>
                        <strong>${escapeHtml(listing.status)}</strong>
                    </div>
                </div>

                <div class="admin-listing-review-description">
                    <span>الوصف</span>
                    <p>${escapeHtml(listing.description || "لا يوجد وصف.")}</p>
                </div>

                <div class="admin-listing-review-actions">
                    <label class="form-field">
                        <span>تصنيف الكمية</span>
                        <select
                            class="admin-listing-quantity-mode"
                            required
                            aria-label="تصنيف كمية الإعلان"
                        >
                            <option value="" selected disabled>اختر SINGLE أو BULK</option>
                            <option value="SINGLE">SINGLE</option>
                            <option value="BULK">BULK</option>
                        </select>
                    </label>
                    <button
                        class="btn btn-primary admin-approve-listing"
                        type="button"
                        data-listing-id="${listing.id}"
                    >
                        اعتماد الإعلان
                    </button>
                </div>
            `;

            container.appendChild(card);
        });

        container.querySelectorAll(".admin-approve-listing")
            .forEach(function (button) {
                button.addEventListener("click", function () {
                    approveListing(button);
                });
            });
    }

    async function loadPendingListings() {
        try {
            const response = await fetch("/admin/listings/pending");

            if (!response.ok) {
                throw new Error(
                    response.status === 401 || response.status === 403
                        ? "غير مصرح بالدخول"
                        : "فشل تحميل الإعلانات"
                );
            }

            const listings = await response.json();
            renderListings(listings);
        } catch (error) {
            console.error(
                "Admin pending listings load failed:",
                error
            );
            status.textContent =
                "تعذر تحميل الإعلانات: " + error.message;
        }
    }

    async function approveListing(button) {
        const listingId = button.dataset.listingId;
        const card = button.closest(".admin-listing-review-card");
        const quantityModeSelect = card
            ? card.querySelector(".admin-listing-quantity-mode")
            : null;
        const quantityMode = quantityModeSelect
            ? quantityModeSelect.value
            : "";

        if (quantityMode !== "SINGLE" && quantityMode !== "BULK") {
            status.textContent = "اختر SINGLE أو BULK قبل اعتماد الإعلان.";
            if (quantityModeSelect) {
                quantityModeSelect.focus();
            }
            return;
        }

        button.disabled = true;
        button.textContent = "جارٍ الاعتماد...";

        try {
            const response = await fetch(
                "/admin/listings/" +
                encodeURIComponent(listingId) +
                "/approve",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        quantity_mode: quantityMode
                    })
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "فشل اعتماد الإعلان"
                );
            }

            button.textContent = "تم الاعتماد";

            await loadPendingListings();
        } catch (error) {
            console.error(
                "Admin listing approval failed:",
                error
            );

            button.disabled = false;
            button.textContent = "اعتماد الإعلان";

            status.textContent =
                "تعذر اعتماد الإعلان: " + error.message;
        }
    }

    loadPendingListings();
}

document.addEventListener("DOMContentLoaded", function () {
    bindAdminPaymentSettings();
    bindAdminListingReview();
});
