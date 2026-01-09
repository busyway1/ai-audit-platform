"""MCP Tool Wrappers for LangGraph Agents

This module provides LangChain tool wrappers around MCP server functionality,
enabling LangGraph agents to call MCP tools through the standard tool interface.

Tool Bindings:
    - StandardRetrieverAgent: search_standards, get_paragraph_by_id (mcp-rag)
    - ExcelParserAgent: read_structure, analyze_workpaper_structure (mcp-excel-processor)
    - PartnerAgent: search_company_news, get_industry_insights (mcp-web-research)

Each tool is designed to:
    1. Call the appropriate MCP client asynchronously
    2. Handle errors gracefully with fallback behavior
    3. Return structured JSON responses for LLM processing

Usage:
    ```python
    from langchain_openai import ChatOpenAI
    from src.tools.mcp_tools import (
        search_standards, get_paragraph_by_id,
        read_excel_structure, analyze_workpaper_structure,
        search_company_news, get_industry_insights
    )

    # Bind tools to LLM
    llm = ChatOpenAI(model="gpt-4o-mini")
    llm_with_tools = llm.bind_tools([search_standards, get_paragraph_by_id])
    ```
"""

import json
import logging
from typing import Optional, List
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# ============================================================================
# GLOBAL MCP CLIENT INSTANCES (Lazy initialization)
# ============================================================================

_rag_client = None
_excel_client = None


async def _get_rag_client():
    """Get or create MCP RAG client singleton."""
    global _rag_client
    if _rag_client is None:
        from ..services.mcp_client import MCPRagClient
        _rag_client = MCPRagClient()
    return _rag_client


async def _get_excel_client():
    """Get or create MCP Excel client singleton."""
    global _excel_client
    if _excel_client is None:
        from ..services.mcp_client import MCPExcelClient
        _excel_client = MCPExcelClient()
    return _excel_client


# ============================================================================
# MCP-RAG TOOLS (For StandardRetrieverAgent)
# ============================================================================

@tool
async def search_standards(
    query: str,
    top_k: int = 10,
    mode: str = "hybrid",
    standard_filter: Optional[str] = None
) -> str:
    """Search K-IFRS/K-GAAS audit standards using hybrid search.

    This tool searches the knowledge base for relevant audit standards
    using a combination of BM25 lexical search and vector semantic search
    with Reciprocal Rank Fusion (RRF) for optimal results.

    Args:
        query: Search query in Korean or English (e.g., "수익인식 5단계",
               "revenue recognition timing", "리스 식별 기준")
        top_k: Maximum number of results to return (default: 10)
        mode: Search mode - "hybrid" (default), "vector", or "bm25"
        standard_filter: Optional filter for specific standard (e.g., "K-IFRS 1115")

    Returns:
        JSON string containing search results with:
        - status: "success" or "error"
        - results: List of matching paragraphs with content, standard_id, paragraph_no
        - metadata: Search duration, mode used, candidate counts

    Example:
        >>> result = await search_standards("수익인식 5단계 모형", top_k=5)
        >>> data = json.loads(result)
        >>> for r in data["results"]:
        ...     print(f"{r['standard_id']} {r['paragraph_no']}: {r['content'][:100]}")
    """
    try:
        client = await _get_rag_client()

        # Check health first
        if not await client.health_check():
            logger.warning("MCP RAG server unavailable, returning fallback")
            return json.dumps({
                "status": "unavailable",
                "message": "MCP RAG server is not available",
                "results": [],
                "fallback": True
            })

        # Execute search
        result = await client.search_standards(
            query_text=query,
            top_k=top_k,
            mode=mode,
            standard_filter=standard_filter
        )

        # Transform response for LLM consumption
        if result.get("status") == "success":
            data = result.get("data", {})
            formatted_results = []

            for r in data.get("results", [])[:top_k]:
                formatted_results.append({
                    "standard_id": r.get("standard_id", "Unknown"),
                    "paragraph_no": r.get("paragraph_no", ""),
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "topic": r.get("topic", ""),
                    "section_type": r.get("section_type", ""),
                    "relevance_score": r.get("scores", {}).get("combined", 0),
                    "related_paragraphs": r.get("related_paragraphs", [])
                })

            return json.dumps({
                "status": "success",
                "query": query,
                "mode": mode,
                "results_count": len(formatted_results),
                "results": formatted_results,
                "metadata": data.get("metadata", {})
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "error",
                "message": result.get("message", "Search failed"),
                "results": []
            }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"search_standards error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e),
            "results": []
        }, ensure_ascii=False)


@tool
async def get_paragraph_by_id(
    standard_id: str,
    paragraph_no: str,
    include_related: bool = True
) -> str:
    """Get a specific K-IFRS/K-GAAS paragraph by ID for multi-hop retrieval.

    This tool retrieves a specific paragraph from the standards knowledge base.
    Use this for following related_paragraphs references to build comprehensive
    context for audit procedures.

    Args:
        standard_id: Standard identifier (e.g., "K-IFRS 1115", "K-GAAS 315")
        paragraph_no: Paragraph number (e.g., "9", "B34", "IE5", "AG15")
        include_related: Include preview of related paragraphs (default: True)

    Returns:
        JSON string containing:
        - status: "success", "not_found", or "error"
        - data: Paragraph content, hierarchy_path, topic, related_paragraphs

    Example:
        >>> result = await get_paragraph_by_id("K-IFRS 1115", "9")
        >>> data = json.loads(result)
        >>> print(data["data"]["content"])
    """
    try:
        client = await _get_rag_client()

        if not await client.health_check():
            return json.dumps({
                "status": "unavailable",
                "message": "MCP RAG server is not available",
                "data": None,
                "fallback": True
            })

        result = await client.get_paragraph_by_id(
            standard_id=standard_id,
            paragraph_no=paragraph_no,
            include_related=include_related
        )

        if result.get("status") == "success":
            data = result.get("data", {})
            return json.dumps({
                "status": "success",
                "data": {
                    "id": data.get("id"),
                    "standard_id": standard_id,
                    "paragraph_no": paragraph_no,
                    "content": data.get("content", ""),
                    "title": data.get("title", ""),
                    "topic": data.get("topic", ""),
                    "hierarchy_path": data.get("hierarchy_path", ""),
                    "section_type": data.get("section_type", ""),
                    "related_paragraphs": data.get("related_paragraphs", [])
                }
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": result.get("status", "error"),
                "message": result.get("message", "Paragraph not found"),
                "data": None
            }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"get_paragraph_by_id error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e),
            "data": None
        }, ensure_ascii=False)


# ============================================================================
# MCP-EXCEL TOOLS (For ExcelParserAgent)
# ============================================================================

@tool
async def read_excel_structure(
    file_path: Optional[str] = None,
    file_url: Optional[str] = None,
    sheet_name: Optional[str] = None
) -> str:
    """Read and analyze the structure of an Excel workpaper file.

    This tool extracts the structure of an Excel file including:
    - Sheet names and their purposes
    - Column headers and data types
    - Row counts and data ranges
    - Detected patterns (trial balance, journal entries, etc.)

    Args:
        file_path: Local path to Excel file (optional if file_url provided)
        file_url: URL to download Excel file from storage (optional if file_path provided)
        sheet_name: Specific sheet to analyze (default: all sheets)

    Returns:
        JSON string containing:
        - status: "success" or "error"
        - structure: Sheet metadata, columns, data types, patterns detected
        - recommendations: Suggested processing approach

    Example:
        >>> result = await read_excel_structure(file_path="/data/trial_balance.xlsx")
        >>> data = json.loads(result)
        >>> print(f"Sheets: {data['structure']['sheets']}")
    """
    if not file_path and not file_url:
        return json.dumps({
            "status": "error",
            "message": "Either file_path or file_url must be provided",
            "structure": None
        })

    try:
        client = await _get_excel_client()

        if not await client.health_check():
            return json.dumps({
                "status": "unavailable",
                "message": "MCP Excel server is not available",
                "structure": None,
                "fallback": True
            })

        # Use parse_excel with structure-only mode
        arguments = {
            "category": "Structure",
            "validate_data": False,
            "detect_anomalies": False
        }

        if file_path:
            arguments["file_path"] = file_path
        if file_url:
            arguments["file_url"] = file_url
        if sheet_name:
            arguments["sheet_name"] = sheet_name

        result = await client._call_tool("read_structure", arguments)

        if result.get("status") == "success":
            return json.dumps({
                "status": "success",
                "structure": result.get("data", {}),
                "metadata": result.get("metadata", {})
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "error",
                "message": result.get("message", "Failed to read structure"),
                "structure": None
            }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"read_excel_structure error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e),
            "structure": None
        }, ensure_ascii=False)


@tool
async def analyze_workpaper_structure(
    file_path: Optional[str] = None,
    file_url: Optional[str] = None,
    category: str = "General"
) -> str:
    """Analyze an Excel workpaper for audit-specific structure and content.

    This tool performs deep analysis of Excel workpapers including:
    - Trial balance structure detection
    - Account mapping identification
    - Data quality assessment
    - Anomaly detection for audit red flags

    Args:
        file_path: Local path to Excel workpaper
        file_url: URL to download Excel workpaper
        category: Account category context (Sales, Inventory, AR, AP, etc.)

    Returns:
        JSON string containing:
        - status: "success" or "error"
        - analysis: Data quality score, detected patterns, anomalies
        - summary: Transaction count, total amounts, period covered
        - recommendations: Suggested audit procedures

    Example:
        >>> result = await analyze_workpaper_structure(
        ...     file_path="/data/sales_tb.xlsx",
        ...     category="Sales"
        ... )
        >>> data = json.loads(result)
        >>> print(f"Quality: {data['analysis']['data_quality']}")
    """
    if not file_path and not file_url:
        return json.dumps({
            "status": "error",
            "message": "Either file_path or file_url must be provided",
            "analysis": None
        })

    try:
        client = await _get_excel_client()

        if not await client.health_check():
            return json.dumps({
                "status": "unavailable",
                "message": "MCP Excel server is not available",
                "analysis": None,
                "fallback": True
            })

        # Full parse with validation and anomaly detection
        result = await client.parse_excel(
            file_path=file_path,
            file_url=file_url,
            category=category,
            validate_data=True,
            detect_anomalies=True
        )

        if result.get("status") == "success":
            data = result.get("data", {})
            return json.dumps({
                "status": "success",
                "analysis": {
                    "data_quality": data.get("data_quality", "UNKNOWN"),
                    "transaction_count": data.get("transaction_count", 0),
                    "total_amount": data.get("total_amount", 0),
                    "period": data.get("period", "Unknown"),
                    "anomalies": data.get("anomalies", []),
                    "anomaly_count": len(data.get("anomalies", []))
                },
                "summary": data.get("summary", {}),
                "metadata": result.get("metadata", {}),
                "recommendations": _generate_audit_recommendations(data)
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "error",
                "message": result.get("message", "Analysis failed"),
                "analysis": None
            }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"analyze_workpaper_structure error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e),
            "analysis": None
        }, ensure_ascii=False)


def _generate_audit_recommendations(data: dict) -> List[str]:
    """Generate audit recommendations based on analysis results."""
    recommendations = []
    anomalies = data.get("anomalies", [])
    data_quality = data.get("data_quality", "UNKNOWN")

    if data_quality == "POOR":
        recommendations.append(
            "Data quality is poor. Consider requesting clean data from client."
        )

    if any(a.get("severity") == "High" for a in anomalies):
        recommendations.append(
            "High severity anomalies detected. Prioritize investigation of flagged items."
        )

    if data.get("transaction_count", 0) > 1000:
        recommendations.append(
            "Large transaction volume. Consider statistical sampling approach."
        )

    if not recommendations:
        recommendations.append(
            "Data quality appears satisfactory. Proceed with standard audit procedures."
        )

    return recommendations


# ============================================================================
# MCP-WEB-RESEARCH TOOLS (For PartnerAgent)
# ============================================================================

@tool
async def search_company_news(
    company_name: str,
    keywords: Optional[List[str]] = None,
    max_results: int = 5,
    language: str = "ko"
) -> str:
    """Search for recent news and developments about a company.

    This tool searches for company-related news that may be relevant
    to audit risk assessment, including:
    - Financial news and earnings announcements
    - Regulatory actions or investigations
    - Management changes
    - Industry developments affecting the company

    Args:
        company_name: Company name to search for
        keywords: Additional keywords to narrow search (e.g., ["fraud", "investigation"])
        max_results: Maximum number of results (default: 5)
        language: Language preference - "ko" (Korean) or "en" (English)

    Returns:
        JSON string containing:
        - status: "success" or "error"
        - results: List of news items with title, snippet, url, date
        - risk_indicators: Any identified risk-related mentions

    Example:
        >>> result = await search_company_news("삼성전자", keywords=["실적"])
        >>> data = json.loads(result)
        >>> for news in data["results"]:
        ...     print(f"{news['title']}: {news['snippet'][:100]}")
    """
    import httpx

    try:
        # Build search query
        query = company_name
        if keywords:
            query += " " + " ".join(keywords)

        # Add audit-relevant context
        audit_query = f"{query} audit financial 감사 재무"

        # Try to call MCP web research server
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    "http://localhost:8002/search",
                    json={
                        "query": audit_query,
                        "max_results": max_results,
                        "language": language
                    }
                )
                response.raise_for_status()
                data = response.json()

                results = []
                risk_indicators = []

                for r in data.get("results", []):
                    result_item = {
                        "title": r.get("title", ""),
                        "snippet": r.get("snippet", r.get("content", "")[:200]),
                        "url": r.get("url", ""),
                        "date": r.get("date", ""),
                        "source": r.get("source", "")
                    }
                    results.append(result_item)

                    # Check for risk indicators
                    content = (r.get("title", "") + " " + r.get("snippet", "")).lower()
                    risk_words = ["fraud", "investigation", "lawsuit", "사기", "조사", "소송",
                                  "회계오류", "감사의견", "부정", "횡령"]
                    for word in risk_words:
                        if word in content:
                            risk_indicators.append({
                                "indicator": word,
                                "source": result_item["title"]
                            })

                return json.dumps({
                    "status": "success",
                    "company": company_name,
                    "results_count": len(results),
                    "results": results,
                    "risk_indicators": risk_indicators,
                    "has_risk_indicators": len(risk_indicators) > 0
                }, ensure_ascii=False)

            except (httpx.HTTPError, httpx.TimeoutException):
                # Fallback response when MCP server unavailable
                return json.dumps({
                    "status": "unavailable",
                    "message": "MCP Web Research server is not available",
                    "company": company_name,
                    "results": [],
                    "risk_indicators": [],
                    "fallback": True
                }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"search_company_news error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e),
            "results": []
        }, ensure_ascii=False)


@tool
async def get_industry_insights(
    industry: str,
    topic: str = "audit_risks",
    language: str = "ko"
) -> str:
    """Get industry-specific insights relevant for audit planning.

    This tool retrieves industry analysis and best practices including:
    - Common industry risks and audit focus areas
    - Regulatory requirements specific to the industry
    - Recent industry trends affecting financial reporting
    - Benchmark data for analytical procedures

    Args:
        industry: Industry name (e.g., "제조업", "금융", "IT", "유통")
        topic: Specific topic - "audit_risks", "regulations", "trends", "benchmarks"
        language: Language preference - "ko" or "en"

    Returns:
        JSON string containing:
        - status: "success" or "error"
        - insights: Industry-specific information and guidance
        - key_risks: Common audit risks for the industry
        - regulatory_focus: Relevant regulatory considerations

    Example:
        >>> result = await get_industry_insights("제조업", topic="audit_risks")
        >>> data = json.loads(result)
        >>> print(f"Key risks: {data['key_risks']}")
    """
    import httpx

    try:
        # Build industry-focused query
        topic_queries = {
            "audit_risks": f"{industry} 감사위험 주요위험 audit risk",
            "regulations": f"{industry} 회계기준 규정 K-IFRS regulation",
            "trends": f"{industry} 동향 트렌드 industry trends",
            "benchmarks": f"{industry} 재무비율 벤치마크 financial ratios"
        }

        query = topic_queries.get(topic, topic_queries["audit_risks"])

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    "http://localhost:8002/search",
                    json={
                        "query": query,
                        "max_results": 5,
                        "language": language
                    }
                )
                response.raise_for_status()
                data = response.json()

                # Process and structure insights
                insights = []
                key_risks = []
                regulatory_focus = []

                for r in data.get("results", []):
                    insights.append({
                        "title": r.get("title", ""),
                        "content": r.get("snippet", r.get("content", ""))[:300],
                        "url": r.get("url", ""),
                        "relevance": r.get("score", 0.5)
                    })

                # Extract risk mentions
                risk_keywords = {
                    "ko": ["위험", "리스크", "주의", "이슈"],
                    "en": ["risk", "concern", "issue", "attention"]
                }

                for r in data.get("results", []):
                    content = r.get("title", "") + " " + r.get("snippet", "")
                    for keyword in risk_keywords.get(language, risk_keywords["ko"]):
                        if keyword in content.lower():
                            # Extract sentence containing risk keyword
                            key_risks.append(r.get("title", "")[:100])
                            break

                return json.dumps({
                    "status": "success",
                    "industry": industry,
                    "topic": topic,
                    "insights": insights,
                    "key_risks": list(set(key_risks))[:5],
                    "regulatory_focus": regulatory_focus,
                    "recommendations": [
                        f"Consider {industry}-specific accounting standards",
                        "Review industry benchmarks for analytical procedures",
                        "Assess going concern risks based on industry trends"
                    ]
                }, ensure_ascii=False)

            except (httpx.HTTPError, httpx.TimeoutException):
                # Return fallback with general industry guidance
                return json.dumps({
                    "status": "unavailable",
                    "message": "MCP Web Research server is not available",
                    "industry": industry,
                    "topic": topic,
                    "insights": [],
                    "key_risks": _get_fallback_industry_risks(industry),
                    "regulatory_focus": [],
                    "fallback": True
                }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"get_industry_insights error: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e),
            "insights": []
        }, ensure_ascii=False)


def _get_fallback_industry_risks(industry: str) -> List[str]:
    """Get fallback industry risks when MCP unavailable."""
    industry_risks = {
        "제조업": [
            "재고자산 평가 및 진부화",
            "고정자산 손상차손",
            "관계사 거래 공정성"
        ],
        "금융": [
            "대손충당금 적정성",
            "파생상품 평가",
            "자기자본비율 규제 준수"
        ],
        "IT": [
            "수익인식 시점 (계약 이행 의무)",
            "무형자산 자본화 기준",
            "스톡옵션 비용 처리"
        ],
        "유통": [
            "재고자산 실사 및 평가",
            "매출채권 대손",
            "리베이트 및 판촉비 처리"
        ]
    }

    return industry_risks.get(industry, [
        "일반적인 수익인식 위험",
        "충당부채 추정의 적정성",
        "관계자 거래 검토"
    ])


# ============================================================================
# TOOL COLLECTIONS FOR AGENT BINDING
# ============================================================================

# Tools for StandardRetrieverAgent
RAG_TOOLS = [search_standards, get_paragraph_by_id]

# Tools for ExcelParserAgent
EXCEL_TOOLS = [read_excel_structure, analyze_workpaper_structure]

# Tools for PartnerAgent
WEB_RESEARCH_TOOLS = [search_company_news, get_industry_insights]

# All MCP tools
ALL_MCP_TOOLS = RAG_TOOLS + EXCEL_TOOLS + WEB_RESEARCH_TOOLS
