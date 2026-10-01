import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { Tabs } from 'expo-router';
import type { ColorValue } from 'react-native';

import { EG_FONTS, EG_TOKENS } from '@/design-system';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

// Two places, always visible at the bottom: the live call guardian, and Show Me for a message.
// Icons always come with a word, and the bar is tall, so nobody has to guess what a symbol means.
function icon(active: IconName, idle: IconName) {
  return function TabIcon({ focused, color }: { focused: boolean; color: ColorValue }) {
    return <Ionicons name={focused ? active : idle} size={28} color={String(color)} />;
  };
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: EG_TOKENS.sand },
        tabBarActiveTintColor: EG_TOKENS.turquoiseDark,
        tabBarInactiveTintColor: EG_TOKENS.textMid,
        tabBarAllowFontScaling: true,
        tabBarLabelStyle: { fontFamily: EG_FONTS.sansSemi, fontSize: 14 },
        tabBarStyle: {
          backgroundColor: EG_TOKENS.creamLight,
          borderTopColor: EG_TOKENS.border,
          minHeight: 68,
          paddingTop: 6,
        },
      }}
      screenListeners={{
        tabPress: () => {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Check a call',
          tabBarIcon: icon('call', 'call-outline'),
          tabBarAccessibilityLabel: 'Check a call. Tab 1 of 2.',
        }}
      />
      <Tabs.Screen
        name="show"
        options={{
          title: 'Show me',
          tabBarIcon: icon('chatbubble-ellipses', 'chatbubble-ellipses-outline'),
          tabBarAccessibilityLabel: 'Show me a message or picture. Tab 2 of 2.',
        }}
      />
    </Tabs>
  );
}
