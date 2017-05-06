'use strict';

class SignalingChannel {
  constructor(childPath) {
    this.onmessage = null;
    this.onopen = null;
    this.onclose = null;

    this._ws = new WebSocket('wss://' + window.location.host + '/websocket' + (childPath ? childPath : ''));
    this._ws.onmessage = function(e) {
      if (this.onmessage) {
        this.onmessage(e);
      }
    }.bind(this);
    this._ws.onopen = function(e) {
      if (this.onopen) {
        this.onopen(e);
      }
    }.bind(this);
    this._ws.onclose = function(e) {
      if (this.onclose) {
        this.onclose(e);
      }
    }.bind(this);
  }

  send(msg) {
    this._ws.send(msg);
  }
}
