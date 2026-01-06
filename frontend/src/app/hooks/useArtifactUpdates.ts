import { useEffect, useRef, useCallback } from 'react';
import { useArtifactStore } from '../stores/useArtifactStore';
import type { Artifact } from '../types/audit';

type Priority = 'P0' | 'P1' | 'P2';

interface QueuedUpdate {
  artifactId: string;
  updates: Partial<Artifact>;
  priority: Priority;
  timestamp: number;
}

export function useArtifactUpdates() {
  const { activeArtifactId, pinnedArtifactId, updateArtifact } = useArtifactStore();

  const p0QueueRef = useRef<Map<string, QueuedUpdate>>(new Map());
  const p1QueueRef = useRef<Map<string, QueuedUpdate>>(new Map());
  const p2QueueRef = useRef<Map<string, QueuedUpdate>>(new Map());

  const p1TimerRef = useRef<NodeJS.Timeout | null>(null);
  const p2IdleCallbackRef = useRef<number | null>(null);

  const isMountedRef = useRef(true);

  const processP0Updates = useCallback(() => {
    if (!isMountedRef.current) return;

    p0QueueRef.current.forEach((update) => {
      updateArtifact(update.artifactId, update.updates);
    });
    p0QueueRef.current.clear();
  }, [updateArtifact]);

  const processP1Updates = useCallback(() => {
    if (!isMountedRef.current) return;

    p1QueueRef.current.forEach((update) => {
      updateArtifact(update.artifactId, update.updates);
    });
    p1QueueRef.current.clear();
  }, [updateArtifact]);

  const processP2Updates = useCallback(() => {
    if (!isMountedRef.current) return;

    p2QueueRef.current.forEach((update) => {
      updateArtifact(update.artifactId, update.updates);
    });
    p2QueueRef.current.clear();
  }, [updateArtifact]);

  const queueUpdate = useCallback(
    (artifactId: string, updates: Partial<Artifact>) => {
      if (!isMountedRef.current) return;

      let priority: Priority;

      if (artifactId === activeArtifactId) {
        priority = 'P0';
      } else if (artifactId === pinnedArtifactId) {
        priority = 'P1';
      } else {
        priority = 'P2';
      }

      const queuedUpdate: QueuedUpdate = {
        artifactId,
        updates,
        priority,
        timestamp: Date.now(),
      };

      if (priority === 'P0') {
        p0QueueRef.current.set(artifactId, queuedUpdate);
        processP0Updates();
      } else if (priority === 'P1') {
        p1QueueRef.current.set(artifactId, queuedUpdate);

        if (p1TimerRef.current) {
          clearTimeout(p1TimerRef.current);
        }

        p1TimerRef.current = setTimeout(() => {
          processP1Updates();
          p1TimerRef.current = null;
        }, 200);
      } else {
        p2QueueRef.current.set(artifactId, queuedUpdate);

        if (p2IdleCallbackRef.current) {
          if (typeof window !== 'undefined' && 'cancelIdleCallback' in window) {
            window.cancelIdleCallback(p2IdleCallbackRef.current);
          } else {
            clearTimeout(p2IdleCallbackRef.current);
          }
        }

        if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
          p2IdleCallbackRef.current = window.requestIdleCallback(() => {
            processP2Updates();
            p2IdleCallbackRef.current = null;
          });
        } else {
          p2IdleCallbackRef.current = setTimeout(() => {
            processP2Updates();
            p2IdleCallbackRef.current = null;
          }, 500) as unknown as number;
        }
      }
    },
    [activeArtifactId, pinnedArtifactId, processP0Updates, processP1Updates, processP2Updates]
  );

  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;

      if (p1TimerRef.current) {
        clearTimeout(p1TimerRef.current);
        p1TimerRef.current = null;
      }

      if (p2IdleCallbackRef.current) {
        if (typeof window !== 'undefined' && 'cancelIdleCallback' in window) {
          window.cancelIdleCallback(p2IdleCallbackRef.current);
        } else {
          clearTimeout(p2IdleCallbackRef.current);
        }
        p2IdleCallbackRef.current = null;
      }

      p0QueueRef.current.clear();
      p1QueueRef.current.clear();
      p2QueueRef.current.clear();
    };
  }, []);

  return {
    queueUpdate,
  };
}
