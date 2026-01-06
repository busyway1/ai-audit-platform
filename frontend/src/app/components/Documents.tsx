import { useState } from 'react';
import { FileText, Upload, Search, Filter, Download, Trash2, ExternalLink } from 'lucide-react';
import { documents } from '../data/mockData';

export function Documents() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState<string>('all');

  const categories = Array.from(new Set(documents.map(doc => doc.category)));

  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = filterCategory === 'all' || doc.category === filterCategory;
    return matchesSearch && matchesCategory;
  });

  const getFileIcon = (type: string) => {
    return <FileText className="size-5 text-blue-600" />;
  };

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl mb-2">Document Management</h1>
          <p className="text-gray-600">Manage audit working papers and reference materials</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          <Upload className="size-5" />
          Upload Document
        </button>
      </div>

      {/* Search and Filter */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search documents..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
          </div>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
          >
            <option value="all">All Categories</option>
            {categories.map(category => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Document Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredDocuments.map((doc) => (
          <div
            key={doc.id}
            className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start gap-3 mb-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                {getFileIcon(doc.type)}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-sm mb-1 truncate">{doc.name}</h3>
                <div className="text-xs text-gray-500">{doc.size}</div>
              </div>
            </div>

            <div className="space-y-2 mb-4">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Category</span>
                <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
                  {doc.category}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Uploaded by</span>
                <span className="font-medium">{doc.uploadedBy}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Date</span>
                <span className="text-gray-700">{formatDate(doc.uploadedAt)}</span>
              </div>
            </div>

            {doc.linkedTasks.length > 0 && (
              <div className="mb-4 p-2 bg-gray-50 rounded border border-gray-200">
                <div className="text-xs text-gray-600 mb-1">Linked Tasks</div>
                <div className="flex flex-wrap gap-1">
                  {doc.linkedTasks.map(taskId => (
                    <span key={taskId} className="text-xs px-2 py-0.5 bg-white border border-gray-300 rounded">
                      {taskId}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="flex gap-2">
              <button className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                <Download className="size-4" />
                Download
              </button>
              <button className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                <ExternalLink className="size-4 text-gray-600" />
              </button>
              <button className="p-2 border border-gray-300 rounded-lg hover:bg-red-50 transition-colors">
                <Trash2 className="size-4 text-red-600" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {filteredDocuments.length === 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <FileText className="size-12 mx-auto mb-3 text-gray-400" />
          <p className="text-gray-600">No documents found</p>
          <p className="text-sm text-gray-400 mt-1">Try adjusting your search or filters</p>
        </div>
      )}

      {/* Summary */}
      <div className="bg-gray-100 rounded-lg p-4 flex items-center justify-between">
        <div className="text-sm text-gray-600">
          Showing {filteredDocuments.length} of {documents.length} documents
        </div>
        <div className="text-sm text-gray-600">
          Total size: {documents.reduce((acc, doc) => {
            const size = parseFloat(doc.size);
            return acc + (doc.size.includes('MB') ? size : size / 1024);
          }, 0).toFixed(1)} MB
        </div>
      </div>
    </div>
  );
}
