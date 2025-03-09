# imports
from bs4 import BeautifulSoup
from collections import OrderedDict
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
import os
import re
import requests
from tqdm import tqdm
from db import DATABASE, get_all_clusters, get_concepts_for_cluster
from llm import classify_concept, get_relevant_clusters
from models import Cluster, Concept


# initialize docling pipeline
pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = False
pipeline_options.do_table_structure = False
pipeline_options.table_structure_options.do_cell_matching = False
converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)


def get_todays_papers() -> list[dict[str, str]]:
    """
    Returns a list of papers on the huggingface page.
    """
    # get contents of page
    url = "https://huggingface.co/papers"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        papers = []

        # find all article elements
        for paper in soup.find_all(
            "article", class_="relative flex flex-col overflow-hidden rounded-xl border"
        ):
            # extract all headers and arxiv ids
            a_tag = paper.find("a", class_="line-clamp-3 cursor-pointer text-balance")
            title = a_tag.text.strip()
            link = a_tag["href"]
            papers.append({"title": title, "link": link})

        return papers
    else:
        raise Exception("Couldn't retrieve papers")


def download_todays_papers():
    """
    Download all papers from the huggingface page.
    """
    # get a list of today's papers
    papers: list[dict[str, str]] = get_todays_papers()
    paper_ids = []
    print("Downloading today's papers")
    for paper in tqdm(papers):
        arxiv_id = paper["link"][8:]
        # check if paper is already downloaded
        if not os.path.exists(f"papers/{arxiv_id}.pdf"):
            # download paper
            pdf_url = "https://arxiv.org/pdf/" + arxiv_id
            pdf_response = requests.get(pdf_url)
            
            # store paper
            with open(f"papers/{arxiv_id}.pdf", "wb") as f:
                f.write(pdf_response.content)
        paper_ids.append(arxiv_id)
    return paper_ids


def store_paper_markdown(paper_ids: list[str]):
    """
    Convert papers to markdown using docling.
    """
    print("Converting to markdown")
    pbar = tqdm(paper_ids)
    for paper_id in pbar:
        pbar.set_description(paper_id)
        # check if markdown already exists
        if not os.path.exists(f"markdown/{paper_id}.md"):
            # convert pdf to markdown
            source = f"papers/{paper_id}.pdf"
            result = converter.convert(source)
            paper_markdown = result.document.export_to_markdown()
            
            # store markdown
            with open(f"markdown/{paper_id}.md", "w") as f:
                f.write(paper_markdown)


def get_sections(paper_id: str):
    """
    Get all section headers from a paper using the markdown.
    """
    # read the markdown
    with open(f"markdown/{paper_id}.md") as f:
        paper_markdown = f.read()
    
    # get all headers
    header_pattern = r"^(\n## .+\n)$"
    re_chunks = re.split(header_pattern, paper_markdown, flags=re.MULTILINE)
    current_header = None
    paper_contents = dict()
    for chunk in re_chunks:
        chunk = chunk.lstrip("\n")
        if current_header and current_header not in paper_contents:
            paper_contents[current_header] = ""
        if chunk.startswith("## ") and chunk.endswith("\n"):
            current_header = chunk[3:-1]
        elif current_header:
            paper_contents[current_header] += chunk

    return paper_contents


def find_relevant_clusters(
    concept: Concept = None,
    conversation: list[dict[str, str]] = None,
    threshold: float = 0.6,
    store: bool = True,
    database: str = DATABASE
) -> list[str] | tuple[list[str], dict[str, Concept]]:
    """
    Find relevant clusters.
    While storing, we classify concepts into clusters and store based on thresholds.
    But when retrieving, we don't consider thresholds and just ask the llm for clusters
    based on the conversation with the user.
    """
    # start with the root cluster
    cluster_ids = list(get_all_clusters(database=database).keys())
    cluster_id = None
    relevant_clusters = []
    other_concepts = dict()
    while len(cluster_ids) > 0:
        # get current cluster
        cluster_id = cluster_ids.pop(0)
        
        # get all sub-clusters of that cluster
        clusters = get_all_clusters(cluster_id, database=database)
        all_cluster_ids = [*clusters.keys(), cluster_id]
        clusters = {
            idx: (
                clusters[cid]
                if cid in clusters
                else Cluster(name="None", description="None of the above")
            )
            for idx, cid in enumerate(all_cluster_ids)
        }
        
        # if no sub-clusters, store and exit
        if len(clusters) == 1:
            relevant_clusters.append(cluster_id)
            continue
        
        # store
        if store:
            # classify the concept into the clusters
            cluster_response = classify_concept(concept, clusters)
            cluster0, cluster1 = cluster_response.cluster0, cluster_response.cluster1
            cluster0_id, cluster1_id = (
                all_cluster_ids[cluster0.cluster_id],
                all_cluster_ids[cluster1.cluster_id],
            )
            
            # if no cluster is predicted with sufficient confidence, store and exit
            if (
                cluster0.confidence_score < threshold
                and cluster1.confidence_score < threshold
            ):
                relevant_clusters.append(cluster_id)
            else:
                # if cluster0 is predicted with sufficient confidence, add it to the list
                if cluster0.confidence_score >= threshold and cluster0_id != cluster_id:
                    cluster_ids.append(cluster0_id)
                # if not, just store the current cluster
                elif cluster0_id == cluster_id:
                    relevant_clusters.append(cluster_id)
            
                # if cluster1 is predicted with sufficient confidence, add it to the list
                if cluster1.confidence_score >= threshold and cluster1_id != cluster_id:
                    cluster_ids.append(cluster1_id)
                # if not, just store the current cluster
                elif cluster1_id == cluster_id:
                    relevant_clusters.append(cluster_id)
        
        # retrieve
        else:
            # get relevant clusters from the llm
            response_clusters = get_relevant_clusters(
                conversation, clusters
            ).relevant_clusters
            if not len(response_clusters):
                relevant_clusters.append(cluster_id)
            else:
                # get concepts from the current cluster
                other_concepts[cluster_id] = get_concepts_for_cluster(cluster_id)
                cluster_ids = list(
                    OrderedDict.fromkeys(
                        [
                            *cluster_ids,
                            *[
                                all_cluster_ids[cluster.cluster_id]
                                for cluster in response_clusters
                            ],
                        ]
                    )
                )
    return list(set(relevant_clusters)), other_concepts


def find_relevant_clusters_retrieve(
    conversation: list[dict[str, str]], database: str = DATABASE
) -> tuple[list[str], dict[str, Concept]]:
    """
    Find relevant clusters for retrieval.
    While storing, we classify concepts into clusters and store based on thresholds.
    But when retrieving, we don't consider thresholds and just ask the llm for clusters.
    """
    # get the root cluster
    cluster_ids = list(get_all_clusters(database=database).keys())
    cluster_id = None
    relevant_clusters = []
    other_concepts = dict()
    while len(cluster_ids) > 0:
        cluster_id = cluster_ids.pop(0)
        clusters = get_all_clusters(cluster_id, database=database)
        all_cluster_ids = [*clusters.keys(), cluster_id]
        clusters = {
            idx: (
                clusters[cid]
                if cid in clusters
                else Cluster(name="None", description="None of the above")
            )
            for idx, cid in enumerate(all_cluster_ids)
        }
        if len(clusters) == 1:
            relevant_clusters.append(cluster_id)
            continue
        response_clusters = get_relevant_clusters(
            conversation, clusters
        ).relevant_clusters
        if not len(response_clusters):
            relevant_clusters.append(cluster_id)
        else:
            other_concepts[cluster_id] = get_concepts_for_cluster(cluster_id)
            cluster_ids = list(
                OrderedDict.fromkeys(
                    [
                        *cluster_ids,
                        *[
                            all_cluster_ids[cluster.cluster_id]
                            for cluster in response_clusters
                        ],
                    ]
                )
            )
    return list(set(relevant_clusters)), other_concepts
