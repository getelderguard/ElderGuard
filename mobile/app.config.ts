/// <reference types="node" />
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

import type { ExpoConfig } from 'expo/config';

// Forks override the store identifiers with their own reverse-DNS IDs. Store IDs are permanent
// once published, so a fork must not ship under ours.
const BUNDLE_ID = process.env.EG_BUNDLE_ID ?? 'org.getelderguard.app';
const APP_NAME = process.env.EG_APP_NAME ?? 'ElderGuard';
// Your Apple Developer team, for device builds. Set it in .env.local; forks use their own.
const APPLE_TEAM_ID = process.env.EG_APPLE_TEAM_ID;

// Firebase client configs are per-project and gitignored (they hold an API key). Download your
// own from your Firebase project into these paths, or point the env vars elsewhere. Without them
// the app still bundles (CI does this), but a native build has no Firebase and cannot sign in.
const IOS_FIREBASE = process.env.EG_IOS_GOOGLE_SERVICES ?? './GoogleService-Info.plist';
const ANDROID_FIREBASE = process.env.EG_ANDROID_GOOGLE_SERVICES ?? './google-services.json';
const hasIosFirebase = existsSync(resolve(__dirname, IOS_FIREBASE));
const hasAndroidFirebase = existsSync(resolve(__dirname, ANDROID_FIREBASE));
const firebasePlugins: ExpoConfig['plugins'] =
  hasIosFirebase && hasAndroidFirebase
    ? [
        // With static frameworks, Firebase must come from CocoaPods, not Swift Package Manager.
        ['@react-native-firebase/app', { ios: { disableSPM: true } }],
        '@react-native-firebase/auth',
      ]
    : [];

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
    ...(APPLE_TEAM_ID ? { appleTeamId: APPLE_TEAM_ID } : {}),
    supportsTablet: false,
    ...(hasIosFirebase ? { googleServicesFile: IOS_FIREBASE } : {}),
  },
  android: {
    package: BUNDLE_ID,
    ...(hasAndroidFirebase ? { googleServicesFile: ANDROID_FIREBASE } : {}),
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
    // React Native Firebase needs static frameworks on iOS.
    ['expo-build-properties', { ios: { useFrameworks: 'static' } }],
    ...firebasePlugins,
  ],
  experiments: {
    typedRoutes: true,
    reactCompiler: true,
  },
};

export default config;
