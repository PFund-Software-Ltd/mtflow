from pfund_kit.cli import create_cli_group
from pfund_kit.cli.commands import config, docker_compose, remove
from mtflow.cli.commands.server import server
# TODO
# from pfund_kit.cli.commands import doc


def init_context(ctx):
    """Initialize mtflow-specific context"""
    from mtflow.config import get_config
    ctx.obj['config'] = get_config()


mtflow_group = create_cli_group('mtflow', init_context=init_context)
mtflow_group.add_command(config)
mtflow_group.add_command(docker_compose)
mtflow_group.add_command(docker_compose, name='compose')
mtflow_group.add_command(remove)
mtflow_group.add_command(remove, name='rm')
mtflow_group.add_command(server)
# TODO: add api doc, in localhost:8000/schema
# mtflow_group.add_command(doc)