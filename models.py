from pydantic import BaseModel


class IntroSectionsResponse(BaseModel):
    title: str
    intro_headers: list[str]


class Concept(BaseModel):
    name: str
    description: str


class ConceptsResponse(BaseModel):
    concepts: list[Concept]


class Cluster(BaseModel):
    name: str
    description: str


class Classify(BaseModel):
    cluster_id: int
    cluster_name: str


class Paper(BaseModel):
    paper_id: int
    paper_name: str


class ClassifyScore(Classify):
    confidence_score: float


class ClassifyResponse(BaseModel):
    cluster0: ClassifyScore
    cluster1: ClassifyScore


class SubClusterResponse(BaseModel):
    generalized_cluster: Cluster
    sub_clusters: list[Cluster]


class ConsolidatedResponse(BaseModel):
    answer: str


class ExplorationResponse(BaseModel):
    relevant_clusters: list[Classify]


class PapersResponse(BaseModel):
    relevant_papers: list[Paper]
