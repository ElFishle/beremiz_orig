#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING file for copyrights details.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


from time import sleep
import copy
import socket
import os.path

import Pyro5
import Pyro5.client
import Pyro5.errors

# TODO: PSK

import importlib


Pyro5.config.SERIALIZER = "msgpack"


def PYRO_connector_factory(uri, confnodesroot):
    """
    This returns the connector to Pyro style PLCobject
    """
    confnodesroot.logger.write(_("PYRO connecting to URI : %s\n") % uri)

    scheme, location = uri.split("://")

    # TODO: use ssl

    schemename = "PYRO"

    # Try to get the proxy object
    try:
        RemotePLCObjectProxy = Pyro5.client.Proxy(f"{schemename}:PLCObject@{location}")
    except Exception as e:
        confnodesroot.logger.write_error(
            _("Connection to {loc} failed with exception {ex}\n").format(
                loc=location, ex=str(e)))
        return None

    RemotePLCObjectProxy._pyroTimeout = 60

    class MissingCallException(Exception):
        pass

    def PyroCatcher(func, default=None):
        """
        A function that catch a Pyro exceptions, write error to logger
        and return default value when it happen
        """
        def catcher_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Pyro5.errors.ConnectionClosedError as e:
                confnodesroot._SetConnector(None)
                confnodesroot.logger.write_error(_("Connection lost!\n"))
            except Pyro5.errors.ProtocolError as e:
                confnodesroot.logger.write_error(_("Pyro exception: %s\n") % e)
            except MissingCallException as e:
                confnodesroot.logger.write_warning(_("Remote call not supported: %s\n") % e.message)
            except Exception as e:
                errmess = ''.join(Pyro5.errors.get_pyro_traceback())
                confnodesroot.logger.write_error(errmess + "\n")
                print(errmess)
                confnodesroot._SetConnector(None)
            return default
        return catcher_func

    # Check connection is effective.
    # lambda is for getattr of GetPLCstatus to happen inside catcher
    IDPSK = PyroCatcher(RemotePLCObjectProxy.GetPLCID)()
    if IDPSK is None:
        confnodesroot.logger.write_warning(_("PLC did not provide identity and security infomation.\n"))
    else:
        ID, secret = IDPSK
        PSK.UpdateID(confnodesroot.ProjectPath, ID, secret, uri)

    class PyroProxyProxy(object):
        """
        A proxy proxy class to handle Beremiz Pyro interface specific behavior.
        And to put Pyro exception catcher in between caller and Pyro proxy
        """
        def __getattr__(self, attrName):
            member = self.__dict__.get(attrName, None)
            if member is None:
                def my_local_func(*args, **kwargs):
                    call = RemotePLCObjectProxy.__getattr__(attrName)
                    if call is None:
                        raise MissingCallException(attrName)
                    else:
                        return call(*args, **kwargs)
                member = PyroCatcher(my_local_func, self.PLCObjDefaults.get(attrName, None))
                self.__dict__[attrName] = member
            return member

    return PyroProxyProxy
