# imports
from dotenv import load_dotenv
import os
from neo4j import GraphDatabase
from models import Cluster, Concept, ConceptsResponse, IntroSectionsResponse


# load env vars
load_dotenv()
DATABASE = os.environ.get("DATABASE", "")


def store_paper_and_concepts(
    intro_response: IntroSectionsResponse,
    concepts_response: ConceptsResponse,
    paper_id: str,
    database: str = DATABASE,
) -> list[str]:
    """
    Store the paper and corresponding concepts.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        concept_ids = []

        # store paper
        driver.execute_query(
            "create (p:Paper {name: $name, title: $title})",
            name=paper_id,
            title=intro_response.title,
        )

        # store concepts
        for concept in concepts_response.concepts:
            name = concept.name.replace('"', "'")

            # store concepts
            concept_ids.append(
                driver.execute_query(
                    "create (c:Concept {name: $name, description: $description}) return c",
                    name=name,
                    description=concept.description.replace('"', "'"),
                )
                .records[0]["c"]
                .element_id
            )

            # add connection between paper and concepts
            driver.execute_query(
                "match (c:Concept {name: $concept_name}), (p:Paper {name: $name}) "
                "create (c)-[:IN]->(p)",
                concept_name=name,
                name=paper_id,
            )
        return concept_ids


def get_all_papers(database: str = DATABASE) -> dict[str, str]:
    """
    Get a dict of all papers in the database.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        return {
            record["p"].element_id: record.data()["p"]["title"]
            for record in driver.execute_query(
                "match (p:Paper) return p",
            ).records
        }


def get_paper_for_concept(concept_id: str, database: str = DATABASE) -> str:
    """
    Get the paper that a particular concept belongs to.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        return driver.execute_query(
            "match (c:Concept)-[:IN]->(p:Paper) where elementId(c) = $id return p",
            id=concept_id,
        ).records[0]["p"]["title"]


def get_concepts_for_paper(paper_id: str, database: str = DATABASE) -> str:
    """
    Get all concepts part of a particular paper.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        return {
            record["c"].element_id: Concept(
                name=record.data()["c"]["name"],
                description=record.data()["c"]["description"],
            )
            for record in driver.execute_query(
                "match (c:Concept)-[:IN]->(p:Paper) where elementId(p) = $id return c",
                id=paper_id,
            ).records
        }


def get_all_clusters(
    cluster_id: str | None = None, database: str = DATABASE
) -> dict[str, Cluster]:
    """
    Get all clusters under a given cluster_id.
    Returns root cluster if cluster_id is None.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        return {
            record["c"].element_id: Cluster(
                name=record.data()["c"]["name"],
                description=record.data()["c"]["description"],
            )
            for record in (
                driver.execute_query(
                    "match (c:Cluster {name: $name}) return c", name="root"
                )
                if not cluster_id
                else driver.execute_query(
                    f"match (c:Cluster)-[:IN]->(c1:Cluster) where elementId(c1) = $id return c",
                    id=cluster_id,
                )
            ).records
        }


def get_num_concepts(database: str = DATABASE) -> int:
    """
    Get the number of concepts in the database.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        return (
            driver.execute_query("match (c:Concept) return count(c) as count")
            .records[0]
            .data()["count"]
        )


def get_concept(concept_id: str, database: str = DATABASE) -> Concept:
    """
    Get the details of a particular concept_id.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        concept_records = driver.execute_query(
            "match (c:Concept) where elementId(c)=$id return c", id=concept_id
        ).records[0]
        return Concept(
            name=concept_records.data()["c"]["name"],
            description=concept_records.data()["c"]["description"],
        )


def add_concept_to_cluster(concept_id, cluster_id, database: str = DATABASE):
    """
    Add a concept to a particular cluster.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        driver.execute_query(
            "match (co:Concept), (c:Cluster) "
            "where elementId(co) = $concept_id and elementId(c) = $cluster_id "
            "create (co)-[:IN]->(c)",
            concept_id=concept_id,
            cluster_id=cluster_id,
        )


def delete_concept_from_cluster(concept_id, cluster_id, database: str = DATABASE):
    """
    Delete a concept from a particular cluster.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        driver.execute_query(
            "match (co:Concept)-[r:IN]->(c:Cluster) "
            "where elementId(co) = $concept_id and elementId(c) = $cluster_id "
            "delete r",
            concept_id=concept_id,
            cluster_id=cluster_id,
        )


def add_cluster(name: str, description: str, database: str = DATABASE) -> str:
    """
    Add a cluster.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        return (
            driver.execute_query(
                "create (c:Cluster {name: $name, description: $description}) return c",
                name=name,
                description=description,
            )
            .records[0]["c"]
            .element_id
        )


def update_cluster(cluster_id: str, cluster: Cluster, database: str = DATABASE):
    """
    Update contents of a cluster.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        driver.execute_query(
            "match (c:Cluster) where elementId(c) = $id "
            "set c.name = $name, c.description = $description",
            id=cluster_id,
            name=cluster.name,
            description=cluster.description,
        )


def get_concepts_for_cluster(
    cluster_id: str, database: str = DATABASE
) -> dict[str, Concept]:
    """
    Get all concepts from a particular cluster.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        return {
            record["co"].element_id: Concept(
                name=record.data()["co"]["name"],
                description=record.data()["co"]["description"],
            )
            for record in driver.execute_query(
                "match (co:Concept)-[:IN]->(c:Cluster) where elementId(c) = $id return co",
                id=cluster_id,
            ).records
        }


def get_non_connected_concepts(database: str = DATABASE) -> dict[str, Concept]:
    """
    Get all concepts that aren't connected to any cluster.
    """
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        return {
            record["co"].element_id: Concept(
                name=record.data()["co"]["name"],
                description=record.data()["co"]["description"],
            )
            for record in driver.execute_query(
                "match (co:Concept) where not (co)-[:IN]->(:Cluster) return co"
            ).records
        }


def get_cluster(cluster_id: str, database: str = DATABASE) -> Cluster:
    """
    Get the details of a particular cluster_id.
    """
    try:
        with GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("vedpatwardhan", "vedpatwardhan"),
            database=database,
        ) as driver:
            return Cluster(
                name=driver.execute_query(
                    "match (c:Cluster) where elementId(c) = $id return c",
                    id=cluster_id,
                ).records[0]["c"]["name"],
                description=driver.execute_query(
                    "match (c:Cluster) where elementId(c) = $id return c",
                    id=cluster_id,
                ).records[0]["c"]["description"],
            )
    except IndexError:
        return None


def add_sub_cluster(
    sub_cluster_name: str,
    sub_cluster_description: str,
    cluster_id: str,
    database: str = DATABASE,
):
    """
    Add a cluster as a sub-cluster of another cluster
    """

    # add sub-cluster
    sub_cluster_id = add_cluster(
        sub_cluster_name, sub_cluster_description, database=database
    )
    with GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("vedpatwardhan", "vedpatwardhan"),
        database=database,
    ) as driver:
        # connect it to the main cluster
        driver.execute_query(
            "match (c1:Cluster {name: $sub_cluster_name, description: $sub_cluster_description}), (c:Cluster) where elementId(c) = $cluster_id "
            "create (c1)-[:IN]->(c)",
            cluster_id=cluster_id,
            sub_cluster_name=sub_cluster_name,
            sub_cluster_description=sub_cluster_description,
        )
    return sub_cluster_id
