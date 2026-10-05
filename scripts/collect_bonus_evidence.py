"""Save live Neo4j diagnostics, clearly distinct from API benchmark results."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from src.graph import Neo4jGraph


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["hint", "bonus"], required=True)
    args = parser.parse_args()
    load_dotenv()
    graph = Neo4jGraph(os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                       os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password123"))
    graph.ontology_mode = args.mode
    questions = json.loads(Path("data/benchmark_kg.json").read_text(encoding="utf-8"))
    # The same manually selected relevant source IDs in both diagnostics.
    # These are NOT presented as vector search results or accuracy scores.
    seeds = {"Q3": ["news-100260918080821054"],
             "Q4": ["news-100260920221957595"],
             "Q5": ["news-100260917203001265"]}
    evidence = {"mode": args.mode, "kind": "live Neo4j diagnostic with manually supplied source seeds",
                "stats": graph.stats(), "contexts": {}}
    for q in questions:
        if q["id"] in seeds:
            evidence["contexts"][q["id"]] = {"question": q["question"],
                "doc_ids": seeds[q["id"]], "facts": graph.context(q["question"], seeds[q["id"]])}
    queries = {
        "labels": "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label",
        "relationships": "MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS n ORDER BY rel",
        "mdma_cases": "MATCH (k:Case)-[:INVOLVES]->(:Substance {name:'MDMA'}) RETURN k.name AS name, k.doc_id AS doc_id ORDER BY doc_id",
    }
    if args.mode == "bonus":
        queries.update({
            "mdma_250_thresholds": "MATCH (:Article {id:'Điều 250 BLHS'})-[:HAS_CLAUSE]->(cl:Clause)-[:HAS_THRESHOLD]->(t:Threshold)-[:OF_SUBSTANCE]->(:Substance {name:'MDMA'}) RETURN cl.number AS clause, t.min_g AS min_g, t.max_g AS max_g, cl.penalty AS penalty ORDER BY clause",
            "person_assertions": "MATCH (p:Person)-[:HAS_PARTICIPATION]->(v:Participation) RETURN p.name AS name, v.charge AS charge, v.stage AS stage, v.sentence AS sentence, v.sentence_stage AS sentence_stage, v.doc_id AS doc_id, v.evidence AS evidence ORDER BY name, doc_id",
        })
    evidence["queries"] = {key: {"cypher": query, "rows": graph.run(query)}
                            for key, query in queries.items()}
    graph.close()
    target = Path(f"report/evidence/{args.mode}.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved live diagnostics: {target}")


if __name__ == "__main__":
    main()
