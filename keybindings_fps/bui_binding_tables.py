"""This module contains several functions that are used in creating the FastHTML gui binding tables."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/04_gui_binding_tables.ipynb.

# %% auto 0
__all__ = ['create_binding_table_category', 'create_bindings_table_print_bup', 'create_bindings_table_print']

# %% ../nbs/04_gui_binding_tables.ipynb 3
from fasthtml.common import *
from monsterui.all import *
from fastcore.test import *

from .create_db_structure import *
from .manipulate_db_contents import *
from .helpers import *

# %% ../nbs/04_gui_binding_tables.ipynb 4
def create_binding_table_category(db, game_id, action_category_id, print_layout=False):
    print("Creating binding table for category", action_category_id)
    print("Game ID:", game_id)

    """Helper function to create the bindings table for a given action category"""
    # Get all categories and create lookup dicts
    cat_actions = db.t.actions.rows_where("category_id = ?", [action_category_id])
    action_ids = L(cat_actions).attrgot("id")

    cat_name = L(db.t.categories.rows_where("id = ?", [action_category_id])).attrgot('name')[0]

    # Create table with category groups
    table_heading = Tr(
        Th("  ", style="width:10px;"),
        Th("Action"),
        Th("Key"),
        Th("Modifier"),
        Th("Game native description"),
        Th("Actions")
    )

    if print_layout:
        table_heading = Tr(
            Th("Action"),
            Th("Key (modifier)")
        )

    text_style = TextT.justify

    rows = []
       
    # Add bindings for this category
    action_ids_str = ','.join(str(id) for id in action_ids) 
    # Convert action_ids to string. Converting to a tuple creates a trailing comma with only one element. Which gives invalid SQL syntax.
    where_string = f"game_id = {game_id} AND action_id IN ({action_ids_str}) ORDER BY sort_order"

    for b in db.t.bindings.rows_where(where_string):
        if not print_layout:
            rows.append(Tr(
                Td("⋮⋮", style="width: 10px;"),
                Td(next(db.t.actions.rows_where("id = ?", [b['action_id']]))['name'],
                    cls=text_style),
                Td(next(db.t.game_keys.rows_where("id = ?", [b['key_id']]))['name'],
                    cls=text_style),
                Td(next(db.t.modifiers.rows_where("id = ?", [b['modifier_id']]))['name'],
                    cls=text_style),
                Td(b['description'],
                    cls=text_style),
                Td(Button("Edit", 
                        hx_get=f"/binding/{b['id']}/edit",
                        hx_target="#bindings-table",
                        cls=ButtonT.secondary),
                    Button("Delete", 
                        hx_delete=f"/binding/{b['id']}/delete",
                        hx_target="#bindings-table",
                        cls=ButtonT.danger),
                    cls="space-x-2"),
                Hidden(name="binding_id", value=b['id'])
                )
            )
        if print_layout:
            rows.append(Tr(
                Td(next(db.t.actions.rows_where("id = ?", [b['action_id']]))['name'],
                    cls=text_style),
                Td(next(db.t.game_keys.rows_where("id = ?", [b['key_id']]))['name'],
                    cls=text_style),
                Td(next(db.t.modifiers.rows_where("id = ?", [b['modifier_id']]))['name'],
                    cls=text_style),
                Hidden(name="binding_id", value=b['id'])
                )
            )
    
    return Div(
        P(cat_name, cls=(TextT.lg, TextT.bold, TextT.primary, TextT.center)),
        Form(
            Table(Thead(table_heading),
                  Tbody(*rows,
                        cls='sortable',
                        id=f"sortable-tbody-{action_category_id}"),
                cls=(TableT.hover, TableT.sm, TableT.striped)
            ),
            hx_post=f"/game/{game_id}/reorder_bindings/{action_category_id}",
            hx_trigger="end from:tbody",
            hx_target=f"#form-category-{action_category_id}",
        ),
        id=f"form-category-{action_category_id}"
    )

# %% ../nbs/04_gui_binding_tables.ipynb 5
def create_bindings_table_print_bup(db, game_id):
    """Helper function to create the bindings table with category grouping"""

    def non_tap_modifier(modifier):
        if modifier != "tap":
            return f"   ({modifier})"
        return ""
    
    # Create table with category groups
    def create_bindings_per_category(cat_bindings, category, actions_dict, print=True):
        rows = []

        rows.append(Tr(Th(P(category, cls=(TextT.lg, TextT.bold, TextT.primary, TextT.center)))))

        for b in cat_bindings:
            is_different = b['action_id'] in differences
            text_style = (TextT.bold, TextT.danger) if is_different else TextT.default
            b_id = b['id']

            rows.append(Tr(
                Td(actions_dict[b['action_id']][0], cls=text_style),
                Td(next(db.t.game_keys.rows_where("id = ?", [b['key_id']]))['name'], 
                P(non_tap_modifier(next(db.t.modifiers.rows_where("id = ?", [b['modifier_id']]))['name']), cls=TextT.italic),
                cls=text_style),
                Td(b['description'], cls=TextT.muted)
            ))
        return rows

    # Get all categories and create lookup dicts
    categories = {c['id']: c['name'] for c in db.t.categories()}
    actions = {a['id']: (a['name'], a['category_id']) for a in db.t.actions()}

    game = db.t.games[game_id]
    differences = compare_with_default(db, game['name'])
    # Group bindings by category
    grouped_bindings = {}
    for b in bindings:
        action_name, category_id = actions[b['action_id']]
        category = categories[category_id]
        if category not in grouped_bindings:
            grouped_bindings[category] = []
        grouped_bindings[category].append(b)
    
    for category, cat_bindings in grouped_bindings.items():
        rows = create_bindings_per_category(cat_bindings, category, actions)
    
    # return Grid(Table(*rows[:split_len], cls=(TableT.sm, TableT.divider)), Table(*rows[split_len:2*split_len], cls=(TableT.sm, TableT.divider)), Table(*rows[2*split_len:], cls=(TableT.sm, TableT.divider)), cols=3, cls='gap-12')
    return Card(Grid(
        Card(Table(*create_bindings_per_category(grouped_bindings['movement'], 'movement', actions))), 
        Card(Table(*create_bindings_per_category(grouped_bindings['combat'], 'combat', actions))), 
        Card(Table(*create_bindings_per_category(grouped_bindings['interaction'], 'interaction', actions)), 
        Table(*create_bindings_per_category(grouped_bindings['communication'], 'communication', actions)), 
        Table(*create_bindings_per_category(grouped_bindings['menu'], 'menu', actions))), 
        cols=3, cls='gap-12'))

# %% ../nbs/04_gui_binding_tables.ipynb 6
def create_bindings_table_print(db, game_id):
    categories = db.t.categories.rows_where("id IN (SELECT DISTINCT category_id FROM actions)")
    category_ids = L(categories).attrgot('id')
    print(category_ids)
    tables = [create_binding_table_category(db, game_id, cat_id, print_layout=True) for cat_id in category_ids]

    return Card(Grid(
        Card(tables[0]),
        Card(tables[1]),
        Card(*tables[2:]),
        cols=3, cls='gap-12'))
