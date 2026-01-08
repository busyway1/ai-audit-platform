"""
LLM Reranking Node for K-IFRS RAG

Takes Top-30 candidates from MCP search and reranks to Top-5
using GPT-based relevance scoring with reasoning.

This is the "High Precision" step in "Wide Recall -> High Precision" strategy.

Reference:
- Wide Recall: MCP search returns 30 candidates (high recall, lower precision)
- High Precision: LLM reranking filters to 5 best matches (high precision)
- Strategy: Balances search coverage with response quality
"""

import json
import logging
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# RERANKING PROMPT
# ============================================================================

RERANK_SYSTEM_PROMPT = """당신은 K-IFRS 회계기준 전문가입니다.
사용자 질문에 가장 관련성 높은 문단 5개를 선정해주세요.

선정 기준:
1. 질문과의 직접적 관련성 (가장 중요)
2. 회계 처리 지침의 구체성
3. 적용 사례 또는 예시 포함 여부
4. 문단의 완결성 (필요한 정보가 충분히 포함되어 있는지)

출력 형식:
JSON 형식으로 정확히 5개의 문단을 선정하여 출력하세요.
"""

RERANK_USER_PROMPT_TEMPLATE = """## 사용자 질문
{query}

## 후보 문단들
{candidates}

## 출력 형식
각 선정된 문단에 대해:
1. 문단 ID
2. 관련성 점수 (0-10)
3. 선정 이유 (한 문장)

JSON 형식으로 출력:
{{"selected": [
    {{"id": "...", "score": 9, "reason": "..."}},
    {{"id": "...", "score": 8, "reason": "..."}},
    {{"id": "...", "score": 7, "reason": "..."}},
    {{"id": "...", "score": 6, "reason": "..."}},
    {{"id": "...", "score": 5, "reason": "..."}}
]}}
"""


# ============================================================================
# RERANKER NODE
# ============================================================================

async def rerank_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM-based reranking of search candidates.

    Takes Top-30 search candidates and reranks to Top-5 using GPT-based
    relevance scoring with Korean K-IFRS expertise.

    Input State:
        - search_candidates: List[Dict] from MCP search (Top-30)
          Each candidate should have: id, standard_id, paragraph_no, content
        - query: str user question

    Output State:
        - standards: List[str] reranked Top-5 (formatted for downstream use)
        - rerank_metadata: Dict with scores, reasons, and execution details

    Example:
        ```python
        state = {
            "query": "수익인식 시점은 언제인가요?",
            "search_candidates": [
                {
                    "id": "kifrs-1115-31",
                    "standard_id": "K-IFRS 1115",
                    "paragraph_no": "31",
                    "content": "수익은 고객에게 약속한 재화나 용역을..."
                },
                # ... 29 more candidates
            ]
        }

        result = await rerank_node(state)
        print(result["standards"])  # Top-5 formatted standards
        print(result["rerank_metadata"]["selections"])  # Detailed scoring
        ```

    Fallback Behavior:
        If LLM reranking fails (API error, parsing error), returns top 5
        candidates by original search order with error details in metadata.
    """
    candidates = state.get("search_candidates", [])
    query = state.get("query", "")

    logger.info(f"[Reranker] Starting rerank for query: {query[:50]}...")
    logger.info(f"[Reranker] Input candidates: {len(candidates)}")

    # Early return if no candidates
    if not candidates:
        logger.warning("[Reranker] No candidates to rerank")
        return {
            "standards": [],
            "rerank_metadata": {
                "input_count": 0,
                "output_count": 0,
                "error": "No candidates provided"
            }
        }

    # Format candidates for prompt (limit to 30)
    candidates_text = _format_candidates_for_prompt(candidates[:30])

    try:
        # Initialize LLM (gpt-4o-mini for cost-effective reranking)
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1  # Low temperature for consistent ranking
        )

        # Call LLM for reranking
        response = await llm.ainvoke([
            SystemMessage(content=RERANK_SYSTEM_PROMPT),
            HumanMessage(content=RERANK_USER_PROMPT_TEMPLATE.format(
                query=query,
                candidates=candidates_text
            ))
        ])

        # Parse LLM response
        result = _parse_rerank_response(response.content)
        selected_ids = [item["id"] for item in result.get("selected", [])]

        # Map back to full content
        id_to_candidate = {c["id"]: c for c in candidates}
        reranked_standards = []

        for sid in selected_ids[:5]:  # Ensure max 5
            if sid in id_to_candidate:
                candidate = id_to_candidate[sid]
                formatted = _format_standard_for_output(candidate)
                reranked_standards.append(formatted)

        logger.info(f"[Reranker] Successfully reranked to {len(reranked_standards)} standards")

        return {
            "standards": reranked_standards,
            "rerank_metadata": {
                "model": "gpt-4o-mini",
                "input_count": len(candidates),
                "output_count": len(reranked_standards),
                "selections": result.get("selected", []),
                "success": True
            }
        }

    except json.JSONDecodeError as e:
        logger.error(f"[Reranker] JSON parsing failed: {e}")
        return _fallback_rerank(candidates, str(e))

    except Exception as e:
        logger.error(f"[Reranker] Reranking failed: {e}")
        return _fallback_rerank(candidates, str(e))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_candidates_for_prompt(candidates: List[Dict]) -> str:
    """
    Format candidates list for LLM prompt.

    Args:
        candidates: List of candidate dictionaries

    Returns:
        Formatted string for prompt injection
    """
    formatted_lines = []

    for i, c in enumerate(candidates):
        content = c.get("content", "")
        # Truncate content to avoid token limits
        if len(content) > 300:
            content = content[:300] + "..."

        line = (
            f"[{i+1}] ID: {c.get('id', 'unknown')}\n"
            f"    기준서: {c.get('standard_id', '')} {c.get('paragraph_no', '')}\n"
            f"    내용: {content}"
        )
        formatted_lines.append(line)

    return "\n\n".join(formatted_lines)


def _format_standard_for_output(candidate: Dict) -> str:
    """
    Format a single candidate for output in standards list.

    Args:
        candidate: Single candidate dictionary

    Returns:
        Formatted string for downstream use
    """
    standard_id = candidate.get("standard_id", "")
    paragraph_no = candidate.get("paragraph_no", "")
    content = candidate.get("content", "")

    # Truncate content for output
    if len(content) > 200:
        content = content[:200] + "..."

    return f"{standard_id} {paragraph_no}: {content}"


def _parse_rerank_response(response_content: str) -> Dict[str, Any]:
    """
    Parse LLM response to extract reranking results.

    Handles various response formats and attempts to extract valid JSON.

    Args:
        response_content: Raw LLM response string

    Returns:
        Parsed dictionary with 'selected' list

    Raises:
        json.JSONDecodeError: If JSON parsing fails
    """
    # Try to extract JSON from response
    content = response_content.strip()

    # Handle markdown code blocks
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        content = content[start:end].strip()
    elif "```" in content:
        start = content.find("```") + 3
        end = content.find("```", start)
        content = content[start:end].strip()

    return json.loads(content)


def _fallback_rerank(candidates: List[Dict], error_message: str) -> Dict[str, Any]:
    """
    Fallback reranking when LLM fails.

    Returns top 5 candidates by original search order.

    Args:
        candidates: Original candidates list
        error_message: Error details for logging

    Returns:
        State update with fallback standards and error metadata
    """
    logger.warning(f"[Reranker] Using fallback rerank due to: {error_message}")

    fallback_standards = [
        _format_standard_for_output(c)
        for c in candidates[:5]
    ]

    return {
        "standards": fallback_standards,
        "rerank_metadata": {
            "error": error_message,
            "fallback": True,
            "input_count": len(candidates),
            "output_count": len(fallback_standards),
            "success": False
        }
    }


# ============================================================================
# TESTING UTILITY
# ============================================================================

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()

    async def test_reranker():
        """Test reranker node with mock data."""

        print("=== Reranker Node Test ===\n")

        # Mock search candidates
        mock_candidates = [
            {
                "id": "kifrs-1115-31",
                "standard_id": "K-IFRS 1115",
                "paragraph_no": "31",
                "content": "수익은 고객에게 약속한 재화나 용역을 이전하여 수행의무를 이행할 때 또는 기간에 걸쳐 이행하는 대로 인식한다."
            },
            {
                "id": "kifrs-1115-35",
                "standard_id": "K-IFRS 1115",
                "paragraph_no": "35",
                "content": "기업이 한 시점에 수행의무를 이행하는 경우에는 통제의 이전 시점을 결정하기 위해 문단 38의 통제 지표를 고려한다."
            },
            {
                "id": "kifrs-1115-38",
                "standard_id": "K-IFRS 1115",
                "paragraph_no": "38",
                "content": "통제의 이전을 나타낼 수 있는 지표에는 (가) 자산에 대한 현재 지급청구권이 있다, (나) 고객에게 자산의 법적 소유권이 있다 등이 포함된다."
            },
            {
                "id": "kifrs-1002-9",
                "standard_id": "K-IFRS 1002",
                "paragraph_no": "9",
                "content": "재고자산은 취득원가와 순실현가능가치 중 낮은 금액으로 측정한다."
            },
            {
                "id": "kgaas-500-a1",
                "standard_id": "K-GAAS 500",
                "paragraph_no": "A1",
                "content": "감사증거는 감사인이 감사의견의 근거가 되는 결론을 도출하는 데 사용하는 정보이다."
            },
        ]

        # Create test state
        test_state = {
            "query": "수익인식 시점은 언제인가요?",
            "search_candidates": mock_candidates
        }

        # Run reranker
        result = await rerank_node(test_state)

        print("=== Results ===")
        print(f"Standards count: {len(result['standards'])}")
        print(f"\nReranked Standards:")
        for i, std in enumerate(result["standards"], 1):
            print(f"  {i}. {std}")

        print(f"\nMetadata:")
        print(f"  Model: {result['rerank_metadata'].get('model', 'N/A')}")
        print(f"  Input count: {result['rerank_metadata'].get('input_count', 0)}")
        print(f"  Output count: {result['rerank_metadata'].get('output_count', 0)}")
        print(f"  Success: {result['rerank_metadata'].get('success', False)}")

        if result['rerank_metadata'].get('selections'):
            print(f"\nSelection Details:")
            for sel in result['rerank_metadata']['selections']:
                print(f"  - {sel['id']}: score={sel['score']}, reason={sel['reason']}")

        print("\n=== Test Completed ===")

    asyncio.run(test_reranker())
