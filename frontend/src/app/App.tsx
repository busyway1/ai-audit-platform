import { useState } from 'react';
import { LayoutDashboard, FileSpreadsheet, ListTodo, MessageSquare, FolderOpen, Menu, X, FileCheck, FileText, AlertTriangle, Settings } from 'lucide-react';
import { Dashboard } from './components/Dashboard';
import { FinancialStatements } from './components/FinancialStatements';
import { TaskExecution } from './components/TaskExecution';
import { EngagementPlan } from './components/EngagementPlan';
import { Documents } from './components/Documents';
import { PlanSummary } from './components/PlanSummary';
import { WorkingPaperViewer } from './components/WorkingPaperViewer';
import { IssueTracker } from './components/IssueTracker';
import { AgentToolRegistry } from './components/AgentToolRegistry';

type View = 'dashboard' | 'financial-statements' | 'engagement-plan' | 'plan-summary' | 'task-execution' | 'working-papers' | 'issues' | 'agent-tools' | 'documents';

export default function App() {
  const [currentView, setCurrentView] = useState<View>('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const navigation = [
    { id: 'dashboard' as View, name: 'Dashboard', icon: LayoutDashboard },
    { id: 'engagement-plan' as View, name: 'Engagement Plan', icon: MessageSquare },
    { id: 'financial-statements' as View, name: 'Financial Statements', icon: FileSpreadsheet },
    { id: 'task-execution' as View, name: 'Task Execution', icon: ListTodo },
    { id: 'documents' as View, name: 'Documents', icon: FolderOpen },
    { id: 'plan-summary' as View, name: 'Plan Summary', icon: FileCheck },
    { id: 'working-papers' as View, name: 'Working Papers', icon: FileText },
    { id: 'issues' as View, name: 'Issues', icon: AlertTriangle },
    { id: 'agent-tools' as View, name: 'Agent Tools', icon: Settings },
  ];

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard />;
      case 'financial-statements':
        return <FinancialStatements />;
      case 'task-execution':
        return <TaskExecution />;
      case 'engagement-plan':
        return <EngagementPlan />;
      case 'documents':
        return <Documents />;
      case 'plan-summary':
        return <PlanSummary />;
      case 'working-papers':
        return <WorkingPaperViewer />;
      case 'issues':
        return <IssueTracker />;
      case 'agent-tools':
        return <AgentToolRegistry />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div
        className={`bg-gray-900 text-white transition-all duration-300 ${
          sidebarOpen ? 'w-64' : 'w-0 lg:w-20'
        } flex-shrink-0`}
      >
        <div className="h-full flex flex-col">
          {/* Logo */}
          <div className="p-6 border-b border-gray-800">
            <div className="flex items-center gap-3">
              <div className="size-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-xl">🔍</span>
              </div>
              {sidebarOpen && (
                <div>
                  <h1 className="text-lg">AuditAI</h1>
                  <p className="text-xs text-gray-400">Multi-Agent Platform</p>
                </div>
              )}
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = currentView === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentView(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  }`}
                >
                  <Icon className="size-5 flex-shrink-0" />
                  {sidebarOpen && <span className="text-sm">{item.name}</span>}
                </button>
              );
            })}
          </nav>

          {/* Project Info */}
          {sidebarOpen && (
            <div className="p-4 border-t border-gray-800">
              <div className="bg-gray-800 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1">Current Project</div>
                <div className="text-sm font-medium">ABC Corporation</div>
                <div className="text-xs text-gray-400 mt-1">FY 2025 Audit</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            {sidebarOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>

          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-600">
              {new Date().toLocaleDateString('ko-KR', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                weekday: 'short'
              })}
            </div>
            <div className="size-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white">
              <span className="text-sm">KA</span>
            </div>
          </div>
        </div>

        {/* View Content */}
        <div className="flex-1 overflow-auto p-6">
          {renderView()}
        </div>
      </div>
    </div>
  );
}