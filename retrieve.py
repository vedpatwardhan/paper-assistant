from db import (
    get_all_papers,
    get_cluster,
    get_concepts_for_cluster,
    get_concepts_for_paper,
    get_paper_for_concept,
)
from llm import get_relevant_papers, get_user_response
from utils import find_relevant_clusters


if __name__ == "__main__":
    end = False
    messages = []
    while not end:
        # input
        print("\n============\nEnter your query: ")
        query = input("")
        print("============")

        # exit route
        if query in ["quit", "q", "end", "exit"]:
            end = True
            continue

        # retrieve relevant clusters
        messages.append({"role": "user", "content": query})
        answer = ""
        data = []
        cluster_ids, other_concepts = find_relevant_clusters(
            conversation=messages,
            store=False,
        )
        cluster_concepts = {
            cluster_id: {
                "concepts": [
                    {
                        "name": concept.name,
                        "description": concept.description,
                        "paper": get_paper_for_concept(concept_id),
                    }
                    for concept_id, concept in get_concepts_for_cluster(
                        cluster_id
                    ).items()
                ],
                "cluster": get_cluster(cluster_id).model_dump(),
            }
            for cluster_id in cluster_ids
        }
        cluster_concepts = {
            **cluster_concepts,
            **{
                cluster_id: {
                    "concepts": [
                        {
                            "name": concept.name,
                            "description": concept.description,
                            "paper": get_paper_for_concept(concept_id),
                        }
                        for concept_id, concept in get_concepts_for_cluster(
                            cluster_id
                        ).items()
                    ],
                    "cluster": get_cluster(cluster_id).model_dump(),
                }
                for cluster_id in other_concepts
            },
        }

        # retrieve relevant papers
        all_papers = get_all_papers()
        all_paper_ids = list(all_papers.keys())
        all_papers = {idx: all_papers[pid] for idx, pid in enumerate(all_paper_ids)}
        papers = get_relevant_papers(messages, all_papers).relevant_papers
        paper_concepts = {
            paper.paper_id: {
                "name": paper.paper_name,
                "concepts": [
                    concept.model_dump()
                    for concept in get_concepts_for_paper(
                        all_paper_ids[paper.paper_id]
                    ).values()
                ],
            }
            for paper in papers
        }

        # consolidate response
        answer = get_user_response(messages, cluster_concepts, paper_concepts).answer

        # output
        messages.append({"role": "assistant", "content": answer})
        print(answer)
