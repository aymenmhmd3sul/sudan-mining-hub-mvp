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
    bindRegisterButton();
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
            card.className = "marketplace-listing-detail-card";

            card.innerHTML = `
                <div class="marketplace-listing-detail-section">
                    <h3>${escapeHtml(listing.title)}</h3>

                    <p>
                        <strong>رقم الإعلان:</strong>
                        ${escapeHtml(String(listing.id))}
                    </p>

                    <p>
                        <strong>المالك:</strong>
                        ${escapeHtml(listing.owner_name || listing.owner_email)}
                    </p>

                    <p>
                        <strong>الهاتف:</strong>
                        ${
                            listing.owner_phone
                                ? `<a href="tel:${escapeHtml(listing.owner_phone)}">${escapeHtml(listing.owner_phone)}</a>`
                                : "غير مسجل"
                        }
                    </p>

                    <p>
                        <strong>البريد الإلكتروني:</strong>
                        <a href="mailto:${escapeHtml(listing.owner_email)}">
                            ${escapeHtml(listing.owner_email)}
                        </a>
                    </p>

                    <p>
                        <strong>الوصف:</strong>
                        ${escapeHtml(listing.description || "لا يوجد وصف.")}
                    </p>

                    <p>
                        <strong>التصنيف:</strong>
                        ${escapeHtml(String(listing.category_id))}
                    </p>

                    <p>
                        <strong>النوع:</strong>
                        ${escapeHtml(listing.listing_type)}
                    </p>

                    <p>
                        <strong>السعر:</strong>
                        ${listing.price === null
                            ? "غير محدد"
                            : escapeHtml(
                                String(listing.price) +
                                " " +
                                String(listing.currency)
                            )
                        }
                    </p>

                    <p>
                        <strong>الحالة:</strong>
                        ${escapeHtml(listing.status)}
                    </p>

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

        button.disabled = true;
        button.textContent = "جارٍ الاعتماد...";

        try {
            const response = await fetch(
                "/admin/listings/" +
                encodeURIComponent(listingId) +
                "/approve",
                {
                    method: "POST"
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
    bindAdminListingReview();
});
