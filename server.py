#!/usr/bin/python2
# Author: Richard Murri
# Date: 9/4/07

# This file is an implementation of an sftp server using python 1.5 and paramiko.  To customize this to your own needs
# search for each line in the file that starts with 'FIX', then follow the instructions.  A little
# programming knowledge may be required.

# Obviously, you may want to change the way I authenticate and make it more powerful (add password
# authentication, etc.)  It should be fairly easy to change.  I assume if you are going to try then
# you'll be up to the task.  Feel free to use (and mangle) the code in any way.  I just ask you to
# leave my name as the author (or one of the authors).  Let me know of any improvements!


from __future__ import with_statement
import base64, os, socket, sys, threading, traceback, paramiko, binascii, utils, configure

# setup
privateKey = '/etc/ssh/ssh_host_rsa_key'    # FIX - change this to the path of the server private key
openSocket = 2200    # FIX - change this to the port that sftp will run on

customers = {}
# FIX - add correct users that can login, their chroot folders and their public key files
customers['richard'] = ('/home/richard', '/home/richard/.ssh/id_rsa.pub')
customers['murri'] = ('/home/murri', '/home/murri/.ssh/id_rsa.pub')

# get host private key
host_key = paramiko.RSAKey(filename=privateKey)

class Server (paramiko.ServerInterface):
    """ Implements an SSH server """
    customerInfo = None

    def check_channel_request(self, kind, chanid):
        """ Only allow session requests """
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_publickey(self, username, key):
        """ Ensure proper authentication """
        customer = customers[username]

        if customer:
            # perform validation of customer
            line = customer[1]
            
            line = None
            with open(file) as f:
                line = f.readline()

            filekey = line.split(' ')[1]
            custKey = paramiko.RSAKey(data=base64.decodestring(filekey))

            if custKey == key:
                self.customer = customer
                return paramiko.AUTH_SUCCESSFUL

        return paramiko.AUTH_FAILED

    #def check_auth_password (self, username, password):
    #   return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        """ Only allow public key authentication """

        return 'publickey'
        # return 'publickey', 'password'


class SFTPHandle (paramiko.SFTPHandle):
    """ Represents a handle to an open file """
    def stat(self):
        try:
            return paramiko.SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))
        except OSError, e:
            return paramiko.SFTPServer.convert_errno(e.errno)

class SFTPServer (paramiko.SFTPServerInterface):
    def __init__(self, server, *largs, **kwargs):
        """ Make customer information accessible as well as set chroot jail directory """
        self.customer = server.customer
        self.ROOT = self.customer[0]
        
    def _realpath(self, path):
        """ Enforce the chroot jail """
        path = self.ROOT + self.canonicalize(path)
        return path

    def list_folder(self, path):
        """ List the contents of a folder """
        path = self._realpath(path)
        try:
            out = []
            flist = os.listdir(path)
            for fname in flist:
                attr = paramiko.SFTPAttributes.from_stat(os.stat(os.path.join(path, fname)))
                attr.filename = fname
                out.append(attr)
            return out
        except OSError, e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def stat(self, path):
        path = self._realpath(path)
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(path))
        except OSError, e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def lstat(self, path):
        path = self._realpath(path)
        try:
            return paramiko.SFTPAttributes.from_stat(os.lstat(path))
        except OSError, e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def open(self, path, flags, attr):
        path = self._realpath(path)
        try:
            binary_flag = getattr(os, 'O_BINARY',  0)
            flags |= binary_flag
            mode = getattr(attr, 'st_mode', None)
            if mode is not None:
                fd = os.open(path, flags, mode)
            else:
                # os.open() defaults to 0777 which is
                # an odd default mode for files
                fd = os.open(path, flags, 0666)
        except OSError, e:
            return paramiko.SFTPServer.convert_errno(e.errno)
        if (flags & os.O_CREAT) and (attr is not None):
            attr._flags &= ~attr.FLAG_PERMISSIONS
            paramiko.SFTPServer.set_file_attr(path, attr)
        if flags & os.O_WRONLY:
            if flags & os.O_APPEND:
                fstr = 'ab'
            else:
                fstr = 'wb'
        elif flags & os.O_RDWR:
            if flags & os.O_APPEND:
                fstr = 'a+b'
            else:
                fstr = 'r+b'
        else:
            # O_RDONLY (== 0)
            fstr = 'rb'
        try:
            f = os.fdopen(fd, fstr)
        except OSError, e:
            return paramiko.SFTPServer.convert_errno(e.errno)
        fobj = SFTPHandle(flags)
        fobj.filename = path
        fobj.readfile = f
        fobj.writefile = f
        return fobj

    def remove(self, path):
        """ Remove a file """
        return paramiko.SFTP_OK

    def rename(self, oldpath, newpath):
        return paramiko.SFTP_OK

    def mkdir(self, path, attr):
        return paramiko.SFTP_OK

    def rmdir(self, path):
        return paramiko.SFTP_OK

    def chattr(self, path, attr):
        return paramiko.SFTP_OK

    def symlink(self, target_path, path):
        return paramiko.SFTP_OK

    def readlink(self, path):
        return paramiko.SFTP_NO_SUCH_FILE

# bind the socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', openSocket))

# listen for a connection
sock.listen(5)

# accept connections
while True:
    client, addr = sock.accept()

    try:
        # set up server
        t = paramiko.Transport(client)
        t.load_server_moduli()
        t.add_server_key(host_key)

        # set up sftp handler
        t.set_subsystem_handler('sftp', paramiko.SFTPServer, SFTPServer)
        server = Server()
        event = threading.Event()

        # start ssh server session
        t.start_server(event, server)

    except Exception, e:
        try:
            t.close()
        except:
            pass
        raise

