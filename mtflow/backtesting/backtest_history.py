from __future__ import annotations
from typing import TYPE_CHECKING, Literal
if TYPE_CHECKING:
    from pfeed.typing import GenericFrame
    from pfund.strategies.strategy_base import BaseStrategy
    from pfund.engines.backtest_engine import BacktestEngine
    
import os
import shutil
import inspect
from pathlib import Path
import json
import datetime
import importlib

import pandas as pd
from rich.console import Console
from IPython import get_ipython

from pfund.utils import utils
from pfund import get_config
from pfund.enums import BacktestMode


config = get_config()


class BacktestHistory:
    # FIXME: remove engine access
    def __init__(self, retention_period: str='7d'):
        retention_period = retention_period.lower()
        assert retention_period[-1] in ['d', 'w', 'm', 'y'], 'retention_period must end with one of [d, w, m, y]'
            
        self._engine = engine
        self.logger = engine.logger
        self.mode = engine.mode
        self.retention_period = engine.retention_period
        self.backtest_path = Path(config.backtest_path)
        self.commit_to_git = engine.commit_to_git
        self.save_backtests = engine.save_backtests
        self.file_name = 'backtest.json'
        self.settings = engine.settings
        if not bool(get_ipython() is not None):
            from pfund.git_controller import GitController
            # Get the current frame and then the outer frame (where the engine instance is created)
            caller_frame = inspect.currentframe().f_back
            file_path = caller_frame.f_code.co_filename  # Extract the file path from the frame
            self._git = GitController(os.path.abspath(file_path))
            if not self._git.is_git_repo():
                self._git = None
        else:
            self._git = None
    
    @staticmethod
    def _read_json(file_path: str | Path) -> dict:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                backtest_json = json.load(f)
        else:
            backtest_json = {}
        return backtest_json
    
    @staticmethod
    def _write_json(file_path: str | Path, json_file: dict) -> None:
        with open(file_path, 'w') as f:
            json.dump(json_file, f, indent=4)
            
    @staticmethod 
    def _generate_backtest_id() -> str:
        import uuid
        return uuid.uuid4().hex
    
    @staticmethod 
    def _generate_backtest_hash(strategy: BaseStrategy):
        '''Generate hash based on strategy for backtest traceability
        backtest_hash is used to identify if the backtests are generated by the same strategy.
        Useful for avoiding overfitting the strategy on the same dataset.
        '''
        import hashlib
        # REVIEW: currently only use strategy to generate hash, may include other settings in the future
        strategy_dict = strategy.to_dict()
        # since conceptually backtest_hash should be the same regardless of the 
        # strategy_signature (params) and data_signatures (e.g. backtest_kwargs, train_kwargs, data_source, resolution etc.)
        # remove them
        del strategy_dict['strategy_signature']
        del strategy_dict['data_signatures']
        strategy_str = json.dumps(strategy_dict)
        return hashlib.sha256(strategy_str.encode()).hexdigest()
            
    @staticmethod
    def _create_backtest_name(strat: str, backtest_id: str, backtest_id_length: int=12) -> str:
        local_tz = utils.get_local_timezone()
        local_now = datetime.datetime.now(tz=local_tz).strftime('%Y-%m-%d_%H:%M:%S_UTC%z')
        trimmed_backtest_id = backtest_id[:backtest_id_length]
        return '.'.join([strat, local_now, trimmed_backtest_id])
    
    @staticmethod
    def _parse_backtest_name(backtest_name: str) -> tuple[str, str, str]:
        strat, local_now, trimmed_backtest_id = backtest_name.split('.')
        return strat, local_now, trimmed_backtest_id
    
    def _create_backtest_path(self, backtest_name: str) -> Path:
        strat, local_now, _ = self._parse_backtest_name(backtest_name)
        today = str(datetime.datetime.strptime(local_now, '%Y-%m-%d_%H:%M:%S_UTC%z').date())
        backtest_path = self.backtest_path / today / strat
        if not os.path.exists(backtest_path):
            os.makedirs(backtest_path)
        return backtest_path
    
    def _generate_backtest_iteration(self, backtest_hash: str) -> int:
        '''Generate backtest iteration number for the same backtest_hash.
        Read the existing backtest.json file to get the iteration number for the same strategy hash
        If the backtest hash is not found, create a new entry with iteration number 1
        else increment the iteration number by 1.
        '''
        file_path = self.backtest_path / self.file_name
        backtest_json = self._read_json(file_path)
        backtest_json[backtest_hash] = backtest_json.get(backtest_hash, 0) + 1
        self._write_json(file_path, backtest_json)
        return backtest_json[backtest_hash]
    
    def _commit_git(self, strategy: BaseStrategy) -> str | None:
        engine_name = self._engine.__class__.__name__
        strat = strategy.name
        commit_hash: str | None = self._git.commit(strategy._file_path, f'[PFund] {engine_name}: auto-commit strategy "{strat}"')
        if commit_hash:
            self.logger.debug(f"Strategy {strat} committed. {commit_hash=}")
        else:
            commit_hash = self._git.get_last_n_commit(n=1)[0]
            self.logger.debug(f"Strategy {strat} has no changes to commit, return the last {commit_hash=}")
        return commit_hash

    def __call__(self, backtest_name: str, file: Literal['json', 'parquet']='parquet') -> dict:
        '''Reads backtest history of a specific backtest''' 
        backtest_path = self._create_backtest_path(backtest_name)
        file_path = backtest_path / f'{backtest_name}.{file}'
        if file == 'json':
            backtest_history = self._read_json(file_path)
            return backtest_history
        elif file == 'parquet':
            data_tool = self._engine.DataTool.name
            data_tool = importlib.import_module(f'pfeed.data_tools.data_tool_{data_tool}')
            df = data_tool.read_parquet(file_path)
            return df
        else:
            raise ValueError(f'file must be one of [json, parquet], got {file}')
            
    def create(self, strategy: BaseStrategy, df: GenericFrame, start_time: float, end_time: float):
        import pfund as pf
        initial_balances = {bkr: broker.get_initial_balances() for bkr, broker in self._engine.brokers.items()}
        backtest_id = self._generate_backtest_id()
        backtest_hash = self._generate_backtest_hash(strategy)
        backtest_name = self._create_backtest_name(strategy.name, backtest_id)
        backtest_iter = self._generate_backtest_iteration(backtest_hash)
        commit_hash = self._commit_git(strategy) if self._git and self.commit_to_git else None
        local_tz = utils.get_local_timezone()
        duration = end_time - start_time
        backtest_history = {
            'metadata': {
                'pfund_version': pf.__version__,
                'backtest_hash': backtest_hash,
                'backtest_iteration': backtest_iter,
                'commit_hash': commit_hash,
                'duration': f'{duration:.2f}s' if duration > 1 else f'{duration*1000:.2f}ms',
                'start_time': datetime.datetime.fromtimestamp(start_time, tz=local_tz).strftime('%Y-%m-%dT%H:%M:%S%z'),
                'end_time': datetime.datetime.fromtimestamp(end_time, tz=local_tz).strftime('%Y-%m-%dT%H:%M:%S%z'),
                'timezone': repr(local_tz),
                'settings': self.settings,
            },
            'backtest_id': backtest_id,
            'backtest_name': backtest_name,
            'initial_balances': initial_balances,
            'strategy': strategy.to_dict(),
        }
        if self.save_backtests:
            backtest_history = self._write(strategy, df, backtest_history)
        self._clean_up(backtest_name)
        return backtest_history
    
    def _write(self, strategy: BaseStrategy, df: GenericFrame, backtest_history: dict) -> dict:
        '''Writes backtest history to a parquet file and adds the file path to backtest.json'''
        backtest_name = backtest_history['backtest_name']
        backtest_path: Path = self._create_backtest_path(backtest_name)
        if self.mode == BacktestMode.vectorized:
            output_file_path = backtest_path / f'{backtest_name}.parquet'
            strategy.dtl.output_df_to_parquet(df, output_file_path)
        elif self.mode == BacktestMode.event_driven:
            # TODO: output trades? or orders? or df?
            output_file_path = ...
        backtest_history['result'] = str(output_file_path)
        self._write_json(backtest_path / f'{backtest_name}.json', backtest_history)
        return backtest_history

    def clear(self):
        '''Clears all backtest history in the 'backtests' folder'''
        for filename in os.listdir(self.backtest_path):
            file_path = os.path.join(self.backtest_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        Console().print('Cleared backtest history!', style='bold red')
    
    def _clean_up(self, backtest_name: str) -> None:
        from pfeed.utils.utils import rollback_date_range
        _, local_now, _ = self._parse_backtest_name(backtest_name)
        today = datetime.datetime.strptime(local_now, '%Y-%m-%d_%H:%M:%S_UTC%z').date()
        if self.retention_period[-1] == 'm':
            # since rollback_date_range uses Resolution(), where 'M' is month, 'm' is minute, need to convert 'm' to 'M'
            retention_period = self.retention_period.replace('m', 'M')
        else:
            retention_period = self.retention_period
        start_date, end_date = rollback_date_range(retention_period)
        end_date += datetime.timedelta(days=1)
        retained_dates = pd.date_range(start_date, end_date).date
        if today not in retained_dates:
            retained_dates.append(today)
        retained_dates = [date.strftime('%Y-%m-%d') for date in retained_dates]
        for path in os.listdir(self.backtest_path):
            if path == self.file_name:
                continue
            if path not in retained_dates:
                shutil.rmtree(self.backtest_path / path)
