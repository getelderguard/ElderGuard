# ElderGuard mobile

The Expo / React Native app for iOS and Android. One codebase, built with EAS.

## Run it

```bash
cd mobile
npm install
npx expo start
```

Scan the QR code with Expo Go. Once Firebase and push notifications land, the app needs a development build (`npx eas-cli@latest build --profile development`) instead of Expo Go.

## Checks

```bash
npx tsc --noEmit
npx expo-doctor
npx expo export --platform ios --platform android
```

CI runs the typecheck, `npm audit --audit-level=high`, and both bundles.

## Forking

Store identifiers are permanent once published. Set your own before your first build:

```bash
EG_BUNDLE_ID=org.example.guardian EG_APP_NAME="Your Guardian" npx expo start
```

Firebase client configs (`google-services.json`, `GoogleService-Info.plist`) contain API keys and are gitignored. Provide them to EAS as file secrets.

## Layout

- `src/app/` routes (expo-router). Every file is a screen.
- `src/design-system/` tokens, type, buttons, Letterhead, BrassDial, ported from `prototype/`.
- `src/session/` live-call state. Tiers mirror the backend; there is no "safe" tier.
- `licenses/` OFL texts for the bundled Fraunces and Public Sans fonts.
