"use strict";

self.addEventListener("push", (event) => {
    let data = {};

    try {
        data = event.data ? event.data.json() : {};
    } catch (_) {
        data = {
            body: event.data ? event.data.text() : ""
        };
    }

    const title = data.title || "Sudan Mining Hub";
    const options = {
        body: data.body || data.message || "",
        icon: "/static/icons/icon-192.png",
        badge: "/static/icons/icon-192.png",
        data: {
            url: data.url || "/"
        }
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();

    const target = new URL(
        event.notification.data?.url || "/",
        self.location.origin
    );

    if (target.origin !== self.location.origin) {
        return;
    }

    event.waitUntil(
        clients.matchAll({
            type: "window",
            includeUncontrolled: true
        }).then((windows) => {
            for (const windowClient of windows) {
                if (windowClient.url === target.href && "focus" in windowClient) {
                    return windowClient.focus();
                }
            }

            return clients.openWindow(target.href);
        })
    );
});
