import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useArtifactUpdates } from '../useArtifactUpdates';
import { useArtifactStore } from '@/app/stores/useArtifactStore';
import type { Artifact } from '@/app/types/audit';

describe('useArtifactUpdates', () => {
  let originalRequestIdleCallback: typeof window.requestIdleCallback | undefined;
  let originalCancelIdleCallback: typeof window.cancelIdleCallback | undefined;

  beforeEach(() => {
    vi.useFakeTimers();

    originalRequestIdleCallback = window.requestIdleCallback;
    originalCancelIdleCallback = window.cancelIdleCallback;

    useArtifactStore.setState({
      artifacts: [],
      activeArtifactId: null,
      pinnedArtifactId: null,
      splitLayout: 'none',
      splitRatio: 0.4,
    });

    vi.spyOn(useArtifactStore.getState(), 'updateArtifact');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.clearAllTimers();
    vi.useRealTimers();

    if (originalRequestIdleCallback) {
      window.requestIdleCallback = originalRequestIdleCallback;
    } else {
      delete (window as any).requestIdleCallback;
    }

    if (originalCancelIdleCallback) {
      window.cancelIdleCallback = originalCancelIdleCallback;
    } else {
      delete (window as any).cancelIdleCallback;
    }
  });

  describe('Priority Categorization', () => {
    it('should categorize active artifact updates as P0 (immediate)', () => {
      useArtifactStore.setState({ activeArtifactId: 'artifact-1' });

      const { result } = renderHook(() => useArtifactUpdates());

      const mockUpdates: Partial<Artifact> = { title: 'Updated Title' };

      act(() => {
        result.current.queueUpdate('artifact-1', mockUpdates);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-1', mockUpdates);
      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledTimes(1);
    });

    it('should categorize pinned artifact updates as P1 (debounced)', () => {
      useArtifactStore.setState({ pinnedArtifactId: 'artifact-2' });

      const { result } = renderHook(() => useArtifactUpdates());

      const mockUpdates: Partial<Artifact> = { title: 'Pinned Update' };

      act(() => {
        result.current.queueUpdate('artifact-2', mockUpdates);
      });

      expect(useArtifactStore.getState().updateArtifact).not.toHaveBeenCalled();

      act(() => {
        vi.advanceTimersByTime(200);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-2', mockUpdates);
      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledTimes(1);
    });

    it('should categorize background artifact updates as P2 (idle callback)', () => {
      window.requestIdleCallback = vi.fn((callback) => {
        callback({
          didTimeout: false,
          timeRemaining: () => 50,
        });
        return 1;
      });

      const { result } = renderHook(() => useArtifactUpdates());

      const mockUpdates: Partial<Artifact> = { title: 'Background Update' };

      act(() => {
        result.current.queueUpdate('artifact-3', mockUpdates);
      });

      expect(window.requestIdleCallback).toHaveBeenCalled();
      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-3', mockUpdates);
    });
  });

  describe('Queue Processing', () => {
    it('should process P0 updates immediately without debounce', () => {
      useArtifactStore.setState({ activeArtifactId: 'artifact-1' });

      const { result } = renderHook(() => useArtifactUpdates());

      const updates1: Partial<Artifact> = { title: 'Update 1' };
      const updates2: Partial<Artifact> = { title: 'Update 2' };

      act(() => {
        result.current.queueUpdate('artifact-1', updates1);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-1', updates1);

      act(() => {
        result.current.queueUpdate('artifact-1', updates2);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-1', updates2);
      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledTimes(2);
    });

    it('should debounce P1 updates at 200ms', () => {
      useArtifactStore.setState({ pinnedArtifactId: 'artifact-2' });

      const { result } = renderHook(() => useArtifactUpdates());

      const updates1: Partial<Artifact> = { title: 'Update 1' };
      const updates2: Partial<Artifact> = { title: 'Update 2' };
      const updates3: Partial<Artifact> = { title: 'Update 3' };

      act(() => {
        result.current.queueUpdate('artifact-2', updates1);
      });

      act(() => {
        vi.advanceTimersByTime(100);
      });

      act(() => {
        result.current.queueUpdate('artifact-2', updates2);
      });

      act(() => {
        vi.advanceTimersByTime(100);
      });

      act(() => {
        result.current.queueUpdate('artifact-2', updates3);
      });

      expect(useArtifactStore.getState().updateArtifact).not.toHaveBeenCalled();

      act(() => {
        vi.advanceTimersByTime(200);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-2', updates3);
      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledTimes(1);
    });

    it('should use requestIdleCallback for P2 updates', () => {
      const requestIdleCallbackSpy = vi.fn((callback) => {
        callback({
          didTimeout: false,
          timeRemaining: () => 50,
        });
        return 1;
      });

      window.requestIdleCallback = requestIdleCallbackSpy;
      window.cancelIdleCallback = vi.fn();

      const { result } = renderHook(() => useArtifactUpdates());

      const mockUpdates: Partial<Artifact> = { title: 'Idle Update' };

      act(() => {
        result.current.queueUpdate('artifact-3', mockUpdates);
      });

      expect(requestIdleCallbackSpy).toHaveBeenCalled();
      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-3', mockUpdates);
    });

    it('should fallback to setTimeout when requestIdleCallback is not available', () => {
      delete (window as any).requestIdleCallback;
      delete (window as any).cancelIdleCallback;

      const { result } = renderHook(() => useArtifactUpdates());

      const mockUpdates: Partial<Artifact> = { title: 'Fallback Update' };

      act(() => {
        result.current.queueUpdate('artifact-3', mockUpdates);
      });

      expect(useArtifactStore.getState().updateArtifact).not.toHaveBeenCalled();

      act(() => {
        vi.advanceTimersByTime(500);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-3', mockUpdates);
    });
  });

  describe('Integration with useArtifactStore', () => {
    it('should call updateArtifact with correct arguments', () => {
      useArtifactStore.setState({ activeArtifactId: 'artifact-1' });

      const { result } = renderHook(() => useArtifactUpdates());

      const mockUpdates: Partial<Artifact> = {
        title: 'New Title',
        updatedAt: new Date(),
      };

      act(() => {
        result.current.queueUpdate('artifact-1', mockUpdates);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-1', mockUpdates);
    });

    it('should handle multiple artifact updates correctly', () => {
      useArtifactStore.setState({
        activeArtifactId: 'artifact-1',
        pinnedArtifactId: 'artifact-2',
      });

      const { result } = renderHook(() => useArtifactUpdates());

      const updates1: Partial<Artifact> = { title: 'Active Update' };
      const updates2: Partial<Artifact> = { title: 'Pinned Update' };
      const updates3: Partial<Artifact> = { title: 'Background Update' };

      window.requestIdleCallback = vi.fn((callback) => {
        callback({
          didTimeout: false,
          timeRemaining: () => 50,
        });
        return 1;
      });

      act(() => {
        result.current.queueUpdate('artifact-1', updates1);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-1', updates1);

      act(() => {
        result.current.queueUpdate('artifact-2', updates2);
      });

      act(() => {
        vi.advanceTimersByTime(200);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-2', updates2);

      act(() => {
        result.current.queueUpdate('artifact-3', updates3);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-3', updates3);
    });
  });

  describe('Cleanup', () => {
    it('should clear P1 timer on unmount', () => {
      useArtifactStore.setState({ pinnedArtifactId: 'artifact-2' });

      const { result, unmount } = renderHook(() => useArtifactUpdates());

      act(() => {
        result.current.queueUpdate('artifact-2', { title: 'Test' });
      });

      unmount();

      act(() => {
        vi.advanceTimersByTime(200);
      });

      expect(useArtifactStore.getState().updateArtifact).not.toHaveBeenCalled();
    });

    it('should cancel P2 idle callback on unmount', () => {
      const cancelIdleCallbackSpy = vi.fn();
      window.requestIdleCallback = vi.fn(() => 1);
      window.cancelIdleCallback = cancelIdleCallbackSpy;

      const { result, unmount } = renderHook(() => useArtifactUpdates());

      act(() => {
        result.current.queueUpdate('artifact-3', { title: 'Test' });
      });

      unmount();

      expect(cancelIdleCallbackSpy).toHaveBeenCalledWith(1);
    });

    it('should cancel P2 setTimeout on unmount when requestIdleCallback not available', () => {
      delete (window as any).requestIdleCallback;
      delete (window as any).cancelIdleCallback;

      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

      const { result, unmount } = renderHook(() => useArtifactUpdates());

      act(() => {
        result.current.queueUpdate('artifact-3', { title: 'Test' });
      });

      unmount();

      expect(clearTimeoutSpy).toHaveBeenCalled();
    });

    it('should clear all queues on unmount', () => {
      useArtifactStore.setState({
        activeArtifactId: 'artifact-1',
        pinnedArtifactId: 'artifact-2',
      });

      window.requestIdleCallback = vi.fn((callback) => {
        callback({
          didTimeout: false,
          timeRemaining: () => 50,
        });
        return 1;
      });

      const { result, unmount } = renderHook(() => useArtifactUpdates());

      act(() => {
        result.current.queueUpdate('artifact-1', { title: 'P0' });
        result.current.queueUpdate('artifact-2', { title: 'P1' });
        result.current.queueUpdate('artifact-3', { title: 'P2' });
      });

      const callCount = (useArtifactStore.getState().updateArtifact as any).mock.calls.length;

      unmount();

      act(() => {
        vi.advanceTimersByTime(500);
      });

      expect((useArtifactStore.getState().updateArtifact as any).mock.calls.length).toBe(callCount);
    });
  });

  describe('Edge Cases', () => {
    it('should merge multiple updates to the same artifact (P1)', () => {
      useArtifactStore.setState({ pinnedArtifactId: 'artifact-2' });

      const { result } = renderHook(() => useArtifactUpdates());

      act(() => {
        result.current.queueUpdate('artifact-2', { title: 'First Update' });
        result.current.queueUpdate('artifact-2', { title: 'Second Update' });
        result.current.queueUpdate('artifact-2', { title: 'Third Update' });
      });

      act(() => {
        vi.advanceTimersByTime(200);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-2', { title: 'Third Update' });
      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledTimes(1);
    });

    it('should merge multiple updates to the same artifact (P2)', () => {
      let idleCallbackId = 1;
      const pendingCallbacks = new Map<number, IdleRequestCallback>();

      window.requestIdleCallback = vi.fn((callback) => {
        const id = idleCallbackId++;
        pendingCallbacks.set(id, callback);
        return id;
      });

      window.cancelIdleCallback = vi.fn((id) => {
        pendingCallbacks.delete(id);
      });

      const { result } = renderHook(() => useArtifactUpdates());

      act(() => {
        result.current.queueUpdate('artifact-3', { title: 'First Update' });
        result.current.queueUpdate('artifact-3', { title: 'Second Update' });
      });

      expect(window.cancelIdleCallback).toHaveBeenCalledWith(1);

      act(() => {
        const lastCallback = Array.from(pendingCallbacks.values()).pop();
        if (lastCallback) {
          lastCallback({
            didTimeout: false,
            timeRemaining: () => 50,
          });
        }
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-3', { title: 'Second Update' });
      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledTimes(1);
    });

    it('should not process updates after unmount', () => {
      useArtifactStore.setState({ pinnedArtifactId: 'artifact-2' });

      const { result, unmount } = renderHook(() => useArtifactUpdates());

      act(() => {
        result.current.queueUpdate('artifact-2', { title: 'Test' });
      });

      unmount();

      const initialCallCount = (useArtifactStore.getState().updateArtifact as any).mock.calls.length;

      act(() => {
        vi.advanceTimersByTime(200);
      });

      expect((useArtifactStore.getState().updateArtifact as any).mock.calls.length).toBe(initialCallCount);
    });

    it('should handle priority changes for the same artifact', () => {
      useArtifactStore.setState({ activeArtifactId: 'artifact-1' });

      const { result, rerender } = renderHook(() => useArtifactUpdates());

      act(() => {
        result.current.queueUpdate('artifact-1', { title: 'Active Update' });
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledTimes(1);

      useArtifactStore.setState({ activeArtifactId: null, pinnedArtifactId: 'artifact-1' });
      rerender();

      act(() => {
        result.current.queueUpdate('artifact-1', { title: 'Now Pinned' });
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledTimes(1);

      act(() => {
        vi.advanceTimersByTime(200);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledTimes(2);
      expect(useArtifactStore.getState().updateArtifact).toHaveBeenLastCalledWith('artifact-1', { title: 'Now Pinned' });
    });

    it('should cancel previous P2 idle callback when new update arrives', () => {
      const cancelIdleCallbackSpy = vi.fn();
      let callbackId = 1;

      window.requestIdleCallback = vi.fn(() => callbackId++);
      window.cancelIdleCallback = cancelIdleCallbackSpy;

      const { result } = renderHook(() => useArtifactUpdates());

      act(() => {
        result.current.queueUpdate('artifact-3', { title: 'First Update' });
      });

      expect(window.requestIdleCallback).toHaveBeenCalledTimes(1);

      act(() => {
        result.current.queueUpdate('artifact-3', { title: 'Second Update' });
      });

      expect(cancelIdleCallbackSpy).toHaveBeenCalledWith(1);
      expect(window.requestIdleCallback).toHaveBeenCalledTimes(2);
    });

    it('should cancel previous P2 setTimeout when requestIdleCallback not available', () => {
      delete (window as any).requestIdleCallback;
      delete (window as any).cancelIdleCallback;

      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

      const { result } = renderHook(() => useArtifactUpdates());

      act(() => {
        result.current.queueUpdate('artifact-3', { title: 'First Update' });
      });

      act(() => {
        result.current.queueUpdate('artifact-3', { title: 'Second Update' });
      });

      expect(clearTimeoutSpy).toHaveBeenCalled();
    });

    it('should handle complex partial Artifact updates', () => {
      useArtifactStore.setState({ activeArtifactId: 'artifact-1' });

      const { result } = renderHook(() => useArtifactUpdates());

      const complexUpdate: Partial<Artifact> = {
        title: 'Complex Update',
        updatedAt: new Date('2024-01-01'),
        status: 'complete',
      };

      act(() => {
        result.current.queueUpdate('artifact-1', complexUpdate);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-1', complexUpdate);
    });
  });

  describe('Concurrency', () => {
    it('should handle rapid P0 updates without loss', () => {
      useArtifactStore.setState({ activeArtifactId: 'artifact-1' });

      const { result } = renderHook(() => useArtifactUpdates());

      act(() => {
        for (let i = 0; i < 10; i++) {
          result.current.queueUpdate('artifact-1', { title: `Update ${i}` });
        }
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledTimes(10);
    });

    it('should handle rapid P1 updates with proper debouncing', () => {
      useArtifactStore.setState({ pinnedArtifactId: 'artifact-2' });

      const { result } = renderHook(() => useArtifactUpdates());

      act(() => {
        for (let i = 0; i < 5; i++) {
          result.current.queueUpdate('artifact-2', { title: `Update ${i}` });
          vi.advanceTimersByTime(50);
        }
      });

      expect(useArtifactStore.getState().updateArtifact).not.toHaveBeenCalled();

      act(() => {
        vi.advanceTimersByTime(200);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledTimes(1);
      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-2', { title: 'Update 4' });
    });

    it('should handle mixed priority updates correctly', () => {
      useArtifactStore.setState({
        activeArtifactId: 'artifact-1',
        pinnedArtifactId: 'artifact-2',
      });

      window.requestIdleCallback = vi.fn((callback) => {
        callback({
          didTimeout: false,
          timeRemaining: () => 50,
        });
        return 1;
      });

      const { result } = renderHook(() => useArtifactUpdates());

      act(() => {
        result.current.queueUpdate('artifact-1', { title: 'P0 Update' });
        result.current.queueUpdate('artifact-2', { title: 'P1 Update' });
        result.current.queueUpdate('artifact-3', { title: 'P2 Update' });
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-1', { title: 'P0 Update' });
      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-3', { title: 'P2 Update' });

      act(() => {
        vi.advanceTimersByTime(200);
      });

      expect(useArtifactStore.getState().updateArtifact).toHaveBeenCalledWith('artifact-2', { title: 'P1 Update' });
    });
  });
});
