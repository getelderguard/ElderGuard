import * as ImagePicker from 'expo-image-picker';
import { useState } from 'react';

import { imageBytes, MAX_IMAGE_BYTES } from '@/api/show';

export type Picture = { uri: string; b64: string };

// Picks a screenshot or takes a photo. The picture is held in memory only, and the base64 is what
// goes to the backend. `problem` is plain words for the senior, never an error code.
export function usePicture() {
  const [picture, setPicture] = useState<Picture | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  const take = (r: ImagePicker.ImagePickerResult) => {
    if (r.canceled) return;
    const a = r.assets[0];
    if (!a?.base64) {
      setProblem('That picture could not be read. Please try another.');
      return;
    }
    // Check here as well as on the server, so she is not left waiting on a doomed upload.
    if (imageBytes(a.base64) > MAX_IMAGE_BYTES) {
      setProblem('That picture is too large. Try a smaller one.');
      return;
    }
    setProblem(null);
    setPicture({ uri: a.uri, b64: a.base64 });
  };

  const choose = async () => {
    try {
      // The system photo picker shows only what she taps, so no library permission is asked for.
      take(await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], base64: true, quality: 0.6 }));
    } catch {
      setProblem('The photo picker could not open.');
    }
  };

  const photograph = async () => {
    try {
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) {
        setProblem(
          'To photograph a letter, allow the camera in your phone’s Settings. You can also choose a screenshot instead.',
        );
        return;
      }
      take(await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], base64: true, quality: 0.6 }));
    } catch {
      setProblem('The camera could not open.');
    }
  };

  const clear = () => {
    setPicture(null);
    setProblem(null);
  };

  return { picture, problem, choose, photograph, clear };
}
