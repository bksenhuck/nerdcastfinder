"""
Podcast Finder - Frontend Dash Application

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

import os
from backend.app.core.logger import logger
from backend.app.db.session import get_db_session
from backend.app.db.models import PodcastEpisode, PodcastSegment

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")


def get_podcast_stats():
    """Get statistics about available podcasts"""
    try:
        db = get_db_session()
        
        # Episódios com metadata (downloaded)
        total_episodes_downloaded = db.query(PodcastEpisode).count()
        
        # Episódios processados (com chunks/embeddings)
        from sqlalchemy import func
        total_episodes_processed = db.query(
            func.count(func.distinct(PodcastSegment.episode))
        ).scalar() or 0
        
        # Programas e feeds (baseado no que foi processado)
        distinct_programs = (
            db.query(PodcastEpisode.program_name)
            .filter(PodcastEpisode.filename.in_(
                db.query(PodcastSegment.episode).distinct()
            ))
            .distinct()
            .count()
        )
        distinct_feeds = (
            db.query(PodcastEpisode.podcast_source)
            .filter(PodcastEpisode.filename.in_(
                db.query(PodcastSegment.episode).distinct()
            ))
            .distinct()
            .count()
        )
        
        db.close()
        return total_episodes_downloaded, total_episodes_processed, distinct_programs, distinct_feeds
    except Exception as e:
        logger.error(f"Error getting podcast stats: {e}")
        return 0, 0, 0, 0


def get_available_filters():
    """Get available feeds and programs for filtering"""
    try:
        response = requests.get(
            f"{BACKEND_URL.rstrip('/')}/api/filters",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("feeds", []), data.get("programs", [])
        else:
            logger.warning(f"Failed to get filters: {response.status_code}")
            return [], []
    except Exception as e:
        logger.error(f"Error getting filters: {e}")
        # Fallback to database
        try:
            db = get_db_session()
            feeds = db.query(
                PodcastEpisode.podcast_source
            ).distinct().all()
            feeds = sorted([f[0] for f in feeds if f[0] is not None])
            
            programs = db.query(
                PodcastEpisode.program_name
            ).distinct().all()
            programs = sorted([p[0] for p in programs if p[0] is not None])
            
            db.close()
            return feeds, programs
        except Exception as db_e:
            logger.error(f"Error getting filters from DB: {db_e}")
            return [], []


# Initialize Dash app with Bootstrap theme
app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        dbc.icons.BOOTSTRAP
    ],
    title="Podcast Finder",
    suppress_callback_exceptions=True,
    # FastAPI's WSGIMiddleware strips the mount prefix (/ui) before
    # forwarding requests to the WSGI app, so PATH_INFO arrives without
    # the /ui prefix. routes_pathname_prefix must be "/" so Dash registers
    # Flask routes at the stripped paths (e.g. "/" not "/ui/").
    # requests_pathname_prefix="/ui/" tells the client-side JS to use
    # the full /ui/... URLs when fetching Dash resources, which FastAPI
    # will then strip and forward correctly.
    requests_pathname_prefix="/ui/",
    routes_pathname_prefix="/",
    assets_url_path="assets"
)

# Custom index with aggressive theme enforcement and logging
app.index_string = '''
<!DOCTYPE html>
<html data-theme="light">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        <!-- Preferred favicon (PNG) served from assets -->
        <link rel="icon" type="image/png" sizes="32x32" href="/ui/assets/images/podcast_finder_logo.png">
        <!-- Fallback for browsers requesting /favicon.ico -->
        <link rel="shortcut icon" href="/favicon.ico">
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
    # Get podcast statistics
    total_downloaded, total_processed, total_programs, total_feeds = get_podcast_stats()
    episodes_pending = total_downloaded - total_processed
    
    # Get available filters
    available_feeds, available_programs = get_available_filters()
    
    return dbc.Container(children=[
        # Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    dcc.Link(
                        html.Div([
                            html.Img(
                                src="/ui/assets/images/podcast_finder_logo.png",
                                className="d-inline-block me-3",
                                style={"height": "50px", "width": "auto", "verticalAlign": "middle"}
                            ),
                            html.H1(
                                "Podcast Finder",
                                className="d-inline-block",
                                style={"verticalAlign": "middle", "marginBottom": "0"}
                            )
                        ], style={"textAlign": "center", "marginTop": "20px", "marginBottom": "20px"}),
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
                f"{total_processed if total_processed > 0 else '-'} episódios prontos para busca • "
                f"{episodes_pending if episodes_pending > 0 else '-'} {'episódio' if episodes_pending == 1 else 'episódios'} em processamento",
                id="stats-subtitle",
                className="text-center mb-2",
                style={"fontSize": "0.85rem", "opacity": "0.7"}
            ),
            html.P(
                f"{total_programs} {'programa' if total_programs == 1 else 'programas'} • "
                f"{total_feeds} {'feed' if total_feeds == 1 else 'feeds'}",
                id="programs-subtitle",
                className="text-center mb-4",
                style={"fontSize": "0.85rem", "opacity": "0.6"}
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
                        className="form-control-lg",
                        style={
                            "paddingRight": "110px",
                            "position": "relative",
                            "zIndex": "1"
                        }
                    ),
                    dbc.Button(
                        html.I(className="bi bi-search"),
                        id="search-button",
                        color="primary",
                        className="btn-lg",
                        n_clicks=0,
                        title="Buscar",
                        style={
                            "width": "96px",
                            "marginLeft": "-48px",
                            "borderTopLeftRadius": "0",
                            "borderBottomLeftRadius": "0",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "position": "relative",
                            "zIndex": "3",
                            "boxShadow": "0 2px 6px rgba(0,0,0,0.08)"
                        }
                    )
                ], className="mb-3"),
                # Informational alert about current search behavior
                dbc.Alert(
                    "A pesquisa atual trará até 20 resultados com as maiores confiabilidades. Você pode usar os filtros e as Opções Avançadas abaixo para refinar a busca.",
                    color="info",
                    id="search-info-alert",
                    className="text-center mb-2",
                    style={"fontSize": "0.95rem"}
                ),
                # Advanced options toggle
                html.Div([
                    dbc.Button(
                        [
                            html.I(className="bi bi-sliders me-2"),
                            "Filtros e Opções Avançadas"
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
                    dbc.Card([
                        dbc.CardBody([
                            # Filters section
                            html.Div([
                                html.H6([
                                    html.I(className="bi bi-filter me-2"),
                                    "Filtros"
                                ], className="mb-3"),
                                dbc.Row([
                                    dbc.Col([
                                        html.Label(
                                            [
                                                html.I(
                                                    className="bi bi-rss me-2"
                                                ),
                                                "Feed:"
                                            ],
                                            className="fw-bold mb-2",
                                            style={"fontSize": "0.9rem"}
                                        ),
                                        dcc.Dropdown(
                                            id="feed-filter",
                                            options=[
                                                {
                                                    "label": "🌐 Todos",
                                                    "value": ""
                                                }
                                            ] + [
                                                {
                                                    "label": feed,
                                                    "value": feed
                                                }
                                                for feed in available_feeds
                                            ],
                                            value="",
                                            placeholder="Todos os feeds",
                                            clearable=True
                                        )
                                    ], md=6, className="mb-3"),
                                    dbc.Col([
                                        html.Label(
                                            [
                                                html.I(
                                                    className="bi bi-mic me-2"
                                                ),
                                                "Programa:"
                                            ],
                                            className="fw-bold mb-2",
                                            style={"fontSize": "0.9rem"}
                                        ),
                                        dcc.Dropdown(
                                            id="program-filter",
                                            options=[
                                                {
                                                    "label": "🎙️ Todos",
                                                    "value": ""
                                                }
                                            ] + [
                                                {
                                                    "label": prog,
                                                    "value": prog
                                                }
                                                for prog in available_programs
                                            ],
                                            value="",
                                            placeholder="Todos os programas",
                                            clearable=True
                                        )
                                    ], md=6, className="mb-3")
                                ])
                            ], className="mb-4 pb-3",
                               style={"borderBottom": "1px solid #dee2e6"}),
                            
                            # Search parameters section
                            html.Div([
                                html.H6([
                                    html.I(className="bi bi-gear me-2"),
                                    "Parâmetros de Busca"
                                ], className="mb-3"),
                                dbc.Row([
                                    # Number of results control
                                    dbc.Col([
                                        html.Div([
                                            html.Label(
                                                "Número de resultados:",
                                                id="top-k-label",
                                                className="fw-bold d-inline",
                                                style={"fontSize": "0.9rem"}
                                            ),
                                            html.I(
                                                className=(
                                                    "bi bi-question-circle "
                                                    "ms-2"
                                                ),
                                                id="tooltip-top-k",
                                                style={
                                                    "cursor": "pointer",
                                                    "fontSize": "0.85rem"
                                                }
                                            ),
                                            dbc.Tooltip(
                                                "Quantidade máxima de "
                                                "episódios retornados",
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
                                    ], md=6, className="mb-3"),
                                    
                                    # Similarity threshold control
                                    dbc.Col([
                                        html.Div([
                                            html.Label(
                                                "Confiabilidade mínima:",
                                                id="similarity-label",
                                                className="fw-bold d-inline",
                                                style={"fontSize": "0.9rem"}
                                            ),
                                            html.I(
                                                className=(
                                                    "bi bi-question-circle "
                                                    "ms-2"
                                                ),
                                                id="tooltip-similarity",
                                                style={
                                                    "cursor": "pointer",
                                                    "fontSize": "0.85rem"
                                                }
                                            ),
                                            dbc.Tooltip(
                                                "Quanto maior, mais preciso e "
                                                "restrito (menos resultados)",
                                                target="tooltip-similarity"
                                            )
                                        ]),
                                        dcc.Slider(
                                            id="similarity-threshold",
                                            min=0,
                                            max=1,
                                            step=0.05,
                                            value=0,
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
                                    ], md=6, className="mb-3")
                                ])
                            ])
                        ])
                    ], id="advanced-card")
                ], id="advanced-options", is_open=False, className="mb-3")
            ], md=8, className="mx-auto")
        ]),
            
        # Loading spinner (add spacing so it doesn't overlap advanced controls)
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    id="loading",
                    type="default",
                    children=html.Div(id="loading-output")
                )
            ], md=8, className="mx-auto")
        ], style={"marginTop": "1.25rem"}),
            
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
                        html.Div([
                            html.Img(
                                src="/ui/assets/images/podcast_finder_logo.png",
                                className="d-inline-block me-3",
                                style={"height": "50px", "width": "auto", "verticalAlign": "middle"}
                            ),
                            html.H1(
                                "Sobre o Podcast Finder",
                                className="d-inline-block",
                                style={"verticalAlign": "middle", "marginBottom": "0"}
                            )
                        ], style={"textAlign": "center", "marginTop": "20px", "marginBottom": "20px"}),
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
                            "Este projeto é uma ferramenta de busca semântica criada para fins ",
                            html.Strong("educacionais, técnicos e de demonstração"),
                            ". O desenvolvedor não possui, hospeda ou redistribui conteúdos de áudio de terceiros."
                        ], className="mb-3"),
                        html.P([
                            html.Strong("Todos os direitos autorais pertencem aos seus respectivos proprietários."),
                            " Esta aplicação não reivindica propriedade sobre o material indexado e respeita os direitos dos criadores e distribuidores originais."
                        ], className="mb-3"),
                        html.P([
                            "A aplicação apenas indexa e permite busca sobre transcrições e metadados gerados localmente para fins de pesquisa e referência. Nenhum arquivo de áudio completo é disponibilizado ou redistribuído por esta ferramenta. Os usuários devem respeitar os direitos autorais e os termos de uso do conteúdo original."
                        ], className="mb-3"),
                        html.P([
                            "Para acessar os episódios originais, por favor visite o site oficial do respectivo podcast ou use as plataformas de distribuição onde os episódios são publicados."
                        ], className="mb-0")
                    ])
                ], className="mb-4"),
                
                # Technical Section
                dbc.Card(id="technical-card", children=[
                    dbc.CardHeader(id="technical-header", children=html.H4("Como Funciona", className="mb-0")),
                    dbc.CardBody([
                        html.P([
                            "O Podcast Finder é uma aplicação de ",
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
                ,
                # Nova seção adicionada: Próximos passos
                dbc.Card(id="next-steps-card", children=[
                    dbc.CardHeader(children=html.H4("Próximos passos", className="mb-0")),
                    dbc.CardBody([
                        html.Ul([
                            html.Li("Abstração da camada de busca para suportar múltiplos backends (ex: interface VectorStore)"),
                            html.Li("Suporte opcional a banco vetorial dedicado para escalabilidade (ex: pgvector ou Qdrant)"),
                            html.Li("Implementação de cache de consultas para reduzir latência e custo computacional"),
                            html.Li("Automação da ingestão de novos episódios (ex: processamento via RSS)"),
                            html.Li("Adição de observabilidade básica (logs estruturados e métricas de busca)"),
                            html.Li("Containerização do ambiente com Docker para facilitar deploy e reprodução"),
                            html.Li("Experimentos futuros com geração de respostas resumidas (RAG)")
                        ], className="mb-0")
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
     State("feed-filter", "value"),
     State("program-filter", "value"),
     State("theme-store", "data")],
    prevent_initial_call=True
)
def search_podcasts(
    n_clicks, n_submit, query, top_k, similarity_threshold,
    feed_filter, program_filter, theme
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
    muted_color = "#adb5bd" if is_dark_mode else "#6c757d"
    
    logger.header("🔍 FRONTEND SEARCH REQUEST")
    logger.info(f"Query: '{query}'")
    logger.info(f"Top K: {top_k}")
    logger.info(f"Similarity Threshold: {similarity_threshold}")
    logger.info(f"Feed filter: {feed_filter if feed_filter else 'None'}")
    logger.info(f"Program filter: {program_filter if program_filter else 'None'}")
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
        # Call search service directly (avoids HTTP self-call deadlock with single worker)
        from backend.app.api.search import get_search_service
        logger.info(f"Query: '{query.strip()}', top_k={top_k}, feed={feed_filter}, program={program_filter}")

        service = get_search_service()
        results = service.search(
            query=query.strip(),
            top_k=top_k,
            podcast_source=feed_filter or None,
            program_name=program_filter or None,
            min_confidence=round(similarity_threshold, 2) if similarity_threshold and similarity_threshold > 0 else None,
        )
        logger.success(f"Received {len(results)} results from search service")
        
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
        
        # Note: Filtering by similarity_threshold is now done by the backend
        # when min_confidence parameter is provided
        filtered_results = results  # Use all results from backend (already filtered if threshold was set)
        
        logger.success(
            f"{len(filtered_results)} results after backend filtering"
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
            author = result.get('author') or result.get('program_name') or result.get('podcast_source') or None

            # If author/program_name is missing from backend response, fall back to local sqlite DB
            if not author:
                try:
                    import sqlite3
                    from pathlib import Path
                    db_path = Path(__file__).parents[1] / 'backend' / 'data' / 'nerdcasts.db'
                    if db_path.exists():
                        conn = sqlite3.connect(str(db_path))
                        cur = conn.cursor()
                        cur.execute('SELECT program_name, podcast_source FROM podcast_episodes WHERE filename = ?', (result.get('episode'),))
                        row = cur.fetchone()
                        if row:
                            prog, src = row
                            author = (prog.strip() if prog and prog.strip() else (src if src else None))
                        conn.close()
                except Exception:
                    pass
            
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
                    html.I(className="bi bi-mic-fill", style={"fontSize": "60px", "color": muted_color}),
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
                        html.I(className="bi bi-calendar3 me-2", style={"color": muted_color}),
                        html.Span(formatted_date, style={"fontSize": "0.85rem"})
                    ], className="mb-2"))
                except:
                    pass

            # Author/program name (show above date) - insert with fallback
            display_author = author if author else "Autor desconhecido"
            metadata_items.insert(0, html.Div([
                html.I(className="bi bi-person-circle me-2", style={"color": muted_color}),
                html.Span(display_author, style={"fontSize": "0.85rem", "fontWeight": "600"})
            ], className="mb-2"))
            
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
                    html.I(className="bi bi-clock me-2", style={"color": muted_color}),
                    html.Span(duration_str, style={"fontSize": "0.85rem"})
                ], className="mb-2"))
            
            if file_size_mb:
                metadata_items.append(html.Div([
                    html.I(className="bi bi-hdd me-2", style={"color": muted_color}),
                    html.Span(f"{file_size_mb:.1f} MB", style={"fontSize": "0.85rem"})
                ], className="mb-2"))
            
            # Determine if this is the top (first) result to highlight
            is_top_result = (i == 1)

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
                        # Visible left border; highlighted for top result
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
                        ], width=2, className="d-flex flex-column align-items-center",
                        style={"borderLeft": f"1px solid {info_border}", "paddingLeft": "12px"}
                        )
                    ], className="g-3")
                ], style={"padding": "1rem"})
            ], className=("mb-3 " + ("first-result" if is_top_result else "")), style={
                "backgroundColor": card_bg,
                "border": ("4px solid #66b2ff" if is_top_result and is_dark_mode else ("4px solid #0d6efd" if is_top_result else f"1px solid {info_border}")),
                # If top result, add a subtle box shadow as fallback
                **({"boxShadow": "0 6px 18px rgba(13,110,253,0.12)"} if is_top_result else {})
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
    logger.header("Starting Podcast Finder Frontend")
    logger.info("URL: http://127.0.0.1:8050")
    logger.info("Make sure the backend API is running on http://localhost:8005")
    app.run(debug=True, host="127.0.0.1", port=8050)
