from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Checkbox
from textual.reactive import Reactive
from rich.text import Text


class CustomCheckbox(Checkbox):
    checked_icon: Reactive[str] = Reactive("✔")  # Customize checked symbol here
    unchecked_icon: Reactive[str] = Reactive(" ")  # Blank space for unchecked state

    def render(self) -> Text:
        # Modify the rendering to use the custom checked symbol
        icon = self.checked_icon if self.value else self.unchecked_icon
        return Text(f"[{icon}] {self.label}", justify="left")


class CheckboxApp(App[None]):
    CSS = """
    Screen {
        align: center middle;
    }

    VerticalScroll {
        width: auto;
        height: auto;
        background: $boost;
        padding: 2;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield CustomCheckbox("Arrakis :sweat:")
            yield CustomCheckbox("Caladan")
            yield CustomCheckbox("Chusuk")
            yield CustomCheckbox("[b]Giedi Prime[/b]")
            yield CustomCheckbox("[magenta]Ginaz[/]")
            yield CustomCheckbox("Grumman", True)
            yield CustomCheckbox("Kaitain", id="initial_focus")
            yield CustomCheckbox("Novebruns", True)

    def on_mount(self):
        self.query_one("#initial_focus", Checkbox).focus()

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        checkbox = event.checkbox
        self.log(f"Checkbox '{checkbox.label}' changed to {'checked' if checkbox.value else 'unchecked'}")


if __name__ == "__main__":
    CheckboxApp().run()
