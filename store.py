# imports
import argparse
import os
import sys
from db import (
    add_concept_to_cluster,
    add_sub_cluster,
    delete_concept_from_cluster,
    get_all_clusters,
    get_cluster,
    add_cluster,
    get_concepts_for_cluster,
    get_non_connected_concepts,
    get_num_concepts,
    store_paper_and_concepts,
    update_cluster,
)
from llm import classify_concept, create_subclusters, get_concepts, get_intro_sections
from models import Cluster
from utils import (
    download_todays_papers,
    find_relevant_clusters,
    store_paper_markdown,
    get_sections,
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    
    # Add an optional argument 
    parser.add_argument("--existing", action="store_true", help="Indicates if existing papers need to be processed")
    args = parser.parse_args()

    if args.existing:
        paper_ids = [paper_id[:-4] for paper_id in os.listdir("papers")]
    else:
        # get todays papers and download to the papers folder
        paper_ids = download_todays_papers()

        # convert paper to markdown and store in the markdown folder
        store_paper_markdown(paper_ids)

    for paper_id in paper_ids:

        # get the sections inside each paper
        print("Getting sections")
        sections = get_sections(paper_id)

        # extract intros of each paper
        print("Getting intro headers")
        intro_sections = get_intro_sections(sections, paper_id)

        # get concepts based on the intros
        print("Getting concepts")
        concepts = get_concepts(intro_sections, sections, paper_id)

        # store paper and concepts
        print("Storing paper and concepts")
        non_connected_concepts = get_non_connected_concepts()
        concept_ids = store_paper_and_concepts(intro_sections, concepts, paper_id)

        # classify each concept
        concept_dict = {
            concept_id: concept
            for concept_id, concept in zip(concept_ids, concepts.concepts)
        }
        all_cluster_ids: list[str] = []
        for concept_id in concept_dict:
            cluster_ids, _ = find_relevant_clusters(concept_dict[concept_id])
            if len(get_all_clusters()) == 0:
                cluster_ids = [add_cluster("root", "Root Cluster")]
            for cluster_id in cluster_ids:
                add_concept_to_cluster(concept_id, cluster_id)
            all_cluster_ids += cluster_ids
        all_cluster_ids = list(set(all_cluster_ids))

        # reorganize if too many concepts
        num_concepts = get_num_concepts()
        if num_concepts > 10:
            print("Too many concepts, reorganizing")
            for cluster_id in all_cluster_ids:
                cluster = get_cluster(cluster_id)
                if cluster is None:
                    continue
                cluster_concepts = get_concepts_for_cluster(cluster_id)
                classification = dict()
                if len(cluster_concepts) > 10:
                    # create subclusters
                    other_subclusters = get_all_clusters(cluster_id)
                    subcluster_response = create_subclusters(
                        cluster, cluster_concepts, other_subclusters
                    )
                    new_cluster = subcluster_response.generalized_cluster

                    # update cluster and subclusters
                    if cluster.name not in [
                        "root",
                        "Models",
                        "Algorithms",
                        "Resources",
                        "Others",
                    ]:
                        update_cluster(cluster_id, new_cluster)
                    subclusters = subcluster_response.sub_clusters
                    subcluster_ids = [
                        add_sub_cluster(
                            subcluster.name, subcluster.description, cluster_id
                        )
                        for subcluster in subclusters
                    ]
                    subcluster_dict = {
                        subcluster_id: subcluster
                        for subcluster_id, subcluster in zip(
                            subcluster_ids, subclusters
                        )
                    }

                    # classify all concepts under the cluster again
                    combined_concepts_dict = {
                        **cluster_concepts,
                        **non_connected_concepts,
                    }
                    all_clusters = {
                        **subcluster_dict,
                        **other_subclusters,
                        cluster_id: Cluster(
                            name="None", description="None of the above"
                        ),
                    }
                    all_cluster_ids = list(all_clusters.keys())
                    classification_clusters = {
                        idx: all_clusters[cid]
                        for idx, cid in enumerate(all_cluster_ids)
                    }
                    classification = {
                        concept_id: classify_concept(
                            combined_concepts_dict[concept_id],
                            classification_clusters,
                        )
                        for concept_id in combined_concepts_dict
                    }
                    classification = {
                        concept_id: (
                            [
                                all_cluster_ids[
                                    classified_clusters.cluster0.cluster_id
                                ],
                                all_cluster_ids[
                                    classified_clusters.cluster1.cluster_id
                                ],
                            ]
                            if (
                                classified_clusters.cluster0.confidence_score >= 0.6
                                and classified_clusters.cluster1.confidence_score >= 0.6
                            )
                            else (
                                [
                                    all_cluster_ids[
                                        classified_clusters.cluster0.cluster_id
                                    ]
                                ]
                                if classified_clusters.cluster0.confidence_score >= 0.6
                                else []
                            )
                        )
                        for concept_id, classified_clusters in classification.items()
                    }

                    # update the graph
                    for concept_id in classification:
                        delete_concept_from_cluster(concept_id, cluster_id)
                        for new_cluster_id in classification[concept_id]:
                            add_concept_to_cluster(concept_id, new_cluster_id)
