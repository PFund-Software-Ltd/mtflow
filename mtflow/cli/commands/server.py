import click


@click.command(
    add_help_option=False,  # disable click's --help option so that server --help can work
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    ),
)
@click.pass_context
def server(ctx):
    """Run litestar CLI"""
    import subprocess

    result = subprocess.run(["litestar", '--app', "mtflow.transport.app:app", *ctx.args])
    ctx.exit(result.returncode)
