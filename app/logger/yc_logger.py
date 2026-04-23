import base64
import json
import logging

from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.struct_pb2 import Struct
from yandex.cloud.logging.v1.log_entry_pb2 import IncomingLogEntry, Destination, LogLevel
from yandex.cloud.logging.v1.log_ingestion_service_pb2 import WriteRequest
from yandex.cloud.logging.v1.log_ingestion_service_pb2_grpc import LogIngestionServiceStub
import yandexcloud

from app.config.settings import settings


class YandexCloudHandler(logging.Handler):
    def __init__(self, log_group_id, sa_key):
        super().__init__()
        self.log_group_id = log_group_id
        sdk = yandexcloud.SDK(service_account_key=sa_key)
        self.client = sdk.client(LogIngestionServiceStub)

    @staticmethod
    def python_level_to_yc_level(levelno):
        level_map = {
            logging.DEBUG: LogLevel.DEBUG,
            logging.INFO: LogLevel.INFO,
            logging.WARNING: LogLevel.WARN,
            logging.ERROR: LogLevel.ERROR,
            logging.CRITICAL: LogLevel.FATAL,
        }
        return level_map.get(levelno, LogLevel.INFO)

    def emit(self, record):
        try:
            ts = Timestamp()
            ts.GetCurrentTime()

            payload = Struct()
            payload['pathname'] = record.pathname
            payload['filename'] = record.filename
            payload['lineno'] = record.lineno
            payload['logger_name'] = record.name
            payload['funcName'] = record.funcName

            for key, value in record.__dict__.items():
                if key not in ['msg', 'args', 'levelname'] and value is not None:
                    payload[key] = str(value)

            entry = IncomingLogEntry(
                timestamp=ts,
                level=self.python_level_to_yc_level(record.levelno),
                message=record.getMessage(),
                json_payload=payload,
                stream_name="app"
            )

            write_request = WriteRequest(
                destination=Destination(log_group_id=self.log_group_id),
                entries=[entry]
            )

            self.client.Write(write_request)
        except Exception as e:
            logging.getLogger().error(f"Yandex handler failed: {e}")


def get_yc_handler() -> logging.Handler:
    log_group_id = settings.yc_logging.log_group_id
    authorized_key_json = base64.b64decode(settings.yc_logging.authorized_key).decode('utf-8')
    authorized_key_dict = json.loads(authorized_key_json)

    sa_key = {
        "id": authorized_key_dict['id'],
        "service_account_id": authorized_key_dict['service_account_id'],
        "private_key": authorized_key_dict['private_key']
    }
    return YandexCloudHandler(log_group_id, sa_key)


def setup_logging():
    logger = logging.getLogger("parser_social_media")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(get_yc_handler())

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        logger.addHandler(console_handler)

    return logger
