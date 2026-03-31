/**
 * GigHala Capacitor Mobile Bridge
 * Initializes native plugins and provides a unified mobile API.
 * Loaded only when running inside the Capacitor Android/iOS shell.
 */

const GigHalaMobile = (() => {
    // ── Detect if running inside Capacitor ────────────────────────────────────
    const isNative = () => !!(window.Capacitor && window.Capacitor.isNativePlatform());

    // ── Lazy-load Capacitor plugins ───────────────────────────────────────────
    let _plugins = null;
    const plugins = () => {
        if (!_plugins && isNative()) {
            _plugins = {
                App:                window.Capacitor.Plugins.App,
                Camera:             window.Capacitor.Plugins.Camera,
                Device:             window.Capacitor.Plugins.Device,
                Filesystem:         window.Capacitor.Plugins.Filesystem,
                Haptics:            window.Capacitor.Plugins.Haptics,
                Keyboard:           window.Capacitor.Plugins.Keyboard,
                LocalNotifications: window.Capacitor.Plugins.LocalNotifications,
                Network:            window.Capacitor.Plugins.Network,
                PushNotifications:  window.Capacitor.Plugins.PushNotifications,
                SplashScreen:       window.Capacitor.Plugins.SplashScreen,
                StatusBar:          window.Capacitor.Plugins.StatusBar,
                GigHalaBiometric:   window.Capacitor.Plugins.GigHalaBiometric,
            };
        }
        return _plugins || {};
    };

    // =========================================================================
    // PUSH NOTIFICATIONS
    // =========================================================================
    const pushNotifications = {
        async init() {
            if (!isNative()) return;
            const { PushNotifications } = plugins();
            if (!PushNotifications) return;

            // Request permission
            const result = await PushNotifications.requestPermissions();
            if (result.receive === 'granted') {
                await PushNotifications.register();
            }

            // Send FCM token to backend
            PushNotifications.addListener('registration', async (token) => {
                console.log('[GigHala] FCM token:', token.value);
                await pushNotifications.sendTokenToServer(token.value);
            });

            PushNotifications.addListener('registrationError', (err) => {
                console.error('[GigHala] Push registration error:', err);
            });

            // Foreground notification received
            PushNotifications.addListener('pushNotificationReceived', (notification) => {
                console.log('[GigHala] Push received:', notification);
                pushNotifications.showInAppBanner(notification);
            });

            // Notification tapped
            PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
                const url = action.notification.data?.url;
                if (url) window.location.href = url;
            });
        },

        async sendTokenToServer(token) {
            try {
                const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
                await fetch('/api/mobile/register-push-token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrf,
                        'X-Mobile-App': 'true',
                    },
                    body: JSON.stringify({ token, platform: 'android' }),
                });
            } catch (e) {
                console.error('[GigHala] Failed to register push token:', e);
            }
        },

        showInAppBanner(notification) {
            const banner = document.createElement('div');
            banner.className = 'mobile-notification-banner';
            banner.innerHTML = `
                <div class="notif-icon">🔔</div>
                <div class="notif-body">
                    <strong>${notification.title || 'GigHala'}</strong>
                    <p>${notification.body || ''}</p>
                </div>
            `;
            document.body.appendChild(banner);
            setTimeout(() => banner.remove(), 4000);
        },
    };

    // =========================================================================
    // CAMERA & PHOTO UPLOAD
    // =========================================================================
    const camera = {
        async pickPhoto(options = {}) {
            if (!isNative()) {
                // Fallback to file input on web
                return camera.webFilePicker(options.accept || 'image/*');
            }

            const { Camera } = plugins();
            const { CameraResultType, CameraSource } = window.Capacitor.Plugins;

            const image = await Camera.getPhoto({
                quality: options.quality || 85,
                allowEditing: options.allowEditing || false,
                resultType: 'base64',
                source: options.source || 'PROMPT', // CAMERA | PHOTOS | PROMPT
                correctOrientation: true,
                width: options.width || 1280,
                height: options.height || 1280,
            });

            // Haptic feedback on selection
            haptics.light();

            return {
                base64: image.base64String,
                format: image.format,
                dataUrl: `data:image/${image.format};base64,${image.base64String}`,
            };
        },

        async uploadPhoto(fieldName, base64Data, format, extraData = {}) {
            const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
            const blob = camera.base64ToBlob(base64Data, `image/${format}`);
            const formData = new FormData();
            formData.append(fieldName, blob, `photo.${format}`);
            Object.entries(extraData).forEach(([k, v]) => formData.append(k, v));

            const response = await fetch('/api/mobile/upload-photo', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrf,
                    'X-Mobile-App': 'true',
                },
                body: formData,
            });
            return response.json();
        },

        base64ToBlob(base64, mimeType) {
            const bytes = atob(base64);
            const arr = new Uint8Array(bytes.length);
            for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
            return new Blob([arr], { type: mimeType });
        },

        webFilePicker(accept) {
            return new Promise((resolve, reject) => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = accept;
                input.onchange = (e) => {
                    const file = e.target.files[0];
                    if (!file) { reject(new Error('No file selected')); return; }
                    const reader = new FileReader();
                    reader.onload = () => resolve({
                        base64: reader.result.split(',')[1],
                        format: file.type.split('/')[1],
                        dataUrl: reader.result,
                    });
                    reader.readAsDataURL(file);
                };
                input.click();
            });
        },
    };

    // =========================================================================
    // BIOMETRIC AUTHENTICATION
    // =========================================================================
    const biometric = {
        async isAvailable() {
            if (!isNative()) return { isAvailable: false };
            const { GigHalaBiometric } = plugins();
            if (!GigHalaBiometric) return { isAvailable: false };
            return GigHalaBiometric.isAvailable();
        },

        async authenticate(options = {}) {
            if (!isNative()) throw new Error('Biometric not available in browser');
            const { GigHalaBiometric } = plugins();
            return GigHalaBiometric.authenticate({
                title: options.title || 'GigHala',
                subtitle: options.subtitle || 'Log masuk dengan biometrik',
                description: options.description || 'Sahkan identiti anda untuk teruskan',
                cancelTitle: options.cancelTitle || 'Batal',
            });
        },

        async loginWithBiometric() {
            try {
                const result = await biometric.authenticate();
                if (result.verified) {
                    const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
                    const response = await fetch('/api/mobile/biometric-login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrf,
                            'X-Mobile-App': 'true',
                        },
                        body: JSON.stringify({ verified: true }),
                    });
                    const data = await response.json();
                    if (data.success) {
                        haptics.success();
                        window.location.href = data.redirect || '/dashboard';
                    }
                }
            } catch (e) {
                console.error('[GigHala] Biometric auth failed:', e);
            }
        },
    };

    // =========================================================================
    // HAPTICS
    // =========================================================================
    const haptics = {
        async light() {
            if (!isNative()) return;
            const { Haptics } = plugins();
            Haptics?.impact({ style: 'LIGHT' });
        },
        async medium() {
            if (!isNative()) return;
            const { Haptics } = plugins();
            Haptics?.impact({ style: 'MEDIUM' });
        },
        async success() {
            if (!isNative()) return;
            const { Haptics } = plugins();
            Haptics?.notification({ type: 'SUCCESS' });
        },
        async error() {
            if (!isNative()) return;
            const { Haptics } = plugins();
            Haptics?.notification({ type: 'ERROR' });
        },
    };

    // =========================================================================
    // NETWORK STATUS
    // =========================================================================
    const network = {
        async getStatus() {
            if (!isNative()) return { connected: navigator.onLine };
            const { Network } = plugins();
            return Network?.getStatus() || { connected: navigator.onLine };
        },

        watchConnectivity() {
            if (!isNative()) return;
            const { Network } = plugins();
            Network?.addListener('networkStatusChange', (status) => {
                const banner = document.getElementById('offline-banner');
                if (banner) banner.style.display = status.connected ? 'none' : 'flex';
            });
        },
    };

    // =========================================================================
    // STATUS BAR & UI
    // =========================================================================
    const ui = {
        async init() {
            if (!isNative()) return;
            const { StatusBar, SplashScreen } = plugins();

            // Dark status bar to match GigHala dark theme
            await StatusBar?.setStyle({ style: 'DARK' });
            await StatusBar?.setBackgroundColor({ color: '#1a1a1a' });

            // Hide splash after page loads
            setTimeout(() => SplashScreen?.hide(), 300);
        },

        async hideKeyboard() {
            if (!isNative()) return;
            plugins().Keyboard?.hide();
        },
    };

    // =========================================================================
    // DEVICE INFO
    // =========================================================================
    const device = {
        async getInfo() {
            if (!isNative()) return null;
            return plugins().Device?.getInfo();
        },
        async getId() {
            if (!isNative()) return null;
            return plugins().Device?.getId();
        },
    };

    // =========================================================================
    // DEEP LINK HANDLER
    // =========================================================================
    const deepLinks = {
        init() {
            if (!isNative()) return;
            const { App } = plugins();
            App?.addListener('appUrlOpen', (event) => {
                // e.g. gighala://app/gigs/123 → navigate to /gigs/123
                const url = new URL(event.url);
                const path = url.pathname || url.host + url.pathname;
                if (path && path !== '/') window.location.href = path;
            });

            // Handle back button on Android
            App?.addListener('backButton', ({ canGoBack }) => {
                if (canGoBack) window.history.back();
                else App.exitApp();
            });
        },
    };

    // =========================================================================
    // INITIALISE EVERYTHING
    // =========================================================================
    const init = async () => {
        if (!isNative()) return;

        // Add mobile class for CSS targeting
        document.documentElement.classList.add('is-mobile-app');
        document.body.classList.add('capacitor-app');

        await ui.init();
        await pushNotifications.init();
        network.watchConnectivity();
        deepLinks.init();

        // Intercept all file/photo input elements and replace with native camera
        document.addEventListener('click', async (e) => {
            const trigger = e.target.closest('[data-native-camera]');
            if (!trigger) return;
            e.preventDefault();
            const targetInput = document.querySelector(trigger.dataset.nativeCamera);
            try {
                const photo = await camera.pickPhoto({
                    source: trigger.dataset.cameraSource || 'PROMPT',
                });
                // Create a synthetic File and assign to the hidden input
                const blob = camera.base64ToBlob(photo.base64, `image/${photo.format}`);
                const file = new File([blob], `photo.${photo.format}`, { type: `image/${photo.format}` });
                const dt = new DataTransfer();
                dt.items.add(file);
                if (targetInput) targetInput.files = dt.files;
                // Show preview if a preview img exists
                const preview = document.querySelector(trigger.dataset.preview);
                if (preview) preview.src = photo.dataUrl;
                haptics.light();
            } catch (err) {
                console.warn('[GigHala] Camera pick cancelled or failed:', err);
            }
        });

        console.log('[GigHala] Capacitor bridge initialised');
    };

    // Auto-init when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ── Public API ────────────────────────────────────────────────────────────
    return {
        isNative,
        pushNotifications,
        camera,
        biometric,
        haptics,
        network,
        ui,
        device,
        deepLinks,
    };
})();

window.GigHalaMobile = GigHalaMobile;
