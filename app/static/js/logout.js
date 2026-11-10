(() => {
    "use strict";

    const button = document.getElementById("smh-logout-button");
    if (!button) return;

    const originalText = button.textContent.trim();
    const inProgressText = button.dataset.inProgress;
    const failedText = button.dataset.failed;

    async function checkAuthentication() {
        try {
            const response = await fetch("/auth/me", {
                method: "GET",
                credentials: "same-origin",
                cache: "no-store",
                headers: { Accept: "application/json" }
            });
            button.hidden = !response.ok;
        } catch (error) {
            console.error("Could not verify authentication", error);
            button.hidden = true;
        }
    }

    async function cleanupPushSubscription() {
        try {
            if (!("serviceWorker" in navigator)) return;

            const registration =
                await navigator.serviceWorker.getRegistration("/");

            if (!registration || !registration.pushManager) return;

            const subscription =
                await registration.pushManager.getSubscription();

            if (!subscription) return;

            try {
                const response = await fetch(
                    "/api/notifications/push-subscription",
                    {
                        method: "DELETE",
                        credentials: "same-origin",
                        cache: "no-store",
                        headers: {
                            Accept: "application/json",
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            endpoint: subscription.endpoint
                        })
                    }
                );

                if (!response.ok) {
                    console.warn(
                        "Could not delete device subscription:",
                        response.status
                    );
                }
            } catch (error) {
                console.warn("Push subscription deletion failed", error);
            }

            try {
                const unsubscribed = await subscription.unsubscribe();
                if (!unsubscribed) {
                    console.warn(
                        "Browser did not confirm subscription removal"
                    );
                }
            } catch (error) {
                console.warn("Browser push unsubscribe failed", error);
            }
        } catch (error) {
            console.warn("Push cleanup failed; continuing logout", error);
        }
    }

    function showLogoutScene() {
        const isArabic =
            (document.documentElement.lang || "ar")
                .toLowerCase()
                .startsWith("ar");

        const scene = document.createElement("div");
        scene.id = "smh-logout-scene";
        scene.setAttribute("role", "status");
        scene.setAttribute("aria-live", "polite");

        const frame = document.createElement("div");
        frame.className = "smh-logout-frame";

        const emblem = document.createElement("div");
        emblem.className = "smh-logout-emblem";
        emblem.textContent = "SMH";

        const title = document.createElement("div");
        title.className = "smh-logout-title";
        title.textContent = isArabic ? "نراك قريباً" : "Until We Meet Again";

        const status = document.createElement("div");
        status.className = "smh-logout-status";
        status.textContent = isArabic
            ? "تم إنهاء رحلتك بأمان"
            : "Your session has ended safely";

        const farewell = document.createElement("div");
        farewell.className = "smh-logout-farewell";
        farewell.textContent = isArabic
            ? "حتى نلتقي من جديد"
            : "Until we meet again";

        const english = document.createElement("span");
        english.className = "smh-logout-english";
        english.textContent = "UNTIL WE MEET AGAIN";

        farewell.appendChild(english);
        frame.append(emblem, title, status, farewell);
        scene.appendChild(frame);
        document.body.appendChild(scene);

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                scene.classList.add("is-visible");
            });
        });

        return scene;
    }

    function wait(milliseconds) {
        return new Promise(resolve => setTimeout(resolve, milliseconds));
    }

    function hideLogoutScene() {
        document.getElementById("smh-logout-scene")?.remove();
    }

    async function logout() {
        if (button.disabled) return;

        button.disabled = true;
        button.textContent = inProgressText;

        const sceneStartedAt = performance.now();
        const scene = showLogoutScene();

        const reducedMotion = window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches;

        try {
            await cleanupPushSubscription();

            const response = await fetch("/auth/logout", {
                method: "POST",
                credentials: "same-origin",
                cache: "no-store",
                headers: { Accept: "application/json" }
            });

            if (!response.ok) {
                throw new Error("Logout request failed: " + response.status);
            }

            // Keep the complete cinematic scene visible before closing.
            const presentationDuration = reducedMotion ? 1200 : 6500;
            const closingDuration = reducedMotion ? 0 : 1700;

            const elapsed = performance.now() - sceneStartedAt;
            const remaining = Math.max(0, presentationDuration - elapsed);

            if (remaining > 0) {
                await wait(remaining);
            }

            // Fade the entire scene, including the emblem and background.
            scene.classList.add("is-closing");

            if (closingDuration > 0) {
                await wait(closingDuration);
            }

            window.location.replace("/");
        } catch (error) {
            console.error("Logout failed", error);

            button.disabled = false;
            button.textContent = originalText;

            hideLogoutScene();
            window.alert(failedText);
        }
    }

    button.addEventListener("click", logout);
    checkAuthentication();
})();
