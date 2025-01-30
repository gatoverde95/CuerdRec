import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GdkPixbuf
import subprocess
import os
import threading
import time
import platform
import signal
from datetime import datetime

# Set GDK_BACKEND environment variable
os.environ['GDK_BACKEND'] = 'x11'

class AudioRecorder(Gtk.Window):
    def __init__(self):
        super().__init__(title="CuerdRec")
        self.set_default_size(600, 400)
        
        script_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(script_dir, "/usr/share/cuerdrec/icons/rec.svg")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

        self.recording = False
        self.paused = False
        self.ffmpeg_process = None
        self.output_file = None
        self.start_time = None
        self.recording_thread = None

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        # Create the menu bar
        menubar = Gtk.MenuBar()
        vbox.pack_start(menubar, False, False, 0)

        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label="Archivo")
        file_item.set_submenu(file_menu)
        menubar.append(file_item)

        about_menu = Gtk.Menu()
        about_item = Gtk.MenuItem(label="Acerca de")
        about_item.set_submenu(about_menu)
        menubar.append(about_item)

        quit_item = Gtk.MenuItem(label="Salir")
        quit_item.connect("activate", Gtk.main_quit)
        file_menu.append(quit_item)

        about_dialog_item = Gtk.MenuItem(label="Acerca de")
        about_dialog_item.connect("activate", self.show_about_dialog)
        about_menu.append(about_dialog_item)

        notebook = Gtk.Notebook()
        vbox.pack_start(notebook, True, True, 0)

        # Tab for recording controls
        recording_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        notebook.append_page(recording_tab, Gtk.Label(label="Grabación"))

        hbox = Gtk.Box(spacing=6)
        recording_tab.pack_start(hbox, False, False, 0)

        self.record_button = Gtk.Button()
        self.record_button.set_image(Gtk.Image.new_from_icon_name("media-record", Gtk.IconSize.BUTTON))
        self.record_button.set_tooltip_text("Iniciar Grabación")
        self.record_button.connect("clicked", self.on_record_button_clicked)
        hbox.pack_start(self.record_button, True, True, 0)

        self.pause_button = Gtk.Button()
        self.pause_button.set_image(Gtk.Image.new_from_icon_name("media-playback-pause", Gtk.IconSize.BUTTON))
        self.pause_button.set_tooltip_text("Pausar Grabación")
        self.pause_button.connect("clicked", self.on_pause_button_clicked)
        self.pause_button.set_sensitive(False)
        hbox.pack_start(self.pause_button, True, True, 0)

        self.stop_button = Gtk.Button()
        self.stop_button.set_image(Gtk.Image.new_from_icon_name("media-playback-stop", Gtk.IconSize.BUTTON))
        self.stop_button.set_tooltip_text("Detener Grabación")
        self.stop_button.connect("clicked", self.on_stop_button_clicked)
        self.stop_button.set_sensitive(False)
        hbox.pack_start(self.stop_button, True, True, 0)

        self.play_button = Gtk.Button()
        self.play_button.set_image(Gtk.Image.new_from_icon_name("media-playback-start", Gtk.IconSize.BUTTON))
        self.play_button.set_tooltip_text("Reproducir Grabación")
        self.play_button.connect("clicked", self.on_play_button_clicked)
        self.play_button.set_sensitive(False)
        hbox.pack_start(self.play_button, True, True, 0)

        self.time_label = Gtk.Label(label="Presione Grabar para empezar")
        self.time_label.set_markup('<span font="20">Presione Grabar para empezar</span>')
        recording_tab.pack_start(self.time_label, False, False, 0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        recording_tab.pack_start(scrolled_window, True, True, 0)

        self.recording_list_store = Gtk.ListStore(bool, str)
        self.treeview = Gtk.TreeView(model=self.recording_list_store)
        self.treeview.set_vexpand(True)

        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_toggle)
        column_toggle = Gtk.TreeViewColumn("Seleccionar", renderer_toggle, active=0)
        self.treeview.append_column(column_toggle)

        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn("Grabaciones", renderer_text, text=1)
        self.treeview.append_column(column_text)

        self.treeview.connect("row-activated", self.on_treeview_row_activated)
        scrolled_window.add(self.treeview)

        hbox_recordings = Gtk.Box(spacing=6)
        recording_tab.pack_start(hbox_recordings, False, False, 0)

        self.select_all_button = Gtk.Button(label="Seleccionar Todas")
        self.select_all_button.connect("clicked", self.on_select_all_button_clicked)
        hbox_recordings.pack_start(self.select_all_button, True, True, 0)

        self.delete_button = Gtk.Button(label="Eliminar Seleccionadas")
        self.delete_button.connect("clicked", self.on_delete_button_clicked)
        hbox_recordings.pack_start(self.delete_button, True, True, 0)

        self.delete_all_button = Gtk.Button(label="Eliminar Todas")
        self.delete_all_button.connect("clicked", self.on_delete_all_button_clicked)
        hbox_recordings.pack_start(self.delete_all_button, True, True, 0)

        # Tab for options
        options_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        notebook.append_page(options_tab, Gtk.Label(label="Opciones"))

        options_grid = Gtk.Grid()
        options_grid.set_column_homogeneous(True)
        options_grid.set_row_homogeneous(True)
        options_grid.set_column_spacing(10)
        options_grid.set_row_spacing(10)
        options_tab.pack_start(options_grid, False, False, 0)

        # Audio source selector
        self.source_label = Gtk.Label(label="Fuente de audio:")
        options_grid.attach(self.source_label, 0, 0, 1, 1)
        self.source_combo = Gtk.ComboBoxText()
        self.source_combo.append_text("default")
        self.source_combo.append_text("mic")
        self.source_combo.append_text("line-in")
        self.source_combo.set_active(0)
        options_grid.attach(self.source_combo, 1, 0, 1, 1)

        # File format selector
        self.format_label = Gtk.Label(label="Formato de archivo:")
        options_grid.attach(self.format_label, 2, 0, 1, 1)
        self.format_combo = Gtk.ComboBoxText()
        self.format_combo.append_text("ogg")
        self.format_combo.append_text("wav")
        self.format_combo.append_text("mp3")
        self.format_combo.append_text("flac")
        self.format_combo.append_text("aac")
        self.format_combo.set_active(0)
        options_grid.attach(self.format_combo, 3, 0, 1, 1)

        # Recording quality selector
        self.quality_label = Gtk.Label(label="Calidad de grabación:")
        options_grid.attach(self.quality_label, 0, 1, 1, 1)
        self.quality_combo = Gtk.ComboBoxText()
        self.quality_combo.append_text("Alta")
        self.quality_combo.append_text("Media")
        self.quality_combo.append_text("Baja")
        self.quality_combo.set_active(0)
        options_grid.attach(self.quality_combo, 1, 1, 1, 1)

        # Sample rate selector
        self.sample_rate_label = Gtk.Label(label="Frecuencia de muestreo:")
        options_grid.attach(self.sample_rate_label, 2, 1, 1, 1)
        self.sample_rate_combo = Gtk.ComboBoxText()
        self.sample_rate_combo.append_text("44100")
        self.sample_rate_combo.append_text("48000")
        self.sample_rate_combo.append_text("96000")
        self.sample_rate_combo.set_active(0)
        options_grid.attach(self.sample_rate_combo, 3, 1, 1, 1)

        # Audio channels selector
        self.channels_label = Gtk.Label(label="Canales de audio:")
        options_grid.attach(self.channels_label, 0, 2, 1, 1)
        self.channels_combo = Gtk.ComboBoxText()
        self.channels_combo.append_text("Mono")
        self.channels_combo.append_text("Stereo")
        self.channels_combo.set_active(1)
        options_grid.attach(self.channels_combo, 1, 2, 1, 1)

        # Load existing recordings
        self.load_recordings()
        self.update_buttons()

    def update_time_label(self):
        while self.recording:
            if not self.paused:
                elapsed_time = time.time() - self.start_time if self.start_time else 0
                hours, rem = divmod(elapsed_time, 3600)
                minutes, seconds = divmod(rem, 60)
                time_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
                GLib.idle_add(self.time_label.set_markup, f'<span font="20">{time_str}</span>')
            time.sleep(1)

    def on_record_button_clicked(self, widget): #pylint: disable=unused-argument
        self.start_recording()

    def start_recording(self):
        self.recording = True
        self.paused = False
        self.record_button.set_sensitive(False)
        self.pause_button.set_sensitive(True)
        self.stop_button.set_sensitive(True)
        self.start_time = time.time()

        # Show time label
        self.time_label.set_markup('<span font="20">00:00:00</span>')

        # Get selected options
        source = self.source_combo.get_active_text()
        quality = self.quality_combo.get_active_text()
        sample_rate = self.sample_rate_combo.get_active_text()
        channels = self.channels_combo.get_active_text()

        # Adjust bitrate according to selected quality
        bitrate = {"Alta": "320k", "Media": "128k", "Baja": "64k"}[quality]

        # Adjust the number of channels
        channel_option = "1" if channels == "Mono" else "2"

        # Get the user's Music directory
        music_dir = os.path.join(os.path.expanduser('~'), 'Music')
        os.makedirs(music_dir, exist_ok=True)

        # Get the current date and time for the file name
        current_time = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        file_format = self.format_combo.get_active_text()
        self.output_file = os.path.join(music_dir, f"grabacion_{current_time}.{file_format}")

        self.ffmpeg_process = subprocess.Popen([
            'ffmpeg', '-y', '-f', 'pulse', '-i', source, '-b:a', bitrate, '-ar', sample_rate, '-ac', channel_option, f'{self.output_file}'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.recording_thread = threading.Thread(target=self.update_time_label)
        self.recording_thread.start()

        # Update the recordings list
        self.recording_list_store.append([False, self.output_file])

        # Update buttons after adding a recording
        self.update_buttons()

    def on_pause_button_clicked(self, widget): #pylint: disable=unused-argument
        if self.recording:
            self.paused = not self.paused
            icon_name = "media-playback-start" if self.paused else "media-playback-pause"
            self.pause_button.set_image(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON))
            if self.ffmpeg_process:
                signal_action = signal.SIGSTOP if self.paused else signal.SIGCONT
                self.ffmpeg_process.send_signal(signal_action)

    def on_stop_button_clicked(self, widget): #pylint: disable=unused-argument
        if self.recording:
            self.recording = False
            self.record_button.set_sensitive(True)
            self.pause_button.set_sensitive(False)
            self.stop_button.set_sensitive(False)
            self.play_button.set_sensitive(True)
            self.stop_recording()

            # Update the time label
            elapsed_time = time.time() - self.start_time if self.start_time else 0
            hours, rem = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(rem, 60)
            time_str = f"Grabación finalizada: {int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            self.time_label.set_markup(f'<span font="20">{time_str}</span>')

            # Reset time label after 5 seconds
            GLib.timeout_add_seconds(5, self.reset_time_label)

    def reset_time_label(self):
        self.time_label.set_markup('<span font="20">Presione Grabar para empezar</span>')
        return False

    def on_play_button_clicked(self, widget): #pylint: disable=unused-argument
        for row in self.recording_list_store:
            if row[0]:  # If selected
                self.output_file = row[1]
                # Open the audio file with the system's default application
                if platform.system() == "Linux":
                    subprocess.Popen(['xdg-open', self.output_file])
                elif platform.system() == "Darwin":
                    subprocess.Popen(['open', self.output_file])
                elif platform.system() == "Windows" and hasattr(os, 'startfile'):
                    os.startfile(self.output_file)

    def on_treeview_row_activated(self, treeview, path, column): #pylint: disable=unused-argument
        model = treeview.get_model()
        self.output_file = model[path][1]
        # Open the audio file with the system's default application
        if platform.system() == "Linux":
            subprocess.Popen(['xdg-open', self.output_file])
        elif platform.system() == "Darwin":
            subprocess.Popen(['open', self.output_file])
        elif platform.system() == "Windows" and hasattr(os, 'startfile'):
            os.startfile(self.output_file)

    def stop_recording(self):
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process = None

    def on_toggle(self, widget, path): #pylint: disable=unused-argument
        self.recording_list_store[path][0] = not self.recording_list_store[path][0]
        self.update_buttons()

    def on_select_all_button_clicked(self, widget): #pylint: disable=unused-argument
        all_selected = all(row[0] for row in self.recording_list_store)
        for row in self.recording_list_store:
            row[0] = not all_selected
        self.update_buttons()

    def on_delete_button_clicked(self, widget): #pylint: disable=unused-argument
        for row in self.recording_list_store:
            if row[0]:
                os.remove(row[1])
        self.recording_list_store.clear()
        self.load_recordings()
        self.update_buttons()

    def on_delete_all_button_clicked(self, widget): #pylint: disable=unused-argument
        for row in self.recording_list_store:
            os.remove(row[1])
        self.recording_list_store.clear()
        self.load_recordings()
        self.update_buttons()

    def load_recordings(self):
        self.recording_list_store.clear()
        music_dir = os.path.join(os.path.expanduser('~'), 'Music')
        for file in os.listdir(music_dir):
            if file.startswith("grabacion_"):
                self.recording_list_store.append([False, os.path.join(music_dir, file)])
        self.update_buttons()

    def update_buttons(self):
        num_recordings = len(self.recording_list_store)
        any_selected = any(row[0] for row in self.recording_list_store)
        all_selected = all(row[0] for row in self.recording_list_store)

        self.select_all_button.set_sensitive(num_recordings > 0)
        self.delete_button.set_visible(num_recordings > 0 and not all_selected)
        self.delete_button.set_sensitive(any_selected and not all_selected)
        self.delete_all_button.set_sensitive(num_recordings > 0)
        self.play_button.set_sensitive(any_selected)

    def show_about_dialog(self, widget=None): #pylint: disable=unused-argument
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_program_name("CuerdRec")
        about_dialog.set_version("1.0 v110125a Elena")
        about_dialog.set_comments("Una aplicación simple para grabar sonidos utilizando ffmpeg, Python y GTK.")
        about_dialog.set_license_type(Gtk.License.GPL_3_0)
        script_dir = os.path.dirname(os.path.realpath(__file__))
        logo_path = os.path.join(script_dir, "/usr/share/cuerdrec/icons/rec.svg")
        about_dialog.set_authors([
            "Ale D.M", "Leo H. Pérez (GatoVerde95)", "Pablo G.", "Welkis", "GatoVerde95 Studios"
        ])
        about_dialog.set_copyright("© 2024 CuerdOS")
        
        if os.path.exists(logo_path):
            logo_pixbuf = GdkPixbuf.Pixbuf.new_from_file(logo_path)
            logo_pixbuf = logo_pixbuf.scale_simple(150, 150, GdkPixbuf.InterpType.BILINEAR)
            about_dialog.set_logo(logo_pixbuf)
            
        about_dialog.run()
        about_dialog.destroy()

win = AudioRecorder()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
