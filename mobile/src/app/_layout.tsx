import {
  CormorantGaramond_500Medium,
  CormorantGaramond_500Medium_Italic,
  CormorantGaramond_600SemiBold,
} from '@expo-google-fonts/cormorant-garamond';
import { Inter_400Regular, Inter_500Medium, Inter_600SemiBold } from '@expo-google-fonts/inter';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { AuthGate, useAuth } from '@/auth/AuthGate';
import { EG_TOKENS } from '@/design-system';

SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  // Keys become the fontFamily names used in EG_FONTS.
  const [loaded, error] = useFonts({
    CormorantGaramond_500Medium,
    CormorantGaramond_500Medium_Italic,
    CormorantGaramond_600SemiBold,
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
  });

  // A font failure falls back to system fonts rather than a blank app.
  if (!loaded && !error) return null;

  return (
    <AuthGate>
      <StatusBar style="dark" />
      <Routes />
    </AuthGate>
  );
}

// Each group is reachable only in its phase; when the phase changes, the router moves to the
// first screen the new phase allows.
function Routes() {
  const { phase } = useAuth();

  useEffect(() => {
    if (phase !== 'loading') SplashScreen.hideAsync().catch(() => {});
  }, [phase]);

  if (phase === 'loading') return null;

  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: EG_TOKENS.sand } }}>
      <Stack.Protected guard={phase === 'ready'}>
        <Stack.Screen name="(app)/(tabs)" />
        <Stack.Screen name="(app)/call/[sessionId]" />
      </Stack.Protected>
      <Stack.Protected guard={phase === 'signed_out'}>
        <Stack.Screen name="(signin)/welcome" />
        <Stack.Screen name="(signin)/phone" />
        <Stack.Screen name="(signin)/code" />
      </Stack.Protected>
      <Stack.Protected guard={phase === 'needs_setup'}>
        <Stack.Screen name="(setup)/about-you" />
        <Stack.Screen name="(setup)/consent" />
      </Stack.Protected>
      <Stack.Protected guard={phase === 'offline'}>
        <Stack.Screen name="offline" />
      </Stack.Protected>
    </Stack>
  );
}
