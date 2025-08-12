from functools import wraps
from utils.structured_logging import structured_logger as logger
import discord
from discord import app_commands

def log_command(func):
    """Decorador que loggea automáticamente la ejecución de comandos"""
    @wraps(func)
    async def wrapper(interaction: discord.Interaction, *args, **kwargs):
        # Información del usuario
        user_info = {
            'user_id': str(interaction.user.id),
            'username': interaction.user.name,
            'user_display_name': interaction.user.display_name,
        }
        
        # Información del servidor (si está en un servidor)
        if interaction.guild:
            user_info.update({
                'guild_id': str(interaction.guild.id),
                'guild_name': interaction.guild.name,
                'channel_id': str(interaction.channel.id),
                'channel_name': interaction.channel.name if hasattr(interaction.channel, 'name') else 'DM'
            })
        else:
            user_info.update({
                'guild_id': None,
                'guild_name': 'DM',
                'channel_id': str(interaction.channel.id),
                'channel_name': 'DM'
            })
        
        # Información del comando
        command_info = {
            'command': func.__name__,
            'operation': 'command_execution',
        }
        
        # Loggear parámetros del comando si los hay
        if args or kwargs:
            command_params = {}
            # Convertir args a dict basado en la función
            if hasattr(func, '__annotations__'):
                param_names = list(func.__annotations__.keys())[1:]  # Skip 'interaction'
                for i, arg in enumerate(args):
                    if i < len(param_names):
                        command_params[param_names[i]] = str(arg)
            
            # Añadir kwargs
            for key, value in kwargs.items():
                command_params[key] = str(value)
            
            if command_params:
                command_info['command_params'] = command_params
        
        # Log de inicio del comando
        logger.info(f"🎮 Comando /{func.__name__} ejecutado por {interaction.user.name}",
                   **user_info,
                   **command_info)
        
        try:
            # Ejecutar el comando original
            result = await func(interaction, *args, **kwargs)
            
            # Log de éxito
            logger.info(f"✅ Comando /{func.__name__} completado exitosamente",
                       **user_info,
                       **command_info,
                       status="success")
            
            return result
            
        except Exception as e:
            # Log de error
            logger.error(f"❌ Error en comando /{func.__name__}: {e}",
                        **user_info,
                        **command_info,
                        error_type=type(e).__name__,
                        status="error")
            
            # Re-lanzar la excepción para que el bot la maneje
            raise e
    
    return wrapper

def log_interaction(interaction_type: str = "interaction"):
    """Decorador más genérico para cualquier tipo de interacción"""
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            user_info = {
                'user_id': str(interaction.user.id),
                'username': interaction.user.name,
                'guild_id': str(interaction.guild.id) if interaction.guild else None,
                'guild_name': interaction.guild.name if interaction.guild else 'DM',
                'interaction_type': interaction_type,
                'operation': f'{interaction_type}_execution'
            }
            
            logger.info(f"🔄 {interaction_type.title()} {func.__name__} iniciado por {interaction.user.name}",
                       **user_info,
                       function_name=func.__name__)
            
            try:
                result = await func(interaction, *args, **kwargs)
                logger.info(f"✅ {interaction_type.title()} {func.__name__} completado",
                           **user_info,
                           function_name=func.__name__,
                           status="success")
                return result
            except Exception as e:
                logger.error(f"❌ Error en {interaction_type} {func.__name__}: {e}",
                            **user_info,
                            function_name=func.__name__,
                            error_type=type(e).__name__,
                            status="error")
                raise e
        return wrapper
    return decorator
