'use client'

import * as React from 'react'
import { useState, useMemo } from 'react'
import { AlertCircle, CheckCircle2, Clock, XCircle, ArrowUpDown, Filter } from 'lucide-react'
import { HITLRequestCard } from './HITLRequestCard'
import { hitlRequests } from '../../data/mockData'
import type { HITLRequest, HITLRequestStatus, HITLRequestType } from '../../types/supabase'

type SortField = 'urgency' | 'date' | 'type'
type SortDirection = 'asc' | 'desc'

interface SortConfig {
  field: SortField
  direction: SortDirection
}

export function HITLQueue() {
  const [requests, setRequests] = useState<HITLRequest[]>(hitlRequests)
  const [filterStatus, setFilterStatus] = useState<HITLRequestStatus | 'all'>('all')
  const [filterType, setFilterType] = useState<HITLRequestType | 'all'>('all')
  const [sortConfig, setSortConfig] = useState<SortConfig>({ field: 'urgency', direction: 'desc' })

  const stats = useMemo(() => ({
    total: requests.length,
    pending: requests.filter(r => r.status === 'pending').length,
    approved: requests.filter(r => r.status === 'approved').length,
    rejected: requests.filter(r => r.status === 'rejected').length,
    critical: requests.filter(r => r.urgency_score >= 80 && r.status === 'pending').length
  }), [requests])

  const filteredAndSortedRequests = useMemo(() => {
    let filtered = requests.filter(request => {
      const matchesStatus = filterStatus === 'all' || request.status === filterStatus
      const matchesType = filterType === 'all' || request.request_type === filterType
      return matchesStatus && matchesType
    })

    filtered.sort((a, b) => {
      let comparison = 0
      switch (sortConfig.field) {
        case 'urgency':
          comparison = a.urgency_score - b.urgency_score
          break
        case 'date':
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          break
        case 'type':
          comparison = a.request_type.localeCompare(b.request_type)
          break
      }
      return sortConfig.direction === 'desc' ? -comparison : comparison
    })

    return filtered
  }, [requests, filterStatus, filterType, sortConfig])

  const handleApprove = async (requestId: string, response?: string) => {
    setRequests(prev => prev.map(request =>
      request.id === requestId
        ? {
            ...request,
            status: 'approved' as HITLRequestStatus,
            response: response || null,
            responded_at: new Date().toISOString(),
            responded_by: 'Current User',
            updated_at: new Date().toISOString()
          }
        : request
    ))
  }

  const handleReject = async (requestId: string, response?: string) => {
    setRequests(prev => prev.map(request =>
      request.id === requestId
        ? {
            ...request,
            status: 'rejected' as HITLRequestStatus,
            response: response || null,
            responded_at: new Date().toISOString(),
            responded_by: 'Current User',
            updated_at: new Date().toISOString()
          }
        : request
    ))
  }

  const toggleSort = (field: SortField) => {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'desc' ? 'asc' : 'desc'
    }))
  }

  const getStatusIcon = (status: HITLRequestStatus) => {
    switch (status) {
      case 'pending':
        return <Clock className="size-4 text-yellow-600" />
      case 'approved':
        return <CheckCircle2 className="size-4 text-green-600" />
      case 'rejected':
        return <XCircle className="size-4 text-red-600" />
      case 'expired':
        return <AlertCircle className="size-4 text-gray-400" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-semibold mb-2">Human-in-the-Loop Queue</h1>
        <p className="text-gray-600">Review and respond to AI agent requests requiring human judgment</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Total Requests</div>
          <div className="text-2xl font-medium">{stats.total}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Pending</div>
          <div className="text-2xl font-medium text-yellow-600">{stats.pending}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Critical Urgency</div>
          <div className="text-2xl font-medium text-red-600">{stats.critical}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Approved</div>
          <div className="text-2xl font-medium text-green-600">{stats.approved}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Rejected</div>
          <div className="text-2xl font-medium text-gray-600">{stats.rejected}</div>
        </div>
      </div>

      {/* Filters and Sorting */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="size-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Filters:</span>
          </div>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as HITLRequestStatus | 'all')}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="expired">Expired</option>
          </select>

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as HITLRequestType | 'all')}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="all">All Types</option>
            <option value="approval">Approval</option>
            <option value="clarification">Clarification</option>
            <option value="escalation">Escalation</option>
            <option value="review">Review</option>
          </select>

          <div className="flex-1" />

          <div className="flex items-center gap-2">
            <ArrowUpDown className="size-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Sort by:</span>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => toggleSort('urgency')}
              className={`px-3 py-2 text-sm rounded-md transition-colors ${
                sortConfig.field === 'urgency'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Urgency {sortConfig.field === 'urgency' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
            </button>
            <button
              onClick={() => toggleSort('date')}
              className={`px-3 py-2 text-sm rounded-md transition-colors ${
                sortConfig.field === 'date'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Date {sortConfig.field === 'date' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
            </button>
            <button
              onClick={() => toggleSort('type')}
              className={`px-3 py-2 text-sm rounded-md transition-colors ${
                sortConfig.field === 'type'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Type {sortConfig.field === 'type' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
            </button>
          </div>
        </div>
      </div>

      {/* Request List */}
      <div className="space-y-4">
        {filteredAndSortedRequests.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
            <AlertCircle className="size-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No requests found</h3>
            <p className="text-gray-600">
              {filterStatus !== 'all' || filterType !== 'all'
                ? 'Try adjusting your filters to see more results.'
                : 'There are no HITL requests at this time.'}
            </p>
          </div>
        ) : (
          filteredAndSortedRequests.map((request) => (
            <HITLRequestCard
              key={request.id}
              request={request}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          ))
        )}
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-sm text-gray-500 bg-gray-50 rounded-lg p-3">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            {getStatusIcon('pending')}
            <span>Pending: {stats.pending}</span>
          </span>
          <span className="flex items-center gap-1">
            {getStatusIcon('approved')}
            <span>Approved: {stats.approved}</span>
          </span>
          <span className="flex items-center gap-1">
            {getStatusIcon('rejected')}
            <span>Rejected: {stats.rejected}</span>
          </span>
        </div>
        <span>
          Showing {filteredAndSortedRequests.length} of {requests.length} requests
        </span>
      </div>
    </div>
  )
}

export default HITLQueue
