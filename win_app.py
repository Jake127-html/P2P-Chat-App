import threading
import socket
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.navigationdrawer import MDNavigationLayout, MDNavigationDrawer
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.button import MDRaisedButton, MDFillRoundFlatButton, MDRoundFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.clock import mainthread

class ChatApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Green"
        
        # Stream Trackers
        self.active_client = None      # Inbound connection handle
        self.outbound_socket = None    # Outbound connection handle
        self.server_running = False
        self.listen_to_partner_active = False
        
        # Default fallback configurations
        self.target_ip = "192.168.1.139"  # Adjust to match destination network node
        self.target_port = 5555

        nav_layout = MDNavigationLayout()
        screen_manager = MDScreenManager()
        screen = MDScreen()
        main_box = MDBoxLayout(orientation='vertical')

        top_bar = MDTopAppBar(title="P2P Desktop Chat 1.0")
        top_bar.anchor_title = "left"
        top_bar.left_action_items = [["menu", lambda x: self.nav_drawer.set_state("toggle")]]
        main_box.add_widget(top_bar)

        self.my_label = Label(text="Welcome to the P2P Chat Client", size_hint_y=0.8, halign="left", valign="bottom")
        self.my_label.bind(size=self.my_label.setter('text_size'))
        main_box.add_widget(self.my_label)

        bottom_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5)
        self.my_input = TextInput(
            multiline=False,
            hint_text="Type your message...",
            background_color=[0.15, 0.15, 0.15, 1],
            foreground_color=[1, 1, 1, 1]
        )
        send_butn = Button(text="Send", size_hint_x=None, width=80)
        send_butn.bind(on_press=self.send_message)

        bottom_layout.add_widget(self.my_input)
        bottom_layout.add_widget(send_butn)
        main_box.add_widget(bottom_layout)

        screen.add_widget(main_box)
        screen_manager.add_widget(screen)
        nav_layout.add_widget(screen_manager)

        self.nav_drawer = MDNavigationDrawer()
        self.nav_drawer.anchor = "left"
        drawer_box = MDBoxLayout(orientation='vertical', padding=10, spacing=15)
        drawer_box.add_widget(Label(text="P2P Desktop Menu", font_size='22sp', size_hint_y=None, height=60))

        btn_start = MDFillRoundFlatButton(text="Start Server", md_bg_color=[0, 0.7, 0.3, 1], pos_hint={"center_x": .5})
        btn_start.bind(on_press=self.start_server_clicked) 

        btn_stop = MDFillRoundFlatButton(text="Stop Server", md_bg_color=[0.9, 0.1, 1], pos_hint={"center_x": .5})
        btn_stop.bind(on_press=self.stop_server_clicked)
        
        btn_config = MDFillRoundFlatButton(text="Edit Server Config", md_bg_color=[0, 0.7, 0.3, 1], pos_hint={"center_x": .5})
        btn_config.bind(on_press=self.open_config_popup)

        drawer_box.add_widget(btn_start)
        drawer_box.add_widget(btn_stop)
        drawer_box.add_widget(btn_config)
        drawer_box.add_widget(Label())

        self.nav_drawer.add_widget(drawer_box)
        nav_layout.add_widget(self.nav_drawer)
        return nav_layout
    
    @mainthread
    def update_ui_log(self, text):
        """Thread-safe worker function to touch GUI main panel safely."""
        self.my_label.text += f"\n{text}"

    def send_message(self, instance):
        user_text = self.my_input.text.strip()
        if user_text != "":
            self.update_ui_log(f"You: {user_text}")
            
            def handle_send():
                # Direct Handoff Option 1: Are we running as a client connected out?
                if self.outbound_socket:
                    try:
                        self.outbound_socket.sendall(f"Partner: {user_text}".encode('utf-8'))
                        return
                    except Exception:
                        self.close_outbound()
                
                # Direct Handoff Option 2: Do we have an active server connection?
                if self.active_client:
                    try:
                        self.active_client.sendall(f"Partner: {user_text}".encode('utf-8'))
                        return
                    except Exception as e:
                        self.update_ui_log(f"[System]: Lost connection: {str(e)}")
                        self.active_client = None
                else:
                    self.update_ui_log("[System Alert]: Message dropped. No active network connections.")

            threading.Thread(target=handle_send, daemon=True).start()
            self.my_input.text = ""

    def start_server_clicked(self, instance):
        if not self.server_running:
            self.server_running = True
            self.update_ui_log("[System]: Starting local background server socket...")
            threading.Thread(target=self.background_server_loop, daemon=True).start()
        self.nav_drawer.set_state("close")

    def stop_server_clicked(self, instance):
        if self.server_running:
            self.server_running = False
            self.update_ui_log("[System]: Server stopped.")
            if self.active_client:
                self.active_client.close()
                self.active_client = None
        self.close_outbound()
        self.nav_drawer.set_state("close")

    def background_server_loop(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server_socket.bind(("0.0.0.0", 5556))
            server_socket.listen(5)
            self.update_ui_log("[Server Engine]: Live & Listening on port 5555")
            server_socket.settimeout(1.0)

            while self.server_running:
                try:
                    client_socket, client_address = server_socket.accept()
                    self.update_ui_log(f"[Server Engine]: Connected to phone client at {client_address[0]}!")
                    self.active_client = client_socket
                    threading.Thread(target=self.handle_incoming_stream, args=(client_socket,), daemon=True).start()
                except socket.timeout:
                    continue
        except Exception as e:
            self.update_ui_log(f"[Server Error]: {str(e)}")
        finally:
            server_socket.close()

    def handle_incoming_stream(self, sock):
        """Reads stream bytes continually from whatever device connects to us."""
        while True:
            try:
                data = sock.recv(1024)
                if not data:
                    break
                self.update_ui_log(data.decode('utf-8').strip())
            except Exception:
                break
        self.update_ui_log("[Network]: Partner disconnected.")
        sock.close()

    def connect_outbound_clicked(self, instance):
        """Triggers outbound dial to connect directly to your mobile device's IP."""
        try:
            self.target_ip = self.ip_input.text.strip()
            self.target_port = int(self.port_input.text.strip())
        except ValueError:
            self.update_ui_log("[Config Error]: Invalid Port Syntax")
            return
        self.config_popup.dismiss()
        self.close_outbound()
        
        def run_dial():
            try:
                self.update_ui_log(f"[Client Engine]: Dialing remote target at {self.target_ip}:{self.target_port}...")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(4.0)
                sock.connect((self.target_ip, self.target_port))
                sock.settimeout(None)
                self.outbound_socket = sock
                self.update_ui_log("[Client Engine]: Connected & Synchronized with phone!")
                
                self.listen_to_partner_active = True
                threading.Thread(target=self.handle_incoming_stream, args=(sock,), daemon=True).start()
            except Exception as e:
                self.update_ui_log(f"[Client Failure]: {str(e)}")
        
        threading.Thread(target=run_dial, daemon=True).start()

    def save_config_clicked(self, instance):
        try:
            self.target_ip = self.ip_input.text.strip()
            self.target_port = int(self.port_input.text.strip())
            self.update_ui_log(f"[Config Updated]: Saved tracking parameters -> {self.target_ip}:{self.target_port}")
        except ValueError:
            self.update_ui_log("[Config Error]: Invalid Port Number syntax.")
        self.config_popup.dismiss()

    def close_outbound(self):
        self.listen_to_partner_active = False
        if self.outbound_socket:
            try: self.outbound_socket.close()
            except Exception: pass
            self.outbound_socket = None

    def open_config_popup(self, instance):
        popup_content = MDBoxLayout(orientation='vertical', padding=15, spacing=15)
        grid = GridLayout(cols=2, spacing=10, size_hint_y=0.6)

        grid.add_widget(Label(text="Port:", size_hint_x=0.3, font_size='18sp'))
        self.port_input = TextInput(text=str(self.target_port), multiline=False)
        grid.add_widget(self.port_input)

        grid.add_widget(Label(text="Target IP:", size_hint_x=0.3, font_size='18sp'))
        self.ip_input = TextInput(text=self.target_ip, multiline=False)
        grid.add_widget(self.ip_input)

        popup_content.add_widget(grid)

        btn_row = MDBoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.4)
        save_btn = MDFillRoundFlatButton(text="Save Config", md_bg_color=[0, 0.7, 0.3, 1], size_hint_x=0.5)
        save_btn.bind(on_press=self.save_config_clicked)
        
        connect_btn = MDRoundFlatButton(
            text="Connect to Phone",
            theme_text_color="Custom",
            text_color=[0.9, 0.1, 1, 1],
            line_color=[0.9, 0.1, 1, 1],
            size_hint_x=0.5
        )
        connect_btn.bind(on_press=self.connect_outbound_clicked)
        
        btn_row.add_widget(save_btn)
        btn_row.add_widget(connect_btn)
        popup_content.add_widget(btn_row)

        self.config_popup = Popup(
            title="P2P Node Parameters",
            content=popup_content,
            size_hint=(0.85, 0.55),
            background_color=[0.12, 0.12, 0.12, 1]
        )
        self.config_popup.open()
        self.nav_drawer.set_state("close")

if __name__ == "__main__":
    ChatApp().run()