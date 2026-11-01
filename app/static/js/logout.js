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

    async function logout() {
        button.disabled = true;
        button.textContent = inProgressText;

        try {
            if ("serviceWorker" in navigator) {
                const registration =
                    await navigator.serviceWorker.getRegistration("/");

                if (registration && registration.pushManager) {
                    const subscription =
                        await registration.pushManager.getSubscription();

                    if (subscription) {
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
                            throw new Error(
                                "Could not delete device subscription: " +
                                response.status
                            );
                        }

                        const unsubscribed =
                            await subscription.unsubscribe();

                        if (!unsubscribed) {
                            throw new Error(
                                "Browser did not confirm subscription removal"
                            );
                        }
                    }
                }
            }

            const response = await fetch("/auth/logout", {
                method: "POST",
                credentials: "same-origin",
                cache: "no-store",
                headers: { Accept: "application/json" }
            });

            if (!response.ok) {
                throw new Error("Logout request failed: " + response.status);
            }

            window.location.replace("/");
        } catch (error) {
            console.error("Logout failed", error);
            button.disabled = false;
            button.textContent = originalText;
            window.alert(failedText);
        }
    }

    button.addEventListener("click", logout);
    checkAuthentication();
})();
