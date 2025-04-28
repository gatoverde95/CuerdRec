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
        self.set_default_size(500, 350)
        
        # Set icon
        icon_path = "icons/rec.svg"
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

        # Variables de estado
        self.recording = False
        self.paused = False
        self.ffmpeg_process = None
        self.output_file = None
        self.start_time = None
        self.option_combos = {}
        
        # Configuración de la interfaz
        self.setup_ui()
        self.load_recordings()
        
    def setup_ui(self):
        # Contenedor principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.add(main_box)
        
        # Barra de herramientas superior
        toolbar = Gtk.HeaderBar()
        toolbar.set_show_close_button(True)
        toolbar.set_title("CuerdRec")
        self.set_titlebar(toolbar)
        
        # Botón Acerca de
        about_button = Gtk.Button()
        about_button.set_image(Gtk.Image.new_from_icon_name("help-about-symbolic", Gtk.IconSize.BUTTON))
        about_button.set_tooltip_text("Acerca de")
        about_button.connect("clicked", self.show_about_dialog)
        toolbar.pack_end(about_button)
        
        # Notebook para pestañas
        notebook = Gtk.Notebook()
        main_box.pack_start(notebook, True, True, 0)
        
        # Pestaña de grabación
        recording_page = self.create_recording_page()
        notebook.append_page(recording_page, Gtk.Label(label="Grabación"))
        
        # Pestaña de opciones
        options_page = self.create_options_page()
        notebook.append_page(options_page, Gtk.Label(label="Opciones"))
    
    def create_recording_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(10)
        
        # Panel superior: tiempo y controles
        top_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        page.pack_start(top_panel, False, False, 0)
        
        # Etiqueta de tiempo
        self.time_label = Gtk.Label(label="Listo para grabar")
        self.time_label.set_markup('<span font="18">Listo para grabar</span>')
        top_panel.pack_start(self.time_label, False, False, 5)
        
        # Controles de grabación
        controls = Gtk.Box(spacing=5)
        top_panel.pack_start(controls, False, False, 5)
        
        # Botones con iconos
        button_size = Gtk.IconSize.LARGE_TOOLBAR
        
        self.record_button = Gtk.Button()
        self.record_button.set_image(Gtk.Image.new_from_icon_name("media-record-symbolic", button_size))
        self.record_button.set_tooltip_text("Grabar")
        self.record_button.connect("clicked", self.on_record_button_clicked)
        controls.pack_start(self.record_button, True, True, 0)
        
        self.pause_button = Gtk.Button()
        self.pause_button.set_image(Gtk.Image.new_from_icon_name("media-playback-pause-symbolic", button_size))
        self.pause_button.set_tooltip_text("Pausar")
        self.pause_button.connect("clicked", self.on_pause_button_clicked)
        self.pause_button.set_sensitive(False)
        controls.pack_start(self.pause_button, True, True, 0)
        
        self.stop_button = Gtk.Button()
        self.stop_button.set_image(Gtk.Image.new_from_icon_name("media-playback-stop-symbolic", button_size))
        self.stop_button.set_tooltip_text("Detener")
        self.stop_button.connect("clicked", self.on_stop_button_clicked)
        self.stop_button.set_sensitive(False)
        controls.pack_start(self.stop_button, True, True, 0)
        
        self.play_button = Gtk.Button()
        self.play_button.set_image(Gtk.Image.new_from_icon_name("media-playback-start-symbolic", button_size))
        self.play_button.set_tooltip_text("Reproducir")
        self.play_button.connect("clicked", self.on_play_button_clicked)
        self.play_button.set_sensitive(False)
        controls.pack_start(self.play_button, True, True, 0)
        
        # Lista de grabaciones
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        page.pack_start(list_box, True, True, 5)
        
        # Etiqueta para la lista
        list_label = Gtk.Label(label="Grabaciones")
        list_label.set_halign(Gtk.Align.START)
        list_box.pack_start(list_label, False, False, 0)
        
        # TreeView para las grabaciones
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)
        list_box.pack_start(scrolled_window, True, True, 0)
        
        self.recording_list_store = Gtk.ListStore(bool, str)
        self.treeview = Gtk.TreeView(model=self.recording_list_store)
        
        # Columnas
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_toggle)
        self.treeview.append_column(Gtk.TreeViewColumn("", renderer_toggle, active=0))
        
        renderer_text = Gtk.CellRendererText()
        self.treeview.append_column(Gtk.TreeViewColumn("Nombre", renderer_text, text=1))
        
        self.treeview.connect("row-activated", self.on_treeview_row_activated)
        scrolled_window.add(self.treeview)
        
        # Botones de acción para grabaciones
        actions_box = Gtk.Box(spacing=5)
        list_box.pack_start(actions_box, False, False, 0)
        
        self.select_all_button = Gtk.Button(label="Seleccionar todas")
        self.select_all_button.connect("clicked", self.on_select_all_button_clicked)
        actions_box.pack_start(self.select_all_button, True, True, 0)
        
        self.delete_button = Gtk.Button(label="Eliminar selección")
        self.delete_button.connect("clicked", self.on_delete_button_clicked)
        actions_box.pack_start(self.delete_button, True, True, 0)
        
        return page
    
    def create_options_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(15)
        
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        page.pack_start(grid, False, False, 0)
        
        options = [
            ("Fuente de audio:", ["default", "mic", "line-in"], 0),
            ("Formato:", ["ogg", "wav", "mp3", "flac", "aac"], 0),
            ("Calidad:", ["Alta", "Media", "Baja"], 0),
            ("Bitrate:", ["320k", "256k", "192k", "128k", "64k"], 0),
            ("Muestreo:", ["44100", "48000", "96000"], 0),
            ("Canales:", ["Stereo", "Mono"], 0)
        ]
        
        for i, (label_text, values, default) in enumerate(options):
            row = i // 2
            col_start = (i % 2) * 2
            
            label = Gtk.Label(label=label_text)
            label.set_halign(Gtk.Align.START)
            grid.attach(label, col_start, row, 1, 1)
            
            combo = Gtk.ComboBoxText()
            for value in values:
                combo.append_text(value)
            combo.set_active(default)
            grid.attach(combo, col_start + 1, row, 1, 1)
            
            option_name = label_text.replace(":", "").lower()
            self.option_combos[option_name] = combo
        
        return page
    
    def update_time_label(self):
        while self.recording:
            if not self.paused:
                elapsed_time = time.time() - self.start_time if self.start_time else 0
                hours, rem = divmod(elapsed_time, 3600)
                minutes, seconds = divmod(rem, 60)
                time_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
                GLib.idle_add(self.time_label.set_markup, f'<span font="18">{time_str}</span>')
            time.sleep(0.5)
    
    def on_record_button_clicked(self, widget):
        self.recording = True
        self.paused = False
        self.start_time = time.time()
        
        # Actualizar botones
        self.record_button.set_sensitive(False)
        self.pause_button.set_sensitive(True)
        self.stop_button.set_sensitive(True)
        
        # Actualizar etiqueta de tiempo
        self.time_label.set_markup('<span font="18">00:00:00</span>')
        
        # Obtener opciones seleccionadas
        source = self.option_combos["fuente de audio"].get_active_text()
        file_format = self.option_combos["formato"].get_active_text()
        sample_rate = self.option_combos["muestreo"].get_active_text()
        channels = self.option_combos["canales"].get_active_text()
        bitrate = self.option_combos["bitrate"].get_active_text()
        
        # Ajustar el número de canales
        channel_option = "1" if channels == "Mono" else "2"
        
        # Preparar el directorio de salida
        music_dir = os.path.join(os.path.expanduser('~'), 'Music')
        os.makedirs(music_dir, exist_ok=True)
        
        # Nombre de archivo con fecha y hora
        current_time = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        self.output_file = os.path.join(music_dir, f"grabacion_{current_time}.{file_format}")
        
        # Iniciar ffmpeg
        try:
            self.ffmpeg_process = subprocess.Popen([
                'ffmpeg', '-y', '-f', 'pulse', '-i', source,
                '-b:a', bitrate, '-ar', sample_rate, '-ac', channel_option,
                self.output_file
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Iniciar hilo para actualizar el tiempo
            threading.Thread(target=self.update_time_label, daemon=True).start()
            
            # Añadir a la lista
            self.recording_list_store.append([False, os.path.basename(self.output_file)])
            
        except Exception as e:
            print(f"Error al iniciar la grabación: {e}")
            self.recording = False
            self.record_button.set_sensitive(True)
            self.pause_button.set_sensitive(False)
            self.stop_button.set_sensitive(False)
    
    def on_pause_button_clicked(self, widget):
        if self.recording:
            self.paused = not self.paused
            icon_name = "media-playback-start-symbolic" if self.paused else "media-playback-pause-symbolic"
            tooltip = "Reanudar" if self.paused else "Pausar"
                
            self.pause_button.set_image(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR))
            self.pause_button.set_tooltip_text(tooltip)
            
            if self.ffmpeg_process:
                self.ffmpeg_process.send_signal(signal.SIGSTOP if self.paused else signal.SIGCONT)
    
    def on_stop_button_clicked(self, widget):
        if self.recording:
            self.recording = False
            
            # Actualizar botones
            self.record_button.set_sensitive(True)
            self.pause_button.set_sensitive(False)
            self.stop_button.set_sensitive(False)
            
            # Detener ffmpeg
            if self.ffmpeg_process:
                try:
                    self.ffmpeg_process.terminate()
                    self.ffmpeg_process = None
                except Exception as e:
                    print(f"Error al detener ffmpeg: {e}")
                    
            # Mostrar tiempo final
            elapsed_time = time.time() - self.start_time if self.start_time else 0
            hours, rem = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(rem, 60)
            time_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            self.time_label.set_markup(f'<span font="18">Grabado: {time_str}</span>')
            
            # Recargar la lista después de unos segundos
            GLib.timeout_add_seconds(1, self.load_recordings)
    
    def open_file(self, filepath):
        if not os.path.exists(filepath):
            return
            
        if platform.system() == "Linux":
            subprocess.Popen(['xdg-open', filepath])
        elif platform.system() == "Darwin":
            subprocess.Popen(['open', filepath])
        elif platform.system() == "Windows" and hasattr(os, 'startfile'):
            os.startfile(filepath)
    
    def on_play_button_clicked(self, widget):
        for row in self.recording_list_store:
            if row[0]:  # Si está seleccionado
                full_path = os.path.join(os.path.expanduser('~'), 'Music', row[1])
                self.open_file(full_path)
    
    def on_treeview_row_activated(self, treeview, path, column):
        filename = treeview.get_model()[path][1]
        full_path = os.path.join(os.path.expanduser('~'), 'Music', filename)
        self.open_file(full_path)
    
    def on_toggle(self, widget, path):
        self.recording_list_store[path][0] = not self.recording_list_store[path][0]
        self.update_buttons()
    
    def on_select_all_button_clicked(self, widget):
        all_selected = all(row[0] for row in self.recording_list_store)
        for row in self.recording_list_store:
            row[0] = not all_selected
        self.update_buttons()
    
    def on_delete_button_clicked(self, widget):
        to_delete = [(i, row[1]) for i, row in enumerate(self.recording_list_store) if row[0]]
        
        if not to_delete:
            return
            
        # Eliminar archivos y entradas de la lista
        for idx, filename in reversed(to_delete):
            full_path = os.path.join(os.path.expanduser('~'), 'Music', filename)
            try:
                if os.path.exists(full_path):
                    os.remove(full_path)
                iter_path = self.recording_list_store.get_iter(idx)
                self.recording_list_store.remove(iter_path)
            except Exception as e:
                print(f"Error al eliminar {filename}: {e}")
                
        self.update_buttons()
    
    def load_recordings(self):
        self.recording_list_store.clear()
        music_dir = os.path.join(os.path.expanduser('~'), 'Music')
        
        if not os.path.exists(music_dir):
            return
            
        for file in os.listdir(music_dir):
            if file.startswith("grabacion_"):
                self.recording_list_store.append([False, file])
        
        self.update_buttons()
        return False
    
    def update_buttons(self):
        has_recordings = len(self.recording_list_store) > 0
        has_selected = any(row[0] for row in self.recording_list_store)
        
        self.select_all_button.set_sensitive(has_recordings)
        self.delete_button.set_sensitive(has_selected)
        self.play_button.set_sensitive(has_selected)
    
    def show_about_dialog(self, widget):
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_transient_for(self)
        about_dialog.set_modal(True)
        about_dialog.set_program_name("CuerdRec")
        about_dialog.set_version("2.0 Alpha")
        about_dialog.set_comments("Aplicación para grabar audio utilizando ffmpeg")
        about_dialog.set_license_type(Gtk.License.GPL_3_0)
        about_dialog.set_authors(["Ale D.M", "Leo H. Pérez (GatoVerde95)", 
                                  "Pablo G.", "Welkis", "GatoVerde95 Studios"])
        about_dialog.set_copyright("© 2025 CuerdOS")
        
        logo_path = "/usr/share/cuerdrec/icons/rec.svg"
        if os.path.exists(logo_path):
            try:
                logo_pixbuf = GdkPixbuf.Pixbuf.new_from_file(logo_path)
                logo_pixbuf = logo_pixbuf.scale_simple(128, 128, GdkPixbuf.InterpType.BILINEAR)
                about_dialog.set_logo(logo_pixbuf)
            except:
                pass
                
        about_dialog.run()
        about_dialog.destroy()

if __name__ == "__main__":
    win = AudioRecorder()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()