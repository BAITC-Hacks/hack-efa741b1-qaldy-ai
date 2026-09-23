import { createDemoState } from "./fixtures";
import {
  getBrowserStorage,
  loadDemoState,
  saveDemoState,
} from "./persistence";
import { demoReducer, type DemoAction } from "./reducer";
import type { DemoState, StorageLike } from "./types";

export type DemoStoreListener = (state: DemoState, action: DemoAction) => void;

export type DemoStore = {
  getState(): DemoState;
  dispatch(action: DemoAction): DemoState;
  subscribe(listener: DemoStoreListener): () => void;
  reset(): DemoState;
};

/**
 * Framework-agnostic external store. React can consume it with useSyncExternalStore;
 * tests and server code can use the reducer directly.
 */
export function createDemoStore(options: {
  initialState?: DemoState;
  storage?: StorageLike | null;
  persist?: boolean;
} = {}): DemoStore {
  const initialState = options.initialState ?? createDemoState();
  const storage = options.storage === undefined ? getBrowserStorage() : options.storage;
  const shouldPersist = options.persist ?? true;
  let state = shouldPersist ? loadDemoState(initialState, storage) : initialState;
  const listeners = new Set<DemoStoreListener>();

  const publish = (action: DemoAction): DemoState => {
    if (shouldPersist) saveDemoState(state, storage);
    listeners.forEach((listener) => listener(state, action));
    return state;
  };

  return {
    getState: () => state,
    dispatch: (action) => {
      const next = demoReducer(state, action);
      if (next === state) return state;
      state = next;
      return publish(action);
    },
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    reset: () => {
      state = createDemoState();
      return publish({ type: "replace-state", state });
    },
  };
}
