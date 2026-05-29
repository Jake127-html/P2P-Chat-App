import threading
import socket

from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.clock import mainthread

from kivymd.app import MDApp
from kivymd.uix.appbar import (
    MDTopAppBar,
    MDTopAppBarLeadingButtonContainer,
    MDActionTopAppBarButton,
    MDTopAppBarTitle,
)
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.navigationdrawer import MDNavigationDrawer, MDNavigationLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.button import MDButton, MDButtonText


class ChatApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Green"

        self.outbound_socket = None     
        self.target_ip = "192.168.1.139"
        self.target_port = 5556

        nav_layout = MDNavigationLayout()
        screen_manager = MDScreenManager()
        screen = MDScreen(name="main")
        main_box = MDBoxLayout(orientation="vertical")

        # ── Drawer ────────────────────────────────────────────────────────────
        self.nav_drawer = MDNavigationDrawer(radius=(0, 16, 16, 0))
        drawer_box = MDBoxLayout(orientation="vertical", padding=10, spacing=15)
        drawer_box.add_widget(Label(text="P2P Client v1.0", font_size="20sp", size_hint_y=None, height=50))
        
        btn_connect = MDButton(MDButtonText(text="Connect to PC"), style="filled", theme_bg_color="Custom", md_bg_color=[0, 0.7, 0.3, 1], pos_hint={"center_x": 0.5})
        btn_connect.bind(on_release=lambda *args: self.connect_to_pc_backend())
        
        btn_config = MDButton(MDButtonText(text="Edit IP/Port"), style="outlined", pos_hint={"center_x": 0.5})
        btn_config.bind(on_release=self.open_config_popup)

        drawer_box.add_widget(btn_connect); drawer_box.add_widget(btn_config)
        self.nav_drawer.add_widget(drawer_box)

        # ── Top bar ──────────────────────────────────────────────────────────
        top_bar = MDTopAppBar(
            MDTopAppBarLeadingButtonContainer(MDActionTopAppBarButton(icon="menu", on_release=lambda *args: self.nav_drawer.set_state("toggle"))),
            MDTopAppBarTitle(text="P2P Client"),
            type="small", theme_bg_color="Custom", md_bg_color=[0, 0.45, 0.22, 1]
        )
        main_box.add_widget(top_bar)

        # ── Chat log ─────────────────────────────────────────────────────────
        scroll = ScrollView(size_hint=(1, 0.9))
        self.my_label = Label(text="Click 'Connect' to begin.", size_hint_y=None, valign="top", halign="left", markup=True, padding=(8, 8))
        self.my_label.bind(texture_size=self._update_label_height, width=lambda *_: setattr(self.my_label, "text_size", (self.my_label.width, None)))
        scroll.add_widget(self.my_label)
        self._scroll_view = scroll
        main_box.add_widget(scroll)

        # ── Input ────────────────────────────────────────────────────────────
        bottom_layout = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=100, padding=[10, 10])
        self.my_input = TextInput(multiline=False, hint_text="Message...")
        self.my_input.bind(on_text_validate=self.send_message)
        send_butn = Button(text="Send", size_hint_x=None, width=80)
        send_butn.bind(on_press=self.send_message)
        bottom_layout.add_widget(self.my_input); bottom_layout.add_widget(send_butn)
        main_box.add_widget(bottom_layout)

        screen.add_widget(main_box); screen_manager.add_widget(screen); nav_layout.add_widget(screen_manager); nav_layout.add_widget(self.nav_drawer)
        return nav_layout

    def _update_label_height(self, instance, value):
        instance.height = max(value[1], self._scroll_view.height)
        self._scroll_view.scroll_y = 0

    @mainthread
    def update_ui_log(self, text):
        self.my_label.text += f"\n{text}"

    # ── Client Only Connection ──────────────────────────────────────────────
    def connect_to_pc_backend(self):
        if self.outbound_socket:
            self.update_ui_log("[Client]: Already connected.")
            return
        
        def _connect():
            try:
                self.update_ui_log(f"[Client]: Connecting to {self.target_ip}:{self.target_port}...")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.target_ip, self.target_port))
                self.outbound_socket = sock
                self.update_ui_log("[Client]: Connected!")
                
                while True:
                    data = sock.recv(4096)
                    if not data: break
                    self.update_ui_log(data.decode("utf-8").strip())
            except Exception as e:
                self.update_ui_log(f"[Error]: {e}")
            finally:
                self.outbound_socket = None
                self.update_ui_log("[Client]: Disconnected.")

        threading.Thread(target=_connect, daemon=True).start()
        self.nav_drawer.set_state("close")

    def send_message(self, *args):
        user_text = self.my_input.text.strip()
        if not user_text or not self.outbound_socket: return
        try:
            self.outbound_socket.sendall((user_text + "\n").encode("utf-8"))
            self.update_ui_log(f"[You]: {user_text}")
            self.my_input.text = ""
        except: self.outbound_socket = None

    # ── Config Popup ────────────────────────────────────────────────────────
    def open_config_popup(self, *args):
        popup_content = MDBoxLayout(orientation="vertical", padding=15, spacing=15)
        grid = GridLayout(cols=2, spacing=10, size_hint_y=0.6)
        
        grid.add_widget(Label(text="IP:", font_size="18sp"))
        self.ip_input = TextInput(text=self.target_ip, multiline=False)
        grid.add_widget(self.ip_input)

        grid.add_widget(Label(text="Port:", font_size="18sp"))
        self.port_input = TextInput(text=str(self.target_port), multiline=False)
        grid.add_widget(self.port_input)
        
        popup_content.add_widget(grid)

        btn_row = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=0.2)
        
        back_btn = MDButton(MDButtonText(text="Back"), style="outlined", size_hint_x=0.3)
        back_btn.bind(on_release=lambda x: self.config_popup.dismiss())
        
        save_btn = MDButton(MDButtonText(text="Save"), style="filled", theme_bg_color="Custom", md_bg_color=[0, 0.7, 0.3, 1], size_hint_x=0.35)
        save_btn.bind(on_release=self.save_config)
        
        connect_btn = MDButton(MDButtonText(text="Connect"), style="outlined", size_hint_x=0.35)
        connect_btn.bind(on_release=self.persistent_connect_clicked)
        
        btn_row.add_widget(back_btn); btn_row.add_widget(save_btn); btn_row.add_widget(connect_btn)
        popup_content.add_widget(btn_row)
        
        self.config_popup = Popup(title="Server Config", content=popup_content, size_hint=(0.9, 0.45))
        self.config_popup.open()

    def save_config(self, *args):
        self.target_ip = self.ip_input.text.strip()
        self.target_port = int(self.port_input.text.strip())
        if self.outbound_socket: self.outbound_socket.close()
        self.config_popup.dismiss()
        
    def persistent_connect_clicked(self, *args):
        self.save_config()
        self.connect_to_pc_backend()

if __name__ == "__main__":
    ChatApp().run()
