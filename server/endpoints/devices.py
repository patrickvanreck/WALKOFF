import json
from flask import current_app, request
from server.security import roles_accepted_for_resources
from flask_jwt_extended import jwt_required
import core.config.config
import core.config.paths
from server.returncodes import *
import pyaes
from server.appdevice import Device, App, device_db


def read_all_devices():

    @jwt_required
    @roles_accepted_for_resources('apps')
    def __func():
        query = device_db.session.query(Device).all()
        output = []
        if query:
            for device in query:
                output.append(device.as_json())
        return output, SUCCESS

    return __func()


def import_devices():

    @jwt_required
    @roles_accepted_for_resources('apps')
    def __func():
        data = request.get_json()
        filename = data['filename'] if 'filename' in data else core.config.paths.default_appdevice_export_path
        try:
            with open(filename, 'r') as devices_file:
                read_file = devices_file.read()
                read_file = read_file.replace('\n', '')
                apps_devices = json.loads(read_file)
        except (OSError, IOError) as e:
            current_app.logger.error('Error importing devices from {0}: {1}'.format(filename, e))
            return {"error": "Error reading file."}, IO_ERROR
        for app in apps_devices:
            for device in apps_devices[app]:
                extra_fields = {}
                for key in device:
                    if key not in ['ip', 'name', 'port', 'username']:
                        extra_fields[key] = device[key]
                extra_fields_str = json.dumps(extra_fields)
                Device.add_device(name=device['name'], username=device['username'], ip=device['ip'],
                                                  port=device['port'], extra_fields=extra_fields_str, password=None,
                                                  app_id=app)
        current_app.logger.debug('Imported devices from {0}'.format(filename))
        return {}, SUCCESS

    return __func()


def export_devices():

    @jwt_required
    @roles_accepted_for_resources('apps')
    def __func():
        data = request.get_json()
        filename = data['filename'] if 'filename' in data else core.config.paths.default_appdevice_export_path
        returned_json = {}
        apps = device_db.session.query(App).all()
        for app in apps:
            devices = []
            for device in app.devices:
                device_json = device.as_json()
                device_json.pop('app', None)
                device_json.pop('id', None)
                devices.append(device_json)
            returned_json[app.as_json()['name']] = devices
        try:
            with open(filename, 'w') as appdevice_file:
                appdevice_file.write(json.dumps(returned_json, indent=4, sort_keys=True))
        except (OSError, IOError) as e:
            current_app.logger.error('Error importing devices from {0}: {1}'.format(filename, e))
            return {"error": "Error writing file"}, IO_ERROR
        else:
            current_app.logger.debug('Exported devices to {0}'.format(filename))
            return {}, SUCCESS

    return __func()


def read_device(device_id):

    @jwt_required
    @roles_accepted_for_resources('apps')
    def __func():
        dev = device_db.session.query(Device).filter(Device.id == device_id).first()
        if dev is not None:
            return dev.as_json(), SUCCESS
        else:
            current_app.logger.error('Could not read device {0}. '
                                     'Device does not exist'.format(device_id))
            return {"error": "Device does not exist."}, OBJECT_DNE_ERROR

    return __func()


def delete_device(device_id):

    @jwt_required
    @roles_accepted_for_resources('apps')
    def __func():
        dev = device_db.session.query(Device).filter(Device.id == device_id).first()
        if dev is not None:
            device_db.session.delete(dev)
            current_app.logger.info('Device removed {0}'.format(device_id))
            device_db.session.commit()
            return {}, SUCCESS
        else:
            current_app.logger.error('Could not delete device {0}. '
                                     'Device does not exist'.format(device_id))
            return {"error": "Device does not exist"}, OBJECT_DNE_ERROR

    return __func()


def create_device():

    @jwt_required
    @roles_accepted_for_resources('apps')
    def __func():
        data = request.get_json()
        if len(device_db.session.query(Device).filter(Device.name == data['name']).all()) > 0:
            current_app.logger.error('Could not create device {0}. '
                                     'Device already exists.'.format(data['name']))
            return {"error": "Device already exists."}, OBJECT_EXISTS_ERROR

        try:
            with open(core.config.paths.AES_key_path, 'rb') as key_file:
                key = key_file.read()
        except (OSError, IOError) as e:
            current_app.logger.error('Could not create device. '
                                     'Could not get key from AES key file. '
                                     'Error: {}'.format(e))
            return {"error": "Could not read key from AES key file."}, INVALID_INPUT_ERROR
        else:
            aes = pyaes.AESModeOfOperationCTR(key)
            pw = data['password'] if 'password' in data else ''
            enc_pw = aes.encrypt(pw)

        dev = Device.add_device(name=data['name'],
                                                username=data['username'] if 'username' in data else '',
                                                password=enc_pw,
                                                ip=data['ip'] if 'ip' in data else '',
                                                port=data['port'] if 'port' in data else '',
                                                extra_fields=data['extraFields'] if 'extraFields' in data else '',
                                                app_id=data['app'])
        return dev.as_json(), OBJECT_CREATED

    return __func()


def update_device():

    @jwt_required
    @roles_accepted_for_resources('apps')
    def __func():
        data = request.get_json()
        dev = device_db.session.query(Device).filter(Device.id == data['id']).first()
        if dev is not None:
            dev.edit_device(data)
            device_db.session.commit()
            current_app.logger.info('Editing device {0}:{1} to {2}'.format(dev.app_id,
                                                                           dev.name,
                                                                           dev.as_json(with_apps=False)))

            return dev.as_json(), SUCCESS
        else:
            current_app.logger.error('Could not update device {0}. '
                                     'Device does not exist'.format(data['id']))
            return {"error": "Device does not exist"}, OBJECT_DNE_ERROR

    return __func()
