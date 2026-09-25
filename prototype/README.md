# ElderGuard prototype (frozen)

This is the original Vite + React click-through of the 19 hi-fi screens in the warm-letter design language. It is kept only as a visual reference while the screens are rebuilt in the Expo app under `mobile/`. It is not deployed and not maintained, and it will be deleted once `mobile/` covers every screen.

The pieces that carry forward, and where they went:

- `src/design-system/tokens.ts` copied verbatim into the mobile design system
- `src/design-system/BrassDial.tsx` lines 17-54 (dial geometry) ported unchanged to react-native-svg
- `src/navigator/types.ts` `ScreenId` union became the mobile route inventory

To look at it locally:

```bash
cd prototype
npm install
npm run dev
```
