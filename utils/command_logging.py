from functools import wraps
from utils.structured_logging import structured_logger as logger
import discord
from discord import app_commands


def log_command(func):
    """Decorator that automatically logs the execution of commands"""
    @wraps(func)
    async def wrapper(interaction: discord.Interaction, *args, **kwargs):
        # User information
        user_info = {
            'user_id': str(interaction.user.id),
            'username': interaction.user.name,
            'user_display_name': interaction.user.display_name,
        }

        # Guild information (if inside a server)
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

        # Command information
        command_info = {
            'command': func.__name__,
            'operation': 'command_execution',
        }

        # Log command parameters if any
        if args or kwargs:
            command_params = {}
            # Convert args to dict based on function annotations
            if hasattr(func, '__annotations__'):
                param_names = list(func.__annotations__.keys())[
                    1:]  # Skip 'interaction'
                for i, arg in enumerate(args):
                    if i < len(param_names):
                        command_params[param_names[i]] = str(arg)

            # Add kwargs
            for key, value in kwargs.items():
                command_params[key] = str(value)

            if command_params:
                command_info['command_params'] = command_params

        # Command start log
        logger.info(f"🎮 Command /{func.__name__} executed by {interaction.user.name}",
                    **user_info,
                    **command_info)

        try:
            # Execute the original command
            result = await func(interaction, *args, **kwargs)

            # Success log
            logger.info(f"✅ Command /{func.__name__} completed successfully",
                        **user_info,
                        **command_info,
                        status="success")

            return result

        except Exception as e:
            # Error log
            logger.error(f"❌ Error in command /{func.__name__}: {e}",
                         **user_info,
                         **command_info,
                         error_type=type(e).__name__,
                         status="error")

            # Re-raise exception so the bot can handle it
            raise e

    return wrapper


def log_interaction(interaction_type: str = "interaction"):
    """More generic decorator for any type of interaction"""
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

            logger.info(f"🔄 {interaction_type.title()} {func.__name__} started by {interaction.user.name}",
                        **user_info,
                        function_name=func.__name__)

            try:
                result = await func(interaction, *args, **kwargs)
                logger.info(f"✅ {interaction_type.title()} {func.__name__} completed",
                            **user_info,
                            function_name=func.__name__,
                            status="success")
                return result
            except Exception as e:
                logger.error(f"❌ Error in {interaction_type} {func.__name__}: {e}",
                             **user_info,
                             function_name=func.__name__,
                             error_type=type(e).__name__,
                             status="error")
                raise e
        return wrapper
    return decorator
