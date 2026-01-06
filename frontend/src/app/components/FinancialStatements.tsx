import { useState } from 'react';
import { FileSpreadsheet, TrendingUp, TrendingDown, AlertCircle, CheckCircle2, Clock, Sparkles } from 'lucide-react';
import { financialStatementItems, tasks } from '../data/mockData';
import type { FinancialStatementItem, RiskLevel } from '../types/audit';
import { AskAIDrawer } from './workspace/AskAIDrawer';

export function FinancialStatements() {
  const [selectedAccount, setSelectedAccount] = useState<FinancialStatementItem | null>(null);
  const [isAskAIOpen, setIsAskAIOpen] = useState(false);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'KRW',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const getRiskBadge = (level: RiskLevel) => {
    const styles = {
      critical: 'bg-red-100 text-red-700 border-red-200',
      high: 'bg-orange-100 text-orange-700 border-orange-200',
      medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      low: 'bg-green-100 text-green-700 border-green-200'
    };
    return (
      <span className={`px-2 py-1 rounded text-xs border ${styles[level]}`}>
        {level.toUpperCase()}
      </span>
    );
  };

  const getStatusIcon = (completed: number, total: number) => {
    if (completed === total && total > 0) {
      return <CheckCircle2 className="size-4 text-green-600" />;
    } else if (completed > 0) {
      return <Clock className="size-4 text-amber-600" />;
    } else {
      return <AlertCircle className="size-4 text-gray-400" />;
    }
  };

  const relatedTasks = selectedAccount 
    ? tasks.filter(t => t.accountCategory === selectedAccount.account)
    : [];

  const assets = financialStatementItems.filter(item => item.category === 'Assets');
  const liabilities = financialStatementItems.filter(item => item.category === 'Liabilities');
  const equity = financialStatementItems.filter(item => item.category === 'Equity');
  const income = financialStatementItems.filter(item => item.category === 'Income');

  const renderStatementSection = (items: FinancialStatementItem[], title: string) => (
    <div className="mb-6">
      <div className="bg-gray-100 px-4 py-2 font-semibold text-sm border-b-2 border-gray-300">
        {title}
      </div>
      {items.map((item) => (
        <div
          key={item.id}
          onClick={() => setSelectedAccount(item)}
          className={`px-4 py-3 border-b border-gray-200 hover:bg-blue-50 cursor-pointer transition-colors ${
            selectedAccount?.id === item.id ? 'bg-blue-100' : ''
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 flex-1">
              {getStatusIcon(item.completedTasks, item.taskCount)}
              <div className="font-medium text-sm">{item.account}</div>
              {item.taskCount > 0 && (
                <div className="text-xs text-gray-500">
                  ({item.completedTasks}/{item.taskCount})
                </div>
              )}
            </div>
            <div className="flex items-center gap-4">
              <div className="text-sm">{formatCurrency(item.currentYear)}</div>
              <div className="text-sm text-gray-500 w-32 text-right">{formatCurrency(item.priorYear)}</div>
              <div className="flex items-center gap-1 w-20 justify-end">
                {item.variance !== 0 && (
                  <>
                    {item.variance > 0 ? (
                      <TrendingUp className="size-4 text-green-600" />
                    ) : (
                      <TrendingDown className="size-4 text-red-600" />
                    )}
                    <span className={`text-sm ${item.variance > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {Math.abs(item.variancePercent).toFixed(1)}%
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl mb-2">Financial Statement Centric View</h1>
        <p className="text-gray-600">Click on any account to view related audit tasks</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Financial Statements */}
        <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4">
            <div className="flex items-center gap-2 mb-2">
              <FileSpreadsheet className="size-5" />
              <h2 className="text-xl">Statement of Financial Position</h2>
            </div>
            <div className="text-sm text-blue-100">As of December 31, 2025</div>
          </div>

          <div className="p-4">
            {/* Header Row */}
            <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200 text-xs text-gray-600 mb-4">
              <div className="flex items-center gap-3 flex-1">
                <div className="w-4"></div>
                <div>Account</div>
              </div>
              <div className="flex items-center gap-4">
                <div className="w-32">2025</div>
                <div className="w-32 text-right">2024</div>
                <div className="w-20 text-right">Change</div>
              </div>
            </div>

            {renderStatementSection(assets, 'ASSETS')}
            {renderStatementSection(liabilities, 'LIABILITIES')}
            {renderStatementSection(equity, 'EQUITY')}
            
            {/* Income Statement Section */}
            <div className="mt-8 pt-4 border-t-2 border-gray-300">
              <div className="bg-gradient-to-r from-emerald-600 to-emerald-700 text-white p-3 -mx-4 mb-4">
                <h3 className="text-lg">Statement of Comprehensive Income</h3>
                <div className="text-sm text-emerald-100">For the year ended December 31, 2025</div>
              </div>
              {renderStatementSection(income, 'INCOME & EXPENSES')}
            </div>
          </div>
        </div>

        {/* Task Mapping Drawer */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="bg-gray-800 text-white p-4">
            <h2 className="text-lg">Related Audit Tasks</h2>
            {selectedAccount && (
              <div className="text-sm text-gray-300 mt-1">{selectedAccount.account}</div>
            )}
          </div>

          {selectedAccount ? (
            <div className="divide-y divide-gray-200">
              {relatedTasks.length > 0 ? (
                relatedTasks.map((task) => (
                  <div key={task.id} className="p-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <div className="text-xs text-gray-500 mb-1">{task.taskNumber}</div>
                        <div className="font-medium text-sm mb-1">{task.title}</div>
                      </div>
                      {getRiskBadge(task.riskLevel)}
                    </div>
                    
                    <div className="text-xs text-gray-600 mb-3">{task.description}</div>
                    
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-600">Progress</span>
                        <span className="font-medium">{task.progress}%</span>
                      </div>
                      <div className="bg-gray-100 rounded-full h-1.5">
                        <div 
                          className="bg-blue-600 h-1.5 rounded-full transition-all"
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                    </div>

                    <div className="mt-3 pt-3 border-t border-gray-100 space-y-1 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">Manager</span>
                        <span className="font-medium">{task.assignedManager}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">Staff</span>
                        <span className="font-medium">{task.assignedStaff.length} assigned</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">Status</span>
                        <span className={`px-2 py-0.5 rounded ${
                          task.status === 'completed' ? 'bg-green-100 text-green-700' :
                          task.status === 'in-progress' ? 'bg-blue-100 text-blue-700' :
                          task.status === 'pending-review' ? 'bg-amber-100 text-amber-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {task.status}
                        </span>
                      </div>
                      {task.requiresReview && (
                        <div className="flex items-center gap-1 text-amber-600 mt-2">
                          <AlertCircle className="size-3" />
                          <span>Review Required</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-gray-500">
                  <AlertCircle className="size-12 mx-auto mb-3 text-gray-400" />
                  <p className="text-sm">No tasks linked to this account</p>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              <FileSpreadsheet className="size-12 mx-auto mb-3 text-gray-400" />
              <p className="text-sm">Select an account from the financial statement</p>
              <p className="text-xs text-gray-400 mt-1">to view related audit tasks</p>
            </div>
          )}
        </div>
      </div>

      <button
        onClick={() => setIsAskAIOpen(true)}
        className="fixed bottom-6 right-6 bg-blue-600 text-white rounded-full p-4 shadow-lg hover:bg-blue-700 transition-colors z-30"
        aria-label="Ask AI"
      >
        <Sparkles className="size-6" />
      </button>

      <AskAIDrawer
        isOpen={isAskAIOpen}
        onClose={() => setIsAskAIOpen(false)}
        context={selectedAccount ? `Financial Statement Account: ${selectedAccount.account} (${selectedAccount.category})` : 'Financial Statements - ABC Corporation FY 2025'}
        onOpenInMainChat={() => {
          window.location.hash = '#/chat';
        }}
      />
    </div>
  );
}