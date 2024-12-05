import os 
import json
import re

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
import mimetypes

from typing import ( TYPE_CHECKING, 
                     Union,Optional,
                     Dict, Any )

if TYPE_CHECKING:
    from .dialog_manager import DialogManager




# Global cache for SentenceTransformer models
MODEL_CACHE = {}

def get_cached_model(model_name="all-MiniLM-L6-v2", cache_folder=None):
    """
    Load or retrieve a cached SentenceTransformer model.
    """
    if model_name not in MODEL_CACHE:
        if cache_folder is None:
            cache_folder = os.path.expanduser("~/.underdogcowboy/models")
        os.makedirs(cache_folder, exist_ok=True)
        MODEL_CACHE[model_name] = SentenceTransformer(model_name, cache_folder=cache_folder)
    return MODEL_CACHE[model_name]

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """
    Splits a large text into smaller chunks for efficient embedding and indexing.

    Args:
        text (str): The input text to split.
        chunk_size (int): The maximum size of each chunk.
        overlap (int): Number of overlapping characters between chunks.

    Returns:
        list[str]: List of text chunks.
    """
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks



class Agent:
    """
    Represents an agent with associated content loaded from a JSON file.

    This class encapsulates the properties and behavior of an agent, including
    its identifier, filename, package, and content. It can load agent data
    from a JSON file and handle potential errors during the loading process.

    Attributes:
        id (str): The identifier of the agent, derived from the filename.
        filename (str): The name of the JSON file containing the agent data.
        package (str): The package or directory where the agent file is located.
        is_user_defined (bool): Indicates whether the agent is user-defined.
        content (dict): The loaded content of the agent file.
    """

    dialog_manager: Optional['DialogManager']

    def __init__(self, filename: str, package: str, is_user_defined: bool = False) -> None:
      
        self.id: str = os.path.splitext(filename)[0]
        self.name: str = self.id
        self.filename: str = filename
        self.package: str = package
        self.is_user_defined: bool = is_user_defined
        self.content: Optional[Dict[str, Any]] = self._load_content()
        self.dialog_manager: Optional['DialogManager'] = None
        self.response = None

        # FAISS 

        # FAISS index attributes
        self.index = None
        self.index_path = None

        # Shared model instance
        self.model = get_cached_model()
        # Initialize FAISS index
        self._initialize_or_create_index()

        # picks up file references send via messages, and adds them to the Rag System
        self.auto_index_file_refs = True # decide on the option set: set via config (yaml), init, during use, via load of meta data agent

    
    def __or__(self, other_agent):
        """
        Overloads the | operator to perform operations between agents.

        Args:
            other_agent: Another agent to interact with.

        Returns:
            Any: The result of the interaction between agents.
        """
        if hasattr(other_agent, 'compress') and callable(other_agent.compress):
            # If other_agent has a compress method, use it
            return other_agent.compress(self.content)
        elif hasattr(self, 'process') and callable(self.process):
            # If self has a process method, use it with other_agent
            return self.process(other_agent)
        else:
            raise TypeError(f"Unsupported operation between {self.__class__.__name__} and {other_agent.__class__.__name__}")

    def __rshift__(self, user_input: str) -> Any:
        """
        Overloads the >> operator to send a message to the agent.

        Args:
            user_input (str): The user's message to send to the agent.

        Returns:
            Any: The agent's response.
        """
        return self.message(user_input)

    def _load_content(self) -> Optional[Dict[str, Any]]:
        try:
            file_path = os.path.join(self.package, self.filename)
            with open(file_path, 'r') as file:
                content = file.read()
            return json.loads(content)
        except FileNotFoundError:
            print(f"Agent file {self.filename} not found.")
            return None 
        except Exception as e:
            print(f"Error loading agent file: {str(e)}")
            return None
    
    def message(self, user_input: str) -> Any:
        """
        Handle incoming messages, extract file paths, and process them for indexing.

        Args:
            user_input (str): The user's message, potentially containing file paths.

        Returns:
            Any: The agent's response.
        """
        if self.dialog_manager is None:
            raise ValueError("Agent is not registered with a dialog manager")

        if self.auto_index_file_refs:
            # Extract file paths from the message
            file_paths = self._extract_text_file_paths(user_input)
            for file_path in file_paths:
                if os.path.exists(file_path) and self._is_text_file(file_path):
                    print(f"Indexing file: {file_path}")
                    self.add_file_to_index(file_path)
                else:
                    print(f"Skipped file: {file_path} (nonexistent or not a text file)")

        # Process the message through the dialog manager
        self.response = self.dialog_manager.message(self, user_input)
        return self.response

    def _extract_text_file_paths(self, text: str) -> list[str]:
        """
        Extract potential file paths from a given text.

        Args:
            text (str): The input text.

        Returns:
            list[str]: List of extracted file paths.
        """
        # Regex pattern to match Unix-style absolute file paths with 
        pattern = r'(/[\w\-/\. ]+\.(md|txt))' # not on windows?

        # Find all matches in the text
        return re.findall(pattern, text)

     
    def _is_text_file(self, file_path: str) -> bool:
        """
        Determine if the provided file is a text file based on MIME type.

        Args:
            file_path (str): The path to the file.

        Returns:
            bool: True if the file is a text file, False otherwise.
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type and mime_type.startswith("text")

    def get_last_response(self) -> Optional[str]:
        """
        Returns the last response of the agent.
        If there's no response yet, returns None.
        """
        return self.response.text if self.response else None

    def register_with_dialog_manager(self, dialog_manager: 'DialogManager') -> None:                  
        if self.dialog_manager != dialog_manager:
            self.dialog_manager = dialog_manager
            self.dialog_manager.prepare_agent(self)    

    def assess(self,msg: str) -> bool:
        return True        
    
    def receive_update(self, update_data: dict):
        """
        Handle updates sent from the CLI.

        Args:
            update_data (dict): The data being sent as an update.
        """
        # For demonstration, we'll simply print the update.
        # Replace this with actual logic to handle the update as needed.
        print("Agent received update (in):")
        print(json.dumps(update_data, indent=2))



    """" FAISS related """


    def _initialize_or_create_index(self, index_dir="~/.underdogcowboy/agents/indexes") -> None:
        """
        Check if an FAISS index exists for this agent; if not, create and save it.
        """
        index_dir = os.path.expanduser(index_dir)
        os.makedirs(index_dir, exist_ok=True)

        self.index_path = os.path.join(index_dir, f"{self.name}_index.faiss")
        dimension = self.model.get_sentence_embedding_dimension()

        if Path(self.index_path).exists():
            self.index = faiss.read_index(self.index_path)
        else:
            # Create a new index
            self.index = faiss.IndexIDMap(faiss.IndexFlatL2(dimension))
            # Save the newly created index to disk
            self.save_index()

    def initialize_index(self, index_dir="~/.underdogcowboy/agents/indexes") -> None:
        """
        Public method to explicitly initialize or load a FAISS index.
        """
        self._initialize_or_create_index(index_dir=index_dir)

    def save_index(self) -> None:
        """
        Save the FAISS index to disk.
        """
        if self.index and self.index_path:
            faiss.write_index(self.index, self.index_path)

    def add_file_to_index(self, file_path: str, chunk_size: int = 512, overlap: int = 50) -> None:
        """
        Read a file, chunk its content, and add it to the FAISS index.

        Args:
            file_path (str): Path to the text file.
            chunk_size (int): Size of each chunk.
            overlap (int): Overlap between chunks.
        """
        if self.index is None:
            raise ValueError("Index is not initialized.")
        
        # Ensure metadata storage exists
        if not hasattr(self, "metadata"):
            self.metadata = {}

        # Read and chunk the file
        text = Path(file_path).read_text(encoding="utf-8")
        chunks = chunk_text(text, chunk_size, overlap)

        # Encode chunks and add to the index
        embeddings = self.model.encode(chunks, batch_size=8, convert_to_numpy=True)
        ids = np.arange(self.index.ntotal, self.index.ntotal + len(embeddings), dtype=np.int64)
        self.index.add_with_ids(embeddings, ids)

        # Store metadata mapping IDs to file and chunk details
        for i, chunk_id in enumerate(ids):
            self.metadata[chunk_id] = {
                "file_path": file_path,
                "chunk_text": chunks[i],
                "chunk_index": i
            }

        # Save metadata to disk for persistence
        self._save_metadata()

    def _save_metadata(self, metadata_path=None) -> None:
        """
        Save metadata to a JSON file for persistence.

        Args:
            metadata_path (str): Optional path to save metadata; defaults to the index directory.
        """
        if metadata_path is None:
            metadata_path = f"{self.index_path}.metadata.json"
        
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=4)

    def _load_metadata(self, metadata_path=None) -> None:
        """
        Load metadata from a JSON file.

        Args:
            metadata_path (str): Optional path to load metadata; defaults to the index directory.
        """
        if metadata_path is None:
            metadata_path = f"{self.index_path}.metadata.json"
        
        if Path(metadata_path).exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}

    def query_index(self, query: str, top_k: int = 5):
        """
        Query the FAISS index and return results with metadata.

        Args:
            query (str): Query string.
            top_k (int): Number of top results to return.

        Returns:
            list[dict]: List of results including metadata and distances.
        """
        if self.index is None:
            raise ValueError("Index is not initialized.")

        query_embedding = self.model.encode([query], convert_to_numpy=True)
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for i, d in zip(indices[0], distances[0]):
            if i != -1:
                metadata = self.metadata.get(i, {})
                results.append({
                    "id": int(i),
                    "distance": float(d),
                    "metadata": metadata
                })
        return results


    def remove_data_from_index(self, ids: list[int]) -> None:
        """
        Remove specific entries by their IDs from the FAISS index.
        """
        if self.index is None:
            raise ValueError("Index is not initialized.")
        
        self.index.remove_ids(np.array(ids, dtype=np.int64))