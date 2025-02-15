#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.


import hashlib
from runtime import PlcStatus


class ConnectorBase(object):

    chuncksize = 1024*1024

    PLCObjDefaults = {
        "StartPLC": False,
        "GetTraceVariables": (PlcStatus.Broken, None),
        "GetPLCstatus": (PlcStatus.Broken, None),
        "RemoteExec": (-1, "RemoteExec script failed!"),
        "GetVersions": "*** Unknown ***"
    }

    def BlobFromFile(self, filepath, seed):
        s = hashlib.new('md5')
        s.update(seed.encode())
        blobID = self.SeedBlob(seed.encode())
        with open(filepath, "rb") as f:
            while blobID == s.digest():
                chunk = f.read(self.chuncksize)
                if len(chunk) == 0:
                    return blobID
                blobID = self.AppendChunkToBlob(chunk, blobID)
                s.update(chunk)
        raise IOError("Data corrupted during transfer or connection lost")
