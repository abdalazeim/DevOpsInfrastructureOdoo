from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Static, Button, DataTable, ProgressBar, Label
from app.core.infrastructure_orchestrator import InfrastructureManager
import logging

class OdooManagerUI(App):
    """Professional Terminal UI for Odoo Infrastructure Manager."""
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("System Overview", classes="panel"),
            DataTable(),
            ProgressBar(total=100, id="progress"),
            Button("Run Health Check", id="health-check"),
            classes="main-container"
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "health-check":
            self.query_one("#progress").update(progress=50)
            # Call Orchestrator here

if __name__ == "__main__":
    app = OdooManagerUI()
    app.run()
