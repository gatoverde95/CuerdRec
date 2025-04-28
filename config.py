"""
Módulo de configuración para CuerdRec
Maneja la persistencia de configuraciones de la aplicación
"""

import os
import json

class ConfigManager:
    """Clase para manejar la configuración de la aplicación"""
    
    def __init__(self):
        """Inicializa el gestor de configuración"""
        self.config_dir = os.path.join(os.path.expanduser('~'), '.config', 'cuerdrec')
        self.config_file = os.path.join(self.config_dir, 'config.json')
        self.config = self._load_config()
    
    def _load_config(self):
        """
        Carga la configuración desde el archivo
        
        Returns:
            dict: Configuración cargada o configuración por defecto
        """
        default_config = {
            "language": "es",  # Idioma por defecto (español)
            "recording_options": {
                "audio_source": "default",
                "format": "ogg",
                "quality": "high",
                "bitrate": "192k",
                "sample_rate": "44100",
                "channels": "stereo"
            }
        }
        
        # Verificar si existe el directorio de configuración
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
            except Exception as e:
                print(f"Error al crear directorio de configuración: {e}")
                return default_config
        
        # Cargar configuración si existe
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error al cargar configuración: {e}")
        
        return default_config
    
    def save_config(self):
        """Guarda la configuración actual en el archivo"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error al guardar configuración: {e}")
            return False
    
    def get_language(self):
        """
        Obtiene el idioma configurado
        
        Returns:
            str: Código de idioma ('es' o 'en')
        """
        return self.config.get("language", "es")
    
    def set_language(self, language):
        """
        Establece el idioma
        
        Args:
            language (str): Código de idioma ('es' o 'en')
            
        Returns:
            bool: True si se guardó correctamente, False en caso contrario
        """
        if language not in ["es", "en"]:
            language = "es"
        
        self.config["language"] = language
        return self.save_config()
    
    def get_recording_option(self, option_name):
        """
        Obtiene una opción de grabación específica
        
        Args:
            option_name (str): Nombre de la opción
            
        Returns:
            str: Valor de la opción o None si no existe
        """
        options = self.config.get("recording_options", {})
        return options.get(option_name)
    
    def set_recording_option(self, option_name, value):
        """
        Establece una opción de grabación
        
        Args:
            option_name (str): Nombre de la opción
            value (str): Valor a establecer
            
        Returns:
            bool: True si se guardó correctamente, False en caso contrario
        """
        if "recording_options" not in self.config:
            self.config["recording_options"] = {}
        
        self.config["recording_options"][option_name] = value
        return self.save_config()