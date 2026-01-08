import { useState, useEffect, useMemo } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ListTodo,
  Shield,
  Search,
  Filter,
  ChevronRight
} from 'lucide-react';
import { useEGAStore } from '../../stores/useEGAStore';
import { useProjectStore } from '../../stores/useProjectStore';
import type { EGARiskLevel, EGAStatus, AuditEGA } from '../../types/supabase';

interface EGAListProps {
  onSelectEGA?: (ega: AuditEGA) => void;
  selectedEGAId?: string;
}

export function EGAList({ onSelectEGA, selectedEGAId }: EGAListProps) {
  const [filterRisk, setFilterRisk] = useState<EGARiskLevel | 'all'>('all');
  const [filterStatus, setFilterStatus] = useState<EGAStatus | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const { egas, loading, error, fetchEGAs, subscribeToUpdates, unsubscribeFromUpdates } = useEGAStore();
  const { selectedProject } = useProjectStore();

  useEffect(() => {
    if (selectedProject?.id) {
      fetchEGAs(selectedProject.id);
      const cleanup = subscribeToUpdates(selectedProject.id);
      return () => {
        cleanup();
        unsubscribeFromUpdates(selectedProject.id);
      };
    }
  }, [selectedProject?.id, fetchEGAs, subscribeToUpdates, unsubscribeFromUpdates]);

  const egaList = useMemo(() => Object.values(egas), [egas]);

  const filteredEGAs = useMemo(() => {
    return egaList.filter(ega => {
      const matchesRisk = filterRisk === 'all' || ega.risk_level === filterRisk;
      const matchesStatus = filterStatus === 'all' || ega.status === filterStatus;
      const matchesSearch = searchQuery === '' ||
        ega.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (ega.description?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false);
      return matchesRisk && matchesStatus && matchesSearch;
    });
  }, [egaList, filterRisk, filterStatus, searchQuery]);

  const stats = useMemo(() => ({
    total: egaList.length,
    critical: egaList.filter(e => e.risk_level === 'Critical').length,
    high: egaList.filter(e => e.risk_level === 'High').length,
    inProgress: egaList.filter(e => e.status === 'In-Progress').length,
    completed: egaList.filter(e => e.status === 'Completed').length,
    totalTasks: egaList.reduce((sum, e) => sum + e.total_tasks, 0),
    completedTasks: egaList.reduce((sum, e) => sum + e.completed_tasks, 0),
  }), [egaList]);

  const overallProgress = stats.totalTasks > 0
    ? Math.round((stats.completedTasks / stats.totalTasks) * 100)
    : 0;

  const getRiskBadgeStyles = (level: EGARiskLevel) => {
    switch (level) {
      case 'Critical':
        return 'bg-red-100 text-red-700 border-red-300';
      case 'High':
        return 'bg-orange-100 text-orange-700 border-orange-300';
      case 'Medium':
        return 'bg-yellow-100 text-yellow-700 border-yellow-300';
      case 'Low':
        return 'bg-green-100 text-green-700 border-green-300';
    }
  };

  const getRiskProgressColor = (level: EGARiskLevel) => {
    switch (level) {
      case 'Critical':
        return 'bg-red-500';
      case 'High':
        return 'bg-orange-500';
      case 'Medium':
        return 'bg-yellow-500';
      case 'Low':
        return 'bg-green-500';
    }
  };

  const getStatusBadgeStyles = (status: EGAStatus) => {
    switch (status) {
      case 'Completed':
        return 'bg-green-100 text-green-700';
      case 'In-Progress':
        return 'bg-blue-100 text-blue-700';
      case 'Not-Started':
        return 'bg-gray-100 text-gray-700';
    }
  };

  const getStatusIcon = (status: EGAStatus) => {
    switch (status) {
      case 'Completed':
        return <CheckCircle2 className="size-4" />;
      case 'In-Progress':
        return <Clock className="size-4" />;
      case 'Not-Started':
        return <ListTodo className="size-4" />;
    }
  };

  if (error) {
    return (
      <div className="p-6 text-center">
        <AlertTriangle className="size-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-600 mb-2">Failed to load EGAs</p>
        <p className="text-sm text-gray-500">{error}</p>
        <button
          onClick={() => selectedProject?.id && fetchEGAs(selectedProject.id)}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl mb-2">Expected General Activities</h1>
        <p className="text-gray-600">
          {selectedProject?.client_name || 'No project selected'} - EGA Overview
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">Total EGAs</div>
            <Shield className="size-5 text-blue-600" />
          </div>
          <div className="text-2xl font-medium">{stats.total}</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">Critical/High</div>
            <AlertTriangle className="size-5 text-red-600" />
          </div>
          <div className="text-2xl font-medium text-red-600">
            {stats.critical + stats.high}
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">In Progress</div>
            <Clock className="size-5 text-amber-600" />
          </div>
          <div className="text-2xl font-medium text-amber-600">{stats.inProgress}</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">Completed</div>
            <CheckCircle2 className="size-5 text-green-600" />
          </div>
          <div className="text-2xl font-medium text-green-600">{stats.completed}</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">Overall Progress</div>
            <ListTodo className="size-5 text-purple-600" />
          </div>
          <div className="text-2xl font-medium text-purple-600">{overallProgress}%</div>
          <div className="text-xs text-gray-500">
            {stats.completedTasks}/{stats.totalTasks} tasks
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="size-5 text-gray-500" />
          <h2 className="font-medium">Filters</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search EGAs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Risk Filter */}
          <select
            value={filterRisk}
            onChange={(e) => setFilterRisk(e.target.value as EGARiskLevel | 'all')}
            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Risk Levels</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>

          {/* Status Filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as EGAStatus | 'all')}
            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Statuses</option>
            <option value="Not-Started">Not Started</option>
            <option value="In-Progress">In Progress</option>
            <option value="Completed">Completed</option>
          </select>
        </div>
      </div>

      {/* EGA List */}
      <div className="space-y-4">
        {loading ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
            <div className="animate-spin size-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-500">Loading EGAs...</p>
          </div>
        ) : filteredEGAs.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
            <Shield className="size-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 mb-2">No EGAs found</p>
            <p className="text-sm text-gray-400">
              {egaList.length === 0
                ? 'No EGAs have been created for this project yet.'
                : 'Try adjusting your filters to see more results.'}
            </p>
          </div>
        ) : (
          filteredEGAs.map((ega) => (
            <EGACard
              key={ega.id}
              ega={ega}
              isSelected={selectedEGAId === ega.id}
              onClick={() => onSelectEGA?.(ega)}
              getRiskBadgeStyles={getRiskBadgeStyles}
              getRiskProgressColor={getRiskProgressColor}
              getStatusBadgeStyles={getStatusBadgeStyles}
              getStatusIcon={getStatusIcon}
            />
          ))
        )}
      </div>

      {/* Footer */}
      {filteredEGAs.length > 0 && (
        <div className="text-center text-sm text-gray-500">
          Showing {filteredEGAs.length} of {egaList.length} EGAs
        </div>
      )}
    </div>
  );
}

interface EGACardProps {
  ega: AuditEGA;
  isSelected: boolean;
  onClick?: () => void;
  getRiskBadgeStyles: (level: EGARiskLevel) => string;
  getRiskProgressColor: (level: EGARiskLevel) => string;
  getStatusBadgeStyles: (status: EGAStatus) => string;
  getStatusIcon: (status: EGAStatus) => React.ReactNode;
}

function EGACard({
  ega,
  isSelected,
  onClick,
  getRiskBadgeStyles,
  getRiskProgressColor,
  getStatusBadgeStyles,
  getStatusIcon,
}: EGACardProps) {
  const progressPercent = ega.total_tasks > 0
    ? Math.round((ega.completed_tasks / ega.total_tasks) * 100)
    : 0;

  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-lg border transition-all ${
        isSelected
          ? 'border-blue-500 ring-2 ring-blue-100'
          : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
      } ${onClick ? 'cursor-pointer' : ''}`}
    >
      <div className="p-5">
        {/* Header Row */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h3 className="font-medium text-lg mb-1">{ega.name}</h3>
            {ega.description && (
              <p className="text-sm text-gray-500 line-clamp-2">{ega.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2 ml-4">
            <span className={`px-2.5 py-1 rounded text-xs font-medium border ${getRiskBadgeStyles(ega.risk_level)}`}>
              {ega.risk_level}
            </span>
            {onClick && <ChevronRight className="size-5 text-gray-400" />}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-500">Progress</span>
            <span className="text-sm font-medium">{progressPercent}%</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${getRiskProgressColor(ega.risk_level)}`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Footer Row */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100">
          <div className="flex items-center gap-4">
            <div className="text-sm">
              <span className="text-gray-500">Tasks: </span>
              <span className="font-medium">{ega.completed_tasks}/{ega.total_tasks}</span>
            </div>
          </div>
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium ${getStatusBadgeStyles(ega.status)}`}>
            {getStatusIcon(ega.status)}
            <span>{ega.status.replace('-', ' ')}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
