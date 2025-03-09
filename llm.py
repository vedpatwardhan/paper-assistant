# imports
from dotenv import load_dotenv
import json
import time
from litellm import completion, RateLimitError
from prompts import (
    intro_sections_system_prompt,
    classify_system_prompt,
    concepts_convo_system_prompt,
    concepts_system_prompt,
    papers_system_prompt,
    consolidate_system_prompt,
    subcluster_system_prompt,
    exploration_system_prompt,
)
from models import (
    ClassifyResponse,
    Cluster,
    Concept,
    ConceptsResponse,
    ConsolidatedResponse,
    ExplorationResponse,
    IntroSectionsResponse,
    PapersResponse,
    SubClusterResponse,
)


# load env vars
load_dotenv()


def rate_limit_completion(fn, *args, **kwargs):
    """
    Wrapper for the litellm completion function to retry on rate limit errors.
    """
    try:
        return completion(*args, **kwargs)
    except RateLimitError:
        print(f"We have hit the rate limits at {fn}!")
        seconds = 15
        while seconds > 0:
            print(
                f"Next try to call the API in {'' if seconds >= 10 else '0'}{seconds} seconds",
                end="\r",
            )
            seconds -= 1
            time.sleep(1)
        return rate_limit_completion(fn, *args, **kwargs)


def get_intro_sections(paper_sections: dict[str, str], paper_id: str):
    """
    Extract the intro sections of the paper (abstract, introduction, etc.)
    """
    print(f"Paper id: {paper_id}")
    intro_sections_user_prompt = (
        "------------\n" + "\n".join(paper_sections.keys()) + "\n------------"
    )
    return IntroSectionsResponse(
        **json.loads(
            rate_limit_completion(
                fn="get_intro_sections",
                model="gemini/gemini-2.0-flash",
                messages=[
                    {"role": "system", "content": intro_sections_system_prompt},
                    {"role": "user", "content": intro_sections_user_prompt},
                ],
                response_format={
                    "type": "json_object",
                    "response_schema": IntroSectionsResponse.model_json_schema(),
                },
            )
            .choices[0]
            .message.content
        )
    )


def get_concepts(
    intro_response: IntroSectionsResponse, paper_sections: dict[str, str], paper_id: str
):
    """
    Process the intro sections of the paper to extract major concepts.
    """
    print(f"Paper id: {paper_id}")
    intro_prompt = "\n\n".join(
        f"""
------------
Name: {item[0]}
Content: {item[1]}
------------
"""
        for item in list(paper_sections.items())
    )

    concepts_user_prompt = f"""
============

Title: {intro_response.title}

{intro_prompt}

============
"""
    return ConceptsResponse(
        **json.loads(
            rate_limit_completion(
                fn="get_concepts",
                model="gemini/gemini-2.0-flash",
                messages=[
                    {"role": "system", "content": concepts_system_prompt},
                    {"role": "user", "content": concepts_user_prompt},
                ],
                response_format={
                    "type": "json_object",
                    "response_schema": ConceptsResponse.model_json_schema(),
                },
            )
            .choices[0]
            .message.content
        )
    )


def classify_concept(
    concept: Concept, clusters: dict[str, Cluster]
) -> ClassifyResponse:
    """
    Classify the concepts into the cluster it relates to the most.
    """
    classify_user_prompt = """
Clusters:
============
"""
    for idx, cluster_id in enumerate(clusters):
        name = clusters[cluster_id].name
        description = clusters[cluster_id].description
        classify_user_prompt += f"""
Cluster{idx + 1}:
ID: {cluster_id}
Name: {name}
Description: {description}

------------

"""

    classify_user_prompt += f"""
============


Concept:
============
Name: {concept.name}
Description: {concept.description}
============

============
"""
    return ClassifyResponse(
        **json.loads(
            rate_limit_completion(
                fn="classify_concept",
                model="gemini/gemini-2.0-flash",
                messages=[
                    {"role": "system", "content": classify_system_prompt},
                    {"role": "user", "content": classify_user_prompt},
                ],
                response_format={
                    "type": "json_object",
                    "response_schema": ClassifyResponse.model_json_schema(),
                },
            )
            .choices[0]
            .message.content
        )
    )


def create_subclusters(
    cluster: Cluster,
    concepts: dict[str, Concept],
    other_subclusters: dict[str, Cluster],
) -> SubClusterResponse:
    """
    Break down a cluster into sub-clusters based on the concepts inside the cluster.
    """
    subcluster_user_prompt = f"""
Cluster
------------
name: {cluster.name}
description: {cluster.description}
------------

Concepts:
------------
"""

    for idx, concept_id in enumerate(concepts.keys()):
        concept_data = concepts[concept_id]
        subcluster_user_prompt += f"""
Concept {idx + 1}:
name: {concept_data.name}
description: {concept_data.description}

"""

    subcluster_user_prompt += """
------------

Other Sub-clusters:
------------
"""

    for idx, subcluster_id in enumerate(other_subclusters.keys()):
        subcluster = other_subclusters[subcluster_id]
        subcluster_user_prompt += f"""
Sub-cluster {idx + 1}:
name: {subcluster.name}
description: {subcluster.description}

"""

    subcluster_user_prompt += """
------------

============
"""

    return SubClusterResponse(
        **json.loads(
            rate_limit_completion(
                fn="create_subclusters",
                model="gemini/gemini-2.0-flash",
                messages=[
                    {"role": "system", "content": subcluster_system_prompt},
                    {"role": "user", "content": subcluster_user_prompt},
                ],
                response_format={
                    "type": "json_object",
                    "response_schema": SubClusterResponse.model_json_schema(),
                },
            )
            .choices[0]
            .message.content
        )
    )


def get_relevant_clusters(
    conversation: list[dict[str, str]], clusters: dict[str, Cluster]
):
    """
    Get all clusters relevant to a particular conversation.
    """
    exploration_user_prompt = f"""
Conversation:
============
{json.dumps(conversation, indent=4)}

Clusters:
============
"""
    for idx, cluster in clusters.items():
        exploration_user_prompt += f"""
Cluster{idx}:
ID: {idx}
Name: {cluster.name}
Description: {cluster.description}

------------

"""

    return ExplorationResponse(
        **json.loads(
            rate_limit_completion(
                fn="create_subclusters",
                model="gemini/gemini-2.0-flash",
                messages=[
                    {"role": "system", "content": exploration_system_prompt},
                    {"role": "user", "content": exploration_user_prompt},
                ],
                response_format={
                    "type": "json_object",
                    "response_schema": ExplorationResponse.model_json_schema(),
                },
            )
            .choices[0]
            .message.content
        )
    )


def get_relevant_papers(
    conversation: list[dict[str, str]], papers: dict[int, str]
) -> PapersResponse:
    """
    Get all papers relevant to a particular conversation.
    """
    papers_user_prompt = f"""
Conversation:
============
{json.dumps(conversation, indent=4)}

Papers:
============
"""
    for idx, paper_id in enumerate(papers):
        papers_user_prompt += f"""
Paper{idx}:
ID: {paper_id}
Name: {papers[paper_id]}

------------
"""
    return PapersResponse(
        **json.loads(
            rate_limit_completion(
                fn="get_relevant_papers",
                model="gemini/gemini-2.0-flash",
                messages=[
                    {"role": "system", "content": papers_system_prompt},
                    {"role": "user", "content": papers_user_prompt},
                ],
                response_format={
                    "type": "json_object",
                    "response_schema": PapersResponse.model_json_schema(),
                },
            )
            .choices[0]
            .message.content
        )
    )


def get_user_response(
    messages: list[dict[str, str]],
    cluster_concepts: list[dict[str, str | list[dict[str, str]]]],
    paper_concepts: list[dict[str, str | list[dict[str, str]]]],
) -> ConsolidatedResponse:
    """
    Use the relevant clusters, papers and their concepts to return the final response.
    """
    consolidate_user_prompt = f"""
Messages:
------------
{json.dumps(messages, indent=4)}

Clusters:
------------
{json.dumps(cluster_concepts, indent=4)}

Papers:
------------
{json.dumps(paper_concepts, indent=4)}
"""
    return ConsolidatedResponse(
        **json.loads(
            rate_limit_completion(
                fn="get_user_response",
                model="gemini/gemini-2.0-flash",
                messages=[
                    {"role": "system", "content": consolidate_system_prompt},
                    {"role": "user", "content": consolidate_user_prompt},
                ],
                response_format={
                    "type": "json_object",
                    "response_schema": ConsolidatedResponse.model_json_schema(),
                },
            )
            .choices[0]
            .message.content
        )
    )
