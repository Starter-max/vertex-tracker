'use client';

import { useEffect, useState } from 'react';
import { AppState } from './types';
import { getAppState, saveAppState } from './storage';

export function useAppState() { const [state, setState] = useState<AppState>(getAppState()); useEffect(() => saveAppState(state), [state]); return { state, setState }; }
