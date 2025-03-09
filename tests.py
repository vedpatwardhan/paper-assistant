# imports
import pytest
from db import add_cluster, add_sub_cluster, get_all_clusters, get_cluster
from models import Concept
from utils import find_relevant_clusters


# seed clusters
CLUSTERS = [
    {
        "name": "Models",
        "description": """
This cluster represents concepts that specifically involve neural network models, their architectures and feature representations. It doesn't include algorithms, strategies, tricks and techniques used for models but rather the models themselves.
Vision models: include concepts specific to neural network models processing images and videos. Both images or videos could contain 2D or 3D, could be in the input or output. Any form of visual-only data processing falls under this category
Language models: include concepts related to neural network models processing text, could be in the input or output for various kinds of tasks.
Multi-modal models: include concepts that involve neural network models processing multiple modalities of data at once. For e.g. processing text and images at the same time. It's important to note that images and videos are a single modality so models processing images to videos or vice-versa don't fall under this category, same applies to any form of visual-only data processing.
There's also models: of other modalities of data, e.g. audio, signals, etc. and those concepts would also fall under this category.
""",
    },
    {
        "name": "Resources",
        "description": """
This cluster includes concepts that involve resources about various experiments such as datasets, benchmarks or challenges/competitions. These could be datasets, benchmarks or challenges/competitions, generally this is explicitly stated in the title or description of the concept, so for e.g. a dataset concept would contain the word dataset in it's title most of the time.
Datasets concepts include all kinds of datasets for various kinds of tasks. The dataset can be in various kinds of modalities and also be specific to certain domains where it's applicable.
Benchmark concepts include various evaluation benchmarks used for comparing different works. Benchmarks are generally specific to a particular domain or task which they try to evaluate algorithms/techniques/models.
Challenge concepts tie into Benchmarks to some extent, but challenges involve a competitive aspect to them, such as a particular task performed over a short period of time on platforms such as Kaggle and workshops in various conferences.
""",
    },
    {
        "name": "Algorithms",
        "description": """
This cluster includes concepts that involve all kinds of algorithms, methods, strategies, tricks and techniques (but except neural network models). These span from training to inference to deployment and for optimizing code on various kinds of hardware and any other general technique that is used in some paper. It doesn't necessarily need to be a whole algorithm, even if it's some sort of a smart trick it would still fall under this cluster.
Generally, a concept named with the word algorithm, method or strategy falls under this category by default.
training concepts: includes concepts involving algorithms, strategies, tricks and techniques relevant to the training process of models. Some examples include learning algorithms like gradient descent, training techniques like Masked Language Modeling, learning rate schedulers like cosine, various kinds of parallelization to optimize training, and any other algorithm, trick or technique that plays a role in training models.
production concepts: includes concepts involving algorithms, strategies, tricks and techniques relevant to the productionizing models which includes their inference, deployment and operations. This includes algorithms such as optimizing performance of models on deployment, scaling performance using parallelizaztion, creating serverless deployments on cloud, other hardware optimizations, etc.
other concepts: includes all kinds of concepts that can't be definitively categorized into training or production, these are just general techniques that could be applied anywhere in any paper.
""",
    },
    {
        "name": "Others",
        "description": """
This cluster includes various other concepts such as those related to social impact, those specific to certain domains and various kinds of developer tools.
Social impact concepts include those that relate to various social aspects such AI safety, ethics, safeguards, regulations, etc.
Domain-specific concepts include those that are specific to their domains, e.g. medicine, zoology, law, etc. These concepts can involve any kind of modality, data, algorithm, but it has a specific niche.
Developer tools concepts include those This cluster includes concepts involving developer tools, mostly open-source that help perform certain tasks. These include APIs for optimally using hardware, certain layers of abstracton for developing projects, running evaluations, operations and productionizing some project.
""",
    },
]

# populate db if empty
database = "test"
clusters = get_all_clusters(database=database)
if len(clusters) == 0:
    root_cluster_id = add_cluster("root", "Root Cluster", database=database)
    for cluster in CLUSTERS:
        add_sub_cluster(
            cluster["name"], cluster["description"], root_cluster_id, database=database
        )

# test cases
TEST_CASES = [
    {
        "name": "Video Super-Resolution (VSR) Models for 3D Reconstruction",
        "description": "This paper introduces the use of Video Super-Resolution models to tackle the challenge of 3D super-resolution, which requires transforming low-resolution (LR) multi-view images into high-resolution (HR) 3D models. Unlike traditional methods that treat each image independently, the approach leverages the temporal relationships between frames, which enhances spatial consistency in the reconstructed models. The authors emphasize that utilizing VSR models allows for referencing surrounding spatial information, leading to better accuracy and detail in the reconstruction process.",
        "cluster": "Models",
    },
    {
        "name": "Artifact Mitigation in VSR-based 3D Super-Resolution",
        "description": "Addressing Artifacts from Rendered Images: The paper identifies that directly applying VSR models to rendered images from 3D Gaussian Splatting (3DGS) introduces artifacts (stripy or blob-like) due to the distribution mismatch between training data (natural LR videos) and testing data (rendered LR videos from 3D models). This negatively impacts the performance of pre-trained VSR models. The paper aims to ensure VSR models receive desired input without fine-tuning by avoiding rendered images and their associated artifacts.",
        "cluster": "Others",
    },
    {
        "name": "HuGe100K Dataset",
        "description": "HuGe100K is a revolutionary large-scale dataset comprising over 2.4 million high-resolution multi-view images of 100,000 diverse subjects. It significantly expands the scale and diversity of training data available for human reconstruction, addressing the limitations of existing datasets. The dataset emphasizes varied attributes such as body shape, age, clothing, and movements, thus enabling model generalization across a wide range of human forms and poses.",
        "cluster": "Resources",
    },
    {
        "name": "IDOL Framework",
        "description": "IDOL, the proposed model, utilizes a feed-forward transformer architecture that processes a single input image to reconstruct a 3D human model instantly. It distinguishes itself by operating within a unified semantic representation space, enabling it to achieve high-fidelity and animatable outputs efficiently. This model bypasses the need for generative refinement processes, allowing for rapid processing times and better integration with various applications.",
        "cluster": "Models",
    },
    {
        "name": "Gaussian Splatting Representation",
        "description": "The use of 3D Gaussian splatting in IDOL's architecture enables the model to efficiently represent complex human geometries and textures in a unified UV space. This approach simplifies the rendering and animation of the avatars, allowing for real-time performance while maintaining high fidelity. The Gaussian representations reduce computational complexity and enhance the model’s ability to generalize across diverse reference images.",
        "cluster": "Models",
    },
]


@pytest.mark.parametrize("test_case", TEST_CASES)
def test_classify(test_case):
    # create concept from test case
    concept = Concept(name=test_case["name"], description=test_case["description"])
    
    # find relevant clusters
    cluster_ids = find_relevant_clusters(concept, database=database)
    
    # test assertion
    assert len(cluster_ids) > 0
    assert get_cluster(cluster_ids[0], database=database).name == test_case["cluster"]
