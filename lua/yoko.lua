local lgi = require 'lgi'
local Gtk = lgi.Gtk
local GLib = lgi.GLib

-- Crear una nueva ventana GTK
local window = Gtk.Window {
    title = "Ejecutar rec.py",
    default_width = 300,
    default_height = 100,
    border_width = 10,
    on_destroy = Gtk.main_quit
}

-- Crear un botón
local button = Gtk.Button { label = "Ejecutar rec.py" }

-- Función para manejar el clic del botón
function button:on_clicked()
    -- Ejecutar el script rec.py
    local handle = io.popen("python3 rec.py")
    local result = handle:read("*a")
    handle:close()
    
    -- Mostrar el resultado en un diálogo
    local dialog = Gtk.MessageDialog {
        transient_for = window,
        modal = true,
        buttons = Gtk.ButtonsType.OK,
        text = "Resultado de rec.py",
        secondary_text = result
    }
    dialog:run()
    dialog:destroy()
end

-- Añadir el botón a la ventana y mostrar todo
window:add(button)
window:show_all()

Gtk.main()
