# gui/app.py
# from fasthtml_hf import setup_hf_backup
from fasthtml.common import *
from monsterui.all import *
from base64 import b64encode

from monsterui.franken import Uk_select
from keybindings_fps.create_db_structure import init_db
from keybindings_fps.manipulate_db_contents import *
from keybindings_fps.helpers import *
from keybindings_fps.gui_binding_tables import *

app, rt = fast_app(hdrs=(Theme.slate.headers(), SortableJS('.sortable')), default_hdrs=True, live=True)
db = init_db()

print(db.conn.filename)

def create_edit_screen(id: int):
    print(f"Editing binding {id}")
    binding = next(db.t.bindings.rows_where("id = ?", [id]))
    
    # Get action with error handling
    try:
        action = next(db.t.actions.rows_where("id = ?", [binding['action_id']]))
        action_name = action['name']
    except StopIteration:
        action_name = f"Unknown Action (ID: {binding['action_id']})"
        print(f"Warning: Action ID {binding['action_id']} not found for binding {id}")
    
    # Get default binding with error handling
    try:
        default_binding = next(db.t.bindings.rows_where(
            "game_id = ? AND action_id = ?", 
            [1, binding['action_id']] # game_id is always 1 for default
        ))
    except StopIteration:
        # Create a dummy default binding if none exists
        default_binding = {'key_id': 0, 'modifier_id': 0}
        print(f"Warning: No default binding found for action ID {binding['action_id']}")

    keys = db.t.game_keys()
    modifiers = db.t.modifiers()
    
    # If binding has a key_id that doesn't exist, mark it as invalid but still allow editing
    has_invalid_key = True
    has_invalid_modifier = True
    
    # Find key index with error handling
    try:
        key_idx = next(i for i, k in enumerate(keys) if k['id']==binding['key_id'])
        has_invalid_key = False
    except StopIteration:
        # Key not found, set to first key as fallback
        key_idx = 0
        print(f"Warning: Key ID {binding['key_id']} not found for binding {id}")
        
    # Find modifier index with error handling
    try:
        mod_idx = next(i for i, k in enumerate(modifiers) if k['id']==binding['modifier_id'])
        has_invalid_modifier = False
    except StopIteration:
        # Modifier not found, set to first modifier as fallback
        mod_idx = 0
        print(f"Warning: Modifier ID {binding['modifier_id']} not found for binding {id}")

    # Get default key and modifier with error handling
    try:
        default_key = next(db.t.game_keys.rows_where("id = ?", [default_binding['key_id']]))
    except StopIteration:
        # Default key not found
        default_key = {"name": "Unknown"}
        print(f"Warning: Default key ID {default_binding['key_id']} not found")
        
    try:
        default_mod = next(db.t.modifiers.rows_where("id = ?", [default_binding['modifier_id']]))
    except StopIteration:
        # Default modifier not found
        default_mod = {"name": "Unknown"}
        print(f"Warning: Default modifier ID {default_binding['modifier_id']} not found")
        
    # Get current description or set default
    description = binding.get('description', '')
    
    # Create warning message if there are invalid values
    warning_message = None
    if has_invalid_key or has_invalid_modifier:
        warning_parts = []
        if has_invalid_key:
            warning_parts.append(f"invalid key ID ({binding['key_id']})")
        if has_invalid_modifier:
            warning_parts.append(f"invalid modifier ID ({binding['modifier_id']})")
        warning_text = " and ".join(warning_parts)
        warning_message = Div(
            f"⚠️ This binding has {warning_text}. Please select valid values and save to fix.",
            cls="uk-alert uk-alert-warning"
        )
    
    return Div(
        DivCentered(
            H3(f"Edit Binding {action_name}", cls=TextT.lg)),
        warning_message if warning_message else None,
        Form(Grid(
                Div(  # Left column - edit controls
                    LabelSelect(
                        *[Option(k['name'], value=k['id'], selected=(i==key_idx)) for i, k in enumerate(keys)],
                        name="key_id",
                        label="Key"
                    ),
                    LabelSelect(
                        *[Option(m['name'], value=m['id'], selected=(i==mod_idx)) for i, m in enumerate(modifiers)],
                        name="modifier_id",
                        label="Modifier"
                    ),
                    LabelInput("Description of action for game", name="description", value=description)
                ),
                Div(  # Right column - default values
                    H3("Default Values", cls=TextT.muted),
                    P(f"Key: {default_key['name']}", cls=TextT.muted),
                    P(f"Modifier: {default_mod['name']}", cls=TextT.muted),
                    cls="uk-text-right"
                ),
                cls="grid-cols-2 gap-4"
            ),
            Button("Save", 
                type="submit",
                cls=ButtonT.primary,
                hx_post=f"/binding/{id}/update",
                hx_target="#bindings-table",
                uk_toggle="target: #edit-modal")  # Close modal after save
            ),
        )

@rt('/')
def get():
    def image_or_placeholder(image_data):
        if image_data:
            b64_image = b64encode(image_data).decode('utf-8')
            return Img(src=f"data:image/jpeg;base64,{b64_image}",
                       cls=(TextT.muted, TextT.italic, BackgroundT.muted))
        return Div("No image", cls=(TextT.muted, TextT.italic, BackgroundT.muted))
    
    # Game grid
    games = db.t.games.rows_where("name != ? ORDER BY name", ["default"])  # Exclude default template
    game_grid = Grid(
        *[A(Card(
            CardHeader(H3(game['name']), cls="text-primary"),
            CardBody(
                image_or_placeholder(game['image']),
                P(f"Type: {game['game_type']}", cls=(TextT.muted))
            ),
            cls=CardT.hover  # Makes whole card clickable
        ), href=f"/game/{game['id']}") for game in games],
        id="games-grid"
    )

    return base_layout(game_grid)

@rt('/add_game')
def get():
    game_type_options = ['tactical', 'dumb']

    form = Form(
        H2("Add New Game", cls=("bg-primary text-primary-content", TextT.center)),
        LabelInput(
            "Game Name",
            name="name",
            cls="text-primary"
            ),
        Select(
            map(Option, game_type_options),
            label="Game Type",
            name="game_type"),
        LabelInput(
            "Image URL",
            name="image_url",
            cls="text-primary"
            ),
        Button("Add Game", cls=ButtonT.primary),
        hx_post="/add_game",
        hx_target="#content-area",
        hx_swap="innerHTML"
    )
    
    return base_layout(form)

@rt('/add_game')
def post(name: str, game_type: str, image_url: str = ""):
    try:
        upsert_game(db, name, game_type, image_url)
        copy_default_bindings(db, name)
        return "Game added successfully with default bindings!"
    except Exception as e:
        return Div(f"Error: {str(e)}", cls=AlertT.error)

@rt('/edit_actions')
def get():
    """Show page for editing an action"""
    return base_layout(create_actions_table(db))

@rt('/add_action')
def get():
    """Show page for adding a new action"""
    # Get existing categories for the dropdown
    categories = [c['name'] for c in db.t.categories()]
    
    form = Form(
        H2("Add New Action", cls=("bg-primary text-primary-content", TextT.center)),
        LabelInput("Action Name", 
                  name="name",
                  placeholder="Enter the name of the action (e.g., jump, crouch, reload)",
                  cls="text-primary"
                  ),
        LabelSelect(
            *[Option(c) for c in categories],
            name="category",
            label="Categories",
            cls="text-primary"
        ),
        LabelSelect(
            *[Option(k['name'], value=k['name']) for k in db.t.game_keys()],
            label="Default Key",
            name="default_keybinding",
        ),
        LabelSelect(
            *[Option(m['name'], value=m['name']) for m in db.t.modifiers()],
            label="Default Modifier",
            
            name="default_modifier",
        ),
        Button("Add Action", cls=ButtonT.primary),
        hx_post="/add_action",
        hx_target="#content-area"
    )
    
    return base_layout(form)

@rt('/add_action')
def post(name: str, category: str = "", default_keybinding: str = "", default_modifier: str = ""):
    """Add a new action"""
    print("Adding action", name, category, default_keybinding, default_modifier)
    try:
        if not category:
            raise ValueError("Please select an existing category or create a new one")
            
        if not name:
            raise ValueError("Please enter an action name")
            
        add_new_action(db, name, category, default_keybinding, default_modifier)
        return Div(
            Div("Action added successfully!"), 
            Button("Back to Home",
                   hx_get="/",
                   hx_target="#base-layout",
                   cls=ButtonT.secondary
            ),
        )
    except Exception as e:
        return Div(f"Error: {str(e)}", cls=AlertT.error)
    
@rt('/settings')
def get():
    return Container(nav(), ex_theme_switcher())

@rt('/game/{game_id}')
def get(game_id: int):

    bindings = db.t.bindings.rows_where("game_id = ?", [game_id])
    game = db.t.games[game_id]
    
    return Div(nav(), Titled(
        f"Key Bindings - {game['name']}",
        Container(
            DivRAligned(
                Button("Copy Default Bindings", 
                    hx_post=f"/game/{game_id}/copy_defaults",
                    hx_target="#bindings-table",
                    cls=(ButtonT.secondary)),
                Button("Add Binding", 
                    hx_get=f"/game/{game_id}/add_binding",
                    hx_target="#game-page-buttons",
                    cls=(ButtonT.secondary)),
                Button("Print layout",
                    hx_get=f"/game/{game_id}/print_layout",
                    hx_target="#game-page",
                    cls=(ButtonT.secondary)),
                Button("Delete game",
                    hx_delete=f"/game/{game_id}/delete",
                    hx_target="#game-page",
                    cls=(ButtonT.destructive)),
                cls="space-x-4",
                id="game-page-buttons"
            ),
            Div(create_bindings_table(db, game_id), id="bindings-table"),
            )
        ),
        id="game-page"
    )

@rt('/game/{game_id}/add_binding')
def get(game_id: int):
    """Show page for adding a new binding"""
    game = db.t.games[game_id]
    actions = db.t.actions.rows
    keys = db.t.game_keys()
    modifiers = db.t.modifiers()
    
    form = Form(
        H2(f"Add New Binding for {game['name']}"),
        LabelSelect(
            *[Option(a['name'], value=a['id']) for a in actions],
            name="action_id",
            label="Action"
        ),
        LabelSelect(
            *[Option(k['name'], value=k['id']) for k in keys],
            name="key_id",
            label="Key"
        ),
        LabelSelect(
            *[Option(m['name'], value=m['id']) for m in modifiers],
            name="modifier_id",
            label="Modifier"
        ),
        Button("Add Binding", cls=ButtonT.primary),
        hx_post=f"/game/{game_id}/add_binding",
        hx_target="#content-area"
    )
    
    return base_layout(
        (DivRAligned(
            A("Back to Game", 
              href=f"/game/{game_id}",
              cls=(ButtonT.secondary, 'pl-3', 'mb-4')),
            cls="space-x-4"
        ),
        form)
    )

@rt('/game/{game_id}/add_binding')
def post(game_id: int, action_id: int, key_id: int, modifier_id: int):
    """Add a new binding"""
    try:
        # Validate that a key has been selected
        if not key_id:
            return Div("Please choose a key to bind to this action", cls=AlertT.warning)
            
        # Add the binding
        db.t.bindings.insert(dict(
            game_id=game_id,
            action_id=action_id,
            key_id=key_id,
            modifier_id=modifier_id
        ))
        print("Binding added successfully!")
        
        return Div(P("Binding added successfully!"), 
                   A("Back to Game",
                     href=f"/game/{game_id}",
                     cls=(ButtonT.primary, 'pl-3'))) 
    except Exception as e:
        return Div(f"Error: {str(e)}", cls=AlertT.error)

@rt('/game/{game_id}/copy_defaults')
def post(game_id: int):
    game = db.t.games[game_id]
    copy_default_bindings(db,game['name'])
    
    return create_bindings_table(db, game_id=game_id)

@rt('/game/{game_id}/delete')
def delete(game_id: int):
    del_message = delete_game(db, game_id)
    
    return Container(
        P(del_message),
        Button(
            "Back to Games",
            hx_get="/",
            cls=ButtonT.secondary
        )
    )

@rt('/game/{game_id}/print_layout')
def get(game_id: int):
    game = db.t.games[game_id]
    bindings = db.t.bindings.rows_where("game_id = ?", [game_id])

    nav = NavBar(
        brand=A(H4(game['name']), href=f"/game/{game_id}")
        )

    return Container(
        nav,
        create_bindings_table_print(db, game_id)
    )
    
@rt("/game/{game_id}/reorder_bindings/{action_category_id}")
def post(binding_id: list[int], action_category_id: int, game_id: int):
    for i, binding_id_ in enumerate(binding_id):
        db.t.bindings.update(
            {'sort_order': i * 100},
            binding_id_)
    
    return create_binding_table_category(db, game_id, action_category_id)

@rt('/binding/{id}/edit')
def get(id: int):
    return Div(
        create_edit_screen(id),
    )

@rt('/binding/{id}/update')
def post(id: int, key_id: int, modifier_id: int, description: str):
    # First get the current binding to get the game_id
    current_binding = next(db.t.bindings.rows_where("id = ?", [id]))
    game_id = current_binding['game_id']
    
    # Validate that a key has been selected
    if not key_id:
        return Div("Please choose a key to bind to this action", cls=AlertT.warning)
    
    # Update the binding with both key and modifier
    binding = db.t.bindings.update(dict(
        id=id,
        key_id=key_id,
        modifier_id=modifier_id,
        description=description
    ))
    
    # Get all bindings for the game and return updated table
    bindings = db.t.bindings.rows_where("game_id = ?", [game_id])
    return create_bindings_table(db, game_id)

@rt('/binding/{id}/delete')
def delete(id: int):
    # First get the current binding to get the game_id
    current_binding = next(db.t.bindings.rows_where("id = ?", [id]))
    game_id = current_binding['game_id']
    action_id = current_binding['action_id']
    action_category_id = next(db.t.actions.rows_where("id = ?", [action_id]))['category_id']
    
    # Delete the binding
    db.t.bindings.delete_where("id = ?", [id])
    
    return create_binding_table_category(db, game_id, action_category_id)

@rt('/binding/{id}/cancel')
def get(id: int):
    # Just return the table without changes
    binding = next(db.t.bindings.rows_where("id = ?", [id]))
    game_id = binding['game_id']
    bindings = db.t.bindings.rows_where("game_id = ?", [game_id])
    return create_bindings_table(db, game_id)

# setup_hf_backup(ap)

serve()