import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.gighala.app',
  appName: 'GigHala',
  webDir: 'www',
  // Point to your live Flask server (update with your Railway/production URL)
  server: {
    url: process.env.CAPACITOR_SERVER_URL || 'https://gighala.up.railway.app',
    cleartext: false,
    allowNavigation: [
      'gighala.up.railway.app',
      '*.gighala.com',
      'accounts.google.com',
      '*.stripe.com',
    ],
  },
  android: {
    buildOptions: {
      keystorePath: 'release.keystore',
      keystorePassword: process.env.KEYSTORE_PASSWORD || '',
      keystoreAlias: 'gighala',
      keystoreAliasPassword: process.env.KEYSTORE_ALIAS_PASSWORD || '',
    },
    // Enable mixed content for development (disable in prod)
    allowMixedContent: false,
    captureInput: true,
    webContentsDebuggingEnabled: false,
    backgroundColor: '#1a1a1a',
    loggingBehavior: 'none',
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#1a1a1a',
      androidSplashResourceName: 'splash',
      androidScaleType: 'CENTER_CROP',
      showSpinner: false,
      androidSpinnerStyle: 'large',
      iosSpinnerStyle: 'small',
      spinnerColor: '#00C853',
      splashFullScreen: true,
      splashImmersive: true,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#1a1a1a',
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    LocalNotifications: {
      smallIcon: 'ic_stat_gighala',
      iconColor: '#00C853',
      sound: 'beep.wav',
    },
    Camera: {
      permissions: ['camera', 'photos'],
    },
    Keyboard: {
      resize: 'body',
      style: 'DARK',
      resizeOnFullScreen: true,
    },
  },
};

export default config;
