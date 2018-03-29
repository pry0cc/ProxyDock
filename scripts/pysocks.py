#!/usr/bin/env python
from SocketServer import BaseServer, ThreadingTCPServer, StreamRequestHandler
from socket import socket, AF_INET, SOCK_STREAM
import logging
import signal
import struct
import sys
import thread
import os
import platform

__author__ = 'Youchao Feng'
support_os = ('Darwin', 'Linux')
current_os = platform.system()


def byte_to_int(b):
    """
    Convert Unsigned byte to int
    :param b: byte value
    :return:  int value
    """
    return b & 0xFF


def port_from_byte(b1, b2):
    """

    :param b1: First byte of port
    :param b2: Second byte of port
    :return: Port in Int
    """
    return byte_to_int(b1) << 8 | byte_to_int(b2)


def host_from_ip(a, b, c, d):
    a = byte_to_int(a)
    b = byte_to_int(b)
    c = byte_to_int(c)
    d = byte_to_int(d)
    return "%d.%d.%d.%d" % (a, b, c, d)


def get_command_name(value):
    """
    Gets command name by value
    :param value:  value of Command
    :return: Command Name
    """
    if value == 1:
        return 'CONNECT'
    elif value == 2:
        return 'BIND'
    elif value == 3:
        return 'UDP_ASSOCIATE'
    else:
        return None


def build_command_response(reply):
    start = b'\x05%s\x00\x01\x00\x00\x00\x00\x00\x00'
    return start % reply.get_byte_string()


def close_session(session):
    session.get_client_socket().close()
    logging.info("Session[%s] closed" % session.get_id())


def run_daemon_process(stdout='/dev/null', stderr=None, stdin='/dev/null',
                       pid_file=None, start_msg='started with pid %s'):
    """
         This forks the current process into a daemon.
         The stdin, stdout, and stderr arguments are file names that
         will be opened and be used to replace the standard file descriptors
         in sys.stdin, sys.stdout, and sys.stderr.
         These arguments are optional and default to /dev/null.
        Note that stderr is opened unbuffered, so
        if it shares a file with stdout then interleaved output
         may not appear in the order that you expect.
    """
    # flush io
    sys.stdout.flush()
    sys.stderr.flush()
    # Do first fork.
    try:
        if os.fork() > 0:
            sys.exit(0)  # Exit first parent.
    except OSError, e:
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror))
        sys.exit(1)
    # Decouple from parent environment.
    os.chdir("/")
    os.umask(0)
    os.setsid()
    # Do second fork.
    try:
        if os.fork() > 0:
            sys.exit(0)  # Exit second parent.
    except OSError, e:
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror))
        sys.exit(1)
    # Open file descriptors and print start message
    if not stderr:
        stderr = stdout
        si = file(stdin, 'r')
        so = file(stdout, 'a+')
        se = file(stderr, 'a+', 0)  # unbuffered
        pid = str(os.getpid())
        sys.stderr.write(start_msg % pid)
        sys.stderr.flush()
    if pid_file:
        file(pid_file, 'w+').write("%s\n" % pid)
    # Redirect standard file descriptors.
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())


class Session(object):
    index = 0

    def __init__(self, client_socket):
        Session.index += 1
        self.__id = Session.index
        self.__client_socket = client_socket
        self._attr = {}

    def get_id(self):
        return self.__id

    def set_attr(self, key, value):
        self._attr[key] = value

    def get_client_socket(self):
        return self.__client_socket


class AddressType(object):
    IPV4 = 1
    DOMAIN_NAME = 3
    IPV6 = 4


class SocksCommand(object):
    CONNECT = 1
    BIND = 2
    UDP_ASSOCIATE = 3


class SocksMethod(object):
    NO_AUTHENTICATION_REQUIRED = 0
    GSS_API = 1
    USERNAME_PASSWORD = 2


class ServerReply(object):
    def __init__(self, value):
        self.__value = value

    def get_byte_string(self):
        if self.__value == 0:
            return b'\x00'
        elif self.__value == 1:
            return b'\x01'
        elif self.__value == 2:
            return b'\x02'
        elif self.__value == 3:
            return b'\x03'
        elif self.__value == 4:
            return b'\x04'
        elif self.__value == 5:
            return b'\x05'
        elif self.__value == 6:
            return b'\x06'
        elif self.__value == 7:
            return b'\x07'
        elif self.__value == 8:
            return b'\x08'

    def get_value(self):
        return self.__value


class ReplyType(object):
    SUCCEEDED = ServerReply(0)
    GENERAL_SOCKS_SERVER_FAILURE = ServerReply(1)
    CONNECTION_NOT_ALLOWED_BY_RULESET = ServerReply(2)
    NETWORK_UNREACHABLE = ServerReply(3)
    HOST_UNREACHABLE = ServerReply(4)
    CONNECTION_REFUSED = ServerReply(5)
    TTL_EXPIRED = ServerReply(6)
    COMMAND_NOT_SUPPORTED = ServerReply(7)
    ADDRESS_TYPE_NOT_SUPPORTED = ServerReply(8)


class SocketPipe(object):
    BUFFER_SIZE = 1024 * 1024

    def __init__(self, socket1, socket2):
        self._socket1 = socket1
        self._socket2 = socket2
        self.__running = False

    def __transfer(self, socket1, socket2):
        while self.__running:
            try:
                data = socket1.recv(self.BUFFER_SIZE)
                if len(data) > 0:
                    socket2.sendall(data)
                else:
                    break
            except IOError:
                self.stop()
        self.stop()

    def start(self):
        self.__running = True
        thread.start_new_thread(self.__transfer, (self._socket1, self._socket2))
        thread.start_new_thread(self.__transfer, (self._socket2, self._socket1))

    def stop(self):
        self._socket1.close()
        self._socket2.close()
        self.__running = False

    def is_running(self):
        return self.__running


class CommandExecutor(object):
    def __init__(self, remote_server_host, remote_server_port, session):
        self.__proxy_socket = socket(AF_INET, SOCK_STREAM)
        self.__remote_server_host = remote_server_host
        self.__remote_server_port = remote_server_port
        self.__client = session.get_client_socket()
        self.__session = session

    def do_connect(self):
        """
        Do SOCKS CONNECT method
        :return: None
        """
        result = self.__proxy_socket.connect_ex(self.__get_address())
        if result == 0:
            self.__client.send(build_command_response(ReplyType.SUCCEEDED))
            socket_pipe = SocketPipe(self.__client, self.__proxy_socket)
            socket_pipe.start()
            while socket_pipe.is_running():
                pass
        elif result == 60:
            self.__client.send(build_command_response(ReplyType.TTL_EXPIRED))
        elif result == 61:
            self.__client.send(build_command_response(ReplyType.NETWORK_UNREACHABLE))
        else:
            logging.error('Connection Error:[%s] is unknown' % result)
            self.__client.send(build_command_response(ReplyType.NETWORK_UNREACHABLE))

    def do_bind(self):
        pass

    def do_udp_associate(self):
        pass

    def __get_address(self):
        return self.__remote_server_host, self.__remote_server_port


class User(object):
    def __init__(self, username, password):
        self.__username = username
        self.__password = password

    def get_username(self):
        return self.__username

    def get_password(self):
        return self.__password

    def __repr__(self):
        return '<user: username=%s, password=%s>' % (self.get_username(), self.__password)


class UserManager(object):
    def __init__(self):
        self.__users = {}

    def add_user(self, user):
        self.__users[user.get_username()] = user

    def remove_user(self, username):
        if username in self.__users:
            del self.__users[username]

    def check(self, username, password):
        if username in self.__users and self.__users[username].get_password() == password:
            return True
        else:
            return False

    def get_user(self, username):
        return self.__users[username]

    def get_users(self):
        return self.__users


class Socks5RequestHandler(StreamRequestHandler):
    def __init__(self, request, client_address, server):
        StreamRequestHandler.__init__(self, request, client_address, server)

    def handle(self):
        session = Session(self.connection)
        logging.info('Create session[%s] for %s:%d' % (
            1, self.client_address[0], self.client_address[1]))
        print self.server.allowed
        if self.server.allowed and self.client_address[0] not in self.server.allowed:
            close_session(session)
            return
        client = self.connection
        client.recv(1)
        method_num, = struct.unpack('b', client.recv(1))
        methods = struct.unpack('b' * method_num, client.recv(method_num))
        auth = self.server.is_auth()
        if methods.__contains__(SocksMethod.NO_AUTHENTICATION_REQUIRED) and not auth:
            client.send(b"\x05\x00")
        elif methods.__contains__(SocksMethod.USERNAME_PASSWORD) and auth:
            client.send(b"\x05\x02")
            if not self.__do_username_password_auth():
                logging.info('Session[%d] authentication failed' % session.get_id())
                close_session(session)
                return
        else:
            client.send(b"\x05\xFF")
            return
        version, command, reserved, address_type = struct.unpack('b' * 4, client.recv(4))
        host = None
        port = None
        if address_type == AddressType.IPV4:
            ip_a, ip_b, ip_c, ip_d, p1, p2 = struct.unpack('b' * 6, client.recv(6))
            host = host_from_ip(ip_a, ip_b, ip_c, ip_d)
            port = port_from_byte(p1, p2)
        elif address_type == AddressType.DOMAIN_NAME:
            host_length, = struct.unpack('b', client.recv(1))
            host = client.recv(host_length)
            p1, p2 = struct.unpack('b' * 2, client.recv(2))
            port = port_from_byte(p1, p2)
        else:  # address type not support
            client.send(build_command_response(ReplyType.ADDRESS_TYPE_NOT_SUPPORTED))

        command_executor = CommandExecutor(host, port, session)
        if command == SocksCommand.CONNECT:
            logging.info("Session[%s] Request connect %s:%d" % (session.get_id(), host, port))
            command_executor.do_connect()
        close_session(session)

    def __do_username_password_auth(self):
        client = self.connection
        client.recv(1)
        length = byte_to_int(struct.unpack('b', client.recv(1))[0])
        username = client.recv(length)
        length = byte_to_int(struct.unpack('b', client.recv(1))[0])
        password = client.recv(length)
        user_manager = self.server.get_user_manager()
        if user_manager.check(username, password):
            client.send(b"\x01\x00")
            return True
        else:
            client.send(b"\x01\x01")
            return False


class Socks5Server(ThreadingTCPServer):
    """
    SOCKS5 proxy server
    """

    def __init__(self, port, auth=False, user_manager=UserManager(), allowed=None):
        ThreadingTCPServer.__init__(self, ('', port), Socks5RequestHandler)
        self.__port = port
        self.__users = {}
        self.__auth = auth
        self.__user_manager = user_manager
        self.__sessions = {}
        self.allowed = allowed

    def serve_forever(self, poll_interval=0.5):
        logging.info("Create SOCKS5 server at port %d" % self.__port)
        ThreadingTCPServer.serve_forever(self, poll_interval)

    def finish_request(self, request, client_address):
        BaseServer.finish_request(self, request, client_address)

    def is_auth(self):
        return self.__auth

    def set_auth(self, auth):
        self.__auth = auth

    def get_all_managed_session(self):
        return self.__sessions

    def get_bind_port(self):
        return self.__port

    def get_user_manager(self):
        return self.__user_manager

    def set_user_manager(self, user_manager):
        self.__user_manager = user_manager


def show_help():
    print 'Usage: start|stop|restart|status [options]'
    print 'Options:'
    print '  --port=<val>         Sets server port, default 1080'
    print '  --log=true|false     Logging on, default true'
    print '  --allowed=IP         set allowed IP list'
    print '  --auth:<user:pwd>    Use username/password authentication'
    print '                       Example:'
    print '                         Create user \"admin\" with password \"1234\":'
    print '                           --auth=admin:1234 '
    print '                         Create tow users:'
    print '                           --auth=admin:1234,root:1234'
    print '  -h                   Show Help'


def check_os_support():
    if not support_os.__contains__(current_os):
        print 'Not support in %s' % current_os
        sys.exit()


def stop(pid_file):
    check_os_support()
    print 'Stopping server...',
    try:
        f = open(pid_file, 'r')
        pid = int(f.readline())
        os.kill(pid, signal.SIGTERM)
        os.remove(pid_file)
        print "                 [OK]"
    except IOError:
        print "pysocks is not running"
    except OSError:
        print "pysocks is not running"


def status(pid_file):
    check_os_support()
    try:
        f = open(pid_file, 'r')
        pid = int(f.readline())
        print 'pysocks(pid %d) is running...' % pid
    except IOError:
        print "pysocks is stopped"


def main():
    port = 1080
    enable_log = True
    log_file = 'socks.log'
    auth = False
    user_home = os.path.expanduser('~')
    pid_file = user_home + '/.pysocks.pid'
    user_manager = UserManager()
    allowed_ips = None

    if sys.argv.__len__() < 2:
        show_help()
        sys.exit()

    command = sys.argv[1]
    if command == 'start':
        pass
    elif command == 'stop':
        stop(pid_file)
        sys.exit()
    elif command == 'restart':
        stop(pid_file)
    elif command == 'status':
        status(pid_file)
        sys.exit()
    else:
        show_help()
        sys.exit()

    for arg in sys.argv[2:]:
        if arg.startswith('--port='):
            try:
                port = int(arg.split('=')[1])
            except ValueError:
                print '--port=<val>  <val> should be a number'
                sys.exit()
        elif arg.startswith('--auth'):
            auth = True
            users = arg.split('=')[1]
            for user in users.split(','):
                user_pwd = user.split(':')
                user_manager.add_user(User(user_pwd[0], user_pwd[1]))
        elif arg == '-h':
            show_help()
            sys.exit()
        elif arg.startswith('--log='):
            value = arg.split('=')[1]
            if value == 'true':
                enable_log = True
            elif value == 'false':
                enable_log = False
            else:
                print '--log=<val>  <val> should be true or false'
                sys.exit()
        elif arg.startswith('--allowed='):
            value = arg.split('=')[1]
            allowed_ips = value.split(',')
        else:
            print 'Unknown argument:%s' % arg
            sys.exit()
    if enable_log:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(levelname)s - %(message)s',
                            filename=log_file,
                            filemode='a')
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(lineno)-3d - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger().addHandler(console)

    Socks5Server.allow_reuse_address = True
    socks5_server = Socks5Server(port, auth, user_manager, allowed=allowed_ips)
    try:
        if support_os.__contains__(current_os):
            run_daemon_process(pid_file=pid_file, start_msg='Start SOCKS5 server at pid %s\n')
        socks5_server.serve_forever()
    except KeyboardInterrupt:
        socks5_server.server_close()
        socks5_server.shutdown()
        logging.info("SOCKS5 server shutdown")


if __name__ == '__main__':
    main()
