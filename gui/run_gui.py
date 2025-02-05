# gui/app.py
from fasthtml.common import *
from monsterui.all import *
from base64 import b64encode
from keybindings_fps.create_db import init_db
from keybindings_fps.manipulate_db import *

app, rt = fast_app(hdrs=Theme.blue.headers(), default_hdrs=True, live=True)
db = init_db()

# Header with navigation
def nav():
    nav = NavBarContainer(
        NavBarLSide(
            NavBarNav(
                Li(A("Games", href="/"))
            )
        ),
        NavBarRSide(
            NavBarNav(
                Li(A("Add Game", href="/add_game")),
                Li(A("Add new action", href="/add_action")),
                Li(A("Settings", href="/settings")),
            )
        )
    )
    return nav

def ex_theme_switcher():
    from fasthtml.components import Uk_theme_switcher
    return Uk_theme_switcher()

def create_bindings_table(bindings, game_id):
    """Helper function to create the bindings table with category grouping"""
    # Get all categories and create lookup dicts
    categories = {c['id']: c['name'] for c in db.t.categories()}
    actions = {a['id']: (a['name'], a['category_id']) for a in db.t.actions()}

    game = db.t.games[game_id]
    differences = compare_with_default(game['name'])
    
    # Group bindings by category
    grouped_bindings = {}
    for b in bindings:
        action_name, category_id = actions[b['action_id']]
        category = categories[category_id]
        if category not in grouped_bindings:
            grouped_bindings[category] = []
        grouped_bindings[category].append(b)
    
    # Create table with category groups
    rows = [Tr(
        Th("Action"),
        Th("Key"),
        Th("Modifier"),
        Th("Actions")
    )]
    
    for category, cat_bindings in grouped_bindings.items():
        # Add category header
        rows.append(Tr(
            Th(P(category, colspan=4, cls=(TextT.lg, TextT.bold, TextT.primary, TextT.center)))
        ))
        
        # Add bindings for this category
        for b in cat_bindings:
            is_different = b['action_id'] in differences
            text_style = (TextT.bold, TextT.danger) if is_different else TextT.default
            b_id = b['id']

            rows.append(Tr(
                Td(actions[b['action_id']][0]),
                Td(next(db.t.game_keys.rows_where("id = ?", [b['key_id']]))['name'],
                   cls=text_style),
                Td(next(db.t.modifiers.rows_where("id = ?", [b['modifier_id']]))['name'],
                   cls=text_style),
                Td(Button("Edit", cls=ButtonT.secondary,
                          uk_toggle="target: #edit-modal"),
                   Button("Delete", 
                        hx_delete=f"/binding/{b['id']}",
                        cls=ButtonT.danger),
                    ModalContainer(
                        create_edit_modal(b_id),
                        id="edit-modal"),
                    cls="space-x-2"
                        
                )
            ))
    
    return Table(*rows, cls=(TableT.hover, TableT.sm, TableT.striped))

def create_bindings_table_print(bindings, game_id):
    """Helper function to create the bindings table with category grouping"""
    # Get all categories and create lookup dicts
    categories = {c['id']: c['name'] for c in db.t.categories()}
    actions = {a['id']: (a['name'], a['category_id']) for a in db.t.actions()}

    game = db.t.games[game_id]
    differences = compare_with_default(game['name'])

    def non_tap_modifier(modifier):
        if modifier != "tap":
            return f"   ({modifier})"
        return ""
    
    # Group bindings by category
    grouped_bindings = {}
    for b in bindings:
        action_name, category_id = actions[b['action_id']]
        category = categories[category_id]
        if category not in grouped_bindings:
            grouped_bindings[category] = []
        grouped_bindings[category].append(b)
    
    # Create table with category groups
    rows = []
    
    for category, cat_bindings in grouped_bindings.items():
        # Add category header
        rows.append(Tr(
            Th(P(category, colspan=3, cls=(TextT.lg, TextT.bold, TextT.primary, TextT.center)))
        ))
        
        # Add bindings for this category
        for b in cat_bindings:
            is_different = b['action_id'] in differences
            text_style = (TextT.bold, TextT.danger) if is_different else TextT.default
            b_id = b['id']

            rows.append(Tr(
                Td(actions[b['action_id']][0]),
                Td(next(db.t.game_keys.rows_where("id = ?", [b['key_id']]))['name'], 
                   P(non_tap_modifier(next(db.t.modifiers.rows_where("id = ?", [b['modifier_id']]))['name']), cls=TextT.italic),
                   cls=text_style),
            ))
    
    split_len = len(rows)//3
    
    return Grid(Table(*rows[:split_len], cls=(TableT.sm, TableT.divider)), Table(*rows[split_len:2*split_len], cls=(TableT.sm, TableT.divider)), Table(*rows[2*split_len:], cls=(TableT.sm, TableT.divider)), cols=3, cls='gap-12')

def create_edit_modal(id: int):
    binding = next(db.t.bindings.rows_where("id = ?", [id]))
    default_binding = next(db.t.bindings.rows_where(
        "game_id = ? AND action_id = ?", 
        [1, binding['action_id']] # game_id is always 1 for default
    ))

    action = next(db.t.actions.rows_where("id = ?", [binding['action_id']]))

    keys = db.t.game_keys()
    modifiers = db.t.modifiers()

    key_idx = next(i for i, k in enumerate(keys) if k['id']==binding['key_id'])
    mod_idx = next(i for i, k in enumerate(modifiers) if k['id']==binding['modifier_id'])

    default_key = next(db.t.game_keys.rows_where("id = ?", [default_binding['key_id']]))
    default_mod = next(db.t.modifiers.rows_where("id = ?", [default_binding['modifier_id']]))
    
    return ModalDialog(
        ModalHeader(
            ModalTitle(action['name'])
        ),
        Form(
            ModalBody(
                Grid(
                    Div(  # Left column - edit controls
                        LabelSelect(
                            *[Option(k['name'], value=k['id']) for k in keys],
                            name="key_id",
                            label="Key",
                            selected_idx=key_idx
                        ),
                        LabelSelect(
                            *[Option(m['name'], value=m['id']) for m in modifiers],
                            name="modifier_id",
                            label="Modifier",
                            selected_idx=mod_idx
                        )
                    ),
                    Div(  # Right column - default values
                        H3("Default Values", cls=TextT.muted),
                        P(f"Key: {default_key['name']}", cls=TextT.muted),
                        P(f"Modifier: {default_mod['name']}", cls=TextT.muted),
                        cls="uk-text-right"
                    ),
                    cls="grid-cols-2 gap-4"
                )
            ),
            ModalFooter(
                ModalCloseButton("Cancel", cls=ButtonT.secondary),
                Button("Save", 
                    type="submit",
                    cls=ButtonT.primary,
                    hx_post=f"/binding/{id}/update",
                    hx_target="#bindings-table",
                    uk_toggle="target: #edit-modal")  # Close modal after save
            ),
        ))

@rt('/')
def get():
    def image_or_placeholder(image_data):
        if image_data:
            b64_image = b64encode(image_data).decode('utf-8')
            return Img(src=f"data:image/jpeg;base64,{b64_image}",
                       cls=(TextT.muted, TextT.italic, BackgroundT.muted))
        return Div("No image", cls=(TextT.muted, TextT.italic, BackgroundT.muted))

    # Game grid
    games = db.t.games.rows_where("name != ?", ["default"])  # Exclude default template
    game_grid = Grid(
        *[A(Card(
            CardHeader(H3(game['name'])),
            CardBody(
                image_or_placeholder(game['image']),
                P(f"Type: {game['game_type']}", cls=(TextT.muted))
            ),
            cls=CardT.hover  # Makes whole card clickable
        ), href=f"/game/{game['id']}") for game in games]
    )
    
    return Container(nav(), game_grid)

@rt('/add_game')
def get():
    form = Form(
        H2("Add New Game"),
        LabelInput("Game Name", id="name"),
        LabelSelect(*Options('tactical', 'dumb'),
            label="Game Type", id="game_type"),
        LabelInput("Image URL", id="image_url"),
        Button("Add Game", cls=ButtonT.primary),
        hx_post="/add_game",
        hx_target="#result",
        hx_swap="innerHTML"
    )
    
    return Container(
        nav(),
        form,
        P("Wacht op input",id="result")  # For showing result/errors
    )

@rt('/settings')
def get():
    return Container(nav(), ex_theme_switcher())

@rt('/add_game')
def post(name: str, game_type: str, image_url: str = None):
    try:
        game = upsert_game(name, game_type, image_url)
        copy_default_bindings(name)
        return "Game added successfully with default bindings!"
    except Exception as e:
        return Div(f"Error: {str(e)}", cls=AlertT.error)

@rt('/game/{id}')
def get(id: int):
    game = db.t.games[id]
    bindings = db.t.bindings.rows_where("game_id = ?", [id])
    
    return Titled(
        f"Key Bindings - {game['name']}",
        Container(
            DivRAligned(
                A("Back to Games",
                    href="/",
                    cls=(ButtonT.secondary, PaddingT.xl)),
                Button("Copy Default Bindings", 
                    hx_post=f"/game/{id}/copy_defaults",
                    hx_target="#bindings-table",
                    cls=(ButtonT.secondary, PaddingT.xl)),
                A("Add Binding", 
                    href=f"/game/{id}/add_binding",
                    cls=(ButtonT.primary, PaddingT.xl)),
                A("Print layout",
                    href=f"/game/{id}/print_layout",
                    cls=(ButtonT.secondary, PaddingT.xl)),
                cls="space-x-4"
            ),
            Div(create_bindings_table(bindings, id), id="bindings-table"),
            ModalContainer(
                ModalDialog(id="edit-modal-content"),
                id="edit-modal"
            )
        )
    )

@rt('/game/{id}/print_layout')
def get(id: int):
    game = db.t.games[id]
    bindings = db.t.bindings.rows_where("game_id = ?", [id])

    nav = NavBarContainer(
        NavBarLSide(
            NavBarNav(
                Li(A("Games", href="/"))
            )
        ),
        NavBarRSide(
            A(H4(game['name']), href=f"/game/{id}"),
            )
        )

    return Container(
        nav,
        create_bindings_table_print(bindings, id)
    )
    
    # return Titled(H3(f"Key Bindings - {game['name']}", href="/"),
    #     NavBarNavContainer(
    #         NavBarRSide(
    #             NavBarNav(
    #                 Li(A("Back to Games",
    #                     href="/",
    #                     cls=(ButtonT.secondary, PaddingT.xs))),
    #             ),
    #         ),
    #     ),
    #     Div(create_bindings_table_print(bindings, id), id="bindings-table_print"),
    #     )

@rt('/binding/{id}/update')
def post(id: int, key_id: int, modifier_id: int):
    # First get the current binding to get the game_id
    current_binding = next(db.t.bindings.rows_where("id = ?", [id]))
    game_id = current_binding['game_id']
    
    # Update the binding with both key and modifier
    binding = db.t.bindings.update(dict(
        id=id,
        key_id=key_id,
        modifier_id=modifier_id
    ))
    
    # Get all bindings for the game and return updated table
    bindings = db.t.bindings.rows_where("game_id = ?", [game_id])
    return create_bindings_table(bindings, game_id)

@rt('/binding/{id}/cancel')
def get(id: int):
    # Just return the table without changes
    binding = next(db.t.bindings.rows_where("id = ?", [id]))
    game_id = binding['game_id']
    bindings = db.t.bindings.rows_where("game_id = ?", [game_id])
    return create_bindings_table(bindings, game_id)

@rt('/game/{id}/copy_defaults')
def post(id: int):
    game = db.t.games[id]
    copy_default_bindings(game['name'])
    
    # Return just the new table
    bindings = db.t.bindings.rows_where("game_id = ?", [id])
    return create_bindings_table(game_id=id, bindings=bindings)

@rt('/game/{id}/add_binding')
def get(id: int):
    """Show page for adding a new binding"""
    game = db.t.games[id]
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
        hx_post=f"/game/{id}/add_binding",
        hx_target="#result"
    )
    
    return Titled("Add Binding", Container(
        nav,  # Reuse the navigation
        DivRAligned(
            A("Back to Game", 
              href=f"/game/{id}",
              cls=(ButtonT.secondary, PaddingT.xl)),
            cls="space-x-4"
        ),
        form,
        Div(id="result")  # For showing result/errors
    ))

@rt('/game/{id}/add_binding')
def post(id: int, action_id: int, key_id: int, modifier_id: int):
    """Add a new binding"""
    try:
        # Add the binding
        db.t.bindings.insert(dict(
            game_id=id,
            action_id=action_id,
            key_id=key_id,
            modifier_id=modifier_id
        ))
        
        return Div("Binding added successfully!", 
                  A("Back to Game", href=f"/game/{id}"), 
                  cls=AlertT.success)
    except Exception as e:
        return Div(f"Error: {str(e)}", cls=AlertT.error)

@rt('/add_action')
def get():
    """Show page for adding a new action"""
    # Get existing categories for the dropdown
    categories = [c['name'] for c in db.t.categories()]
    
    form = Form(
        H2("Add New Action"),
        LabelInput("Action Name", 
                  name="name",
                  placeholder="Enter the name of the action (e.g., jump, crouch, reload)"),
        LabelSelect(
            *[Option(c) for c in categories],
            name="category",
            label="Categories",
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
        hx_target="#result"
    )
    
    return Titled("Add Action", Container(
        nav,  # Reuse the navigation
        form,
        Div(id="result")  # For showing result/errors
    ))

@rt('/add_action')
def post(name: str, existing_category: str = "", new_category: str = "", default_keybinding: str = "", default_modifier: str = ""):
    """Add a new action"""
    try:
        # Use existing category if selected, otherwise use new category
        category = existing_category if existing_category else new_category
        if not category:
            raise ValueError("Please select an existing category or create a new one")
            
        if not name:
            raise ValueError("Please enter an action name")
            
        add_new_action(name, category, default_keybinding, default_modifier)
        return Div("Action added successfully!", 
                  A("Back to Home", href="/"), 
                  cls=AlertT.success)
    except Exception as e:
        return Div(f"Error: {str(e)}", cls=AlertT.error)
    
serve()