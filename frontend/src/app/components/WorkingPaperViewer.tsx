import { useState } from 'react';
import { FileText, CheckCircle2, AlertCircle, Download, MessageSquare, Eye } from 'lucide-react';
import { tasks, workingPapers } from '../data/mockData';

export function WorkingPaperViewer() {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>('T-001');

  const completedTasks = tasks.filter(t => t.status === 'completed' || t.status === 'pending-review');
  const selectedTask = tasks.find(t => t.id === selectedTaskId);
  const workingPaper = workingPapers.find(wp => wp.taskId === selectedTaskId);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'signed-off':
        return 'bg-green-100 text-green-700 border-green-300';
      case 'reviewed':
        return 'bg-blue-100 text-blue-700 border-blue-300';
      case 'prepared':
        return 'bg-purple-100 text-purple-700 border-purple-300';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-300';
    }
  };

  const getConclusionColor = (type: string) => {
    switch (type) {
      case 'satisfactory':
        return 'bg-green-50 border-green-200 text-green-900';
      case 'adjustment-required':
        return 'bg-amber-50 border-amber-200 text-amber-900';
      case 'further-investigation':
        return 'bg-red-50 border-red-200 text-red-900';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-900';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl mb-2">Working Paper Viewer</h1>
        <p className="text-gray-600">Formal audit documentation and conclusions</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Task List */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-lg mb-3 flex items-center gap-2">
            <FileText className="size-5 text-blue-600" />
            Completed Tasks
          </h2>
          <div className="space-y-2">
            {completedTasks.map((task) => (
              <div
                key={task.id}
                onClick={() => setSelectedTaskId(task.id)}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  selectedTaskId === task.id
                    ? 'bg-blue-50 border-blue-300 shadow-sm'
                    : 'border-gray-200 hover:border-blue-200 hover:bg-gray-50'
                }`}
              >
                <div className="text-xs text-gray-600 mb-1">{task.taskNumber}</div>
                <div className="font-medium text-sm mb-2">{task.title}</div>
                {workingPapers.find(wp => wp.taskId === task.id) ? (
                  <div className="flex items-center gap-1 text-xs text-green-600">
                    <CheckCircle2 className="size-3" />
                    Working Paper Available
                  </div>
                ) : (
                  <div className="flex items-center gap-1 text-xs text-gray-400">
                    <AlertCircle className="size-3" />
                    Not Yet Documented
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Working Paper Content */}
        <div className="lg:col-span-3">
          {workingPaper && selectedTask ? (
            <div className="bg-white rounded-lg border-2 border-gray-300 shadow-lg">
              {/* Header - Paper-like */}
              <div className="bg-gradient-to-b from-gray-50 to-white border-b-2 border-gray-300 p-8">
                <div className="flex items-start justify-between mb-6">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">WORKING PAPER</div>
                    <h2 className="text-2xl font-medium mb-2">{selectedTask.title}</h2>
                    <div className="text-sm text-gray-600">Ref: {workingPaper.taskNumber}</div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <span className={`px-3 py-1 rounded border text-xs ${getStatusColor(workingPaper.status)}`}>
                      {workingPaper.status.replace('-', ' ').toUpperCase()}
                    </span>
                    {workingPaper.version > 1 && (
                      <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">
                        Version {workingPaper.version}
                      </span>
                    )}
                  </div>
                </div>

                {/* Formal Header Grid */}
                <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm border-t border-b border-gray-300 py-4">
                  <div className="flex">
                    <div className="w-32 text-gray-600">Client:</div>
                    <div className="font-medium">{workingPaper.clientName}</div>
                  </div>
                  <div className="flex">
                    <div className="w-32 text-gray-600">Period End:</div>
                    <div className="font-medium">December 31, {workingPaper.fiscalYear}</div>
                  </div>
                  <div className="flex">
                    <div className="w-32 text-gray-600">Account:</div>
                    <div className="font-medium">{workingPaper.accountCategory}</div>
                  </div>
                  <div className="flex">
                    <div className="w-32 text-gray-600">Prepared By:</div>
                    <div className="font-medium">{workingPaper.preparedBy}</div>
                  </div>
                  <div className="flex">
                    <div className="w-32 text-gray-600">Prepared Date:</div>
                    <div className="font-medium">{formatDate(workingPaper.preparedDate)}</div>
                  </div>
                  {workingPaper.reviewedBy && (
                    <div className="flex">
                      <div className="w-32 text-gray-600">Reviewed By:</div>
                      <div className="font-medium">{workingPaper.reviewedBy}</div>
                    </div>
                  )}
                  {workingPaper.reviewedDate && (
                    <div className="flex">
                      <div className="w-32 text-gray-600">Reviewed Date:</div>
                      <div className="font-medium">{formatDate(workingPaper.reviewedDate)}</div>
                    </div>
                  )}
                  {workingPaper.signedOffBy && (
                    <div className="flex">
                      <div className="w-32 text-gray-600">Signed Off By:</div>
                      <div className="font-medium flex items-center gap-2">
                        {workingPaper.signedOffBy}
                        <CheckCircle2 className="size-4 text-green-600" />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Content */}
              <div className="p-8 space-y-6">
                {/* Purpose */}
                <section>
                  <h3 className="text-sm font-medium text-gray-700 mb-2 uppercase tracking-wide">1. Purpose</h3>
                  <div className="pl-4 text-sm text-gray-700 leading-relaxed">
                    {workingPaper.purpose}
                  </div>
                </section>

                {/* Procedures */}
                <section>
                  <h3 className="text-sm font-medium text-gray-700 mb-2 uppercase tracking-wide">2. Audit Procedures Performed</h3>
                  <div className="pl-4 space-y-2">
                    {workingPaper.procedures.map((procedure, index) => (
                      <div key={index} className="flex gap-3 text-sm text-gray-700">
                        <span className="text-gray-500">{String.fromCharCode(97 + index)})</span>
                        <span className="flex-1">{procedure}</span>
                      </div>
                    ))}
                  </div>
                </section>

                {/* Results */}
                <section>
                  <h3 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide">3. Results and Findings</h3>
                  <div className="pl-4">
                    <table className="w-full border-collapse">
                      <thead>
                        <tr className="border-b-2 border-gray-300">
                          <th className="text-left py-2 text-xs font-medium text-gray-600 uppercase">Description</th>
                          <th className="text-left py-2 text-xs font-medium text-gray-600 uppercase">Value/Details</th>
                          <th className="text-center py-2 text-xs font-medium text-gray-600 uppercase w-24">Exception</th>
                        </tr>
                      </thead>
                      <tbody>
                        {workingPaper.results.map((result, index) => (
                          <tr key={index} className={`border-b border-gray-200 ${result.exception ? 'bg-amber-50' : ''}`}>
                            <td className="py-3 text-sm text-gray-700">{result.description}</td>
                            <td className="py-3 text-sm font-medium text-gray-900">{result.value}</td>
                            <td className="py-3 text-center">
                              {result.exception ? (
                                <AlertCircle className="size-5 text-amber-600 mx-auto" />
                              ) : (
                                <CheckCircle2 className="size-5 text-green-600 mx-auto" />
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>

                {/* Conclusion */}
                <section>
                  <h3 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide">4. Conclusion</h3>
                  <div className={`p-4 rounded-lg border-2 ${getConclusionColor(workingPaper.conclusionType)}`}>
                    <div className="flex items-start gap-3">
                      {workingPaper.conclusionType === 'satisfactory' ? (
                        <CheckCircle2 className="size-6 flex-shrink-0 mt-0.5" />
                      ) : (
                        <AlertCircle className="size-6 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <div className="font-medium text-xs uppercase mb-2 tracking-wide">
                          {workingPaper.conclusionType.replace('-', ' ')}
                        </div>
                        <div className="text-sm leading-relaxed">
                          {workingPaper.conclusion}
                        </div>
                      </div>
                    </div>
                  </div>
                </section>

                {/* Attachments */}
                {workingPaper.attachments.length > 0 && (
                  <section>
                    <h3 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide">5. Supporting Documents</h3>
                    <div className="pl-4 space-y-2">
                      {workingPaper.attachments.map((attachment, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded border border-gray-200 hover:border-blue-300 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <FileText className="size-5 text-blue-600" />
                            <div>
                              <div className="text-sm font-medium">{attachment.name}</div>
                              <div className="text-xs text-gray-500">{attachment.type}</div>
                            </div>
                          </div>
                          <button className="p-2 hover:bg-blue-50 rounded transition-colors">
                            <Download className="size-4 text-blue-600" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </div>

              {/* Footer - Signatures */}
              <div className="border-t-2 border-gray-300 bg-gray-50 p-6">
                <div className="grid grid-cols-3 gap-6">
                  <div className="border-t-2 border-gray-400 pt-2">
                    <div className="text-xs text-gray-600 mb-1">Prepared by</div>
                    <div className="font-medium text-sm">{workingPaper.preparedBy}</div>
                    <div className="text-xs text-gray-500">{formatDate(workingPaper.preparedDate)}</div>
                  </div>
                  {workingPaper.reviewedBy && (
                    <div className="border-t-2 border-gray-400 pt-2">
                      <div className="text-xs text-gray-600 mb-1">Reviewed by</div>
                      <div className="font-medium text-sm">{workingPaper.reviewedBy}</div>
                      <div className="text-xs text-gray-500">{formatDate(workingPaper.reviewedDate!)}</div>
                    </div>
                  )}
                  {workingPaper.signedOffBy && (
                    <div className="border-t-2 border-green-600 pt-2">
                      <div className="text-xs text-green-700 mb-1 flex items-center gap-1">
                        <CheckCircle2 className="size-3" />
                        Signed off by
                      </div>
                      <div className="font-medium text-sm text-green-900">{workingPaper.signedOffBy}</div>
                      <div className="text-xs text-green-700">{formatDate(workingPaper.signedOffDate!)}</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Action Bar */}
              <div className="border-t border-gray-200 bg-white p-4 flex items-center justify-between">
                <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm">
                  <MessageSquare className="size-4" />
                  View Conversation Log
                </button>
                <div className="flex gap-2">
                  <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                    <Download className="size-4" />
                    Export PDF
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
              <Eye className="size-16 mx-auto mb-4 text-gray-300" />
              <p className="text-gray-600 mb-2">No Working Paper Available</p>
              <p className="text-sm text-gray-400">
                {selectedTask ? 'This task has not been documented yet' : 'Select a completed task to view its working paper'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
