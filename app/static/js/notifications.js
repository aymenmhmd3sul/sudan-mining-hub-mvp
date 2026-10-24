(() => {
    "use strict";

    const root = document.getElementById("smh-notifications");
    if (!root) return;

    // Keep the notification button visible for visitors.
    // Authentication is still enforced by the notification API.
    root.hidden = false;

    const toggle = document.getElementById("smh-notifications-toggle");
    const count = document.getElementById("smh-notifications-count");
    const panel = document.getElementById("smh-notifications-panel");
    const list = document.getElementById("smh-notifications-list");
    const empty = document.getElementById("smh-notifications-empty");
    const readAll = document.getElementById("smh-notifications-read-all");
    const toast = document.getElementById("smh-notification-toast");
    const toastTitle = document.getElementById("smh-notification-toast-title");
    const toastMessage = document.getElementById("smh-notification-toast-message");
    const pushEnable = document.getElementById("smh-notifications-enable-push");

    const labels = {
        unread: root.dataset.unread || "Unread notifications",
        empty: root.dataset.empty || "No notifications",
        readAll: root.dataset.readAll || "Mark all as read",
        requestError: root.dataset.error || "Could not load notifications",
        close: root.dataset.close || "Close notifications",
        pushEnable: root.dataset.pushEnable || "Enable notifications",
        pushEnabled: root.dataset.pushEnabled || "Notifications enabled",
        pushDenied: root.dataset.pushDenied || "Notification permission was not granted",
        pushBlocked: root.dataset.pushBlocked || "Notifications are blocked in browser settings",
        pushBlockedHelp: root.dataset.pushBlockedHelp || "Open this site's browser permissions and allow notifications, then reload the page.",
        pushUnavailable: root.dataset.pushUnavailable || "Could not enable notifications; check server configuration",
        pushUnsupported: root.dataset.pushUnsupported || "This browser does not support notifications"
    };

    let initialized = false;
    let polling = false;
    let knownIds = new Set();
    let toastTimer = null;

    function showToast(title, message) {
        toastTitle.textContent = title || labels.unread;
        toastMessage.textContent = message || "";
        toast.hidden = false;

        if (toastTimer) window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => {
            toast.hidden = true;
        }, 6000);
    }

    function updateCount(value) {
        const number = Number(value) || 0;
        count.textContent = number > 99 ? "99+" : (number > 0 ? String(number) : "");
        count.setAttribute("aria-label", `${number} ${labels.unread}`);
        toggle.setAttribute("aria-label", `${labels.unread}: ${number}`);
    }

    function renderItems(items) {
        list.replaceChildren();

        if (!items.length) {
            empty.hidden = false;
            return;
        }

        empty.hidden = true;

        for (const item of items) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "smh-notification-item";
            if (!item.is_read) button.classList.add("is-unread");
            button.dataset.notificationId = String(item.id);

            const title = document.createElement("strong");
            title.textContent = item.title || labels.unread;

            const message = document.createElement("span");
            message.textContent = item.message || "";

            button.append(title, message);

            if (item.created_at) {
                const time = document.createElement("time");
                time.dateTime = item.created_at;

                const date = new Date(item.created_at);
                time.textContent = Number.isNaN(date.getTime())
                    ? item.created_at
                    : new Intl.DateTimeFormat(
                        document.documentElement.lang || undefined,
                        { dateStyle: "medium", timeStyle: "short" }
                    ).format(date);

                button.append(time);
            }

            button.addEventListener("click", async () => {
                if (!item.is_read) {
                    const result = await markRead(item.id);
                    if (!result) return;
                }

                if (item.related_type === "NEGOTIATION_ROOM" && item.related_id) {
                    window.location.href =
                        `/negotiation?room_id=${encodeURIComponent(item.related_id)}`;
                } else {
                    await refresh(false);
                }
            });

            list.append(button);
        }
    }

    async function requestJson(url, options = {}) {
        const response = await fetch(url, {
            credentials: "same-origin",
            cache: "no-store",
            ...options,
            headers: {
                Accept: "application/json",
                ...(options.headers || {})
            }
        });

        if (response.status === 401 || response.status === 403) {
            return null;
        }

        if (!response.ok) {
            throw new Error(`Notification request failed: ${response.status}`);
        }

        return response.json();
    }

    async function markRead(id) {
        try {
            await requestJson(
                `/api/notifications/${encodeURIComponent(id)}/read`,
                { method: "PATCH" }
            );
            await refresh(false);
            return true;
        } catch (error) {
            console.error("Could not mark notification as read", error);
            showToast(labels.requestError, "");
            return false;
        }
    }

    async function refresh(allowToast = true) {
        if (polling || document.hidden) return;
        polling = true;

        try {
            const data = await requestJson("/api/notifications?limit=20");
            if (!data) return false;

            root.hidden = false;
            updateCount(data.unread_count);

            const items = Array.isArray(data.items) ? data.items : [];

            if (initialized && allowToast) {
                const fresh = items
                    .filter(item => !knownIds.has(String(item.id)))
                    .sort((a, b) => {
                        const aTime = Date.parse(a.created_at || "") || 0;
                        const bTime = Date.parse(b.created_at || "") || 0;
                        return aTime - bTime;
                    });

                if (fresh.length) {
                    const latest = fresh[fresh.length - 1];
                    showToast(latest.title, latest.message);
                }
            }

            for (const item of items) knownIds.add(String(item.id));
            if (knownIds.size > 200) {
                knownIds = new Set(
                    [...knownIds].slice(-100)
                );
            }

            renderItems(items);
            initialized = true;
        } catch (error) {
            console.error("Could not load notifications", error);
        } finally {
            polling = false;
        }
    }

    toggle.addEventListener("click", async () => {
        const opening = panel.hidden;
        panel.hidden = !opening;
        toggle.setAttribute("aria-expanded", String(opening));

        if (opening) {
            await refresh(false);
        }
    });

    readAll.addEventListener("click", async () => {
        try {
            await requestJson("/api/notifications/read-all", { method: "PATCH" });
            await refresh(false);
        } catch (error) {
            console.error("Could not mark all notifications as read", error);
            showToast(labels.requestError, "");
        }
    });

    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) refresh(true);
    });

    async function enablePushForGrantedPermission() {
        if (
            !("serviceWorker" in navigator) ||
            !("PushManager" in window) ||
            !("Notification" in window)
        ) {
            return false;
        }

        try {
            const registration = await navigator.serviceWorker.register(
                "/service-worker.js",
                { scope: "/" }
            );

            const keyResponse = await requestJson(
                "/api/notifications/push-public-key"
            );

            if (
                !keyResponse ||
                !keyResponse.enabled ||
                !keyResponse.public_key ||
                Notification.permission !== "granted"
            ) {
                return false;
            }

            let encodedKey = keyResponse.public_key
                .replace(/-/g, "+")
                .replace(/_/g, "/");
            encodedKey += "=".repeat((4 - encodedKey.length % 4) % 4);

            const applicationServerKey = Uint8Array.from(
                atob(encodedKey),
                character => character.charCodeAt(0)
            );

            let subscription = await registration.pushManager.getSubscription();

            if (!subscription) {
                subscription = await registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey
                });
            }

            const response = await fetch(
                "/api/notifications/push-subscription",
                {
                    method: "POST",
                    credentials: "same-origin",
                    cache: "no-store",
                    headers: {
                        Accept: "application/json",
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(subscription)
                }
            );

            if (!response.ok) {
                throw new Error(
                    "Push subscription registration failed: " + response.status
                );
            }

            return true;
        } catch (error) {
            console.error(
                "Could not register web push subscription",
                error
            );
            return false;
        }
    }

    pushEnable.addEventListener("click", async () => {
        pushEnable.disabled = true;

        try {
            if (!("Notification" in window)) {
                showToast(labels.pushUnsupported, "");
                pushEnable.disabled = false;
                return;
            }

            if (Notification.permission === "denied") {
                pushEnable.textContent = labels.pushBlocked;
                showToast(labels.pushBlocked, labels.pushBlockedHelp);
                pushEnable.disabled = false;
                return;
            }

            let permission = Notification.permission;
            if (permission === "default") {
                permission = await Notification.requestPermission();
            }

            if (permission !== "granted") {
                if (permission === "denied") {
                    pushEnable.textContent = labels.pushBlocked;
                    showToast(labels.pushBlocked, labels.pushBlockedHelp);
                } else {
                    showToast(labels.pushDenied, "");
                }
                pushEnable.disabled = false;
                return;
            }

            const enabled = await enablePushForGrantedPermission();

            if (!enabled) {
                showToast(labels.pushUnavailable, "");
                pushEnable.disabled = false;
                return;
            }

            pushEnable.textContent = labels.pushEnabled;
            showToast(labels.pushEnabled, "");
        } catch (error) {
            console.error("Could not enable notifications", error);
            showToast(labels.pushUnavailable, "");
            pushEnable.disabled = false;
        }
    });

    if ("Notification" in window && Notification.permission === "denied") {
        pushEnable.textContent = labels.pushBlocked;
    }

    enablePushForGrantedPermission().then(enabled => {
        if (enabled) {
            pushEnable.textContent = labels.pushEnabled;
            pushEnable.disabled = true;
        }
    });

    refresh(false);
    window.setInterval(() => refresh(true), 30000);
})();
