"""
Nerdcast Finder - Frontend Dash Application

A minimal search interface for finding podcast episodes using semantic search.
"""
import sys
from pathlib import Path

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
import requests
from dash import Dash, html, dcc, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from utils.logger import logger

# Configuration
BACKEND_URL = "http://localhost:8000/api/search"

# Initialize Dash app with Bootstrap theme
app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        dbc.icons.BOOTSTRAP
    ],
    title="Nerdcast Finder",
    suppress_callback_exceptions=True
)

# Custom index with aggressive theme enforcement and logging
app.index_string = '''
<!DOCTYPE html>
<html data-theme="light">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        <script>
            // Apply theme before CSS loads
            (function() {
                try {
                    var stored = localStorage.getItem('theme-store');
                    var theme = 'light';
                    if (stored) {
                        try {
                            theme = JSON.parse(stored);
                        } catch(e) {
                            theme = stored === 'dark' ? 'dark' : 'light';
                        }
                    }
                    document.documentElement.setAttribute('data-theme', theme);
                } catch(e) {
                    document.documentElement.setAttribute('data-theme', 'light');
                }
            })();
        </script>
        {%css%}
        <script>
            // Continuous theme enforcement
            (function() {
                function getTheme() {
                    try {
                        var stored = localStorage.getItem('theme-store');
                        if (!stored) return 'light';
                        try {
                            return JSON.parse(stored);
                        } catch(e) {
                            return stored === 'dark' ? 'dark' : 'light';
                        }
                    } catch(e) {
                        return 'light';
                    }
                }
                
                function enforceTheme() {
                    var correctTheme = getTheme();
                    var currentAttr = document.documentElement.getAttribute('data-theme');
                    if (currentAttr !== correctTheme) {
                        document.documentElement.setAttribute('data-theme', correctTheme);
                    }
                }
                
                enforceTheme();
                
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', enforceTheme);
                }
                
                window.addEventListener('storage', function(e) {
                    if (e.key === 'theme-store') {
                        enforceTheme();
                    }
                });
                
                setInterval(enforceTheme, 200);
                
                var lastPathname = window.location.pathname;
                setInterval(function() {
                    if (window.location.pathname !== lastPathname) {
                        lastPathname = window.location.pathname;
                        enforceTheme();
                    }
                }, 50);
            })();
        </script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Layouts functions for different pages
def home_layout():
    """Layout for the home/search page"""
    return dbc.Container(children=[
        # Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    dcc.Link(
                        html.H1(
                            "🎙️ Nerdcast Finder",
                            className="text-center my-4 d-inline-block",
                            style={"width": "100%"}
                        ),
                        href="/",
                        style={"textDecoration": "none", "color": "inherit"}
                    ),
                    html.Div([
                        dcc.Link(
                            "Sobre",
                            href="/about",
                            id="about-link",
                            className="me-3",
                            style={"fontSize": "16px", "textDecoration": "none"}
                        ),
                        dbc.Button(
                            html.I(className="bi bi-moon-fill"),
                            id="theme-toggle",
                            color="link",
                            size="lg",
                            style={"fontSize": "24px"}
                        )
                    ], style={
                        "position": "absolute",
                        "top": "20px",
                        "right": "20px",
                        "display": "flex",
                        "alignItems": "center"
                    })
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
                ], className="mb-3"),
                # Advanced options toggle
                html.Div([
                    dbc.Button(
                        [
                            html.I(className="bi bi-gear me-2"),
                            "Opções avançadas"
                        ],
                        id="toggle-advanced",
                        color="link",
                        size="sm",
                        className="text-decoration-none",
                        n_clicks=0
                    )
                ], className="text-center mb-2")
            ], md=8, className="mx-auto")
        ]),
            
        # Advanced search controls (collapsible)
        dbc.Row([
            dbc.Col([
                dbc.Collapse([
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
                                        value=20,
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
                                            "Confiabilidade mínima:",
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
                                        value=0.5,
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
                ], id="advanced-options", is_open=False, className="mb-3")
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
                    id="results-container"
                )
            ], md=8, className="mx-auto")
        ])
    ], fluid=True, className="py-4")


def about_layout():
    """Layout for the about page"""
    return dbc.Container(children=[
        # Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    dcc.Link(
                        html.H1(
                            "Sobre o Nerdcast Finder",
                            className="text-center my-4 d-inline-block",
                            style={"width": "100%"}
                        ),
                        href="/",
                        style={"textDecoration": "none", "color": "inherit"}
                    ),
                    html.Div([
                        dcc.Link(
                            "← Voltar",
                            href="/",
                            id="back-link",
                            className="me-3",
                            style={"fontSize": "16px", "textDecoration": "none"}
                        ),
                        dbc.Button(
                            html.I(className="bi bi-moon-fill"),
                            id="theme-toggle",
                            color="link",
                            size="lg",
                            style={"fontSize": "24px"}
                        )
                    ], style={
                        "position": "absolute",
                        "top": "20px",
                        "right": "20px",
                        "display": "flex",
                        "alignItems": "center"
                    })
                ], style={"position": "relative"})
            ])
        ]),
        
        # Content
        dbc.Row([
            dbc.Col([
                # Disclaimer Section
                dbc.Card(id="disclaimer-card", children=[
                    dbc.CardHeader(id="disclaimer-header", children=html.H4("Aviso Legal e Direitos Autorais", className="mb-0")),
                    dbc.CardBody([
                        html.P([
                            "Este projeto é uma ferramenta de busca semântica desenvolvida exclusivamente para fins ",
                            html.Strong("educacionais, técnicos e de demonstração de habilidades profissionais"), 
                            ". O desenvolvedor não possui, hospeda ou distribui qualquer conteúdo de áudio dos podcasts."
                        ], className="mb-3"),
                        html.P([
                            html.Strong("Todos os direitos autorais pertencem aos seus respectivos proprietários."),
                            " O conteúdo dos episódios do Nerdcast é de propriedade exclusiva do ",
                            html.A("Jovem Nerd", href="https://jovemnerd.com.br", target="_blank", className="text-primary"),
                            " e seus criadores."
                        ], className="mb-3"),
                        html.P([
                            "Esta aplicação apenas indexa e busca transcrições geradas localmente para fins de ",
                            "pesquisa e referência. Nenhum conteúdo de áudio é redistribuído ou disponibilizado ",
                            "através desta ferramenta. Os usuários são responsáveis por respeitar os direitos ",
                            "autorais e termos de uso do conteúdo original."
                        ], className="mb-3"),
                        html.P([
                            "Para ouvir os episódios originais, por favor visite o site oficial: ",
                            html.A("https://jovemnerd.com.br", href="https://jovemnerd.com.br", target="_blank", className="text-primary"),
                            " ou suas plataformas de podcast preferidas."
                        ], className="mb-0")
                    ])
                ], className="mb-4"),
                
                # Technical Section
                dbc.Card(id="technical-card", children=[
                    dbc.CardHeader(id="technical-header", children=html.H4("Como Funciona", className="mb-0")),
                    dbc.CardBody([
                        html.P([
                            "O Nerdcast Finder é uma aplicação de ",
                            html.Strong("busca semântica"), 
                            " que permite encontrar episódios de podcast por significado e contexto, ",
                            "não apenas por palavras-chave exatas."
                        ], className="mb-3"),
                        
                        html.H5("Arquitetura e Tecnologias:", className="mt-4 mb-3"),
                        html.Ul([
                            html.Li([
                                html.Strong("Backend (FastAPI):"), 
                                " API REST construída com FastAPI, responsável por processar ",
                                "as buscas e retornar resultados ranqueados por confiabilidade semântica."
                            ]),
                            html.Li([
                                html.Strong("Banco de Dados (SQLite):"), 
                                " Armazena metadados dos episódios (título, data de publicação, duração, ",
                                "tamanho do arquivo, etc.) e segmentos transcritos do conteúdo de áudio."
                            ]),
                            html.Li([
                                html.Strong("Coleta de Metadados (RSS Feed):"), 
                                " Os metadados dos episódios são carregados automaticamente do feed RSS ",
                                "oficial do Nerdcast, garantindo informações atualizadas sobre cada episódio."
                            ]),
                            html.Li([
                                html.Strong("Transcrição (Whisper):"), 
                                " Utiliza o modelo Whisper da OpenAI para converter áudio em texto, ",
                                "permitindo a indexação do conteúdo falado dos episódios."
                            ]),
                            html.Li([
                                html.Strong("Embeddings (Sentence-Transformers):"), 
                                " Modelo all-mpnet-base-v2 (768 dimensões) converte texto em vetores ",
                                "numéricos que capturam significado semântico."
                            ]),
                            html.Li([
                                html.Strong("Busca Vetorial (FAISS):"), 
                                " Facebook AI Similarity Search (IndexFlatL2) permite busca rápida ",
                                "por confiabilidade de cosseno em milhares de vetores."
                            ]),
                            html.Li([
                                html.Strong("Frontend (Dash + Bootstrap):"), 
                                " Interface web responsiva com suporte a temas claro/escuro, ",
                                "construída com Plotly Dash e Bootstrap components."
                            ])
                        ], className="mb-3"),
                        
                        html.H5("Fluxo de Funcionamento:", className="mt-4 mb-3"),
                        html.Ol([
                            html.Li("Os metadados dos episódios são extraídos do feed RSS oficial"),
                            html.Li("O áudio do episódio é transcrito usando o modelo Whisper"),
                            html.Li("A transcrição é segmentada em partes menores para indexação"),
                            html.Li("Cada segmento é convertido em embedding vetorial (768 dims)"),
                            html.Li("Os vetores são indexados no FAISS para busca eficiente"),
                            html.Li("Quando você faz uma busca, sua query também é vetorizada"),
                            html.Li("O FAISS compara seu vetor com todos os segmentos indexados"),
                            html.Li("Resultados são ranqueados por confiabilidade semântica"),
                            html.Li("A interface exibe os trechos mais relevantes com metadados")
                        ], className="mb-3")
                    ])
                ], className="mb-4")
            ], md=10, lg=8, className="mx-auto")
        ])
    ], fluid=True, className="py-4")


# Main app layout with routing
app.layout = html.Div([
    # URL routing
    dcc.Location(id="url", refresh=False),
    
    # Store for theme state (dark/light) - persists to localStorage
    dcc.Store(id="theme-store", storage_type="local"),
    
    # Page wrapper
    html.Div(id="page-wrapper", children=[
        # Page content (will be populated by callback)
        html.Div(id="page-content")
    ], style={
        "minHeight": "100vh",
        "paddingBottom": "100px"
    }),
    
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


# Page routing callback
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    """Render the appropriate page based on the URL"""
    if pathname == "/about":
        return about_layout()
    else:
        return home_layout()


# Theme toggle callback - clientside for instant response
app.clientside_callback(
    """
    function(n_clicks, current_theme) {
        // Only proceed if this is a real click
        if (!n_clicks || n_clicks === 0 || typeof n_clicks !== 'number') {
            return window.dash_clientside.no_update;
        }
        
        if (!current_theme) current_theme = "light";
        var newTheme = current_theme === "light" ? "dark" : "light";
        
        // Update localStorage synchronously
        try {
            localStorage.setItem('theme-store', JSON.stringify(newTheme));
        } catch(e) {}
        
        // Apply to DOM
        document.documentElement.setAttribute('data-theme', newTheme);
        
        return newTheme;
    }
    """,
    Output("theme-store", "data"),
    Input("theme-toggle", "n_clicks"),
    State("theme-store", "data"),
    prevent_initial_call=True
)


# Advanced options toggle callback - clientside for instant response
app.clientside_callback(
    """
    function(n_clicks, is_open) {
        // Only proceed if this is a real click
        if (!n_clicks || n_clicks === 0 || typeof n_clicks !== 'number') {
            return window.dash_clientside.no_update;
        }
        
        // Toggle the current state
        return !is_open;
    }
    """,
    Output("advanced-options", "is_open"),
    Input("toggle-advanced", "n_clicks"),
    State("advanced-options", "is_open"),
    prevent_initial_call=True
)


@app.callback(
    Output("theme-toggle", "children"),
    Input("theme-store", "data")
)
def update_theme_icon(theme):
    """Update theme toggle button icon"""
    if not theme:
        theme = "light"
    if theme == "dark":
        return html.I(className="bi bi-sun-fill")
    return html.I(className="bi bi-moon-fill")


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
    
    is_dark_mode = (theme == "dark")
    
    logger.header("🔍 FRONTEND SEARCH REQUEST")
    logger.info(f"Query: '{query}'")
    logger.info(f"Top K: {top_k}")
    logger.info(f"Similarity Threshold: {similarity_threshold}")
    logger.info(f"n_clicks: {n_clicks}, n_submit: {n_submit}")
    
    if not query or query.strip() == "":
        logger.warning("Empty query, returning warning")
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
        logger.info(f"Making request to: {url}")
        
        response = requests.get(
            BACKEND_URL,
            params={"q": query.strip(), "top_k": top_k},
            timeout=30
        )
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            logger.error(f"Error response: {response.text}")
            # Mensagem amigável para o usuário, detalhes nos logs
            return html.Div(
                dbc.Alert(
                    "Infelizmente aconteceu um erro ao processar sua busca. Por favor, tente novamente em alguns instantes.",
                    color="danger"
                ),
                className="mt-4"
            ), ""
        
        results = response.json()
        logger.success(f"Received {len(results)} results from backend")
        
        # Check if backend returned any results
        if not results:
            logger.info("No results found from backend")
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
                                    "Reduza a confiabilidade",
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
        logger.success(
            f"{len(filtered_results)} results after "
            f"applying threshold {similarity_threshold}"
        )
        
        if not filtered_results:
            logger.info("No results found above similarity threshold")
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
                                "Resultados com baixa confiabilidade",
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
                                    f"Confiabilidade: {similarity_threshold:.0%}",
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
            title = result.get('title', result['episode'])
            image_url = result.get('image_url')
            
            # Highlight similar words in excerpt
            highlighted_text = highlight_similar_words(
                result['excerpt'],
                query
            )
            
            # Image component (with fixed size)
            if image_url:
                image_component = html.Img(
                    src=image_url,
                    style={
                        "width": "150px",
                        "height": "150px",
                        "borderRadius": "8px",
                        "objectFit": "cover"
                    }
                )
            else:
                # Placeholder for episodes without image
                image_component = html.Div([
                    html.I(className="bi bi-mic-fill", style={"fontSize": "60px", "color": "#6c757d"}),
                ], style={
                    "width": "150px",
                    "height": "150px",
                    "borderRadius": "8px",
                    "backgroundColor": "#2d2d2d" if is_dark_mode else "#e9ecef",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center"
                })
            
            # Metadata area (30% right side)
            published_date = result.get('published_date')
            duration_seconds = result.get('duration_seconds')
            file_size_mb = result.get('file_size_mb')
            
            # Format metadata
            metadata_items = []
            if published_date:
                # Convert ISO date to readable format
                from datetime import datetime
                try:
                    date_obj = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime('%d/%m/%Y')
                    metadata_items.append(html.Div([
                        html.I(className="bi bi-calendar3 me-2", style={"color": "#6c757d"}),
                        html.Span(formatted_date, style={"fontSize": "0.85rem"})
                    ], className="mb-2"))
                except:
                    pass
            
            if duration_seconds:
                # Convert seconds to MM:SS or HH:MM:SS
                hours = duration_seconds // 3600
                minutes = (duration_seconds % 3600) // 60
                seconds = duration_seconds % 60
                if hours > 0:
                    duration_str = f"{hours}h {minutes}m"
                else:
                    duration_str = f"{minutes}m {seconds}s"
                metadata_items.append(html.Div([
                    html.I(className="bi bi-clock me-2", style={"color": "#6c757d"}),
                    html.Span(duration_str, style={"fontSize": "0.85rem"})
                ], className="mb-2"))
            
            if file_size_mb:
                metadata_items.append(html.Div([
                    html.I(className="bi bi-hdd me-2", style={"color": "#6c757d"}),
                    html.Span(f"{file_size_mb:.1f} MB", style={"fontSize": "0.85rem"})
                ], className="mb-2"))
            
            # Build card with 3-column layout
            card = dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        # Image column (fixed width)
                        dbc.Col([
                            image_component
                        ], width="auto", className="d-flex align-items-start"),
                        
                        # Content column (flexible)
                        dbc.Col([
                            html.H5(
                                f"🎧 {title}",
                                className="card-title mb-2",
                                style={"color": card_text, "fontSize": "1.1rem"}
                            ),
                            html.P(
                                highlighted_text,
                                className="card-text mb-0",
                                style={"color": card_text, "fontSize": "0.95rem"}
                            )
                        ], className="flex-grow-1"),
                        
                        # Metadata column (smaller, right side)
                        dbc.Col([
                            # Similarity badge at top
                            html.Div([
                                dbc.Badge(
                                    [
                                        html.Div("Confiabilidade", className="small", style={"fontSize": "0.7rem"}),
                                        html.Div(f"{score:.2%}", style={"fontSize": "1.1rem", "fontWeight": "bold"})
                                    ],
                                    color="primary",
                                    className="mb-3",
                                    style={"fontSize": "1rem", "padding": "0.5rem 1rem"}
                                ),
                            ], className="text-center mb-3"),
                            # Metadata items below
                            html.Div(
                                metadata_items,
                                style={"color": card_text}
                            )
                        ], width=2, className="d-flex flex-column align-items-center border-start", style={"borderColor": info_border + "!important"})
                    ], className="g-3")
                ], style={"padding": "1rem"})
            ], className="mb-3", style={
                "backgroundColor": card_bg,
                "borderColor": info_border
            })
            cards.append(card)
        
        logger.success(f"Returning {len(cards)} result cards")
        
        # Build header with result count and threshold info
        header = html.Div([
            html.H4(
                f"Encontrados {len(filtered_results)} resultados",
                className="mb-2",
                style={"color": card_text}
            ),
            html.P(
                f"Confiabilidade mínima: {similarity_threshold:.2f}",
                className="mb-2",
                style={"color": card_text}
            )
        ])
        
        return html.Div([
            header,
            html.Div(cards)
        ]), ""
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection Error: {e}")
        return html.Div(
            dbc.Alert(
                "Cannot connect to backend. Make sure the API server is running on port 8000.",
                color="danger"
            ),
            className="mt-4"
        ), ""
    
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout Error: {e}")
        return html.Div(
            dbc.Alert("Request timed out. Please try again.", color="warning"),
            className="mt-4"
        ), ""
    
    except Exception as e:
        import traceback
        logger.error(f"Unexpected Error: {type(e).__name__}: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        # Mensagem amigável para o usuário, detalhes completos nos logs
        return html.Div(
            dbc.Alert(
                "Ops! Algo inesperado aconteceu. Por favor, tente novamente.",
                color="danger"
            ),
            className="mt-4"
        ), ""


if __name__ == "__main__":
    logger.header("Starting Nerdcast Finder Frontend")
    logger.info("URL: http://127.0.0.1:8050")
    logger.info("Make sure the backend API is running on http://localhost:8000")
    
    app.run(debug=True, host="127.0.0.1", port=8050)
