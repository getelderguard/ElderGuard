import type { ExpoConfig } from 'expo/config';

// Forks override the store identifiers with their own reverse-DNS IDs. Store IDs are permanent
// once published, so a fork must not ship under ours.
const BUNDLE_ID = process.env.EG_BUNDLE_ID ?? 'org.getelderguard.app';
const APP_NAME = process.env.EG_APP_NAME ?? 'ElderGuard';

const config: ExpoConfig = {
  name: APP_NAME,
  slug: 'elderguard',
  version: '0.1.0',
  orientation: 'portrait',
  icon: './assets/images/icon.png',
  scheme: 'elderguard',
  userInterfaceStyle: 'light',
  ios: {
    bundleIdentifier: BUNDLE_ID,
    supportsTablet: false,
  },
  android: {
    package: BUNDLE_ID,
    adaptiveIcon: {
      backgroundColor: '#f5ede0',
      foregroundImage: './assets/images/android-icon-foreground.png',
      backgroundImage: './assets/images/android-icon-background.png',
      monochromeImage: './assets/images/android-icon-monochrome.png',
    },
    predictiveBackGestureEnabled: false,
  },
  plugins: [
    'expo-router',
    'expo-font',
    [
      'expo-splash-screen',
      {
        backgroundColor: '#f5ede0',
        image: './assets/images/splash-icon.png',
        imageWidth: 76,
      },
    ],
  ],
  experiments: {
    typedRoutes: true,
    reactCompiler: true,
  },
};

export default config;
