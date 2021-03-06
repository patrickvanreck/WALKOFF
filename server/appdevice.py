import json
from abc import abstractmethod
import core.config.paths
from core.config.config import device_db_type
from core.helpers import format_exception_message, format_db_path
import pyaes
import logging
from sqlalchemy import Column, Integer, ForeignKey, String, create_engine, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session


logger = logging.getLogger(__name__)

Device_Base = declarative_base()


class App(Device_Base):
    __tablename__ = 'app'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    devices = relationship("Device", back_populates="app")

    def __init__(self, app=None, devices=None):
        """Initializes an App object.
        
        Args:
            app (str, optional): The name of the app. Defaults to None.
            devices (list[str], optional): The list of device names to be associated with the App object. There is a
                one to many mapping from Apps to Devices.
        """
        self.name = app
        self.devices = [Device(name=device_name, app_id=app) for device_name in devices]

    def initialize(self):
        # self.api = WalkoffAppDefinition(self.name, self)
        pass

    def as_json(self, with_devices=False):
        """Gets the JSON representation of an App object.

        Returns:
            The JSON representation of an App object.
        """
        output = {'name': self.name}
        if with_devices:
            output['devices'] = [device.as_json() for device in self.devices]
        return output

    @staticmethod
    def get_all_devices_for_app(app_name):
        """ Gets all the devices associated with an app.

        Args:
            app_name (str): The name of the app.
        Returns:
            (list[Device]): A list of devices associated with this app. Returns empty list if app is not in database.
        """
        app = device_db.session.query(App).filter(App.name == app_name).first()
        if app is not None:
            return app.devices
        else:
            logger.warning('Cannot get devices for app {0}. App does not exist'.format(app_name))
            return []

    @staticmethod
    def get_device(app_name, device_name):
        """ Gets the device associated with the app.

        Args:
            app_name (str): The name of the app.
            device_name (str): The name of the device.
        Returns:
            (Device): The desired device. Returns None if app or device not found.
        """
        app = device_db.session.query(App).filter(App.name == app_name).first()
        if app is not None:
            # efficient generator to get first instance of device with matching name. Returns None if not found.
            device = next((device for device in app.devices if device.name == device_name), None)
            if device is not None:
                return device
            else:
                logger.warning('Cannot get device {0} for app {1}. '
                               'Device does not exist for app'.format(device_name, app_name))
                return None
        else:
            logger.warning('Cannot get device {0} for app {1}. App does not exist'.format(device_name, app_name))
            return None

    @abstractmethod
    def shutdown(self):
        pass


class Device(Device_Base):
    __tablename__ = 'device'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    username = Column(String(80))
    password = Column(LargeBinary())
    ip = Column(String(15))
    port = Column(Integer())
    extra_fields = Column(String)
    app_id = Column(String, ForeignKey('app.name'))
    app = relationship(App, back_populates="devices")

    def __init__(self, name, app_id, username="", password=None, ip="0.0.0.0", port=0, extra_fields=""):
        """Initializes a new Device object, which will be associated with an App object.
        
        Args:
            name (str, optional): The name of the Device object. Defaults to an empty string.
            app_id (str): The ID of the App object to which this Device is associated.
            username (str, optional): The username for the Device object. Defaults to an empty string.
            password (str, optional): The password for the Device object. Defaults to an empty string.
            ip (str, optional): The IP address for for the Device object. Defaults to "0.0.0.0".
            port (int, optional): The port for the Device object. Defaults to 0.
            extra_fields (str, optional): The string representation of a dictionary that holds various custom
                extra fields for the Device object. Defaults to an empty string.
        """
        self.name = name
        self.app_id = app_id
        self.username = username
        self.password = password
        self.ip = ip
        self.port = port
        if self.extra_fields != "":
            self.extra_fields = extra_fields.replace("\'", "\"")
        else:
            self.extra_fields = extra_fields

    @staticmethod
    def add_device(name, app_id, username, password, ip, port, extra_fields):
        """Adds a new Device object.
        
        Args:
            name (str, optional): The name of the Device object. Defaults to an empty string.
            app_id (str): The ID of the App object to which this Device is associated.
            username (str, optional): The username for the Device object. Defaults to an empty string.
            password (str, optional): The password for the Device object. Defaults to an empty string.
            ip (str, optional): The IP address for for the Device object. Defaults to "0.0.0.0".
            port (int, optional): The port for the Device object. Defaults to 0.
            extra_fields (str, optional): The string representation of a dictionary that holds various custom
            extra fields for the Device object. Defaults to an empty string.
        """
        device = Device(name=name, username=username, app_id=app_id, password=password, ip=ip, port=port,
                        extra_fields=extra_fields)
        device_db.session.add(device)
        device_db.session.commit()
        logger.info('Adding device {0}'.format(device.as_json(with_apps=False)))
        return device

    def get_password(self):
        """Retrieves the password for a device.

        Returns:
            The decrypted password.
        """
        try:
            with open(core.config.paths.AES_key_path, 'rb') as key_file:
                key = key_file.read()
        except (OSError, IOError):
            logger.error('No AES key found')
            return None
        else:
            aes = pyaes.AESModeOfOperationCTR(key)
            return aes.decrypt(self.password)

    def edit_device(self, data):
        """Edits various fields of the Device object. 
        
        Args:
            data (dict): The data object containing the fields that the user wishes to change.
        """
        if 'name' in data and data['name']:
            self.name = data['name']

        if 'app' in data and data['app']:
            self.app_id = data['app']

        if 'username' in data and data['username']:
            self.username = data['username']

        if 'password' in data and data['password']:
            try:
                with open(core.config.paths.AES_key_path, 'rb') as key_file:
                    key = key_file.read()
            except (OSError, IOError) as e:
                logger.error('Error loading AES key from from {0}: '
                                         '{1}'.format(core.config.paths.AES_key_path, format_exception_message(e)))
            else:
                aes = pyaes.AESModeOfOperationCTR(key)
                pw = data['password']
                self.password = aes.encrypt(pw)

        if 'ip' in data and data['ip']:
            self.ip = data['ip']

        if 'port' in data and data['port']:
            self.port = data['port']

        if 'extraFields' in data and data['extraFields']:
            fields_dict = json.loads(data['extraFields'].replace("\'", "\""))
            if self.extra_fields == "":
                self.extra_fields = data['extraFields']
            else:
                extra_fields = json.loads(self.extra_fields)
                for field in fields_dict:
                    extra_fields[field] = fields_dict[field]
                self.extra_fields = json.dumps(extra_fields)

    def as_json(self, with_apps=False):
        """Gets the JSON representation of a Device object.
        
        Args:
            with_apps (bool, optional): A boolean to determine whether or not to include the App to which the Device
                is associated in the JSON output. Defaults to True.
                
        Returns:
            The JSON representation of a Device object.
        """
        output = {'id': self.id, 'name': self.name, 'username': self.username, 'ip': self.ip,
                  'port': self.port}
        if with_apps:
            output['app'] = self.app.as_json()
        else:
            output['app'] = self.app.name
        if self.extra_fields:
            extra_fields = json.loads(self.extra_fields)
            for field in extra_fields:
                output[field] = extra_fields[field]
        return output

    def __repr__(self):
        return str({"name": self.name, "username": self.username, "password": self.password,
                    "ip": self.ip, "port": str(self.port), "app": self.app.as_json()})


class DeviceDatabase(object):
    """
    Wrapper for the SQLAlchemy Case database object
    """

    def __init__(self):
        self.engine = create_engine(format_db_path(core.config.config.device_db_type, core.config.paths.device_db_path))
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()

        Session = sessionmaker()
        Session.configure(bind=self.engine)
        self.session = scoped_session(Session)

        Device_Base.metadata.bind = self.engine
        Device_Base.metadata.create_all(self.engine)


def get_device_db(_singleton=DeviceDatabase()):
    """ Singleton factory which returns the case database"""
    return _singleton


device_db = get_device_db()

