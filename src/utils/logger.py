import logging
import os
from pathlib import Path

def setup_logger(
        name:str="Job_automation",
        log_file:str="data/job_automation.log",
        level:str="INFO"
        )->logging.Logger:
    # Create the log directory if it doesn't exist
    log_dir = Path(log_file).parent 
    log_dir.parent.mkdir(parents=True, exist_ok=True)

    #convert text level to logging level
    log_level=getattr(logging, level.upper(), logging.INFO)

    #create logger
    logger=logging.getLogger(name)
    logger.setLevel(log_level)
    #prevent duplicate log entries
    if logger.handlers:
        return logger
    # Log format
    formatter=logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

    #file handler
    file_handler=logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    #console handler
    console_handler=logging.StreamHandler()
    console_handler.setLevel(log_level
                            )
    console_handler.setFormatter(formatter)

    #Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger