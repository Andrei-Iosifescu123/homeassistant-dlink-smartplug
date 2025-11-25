import socket
import ssl
import json
import hashlib
import time
import random

RSV1 = 64
RSV2 = 32
RSV3 = 16

OP_CONTINUATION =  0
OP_TEXT         =  1
OP_BINARY       =  2
OP_CLOSE        =  8
OP_PING         =  9
OP_PONG         = 10

OPCODES = [
    OP_CONTINUATION,
    OP_TEXT,
    OP_BINARY,
    OP_CLOSE,
    OP_PING,
    OP_PONG
]

FRAGMENTED_OPCODES = [
    OP_CONTINUATION, OP_TEXT, OP_BINARY
]

FIN = 128
MASK = 128
LENGTH = 127
OPCODE = 15

class HybiParser:
    """
    Class is simplified for use with DSP-W245. Some paths are not taken by the
    device and have thus not been implemented.
    """

    def parseOpCode(self, data):
        rsv1 = (data & RSV1) == RSV1
        rsv2 = (data & RSV2) == RSV2
        rsv3 = (data & RSV3) == RSV3

        if rsv1 or rsv2 or rsv3:
            raise ValueError("WebSocket RSV bits not zero - invalid frame")

        self.final = (data & FIN) == FIN
        self.opcode = (data & OPCODE)
        self.mmask = []
        self.payload = []

        if self.opcode not in OPCODES:
            raise ValueError(f"WebSocket bad opcode: {self.opcode}")

        if self.opcode not in FRAGMENTED_OPCODES and not self.final:
            raise ValueError("WebSocket non-final packet for non-fragmentable opcode")

    def parseLength(self, data):
        self.masked = (data & MASK) == MASK
        self.length = (data & LENGTH)

        if self.length >= 0 and self.length <= 125:
            self.stage = 3 if self.masked else 4
        else:
            self.lengthSize = 2 if self.length == 126 else 8
            self.stage = 2

    def byteArrayToLong(self, b, offset, l):
        if len(b) < l:
            raise ValueError(f"WebSocket buffer too short: need {l} bytes, got {len(b)}")
        value = 0
        for i in range(l):
            shift = (l - 1 - i) * 8
            value += (b[i + offset] & 0x000000FF) << shift
        return value

    def getInteger(self, b):
        i = self.byteArrayToLong(b, 0, len(b))
        if i < 0 or i > 2000000000:
            raise ValueError(f"WebSocket bad integer value: {i}")
        return i

    def parseExtendedLength(self, buf):
        self.length = self.getInteger(buf)
        self.stage = 3 if self.masked else 4

    def fn_mask(self, payload, mask, offset):
        if len(mask) == 0:
            return payload
        for i in range(len(payload) - offset):
            payload[offset + i] = payload[offset + i] ^ mask[i % 4]
        return payload

    def d_encode(self, payload):
        r = ''.join([chr(c) for c in payload])
        return r

    def emitFrame(self):
        payload = self.fn_mask(self.payload, self.mmask, 0)
        opcode = self.opcode # This is 1 so I only bother about that.
        if opcode == OP_TEXT:
            if self.final: # This is true so I only bother about this.
                self.messageText = self.d_encode(payload)

    def readbytes(self, n):
        r = self.data[:n]
        self.data = self.data[n:]
        return r

    def __init__(self):
        self.stage = 0
        self.length = None

    def mask(self, payload, mask, offset):
        if len(mask) != 0:
            for i in range(len(payload) - offset):
                payload[offset + i] = payload[offset + i] ^ mask[i % 4]
        return payload

    def encode(self, data):
        """
        opcode = 1, errorCode = -1, masking = true
        Code is simplified for this.
        """
        buf = data.encode()
        length = len(buf)
        header = 0
        if length <= 125:
            header = 2
        else:
            header = 4 if length <= 65535 else 10
        offset = header + 4
        masked = 128
        frame = [0] * (length + offset)
        frame[0] = (1 | -128)
        if length <= 125:
            frame[1] = (masked | length)
        elif length <= 65535:
            frame[1] = (masked | 126)
            frame[2] = length // 256
            frame[3] = (length & 255)
        else:
            # Not implemented since it does not appear to be used.
            pass
        frame[offset:] = buf
        mask = [int(random.random() * 256.0) for _ in range(4)]
        frame[header:header+len(mask)] = mask
        frame = self.mask(frame, mask, offset)
        return frame

    def decode(self, data):
        self.stage = 0
        while True:
            if self.stage == 0:
                self.parseOpCode(data(1))
                self.stage = 1
            elif self.stage == 1:
                self.parseLength(data(1))
            elif self.stage == 2:
                self.parseExtendedLength(data(self.lengthSize))
            elif self.stage == 3:
                self.mmask = data(4)
                self.stage = 4
            elif self.stage == 4:
                self.payload = data(self.length)
                self.emitFrame()
                self.stage = 0
                break
        return self.messageText

class SmartPlug:

    def __init__(self, host, pin, model="W245", verbose=0):
        self.socket = None
        self.host = host
        self.port = 8080
        self.pin = pin
        self.model = model
        self.obj = {}
        self.verbose = verbose
        self.parser = HybiParser()
        self._last_get_setting_response = None  # Store last response for debugging
        self.connect()
        self.send_upgrade()
        self.send_login()

    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        # Create SSL context with older protocol support for compatibility with older devices
        # The DSP-W245 uses older TLS/SSL protocols
        try:
            # Use PROTOCOL_TLS which allows negotiation of available protocols
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            # Lower security level to allow older ciphers and protocols
            try:
                context.set_ciphers('DEFAULT@SECLEVEL=1')
            except:
                pass
            # Try to set minimum version to allow TLS 1.0
            try:
                # Python 3.7+ has TLSVersion enum
                context.minimum_version = ssl.TLSVersion.MINIMUM_SUPPORTED
            except AttributeError:
                # Older Python versions don't have TLSVersion
                pass
            self.socket = context.wrap_socket(sock, server_hostname=None)
        except Exception:
            # Fallback: use deprecated wrap_socket with most permissive settings
            try:
                # Try PROTOCOL_TLS first (Python 3.6+)
                self.socket = ssl.wrap_socket(
                    sock,
                    ssl_version=ssl.PROTOCOL_TLS,
                    cert_reqs=ssl.CERT_NONE,
                    do_handshake_on_connect=True,
                    suppress_ragged_eofs=True
                )
            except:
                # Last resort: try PROTOCOL_TLSv1 (may be deprecated but might work)
                try:
                    self.socket = ssl.wrap_socket(
                        sock,
                        ssl_version=ssl.PROTOCOL_TLSv1,
                        cert_reqs=ssl.CERT_NONE,
                        do_handshake_on_connect=True,
                        suppress_ragged_eofs=True
                    )
                except:
                    # If all else fails, use default but with no cert verification
                    self.socket = ssl.wrap_socket(
                        sock,
                        cert_reqs=ssl.CERT_NONE
                    )
        self.socket.connect((self.host, self.port))

    def send(self, data, log, raw=False):
        if self.verbose > 0:
            print(log)
        self.socket.send(data)
        r = self.recv(raw)
        if self.verbose > 1:
            print("Recieved:")
            print('"{}"'.format(r))
            print()
        return r

    def recv(self, raw):
        def _recv(n):
            r = [d for d in self.socket.recv(n)]
            return r[0] if n == 1 else r
        return self.socket.recv(1024) if raw else self.parser.decode(_recv)
    
    def recv_until_command(self, expected_command, max_attempts=10):
        """
        Read messages from socket until we get one with the expected command.
        This handles cases where keep_alive or other responses arrive first.
        
        Args:
            expected_command: The command name we're expecting in the response
            max_attempts: Maximum number of messages to read before giving up
            
        Returns:
            The JSON response with the expected command, or None if not found
        """
        import json
        import socket as socket_module
        
        # Save original timeout
        try:
            original_timeout = self.socket.gettimeout()
        except:
            original_timeout = 10
        
        try:
            for _ in range(max_attempts):
                try:
                    # Set a short timeout to avoid blocking indefinitely
                    self.socket.settimeout(1.0)
                    raw_response = self.recv(raw=False)
                    
                    if raw_response:
                        try:
                            response = json.loads(raw_response)
                            if response.get('command') == expected_command:
                                return response
                            # If it's a keep_alive, log it and continue reading
                            elif response.get('command') == 'keep_alive':
                                if self.verbose > 1:
                                    print(f"Received keep_alive response, continuing to read for {expected_command}")
                                continue
                            # For other unexpected commands, log and continue
                            elif self.verbose > 1:
                                print(f"Received unexpected command '{response.get('command')}', continuing to read for {expected_command}")
                                continue
                        except json.JSONDecodeError:
                            if self.verbose > 0:
                                print(f"Failed to parse response as JSON: {raw_response}")
                            continue
                except socket_module.timeout:
                    # Timeout is expected if no message is available
                    if self.verbose > 1:
                        print(f"Timeout waiting for {expected_command} response, retrying...")
                    continue
                except Exception as e:
                    if self.verbose > 0:
                        print(f"Error reading response: {e}")
                    break
        finally:
            # Always restore original timeout
            try:
                self.socket.settimeout(original_timeout)
            except:
                pass
        
        return None

    def close(self):
        self.socket.close()

    def bytes(self, data):
        for i in range(len(data)):
            if data[i] < 0:
                data[i] += 255
        data = bytes(data)
        return data

    def send_json(self, data, log, match_response_command=False):
        """
        Send a JSON command and receive the response.
        
        Args:
            data: The command data dictionary
            log: Log message for the command
            match_response_command: If True, read messages until we get one matching
                                   the sent command. Useful when keep_alive responses
                                   might arrive first.
        """
        import json
        expected_command = data.get('command') if match_response_command else None
        
        d = {
            "sequence_id": 1001, # Does not matter.
        	"local_cid": 41566, # Does not matter.
        	"timestamp": int(time.time()),
            "client_id": "",
        }
        if 'device_id' in self.obj:
            d.update({
            	"device_id": self.obj['device_id'],
        	    "device_token": self.generate_device_token(),
            })
        d.update(data)
        data = d
        data = json.dumps(data)
        data = self.parser.encode(data)
        data = self.bytes(data)
        
        if self.verbose > 0:
            print(log)
        self.socket.send(data)
        
        # Read response, matching command if requested
        if match_response_command and expected_command:
            r = self.recv_until_command(expected_command)
            if r is None:
                # Fallback to regular recv if matching failed
                r = self.recv(raw=False)
                r = json.loads(r)
            # Note: recv_until_command already returns a parsed dict, no need to json.loads
        else:
            r = self.recv(raw=False)
            r = json.loads(r)
        
        if self.verbose > 1:
            print("Recieved:")
            print(json.dumps(r, indent=2))
            print()
        
        if 'code' in r and r['code'] != 0:
            error_msg = r.get('message', 'Unknown error')
            raise Exception(f"Device returned error code {r['code']}: {error_msg}")
        return r

    def send_login(self):
        data = {
            "command": "sign_in",
        }
        res = self.send_json(data, log="Sending sign_in to get salt")
        self.obj = res
        return res

    def generate_device_token(self):
        token = self.pin + self.obj['salt']
        token = hashlib.sha1(token.encode()).hexdigest()
        self.token = "{}-{}".format(self.obj['device_id'], token)
        return self.token

    def device_status(self):
        data = {
        	"command": "device_status",
        }
        return self.send_json(data, log="Sending get device status")

    def send_wlan_survey(self):
        data = {
        	"command": "wlan_survey",
        }
        self.send_json(data, log="Sending get device status")

    def upgrade_fw(self, url):
        """
        The provided url should contain the firmware to upgrade to.
        """
        data = {
        	"command": "fw_upgrade",
        	"timestamp": int(time.time()),
            "url": url,
        }
        self.send_json(data, log="Sending firmware upgrade")

    def send_register(self):
        data = {
        	"command": "register",
            "owner_id": "owneridhere",
            "owner_token": "sometoken",
            "dcd_url": "http://someurl.se/targetfile"
        }
        self.send_json(data, log="Sending register")

    def set_socket(self, socket, on):
        """Set socket state and return the response which may contain state info."""
        return self.set_led(socket, on)

    def u_nr(self):
        return self.obj['device_id'][-4:]

    def test(self):
        """
        Turns all sockets OFF, ON and then OFF again.
        """
        for i in range(4): self.set_socket(i+1, False)
        for i in range(4): self.set_socket(i+1, True)
        for i in range(4): self.set_socket(i+1, False)

    def set_led(self, led, on):
        """
        On the DSP-W245 led can be 1,2,3,4.
        Returns the response from the device, which may contain state information.
        """
        data = {
        	"command": "set_setting",
        	"setting":[
                {
                	"uid": 0,
                	"metadata": {
                	   "value": 1 if on else 0
                    },
                	"name ":"DSP-{}-{}-{}".format(self.model, self.u_nr(), str(led)),
                	"idx": (led - 1),
                	"type": 16
                }
            ]
        }
        on_str = "ON" if on else "OFF"
        return self.send_json(data, log="Turning LED #{} {}".format(led, on_str))

    def send_get_setup_status(self):
        data = {
            "command": "get_setup_status",
        }
        self.send_json(data, log="Sending get setup status")

    def get_socket_states(self, socket=-1):
        """
        Get the current state of socket(s).
        Based on the Node.js implementation: https://github.com/Garfonso/dlinkWebSocketClient
        
        Args:
            socket: Socket index (0-3 for W245, or -1 to get all sockets). Defaults to -1.
        
        Returns:
            Dictionary with socket states {1: True/False, 2: True/False, ...} if socket=-1,
            or boolean for specific socket, or None on error.
        """
        TYPE_SOCKET = 16  # Socket type constant from Node.js implementation
        try:
            # get_setting requires a setting array with type and idx in the request
            data = {
                "command": "get_setting",
                "setting": [{
                    "type": TYPE_SOCKET,
                    "idx": socket
                }]
            }
            # Use match_response_command=True to ensure we get the get_setting response
            # even if keep_alive responses arrive first
            response = self.send_json(data, log="Getting socket settings", match_response_command=True)
            # Store last response for debugging
            self._last_get_setting_response = response
            
            # Log response for debugging if it's invalid
            if 'setting' not in response:
                if self.verbose > 0:
                    import json
                    print(f"Invalid response - missing 'setting' field: {json.dumps(response, indent=2)}")
                return None
            
            if len(response['setting']) == 0:
                if self.verbose > 0:
                    import json
                    print(f"Invalid response - empty 'setting' array: {json.dumps(response, indent=2)}")
                return None
            
            # Parse the response
            setting = response['setting'][0]
            
            if socket >= 0:
                # Single socket query - returns boolean
                if 'metadata' in setting and 'value' in setting['metadata']:
                    return setting['metadata']['value'] == 1
                else:
                    if self.verbose > 0:
                        import json
                        print(f"Invalid response - missing metadata/value in setting: {json.dumps(response, indent=2)}")
                    return None
            else:
                # Query all sockets - returns array in metadata.value
                socket_states = {}
                if 'metadata' in setting and 'value' in setting['metadata']:
                    value_data = setting['metadata']['value']
                    # Check if value is actually a list/array
                    if not isinstance(value_data, list):
                        # Always log this error for debugging
                        import json
                        error_msg = f"Invalid response - metadata.value is not a list: {type(value_data)}, value: {value_data}"
                        if self.verbose > 0:
                            print(error_msg)
                            print(f"Full response: {json.dumps(response, indent=2)}")
                        # Store error in response for HA logging
                        self._last_get_setting_response = response
                        return None
                    
                    # metadata.value is an array of {idx, metadata: {value}}
                    parsed_count = 0
                    for item in value_data:
                        if not isinstance(item, dict):
                            # Only log on error
                            import json
                            if self.verbose > 0:
                                print(f"Invalid response - item in metadata.value is not a dict: {type(item)}, value: {item}")
                            continue
                        
                        if 'idx' in item and 'metadata' in item and isinstance(item['metadata'], dict) and 'value' in item['metadata']:
                            try:
                                socket_num = int(item['idx']) + 1  # Convert 0-based to 1-based
                                socket_value = int(item['metadata']['value'])
                                socket_states[socket_num] = (socket_value == 1)
                                parsed_count += 1
                            except (ValueError, TypeError, KeyError) as e:
                                # Only log on error
                                import json
                                if self.verbose > 0:
                                    print(f"Error parsing socket item: {e}, item: {json.dumps(item, indent=2)}")
                                continue
                        else:
                            # Only log on error - store which check failed for debugging
                            missing = []
                            if 'idx' not in item:
                                missing.append("idx")
                            if 'metadata' not in item:
                                missing.append("metadata")
                            elif not isinstance(item.get('metadata'), dict):
                                missing.append("metadata (not a dict)")
                            elif 'value' not in item.get('metadata', {}):
                                missing.append("metadata.value")
                            
                            # Only log on error
                            import json
                            if self.verbose > 0:
                                print(f"Invalid response - item missing required fields: {missing}, item: {json.dumps(item, indent=2)}")
                    
                    if socket_states:
                        return socket_states
                    else:
                        # Always log this error for debugging
                        import json
                        error_msg = f"Invalid response - no valid socket states parsed (parsed {parsed_count} items from {len(value_data)} total)"
                        if self.verbose > 0:
                            print(error_msg)
                            print(f"Full response: {json.dumps(response, indent=2)}")
                            print(f"value_data: {value_data}")
                            print(f"socket_states dict: {socket_states}")
                        # Store error in response for HA logging
                        self._last_get_setting_response = response
                        return None
                else:
                    # Always log this error for debugging
                    import json
                    error_msg = "Invalid response - missing metadata/value for all sockets"
                    if self.verbose > 0:
                        print(error_msg)
                        print(f"Full response: {json.dumps(response, indent=2)}")
                    # Store error in response for HA logging
                    self._last_get_setting_response = response
                    return None
        except Exception as e:
            import traceback
            import json
            error_msg = f"Exception in get_socket_states: {e}"
            if self.verbose > 0:
                print(error_msg)
                print(f"Traceback: {traceback.format_exc()}")
            # Store error in response for HA logging
            try:
                self._last_get_setting_response = response
            except:
                pass
            return None

    def keep_alive(self):
        data = {
            "command": "keep_alive",
        }
        self.send_json(data, log="Sending keep alive")

    def send_upgrade(self):
        data = "GET /SwitchCamera HTTP/1.1\r\n" \
             + "Host: " + self.host + ":" + str(self.port) + "\r\n" \
             + "Connection: Upgrade\r\n" \
             + "Accept: */*\r\n" \
             + "Sec-WebSocket-Version: 13\r\n" \
             + "Sec-WebSocket-Key: \r\n" \
             + "Sec-WebSocket-Extensions: x-webkit-deflate-frame\r\n" \
             + "Upgrade: websocket\r\n" \
             + "Sec-WebSocket-Protocol: \r\n" \
             + "Pragma: no-cache\r\n" \
             + "Cache-Control: no-cache\r\n\r\n"
        data = data.encode('utf-8')
        self.send(data, log="Sending HTTP upgrade request", raw=True)

if __name__ == "__main__":
    HOST = "192.168.0.20"
    pin = "000000"

    sp = SmartPlug(HOST, pin, verbose=1)

    sp.device_status()
    sp.set_led(1, True)
    sp.set_led(2, False)
    sp.keep_alive()

    sp.close()
