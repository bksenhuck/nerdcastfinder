"""
Nerdcast Finder - Frontend Dash Application

A minimal search interface for finding podcast episodes using semantic search.
"""
import re
import requests
from dash import Dash, html, dcc, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

# Configuration
BACKEND_URL = "http://localhost:8000/api/search"

# Initialize Dash app with Bootstrap theme
app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        dbc.icons.BOOTSTRAP
    ],
    title="Nerdcast Finder"
)

# Layout
app.layout = html.Div([
    # Store for theme state (dark/light)
    dcc.Store(id="theme-store", data="light", storage_type="local"),
    
    # Main content container with margin-bottom for fixed footer
    dbc.Container(id="main-container", children=[
        # Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H1(
                        "🎙️ Nerdcast Finder",
                        className="text-center my-4 d-inline-block",
                        style={"width": "100%"}
                    ),
                    dbc.Button(
                        html.I(className="bi bi-moon-fill"),
                        id="theme-toggle",
                        color="link",
                        size="lg",
                        style={
                            "position": "absolute",
                            "top": "20px",
                            "right": "20px",
                            "fontSize": "24px"
                        }
                    )
                ], style={"position": "relative"}),
                html.P(
                    "Busque episódios do Nerdcast por tema, assunto ou palavra-chave",
                    id="subtitle",
                    className="text-center text-muted mb-4"
                )
            ])
        ]),
        
        # Search bar
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.Input(
                        id="search-input",
                        placeholder="Busque por um tema, palavra-chave ou assunto...",
                        type="text",
                        className="form-control-lg"
                    ),
                    dbc.Button(
                        "Search",
                        id="search-button",
                        color="primary",
                        className="btn-lg",
                        n_clicks=0
                    )
                ], className="mb-3")
            ], md=8, className="mx-auto")
        ]),
            
        # Search controls
        dbc.Row([
            dbc.Col([
                dbc.Row([
                    # Number of results control
                    dbc.Col([
                        dbc.Card(id="top-k-card", children=[
                            dbc.CardBody([
                                html.Div([
                                    html.Label(
                                        "Número de resultados:",
                                        id="top-k-label",
                                        className="fw-bold d-inline"
                                    ),
                                    html.I(
                                        className="bi bi-question-circle ms-2",
                                        id="tooltip-top-k",
                                        style={"cursor": "pointer"}
                                    ),
                                    dbc.Tooltip(
                                        "Quanto maior, mais resultados serão "
                                        "retornados pela busca.",
                                        target="tooltip-top-k"
                                    )
                                ]),
                                dcc.Slider(
                                    id="top-k-slider",
                                    min=1,
                                    max=20,
                                    step=1,
                                    value=10,
                                    marks={
                                        1: "1",
                                        5: "5",
                                        10: "10",
                                        15: "15",
                                        20: "20"
                                    },
                                    tooltip={
                                        "placement": "bottom",
                                        "always_visible": True
                                    }
                                )
                            ])
                        ], className="mb-4")
                    ], md=6),
                    
                    # Similarity threshold control
                    dbc.Col([
                        dbc.Card(id="similarity-card", children=[
                            dbc.CardBody([
                                html.Div([
                                    html.Label(
                                        "Similaridade mínima:",
                                        id="similarity-label",
                                        className="fw-bold d-inline"
                                    ),
                                    html.I(
                                        className="bi bi-question-circle ms-2",
                                        id="tooltip-similarity",
                                        style={"cursor": "pointer"}
                                    ),
                                    dbc.Tooltip(
                                        "Quanto maior, mais preciso e restrito "
                                        "serão os resultados.",
                                        target="tooltip-similarity"
                                    )
                                ]),
                                dcc.Slider(
                                    id="similarity-threshold",
                                    min=0,
                                    max=1,
                                    step=0.05,
                                    value=0.8,
                                    marks={
                                        0.0: "0.0",
                                        0.2: "0.2",
                                        0.4: "0.4",
                                        0.6: "0.6",
                                        0.8: "0.8",
                                        1.0: "1.0"
                                    },
                                    tooltip={
                                        "placement": "bottom",
                                        "always_visible": True
                                    }
                                )
                            ])
                        ], className="mb-4")
                    ], md=6)
                ])
            ], md=8, className="mx-auto")
        ]),
            
        # Loading spinner
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    id="loading",
                    type="default",
                    children=html.Div(id="loading-output")
                )
            ], md=8, className="mx-auto")
        ]),
            
        # Results
        dbc.Row([
            dbc.Col([
                html.Div(
                    id="results-container",
                    style={"paddingBottom": "100px"}
                )
            ], md=8, className="mx-auto")
        ])
    ], fluid=True, className="py-4", style={"minHeight": "100vh"}),
    
    # Footer - fixado na parte inferior
    html.Footer(id="footer", children=[
        html.Hr(id="footer-hr", style={"margin": "0"}),
        html.P(
            "Powered by FastAPI, FAISS, and sentence-transformers",
            id="footer-text",
            className="text-center small py-3 mb-0"
        )
    ], style={
        "position": "fixed",
        "bottom": "0",
        "width": "100%",
        "zIndex": "1000"
    })
])


def highlight_similar_words(text, query):
    """
    Highlight words in text that match query terms.
    
    Args:
        text: The text to highlight
        query: The search query
    
    Returns:
        A list of html components with highlighted matches
    """
    if not query or not text:
        return text
    
    # Extract query words (split by spaces and remove punctuation)
    query_words = [w.strip().lower() for w in query.split() if w.strip()]
    
    if not query_words:
        return text
    
    # Create a pattern that matches any of the query words
    # Use word boundaries to match whole words only
    pattern = r'\b(' + '|'.join(
        re.escape(word) for word in query_words
    ) + r')\b'
    
    # Split text by matches while keeping the matched parts
    parts = re.split(pattern, text, flags=re.IGNORECASE)
    
    # Build result with highlighted matches
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Non-matching part
            if part:
                result.append(part)
        else:
            # Matching part - highlight it
            result.append(
                html.Span(
                    part,
                    style={
                        "fontWeight": "bold",
                        "fontSize": "1.2em"
                    }
                )
            )
    
    return result


# Dark mode callbacks
@app.callback(
    Output("theme-store", "data"),
    Input("theme-toggle", "n_clicks"),
    State("theme-store", "data"),
    prevent_initial_call=True
)
def toggle_theme(n_clicks, current_theme):
    """Toggle between light and dark theme"""
    return "dark" if current_theme == "light" else "light"


@app.callback(
    Output("theme-toggle", "children"),
    Input("theme-store", "data")
)
def update_theme_icon(theme):
    """Update theme toggle button icon"""
    if theme == "dark":
        return html.I(className="bi bi-sun-fill")
    return html.I(className="bi bi-moon-fill")


@app.callback(
    Output("main-container", "style"),
    Input("theme-store", "data")
)
def update_container_style(theme):
    """Update main container style based on theme"""
    if theme == "dark":
        return {
            "minHeight": "90vh",
            "backgroundColor": "#1a1a1a",
            "color": "#f8f9fa"
        }
    return {
        "minHeight": "90vh",
        "backgroundColor": "#ffffff",
        "color": "#212529"
    }


@app.callback(
    Output("footer", "style"),
    Input("theme-store", "data")
)
def update_footer_style(theme):
    """Update footer style based on theme"""
    base_style = {
        "position": "fixed",
        "bottom": "0",
        "width": "100%",
        "zIndex": "1000"
    }
    
    if theme == "dark":
        base_style.update({
            "backgroundColor": "#2d2d2d",
            "color": "#f8f9fa"
        })
    else:
        base_style.update({
            "backgroundColor": "white",
            "color": "#6c757d"
        })
    
    return base_style


@app.callback(
    Output("subtitle", "className"),
    Input("theme-store", "data")
)
def update_subtitle_class(theme):
    """Update subtitle className based on theme"""
    if theme == "dark":
        return "text-center mb-4"
    return "text-center text-muted mb-4"


@app.callback(
    [Output("footer-hr", "style"),
     Output("footer-text", "style")],
    Input("theme-store", "data")
)
def update_footer_elements_style(theme):
    """Update footer HR and text style based on theme"""
    if theme == "dark":
        hr_style = {"margin": "0", "borderColor": "#444444"}
        text_style = {"color": "#f8f9fa"}
    else:
        hr_style = {"margin": "0"}
        text_style = {"color": "#6c757d"}
    
    return hr_style, text_style


@app.callback(
    [Output("top-k-card", "style"),
     Output("similarity-card", "style")],
    Input("theme-store", "data")
)
def update_control_cards_style(theme):
    """Update control cards style based on theme"""
    if theme == "dark":
        card_style = {
            "backgroundColor": "#2d2d2d",
            "borderColor": "#444444",
            "color": "#f8f9fa"
        }
    else:
        card_style = {
            "backgroundColor": "#ffffff",
            "borderColor": "#dee2e6",
            "color": "#212529"
        }
    return card_style, card_style


@app.callback(
    [Output("top-k-label", "style"),
     Output("similarity-label", "style")],
    Input("theme-store", "data")
)
def update_control_labels_style(theme):
    """Update control labels style based on theme"""
    if theme == "dark":
        label_style = {"color": "#f8f9fa"}
    else:
        label_style = {"color": "#212529"}
    return label_style, label_style


@app.callback(
    [Output("results-container", "children"),
     Output("loading-output", "children")],
    [Input("search-button", "n_clicks"),
     Input("search-input", "n_submit")],
    [State("search-input", "value"),
     State("top-k-slider", "value"),
     State("similarity-threshold", "value"),
     State("theme-store", "data")],
    prevent_initial_call=True
)
def search_podcasts(
    n_clicks, n_submit, query, top_k, similarity_threshold, theme
):
    """
    Handle search button click or Enter key press
    
    Args:
        n_clicks: Number of times search button was clicked
        n_submit: Number of times Enter was pressed in input
        query: Search query string
        top_k: Number of results to return
        similarity_threshold: Minimum similarity score
        theme: Current theme (light/dark)
    
    Returns:
        Tuple of (results HTML, loading indicator)
    """
    # Theme colors
    if theme == "dark":
        card_bg = "#2d2d2d"
        card_text = "#f8f9fa"
        warning_bg = "#3a3a1a"
        warning_border = "#666633"
        info_bg = "#2a2a2a"
        info_border = "#444444"
    else:
        card_bg = "#ffffff"
        card_text = "#212529"
        warning_bg = "#fff3cd"
        warning_border = "#ffc107"
        info_bg = "#f8f9fa"
        info_border = "#dee2e6"
    
    print(f"\n{'='*60}")
    print(f"🔍 FRONTEND SEARCH REQUEST")
    print(f"{'='*60}")
    print(f"Query: '{query}'")
    print(f"Top K: {top_k}")
    print(f"Similarity Threshold: {similarity_threshold}")
    print(f"n_clicks: {n_clicks}, n_submit: {n_submit}")
    
    if not query or query.strip() == "":
        print("❌ Empty query, returning warning")
        return html.Div([
            html.Div(
                [
                    html.Div(
                        "✍️",
                        style={
                            "fontSize": "50px",
                            "textAlign": "center",
                            "marginBottom": "10px"
                        }
                    ),
                    html.H5(
                        "Digite algo para buscar",
                        className="text-center mb-2",
                        style={"color": card_text}
                    ),
                    html.P(
                        "Insira um termo ou frase no campo acima "
                        "para encontrar episódios relacionados.",
                        className="text-center small mb-0",
                        style={"color": card_text}
                    )
                ],
                style={
                    "padding": "25px",
                    "backgroundColor": info_bg,
                    "borderRadius": "10px",
                    "border": f"1px solid {info_border}"
                }
            )
        ], className="mt-4"), ""
    
    try:
        # Call backend API
        url = f"{BACKEND_URL}?q={query.strip()}&top_k={top_k}"
        print(f"📡 Making request to: {url}")
        
        response = requests.get(
            BACKEND_URL,
            params={"q": query.strip(), "top_k": top_k},
            timeout=30
        )
        
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"❌ Error response: {response.text}")
            # Mensagem amigável para o usuário, detalhes nos logs
            return html.Div(
                dbc.Alert(
                    "Infelizmente aconteceu um erro ao processar sua busca. Por favor, tente novamente em alguns instantes.",
                    color="danger"
                ),
                className="mt-4"
            ), ""
        
        results = response.json()
        print(f"✓ Received {len(results)} results from backend")
        
        # Check if backend returned any results
        if not results:
            print("ℹ️  No results found from backend")
            return html.Div([
                html.Div(
                    dbc.Row([
                        # Lado esquerdo - Informação (60%)
                        dbc.Col([
                            html.Div(
                                "🔍",
                                style={
                                    "fontSize": "50px",
                                    "textAlign": "center",
                                    "marginBottom": "10px"
                                }
                            ),
                            html.H5(
                                "Nenhum resultado encontrado",
                                className="text-center mb-2",
                                style={"color": card_text}
                            ),
                            html.P(
                                f'Não encontramos episódios relacionados a '
                                f'"{query}".',
                                className="text-center small mb-0",
                                style={"color": card_text}
                            )
                        ], md=7, className="d-flex flex-column justify-content-center"),
                        
                        # Lado direito - Sugestões (40%)
                        dbc.Col([
                            html.P(
                                "💡 Sugestões:",
                                className="fw-bold mb-2 small",
                                style={"color": card_text}
                            ),
                            html.Ul([
                                html.Li(
                                    "Palavras-chave diferentes",
                                    className="small",
                                    style={"color": card_text}
                                ),
                                html.Li(
                                    "Termos mais gerais",
                                    className="small",
                                    style={"color": card_text}
                                ),
                                html.Li(
                                    "Reduza a similaridade",
                                    className="small",
                                    style={"color": card_text}
                                )
                            ], className="mb-0 small")
                        ], md=5, className="d-flex flex-column justify-content-center")
                    ], className="g-3"),
                    style={
                        "padding": "25px",
                        "backgroundColor": info_bg,
                        "borderRadius": "10px",
                        "border": f"1px solid {info_border}"
                    }
                )
            ], className="mt-4"), ""
        
        # Filter results by similarity threshold
        filtered_results = [
            r for r in results if r['score'] >= similarity_threshold
        ]
        print(
            f"✓ {len(filtered_results)} results after "
            f"applying threshold {similarity_threshold}"
        )
        
        if not filtered_results:
            print("ℹ️  No results found above similarity threshold")
            return html.Div([
                html.Div(
                    dbc.Row([
                        # Lado esquerdo - Informação (60%)
                        dbc.Col([
                            html.Div(
                                "⚠️",
                                style={
                                    "fontSize": "50px",
                                    "textAlign": "center",
                                    "marginBottom": "10px"
                                }
                            ),
                            html.H5(
                                "Resultados com baixa similaridade",
                                className="text-center mb-2",
                                style={"color": card_text}
                            ),
                            html.P(
                                f"Encontramos {len(results)} resultado(s), "
                                f"mas nenhum atingiu {similarity_threshold:.0%}.",
                                className="text-center small mb-0",
                                style={"color": card_text}
                            )
                        ], md=7, className="d-flex flex-column justify-content-center"),
                        
                        # Lado direito - Sugestões (40%)
                        dbc.Col([
                            html.P(
                                "💡 Tente ajustar:",
                                className="fw-bold mb-2 small",
                                style={"color": card_text}
                            ),
                            html.Ul([
                                html.Li(
                                    f"Similaridade: {similarity_threshold:.0%}",
                                    className="small",
                                    style={"color": card_text}
                                ),
                                html.Li(
                                    "Número de resultados",
                                    className="small",
                                    style={"color": card_text}
                                ),
                                html.Li(
                                    "Termos de busca",
                                    className="small",
                                    style={"color": card_text}
                                )
                            ], className="mb-0 small")
                        ], md=5, className="d-flex flex-column justify-content-center")
                    ], className="g-3"),
                    style={
                        "padding": "25px",
                        "backgroundColor": warning_bg,
                        "borderRadius": "10px",
                        "border": f"1px solid {warning_border}"
                    }
                )
            ], className="mt-4"), ""
        
        # Build results cards
        cards = []
        for i, result in enumerate(filtered_results, 1):
            score = result['score']
            
            # Highlight similar words in excerpt
            highlighted_text = highlight_similar_words(
                result['excerpt'],
                query
            )
            
            card = dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.H5(
                            f"🎧 {result['episode']}",
                            className="card-title d-inline",
                            style={"color": card_text}
                        ),
                        dbc.Badge(
                            f"{score:.2%}",
                            color="primary",
                            className="float-end"
                        )
                    ]),
                    html.P(
                        highlighted_text,
                        className="card-text mt-2",
                        style={"color": card_text}
                    )
                ])
            ], className="mb-3", style={
                "backgroundColor": card_bg,
                "borderColor": info_border
            })
            cards.append(card)
        
        print(f"✓ Returning {len(cards)} result cards")
        print(f"{'='*60}\n")
        
        # Build header with result count and threshold info
        header = html.Div([
            html.H4(
                f"Encontrados {len(filtered_results)} resultados",
                className="mb-2",
                style={"color": card_text}
            ),
            html.P(
                f"Similaridade mínima: {similarity_threshold:.2f}",
                className="mb-2",
                style={"color": card_text}
            )
        ])
        
        return html.Div([
            header,
            html.Div(cards)
        ]), ""
    
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        print(f"{'='*60}\n")
        return html.Div(
            dbc.Alert(
                "Cannot connect to backend. Make sure the API server is running on port 8000.",
                color="danger"
            ),
            className="mt-4"
        ), ""
    
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout Error: {e}")
        print(f"{'='*60}\n")
        return html.Div(
            dbc.Alert("Request timed out. Please try again.", color="warning"),
            className="mt-4"
        ), ""
    
    except Exception as e:
        print(f"❌ Unexpected Error: {type(e).__name__}: {e}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        print(f"{'='*60}\n")
        # Mensagem amigável para o usuário, detalhes completos nos logs
        return html.Div(
            dbc.Alert(
                "Ops! Algo inesperado aconteceu. Por favor, tente novamente.",
                color="danger"
            ),
            className="mt-4"
        ), ""


if __name__ == "__main__":
    print("=" * 60)
    print("Starting Nerdcast Finder Frontend")
    print("=" * 60)
    print("URL: http://127.0.0.1:8050")
    print("Make sure the backend API is running on http://localhost:8000")
    print("=" * 60)
    
    app.run(debug=True, host="127.0.0.1", port=8050)
