def run_cli() -> None:
    """Application Entrypoint."""
    from mtflow.cli import mtflow_group
    mtflow_group(obj={})


if __name__ == '__main__':
    run_cli()
