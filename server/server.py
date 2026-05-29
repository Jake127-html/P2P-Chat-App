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

        self.active_clients = []        
        self.outbound_socket = None     
        self.server_running = False
        self.listen_to_pc_active = False

        self.target_ip = "192.168.1.139"
        self.target_port = 5556

        # ── Root layout ──────────────────────────────────────────────────────
        nav_layout = MDNavigationLayout()
        screen_manager = MDScreenManager()
        screen = MDScreen(name="main")
        main_box = MDBoxLayout(orientation="vertical")

        # ── Navigation drawer ─────────────────────────────────────────────────
        self.nav_drawer = MDNavigationDrawer(radius=(0, 16, 16, 0))
        self.nav_drawer.anchor = "left"

        drawer_box = MDBoxLayout(orientation="vertical", padding=10, spacing=15)
        drawer_box.add_widget(Label(text="P2P Chat Beta 1.0\nMenu", font_size="22sp", size_hint_y=None, height=60))

        btn_start = MDButton(MDButtonText(text="Start Server"), style="filled", theme_bg_color="Custom", md_bg_color=[0, 0.7, 0.3, 1], pos_hint={"center_x": 0.5})
        btn_start.bind(on_release=self.start_server_clicked)

        btn_stop = MDButton(MDButtonText(text="Stop Server"), style="filled", theme_bg_color="Custom", md_bg_color=[0.8, 0.1, 0.8, 1], pos_hint={"center_x": 0.5})
        btn_stop.bind(on_release=self.stop_server_clicked)

        btn_config = MDButton(MDButtonText(text="Edit Server Config"), style="filled", theme_bg_color="Custom", md_bg_color=[0, 0.7, 0.3, 1], pos_hint={"center_x": 0.5})
        btn_config.bind(on_release=self.open_config_popup)

        drawer_box.add_widget(btn_start); drawer_box.add_widget(btn_stop); drawer_box.add_widget(btn_config)
        self.nav_drawer.add_widget(drawer_box)

        # ── Top bar ──────────────────────────────────────────────────────────
        top_bar = MDTopAppBar(
            MDTopAppBarLeadingButtonContainer(MDActionTopAppBarButton(icon="menu", on_release=lambda *args: self.nav_drawer.set_state("toggle"))),
            MDTopAppBarTitle(text="P2P Chat Beta 1.0"),
            type="small", theme_bg_color="Custom", md_bg_color=[0, 0.45, 0.22, 1]
        )
        main_box.add_widget(top_bar)

        # ── Chat log ─────────────────────────────────────────────────────────
        scroll = ScrollView(size_hint=(1, 0.85))
        self.my_label = Label(text="Welcome to the P2P Chat Server", size_hint_y=None, valign="top", halign="left", markup=True, padding=(8, 8))
        self.my_label.bind(texture_size=self._update_label_height)
        self.my_label.bind(width=lambda *_: setattr(self.my_label, "text_size", (self.my_label.width, None)))
        scroll.add_widget(self.my_label)
        self._scroll_view = scroll
        main_box.add_widget(scroll)

        # ── Input ────────────────────────────────────────────────────────────
        bottom_layout = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=48, spacing=5, padding=[5, 4])
        self.my_input = TextInput(multiline=False, hint_text="Type your message...", background_color=[0.15, 0.15, 0.15, 1], foreground_color=[1, 1, 1, 1])
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

    # ── Outbound Client Logic ───────────────────────────────────────────────
    def connect_to_pc_backend(self):
        try:
            if self.outbound_socket is None:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((self.target_ip, self.target_port))
                sock.settimeout(None)
                self.outbound_socket = sock
                self.listen_to_pc_active = True
                threading.Thread(target=self.handle_server_replies, args=(sock,), daemon=True).start()
            return True
        except Exception:
            return False

    def handle_server_replies(self, sock):
        while self.listen_to_pc_active:
            try:
                data = sock.recv(4096)
                if not data: break
                # SILENCE ECHOS: Only log if it's NOT a formatted message (formatted come from server loop)
                msg = data.decode("utf-8").strip()
                if msg and not (msg.startswith("[") and "]:" in msg):
                    self.update_ui_log(msg)
            except Exception: break
        self.outbound_socket = None

    def close_outbound(self):
        self.listen_to_pc_active = False
        if self.outbound_socket:
            try: self.outbound_socket.close()
            except: pass
            self.outbound_socket = None

    def send_message(self, *args):
        user_text = self.my_input.text.strip()
        if not user_text: return
        self.update_ui_log(f"[You]: {user_text}")
        self.my_input.text = ""
        def _send():
            if self.outbound_socket is None:
                if not self.connect_to_pc_backend(): return
            try: self.outbound_socket.sendall((user_text + "\n").encode("utf-8"))
            except: self.outbound_socket = None
        threading.Thread(target=_send, daemon=True).start()

    # ── Inbound Server Logic ────────────────────────────────────────────────
    def start_server_clicked(self, *args):
        if not self.server_running:
            self.server_running = True
            self.update_ui_log("[System]: Starting server…")
            threading.Thread(target=self.background_server_loop, daemon=True).start()
        self.nav_drawer.set_state("close")

    def stop_server_clicked(self, *args):
        if self.server_running:
            self.server_running = False
            self.update_ui_log("[System]: Server stopped.")
            for c in list(self.active_clients):
                try: c.close()
                except: pass
            self.active_clients.clear()
            self.close_outbound()
        self.nav_drawer.set_state("close")

    def background_server_loop(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", self.target_port))
            s.listen()
            self.update_ui_log(f"[Server]: Listening on port {self.target_port}...")
            s.settimeout(1.0)
            while self.server_running:
                try:
                    conn, addr = s.accept()
                    self.active_clients.append(conn)
                    threading.Thread(target=self.handle_coms_stream, args=(conn, addr), daemon=True).start()
                except socket.timeout: continue
        except Exception as e: self.update_ui_log(f"[Server Error]: {e}")
        finally: s.close()

    def handle_coms_stream(self, conn, addr):
        while self.server_running:
            try:
                data = conn.recv(1024)
                if not data: break
                message = data.decode(encoding="utf-8").strip()
                # If message is from an external device (Phone), log it once
                if addr[0] != "127.0.0.1" and addr[0] != self.target_ip:
                    formatted_msg = f"[{addr[0]}]: {message}"
                    self.update_ui_log(formatted_msg)
                    self._broadcast(formatted_msg.encode('utf-8'), sender=conn)
                else:
                    # Message is from this PC, just broadcast to phones
                    self._broadcast(message.encode('utf-8'), sender=conn)
            except: break
        if conn in self.active_clients: self.active_clients.remove(conn)
        conn.close()

    def _broadcast(self, data, sender=None):
        for c in list(self.active_clients):
            if c is sender: continue
            try:
                # Stop broadcasting back to the local PC UI client
                try:
                    peer = c.getpeername()
                    if peer[0] == "127.0.0.1" or peer[0] == self.target_ip: continue
                except: pass
                c.sendall(data)
            except:
                if c in self.active_clients: self.active_clients.remove(c)

    # ── Config ──────────────────────────────────────────────────────────────
    def open_config_popup(self, *args):
        popup_content = MDBoxLayout(orientation="vertical", padding=15, spacing=15)
        grid = GridLayout(cols=2, spacing=10, size_hint_y=0.6)
        grid.add_widget(Label(text="IP:")); self.ip_input = TextInput(text=self.target_ip, multiline=False); grid.add_widget(self.ip_input)
        grid.add_widget(Label(text="Port:")); self.port_input = TextInput(text=str(self.target_port), multiline=False); grid.add_widget(self.port_input)
        popup_content.add_widget(grid)
        
        btn_row = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=0.4)
        
        # FIXED: Added *args to lambda to swallow the touch event passed by Kivy
        back_btn = MDButton(MDButtonText(text="Back"), style="outlined", size_hint_x=0.33)
        back_btn.bind(on_release=lambda *args: self.config_popup.dismiss())
        
        save_btn = MDButton(MDButtonText(text="Save"), style="filled", theme_bg_color="Custom", md_bg_color=[0, 0.7, 0.3, 1], size_hint_x=0.33)
        save_btn.bind(on_release=self.save_config_clicked)
        
        connect_btn = MDButton(MDButtonText(text="Connect"), style="outlined", size_hint_x=0.33)
        connect_btn.bind(on_release=self.persistent_connect_clicked)
        
        btn_row.add_widget(back_btn); btn_row.add_widget(save_btn); btn_row.add_widget(connect_btn)
        popup_content.add_widget(btn_row)
        
        self.config_popup = Popup(title="Server Config", content=popup_content, size_hint=(0.85, 0.50))
        self.config_popup.open(); self.nav_drawer.set_state("close")

    def save_config_clicked(self, *args):
        try:
            self.target_ip = self.ip_input.text.strip()
            self.target_port = int(self.port_input.text.strip())
            self.update_ui_log(f"[Config]: Target set to {self.target_ip}:{self.target_port}")
            self.close_outbound()
        except: pass
        self.config_popup.dismiss()

    def persistent_connect_clicked(self, *args):
        self.save_config_clicked()
        threading.Thread(target=self.connect_to_pc_backend, daemon=True).start()

if __name__ == "__main__":
    ChatApp().run()