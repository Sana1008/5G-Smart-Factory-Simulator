from dash import Dash

from dashboard.callbacks import register_callbacks
from dashboard.layout import create_layout


app = Dash(__name__)
app.title = "FactoryNet 5G Simulator"
app.layout = create_layout()

register_callbacks(app)

server = app.server


if __name__ == "__main__":
    app.run(debug=True)