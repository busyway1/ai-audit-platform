"""
Multi-hop Retrieval Node for K-IFRS RAG

This module implements agent-controlled N-hop retrieval for the K-IFRS RAG system.
It follows related_paragraphs references to expand context when needed for complex queries.

Key Features:
    - LLM-based decision making for context expansion
    - Maximum 3-hop retrieval to prevent runaway expansion
    - Graceful degradation when MCP client is unavailable
    - Structured metadata tracking for debugging and analysis

Architecture:
    1. Receives initial search results with related_paragraphs references
    2. Uses GPT-4o-mini to evaluate if expansion is needed
    3. Fetches additional paragraphs via MCP client (when available)
    4. Returns expanded context with hop metadata

Reference: K-IFRS RAG Architecture Document
"""

import json
import logging
from typing import Dict, Any, List, Set, Optional

from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# MCP CLIENT IMPORT (GRACEFUL FALLBACK)
# ============================================================================

# MCPRagClient will be implemented in services/mcp_client.py
# For now, we provide a stub implementation for development/testing
try:
    from ...services.mcp_client import MCPRagClient
    MCP_CLIENT_AVAILABLE = True
except ImportError:
    MCP_CLIENT_AVAILABLE = False
    logger.warning(
        "[Multi-hop] MCPRagClient not available. "
        "Multi-hop retrieval will return original context."
    )

    # Stub implementation for development
    class MCPRagClient:  # type: ignore[no-redef]
        """Stub MCPRagClient for development when real client is unavailable."""

        async def get_paragraph_by_id(
            self,
            standard_id: str,
            paragraph_no: str
        ) -> Dict[str, Any]:
            """Stub implementation returns error status."""
            return {
                "status": "error",
                "message": "MCPRagClient not implemented yet"
            }


# ============================================================================
# PROMPTS
# ============================================================================

EXPANSION_CHECK_PROMPT = '''질문: {query}

현재 검색된 문단:
{current_content}

관련 참조:
{related_refs}

이 질문에 답하기 위해 관련 참조 문단을 추가로 조회해야 하나요?
조회가 필요한 참조만 선택해주세요.

다음 기준으로 판단하세요:
1. 현재 문단에서 참조하는 정의나 용어가 있는 경우
2. 예외 조항이나 추가 조건이 참조되는 경우
3. 적용 범위나 경과조치가 다른 문단에 있는 경우
4. 계산 방법이나 공시 요구사항이 별도 문단에 있는 경우

JSON 형식으로 응답:
{{"needs_expansion": true/false, "refs_to_fetch": ["standard_id.paragraph_no", ...], "reasoning": "판단 근거"}}
'''


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_paragraph_reference(ref: str) -> Optional[tuple[str, str]]:
    """
    Parse paragraph reference string into (standard_id, paragraph_no).

    Handles formats like:
        - "K-IFRS 1115.B34" -> ("K-IFRS 1115", "B34")
        - "K-IFRS 제1109호.5.5.1" -> ("K-IFRS 제1109호", "5.5.1")
        - "KIFRS1032.AG31" -> ("KIFRS1032", "AG31")

    Args:
        ref: Reference string in format "standard_id.paragraph_no"

    Returns:
        Tuple of (standard_id, paragraph_no) or None if parsing fails
    """
    if not ref or not isinstance(ref, str):
        return None

    # Find the last period that separates standard_id from paragraph_no
    # Handle edge cases like "K-IFRS 1115.B34" vs "K-IFRS 제1109호.5.5.1"
    parts = ref.rsplit(".", 1)

    if len(parts) == 2:
        standard_id, paragraph_no = parts
        standard_id = standard_id.strip()
        paragraph_no = paragraph_no.strip()

        if standard_id and paragraph_no:
            return (standard_id, paragraph_no)

    return None


def format_multihop_content(
    data: Dict[str, Any],
    hop_number: int
) -> str:
    """
    Format fetched paragraph data into a standardized string.

    Args:
        data: Paragraph data from MCP client
        hop_number: Current hop number (1-indexed)

    Returns:
        Formatted string for inclusion in expanded context
    """
    standard_id = data.get("standard_id", "Unknown")
    paragraph_no = data.get("paragraph_no", "Unknown")
    content = data.get("content", "")
    title = data.get("title", "")

    # Truncate long content for context efficiency
    max_content_length = 500
    if len(content) > max_content_length:
        content = content[:max_content_length] + "..."

    header = f"[Multi-hop #{hop_number}] {standard_id} {paragraph_no}"
    if title:
        header += f" - {title}"

    return f"{header}:\n{content}"


# ============================================================================
# MAIN NODE IMPLEMENTATION
# ============================================================================

async def multihop_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent-controlled Multi-hop retrieval node for K-IFRS RAG.

    This node implements intelligent context expansion by following
    related_paragraphs references when the LLM determines additional
    context is needed to answer the user's query.

    Input State:
        - standards: List[str] - Current context (from reranker)
        - search_candidates: List[Dict] - Full search results with metadata
            - Each candidate may contain:
                - content: str
                - related_paragraphs: List[str]
                - standard_id: str
                - paragraph_no: str
        - query: str - User's original question

    Output State:
        - standards: List[str] - Expanded context with multi-hop results
        - multihop_metadata: Dict - Metadata about the expansion process
            - hops: int - Number of additional paragraphs fetched
            - fetched_refs: List[str] - References that were fetched
            - max_hops: int - Maximum allowed hops (always 3)
            - expansion_reasoning: List[str] - LLM reasoning for each expansion

    Behavior:
        1. If no candidates or MCP client unavailable: returns original state
        2. For each top candidate (up to 5):
            a. Checks if related_paragraphs exist
            b. Asks LLM if expansion is needed
            c. Fetches recommended paragraphs via MCP
        3. Returns expanded context with metadata

    Error Handling:
        - LLM call failures: Logs warning, skips candidate
        - MCP fetch failures: Logs warning, continues with other refs
        - Invalid references: Skips with warning

    Example:
        ```python
        state = {
            "query": "수익인식 시점에 대해 설명해주세요",
            "standards": ["K-IFRS 1115.35: 수익은 ..."],
            "search_candidates": [
                {
                    "content": "수익은 기업이 고객에게...",
                    "related_paragraphs": ["K-IFRS 1115.B34", "K-IFRS 1115.B35"],
                    "standard_id": "K-IFRS 1115",
                    "paragraph_no": "35"
                }
            ]
        }

        result = await multihop_node(state)
        print(result["multihop_metadata"]["hops"])  # e.g., 2
        print(len(result["standards"]))  # Original + 2 expanded
        ```
    """
    # Extract state
    standards = state.get("standards", [])
    candidates = state.get("search_candidates", [])
    query = state.get("query", "")

    # Initialize metadata
    multihop_metadata: Dict[str, Any] = {
        "hops": 0,
        "fetched_refs": [],
        "max_hops": 3,
        "expansion_reasoning": [],
        "skipped_refs": [],
        "errors": []
    }

    # Early return if no candidates
    if not candidates:
        logger.info("[Multi-hop] No search candidates, skipping expansion")
        return {
            "standards": standards,
            "multihop_metadata": multihop_metadata
        }

    # Early return if MCP client not available (in production)
    if not MCP_CLIENT_AVAILABLE:
        logger.warning(
            "[Multi-hop] MCP client not available, returning original context"
        )
        multihop_metadata["errors"].append("MCPRagClient not available")
        return {
            "standards": standards,
            "multihop_metadata": multihop_metadata
        }

    # Initialize components
    mcp_client = MCPRagClient()
    fetched_ids: Set[str] = set()
    expanded_content: List[str] = list(standards)  # Copy original standards
    total_hops = 0
    max_hops = 3

    # Initialize OpenAI client
    try:
        openai_client = AsyncOpenAI()
    except Exception as e:
        logger.error(f"[Multi-hop] Failed to initialize OpenAI client: {e}")
        multihop_metadata["errors"].append(f"OpenAI client init failed: {str(e)}")
        return {
            "standards": standards,
            "multihop_metadata": multihop_metadata
        }

    # Process top candidates (limit to 5 for efficiency)
    for candidate_idx, candidate in enumerate(candidates[:5]):
        # Check if we've reached max hops
        if total_hops >= max_hops:
            logger.info(
                f"[Multi-hop] Reached max hops ({max_hops}), stopping expansion"
            )
            break

        # Get related paragraphs
        related = candidate.get("related_paragraphs", [])
        if not related:
            continue

        # Prepare current content for LLM evaluation
        current_content = candidate.get("content", "")
        if not current_content:
            continue

        # Limit related refs shown to LLM
        related_refs_str = ", ".join(related[:10])

        # Ask LLM if expansion is needed
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": EXPANSION_CHECK_PROMPT.format(
                        query=query,
                        current_content=current_content[:1000],  # Limit content length
                        related_refs=related_refs_str
                    )
                }],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=500
            )

            # Parse LLM response
            result_text = response.choices[0].message.content
            if not result_text:
                logger.warning(
                    f"[Multi-hop] Empty LLM response for candidate {candidate_idx}"
                )
                continue

            result = json.loads(result_text)

            # Store reasoning
            reasoning = result.get("reasoning", "No reasoning provided")
            multihop_metadata["expansion_reasoning"].append({
                "candidate_idx": candidate_idx,
                "needs_expansion": result.get("needs_expansion", False),
                "reasoning": reasoning
            })

            # Check if expansion is needed
            if not result.get("needs_expansion"):
                logger.debug(
                    f"[Multi-hop] Candidate {candidate_idx}: No expansion needed"
                )
                continue

            # Get refs to fetch (limit to 3 per candidate)
            refs_to_fetch = result.get("refs_to_fetch", [])[:3]

            for ref in refs_to_fetch:
                # Check hop limit
                if total_hops >= max_hops:
                    break

                # Skip already fetched refs
                if ref in fetched_ids:
                    continue

                # Parse reference
                parsed = parse_paragraph_reference(ref)
                if not parsed:
                    logger.warning(f"[Multi-hop] Invalid reference format: {ref}")
                    multihop_metadata["skipped_refs"].append({
                        "ref": ref,
                        "reason": "Invalid format"
                    })
                    continue

                standard_id, paragraph_no = parsed

                # Fetch via MCP
                try:
                    fetch_result = await mcp_client.get_paragraph_by_id(
                        standard_id=standard_id,
                        paragraph_no=paragraph_no
                    )

                    if fetch_result.get("status") == "success":
                        data = fetch_result.get("data", {})
                        total_hops += 1

                        # Format and add to expanded content
                        formatted_content = format_multihop_content(
                            data, total_hops
                        )
                        expanded_content.append(formatted_content)
                        fetched_ids.add(ref)

                        logger.info(
                            f"[Multi-hop] Fetched {ref} (hop {total_hops}/{max_hops})"
                        )
                    else:
                        error_msg = fetch_result.get("message", "Unknown error")
                        logger.warning(
                            f"[Multi-hop] Failed to fetch {ref}: {error_msg}"
                        )
                        multihop_metadata["skipped_refs"].append({
                            "ref": ref,
                            "reason": f"MCP fetch failed: {error_msg}"
                        })

                except Exception as e:
                    logger.error(
                        f"[Multi-hop] MCP client error for {ref}: {e}"
                    )
                    multihop_metadata["skipped_refs"].append({
                        "ref": ref,
                        "reason": f"MCP exception: {str(e)}"
                    })

        except json.JSONDecodeError as e:
            logger.warning(
                f"[Multi-hop] JSON parse error for candidate {candidate_idx}: {e}"
            )
            multihop_metadata["errors"].append(
                f"JSON parse error: {str(e)}"
            )
            continue

        except Exception as e:
            logger.warning(
                f"[Multi-hop] LLM call failed for candidate {candidate_idx}: {e}"
            )
            multihop_metadata["errors"].append(
                f"LLM call failed: {str(e)}"
            )
            continue

    # Update final metadata
    multihop_metadata["hops"] = total_hops
    multihop_metadata["fetched_refs"] = list(fetched_ids)

    logger.info(
        f"[Multi-hop] Completed: {total_hops} hops, "
        f"{len(fetched_ids)} unique refs fetched, "
        f"{len(expanded_content) - len(standards)} paragraphs added"
    )

    return {
        "standards": expanded_content,
        "multihop_metadata": multihop_metadata
    }


# ============================================================================
# TESTING UTILITIES
# ============================================================================

async def test_multihop_node():
    """
    Test multihop_node with mock data.

    This test function verifies the node's behavior without external dependencies.
    It tests both the expansion logic and graceful degradation.

    Usage:
        ```bash
        cd backend
        python -c "import asyncio; from src.graph.nodes.multihop_node import test_multihop_node; asyncio.run(test_multihop_node())"
        ```
    """
    print("=== Multi-hop Node Test ===\n")

    # Test case 1: Basic expansion test
    test_state = {
        "query": "K-IFRS 1115에서 수익인식의 5단계 모델에 대해 설명해주세요",
        "standards": [
            "K-IFRS 1115.9: 기업은 다음 단계를 적용하여 수익을 인식한다..."
        ],
        "search_candidates": [
            {
                "content": "기업은 다음 단계를 적용하여 수익을 인식한다: "
                          "(가) 고객과의 계약 식별 (문단 9-16) "
                          "(나) 계약의 수행의무 식별 (문단 22-30)",
                "related_paragraphs": [
                    "K-IFRS 1115.10",
                    "K-IFRS 1115.22",
                    "K-IFRS 1115.B34"
                ],
                "standard_id": "K-IFRS 1115",
                "paragraph_no": "9"
            }
        ]
    }

    print("Input state:")
    print(f"  Query: {test_state['query'][:50]}...")
    print(f"  Initial standards count: {len(test_state['standards'])}")
    print(f"  Search candidates: {len(test_state['search_candidates'])}")
    print()

    result = await multihop_node(test_state)

    print("Output state:")
    print(f"  Final standards count: {len(result['standards'])}")
    print(f"  Metadata: {json.dumps(result['multihop_metadata'], indent=2, ensure_ascii=False)}")
    print()

    # Test case 2: Empty candidates
    print("Test case 2: Empty candidates")
    empty_state = {
        "query": "테스트",
        "standards": ["Original content"],
        "search_candidates": []
    }

    empty_result = await multihop_node(empty_state)
    print(f"  Hops: {empty_result['multihop_metadata']['hops']}")
    print(f"  Standards unchanged: {empty_result['standards'] == empty_state['standards']}")
    print()

    print("=== Test Completed ===")


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    "multihop_node",
    "parse_paragraph_reference",
    "format_multihop_content",
    "test_multihop_node",
]
