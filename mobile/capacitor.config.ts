import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.fplaipro.app',
  appName: 'FPL AI Pro',
  webDir: '../frontend',          // reuse the existing index.html directly

  server: {
    // Allow the app to reach the production API.
    // AndroidScheme: 'https' avoids mixed-content warnings on Android 9+
    androidScheme: 'https',
    // Uncomment the line below to load the live site instead of bundled files
    // (useful for testing but requires internet — bundled files work offline for UI):
    // url: 'https://epl-prediction-app.web.app',
    allowNavigation: [
      'epl-prediction-app.web.app',
      'www.payfast.co.za',
      'sandbox.payfast.co.za',
    ],
  },

  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#050a0c',
      androidSplashResourceName: 'splash',
      androidScaleType: 'CENTER_CROP',
      showSpinner: false,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#050a0c',
    },
    Keyboard: {
      resize: 'body',
      style: 'DARK',
    },
  },

  android: {
    buildOptions: {
      keystorePath: 'fpl-ai-pro.keystore',
      keystoreAlias: 'fplaipro',
    },
  },

  ios: {
    contentInset: 'always',
  },
};

export default config;
