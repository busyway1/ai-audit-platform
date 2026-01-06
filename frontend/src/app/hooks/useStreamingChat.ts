import { nanoid } from 'nanoid';
import { useChatStore } from '@/app/stores/useChatStore';
import { useArtifactStore } from '@/app/stores/useArtifactStore';
import type { ChatMessage, Artifact } from '@/app/types/audit';

/**
 * Hook for SSE streaming with artifact parsing
 *
 * Features:
 * - Sends user messages to chat store
 * - Simulates AI streaming responses (mock SSE for Phase 2)
 * - Parses JSON blocks from AI responses to create artifacts
 * - Updates both chat and artifact stores
 *
 * Phase 2: Mock implementation with simulated streaming
 * Future: Real SSE backend integration
 */
export function useStreamingChat() {
  const { addMessage, updateMessage } = useChatStore();
  const { addArtifact, updateArtifact } = useArtifactStore();

  /**
   * Send a message and handle the streaming AI response
   *
   * @param content - User message content
   */
  const sendMessage = async (content: string): Promise<void> => {
    // Add user message to chat
    const userMsg: ChatMessage = {
      id: nanoid(),
      sender: 'user',
      content,
      timestamp: new Date(),
    };
    addMessage(userMsg);

    // Create AI message with streaming state
    const aiMsgId = nanoid();
    const aiMsg: ChatMessage = {
      id: aiMsgId,
      sender: 'ai',
      content: 'Analyzing your request...',
      timestamp: new Date(),
      streaming: true,
    };
    addMessage(aiMsg);

    // Simulate streaming delay (mock SSE)
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Mock artifact creation
    // In production: Parse JSON blocks from SSE stream
    const mockArtifact: Artifact = {
      id: nanoid(),
      type: 'engagement-plan',
      title: 'Engagement Plan',
      data: {
        mock: true,
        userRequest: content,
        generatedAt: new Date().toISOString(),
      },
      createdAt: new Date(),
      updatedAt: new Date(),
      status: 'streaming',
    };

    // Add artifact to store
    addArtifact(mockArtifact);

    // Update AI message with final content and artifact reference
    updateMessage(aiMsgId, {
      content: "I've created an engagement plan for you. Check the artifact panel →",
      streaming: false,
      artifactId: mockArtifact.id,
    });

    // Simulate artifact completion delay
    await new Promise(resolve => setTimeout(resolve, 500));

    // Mark artifact as complete
    updateArtifact(mockArtifact.id, { status: 'complete' });
  };

  return { sendMessage };
}
