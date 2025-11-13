import logging
import threading
import datetime

import tango

from sqlalchemy import Column, Integer, String, DateTime, Double, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker, scoped_session
import os
import json
import time
import platform
import sys
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)
Base = declarative_base()


class Logs(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    attr = Column(String)
    value = Column(String)


class AttributeLogger:
    def __init__(self, db_path):
        self.db_path = db_path
        self.attributes_dict = self.read_attributes_dictionary()
        self.time_attr = tango.AttributeProxy("other/Clock/clock/time")
        self.daytime_start = datetime.time(6, 0, 0)  # 6:00 AM
        self.daytime_end = datetime.time(22, 0, 0)  # 10:00 PM
        self.connect_db()

    def connect_db(self):
        engine = create_engine(
            f'sqlite:///{self.db_path}')  # Example for SQLite
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine)
        self.Session = scoped_session(SessionLocal)

    def read_attributes_dictionary(self):
        with open(os.path.join(os.path.dirname(__file__), 'attributes_to_log.json'), 'r') as f:
            attributes_dict = json.load(f)
        return attributes_dict

    def start_threading(self):
        for attr, config in self.attributes_dict.items():
            if not config or 'interval' not in config:
                config['interval'] = 60  # default to 60 seconds
            self.log_attribute_value(attr, config)

    def get_time(self):
        try:
            value = self.time_attr.read().value
        except Exception as e:
            print(
                f"Error getting time from clock. Using system time instead.")
            value = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S.%f')
        finally:
            return datetime.datetime.strptime(value, '%Y/%m/%d %H:%M:%S.%f')

    def log_attribute_value(self, attr_name, config):
        current_time = self.get_time()
        if current_time.time() > self.daytime_start and current_time.time() < self.daytime_end:
            t = threading.Timer(config['interval'],
                                self.log_attribute_value, args=[attr_name, config])
        else:
            t = threading.Timer(600,
                                self.log_attribute_value, args=[attr_name, config])
        t.daemon = True
        t.start()
        session = self.Session()
        try:
            attr_proxy = tango.AttributeProxy(attr_name)
            value = attr_proxy.read().value
            new_log = Logs(timestamp=current_time,
                           attr=attr_name, value=value)
            session.add(new_log)
            session.commit()
            logging.info(f"Logging attribute {attr_name}: {value}")
        except Exception as e:
            logging.error(f"Error getting attribute {attr_name}")


if __name__ == "__main__":
    if sys.argv and len(sys.argv) > 1:
        db_file = sys.argv[1]
    elif platform.system() == "Windows":
        db_file = r'Z:\ZEUS_website_resources\lab_log\lab_log.db'
    else:
        db_file = '/mnt/coe-zeus1/ZEUS_website_resources/lab_log/lab_log.db'
    attribute_logger = AttributeLogger(db_file)
    attribute_logger.start_threading()
    while True:
        time.sleep(86400)
