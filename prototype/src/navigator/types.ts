export type ScreenId =
  | 'ob-splash'
  | 'ob-1'
  | 'ob-2'
  | 'ob-3'
  | 'ob-4'
  | 'home'
  | 'profile'
  | 'call-clear'
  | 'call-caution'
  | 'call-checking'
  | 'call-takeover'
  | 'call-noVoice'
  | 'call-falseAlarm'
  | 'show-empty'
  | 'show-q1'
  | 'show-q2'
  | 'verdict-ok'
  | 'verdict-care'
  | 'verdict-no';

export type Nav = (id: ScreenId) => void;
