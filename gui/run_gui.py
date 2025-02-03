# gui/app.py
from fasthtml.common import *
from monsterui.all import *
from base64 import b64encode
from keybindings_fps.create_db import init_db
from keybindings_fps.manipulate_db import *

app, rt = fast_app(hdrs=Theme.blue.headers(), default_hdrs=True, live=True)
db = init_db()

# Header with navigation
nav = NavBarContainer(
    NavBarLSide(
        NavBarNav(
            Li(A("Games", href="/"))
        )
    ),
    NavBarRSide(
        NavBarNav(
            Li(A("Add Game", href="/add_game")),
            Li(A("Settings", href="/settings")),
        )
    )
)

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
            text_style = TextT.bold if is_different else TextT.default

            rows.append(Tr(
                Td(actions[b['action_id']][0]),
                Td(next(db.t.game_keys.rows_where("id = ?", [b['key_id']]))['name'],
                   hx_get=f"/binding/{b['id']}/edit_key",
                   hx_target="body",
                   hx_swap="beforeend",
                   cls=(text_style, "cursor-pointer")),
                Td(next(db.t.modifiers.rows_where("id = ?", [b['modifier_id']]))['name'],
                   hx_get=f"/binding/{b['id']}/edit_modifier",
                   hx_trigger="click",
                   cls=(text_style, "cursor-pointer")),
                Td(Button("Delete", 
                    hx_delete=f"/binding/{b['id']}",
                    cls=ButtonT.danger))
            ))
    
    return Table(*rows, cls=(TableT.hover, TableT.sm, TableT.striped))

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
    
    return Container(nav, game_grid)

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
        hx_target="#result"
    )
    
    return Container(
        nav,  # Reuse the navigation
        form,
        Div(id="result")  # For showing result/errors
    )

@rt('/settings')
def get():
    return Container(nav, ex_theme_switcher())

@rt('/add_game')
def post(name: str, game_type: str, image_url: str = None):
    try:
        game = upsert_game(name, game_type, image_url)
        copy_default_bindings(name)
        return Div("Game added successfully with default bindings!", 
                  A("View Games", href="/"), 
                  cls=AlertT.success)
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
                Button("Add Binding", 
                    hx_get=f"/game/{id}/add_binding",
                    cls=(ButtonT.primary, PaddingT.xl)),
                cls="space-x-4"
            ),
            Div(id="modal-container", _script="UIkit.modal('#edit-key-modal').show();"),  # Add script trigger
            Div(create_bindings_table(bindings, id), id="bindings-table"),
        )
    )

@rt('/binding/{id}/edit_key')
def get(id: int):
    binding = next(db.t.bindings.rows_where("id = ?", [id]))
    keys = db.t.game_keys()
    selected_idx = next(i for i, k in enumerate(keys) if k['id']==binding['key_id'])
    
    modal = Div(
        ModalContainer(
            ModalDialog(
                ModalHeader(H3("Edit Key Binding")),
                ModalBody(
                    LabelUkSelect(
                        *[Option(k['name'], value=k['id']) for k in keys],
                        name="value",
                        label="Select Key",
                        selected_idx=selected_idx,
                    )
                ),
                ModalFooter(
                    Button("Save", 
                        hx_post=f"/binding/{id}/update_key",
                        hx_target="#bindings-table",
                        cls=ButtonT.primary),
                    ModalCloseButton("Cancel", cls=ButtonT.secondary)
                ),
                id="edit-key-modal"
            )
        ),
        _script="UIkit.modal('#edit-key-modal').show();"
    )
    
    print(f"Generated modal HTML: {modal}")  # Debug print
    return modal

@rt('/binding/{id}/update_key')
def post(id: int, value: int):
    print(f"Updating binding {id} with key {value}")
    # First get the current binding to get the game_id
    current_binding = next(db.t.bindings.rows_where("id = ?", [id]))
    game_id = current_binding['game_id']
    
    # Update the binding
    binding = db.t.bindings.update(dict(
        id=id,
        key_id=value
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
    return create_bindings_table(bindings)

serve()