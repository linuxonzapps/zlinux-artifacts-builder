#  Copyright Contributors to the Mainframe Software Hub for Linux Project.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
from datetime import datetime

class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.logger = logging.getLogger('BuildSystem')
        self.logger.setLevel(logging.INFO)

        # Clear any existing handlers to prevent duplicates
        self.logger.handlers = []

        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)

        # Configure file handler
        log_file = f'logs/build_system_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def info(self, message: str):
        self.logger.info(message)

    def error(self, message: str):
        self.logger.error(message)

    def warning(self, message: str):
        self.logger.warning(message)
