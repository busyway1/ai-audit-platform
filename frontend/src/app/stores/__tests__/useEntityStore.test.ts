import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useEntityStore } from '../useEntityStore';
import type { Task, Issue, Document } from '../../types/audit';

describe('useEntityStore', () => {
  beforeEach(() => {
    act(() => {
      useEntityStore.getState().clearAll();
    });
  });

  // Helper function to create mock entities
  const createMockTask = (id: string, overrides?: Partial<Task>): Task => ({
    id,
    taskNumber: `T-${id}`,
    title: `Task ${id}`,
    description: `Description for task ${id}`,
    status: 'not-started',
    phase: 'planning',
    accountCategory: 'Assets',
    businessProcess: 'Revenue',
    assignedManager: 'Manager 1',
    assignedStaff: ['Staff 1', 'Staff 2'],
    progress: 0,
    riskLevel: 'medium',
    requiresReview: false,
    dueDate: '2024-12-31',
    createdAt: '2024-01-01',
    ...overrides,
  });

  const createMockIssue = (id: string, overrides?: Partial<Issue>): Issue => ({
    id,
    taskId: 'T-001',
    taskNumber: 'T-001',
    title: `Issue ${id}`,
    description: `Description for issue ${id}`,
    accountCategory: 'Revenue',
    impact: 'medium',
    status: 'open',
    identifiedBy: 'Auditor 1',
    identifiedDate: '2024-01-01',
    requiresAdjustment: false,
    includeInManagementLetter: false,
    ...overrides,
  });

  const createMockDocument = (id: string, overrides?: Partial<Document>): Document => ({
    id,
    name: `Document ${id}`,
    type: 'PDF',
    uploadedBy: 'User 1',
    uploadedAt: '2024-01-01',
    size: '1.5 MB',
    category: 'Financial Statements',
    linkedTasks: ['T-001'],
    ...overrides,
  });

  describe('Task operations', () => {
    describe('addTask', () => {
      it('should add a task to the store', () => {
        const { result } = renderHook(() => useEntityStore());
        const task = createMockTask('001');

        act(() => {
          result.current.addTask(task);
        });

        expect(result.current.getTasks()).toHaveLength(1);
        expect(result.current.getTask('001')).toEqual(task);
      });

      it('should add multiple tasks to the store', () => {
        const { result } = renderHook(() => useEntityStore());
        const task1 = createMockTask('001');
        const task2 = createMockTask('002');

        act(() => {
          result.current.addTask(task1);
          result.current.addTask(task2);
        });

        expect(result.current.getTasks()).toHaveLength(2);
        expect(result.current.getTask('001')).toEqual(task1);
        expect(result.current.getTask('002')).toEqual(task2);
      });

      it('should overwrite task if same id is added', () => {
        const { result } = renderHook(() => useEntityStore());
        const task1 = createMockTask('001', { title: 'Original Task' });
        const task2 = createMockTask('001', { title: 'Updated Task' });

        act(() => {
          result.current.addTask(task1);
          result.current.addTask(task2);
        });

        expect(result.current.getTasks()).toHaveLength(1);
        expect(result.current.getTask('001')?.title).toBe('Updated Task');
      });
    });

    describe('getTask', () => {
      it('should retrieve a task by id with O(1) lookup', () => {
        const { result } = renderHook(() => useEntityStore());
        const task = createMockTask('001');

        act(() => {
          result.current.addTask(task);
        });

        expect(result.current.getTask('001')).toEqual(task);
      });

      it('should return undefined for non-existent task', () => {
        const { result } = renderHook(() => useEntityStore());

        expect(result.current.getTask('999')).toBeUndefined();
      });
    });

    describe('getTasks', () => {
      it('should return empty array when no tasks', () => {
        const { result } = renderHook(() => useEntityStore());

        expect(result.current.getTasks()).toEqual([]);
      });

      it('should return all tasks as an array', () => {
        const { result } = renderHook(() => useEntityStore());
        const task1 = createMockTask('001');
        const task2 = createMockTask('002');

        act(() => {
          result.current.addTask(task1);
          result.current.addTask(task2);
        });

        const tasks = result.current.getTasks();
        expect(tasks).toHaveLength(2);
        expect(tasks).toEqual(expect.arrayContaining([task1, task2]));
      });
    });

    describe('updateTask', () => {
      it('should update task with partial data', () => {
        const { result } = renderHook(() => useEntityStore());
        const task = createMockTask('001', { title: 'Original Title', progress: 0 });

        act(() => {
          result.current.addTask(task);
          result.current.updateTask('001', { title: 'Updated Title', progress: 50 });
        });

        const updatedTask = result.current.getTask('001');
        expect(updatedTask?.title).toBe('Updated Title');
        expect(updatedTask?.progress).toBe(50);
        expect(updatedTask?.description).toBe('Description for task 001');
      });

      it('should handle update of non-existent task gracefully', () => {
        const { result } = renderHook(() => useEntityStore());

        act(() => {
          result.current.updateTask('999', { title: 'Should Not Exist' });
        });

        expect(result.current.getTask('999')).toBeUndefined();
      });

      it('should update only specified fields', () => {
        const { result } = renderHook(() => useEntityStore());
        const task = createMockTask('001', {
          title: 'Original Title',
          status: 'not-started',
          progress: 0,
        });

        act(() => {
          result.current.addTask(task);
          result.current.updateTask('001', { status: 'in-progress' });
        });

        const updatedTask = result.current.getTask('001');
        expect(updatedTask?.status).toBe('in-progress');
        expect(updatedTask?.title).toBe('Original Title');
        expect(updatedTask?.progress).toBe(0);
      });
    });

    describe('removeTask', () => {
      it('should remove a task from the store', () => {
        const { result } = renderHook(() => useEntityStore());
        const task = createMockTask('001');

        act(() => {
          result.current.addTask(task);
          result.current.removeTask('001');
        });

        expect(result.current.getTasks()).toHaveLength(0);
        expect(result.current.getTask('001')).toBeUndefined();
      });

      it('should only remove specified task', () => {
        const { result } = renderHook(() => useEntityStore());
        const task1 = createMockTask('001');
        const task2 = createMockTask('002');

        act(() => {
          result.current.addTask(task1);
          result.current.addTask(task2);
          result.current.removeTask('001');
        });

        expect(result.current.getTasks()).toHaveLength(1);
        expect(result.current.getTask('001')).toBeUndefined();
        expect(result.current.getTask('002')).toEqual(task2);
      });

      it('should handle removal of non-existent task gracefully', () => {
        const { result } = renderHook(() => useEntityStore());

        act(() => {
          result.current.removeTask('999');
        });

        expect(result.current.getTasks()).toHaveLength(0);
      });
    });

    describe('bulkUpdateTasks', () => {
      it('should update multiple tasks in a single call', () => {
        const { result } = renderHook(() => useEntityStore());
        const task1 = createMockTask('001', { progress: 0 });
        const task2 = createMockTask('002', { progress: 0 });
        const task3 = createMockTask('003', { progress: 0 });

        act(() => {
          result.current.addTask(task1);
          result.current.addTask(task2);
          result.current.addTask(task3);
        });

        act(() => {
          result.current.bulkUpdateTasks({
            '001': { progress: 50 },
            '002': { progress: 75 },
          });
        });

        expect(result.current.getTask('001')?.progress).toBe(50);
        expect(result.current.getTask('002')?.progress).toBe(75);
        expect(result.current.getTask('003')?.progress).toBe(0);
      });

      it('should not affect non-existent tasks in bulk update', () => {
        const { result } = renderHook(() => useEntityStore());
        const task1 = createMockTask('001', { progress: 0 });

        act(() => {
          result.current.addTask(task1);
        });

        act(() => {
          result.current.bulkUpdateTasks({
            '001': { progress: 50 },
            '999': { progress: 100 },
          });
        });

        expect(result.current.getTask('001')?.progress).toBe(50);
        expect(result.current.getTask('999')).toBeUndefined();
      });

      it('should handle empty bulk update', () => {
        const { result } = renderHook(() => useEntityStore());
        const task = createMockTask('001', { progress: 50 });

        act(() => {
          result.current.addTask(task);
          result.current.bulkUpdateTasks({});
        });

        expect(result.current.getTask('001')?.progress).toBe(50);
      });
    });

    describe('setTasks', () => {
      it('should replace all tasks with new array', () => {
        const { result } = renderHook(() => useEntityStore());
        const oldTask = createMockTask('001');
        const newTask1 = createMockTask('002');
        const newTask2 = createMockTask('003');

        act(() => {
          result.current.addTask(oldTask);
          result.current.setTasks([newTask1, newTask2]);
        });

        expect(result.current.getTasks()).toHaveLength(2);
        expect(result.current.getTask('001')).toBeUndefined();
        expect(result.current.getTask('002')).toEqual(newTask1);
        expect(result.current.getTask('003')).toEqual(newTask2);
      });

      it('should convert array to Record with id as key', () => {
        const { result } = renderHook(() => useEntityStore());
        const task1 = createMockTask('001');
        const task2 = createMockTask('002');

        act(() => {
          result.current.setTasks([task1, task2]);
        });

        expect(result.current.getTask('001')).toEqual(task1);
        expect(result.current.getTask('002')).toEqual(task2);
      });

      it('should handle empty array', () => {
        const { result } = renderHook(() => useEntityStore());
        const task = createMockTask('001');

        act(() => {
          result.current.addTask(task);
          result.current.setTasks([]);
        });

        expect(result.current.getTasks()).toHaveLength(0);
      });
    });
  });

  describe('Issue operations', () => {
    describe('addIssue', () => {
      it('should add an issue to the store', () => {
        const { result } = renderHook(() => useEntityStore());
        const issue = createMockIssue('I-001');

        act(() => {
          result.current.addIssue(issue);
        });

        expect(result.current.getIssues()).toHaveLength(1);
        expect(result.current.getIssue('I-001')).toEqual(issue);
      });

      it('should add multiple issues to the store', () => {
        const { result } = renderHook(() => useEntityStore());
        const issue1 = createMockIssue('I-001');
        const issue2 = createMockIssue('I-002');

        act(() => {
          result.current.addIssue(issue1);
          result.current.addIssue(issue2);
        });

        expect(result.current.getIssues()).toHaveLength(2);
        expect(result.current.getIssue('I-001')).toEqual(issue1);
        expect(result.current.getIssue('I-002')).toEqual(issue2);
      });
    });

    describe('getIssue', () => {
      it('should retrieve an issue by id with O(1) lookup', () => {
        const { result } = renderHook(() => useEntityStore());
        const issue = createMockIssue('I-001');

        act(() => {
          result.current.addIssue(issue);
        });

        expect(result.current.getIssue('I-001')).toEqual(issue);
      });

      it('should return undefined for non-existent issue', () => {
        const { result } = renderHook(() => useEntityStore());

        expect(result.current.getIssue('I-999')).toBeUndefined();
      });
    });

    describe('getIssues', () => {
      it('should return empty array when no issues', () => {
        const { result } = renderHook(() => useEntityStore());

        expect(result.current.getIssues()).toEqual([]);
      });

      it('should return all issues as an array', () => {
        const { result } = renderHook(() => useEntityStore());
        const issue1 = createMockIssue('I-001');
        const issue2 = createMockIssue('I-002');

        act(() => {
          result.current.addIssue(issue1);
          result.current.addIssue(issue2);
        });

        const issues = result.current.getIssues();
        expect(issues).toHaveLength(2);
        expect(issues).toEqual(expect.arrayContaining([issue1, issue2]));
      });
    });

    describe('updateIssue', () => {
      it('should update issue with partial data', () => {
        const { result } = renderHook(() => useEntityStore());
        const issue = createMockIssue('I-001', { status: 'open', impact: 'medium' });

        act(() => {
          result.current.addIssue(issue);
          result.current.updateIssue('I-001', { status: 'resolved', impact: 'high' });
        });

        const updatedIssue = result.current.getIssue('I-001');
        expect(updatedIssue?.status).toBe('resolved');
        expect(updatedIssue?.impact).toBe('high');
        expect(updatedIssue?.title).toBe('Issue I-001');
      });

      it('should handle update of non-existent issue gracefully', () => {
        const { result } = renderHook(() => useEntityStore());

        act(() => {
          result.current.updateIssue('I-999', { status: 'resolved' });
        });

        expect(result.current.getIssue('I-999')).toBeUndefined();
      });
    });

    describe('removeIssue', () => {
      it('should remove an issue from the store', () => {
        const { result } = renderHook(() => useEntityStore());
        const issue = createMockIssue('I-001');

        act(() => {
          result.current.addIssue(issue);
          result.current.removeIssue('I-001');
        });

        expect(result.current.getIssues()).toHaveLength(0);
        expect(result.current.getIssue('I-001')).toBeUndefined();
      });
    });

    describe('bulkUpdateIssues', () => {
      it('should update multiple issues in a single call', () => {
        const { result } = renderHook(() => useEntityStore());
        const issue1 = createMockIssue('I-001', { status: 'open' });
        const issue2 = createMockIssue('I-002', { status: 'open' });

        act(() => {
          result.current.addIssue(issue1);
          result.current.addIssue(issue2);
        });

        act(() => {
          result.current.bulkUpdateIssues({
            'I-001': { status: 'resolved' },
            'I-002': { status: 'waived' },
          });
        });

        expect(result.current.getIssue('I-001')?.status).toBe('resolved');
        expect(result.current.getIssue('I-002')?.status).toBe('waived');
      });

      it('should not affect non-existent issues in bulk update', () => {
        const { result } = renderHook(() => useEntityStore());
        const issue1 = createMockIssue('I-001', { status: 'open' });

        act(() => {
          result.current.addIssue(issue1);
        });

        act(() => {
          result.current.bulkUpdateIssues({
            'I-001': { status: 'resolved' },
            'I-999': { status: 'waived' },
          });
        });

        expect(result.current.getIssue('I-001')?.status).toBe('resolved');
        expect(result.current.getIssue('I-999')).toBeUndefined();
      });

      it('should handle empty bulk update', () => {
        const { result } = renderHook(() => useEntityStore());
        const issue = createMockIssue('I-001', { status: 'open' });

        act(() => {
          result.current.addIssue(issue);
          result.current.bulkUpdateIssues({});
        });

        expect(result.current.getIssue('I-001')?.status).toBe('open');
      });
    });

    describe('setIssues', () => {
      it('should replace all issues with new array', () => {
        const { result } = renderHook(() => useEntityStore());
        const oldIssue = createMockIssue('I-001');
        const newIssue1 = createMockIssue('I-002');
        const newIssue2 = createMockIssue('I-003');

        act(() => {
          result.current.addIssue(oldIssue);
          result.current.setIssues([newIssue1, newIssue2]);
        });

        expect(result.current.getIssues()).toHaveLength(2);
        expect(result.current.getIssue('I-001')).toBeUndefined();
        expect(result.current.getIssue('I-002')).toEqual(newIssue1);
        expect(result.current.getIssue('I-003')).toEqual(newIssue2);
      });
    });
  });

  describe('Document operations', () => {
    describe('addDocument', () => {
      it('should add a document to the store', () => {
        const { result } = renderHook(() => useEntityStore());
        const document = createMockDocument('D-001');

        act(() => {
          result.current.addDocument(document);
        });

        expect(result.current.getDocuments()).toHaveLength(1);
        expect(result.current.getDocument('D-001')).toEqual(document);
      });

      it('should add multiple documents to the store', () => {
        const { result } = renderHook(() => useEntityStore());
        const doc1 = createMockDocument('D-001');
        const doc2 = createMockDocument('D-002');

        act(() => {
          result.current.addDocument(doc1);
          result.current.addDocument(doc2);
        });

        expect(result.current.getDocuments()).toHaveLength(2);
        expect(result.current.getDocument('D-001')).toEqual(doc1);
        expect(result.current.getDocument('D-002')).toEqual(doc2);
      });
    });

    describe('getDocument', () => {
      it('should retrieve a document by id with O(1) lookup', () => {
        const { result } = renderHook(() => useEntityStore());
        const document = createMockDocument('D-001');

        act(() => {
          result.current.addDocument(document);
        });

        expect(result.current.getDocument('D-001')).toEqual(document);
      });

      it('should return undefined for non-existent document', () => {
        const { result } = renderHook(() => useEntityStore());

        expect(result.current.getDocument('D-999')).toBeUndefined();
      });
    });

    describe('getDocuments', () => {
      it('should return empty array when no documents', () => {
        const { result } = renderHook(() => useEntityStore());

        expect(result.current.getDocuments()).toEqual([]);
      });

      it('should return all documents as an array', () => {
        const { result } = renderHook(() => useEntityStore());
        const doc1 = createMockDocument('D-001');
        const doc2 = createMockDocument('D-002');

        act(() => {
          result.current.addDocument(doc1);
          result.current.addDocument(doc2);
        });

        const documents = result.current.getDocuments();
        expect(documents).toHaveLength(2);
        expect(documents).toEqual(expect.arrayContaining([doc1, doc2]));
      });
    });

    describe('updateDocument', () => {
      it('should update document with partial data', () => {
        const { result } = renderHook(() => useEntityStore());
        const document = createMockDocument('D-001', { name: 'Original Name', size: '1.5 MB' });

        act(() => {
          result.current.addDocument(document);
          result.current.updateDocument('D-001', { name: 'Updated Name', size: '2.0 MB' });
        });

        const updatedDocument = result.current.getDocument('D-001');
        expect(updatedDocument?.name).toBe('Updated Name');
        expect(updatedDocument?.size).toBe('2.0 MB');
        expect(updatedDocument?.type).toBe('PDF');
      });

      it('should handle update of non-existent document gracefully', () => {
        const { result } = renderHook(() => useEntityStore());

        act(() => {
          result.current.updateDocument('D-999', { name: 'Should Not Exist' });
        });

        expect(result.current.getDocument('D-999')).toBeUndefined();
      });
    });

    describe('removeDocument', () => {
      it('should remove a document from the store', () => {
        const { result } = renderHook(() => useEntityStore());
        const document = createMockDocument('D-001');

        act(() => {
          result.current.addDocument(document);
          result.current.removeDocument('D-001');
        });

        expect(result.current.getDocuments()).toHaveLength(0);
        expect(result.current.getDocument('D-001')).toBeUndefined();
      });
    });

    describe('bulkUpdateDocuments', () => {
      it('should update multiple documents in a single call', () => {
        const { result } = renderHook(() => useEntityStore());
        const doc1 = createMockDocument('D-001', { size: '1.0 MB' });
        const doc2 = createMockDocument('D-002', { size: '2.0 MB' });

        act(() => {
          result.current.addDocument(doc1);
          result.current.addDocument(doc2);
        });

        act(() => {
          result.current.bulkUpdateDocuments({
            'D-001': { size: '1.5 MB' },
            'D-002': { size: '2.5 MB' },
          });
        });

        expect(result.current.getDocument('D-001')?.size).toBe('1.5 MB');
        expect(result.current.getDocument('D-002')?.size).toBe('2.5 MB');
      });

      it('should not affect non-existent documents in bulk update', () => {
        const { result } = renderHook(() => useEntityStore());
        const doc1 = createMockDocument('D-001', { size: '1.0 MB' });

        act(() => {
          result.current.addDocument(doc1);
        });

        act(() => {
          result.current.bulkUpdateDocuments({
            'D-001': { size: '1.5 MB' },
            'D-999': { size: '999 MB' },
          });
        });

        expect(result.current.getDocument('D-001')?.size).toBe('1.5 MB');
        expect(result.current.getDocument('D-999')).toBeUndefined();
      });

      it('should handle empty bulk update', () => {
        const { result } = renderHook(() => useEntityStore());
        const doc = createMockDocument('D-001', { size: '1.0 MB' });

        act(() => {
          result.current.addDocument(doc);
          result.current.bulkUpdateDocuments({});
        });

        expect(result.current.getDocument('D-001')?.size).toBe('1.0 MB');
      });
    });

    describe('setDocuments', () => {
      it('should replace all documents with new array', () => {
        const { result } = renderHook(() => useEntityStore());
        const oldDoc = createMockDocument('D-001');
        const newDoc1 = createMockDocument('D-002');
        const newDoc2 = createMockDocument('D-003');

        act(() => {
          result.current.addDocument(oldDoc);
          result.current.setDocuments([newDoc1, newDoc2]);
        });

        expect(result.current.getDocuments()).toHaveLength(2);
        expect(result.current.getDocument('D-001')).toBeUndefined();
        expect(result.current.getDocument('D-002')).toEqual(newDoc1);
        expect(result.current.getDocument('D-003')).toEqual(newDoc2);
      });
    });
  });

  describe('clearAll', () => {
    it('should clear all entities from the store', () => {
      const { result } = renderHook(() => useEntityStore());
      const task = createMockTask('001');
      const issue = createMockIssue('I-001');
      const document = createMockDocument('D-001');

      act(() => {
        result.current.addTask(task);
        result.current.addIssue(issue);
        result.current.addDocument(document);
      });

      expect(result.current.getTasks()).toHaveLength(1);
      expect(result.current.getIssues()).toHaveLength(1);
      expect(result.current.getDocuments()).toHaveLength(1);

      act(() => {
        result.current.clearAll();
      });

      expect(result.current.getTasks()).toHaveLength(0);
      expect(result.current.getIssues()).toHaveLength(0);
      expect(result.current.getDocuments()).toHaveLength(0);
    });

    it('should handle clearAll on empty store', () => {
      const { result } = renderHook(() => useEntityStore());

      act(() => {
        result.current.clearAll();
      });

      expect(result.current.getTasks()).toHaveLength(0);
      expect(result.current.getIssues()).toHaveLength(0);
      expect(result.current.getDocuments()).toHaveLength(0);
    });
  });

  describe('Reactive updates', () => {
    it('should notify subscribers on task update', () => {
      const { result, rerender } = renderHook(() => useEntityStore());
      const task = createMockTask('001', { progress: 0 });

      act(() => {
        result.current.addTask(task);
      });

      expect(result.current.getTask('001')?.progress).toBe(0);

      act(() => {
        result.current.updateTask('001', { progress: 50 });
      });

      rerender();

      expect(result.current.getTask('001')?.progress).toBe(50);
    });

    it('should trigger re-render when entity is added', () => {
      const { result, rerender } = renderHook(() => useEntityStore());

      expect(result.current.getTasks()).toHaveLength(0);

      act(() => {
        result.current.addTask(createMockTask('001'));
      });

      rerender();

      expect(result.current.getTasks()).toHaveLength(1);
    });

    it('should trigger re-render when entity is removed', () => {
      const { result, rerender } = renderHook(() => useEntityStore());
      const task = createMockTask('001');

      act(() => {
        result.current.addTask(task);
      });

      expect(result.current.getTasks()).toHaveLength(1);

      act(() => {
        result.current.removeTask('001');
      });

      rerender();

      expect(result.current.getTasks()).toHaveLength(0);
    });
  });

  describe('Mixed entity operations', () => {
    it('should handle operations on different entity types independently', () => {
      const { result } = renderHook(() => useEntityStore());
      const task = createMockTask('001');
      const issue = createMockIssue('I-001');
      const document = createMockDocument('D-001');

      act(() => {
        result.current.addTask(task);
        result.current.addIssue(issue);
        result.current.addDocument(document);
      });

      expect(result.current.getTasks()).toHaveLength(1);
      expect(result.current.getIssues()).toHaveLength(1);
      expect(result.current.getDocuments()).toHaveLength(1);

      act(() => {
        result.current.removeTask('001');
      });

      expect(result.current.getTasks()).toHaveLength(0);
      expect(result.current.getIssues()).toHaveLength(1);
      expect(result.current.getDocuments()).toHaveLength(1);
    });

    it('should handle bulk operations on different entity types', () => {
      const { result } = renderHook(() => useEntityStore());
      const task1 = createMockTask('001', { progress: 0 });
      const task2 = createMockTask('002', { progress: 0 });
      const issue1 = createMockIssue('I-001', { status: 'open' });
      const issue2 = createMockIssue('I-002', { status: 'open' });

      act(() => {
        result.current.addTask(task1);
        result.current.addTask(task2);
        result.current.addIssue(issue1);
        result.current.addIssue(issue2);
      });

      act(() => {
        result.current.bulkUpdateTasks({
          '001': { progress: 50 },
          '002': { progress: 75 },
        });
        result.current.bulkUpdateIssues({
          'I-001': { status: 'resolved' },
          'I-002': { status: 'waived' },
        });
      });

      expect(result.current.getTask('001')?.progress).toBe(50);
      expect(result.current.getTask('002')?.progress).toBe(75);
      expect(result.current.getIssue('I-001')?.status).toBe('resolved');
      expect(result.current.getIssue('I-002')?.status).toBe('waived');
    });
  });

  describe('Edge cases', () => {
    it('should handle task with all optional fields undefined', () => {
      const { result } = renderHook(() => useEntityStore());
      const task = createMockTask('001', { completedAt: undefined });

      act(() => {
        result.current.addTask(task);
      });

      expect(result.current.getTask('001')?.completedAt).toBeUndefined();
    });

    it('should handle issue with financial impact', () => {
      const { result } = renderHook(() => useEntityStore());
      const issue = createMockIssue('I-001', {
        financialImpact: 50000,
        clientResponse: 'We agree to adjust',
        clientResponseDate: '2024-02-01',
      });

      act(() => {
        result.current.addIssue(issue);
      });

      const storedIssue = result.current.getIssue('I-001');
      expect(storedIssue?.financialImpact).toBe(50000);
      expect(storedIssue?.clientResponse).toBe('We agree to adjust');
      expect(storedIssue?.clientResponseDate).toBe('2024-02-01');
    });

    it('should handle document with multiple linked tasks', () => {
      const { result } = renderHook(() => useEntityStore());
      const document = createMockDocument('D-001', {
        linkedTasks: ['T-001', 'T-002', 'T-003'],
      });

      act(() => {
        result.current.addDocument(document);
      });

      expect(result.current.getDocument('D-001')?.linkedTasks).toEqual([
        'T-001',
        'T-002',
        'T-003',
      ]);
    });

    it('should maintain data integrity across multiple operations', () => {
      const { result } = renderHook(() => useEntityStore());
      const task = createMockTask('001', { progress: 0 });

      act(() => {
        result.current.addTask(task);
        result.current.updateTask('001', { progress: 25 });
        result.current.updateTask('001', { progress: 50 });
        result.current.updateTask('001', { progress: 75 });
        result.current.updateTask('001', { progress: 100, status: 'completed' });
      });

      const finalTask = result.current.getTask('001');
      expect(finalTask?.progress).toBe(100);
      expect(finalTask?.status).toBe('completed');
      expect(finalTask?.title).toBe('Task 001');
    });
  });
});
