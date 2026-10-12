"""그래프 유스케이스 — Neo4j 를 몰라도 되는 얇은 애플리케이션 규칙."""

from __future__ import annotations

from backend.domain.entities import GraphAlgorithm, GraphEdge, GraphNode, NodeScore
from backend.domain.exceptions import ValidationError
from backend.domain.ports import GraphStore


class GraphUseCase:
    def __init__(self, store: GraphStore) -> None:
        self._store = store

    def add_node(self, node: GraphNode) -> GraphNode:
        return self._store.merge_node(node)

    def add_edge(self, edge: GraphEdge) -> GraphEdge:
        # 비즈니스 규칙: 자기 자신을 가리키는 엣지는 분석(PageRank) 결과를 왜곡하므로 금지.
        if edge.source == edge.target:
            raise ValidationError("source 와 target 이 같은 self-loop 엣지는 허용하지 않습니다.")
        return self._store.merge_edge(edge)

    def analyze(self, algorithm: GraphAlgorithm, limit: int = 10) -> list[NodeScore]:
        return self._store.analyze(algorithm, limit)
