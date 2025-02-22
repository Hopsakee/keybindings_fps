"""This module contains several functions that are used in creating the FastHTML gui that makes the handling of the keybindings database more user friendly."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/03_helpers.ipynb.

# %% auto 0
__all__ = ['get_project_root', 'update_binding_order']

# %% ../nbs/03_helpers.ipynb 3
from fasthtml.common import *
from fastcore.test import *

# %% ../nbs/03_helpers.ipynb 5
def get_project_root() -> Optional[Path]:
    """Get the project root directory from either notebook or module context"""
    try:
        try:
            get_ipython()
            current = Path.cwd()
        except NameError:
            current = Path(__file__).resolve().parent

        while current != current.parent: # Stop at root directory
            if (current / 'pyproject.toml').exists():
                return current
            current = current.parent
        raise FileNotFoundError("Could not find pyproject.toml in any parent directory")
    except Exception as e:
        print(f"Error finding project root: {str(e)}")
        return None

# %% ../nbs/03_helpers.ipynb 6
test_eq(get_project_root(), Path('/home/jelle/code/keybindings_fps'))

# %% ../nbs/03_helpers.ipynb 8
def update_binding_order(db: database,
                         binding_id: int,
                         new_order: int):
    """Update the sort_order of a binding"""
    db.t.bindings.update(dict(id=binding_id, sort_order=new_order))
