import os
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from pathlib import Path

# Fixes for semaphore and thread-related issues
os.environ["TOKENIZERS_PARALLELISM"] = "false"
faiss.omp_set_num_threads(1)

# Ensure cache directory exists
DEFAULT_INDEX_DIR = os.path.expanduser("~/.underdogcowboy/agents/indexes")
os.makedirs(DEFAULT_INDEX_DIR, exist_ok=True)

# Global Model Cache
def get_cached_model(model_name='all-MiniLM-L6-v2', cache_folder=None):
    """
    Load or initialize the SentenceTransformer model with a local cache.
    """
    if cache_folder is None:
        cache_folder = "/Users/reneluijk/projects/models/cache/all-MiniLM-L6-v2"
    return SentenceTransformer(model_name, cache_folder=cache_folder)

# Agent-Specific Functions
def initialize_agent_index(agent_name, model, index_dir=DEFAULT_INDEX_DIR):
    """
    Initialize or load a FAISS index for a specific agent.
    """
    dimension = model.get_sentence_embedding_dimension()
    index_path = f"{index_dir}/{agent_name}_index.faiss"

    if Path(index_path).exists():
        index = faiss.read_index(index_path)
    else:
        index = faiss.IndexIDMap(faiss.IndexFlatL2(dimension))
    
    return index, index_path

def add_data_to_agent_index(agent_index, embeddings, ids):
    """
    Add embeddings with unique IDs to the agent's FAISS index.
    """
    agent_index.add_with_ids(embeddings, ids)

def remove_data_from_agent_index(agent_index, ids_to_remove):
    """
    Remove specific embeddings from the FAISS index using their IDs.
    """
    agent_index.remove_ids(ids_to_remove)

def save_agent_index(agent_index, index_path):
    """
    Save the FAISS index to the specified path, ensuring the directory exists.
    """
    directory = os.path.dirname(index_path)
    os.makedirs(directory, exist_ok=True)
    faiss.write_index(agent_index, index_path)

def query_agent_index(agent_metadata, query, model, top_k=5):
    """
    Query a specific agent's index and return the results.
    """
    index = faiss.read_index(agent_metadata["index_path"])
    query_embedding = model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, top_k)
    return indices, distances

# Text Parsing and Chunking
def parse_and_chunk(file_path, chunk_size=512):
    """
    Parse a text file and split it into manageable chunks of the specified size.
    """
    text = Path(file_path).read_text(encoding='utf-8')
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

# Main Function
def main():
    # Initialize the SentenceTransformer model
    model = get_cached_model()

    # Setup agent-specific index
    agent_name = "Agent1"
    index, index_path = initialize_agent_index(agent_name, model)
    agent_metadata = {
        "agent_name": agent_name,
        "index_path": index_path
    }

    # Parse and chunk a file
    file_path = "/Users/reneluijk/projects/UnderdogCowboy_fork/underdogcowboy/core/rag/concept_dev/example.md"
    chunks = parse_and_chunk(file_path)

    # Encode the text chunks
    embeddings = model.encode(chunks, batch_size=8, convert_to_numpy=True)

    # Assign unique IDs and add data to the FAISS index
    ids = np.arange(len(embeddings))  # Generate unique IDs
    add_data_to_agent_index(index, embeddings, ids)

    # Save the FAISS index to disk
    save_agent_index(index, index_path)

    # Query the agent's FAISS index
    query = "What is this document about?"
    indices, distances = query_agent_index(agent_metadata, query, model)

    # Print query results
    print(f"Query Results: Indices: {indices}, Distances: {distances}")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.set_start_method("spawn", force=True)  # Use spawn start method
    main()
