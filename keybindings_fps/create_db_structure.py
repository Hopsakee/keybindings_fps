"""Core database functionality for the keybindings_fps app. This module is meant to run once to create the database and tables. Don't run this module again if the database already exists, because it will drop the existing tables."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_create_db_structure.ipynb.

# %% auto 0
__all__ = ['init_db', 'create_tables', 'add_clmn_to_table', 'drop_clmn_from_table']

# %% ../nbs/00_create_db_structure.ipynb 3
from pathlib import Path
from typing import Optional
from fastcore.test import *
from fasthtml.common import *

from .helpers import get_project_root

# %% ../nbs/00_create_db_structure.ipynb 5
def init_db(data_dir: Path = None):
    # TODO: Add to logging
    """Initialize the database connection
    Args:
        data_dir: Optional path to data directory. If None, uses project's data dir
    """
    if data_dir is None:
        data_dir = get_project_root() / 'data'
    data_dir.mkdir(exist_ok=True)
    return database(data_dir / 'game_bindings.db')

# %% ../nbs/00_create_db_structure.ipynb 10
def create_tables(db: database, # Database connection
                  overwrite_existing: bool = False # Remove all existing data in database
                  ):
    """Create all required database tables.
    """
    # TODO: Create dataclasses to create table structure
    if overwrite_existing:
        replace=True
        transform=False
    else:
        replace=False
        transform=True
    
    tables = ['categories', 'actions', 'games', 'game_keys', 'modifiers', 'bindings']
    
    # Drop tables if they exist
    for table in tables:
        if table in db.t:
            db.t[table].drop()
    
    # Create categories table
    db.t.categories.create(
        id=int,
        name=str,
        description=str,
        pk='id',
        not_null=['name'],
        transform=transform,
        replace=replace
    )
    
    # Create actions table
    db.t.actions.create(
        id=int,
        name=str,
        description=str,
        category_id=int,
        pk='id',
        not_null=['name', 'category_id'],
        transform=transform,
        replace=replace
    )
    
    # Create games table
    db.t.games.create(
        id=int,
        name=str,
        game_type=str,
        image=bytes,
        pk='id',
        not_null=['name'],
        transform=transform,
        replace=replace
    )
    
    # Create game_keys table
    db.t.game_keys.create(
        id=int,
        name=str,
        pk='id',
        not_null=['name'],
        transform=transform,
        replace=replace
    )
    
    # Create modifiers table
    db.t.modifiers.create(
        id=int,
        name=str,
        pk='id',
        not_null=['name'],
        transform=transform,
        replace=replace
    )
    
    # Create bindings table
    db.t.bindings.create(
        id=int,
        game_id=int,
        action_id=int,
        key_id=int,
        modifier_id=int,
        description=str,
        sort_order=int,
        pk='id',
        not_null=['game_id', 'action_id', 'key_id', 'modifier_id'],
        transform=transform,
        replace=replace
    )


# %% ../nbs/00_create_db_structure.ipynb 17
def add_clmn_to_table(db, table, column, col_type, **kwargs):
    """Add a new column to an existing table"""
    if column in db.t[table].c:
        print(f"Column {column} already exists in table {table}")
    else:
        return db.t[table].add_column(column, col_type, **kwargs)

# %% ../nbs/00_create_db_structure.ipynb 22
def drop_clmn_from_table(db, table, column):
    """Drop a column from an existing table"""
    if column not in db.t[table].c:
        print(f"Column {column} does not exist in table {table}")
    else:
        return db.t[table].drop_column(column)
