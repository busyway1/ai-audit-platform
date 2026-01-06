import { Wrench, AlertCircle } from 'lucide-react';

export function AgentToolsSettings() {
  return (
    <div className="p-6 md:p-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Wrench className="w-6 h-6 text-primary-600" />
          <h1 className="text-2xl font-bold text-gray-900">Agent Tools Settings</h1>
        </div>
        <p className="text-gray-600">
          Configure and manage agent tools, registry settings, and integration preferences.
        </p>
      </div>

      {/* Placeholder Content */}
      <div className="bg-white rounded-lg border border-gray-200 p-8">
        <div className="flex flex-col items-center justify-center text-center space-y-4">
          <div className="w-16 h-16 bg-primary-50 rounded-full flex items-center justify-center">
            <AlertCircle className="w-8 h-8 text-primary-600" />
          </div>

          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              Coming Soon
            </h2>
            <p className="text-gray-600 max-w-md">
              Agent Tools configuration interface will be integrated in the next phase.
              This will include the Agent Tool Registry with full management capabilities.
            </p>
          </div>

          {/* Preview Features List */}
          <div className="mt-8 w-full max-w-md">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Upcoming Features:</h3>
            <ul className="text-left space-y-2 text-sm text-gray-600">
              <li className="flex items-start gap-2">
                <span className="text-primary-500 mt-0.5">•</span>
                <span>Tool Registry management and configuration</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary-500 mt-0.5">•</span>
                <span>MCP server integration settings</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary-500 mt-0.5">•</span>
                <span>Custom tool creation and editing</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary-500 mt-0.5">•</span>
                <span>Tool permissions and access control</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-primary-500 mt-0.5">•</span>
                <span>Integration testing and validation</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
