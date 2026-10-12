"""
Neo4j 게이트웨이 — GraphStore 포트 구현 (Cypher + GDS).

[Python 중급 적용 사례 — 예외 처리: 특정 오류만 무시하기]
  `gds.graph.drop` 은 그래프가 없으면 ClientError 를 던집니다. 이것은 "처음 실행" 이라는 정상 상황이라
  메시지를 검사해 그 경우만 무시하고(pass), 다른 ClientError 는 다시 올립니다(raise).
  "모든 예외를 삼키지 말고, 알고 있는 예외만 처리" 하는 원칙의 예입니다.
"""

from __future__ import annotations

from typing import Final

from neo4j import Driver
from neo4j.exceptions import ClientError, Neo4jError, ServiceUnavailable

from backend.domain.entities import GraphAlgorithm, GraphEdge, GraphNode, NodeScore
from backend.domain.exceptions import ExternalServiceError
from backend.domain.ports import GraphStore

# 알고리즘 이름 → GDS 프로시저. Literal 타입(GraphAlgorithm) 과 키가 1:1 로 맞아야 합니다.
_PROCEDURES: Final[dict[str, str]] = {
    "pagerank": "gds.pageRank.stream",
    "degree": "gds.degree.stream",
}


class Neo4jGraphStore(GraphStore):
    def __init__(self, driver: Driver, database: str, graph_name: str) -> None:
        self._driver = driver
        self._database = database
        self._graph_name = graph_name

    def merge_node(self, node: GraphNode) -> GraphNode:
        try:
            with self._driver.session(database=self._database) as session:
                record = session.run(
                    "MERGE (n:Entity {id: $id}) SET n.label = $label RETURN n.id AS id, n.label AS label",
                    id=node.id,
                    label=node.label,
                ).single()
        except (Neo4jError, ServiceUnavailable) as exc:
            raise ExternalServiceError("Neo4j 노드 생성 실패", service="neo4j") from exc
        if record is None:
            raise ExternalServiceError("Neo4j 가 노드를 반환하지 않았습니다.", service="neo4j")
        return GraphNode(id=record["id"], label=record["label"])

    def merge_edge(self, edge: GraphEdge) -> GraphEdge:
        try:
            with self._driver.session(database=self._database) as session:
                session.run(
                    """
                    MERGE (a:Entity {id: $source})
                    MERGE (b:Entity {id: $target})
                    MERGE (a)-[r:RELATES_TO]->(b)
                    SET r.weight = $weight
                    """,
                    source=edge.source,
                    target=edge.target,
                    weight=edge.weight,
                ).consume()
        except (Neo4jError, ServiceUnavailable) as exc:
            raise ExternalServiceError("Neo4j 엣지 생성 실패", service="neo4j") from exc
        return edge

    def analyze(self, algorithm: GraphAlgorithm, limit: int = 10) -> list[NodeScore]:
        procedure = _PROCEDURES[algorithm]
        try:
            with self._driver.session(database=self._database) as session:
                try:
                    session.run(
                        "CALL gds.graph.drop($graph_name, false) YIELD graphName", graph_name=self._graph_name
                    ).consume()
                except ClientError as exc:
                    if "does not exist" not in str(exc):
                        raise
                session.run(
                    """
                    CALL gds.graph.project($graph_name, 'Entity',
                        {RELATES_TO: {orientation: 'NATURAL', properties: 'weight'}})
                    """,
                    graph_name=self._graph_name,
                ).consume()
                result = session.run(
                    f"""
                    CALL {procedure}($graph_name)
                    YIELD nodeId, score
                    RETURN gds.util.asNode(nodeId).id AS id, score
                    ORDER BY score DESC
                    LIMIT $limit
                    """,
                    graph_name=self._graph_name,
                    limit=limit,
                )
                return [NodeScore(id=row["id"], score=float(row["score"])) for row in result]
        except (Neo4jError, ServiceUnavailable) as exc:
            raise ExternalServiceError("Neo4j 그래프 분석 실패", service="neo4j") from exc
