# gui/app.py
from fasthtml.common import *
from monsterui.all import *
from base64 import b64encode
from keybindings_fps.create_db_structure import init_db
from keybindings_fps.manipulate_db_contents import *
from keybindings_fps.helpers import *

app, rt = fast_app(hdrs=(Theme.blue.headers(), SortableJS('.sortable')), default_hdrs=True, live=True)
db = init_db()

print(db.conn.filename)

def create_binding_table_category(db, game_id, action_category_id):
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

    text_style = TextT.justify

    rows = []
       
    # Add bindings for this category
    action_ids_str = ','.join(str(id) for id in action_ids) 
    # Convert action_ids to string. Converting to a tuple creates a trailing comma with only one element. Which gives invalid SQL syntax.
    where_string = f"game_id = {game_id} AND action_id IN ({action_ids_str}) ORDER BY sort_order"

    for b in db.t.bindings.rows_where(where_string):

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

def create_bindings_table(db, game_id):
    """Create tables for all action categories and stack them vertically"""
    # Get all unique category IDs
    categories = db.t.categories.rows_where("id IN (SELECT DISTINCT category_id FROM actions)")
    category_ids = L(categories).attrgot('id')
    
    # Create a table for each category
    tables = [create_binding_table_category(db, game_id, cat_id) for cat_id in category_ids]
    
    # Stack tables in a container div
    return Div(*tables, id="all-bindings-tables")

def create_bindings_table_print(bindings, game_id):
    """Helper function to create the bindings table with category grouping"""

    def non_tap_modifier(modifier):
        if modifier != "tap":
            return f"   ({modifier})"
        return ""
    
    # Create table with category groups
    def create_bindings_per_category(cat_bindings, category, actions_dict):
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
    differences = compare_with_default(game['name'])
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

def create_edit_screen(id: int):
    print(f"Editing binding {id}")
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
    
    return Div(
        DivCentered(
            H3(f"Edit Binding {action['name']}", cls=TextT.lg)),
        Form(Grid(
                Div(  # Left column - edit controls
                    LabelSelect(
                        *[Option(k['name'], value=k['id']) for k in keys],
                        name="key_id",
                        label="Key",
                        # selected_idx=key_idx
                    ),
                    LabelSelect(
                        *[Option(m['name'], value=m['id']) for m in modifiers],
                        name="modifier_id",
                        label="Modifier",
                        # selected_idx=mod_idx
                    ),
                    LabelInput("Descriptio of action for game", id="description")
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
    form = Form(
        H2("Add New Game", cls=("bg-primary text-primary-content", TextT.center)),
        LabelInput("Game Name", id="name", cls="text-primary"),
        LabelSelect(*Options('tactical', 'dumb'),
            label="Game Type", id="game_type", cls="text-primary"),
        LabelInput("Image URL", id="image_url", cls="text-primary"),
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

@rt('/add_game')
def post(name: str, game_type: str, image_url: str = None):
    try:
        game = upsert_game(db, name, game_type, image_url)
        copy_default_bindings(db, game['name'])
        return "Game added successfully with default bindings!"
    except Exception as e:
        return Div(f"Error: {str(e)}", cls=AlertT.error)

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
                Button("Back to Games",
                    hx_get="/",
                    hx_target="#game-page",
                    hx_swap="outer-html",
                    cls=(ButtonT.secondary, PaddingT.xl, 'mb-4')),
                Button("Copy Default Bindings", 
                    hx_post=f"/game/{game_id}/copy_defaults",
                    hx_target="#bindings-table",
                    cls=(ButtonT.secondary, PaddingT.xl, 'mb-4')),
                A("Add Binding", 
                    href=f"/game/{game_id}/add_binding",
                    cls=(ButtonT.secondary, PaddingT.xl, 'mb-4')),
                A("Print layout",
                    href=f"/game/{game_id}/print_layout",
                    cls=(ButtonT.secondary, PaddingT.xl, 'mb-4')),
                cls="space-x-4"
            ),
            Div(create_bindings_table(db, game_id), id="bindings-table"),
            )
        ),
        id="game-page"
    )

@rt('/game/{game_id}/copy_defaults')
def post(game_id: int):
    game = db.t.games[game_id]
    copy_default_bindings(db,game['name'])
    
    return create_bindings_table(db, game_id=game_id)

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
              cls=(ButtonT.secondary, PaddingT.xl)),
            cls="space-x-4"
        ),
        form)
    )

@rt('/game/{game_id}/add_binding')
def post(game_id: int, action_id: int, key_id: int, modifier_id: int):
    """Add a new binding"""
    try:
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
                     cls=(ButtonT.primary, PaddingT.xl))) 
    except Exception as e:
        return Div(f"Error: {str(e)}", cls=AlertT.error)

@rt('/game/{game_id}/print_layout')
def get(game_id: int):
    game = db.t.games[game_id]
    bindings = db.t.bindings.rows_where("game_id = ?", [game_id])

    nav = NavBarContainer(
        NavBarLSide(
            NavBarNav(
                Li(A("Games", href="/"))
            )
        ),
        NavBarRSide(
            A(H4(game['name']), href=f"/game/{game_id}"),
            )
        )

    return Container(
        nav,
        create_bindings_table_print(bindings, game_id)
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
    
    # Update the binding with both key and modifier
    binding = db.t.bindings.update(dict(
        id=id,
        key_id=key_id,
        modifier_id=modifier_id,
        description=description
    ))
    
    # Get all bindings for the game and return updated table
    bindings = db.t.bindings.rows_where("game_id = ?", [game_id])
    return create_bindings_table(bindings, game_id)

@rt('/binding/{id}/delete')
def delete(id: int):
    # First get the current binding to get the game_id
    current_binding = next(db.t.bindings.rows_where("id = ?", [id]))
    game_id = current_binding['game_id']
    
    # Delete the binding
    db.t.bindings.delete_where("id = ?", [id])
    
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


serve()