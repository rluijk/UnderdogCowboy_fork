import importlib.util
import os

# Predefined components
from underdogcowboy.core.commandtools.agent_flow.ui_components.center_content_ui import CenterContent

UI_COMPONENTS = {
    "CenterContent": CenterContent,
}

def dynamic_import(module_path):
    """
    Dynamically import a class from a given module path.

    Args:
        module_path (str): The full module path in the format 'folder.module.ClassName'.

    Returns:
        The imported class, or None if the import fails.
    """
    try:
        module_name, class_name = module_path.rsplit('.', 1)
        module_file = module_name.replace('.', '/') + ".py"  # Convert module path to file path
        spec = importlib.util.spec_from_file_location(module_name, module_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, class_name)
    except (ImportError, AttributeError, ValueError, FileNotFoundError) as e:
        print(f"Error importing {module_path}: {e}")
        return None


def get_ui_component(component_config):
    """
    Fetch a UI component by name or path from the registry or dynamically import it.

    Args:
        component_config (str | dict): The component name or a dictionary with "path" for dynamic imports.

    Returns:
        The UI component class if found, otherwise None.
    """
    if isinstance(component_config, str):
        # Check if the component is in the predefined registry
        component = UI_COMPONENTS.get(component_config)
        if component:
            return component
        # If not found, treat the string as a dynamic import path
        return dynamic_import(component_config)
    elif isinstance(component_config, dict) and "path" in component_config:
        # Dynamically import a component from the specified path in a dictionary
        return dynamic_import(component_config["path"])
    return None
