import type { Artifact } from '@/app/types/audit';
import { EngagementPlanArtifact } from './EngagementPlanArtifact';
import { TaskStatusArtifact } from './TaskStatusArtifact';
import { IssueDetailsArtifact } from './IssueDetailsArtifact';
import { FinancialStatementsArtifact } from './FinancialStatementsArtifact';
import { DashboardArtifact } from './DashboardArtifact';

interface ArtifactRendererProps {
  artifact: Artifact;
}

export function ArtifactRenderer({ artifact }: ArtifactRendererProps) {
  switch (artifact.type) {
    case 'engagement-plan':
      return <EngagementPlanArtifact data={artifact.data} status={artifact.status} />;
    case 'task-status':
      return <TaskStatusArtifact data={artifact.data} status={artifact.status} />;
    case 'issue-details':
      return <IssueDetailsArtifact data={artifact.data} status={artifact.status} />;
    case 'financial-statements':
      return <FinancialStatementsArtifact data={artifact.data} status={artifact.status} />;
    case 'dashboard':
      return <DashboardArtifact data={artifact.data} status={artifact.status} />;
    default:
      return (
        <div className="p-4 text-gray-500">
          Unknown artifact type: {artifact.type}
        </div>
      );
  }
}
