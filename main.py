import threading
import time
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager  # IMPORTED THE MIDDLEMAN
from kivymd.uix.navigationdrawer import MDNavigationLayout, MDNavigationDrawer
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.button import MDRaisedButton, MDFillRoundFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
import socket
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
# CHANGE THIS LINE (Line 16)
from kivymd.uix.button import MDRaisedButton, MDFillRoundFlatButton, MDRoundFlatButton
class ChatApp(MDApp):
    def build(self):
        # Apply a sleek dark theme to make it look like a professional chat client
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Green"
        self.active_client = None
        self.server_running = False
        self.target_ip = "127.0.0.1"
        self.target_port = 5555
        # 1. The master Navigation Shell (Allows panels to slide over each other)
        nav_layout = MDNavigationLayout()

        # 2. FIXED: Create the Screen Manager wrapper that KivyMD demands
        screen_manager = MDScreenManager()

        # 3. The Main Screen Area Container (Header, Chat, and Input Bar)
        screen = MDScreen()
        main_box = MDBoxLayout(orientation='vertical')

        # Top Action Bar containing your Hamburger Menu Icon
        top_bar = MDTopAppBar(title="P2P Chat Beta 1.0")
        top_bar.anchor_title = "left"

        # Clicking this menu icon toggles the drawer panel open and shut!
        top_bar.left_action_items = [["menu", lambda x: self.nav_drawer.set_state("toggle")]]
        main_box.add_widget(top_bar)

        # Big central text display for your chat logs
        self.my_label = Label(text="Welcome to the P2P Chat Server", size_hint_y=0.8)
        main_box.add_widget(self.my_label)

        # Bottom row container for typing text and sending
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
        
        # FIXED: Add the screen to the manager, then add the manager to the master layout
        screen_manager.add_widget(screen)
        nav_layout.add_widget(screen_manager)

        # 4. The Slide-Out Left Menu Drawer
        self.nav_drawer = MDNavigationDrawer()
        self.nav_drawer.anchor = "left"

        drawer_box = MDBoxLayout(orientation='vertical', padding=10, spacing=15)

        # Menu Header Text
        drawer_box.add_widget(Label(text="P2P Chat Beta 1.0\nMenu", font_size='22sp', size_hint_y=None, height=60))

        # Your custom control buttons brought to life
        btn_start = MDFillRoundFlatButton(text="Start Server", md_bg_color=[0, 0.7, 0.3, 1], pos_hint={"center_x": .5})
        btn_start.bind(on_press=self.start_server_clicked) 

        btn_stop = MDFillRoundFlatButton(text="Stop Server", md_bg_color=[0.9, 0.1, 1], pos_hint={"center_x": .5})
        btn_stop.bind(on_press=self.stop_server_clicked)
        
        btn_view = MDRaisedButton(text="View Connections", pos_hint={"center_x": .5})

        btn_config = MDFillRoundFlatButton(text="Edit server config", md_bg_color=[0, 0.7, 0.3, 1], pos_hint={"center_x": .5})
        btn_config.bind(on_press=self.open_config_popup)

        drawer_box.add_widget(btn_start)
        drawer_box.add_widget(btn_stop)
        drawer_box.add_widget(btn_view)
        drawer_box.add_widget(btn_config)
        drawer_box.add_widget(Label()) # Empty space widget pushing buttons to the top

        self.nav_drawer.add_widget(drawer_box)
        nav_layout.add_widget(self.nav_drawer)

        return nav_layout
    
    # Functional code when "send" is pressed
    def send_message(self, instance):
        user_text = self.my_input.text
        if user_text.strip() != "":
            self.my_label.text += f"\nYou: {user_text}"
            
            # If an active client socket exists, push our data into it!
            if self.active_client:
                try:
                    # Text string must become raw data bytes (.encode()) to cross ports
                    self.active_client.sendall(f"Partner: {user_text}".encode('utf-8'))
                except Exception as e:
                    self.my_label.text += f"\n[System]: Lost connection: {str(e)}"
                    self.active_client = None

            self.my_input.text = ""
# NETWORKING LOGIC METHODS

    def start_server_clicked(self, instance):
        if not self.server_running:
            self.server_running = True
            self.my_label.text += "\n[System]: Starting server thread"

        # Spin up background worker thread so the UI stays butter smooth
            server_thread = threading.Thread(target=self.background_server_loop, daemon=True)
            server_thread.start()

        self.nav_drawer.set_state("close") # Close menu automatically

    def save_config_clicked(self, instance): # NEW!
        try: # NEW!
            self.target_ip = self.ip_input.text.strip() # NEW!
            self.target_port = int(self.port_input.text.strip()) # NEW!
            self.my_label.text += f"\n[System Config]: Saved Target -> {self.target_ip}:{self.target_port}" # NEW!
        except ValueError: # NEW!
            self.my_label.text += f"\n[System Error]: Invalid Port Number entered!" # NEW!
        
        self.config_popup.dismiss() # NEW! Close the modal box cleanly

    def test_connection_clicked(self, instance): # NEW!
        target_ip = self.ip_input.text.strip() # NEW!
        target_port = self.port_input.text.strip() # NEW!
        
        self.my_label.text += f"\n[Network Test]: Scanning {target_ip}:{target_port}..." # NEW!
        self.config_popup.dismiss() # NEW!
        
        # This thread keeps your interface from lagging while sockets scan ports
        tester_thread = threading.Thread( # NEW!
            target=self.background_network_scanner, # NEW!
            args=(target_ip, target_port), # NEW!
            daemon=True # NEW!
        ) # NEW!
        tester_thread.start() # NEW!

    def background_network_scanner(self, ip, port): # NEW!
        try: # NEW!
            port_num = int(port) # NEW!
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # NEW!
            test_socket.settimeout(3.0) # NEW! Drop connection if host doesn't respond in 3 seconds
            
            test_socket.connect((ip, port_num)) # NEW! Run handshake
            self.my_label.text += f"\n[Network Test SUCCESS]: {ip}:{port} is REACHABLE!" # NEW!
            test_socket.close() # NEW!
        except ValueError: # NEW!
            self.my_label.text += f"\n[Network Test ERROR]: Port must be a clean number!" # NEW!
        except Exception as e: # NEW!
            self.my_label.text += f"\n[Network Test FAILED]: Unable to reach {ip}:{port}. (Host Offline)" # NEW!
    def stop_server_clicked(self, instance):
        if self.server_running:
            self.server_running = False
            self.my_label.text += "\n[System]: Server Stopped."
            self.nav_drawer.set_state("close")

    def background_server_loop(self):
        # 1. Setup TCP Socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 2. Tell the OS to let us reclaim port 5555 instantly on restart
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            # 3. Bind to all local interfaces on port 5555 and listen
            server_socket.bind(("0.0.0.0", 5555))
            server_socket.listen(5)
            self.my_label.text += "\n[Server]: Online! Listening on port 5555"

            # 4. Set a 1-second timeout
            server_socket.settimeout(1.0)

            while self.server_running:
                try:
                    # System halts here waiting for a client connection packet
                    client_socket,client_address = server_socket.accept()
                    self.my_label.text += f"\n[Server]: Connected to {client_address[0]}!"

                    self.active_client = client_socket

                    #Set up background reader thread
                    client_thread = threading.Thread(
                        target=self.handle_client_messages,
                        args=(client_socket,),
                        daemon=True
                    )
                    client_thread.start()
                except socket.timeout:
                    # Nobody connected this second, loop back and check self.server_running
                    continue
        
        except Exception as e:
            self.my_label.text += f"\n[Server Error]: {str(e)}"
        finally:
            server_socket.close()
            self.my_label.text += "\n[Server]: Socket cleanly closed."

    def handle_client_messages(self, client_socket):
        while self.server_running:
            try:
                # Read up to 1024 bytes of incoming network packets
                data = client_socket.recv(1024)
                if not data:
                    break

                # Turn raw data bytes back into a readable string
                incoming_text = data.decode('utf-8')
                self.my_label.text += f"\n{incoming_text}"

            except Exception:
                break

        self.my_label.text += "\n[Server]: Client disconnected."
        if client_socket == self.active_client:
            self.active_client = None
        client_socket.close()

    def open_config_popup(self, instance):
        # 1. Main outer layout container for the popup inside
        popup_content = MDBoxLayout(orientation='vertical', padding=15, spacing=15)

        # 2. Grid layout for alignment [Label] [TextInput] [Button]
        grid = GridLayout(cols=3, spacing=10, size_hint_y=0.6)

        # Row 1: Port Configuration
        grid.add_widget(Label(text="Port", size_hint_x=0.2, font_size='18sp'))
        self.port_input = TextInput(text="5555", multiline=False, size_hint_x=0.5)
        set_port_btn = MDFillRoundFlatButton(text="Set", md_bg_color=[0, 0.7, 0.3, 1], size_hint_x=0.3)
        grid.add_widget(self.port_input)
        grid.add_widget(set_port_btn)

        # Row 2: IP Configuration
        grid.add_widget(Label(text="IP:", size_hint_x=0.2, font_size='18sp'))
        self.ip_input = TextInput(hint_text="192.168.x.x", multiline=False, size_hint_x=0.5)
        set_ip_btn = MDFillRoundFlatButton(text="Set", md_bg_color=[0, 0.7, 0.3, 1], size_hint_x=0.3)
        grid.add_widget(self.ip_input)
        grid.add_widget(set_ip_btn)

        popup_content.add_widget(grid)

        # 3. Bottom Action Row Container (Primary Green vs Secondary Purple Outline)
        btn_row = MDBoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.4)
        
        save_btn = MDFillRoundFlatButton(text="Save Config", md_bg_color=[0, 0.7, 0.3, 1], size_hint_x=0.5)
        save_btn.bind(on_press=self.save_config_clicked)
        
        test_btn = MDRoundFlatButton(
            text="Test",
            theme_text_color="Custom",
            text_color=[0.9, 0.1, 1, 1],
            line_color=[0.9, 0.1, 1, 1],
            size_hint_x=0.5
        )
        test_btn.bind(on_press=self.test_connection_clicked)
        
        btn_row.add_widget(save_btn)
        btn_row.add_widget(test_btn)
        popup_content.add_widget(btn_row)

        # 4. Generate and open the master window overlay
        self.config_popup = Popup(
            title="Editing Target Server Configuration",
            content=popup_content,
            size_hint=(0.85, 0.55),
            background_color=[0.12, 0.12, 0.12, 1]
        )

        self.config_popup.open()
        self.nav_drawer.set_state("close")
        



if __name__ == "__main__":
    ChatApp().run()