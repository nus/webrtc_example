#!/usr/bin/env python
# coding: utf-8

import json
import os
import tornado.ioloop
import tornado.web
import tornado.websocket
from uuid import uuid4

PORT = 8081
P2P_PATH = r'/websocket/p2p'
PUBLISHER_PATH = r'/websocket/pub'
SUBSCRIBER_PATH = r'/websocket/sub'
KEY_FILE = 'ca.key'
CERT_FILE = 'ca.crt'

class WsPubSubHandler(tornado.websocket.WebSocketHandler):
    subscribers = {}
    publisher = None

    def open(self):
        path = self.request.path
        if self._is_request_publish():
            WsPubSubHandler.publisher = self
            print 'publisher opened, %s' % self.request.remote_ip
        elif self._is_request_subscribe():
            uuid = str(uuid4())
            WsPubSubHandler.subscribers[uuid] = self
            print 'subscriber opened, %s, %s, %d' % (
                uuid, self.request.remote_ip, len(WsPubSubHandler.subscribers))
        else:
            print 'Unexpected path: ' + path

    def on_message(self, message):
        if self._is_request_subscribe() and WsPubSubHandler.publisher != None:
            uuid = self._get_uuid()
            if not uuid:
                print 'Error, no uuid value which is related self'
                return

            d = json.loads(message)
            d['uuid'] = uuid
            WsPubSubHandler.publisher.write_message(json.dumps(d))
        elif self._is_request_publish():
            d = json.loads(message)
            uuid = d.get('uuid', None)
            if not uuid:
                print 'Error, no uuid value in message'
                return

            sub = WsPubSubHandler.subscribers.get(uuid, None)
            if not sub:
                print 'Error, no subscriber with "%s"' % uuid
                return

            del d['uuid']
            sub.write_message(json.dumps(d))
        else:
            print 'Error, unexpected.'
            print self.request.path
            print message

    def on_close(self):
        if self._is_request_subscribe():
            self._close_client(WsPubSubHandler.subscribers)
        elif self._is_request_publish():
            print 'publisher closed, %s' % self.request.remote_ip
            WsPubSubHandler.publisher = None

    def _get_uuid(self):
        for uuid, sub in WsPubSubHandler.subscribers.iteritems():
            if sub == self:
                return uuid
        return None

    def _is_request_publish(self):
        return self.request.path == PUBLISHER_PATH

    def _is_request_subscribe(self):
        return self.request.path == SUBSCRIBER_PATH

    def _close_client(self, clients):
        for uid, client in clients.iteritems():
            if self == client:
                del clients[uid]
                print 'subscriber closed, %s, %s, %d' % (
                    uid, self.request.remote_ip,
                    len(WsPubSubHandler.subscribers))
                return True
        return False

class WsP2pHandler(tornado.websocket.WebSocketHandler):
    _clients = set()

    def open(self):
        self._clients.add(self)

    def on_message(self, message):
        for c in self._clients:
            if c == self:
                continue

            c.write_message(message)

    def on_close(self):
        self._clients.remove(self)

class MainHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header(
            'Cache-Control',
            'no-store, no-cache, must-revalidate, max-age=0')


application = tornado.web.Application([
    (PUBLISHER_PATH, WsPubSubHandler),
    (SUBSCRIBER_PATH, WsPubSubHandler),
    (r"/(.*)", MainHandler, {'path': './', 'default_filename': 'index.html'}),
])

def generate_key(key_name):
    assert os.system('openssl genrsa 2048 > %s' % key_name) == 0

def generate_cert(key_name, cert_name):
    csr = 'ca.csr'
    assert os.system('openssl req -new -key %s > %s'
        % (key_name, csr)) == 0
    assert os.system('openssl x509 -days 3650 -req -signkey %s < %s > %s'
        % (key_name, csr, cert_name)) == 0
    os.remove(csr)

if __name__ == "__main__":
    if not os.path.exists(KEY_FILE):
        generate_key(KEY_FILE)
    if not os.path.exists(CERT_FILE):
        generate_cert(KEY_FILE, CERT_FILE)

    http_server =   tornado.httpserver.HTTPServer(application, ssl_options={
        'certfile': CERT_FILE,
        'keyfile': KEY_FILE
    })
    http_server.listen(PORT)
    tornado.ioloop.IOLoop.current().start()
