#!/bin/bash

# Detectar idioma del sistema
LANGUAGE=$(echo $LANG | cut -d'_' -f1)

# Decidir qué script ejecutar
if [ "$LANGUAGE" == "es" ]; then
    python3 /usr/share/cuerdrec/rec.py
elif [ "$LANGUAGE" == "en" ]; then
    python3 /usr/share/cuerdrec/rec_en.py
else
    echo "Idioma no soportado: $LANGUAGE"
    # Puedes establecer un script por defecto o mostrar un mensaje de error
    python3 /usr/share/cuerdrec/rec.py  # Por defecto a español
fi

