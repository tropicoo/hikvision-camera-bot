import logging

FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class Log:
    """"""

    def __init__(self):
        pass

    @staticmethod
    def get_logger(name):
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # file_handler = logging.FileHandler('bot.log')
        # file_handler.setFormatter(formatter)
        handler = logging.StreamHandler()
        handler.setFormatter(FORMATTER)

        logger = logging.getLogger(name)
        logger.addHandler(handler)

        return logger
