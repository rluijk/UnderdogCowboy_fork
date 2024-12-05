


# tests/test_agent_model_cache.py

import pytest
from underdogcowboy.core.agent import Agent, get_cached_model, MODEL_CACHE

def test_get_cached_model_caching(tmp_path):
    """
    Test that get_cached_model loads a new model if not cached and retrieves it from cache if already loaded.
    
    This test performs the following steps:
    1. Clears the MODEL_CACHE to ensure a clean state.
    2. Loads a model using get_cached_model, which should add it to the cache.
    3. Asserts that the model is present in MODEL_CACHE after loading.
    4. Calls get_cached_model again with the same parameters.
    5. Asserts that the returned model is the same instance from the cache.
    """
    # Step 1: Clear the MODEL_CACHE before the test
    MODEL_CACHE.clear()
    
    # Define the model name and use the temporary directory for caching
    model_name = "all-MiniLM-L6-v2"  # A lightweight and commonly used model
    cache_folder = tmp_path / "models"
    
    # Ensure the cache directory exists
    cache_folder.mkdir(parents=True, exist_ok=True)
    
    # Step 2: First call - should load the model and add to cache
    model1 = get_cached_model(model_name=model_name, cache_folder=str(cache_folder))
    
    # Step 3: Assert that the model is now in MODEL_CACHE
    assert model_name in MODEL_CACHE, "Model should be added to MODEL_CACHE after loading."
    assert MODEL_CACHE[model_name] == model1, "Cached model should match the loaded model."
    
    # Step 4: Second call - should retrieve the model from cache
    model2 = get_cached_model(model_name=model_name, cache_folder=str(cache_folder))
    
    # Step 5: Assert that the retrieved model is the same as the cached model
    assert MODEL_CACHE[model_name] == model2, "Cached model should be retrieved on second call."
    assert model1 is model2, "Both calls should return the same model instance."
