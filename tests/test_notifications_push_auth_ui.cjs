"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const source = fs.readFileSync(
    path.join(__dirname, "..", "app", "static", "js", "notifications.js"),
    "utf8"
);

class FakeElement {
    constructor(id = "") {
        this.id = id;
        this.hidden = false;
        this.disabled = false;
        this.textContent = "";
        this.dataset = {};
        this.attributes = {};
        this.listeners = {};
        this.children = [];
        this.classList = { add() {} };
    }
    addEventListener(name, callback) {
        this.listeners[name] = callback;
    }
    setAttribute(name, value) {
        this.attributes[name] = String(value);
    }
    append(...items) {
        this.children.push(...items);
    }
    replaceChildren(...items) {
        this.children = [...items];
    }
}

function response(status, body = {}) {
    return {
        status,
        ok: status >= 200 && status < 300,
        async json() { return body; }
    };
}

function createHarness({
    authStatus = 200,
    keyStatus = 200,
    subscriptionStatus = 200
} = {}) {
    const ids = [
        "smh-notifications",
        "smh-notifications-toggle",
        "smh-notifications-count",
        "smh-notifications-panel",
        "smh-notifications-list",
        "smh-notifications-empty",
        "smh-notifications-read-all",
        "smh-notification-toast",
        "smh-notification-toast-title",
        "smh-notification-toast-message",
        "smh-notifications-enable-push"
    ];

    const elements = Object.fromEntries(
        ids.map(id => [id, new FakeElement(id)])
    );

    elements["smh-notifications"].dataset = {
        pushLoginRequired: "Please sign in before enabling notifications.",
        pushEnabled: "Notifications enabled",
        pushUnavailable: "Could not enable notifications"
    };

    elements["smh-notifications-panel"].hidden = true;
    elements["smh-notification-toast"].hidden = true;

    const events = [];
    const fetchCalls = [];
    let permission = "default";
    let registerCalls = 0;
    let permissionRequests = 0;
    let subscribeCalls = 0;

    const subscription = {
        toJSON() {
            return {
                endpoint: "https://push.example.test/subscription",
                keys: { p256dh: "test-p256dh", auth: "test-auth" }
            };
        }
    };

    const registration = {
        pushManager: {
            async getSubscription() { return null; },
            async subscribe() {
                subscribeCalls++;
                events.push("subscribe");
                return subscription;
            }
        }
    };

    const navigator = {
        serviceWorker: {
            async register() {
                registerCalls++;
                events.push("service-worker-register");
                return registration;
            }
        }
    };

    const NotificationApi = {
        get permission() { return permission; },
        async requestPermission() {
            permissionRequests++;
            events.push("permission-request");
            permission = "granted";
            return permission;
        }
    };

    async function fetchMock(url, options = {}) {
        fetchCalls.push({ url, options });

        if (url === "/auth/me") {
            events.push("auth-check");
            return response(authStatus);
        }

        if (url === "/api/notifications?limit=20") {
            return response(200, { unread_count: 0, items: [] });
        }

        if (url === "/api/notifications/push-public-key") {
            events.push("public-key");
            return response(keyStatus, {
                enabled: true,
                public_key: "AQIDBA"
            });
        }

        if (url === "/api/notifications/push-subscription") {
            events.push("subscription-save");
            return response(subscriptionStatus, { ok: true });
        }

        throw new Error("Unexpected fetch URL: " + url);
    }

    const document = {
        hidden: false,
        documentElement: { lang: "en" },
        getElementById(id) { return elements[id] || null; },
        createElement() { return new FakeElement(); },
        addEventListener() {}
    };

    const window = {
        Notification: NotificationApi,
        PushManager: function PushManager() {},
        setTimeout() { return 1; },
        clearTimeout() {},
        setInterval() { return 1; },
        location: { href: "" }
    };

    vm.runInNewContext(source, {
        document,
        window,
        navigator,
        Notification: NotificationApi,
        fetch: fetchMock,
        atob(value) {
            return Buffer.from(value, "base64").toString("binary");
        },
        Uint8Array,
        Intl,
        Date,
        Number,
        String,
        Set,
        Array,
        Error,
        console: { error() {} }
    }, { filename: "notifications.js" });

    return {
        elements,
        events,
        fetchCalls,
        async clickEnable() {
            await elements["smh-notifications-enable-push"].listeners.click();
        },
        get permission() { return permission; },
        get registerCalls() { return registerCalls; },
        get permissionRequests() { return permissionRequests; },
        get subscribeCalls() { return subscribeCalls; }
    };
}

test("visitor must sign in before permission or service worker access", async () => {
    const app = createHarness({ authStatus: 401 });
    await app.clickEnable();

    assert.equal(
        app.fetchCalls.filter(call => call.url === "/auth/me").length,
        1
    );
    assert.equal(app.permissionRequests, 0);
    assert.equal(app.registerCalls, 0);
    assert.equal(app.subscribeCalls, 0);
    assert.equal(app.permission, "default");
    assert.equal(
        app.elements["smh-notification-toast-title"].textContent,
        "Please sign in before enabling notifications."
    );
    assert.equal(
        app.elements["smh-notifications-enable-push"].disabled,
        false
    );
});

test("authenticated user completes the push subscription flow", async () => {
    const app = createHarness();
    await app.clickEnable();

    assert.deepEqual(
        app.events.slice(0, 5),
        [
            "auth-check",
            "permission-request",
            "service-worker-register",
            "public-key",
            "subscribe"
        ]
    );
    assert.equal(app.permissionRequests, 1);
    assert.equal(app.registerCalls, 1);
    assert.equal(app.subscribeCalls, 1);
    assert.ok(app.events.includes("subscription-save"));
    assert.equal(
        app.elements["smh-notifications-enable-push"].textContent,
        "Notifications enabled"
    );
});

test("expired session at public key request prevents subscription saving", async () => {
    const app = createHarness({ keyStatus: 401 });
    await app.clickEnable();

    assert.ok(app.events.includes("auth-check"));
    assert.ok(app.events.includes("public-key"));
    assert.equal(app.events.includes("subscription-save"), false);
    assert.equal(
        app.elements["smh-notification-toast-title"].textContent,
        "Please sign in before enabling notifications."
    );
    assert.equal(
        app.elements["smh-notifications-enable-push"].disabled,
        false
    );
});

test("expired session at subscription saving does not report success", async () => {
    const app = createHarness({ subscriptionStatus: 401 });
    await app.clickEnable();

    assert.ok(app.events.includes("subscription-save"));
    assert.equal(
        app.elements["smh-notification-toast-title"].textContent,
        "Please sign in before enabling notifications."
    );
    assert.notEqual(
        app.elements["smh-notifications-enable-push"].textContent,
        "Notifications enabled"
    );
    assert.equal(
        app.elements["smh-notifications-enable-push"].disabled,
        false
    );
});
