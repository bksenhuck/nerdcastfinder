"""
Nerdcast Finder - Frontend Dash Application

A minimal search interface for finding podcast episodes using semantic search.
"""
import requests
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc

# Configuration
BACKEND_URL = "http://localhost:8000/api/search"

# Initialize Dash app with Bootstrap theme
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Nerdcast Finder"
)

# Layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("🎙️ Nerdcast Finder", className="text-center my-4"),
            html.P(
                "Search podcast episodes using semantic search",
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
                    placeholder="Enter your search query...",
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
            ], className="mb-4")
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
        ])
    ]),
    
    # Results
    dbc.Row([
        dbc.Col([
            html.Div(id="results-container")
        ], md=10, className="mx-auto")
    ]),
    
    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P(
                "Powered by FastAPI, FAISS, and sentence-transformers",
                className="text-center text-muted small"
            )
        ])
    ])
], fluid=True, className="py-4")


@app.callback(
    [Output("results-container", "children"),
     Output("loading-output", "children")],
    [Input("search-button", "n_clicks"),
     Input("search-input", "n_submit")],
    [State("search-input", "value")],
    prevent_initial_call=True
)
def search_podcasts(n_clicks, n_submit, query):
    """
    Handle search button click or Enter key press
    
    Args:
        n_clicks: Number of times search button was clicked
        n_submit: Number of times Enter was pressed in input
        query: Search query string
    
    Returns:
        Tuple of (results HTML, loading indicator)
    """
    if not query or query.strip() == "":
        return html.Div(
            dbc.Alert("Please enter a search query", color="warning"),
            className="mt-4"
        ), ""
    
    try:
        # Call backend API
        response = requests.get(
            BACKEND_URL,
            params={"q": query.strip(), "top_k": 10},
            timeout=30
        )
        
        if response.status_code != 200:
            return html.Div(
                dbc.Alert(
                    f"Error: {response.status_code} - {response.text}",
                    color="danger"
                ),
                className="mt-4"
            ), ""
        
        results = response.json()
        
        if not results:
            return html.Div(
                dbc.Alert("No results found", color="info"),
                className="mt-4"
            ), ""
        
        # Build results cards
        cards = []
        for i, result in enumerate(results, 1):
            card = dbc.Card([
                dbc.CardBody([
                    html.H5(
                        f"🎧 {result['episode']}",
                        className="card-title"
                    ),
                    html.P(
                         result['excerpt'],
                        className="card-text"
                    ),
                    html.Small(
                        f"Similarity Score: {result['score']:.4f}",
                        className="text-muted"
                    )
                ])
            ], className="mb-3")
            cards.append(card)
        
        return html.Div([
            html.H4(f"Found {len(results)} results", className="mb-3"),
            html.Div(cards)
        ]), ""
    
    except requests.exceptions.ConnectionError:
        return html.Div(
            dbc.Alert(
                "Cannot connect to backend. Make sure the API server is running on port 8000.",
                color="danger"
            ),
            className="mt-4"
        ), ""
    
    except requests.exceptions.Timeout:
        return html.Div(
            dbc.Alert("Request timed out. Please try again.", color="warning"),
            className="mt-4"
        ), ""
    
    except Exception as e:
        return html.Div(
            dbc.Alert(f"An error occurred: {str(e)}", color="danger"),
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
