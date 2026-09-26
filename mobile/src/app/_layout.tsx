import { Fraunces_400Regular_Italic, Fraunces_500Medium } from '@expo-google-fonts/fraunces';
import {
  PublicSans_400Regular,
  PublicSans_600SemiBold,
  PublicSans_700Bold,
} from '@expo-google-fonts/public-sans';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { EG_TOKENS } from '@/design-system';

SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  // Keys become the fontFamily names used in EG_FONTS.
  const [loaded, error] = useFonts({
    Fraunces_500Medium,
    Fraunces_400Regular_Italic,
    PublicSans_400Regular,
    PublicSans_600SemiBold,
    PublicSans_700Bold,
  });

  useEffect(() => {
    if (loaded || error) SplashScreen.hideAsync().catch(() => {});
  }, [loaded, error]);

  // A font failure falls back to system fonts rather than a blank app.
  if (!loaded && !error) return null;

  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: EG_TOKENS.paper },
        }}
      />
    </>
  );
}
