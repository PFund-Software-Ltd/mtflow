from __future__ import annotations

from pathlib import Path

from pfund_kit.config import Configuration


__all__ = [
    'get_config',
    'configure',
    'configure_logging',
    'setup_logging',
]


project_name = 'mtflow'
_config: MTFlowConfig | None = None
_logging_config: dict | None = None

DEFAULT_UVICORN_LOGGING_CONFIG = {
    "uvicorn": {
        "level": "DEBUG",
        "handlers": ["compressed_timed_rotating_file_handler", "queue_listener_handler"],
        "propagate": False,
    },
    "uvicorn.access": {
        "level": "DEBUG",
        "handlers": ["compressed_timed_rotating_file_handler", "queue_listener_handler"],
        "propagate": False,
    },
}


def setup_logging(
    logging_config: dict,
    include_uvicorn: bool = False,
    env: str | None=None,
    reset: bool=False
):
    """
    Drop-in replacement for logging.config.dictConfig, called by Litestar internally.

    This function is monkey-patched as `logging.config.dictConfig = setup_logging`,
    so Litestar's logging initialization calls this instead of the standard dictConfig.

    Args:
        logging_config: Logging configuration dict passed by Litestar when it calls
            dictConfig internally during app initialization.
        include_uvicorn: If True, overrides uvicorn's default StreamHandler configuration
            to use file logging and Litestar's QueueListenerHandler. This provides:
            - Persistent uvicorn logs written to rotating log files
            - Non-blocking logging via QueueListenerHandler (async queue-based)
            By default False since uvicorn's verbose DEBUG logs are rarely needed
            during local development.
        env: Environment name to create a subdirectory under log_path.
        reset: If True, clears all existing logging handlers before configuring.

    Returns:
        The (potentially modified) logging config dict.
    """
    from pfund_kit.logging import clear_logging_handlers, setup_exception_logging
    from pfund_kit.logging.configurator import LoggingDictConfigurator
    
    env = env.upper() if env else ''
    
    if reset:
        clear_logging_handlers()
        
    config: MTFlowConfig = get_config()

    log_path = config.log_path / env if env else config.log_path
    log_path.mkdir(parents=True, exist_ok=True)

    if include_uvicorn:
        logging_config['loggers'].update(DEFAULT_UVICORN_LOGGING_CONFIG)

    # ≈ logging.config.dictConfig(logging_config) with a custom configurator
    logging_configurator = LoggingDictConfigurator.create(
        log_path=log_path, 
        logging_config=logging_config, 
        lazy=True,
        use_colored_logger=True,
    )
    logging_configurator.configure()
    
    setup_exception_logging(logger_name=project_name)
    return logging_config


def get_config() -> MTFlowConfig:
    """Lazy singleton - only creates config when first called.
    Also loads the .env file.
    """
    global _config
    if _config is None:
        _config = MTFlowConfig()
    return _config


def get_logging_config() -> dict:
    global _logging_config
    if _logging_config is None:
        _logging_config = configure_logging()
    return _logging_config


def configure(
    data_path: str | None = None,
    log_path: str | None = None,
    cache_path: str | None = None,
    num_workers: int | None = None,
    persist: bool = False,
) -> MTFlowConfig:
    '''
    Configures the global config object.
    Args:
        data_path: Path to the data directory.
        log_path: Path to the log directory.
        cache_path: Path to the cache directory.
        num_workers: Number of workers to use for the WS server, equivalent to --web-concurrency in litestar.
        persist: If True, the config will be saved to the config file.
    '''
    config = get_config()
    config_dict = config.to_dict()
    config_dict.pop('__version__')
    
    # Apply updates for non-None values
    for k in config_dict:
        v = locals().get(k)
        if v is not None:
            if '_path' in k:
                v = Path(v)
            elif k == 'num_workers':
                v = max(int(v), 1)
            setattr(config, k, v)
    
    config.ensure_dirs()
    
    if persist:
        config.save()
        
    return config


def configure_logging(logging_config: dict | None=None, debug: bool=False) -> dict:
    '''
    Loads logging config from YAML file and merges with optional user overrides.

    Args:
        logging_config: Optional dict to override/extend the base YAML config.
        debug: If True, sets all loggers and handlers to DEBUG level.
               This overrides any level settings from the YAML file and logging_config.

    Returns:
        Merged logging config dict.

    Raises:
        FileNotFoundError: If the logging config YAML file is not found.
    '''
    from pfund_kit.utils import deep_merge
    from pfund_kit.logging import enable_debug_logging
    from pfund_kit.utils.yaml import load

    global _logging_config

    config = get_config()

    # load logging.yml file
    logging_config_from_yml: dict | None = load(config.logging_config_file_path)
    if logging_config_from_yml is None:
        raise FileNotFoundError(f"Logging config file {config.logging_config_file_path} not found")
    
    _logging_config = deep_merge(logging_config_from_yml, logging_config or {})
    if debug:
        _logging_config = enable_debug_logging(_logging_config)
    return _logging_config
    

class MTFlowConfig(Configuration):
    def __init__(self):
        from pfund_kit.utils import load_env_file
        load_env_file(verbose=False)
        super().__init__(project_name=project_name, source_file=__file__)

    def _initialize_from_data(self):
        """No additional config attributes to initialize."""
        self.num_workers = int(self._data.get('num_workers', 1))
    
    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            'num_workers': self.num_workers,
        }
    
    def prepare_docker_context(self):
        pass
    
    @property
    def artifact_path(self) -> Path:
        return self.data_path / 'artifacts'
    
    @property
    def strategy_path(self) -> Path:
        return self.artifact_path / 'strategies'
    
    @property
    def model_path(self) -> Path:
        return self.artifact_path / 'models'
    
    @property
    def feature_path(self) -> Path:
        return self.artifact_path / 'features'
    
    @property
    def indicator_path(self) -> Path:
        return self.artifact_path / 'indicators'
    
    @property
    def notebook_path(self) -> Path:
        return self.artifact_path / 'notebooks'
    
    @property
    def dashboard_path(self) -> Path:
        return self.artifact_path / 'dashboards'
    